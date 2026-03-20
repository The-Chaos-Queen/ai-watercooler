"""
linearity_probe.py - bridge diagnostics entry point.

Modes:
    context-pca      Analyze saved compressed-state vectors from
                     --save-train-contexts / --save-eval-contexts.
    hyper-linearity  Measure how well a linear map predicts generated
                     LoRA weights from saved compressed-state vectors.

This keeps the probe surface in one place so compressor-collapse and
hypernetwork-linearity checks live side by side.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import torch

from models import LoRAHypernetwork


def load_torch_object(path: Path) -> Any:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def load_context_rows(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in paths:
        payload = load_torch_object(path)
        if not isinstance(payload, list):
            raise TypeError(f"{path} did not contain a list of context rows")
        for index, row in enumerate(payload):
            if not isinstance(row, dict) or "context_vector" not in row:
                raise TypeError(f"{path} row {index} is missing a 'context_vector' entry")
            enriched = dict(row)
            enriched["source_path"] = str(path)
            rows.append(enriched)
    if not rows:
        raise ValueError("No context rows were found in the provided files")
    return rows


def stack_context_matrix(rows: Sequence[Dict[str, Any]]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    vectors: List[np.ndarray] = []
    projection_rows: List[Dict[str, Any]] = []
    expected_dim: int | None = None

    for sample_index, row in enumerate(rows):
        vector = torch.as_tensor(row["context_vector"]).detach().cpu().numpy().astype(np.float64, copy=False)
        flat = vector.reshape(-1)
        if expected_dim is None:
            expected_dim = int(flat.shape[0])
        elif int(flat.shape[0]) != expected_dim:
            raise ValueError(
                f"Context dimensionality mismatch at row {sample_index}: "
                f"got {flat.shape[0]}, expected {expected_dim}"
            )
        vectors.append(flat)
        projection_rows.append(
            {
                "sample_index": sample_index,
                "source_path": row.get("source_path", ""),
                "fact_kind": row.get("fact_kind", ""),
                "question_text": row.get("question_text", ""),
                "answer_text": row.get("answer_text", ""),
            }
        )

    matrix = np.stack(vectors, axis=0)
    return matrix, projection_rows


def maybe_subsample_rows(
    matrix: np.ndarray,
    rows: Sequence[Dict[str, Any]],
    max_samples: int,
    seed: int,
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    if max_samples <= 0 or matrix.shape[0] <= max_samples:
        return matrix, list(rows)
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(matrix.shape[0], size=max_samples, replace=False))
    subset_rows = [dict(rows[index]) for index in indices]
    return matrix[indices], subset_rows


def dims_for_fraction(cumulative: np.ndarray, threshold: float) -> int:
    if cumulative.size == 0:
        return 0
    return int(np.searchsorted(cumulative, threshold, side="left") + 1)


def pairwise_l2_stats(matrix: np.ndarray) -> Dict[str, float]:
    sample_count = int(matrix.shape[0])
    if sample_count < 2:
        return {
            "pairwise_l2_mean": 0.0,
            "pairwise_l2_median": 0.0,
            "pairwise_l2_min": 0.0,
            "pairwise_l2_max": 0.0,
        }

    sq_norms = np.sum(matrix * matrix, axis=1, keepdims=True)
    sq_dist = sq_norms + sq_norms.T - (2.0 * matrix @ matrix.T)
    sq_dist = np.maximum(sq_dist, 0.0)
    upper = sq_dist[np.triu_indices(sample_count, k=1)]
    distances = np.sqrt(upper)
    return {
        "pairwise_l2_mean": float(np.mean(distances)),
        "pairwise_l2_median": float(np.median(distances)),
        "pairwise_l2_min": float(np.min(distances)),
        "pairwise_l2_max": float(np.max(distances)),
    }


def collapse_heuristic(
    explained_variance_ratio: np.ndarray,
    effective_rank: float,
    dims_90: int,
    sample_count: int,
) -> str:
    if sample_count < 8:
        return "too_few_samples"
    pc1 = float(explained_variance_ratio[0]) if explained_variance_ratio.size else 0.0
    if pc1 >= 0.85 or dims_90 <= 2 or effective_rank < 2.5:
        return "strong_concentration"
    if pc1 >= 0.60 or dims_90 <= 6 or effective_rank < 6.0:
        return "moderate_concentration"
    return "distributed"


def compute_context_pca_report(
    matrix: np.ndarray,
    rows: Sequence[Dict[str, Any]],
    top_components: int,
    projection_dims: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    sample_count, context_dim = matrix.shape
    centroid = matrix.mean(axis=0)
    centered = matrix - centroid

    try:
        _, singular_values, vt = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError as exc:
        raise RuntimeError(f"SVD failed for context matrix with shape {matrix.shape}") from exc

    if sample_count > 1:
        explained_variance = (singular_values ** 2) / float(sample_count - 1)
    else:
        explained_variance = np.zeros_like(singular_values)
    total_variance = float(np.sum(explained_variance))
    if total_variance > 0.0:
        explained_variance_ratio = explained_variance / total_variance
    else:
        explained_variance_ratio = np.zeros_like(explained_variance)
    cumulative = np.cumsum(explained_variance_ratio)

    nonzero = explained_variance_ratio[explained_variance_ratio > 0]
    effective_rank = float(math.exp(-np.sum(nonzero * np.log(nonzero)))) if nonzero.size else 0.0
    stable_rank = (
        float(np.sum(explained_variance) / np.max(explained_variance))
        if explained_variance.size and float(np.max(explained_variance)) > 0.0
        else 0.0
    )

    norms = np.linalg.norm(matrix, axis=1)
    centroid_l2 = np.linalg.norm(centered, axis=1)
    projection_rank = min(max(1, projection_dims), vt.shape[0]) if vt.ndim == 2 else 1
    projected = centered @ vt[:projection_rank].T

    projection_rows: List[Dict[str, Any]] = []
    for row_meta, coords, norm, dist in zip(rows, projected, norms, centroid_l2):
        projection_row = dict(row_meta)
        projection_row["context_norm"] = float(norm)
        projection_row["centroid_l2"] = float(dist)
        for dim_index in range(projection_rank):
            projection_row[f"pc{dim_index + 1}"] = float(coords[dim_index])
        projection_rows.append(projection_row)

    fact_kind_counts = Counter(str(row.get("fact_kind", "")) for row in rows if row.get("fact_kind", "") != "")
    dims_80 = dims_for_fraction(cumulative, 0.80)
    dims_90 = dims_for_fraction(cumulative, 0.90)
    dims_95 = dims_for_fraction(cumulative, 0.95)

    report = {
        "mode": "context_pca",
        "sample_count": sample_count,
        "context_dim": context_dim,
        "centroid_norm": float(np.linalg.norm(centroid)),
        "context_norm_mean": float(np.mean(norms)),
        "context_norm_std": float(np.std(norms)),
        "centroid_l2_mean": float(np.mean(centroid_l2)),
        "centroid_l2_std": float(np.std(centroid_l2)),
        "explained_variance_ratio": [float(x) for x in explained_variance_ratio[:top_components]],
        "cumulative_explained_variance": [float(x) for x in cumulative[:top_components]],
        "dims_for_80pct": dims_80,
        "dims_for_90pct": dims_90,
        "dims_for_95pct": dims_95,
        "effective_rank": effective_rank,
        "stable_rank": stable_rank,
        "fact_kind_counts": dict(sorted(fact_kind_counts.items())),
        "heuristic_interpretation": collapse_heuristic(
            explained_variance_ratio=explained_variance_ratio,
            effective_rank=effective_rank,
            dims_90=dims_90,
            sample_count=sample_count,
        ),
        "heuristic_note": (
            "Heuristic only: strong_concentration means the manifold is dominated by a small number "
            "of principal directions."
        ),
    }
    report.update(pairwise_l2_stats(matrix))
    return report, projection_rows


def default_output_path(first_source: Path, suffix: str) -> Path:
    return first_source.with_name(f"{first_source.stem}_{suffix}")


def write_projection_csv(path: Path, rows: Sequence[Dict[str, Any]], projection_dims: int) -> None:
    fieldnames = [
        "sample_index",
        "source_path",
        "fact_kind",
        "question_text",
        "answer_text",
        "context_norm",
        "centroid_l2",
    ]
    fieldnames.extend(f"pc{index}" for index in range(1, projection_dims + 1))

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def append_bias_column(matrix: np.ndarray) -> np.ndarray:
    ones = np.ones((matrix.shape[0], 1), dtype=matrix.dtype)
    return np.concatenate([matrix, ones], axis=1)


def infer_target_dims(
    hyper_state_dict: Dict[str, torch.Tensor],
    lora_rank: int,
) -> List[Tuple[int, int]]:
    head_indices: List[int] = []
    pattern = re.compile(r"^heads_A\.(\d+)\.weight$")
    for key in hyper_state_dict:
        match = pattern.match(key)
        if match:
            head_indices.append(int(match.group(1)))
    if not head_indices:
        raise ValueError("Could not infer target heads from hypernetwork state_dict")

    target_dims: List[Tuple[int, int]] = []
    for head_index in sorted(head_indices):
        key_a = f"heads_A.{head_index}.weight"
        key_b = f"heads_B.{head_index}.weight"
        if key_a not in hyper_state_dict or key_b not in hyper_state_dict:
            raise KeyError(f"Missing hypernetwork head weights for target index {head_index}")
        rows_a = int(hyper_state_dict[key_a].shape[0])
        rows_b = int(hyper_state_dict[key_b].shape[0])
        if rows_a % lora_rank != 0 or rows_b % lora_rank != 0:
            raise ValueError(
                f"Head {head_index} shapes are incompatible with lora_rank={lora_rank}: "
                f"A_rows={rows_a}, B_rows={rows_b}"
            )
        target_dims.append((rows_a // lora_rank, rows_b // lora_rank))
    return target_dims


def load_hypernetwork_from_checkpoint(checkpoint_path: Path) -> Dict[str, Any]:
    checkpoint = load_torch_object(checkpoint_path)
    if not isinstance(checkpoint, dict):
        raise TypeError(f"{checkpoint_path} did not contain a checkpoint dictionary")
    if "hypernetwork_state_dict" not in checkpoint:
        raise KeyError(f"{checkpoint_path} is missing hypernetwork_state_dict")

    bridge_config = checkpoint.get("bridge_config", {})
    if not isinstance(bridge_config, dict):
        raise TypeError(f"{checkpoint_path} bridge_config is not a dictionary")

    hyper_state = checkpoint["hypernetwork_state_dict"]
    if not isinstance(hyper_state, dict):
        raise TypeError(f"{checkpoint_path} hypernetwork_state_dict is not a dictionary")

    lora_rank = int(bridge_config.get("lora_rank", 0))
    if lora_rank <= 0:
        raise ValueError(f"{checkpoint_path} has invalid lora_rank={lora_rank}")

    if "backbone.0.weight" not in hyper_state:
        raise KeyError(f"{checkpoint_path} is missing backbone.0.weight in hypernetwork state")

    hidden_dim = int(hyper_state["backbone.0.weight"].shape[0])
    context_dim = int(hyper_state["backbone.0.weight"].shape[1])
    target_dims = infer_target_dims(hyper_state, lora_rank=lora_rank)

    hypernetwork = LoRAHypernetwork(
        context_dim=context_dim,
        target_dims=target_dims,
        lora_rank=lora_rank,
        hidden_dim=hidden_dim,
    )
    hypernetwork.load_state_dict(hyper_state)
    hypernetwork.eval()

    raw_target_specs = checkpoint.get("target_specs", [])
    target_specs: List[str] = []
    for index, spec in enumerate(raw_target_specs):
        if isinstance(spec, (list, tuple)) and len(spec) == 2:
            target_specs.append(f"{spec[0]}:{spec[1]}")
        else:
            target_specs.append(f"target_{index}")
    if len(target_specs) != len(target_dims):
        target_specs = [f"target_{index}" for index in range(len(target_dims))]

    return {
        "checkpoint": checkpoint,
        "bridge_config": bridge_config,
        "context_dim": context_dim,
        "hidden_dim": hidden_dim,
        "lora_rank": lora_rank,
        "target_dims": target_dims,
        "target_specs": target_specs,
        "hypernetwork": hypernetwork,
    }


def flatten_hypernetwork_outputs(
    hypernetwork: LoRAHypernetwork,
    context_matrix: np.ndarray,
) -> List[np.ndarray]:
    with torch.no_grad():
        context_tensor = torch.from_numpy(context_matrix).to(dtype=hypernetwork.backbone[0].weight.dtype)
        pairs = hypernetwork(context_tensor)

    flattened: List[np.ndarray] = []
    for A, B in pairs:
        batch_size = int(A.shape[0])
        flat = torch.cat([A.reshape(batch_size, -1), B.reshape(batch_size, -1)], dim=1)
        flattened.append(flat.detach().cpu().numpy().astype(np.float64, copy=False))
    return flattened


def make_cv_folds(sample_count: int, fold_count: int, seed: int) -> List[np.ndarray]:
    if sample_count < 2:
        raise ValueError("Need at least 2 samples for cross-validated linearity analysis")
    effective_folds = max(2, min(fold_count, sample_count))
    order = np.random.default_rng(seed).permutation(sample_count)
    fold_sizes = [sample_count // effective_folds] * effective_folds
    for index in range(sample_count % effective_folds):
        fold_sizes[index] += 1

    folds: List[np.ndarray] = []
    cursor = 0
    for size in fold_sizes:
        folds.append(order[cursor : cursor + size])
        cursor += size
    return folds


def ratio_from_squares(residual_sq: float, target_sq: float) -> float:
    if target_sq <= 0.0:
        return 0.0
    return float(math.sqrt(max(residual_sq, 0.0) / target_sq))


def explained_fraction_from_ratio(ratio: float) -> float:
    value = 1.0 - (ratio * ratio)
    return float(max(0.0, min(1.0, value)))


def linearity_heuristic(cv_ratio: float) -> str:
    if cv_ratio <= 0.10:
        return "mostly_linear"
    if cv_ratio <= 0.35:
        return "mixed"
    return "substantially_nonlinear"


def compute_full_fit_stats(
    context_matrix: np.ndarray,
    flattened_outputs: Sequence[np.ndarray],
    target_specs: Sequence[str],
    target_dims: Sequence[Tuple[int, int]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    augmented = append_bias_column(context_matrix)
    projection = augmented @ np.linalg.pinv(augmented)

    total_target_sq = 0.0
    total_residual_sq = 0.0
    per_target: List[Dict[str, Any]] = []

    for target_index, (target_matrix, spec, (in_dim, out_dim)) in enumerate(
        zip(flattened_outputs, target_specs, target_dims)
    ):
        predicted = projection @ target_matrix
        residual = target_matrix - predicted
        target_sq = float(np.sum(target_matrix * target_matrix))
        residual_sq = float(np.sum(residual * residual))
        total_target_sq += target_sq
        total_residual_sq += residual_sq
        per_target.append(
            {
                "target_index": target_index,
                "target_spec": spec,
                "in_dim": int(in_dim),
                "out_dim": int(out_dim),
                "output_dim": int(target_matrix.shape[1]),
                "full_fit_linearity_ratio": ratio_from_squares(residual_sq, target_sq),
                "full_fit_linear_explained_fraction": explained_fraction_from_ratio(
                    ratio_from_squares(residual_sq, target_sq)
                ),
            }
        )

    return (
        {
            "full_fit_linearity_ratio": ratio_from_squares(total_residual_sq, total_target_sq),
            "full_fit_linear_explained_fraction": explained_fraction_from_ratio(
                ratio_from_squares(total_residual_sq, total_target_sq)
            ),
        },
        per_target,
    )


def compute_cross_validated_linearity_report(
    context_matrix: np.ndarray,
    flattened_outputs: Sequence[np.ndarray],
    target_specs: Sequence[str],
    target_dims: Sequence[Tuple[int, int]],
    fold_count: int,
    seed: int,
) -> Dict[str, Any]:
    sample_count, context_dim = context_matrix.shape
    folds = make_cv_folds(sample_count=sample_count, fold_count=fold_count, seed=seed)

    total_target_sq = 0.0
    total_residual_sq = 0.0
    sample_target_sq = np.zeros(sample_count, dtype=np.float64)
    sample_residual_sq = np.zeros(sample_count, dtype=np.float64)

    per_target_target_sq = [0.0 for _ in flattened_outputs]
    per_target_residual_sq = [0.0 for _ in flattened_outputs]
    fold_reports: List[Dict[str, Any]] = []

    all_indices = np.arange(sample_count)
    for fold_index, test_indices in enumerate(folds):
        train_mask = np.ones(sample_count, dtype=bool)
        train_mask[test_indices] = False
        train_indices = all_indices[train_mask]
        if train_indices.size == 0 or test_indices.size == 0:
            continue

        x_train = append_bias_column(context_matrix[train_indices])
        x_test = append_bias_column(context_matrix[test_indices])
        kernel = x_test @ np.linalg.pinv(x_train)

        fold_target_sq = 0.0
        fold_residual_sq = 0.0
        for target_index, target_matrix in enumerate(flattened_outputs):
            y_train = target_matrix[train_indices]
            y_test = target_matrix[test_indices]
            y_pred = kernel @ y_train
            residual = y_test - y_pred

            target_sq = float(np.sum(y_test * y_test))
            residual_sq = float(np.sum(residual * residual))
            fold_target_sq += target_sq
            fold_residual_sq += residual_sq
            total_target_sq += target_sq
            total_residual_sq += residual_sq
            per_target_target_sq[target_index] += target_sq
            per_target_residual_sq[target_index] += residual_sq

            sample_target_sq[test_indices] += np.sum(y_test * y_test, axis=1)
            sample_residual_sq[test_indices] += np.sum(residual * residual, axis=1)

        fold_reports.append(
            {
                "fold_index": fold_index,
                "train_size": int(train_indices.size),
                "test_size": int(test_indices.size),
                "linearity_ratio": ratio_from_squares(fold_residual_sq, fold_target_sq),
                "linear_explained_fraction": explained_fraction_from_ratio(
                    ratio_from_squares(fold_residual_sq, fold_target_sq)
                ),
            }
        )

    per_target_reports: List[Dict[str, Any]] = []
    for target_index, (spec, (in_dim, out_dim), target_matrix) in enumerate(
        zip(target_specs, target_dims, flattened_outputs)
    ):
        cv_ratio = ratio_from_squares(per_target_residual_sq[target_index], per_target_target_sq[target_index])
        per_target_reports.append(
            {
                "target_index": target_index,
                "target_spec": spec,
                "in_dim": int(in_dim),
                "out_dim": int(out_dim),
                "output_dim": int(target_matrix.shape[1]),
                "cv_linearity_ratio": cv_ratio,
                "cv_linear_explained_fraction": explained_fraction_from_ratio(cv_ratio),
            }
        )

    overall_ratio = ratio_from_squares(total_residual_sq, total_target_sq)
    full_fit_summary, full_fit_per_target = compute_full_fit_stats(
        context_matrix=context_matrix,
        flattened_outputs=flattened_outputs,
        target_specs=target_specs,
        target_dims=target_dims,
    )
    for summary, full_fit in zip(per_target_reports, full_fit_per_target):
        summary.update(full_fit)

    sample_ratio = np.zeros(sample_count, dtype=np.float64)
    nonzero_mask = sample_target_sq > 0.0
    sample_ratio[nonzero_mask] = np.sqrt(sample_residual_sq[nonzero_mask] / sample_target_sq[nonzero_mask])

    total_output_dim = int(sum(target_matrix.shape[1] for target_matrix in flattened_outputs))
    report = {
        "mode": "hyper_linearity",
        "sample_count": sample_count,
        "context_dim": context_dim,
        "total_output_dim": total_output_dim,
        "fold_count": len(folds),
        "cv_linearity_ratio": overall_ratio,
        "cv_linear_explained_fraction": explained_fraction_from_ratio(overall_ratio),
        "heuristic_interpretation": linearity_heuristic(overall_ratio),
        "heuristic_note": (
            "Linearity ratio is cross-validated residual_norm / target_norm. "
            "Lower means a simple linear map predicts the generated LoRA weights well."
        ),
        "sample_linearity_ratio_mean": float(np.mean(sample_ratio)),
        "sample_linearity_ratio_std": float(np.std(sample_ratio)),
        "folds": fold_reports,
        "per_target": per_target_reports,
        "full_fit_note": (
            "Full-fit metrics use the same samples for fit and evaluation and can look deceptively linear "
            "when context_dim exceeds sample_count. Prefer the cross-validated ratio above."
        ),
    }
    report.update(full_fit_summary)
    return report


def run_context_pca(args: argparse.Namespace) -> int:
    context_paths = [Path(path).expanduser().resolve() for path in args.contexts]
    rows = load_context_rows(context_paths)
    matrix, projection_rows = stack_context_matrix(rows)
    matrix, projection_rows = maybe_subsample_rows(
        matrix=matrix,
        rows=projection_rows,
        max_samples=args.max_samples,
        seed=args.seed,
    )
    report, projected_rows = compute_context_pca_report(
        matrix=matrix,
        rows=projection_rows,
        top_components=args.top_components,
        projection_dims=args.projection_dims,
    )
    report["sources"] = [str(path) for path in context_paths]

    output_json = (
        Path(args.output_json).expanduser().resolve()
        if args.output_json
        else default_output_path(context_paths[0], "pca_report.json")
    )
    output_csv = (
        Path(args.projection_csv).expanduser().resolve()
        if args.projection_csv
        else default_output_path(context_paths[0], "pca_projection.csv")
    )

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    write_projection_csv(output_csv, projected_rows, projection_dims=args.projection_dims)

    top_ratios = report["explained_variance_ratio"][: min(3, len(report["explained_variance_ratio"]))]
    ratio_str = ", ".join(f"pc{index + 1}={value:.4f}" for index, value in enumerate(top_ratios))
    print(
        f"Loaded {report['sample_count']} contexts with dim={report['context_dim']} from "
        f"{len(context_paths)} file(s)."
    )
    if ratio_str:
        print(f"Top components: {ratio_str}")
    print(
        "Collapse view: "
        f"dims@90%={report['dims_for_90pct']} effective_rank={report['effective_rank']:.2f} "
        f"pairwise_l2_mean={report['pairwise_l2_mean']:.4f} heuristic={report['heuristic_interpretation']}"
    )
    print(f"Wrote JSON report: {output_json}")
    print(f"Wrote projection CSV: {output_csv}")
    return 0


def run_hyper_linearity(args: argparse.Namespace) -> int:
    checkpoint_path = Path(args.checkpoint).expanduser().resolve()
    context_paths = [Path(path).expanduser().resolve() for path in args.contexts]

    checkpoint_info = load_hypernetwork_from_checkpoint(checkpoint_path)
    rows = load_context_rows(context_paths)
    context_matrix, projection_rows = stack_context_matrix(rows)
    context_matrix, projection_rows = maybe_subsample_rows(
        matrix=context_matrix,
        rows=projection_rows,
        max_samples=args.max_samples,
        seed=args.seed,
    )

    expected_dim = int(checkpoint_info["context_dim"])
    if context_matrix.shape[1] != expected_dim:
        raise ValueError(
            f"Context dimensionality mismatch: contexts have dim={context_matrix.shape[1]}, "
            f"checkpoint hypernetwork expects dim={expected_dim}"
        )

    flattened_outputs = flatten_hypernetwork_outputs(
        hypernetwork=checkpoint_info["hypernetwork"],
        context_matrix=context_matrix,
    )
    report = compute_cross_validated_linearity_report(
        context_matrix=context_matrix,
        flattened_outputs=flattened_outputs,
        target_specs=checkpoint_info["target_specs"],
        target_dims=checkpoint_info["target_dims"],
        fold_count=args.folds,
        seed=args.seed,
    )
    report["checkpoint_path"] = str(checkpoint_path)
    report["sources"] = [str(path) for path in context_paths]
    report["bridge_config"] = {
        "qwen_model_id": checkpoint_info["bridge_config"].get("qwen_model_id"),
        "mamba_model_id": checkpoint_info["bridge_config"].get("mamba_model_id"),
        "lora_rank": checkpoint_info["bridge_config"].get("lora_rank"),
        "lora_alpha": checkpoint_info["bridge_config"].get("lora_alpha"),
        "lora_scaling": checkpoint_info["bridge_config"].get("lora_scaling"),
        "hyper_hidden_dim": checkpoint_info["bridge_config"].get("hyper_hidden_dim"),
        "context_dim": checkpoint_info["bridge_config"].get("context_dim"),
    }
    report["target_specs"] = list(checkpoint_info["target_specs"])

    output_json = (
        Path(args.output_json).expanduser().resolve()
        if args.output_json
        else default_output_path(checkpoint_path, "hyper_linearity.json")
    )
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(
        f"Loaded checkpoint with {len(checkpoint_info['target_dims'])} target(s), "
        f"context_dim={report['context_dim']} and total_output_dim={report['total_output_dim']}."
    )
    print(
        "Cross-validated linearity: "
        f"ratio={report['cv_linearity_ratio']:.4f} "
        f"explained={report['cv_linear_explained_fraction']:.4f} "
        f"heuristic={report['heuristic_interpretation']}"
    )
    print(
        "In-sample fit (for reference only): "
        f"ratio={report['full_fit_linearity_ratio']:.4f} "
        f"explained={report['full_fit_linear_explained_fraction']:.4f}"
    )
    print(f"Wrote JSON report: {output_json}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge diagnostics for saved compressed-state artifacts.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    pca_parser = subparsers.add_parser(
        "context-pca",
        help="Run PCA/collapse analysis over one or more *_contexts.pt files.",
    )
    pca_parser.add_argument("contexts", nargs="+", help="Saved *_contexts.pt files from train_bridge.py")
    pca_parser.add_argument("--output-json", type=str, default="", help="Optional path for the JSON summary report.")
    pca_parser.add_argument(
        "--projection-csv",
        type=str,
        default="",
        help="Optional path for the per-sample PCA projection CSV.",
    )
    pca_parser.add_argument(
        "--top-components",
        type=int,
        default=8,
        help="How many explained-variance entries to store in the JSON summary.",
    )
    pca_parser.add_argument(
        "--projection-dims",
        type=int,
        default=3,
        help="How many principal-component coordinates to write per sample.",
    )
    pca_parser.add_argument(
        "--max-samples",
        type=int,
        default=0,
        help="Optional sample cap for faster local diagnostics; 0 uses all rows.",
    )
    pca_parser.add_argument("--seed", type=int, default=1337, help="Seed used when subsampling rows.")

    hyper_parser = subparsers.add_parser(
        "hyper-linearity",
        help="Cross-validated linear fit from saved contexts to generated LoRA weights.",
    )
    hyper_parser.add_argument("checkpoint", help="Bridge checkpoint (*.pt) with hypernetwork weights.")
    hyper_parser.add_argument("contexts", nargs="+", help="Saved *_contexts.pt files from train_bridge.py")
    hyper_parser.add_argument("--output-json", type=str, default="", help="Optional path for the JSON summary report.")
    hyper_parser.add_argument(
        "--folds",
        type=int,
        default=5,
        help="Number of cross-validation folds for the linearity probe.",
    )
    hyper_parser.add_argument(
        "--max-samples",
        type=int,
        default=0,
        help="Optional sample cap for faster diagnostics; 0 uses all rows.",
    )
    hyper_parser.add_argument("--seed", type=int, default=1337, help="Seed for fold shuffling/subsampling.")

    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.mode == "context-pca":
        return run_context_pca(args)
    if args.mode == "hyper-linearity":
        return run_hyper_linearity(args)
    raise ValueError(f"Unsupported mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
