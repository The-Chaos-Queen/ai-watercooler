#!/usr/bin/env python3
"""CPU-only retrospective variance/rank/norm diagnosis for a frozen bridge result.

This tool deliberately reads only the retained bridge artifact.  It never loads
Mamba or Gemma, captures activations, trains a bridge, writes back to its input,
or uses CUDA.  Train-only norm calibrations are descriptive post-run probes;
the eval-target-norm rescale is explicitly oracle-only and non-deployable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch

import run_gemma_value_norm_bridge_refit_eval as refit
import train_gemma_value_norm_bridge_microtrain as microtrain


SCHEMA_VERSION = "bridge_refit_norm_rank_diagnostic/v1"
EXPECTED_TRAIN_ROWS = 24
EXPECTED_EVAL_ROWS = 8
DEFAULT_REPRODUCTION_ATOL = 1e-5
DEFAULT_REPRODUCTION_RTOL = 1e-5


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json_no_overwrite(value: Mapping[str, Any], path: Path) -> str:
    """Atomically publish a JSON result without replacing an existing result."""

    payload = _canonical_json_bytes(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite artifact: {path}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        digest = _file_sha256(temporary)
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise FileExistsError(f"concurrent artifact exists: {path}") from exc
        return digest
    finally:
        temporary.unlink(missing_ok=True)


def _finite_float(value: float | torch.Tensor) -> float | None:
    result = float(value)
    return result if math.isfinite(result) else None


def _matrix(value: Any, *, label: str, width: int) -> torch.Tensor:
    matrix = torch.as_tensor(value).detach().cpu().float().contiguous()
    if matrix.ndim != 2 or matrix.shape[1] != width:
        raise ValueError(f"{label} must have shape [N,{width}], got {tuple(matrix.shape)}")
    if matrix.shape[0] < 2:
        raise ValueError(f"{label} needs at least two rows")
    if not torch.isfinite(matrix).all():
        raise ValueError(f"{label} contains non-finite values")
    return matrix


def _row_norms(matrix: torch.Tensor) -> torch.Tensor:
    return matrix.float().norm(dim=-1)


def scalar_stats(values: torch.Tensor) -> dict[str, float | None]:
    values = torch.as_tensor(values).detach().cpu().float().reshape(-1)
    if values.numel() < 1 or not torch.isfinite(values).all():
        raise ValueError("scalar statistics need finite non-empty values")
    mean = values.mean()
    sd = values.std(unbiased=False)
    return {
        "mean": _finite_float(mean),
        "median": _finite_float(values.median()),
        "sd_population": _finite_float(sd),
        "cv_population": _finite_float(sd / mean) if mean > 0 else None,
        "min": _finite_float(values.min()),
        "max": _finite_float(values.max()),
    }


def norm_stats(matrix: torch.Tensor) -> dict[str, float | None]:
    return scalar_stats(_row_norms(matrix))


def pearson_correlation(left: torch.Tensor, right: torch.Tensor) -> float | None:
    left = torch.as_tensor(left).detach().cpu().float().reshape(-1)
    right = torch.as_tensor(right).detach().cpu().float().reshape(-1)
    if left.shape != right.shape or left.numel() < 2:
        raise ValueError("Pearson correlation needs equally shaped vectors with at least two values")
    centered_left = left - left.mean()
    centered_right = right - right.mean()
    denominator = (centered_left.square().sum() * centered_right.square().sum()).sqrt()
    return _finite_float((centered_left * centered_right).sum() / denominator) if denominator > 0 else None


def centered_spectrum(matrix: torch.Tensor) -> dict[str, Any]:
    """Report centered sample-space rank and spectral concentration, never a population rank claim."""

    matrix = torch.as_tensor(matrix).detach().cpu().float()
    centered = matrix - matrix.mean(dim=0, keepdim=True)
    singular_values = torch.linalg.svdvals(centered)
    energy = singular_values.square()
    total_energy = energy.sum()
    proportions = energy / total_energy if total_energy > 0 else torch.zeros_like(energy)
    nonzero = proportions[proportions > 0]
    entropy_effective_rank = torch.exp(-(nonzero * nonzero.log()).sum()) if nonzero.numel() else torch.tensor(0.0)
    stable_rank = total_energy / energy.max() if energy.numel() and energy.max() > 0 else torch.tensor(0.0)
    tolerance = (
        torch.finfo(singular_values.dtype).eps * max(centered.shape) * singular_values[0]
        if singular_values.numel()
        else torch.tensor(0.0)
    )
    return {
        "n_rows": int(matrix.shape[0]),
        "width": int(matrix.shape[1]),
        "centered_numerical_rank": int((singular_values > tolerance).sum()),
        "centered_entropy_effective_rank": _finite_float(entropy_effective_rank),
        "centered_stable_rank": _finite_float(stable_rank),
        "centered_pc1_energy_fraction": _finite_float(proportions[0]) if proportions.numel() else None,
        "centered_top3_energy_fraction": _finite_float(proportions[:3].sum()) if proportions.numel() else None,
        "centered_singular_values": [_finite_float(value) for value in singular_values.tolist()],
    }


def fit_positive_vector_l2_scale(prediction: torch.Tensor, target: torch.Tensor) -> dict[str, float | bool]:
    """Fit one nonnegative scalar on train vectors only to minimize vector L2 error.

    A negative unconstrained solution would reverse a predicted activation
    direction.  The constrained optimum is therefore exactly zero, retained
    and reported rather than turning an unrelated bridge into a crash-only
    artifact.
    """

    prediction = torch.as_tensor(prediction).detach().cpu().float()
    target = torch.as_tensor(target).detach().cpu().float()
    if prediction.shape != target.shape or prediction.ndim != 2:
        raise ValueError("vector L2 calibration needs equally shaped rank-2 matrices")
    denominator = prediction.square().sum()
    if denominator <= 0:
        raise ValueError("vector L2 calibration needs nonzero predicted energy")
    unconstrained_alpha = (prediction * target).sum() / denominator
    if not torch.isfinite(unconstrained_alpha):
        raise ValueError("train vector L2 calibration produced a non-finite scale")
    alpha = unconstrained_alpha.clamp_min(0.0)
    return {
        "alpha": float(alpha),
        "unconstrained_alpha": float(unconstrained_alpha),
        "nonnegative_constraint_active": bool(unconstrained_alpha < 0),
    }


def fit_affine_norm(prediction: torch.Tensor, target: torch.Tensor) -> dict[str, float | None]:
    """Fit target_norm = slope * predicted_norm + intercept on train rows only."""

    prediction = torch.as_tensor(prediction).detach().cpu().float()
    target = torch.as_tensor(target).detach().cpu().float()
    if prediction.shape != target.shape or prediction.ndim != 2:
        raise ValueError("affine norm calibration needs equally shaped rank-2 matrices")
    predicted_norms = _row_norms(prediction)
    target_norms = _row_norms(target)
    design = torch.stack((predicted_norms, torch.ones_like(predicted_norms)), dim=1)
    solution = torch.linalg.lstsq(design, target_norms.unsqueeze(1)).solution.squeeze(1)
    slope, intercept = solution[0], solution[1]
    fitted = slope * predicted_norms + intercept
    residual = (target_norms - fitted).square().sum()
    total = (target_norms - target_norms.mean()).square().sum()
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "train_r2": _finite_float(1.0 - residual / total) if total > 0 else None,
        "train_pearson_predicted_to_target_norm": pearson_correlation(predicted_norms, target_norms),
    }


def apply_affine_norm(prediction: torch.Tensor, fit: Mapping[str, float | None]) -> torch.Tensor:
    """Apply a train-fitted affine norm map without changing each predicted direction."""

    prediction = torch.as_tensor(prediction).detach().cpu().float()
    slope = fit.get("slope")
    intercept = fit.get("intercept")
    if slope is None or intercept is None:
        raise ValueError("affine norm fit requires finite slope and intercept")
    current_norms = _row_norms(prediction).clamp_min(1e-12)
    desired_norms = (float(slope) * current_norms + float(intercept)).clamp_min(0.0)
    return prediction * (desired_norms / current_norms).unsqueeze(1)


def apply_oracle_target_norm(prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Diagnostic-only: rescale each eval prediction by its true eval target norm."""

    prediction = torch.as_tensor(prediction).detach().cpu().float()
    target = torch.as_tensor(target).detach().cpu().float()
    if prediction.shape != target.shape or prediction.ndim != 2:
        raise ValueError("oracle norm rescale needs equally shaped rank-2 matrices")
    return prediction * (_row_norms(target) / _row_norms(prediction).clamp_min(1e-12)).unsqueeze(1)


def _compact_evaluation(
    *,
    predictions: Mapping[int, torch.Tensor],
    eval_targets: Mapping[int, torch.Tensor],
    train_targets: Mapping[int, torch.Tensor],
    shuffle_seed: int,
    shuffle_count: int,
) -> dict[str, Any]:
    full = refit.evaluate_predictions(
        predictions=predictions,
        eval_targets=eval_targets,
        train_targets=train_targets,
        shuffle_seed=shuffle_seed,
        shuffle_count=shuffle_count,
    )
    result: dict[str, Any] = {}
    for tooth in microtrain.APPROVED_TEETH:
        row = full["per_tooth"][str(tooth)]
        observed = row["observed"]
        result[str(tooth)] = {
            "mean_cosine": observed["mean_cosine"],
            "median_cosine": observed["median_cosine"],
            "mean_relative_l2": observed["mean_relative_l2"],
            "median_relative_l2": observed["median_relative_l2"],
            "minus_constant_mean_cosine": row["observed_minus_constant_mean_cosine"],
        }
    return result


def _partition_matrices(
    captured: Mapping[str, Any], *, partition: str, include_predictions: bool = False
) -> tuple[torch.Tensor, dict[int, torch.Tensor], dict[int, torch.Tensor] | None]:
    if partition not in captured or not isinstance(captured[partition], Mapping):
        raise ValueError(f"captured deltas are missing {partition} partition")
    payload = captured[partition]
    source = _matrix(payload.get("source_deltas"), label=f"{partition}.source_deltas", width=microtrain.SOURCE_WIDTH)
    raw_targets = payload.get("target_deltas")
    if not isinstance(raw_targets, Mapping):
        raise ValueError(f"{partition}.target_deltas must be a mapping")
    targets = {
        tooth: _matrix(raw_targets.get(str(tooth)), label=f"{partition}.target_deltas[{tooth}]", width=microtrain.TARGET_WIDTH)
        for tooth in microtrain.APPROVED_TEETH
    }
    predictions: dict[int, torch.Tensor] | None = None
    if include_predictions:
        raw_predictions = payload.get("predicted_target_deltas")
        if not isinstance(raw_predictions, Mapping):
            raise ValueError(f"{partition}.predicted_target_deltas must be a mapping")
        predictions = {
            tooth: _matrix(
                raw_predictions.get(str(tooth)),
                label=f"{partition}.predicted_target_deltas[{tooth}]",
                width=microtrain.TARGET_WIDTH,
            )
            for tooth in microtrain.APPROVED_TEETH
        }
    return source, targets, predictions


def _validate_payload_shape(payload: Mapping[str, Any], train_source: torch.Tensor, eval_source: torch.Tensor) -> None:
    models = payload.get("models")
    if not isinstance(models, Mapping):
        raise ValueError("artifact models receipt is missing")
    if tuple(models.get("teeth", ())) != tuple(microtrain.APPROVED_TEETH):
        raise ValueError(f"artifact teeth are not exactly {microtrain.APPROVED_TEETH}")
    if models.get("source_width") != microtrain.SOURCE_WIDTH or models.get("target_width") != microtrain.TARGET_WIDTH:
        raise ValueError("artifact source/target widths do not match the approved bridge")
    if train_source.shape[0] != EXPECTED_TRAIN_ROWS or eval_source.shape[0] != EXPECTED_EVAL_ROWS:
        raise ValueError(
            f"diagnostic is pinned to the frozen {EXPECTED_TRAIN_ROWS}/{EXPECTED_EVAL_ROWS} split; "
            f"got {train_source.shape[0]}/{eval_source.shape[0]} rows"
        )


def _verify_embedded_evaluation(
    payload: Mapping[str, Any], original: Mapping[str, Any]
) -> bool | None:
    embedded = payload.get("evaluation")
    if not isinstance(embedded, Mapping) or not isinstance(embedded.get("per_tooth"), Mapping):
        return None
    for tooth in microtrain.APPROVED_TEETH:
        recorded = embedded["per_tooth"].get(str(tooth), {}).get("observed")
        if not isinstance(recorded, Mapping):
            raise ValueError(f"artifact evaluation receipt is missing observed tooth {tooth}")
        for field in ("mean_cosine", "median_cosine", "mean_relative_l2", "median_relative_l2"):
            if abs(float(recorded[field]) - float(original[str(tooth)][field])) > 1e-6:
                raise ValueError(f"saved evaluation metric mismatch for tooth {tooth} field {field}")
    return True


def analyze_payload(
    payload: Mapping[str, Any],
    *,
    artifact_sha256: str,
    diagnostic_runner_sha256: str,
    reproduction_atol: float = DEFAULT_REPRODUCTION_ATOL,
    reproduction_rtol: float = DEFAULT_REPRODUCTION_RTOL,
) -> dict[str, Any]:
    """Analyze a trusted frozen artifact without mutating it or loading host models."""

    if len(artifact_sha256) != 64 or len(diagnostic_runner_sha256) != 64:
        raise ValueError("artifact and diagnostic runner SHA-256 values must be 64 hex characters")
    captured = payload.get("captured_deltas")
    recorded_receipts = payload.get("captured_delta_sha256")
    if not isinstance(captured, Mapping) or not isinstance(recorded_receipts, Mapping):
        raise ValueError("artifact is missing captured deltas or their receipts")
    recomputed_receipts = refit.captured_delta_sha256(captured)
    if recomputed_receipts != recorded_receipts:
        raise ValueError("captured delta receipts do not match the artifact")

    train_source, train_targets, _ = _partition_matrices(captured, partition="train")
    eval_source, eval_targets, saved_eval_predictions = _partition_matrices(
        captured, partition="evaluation", include_predictions=True
    )
    assert saved_eval_predictions is not None
    _validate_payload_shape(payload, train_source, eval_source)

    training = payload.get("training")
    state_dict = payload.get("bridge_state_dict")
    if not isinstance(training, Mapping) or not isinstance(state_dict, Mapping):
        raise ValueError("artifact is missing bridge training receipt or state dict")
    hidden_dim = training.get("hidden_dim")
    if not isinstance(hidden_dim, int) or hidden_dim <= 0:
        raise ValueError("artifact hidden_dim must be a positive integer")

    # This is the small saved bridge only, on CPU.  No Mamba/Gemma model is instantiated.
    bridge = microtrain.ValueNormDeltaBridge(hidden_dim=hidden_dim).cpu().eval()
    bridge.load_state_dict(state_dict, strict=True)
    with torch.no_grad():
        train_predictions = bridge(train_source)
        reproduced_eval_predictions = bridge(eval_source)

    reproduction: dict[str, dict[str, float]] = {}
    for tooth in microtrain.APPROVED_TEETH:
        difference = (reproduced_eval_predictions[tooth] - saved_eval_predictions[tooth]).abs()
        if not torch.allclose(
            reproduced_eval_predictions[tooth],
            saved_eval_predictions[tooth],
            atol=reproduction_atol,
            rtol=reproduction_rtol,
        ):
            raise ValueError(
                f"saved eval prediction for tooth {tooth} is not reproducible within "
                f"atol={reproduction_atol}, rtol={reproduction_rtol}"
            )
        reproduction[str(tooth)] = {
            "max_abs": float(difference.max()),
            "mean_abs": float(difference.mean()),
        }

    evaluation = payload.get("evaluation")
    if not isinstance(evaluation, Mapping) or not isinstance(evaluation.get("shuffle_null"), Mapping):
        raise ValueError("artifact evaluation shuffle-null receipt is missing")
    shuffle = evaluation["shuffle_null"]
    shuffle_seed = shuffle.get("seed")
    shuffle_count = shuffle.get("count")
    if not isinstance(shuffle_seed, int) or not isinstance(shuffle_count, int) or shuffle_count <= 0:
        raise ValueError("artifact shuffle-null seed/count is invalid")

    original_metrics = _compact_evaluation(
        predictions=saved_eval_predictions,
        eval_targets=eval_targets,
        train_targets=train_targets,
        shuffle_seed=shuffle_seed,
        shuffle_count=shuffle_count,
    )
    fits = {
        tooth: {
            "vector_l2": fit_positive_vector_l2_scale(train_predictions[tooth], train_targets[tooth]),
            "affine_norm": fit_affine_norm(train_predictions[tooth], train_targets[tooth]),
        }
        for tooth in microtrain.APPROVED_TEETH
    }
    vector_scaled = {
        tooth: saved_eval_predictions[tooth] * fits[tooth]["vector_l2"]["alpha"]
        for tooth in microtrain.APPROVED_TEETH
    }
    affine_scaled = {
        tooth: apply_affine_norm(saved_eval_predictions[tooth], fits[tooth]["affine_norm"])
        for tooth in microtrain.APPROVED_TEETH
    }
    oracle_scaled = {
        tooth: apply_oracle_target_norm(saved_eval_predictions[tooth], eval_targets[tooth])
        for tooth in microtrain.APPROVED_TEETH
    }

    per_tooth: dict[str, Any] = {}
    for tooth in microtrain.APPROVED_TEETH:
        per_tooth[str(tooth)] = {
            "target_centered_spectrum": {
                "train": centered_spectrum(train_targets[tooth]),
                "eval": centered_spectrum(eval_targets[tooth]),
            },
            "prediction_centered_spectrum": {
                "train": centered_spectrum(train_predictions[tooth]),
                "eval": centered_spectrum(saved_eval_predictions[tooth]),
            },
            "norms": {
                "train_target": norm_stats(train_targets[tooth]),
                "train_prediction": norm_stats(train_predictions[tooth]),
                "eval_target": norm_stats(eval_targets[tooth]),
                "eval_prediction": norm_stats(saved_eval_predictions[tooth]),
                "eval_predicted_to_target_norm_ratio": scalar_stats(
                    _row_norms(saved_eval_predictions[tooth]) / _row_norms(eval_targets[tooth]).clamp_min(1e-12)
                ),
                "eval_predicted_target_norm_pearson": pearson_correlation(
                    _row_norms(saved_eval_predictions[tooth]), _row_norms(eval_targets[tooth])
                ),
            },
            "train_only_fits": fits[tooth],
        }

    provenance = payload.get("provenance")
    split_manifest = payload.get("split_manifest")
    source_runner_sha256 = provenance.get("runner_code_sha256") if isinstance(provenance, Mapping) else None
    split_id = split_manifest.get("split_id") if isinstance(split_manifest, Mapping) else None
    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": {
            "retrospective_only": True,
            "cpu_only": True,
            "host_model_loading": False,
            "new_bridge_training": False,
            "new_activation_capture": False,
            "gpu_use": False,
            "artifact_mutated": False,
            "c1": False,
            "b0": False,
            "nonzero_injection": False,
            "generation": False,
            "qdrant": False,
            "memory": False,
            "replay": False,
            "sleep": False,
        },
        "source_artifact": {
            "sha256": artifact_sha256,
            "split_id": split_id,
            "source_runner_sha256": source_runner_sha256,
            "captured_delta_sha256": recorded_receipts,
        },
        "diagnostic_runner": {
            "sha256": diagnostic_runner_sha256,
            "python_version": sys.version,
            "torch_version": torch.__version__,
            "device": "cpu",
        },
        "integrity": {
            "captured_delta_receipts_verified": True,
            "saved_eval_reproduction": reproduction,
            "reproduction_atol": reproduction_atol,
            "reproduction_rtol": reproduction_rtol,
            "embedded_evaluation_metrics_verified": _verify_embedded_evaluation(payload, original_metrics),
        },
        "calibration_boundary": {
            "fit_rows": EXPECTED_TRAIN_ROWS,
            "eval_rows": EXPECTED_EVAL_ROWS,
            "vector_l2_scale": "One positive least-squares scalar per tooth, fit only on train predicted/target vectors.",
            "affine_norm": "One OLS predicted-norm-to-target-norm affine map per tooth, fit only on train rows; eval desired norms are clamped nonnegative.",
            "oracle_norm": "Uses eval target norms solely to decompose direction versus magnitude error; non-deployable and not a held-out method.",
        },
        "analysis": {
            "source_centered_spectrum": centered_spectrum(train_source),
            "per_tooth": per_tooth,
            "evaluation_metrics": {
                "original": original_metrics,
                "train_vector_l2_scale": _compact_evaluation(
                    predictions=vector_scaled,
                    eval_targets=eval_targets,
                    train_targets=train_targets,
                    shuffle_seed=shuffle_seed,
                    shuffle_count=shuffle_count,
                ),
                "train_affine_predicted_norm": _compact_evaluation(
                    predictions=affine_scaled,
                    eval_targets=eval_targets,
                    train_targets=train_targets,
                    shuffle_seed=shuffle_seed,
                    shuffle_count=shuffle_count,
                ),
                "oracle_eval_target_norm": _compact_evaluation(
                    predictions=oracle_scaled,
                    eval_targets=eval_targets,
                    train_targets=train_targets,
                    shuffle_seed=shuffle_seed,
                    shuffle_count=shuffle_count,
                ),
            },
        },
        "interpretation_boundary": [
            "This is a retrospective diagnosis of the existing 24/8 bridge result, not a new bridge fit or pristine-corpus generalization test.",
            "Train-only calibration scores use frozen held-out labels only for final evaluation; the oracle norm row is explicitly non-deployable.",
            "Activation-space metrics establish no behavior, welfare, consciousness, identity, recovery, C1 readiness, or authorization for nonzero steering.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True, help="Frozen bridge .pt artifact to inspect read-only")
    parser.add_argument("--out", type=Path, required=True, help="New diagnostic JSON path; must not already exist")
    parser.add_argument("--reproduction-atol", type=float, default=DEFAULT_REPRODUCTION_ATOL)
    parser.add_argument("--reproduction-rtol", type=float, default=DEFAULT_REPRODUCTION_RTOL)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.reproduction_atol < 0 or args.reproduction_rtol < 0:
        raise SystemExit("reproduction tolerances must be non-negative")
    artifact = Path(args.artifact)
    out = Path(args.out)
    if not artifact.is_file():
        raise SystemExit(f"artifact is missing: {artifact}")
    if out.exists():
        raise FileExistsError(f"refusing to overwrite diagnostic artifact: {out}")

    # This trusted local artifact was produced by the bounded runner; map to CPU before inspection.
    payload = torch.load(artifact, map_location="cpu", weights_only=False)
    report = analyze_payload(
        payload,
        artifact_sha256=_file_sha256(artifact),
        diagnostic_runner_sha256=_file_sha256(Path(__file__)),
        reproduction_atol=args.reproduction_atol,
        reproduction_rtol=args.reproduction_rtol,
    )
    output_sha256 = write_json_no_overwrite(report, out)
    print(
        json.dumps(
            {
                "status": "pass",
                "artifact": str(artifact),
                "artifact_sha256": report["source_artifact"]["sha256"],
                "diagnostic": str(out),
                "diagnostic_sha256": output_sha256,
                "split_id": report["source_artifact"]["split_id"],
                "scope": report["scope"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
