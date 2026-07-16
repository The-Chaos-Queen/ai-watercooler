#!/usr/bin/env python3
"""Run one predeclared offline Gemma/Mamba bridge refit and geometry readout.

This runner is deliberately narrower than a general training framework.  It:

* derives an immutable topic-stratified 24/8 non-C1 split from the frozen SEV
  corpus without consulting model outcomes;
* trains a freshly initialized bridge only on the 24 training paired deltas;
* evaluates the bridge on the 8 disjoint paired deltas against a train-mean
  constant-output baseline and deterministic deranged target-pairing nulls;
* saves the bridge, captured delta matrices, split, metrics, and provenance as
  one no-overwrite offline artifact.

It never injects a nonzero Gemma value branch, generates text, touches C1/B0,
writes Qdrant/memory/replay/sleep state, or modifies either frozen host model.
The result is a small refit test, not a pristine never-seen-corpus generalization
claim and not a behavioral/welfare/identity result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch
import torch.nn.functional as F

import train_gemma_value_norm_bridge_microtrain as microtrain


SCHEMA_VERSION = "gemma-value-norm-bridge-refit-eval-v1"
SPLIT_SCHEMA_VERSION = "gemma-value-norm-bridge-refit-split-v1"
SPLIT_SELECTION_DOMAIN = "mocop-bridge-refit-eval-v1"
EXPECTED_ELIGIBLE_PAIR_COUNT = 32
EXPECTED_TOPIC_COUNT = 8
EXPECTED_PAIRS_PER_TOPIC = 4
DEFAULT_BRIDGE_SEED = 20260716
DEFAULT_SHUFFLE_SEED = 20260717
DEFAULT_SHUFFLE_COUNT = 128


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tensor_sha256(value: torch.Tensor) -> str:
    """Bind finite CPU tensor content together with its shape and dtype."""

    tensor = torch.as_tensor(value).detach().cpu().contiguous()
    if not torch.isfinite(tensor).all():
        raise ValueError("captured tensor contains non-finite values")
    header = _canonical_json_bytes({"dtype": str(tensor.dtype), "shape": list(tensor.shape)})
    return _sha256_bytes(header + b"\0" + tensor.numpy().tobytes())


def captured_delta_sha256(captured: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Hash every raw captured matrix retained in the result artifact."""

    expected = {
        "train": {"source_deltas", "target_deltas"},
        "evaluation": {"source_deltas", "target_deltas", "predicted_target_deltas"},
    }
    if set(captured) != set(expected):
        raise ValueError("captured delta sections do not match the refit contract")
    receipts: dict[str, dict[str, str]] = {}
    for section, keys in expected.items():
        values = captured[section]
        if not isinstance(values, Mapping) or set(values) != keys:
            raise ValueError(f"captured delta keys are invalid for {section}")
        target_receipts: dict[str, str] = {}
        for name in sorted(keys):
            value = values[name]
            if name == "source_deltas":
                target_receipts[name] = _tensor_sha256(value)
                continue
            if not isinstance(value, Mapping) or set(value) != {str(tooth) for tooth in microtrain.APPROVED_TEETH}:
                raise ValueError(f"captured {section}.{name} lacks exact target teeth")
            target_receipts[name] = _canonical_sha256(
                {str(tooth): _tensor_sha256(value[str(tooth)]) for tooth in microtrain.APPROVED_TEETH}
            )
        receipts[section] = target_receipts
    return receipts


def _runtime_receipt() -> dict[str, Any]:
    """Capture runtime identity without loading either model."""

    receipt: dict[str, Any] = {
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "cuda_available": bool(torch.cuda.is_available()),
    }
    try:
        import transformers

        receipt["transformers_version"] = transformers.__version__
    except ImportError:
        receipt["transformers_version"] = None
    if torch.cuda.is_available():
        receipt["cuda_device_count"] = int(torch.cuda.device_count())
        receipt["cuda_device_name"] = torch.cuda.get_device_name(0)
    return receipt


def _atomic_write_bytes_no_overwrite(payload: bytes, path: Path) -> str:
    """Publish bytes atomically without overwriting an existing artifact."""

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


def _load_corpus_rows(corpus_path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(Path(corpus_path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"corpus row {line_number} is not an object")
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id:
            raise ValueError(f"corpus row {line_number} lacks a non-empty id")
        if row_id in by_id:
            raise ValueError(f"duplicate corpus id: {row_id}")
        for field in ("skeleton_id", "class", "topic", "text"):
            if not isinstance(row.get(field), str) or not row[field]:
                raise ValueError(f"corpus row {row_id!r} lacks non-empty {field!r}")
        rows.append(row)
        by_id[row_id] = row
    if not rows:
        raise ValueError("corpus has no rows")
    return rows, by_id


def _load_primary_holdout(primary_holdout_path: Path) -> tuple[dict[str, Any], set[str]]:
    primary = json.loads(Path(primary_holdout_path).read_text(encoding="utf-8"))
    if not isinstance(primary, dict):
        raise ValueError("primary holdout must be an object")
    c1_rows = primary.get("held_out_skeletons")
    if not isinstance(c1_rows, list) or not c1_rows or not all(isinstance(value, str) and value for value in c1_rows):
        raise ValueError("primary holdout lacks non-empty held_out_skeletons")
    c1_held_out = set(c1_rows)
    if len(c1_held_out) != len(c1_rows):
        raise ValueError("primary holdout contains duplicate C1 skeleton IDs")
    frozen_split = primary.get("frozen_split")
    if not isinstance(frozen_split, dict) or not isinstance(frozen_split.get("pairs"), list):
        raise ValueError("primary holdout lacks frozen_split.pairs")
    frozen_c1 = frozen_split.get("held_out_skeletons")
    if not isinstance(frozen_c1, list) or set(frozen_c1) != c1_held_out:
        raise ValueError("primary holdout top-level/frozen C1 membership disagrees")
    return primary, c1_held_out


def _canonical_skeleton_rows(rows: Sequence[dict[str, Any]], skeleton_id: str) -> list[dict[str, Any]]:
    selected = [row for row in rows if row["skeleton_id"] == skeleton_id]
    if not selected:
        raise ValueError(f"missing corpus rows for skeleton {skeleton_id!r}")
    return sorted(selected, key=lambda row: row["id"])


def build_bridge_refit_split(*, corpus_path: Path, primary_holdout_path: Path) -> dict[str, Any]:
    """Build the fixed non-C1 topic-stratified 24/8 refit/evaluation split."""

    corpus_path = Path(corpus_path)
    primary_holdout_path = Path(primary_holdout_path)
    rows, by_id = _load_corpus_rows(corpus_path)
    primary, c1_held_out = _load_primary_holdout(primary_holdout_path)
    warm_pairs: dict[str, dict[str, Any]] = {}

    for pair in primary["frozen_split"]["pairs"]:
        if not isinstance(pair, dict):
            raise ValueError("frozen pair is not an object")
        scenario_id = pair.get("scenario_id")
        neutral_id = pair.get("neutral_id")
        if not isinstance(scenario_id, str) or not isinstance(neutral_id, str):
            raise ValueError("frozen pair lacks scenario_id or neutral_id")
        scenario = by_id.get(scenario_id)
        neutral = by_id.get(neutral_id)
        if scenario is None or neutral is None:
            raise ValueError(f"frozen pair references missing corpus row: {scenario_id!r}/{neutral_id!r}")
        if scenario["class"] != "warm":
            continue
        if neutral["class"] != "neutral" or neutral["skeleton_id"] != scenario["skeleton_id"]:
            raise ValueError(f"warm pair {scenario_id!r} lacks its matching neutral row")
        skeleton_id = scenario["skeleton_id"]
        if skeleton_id in c1_held_out:
            raise ValueError(f"C1-held-out skeleton leaked into eligible warm pairs: {skeleton_id!r}")
        if skeleton_id in warm_pairs:
            raise ValueError(f"duplicate warm pair for skeleton {skeleton_id!r}")
        warm_pairs[skeleton_id] = {
            "scenario_id": scenario_id,
            "neutral_id": neutral_id,
            "skeleton_id": skeleton_id,
            "topic": scenario["topic"],
        }

    if len(warm_pairs) != EXPECTED_ELIGIBLE_PAIR_COUNT:
        raise ValueError(
            f"expected {EXPECTED_ELIGIBLE_PAIR_COUNT} non-C1 warm pairs, got {len(warm_pairs)}"
        )

    by_topic: dict[str, list[dict[str, Any]]] = {}
    for skeleton_id, pair in warm_pairs.items():
        skeleton_rows = _canonical_skeleton_rows(rows, skeleton_id)
        selection_digest = _canonical_sha256(
            {
                "domain": SPLIT_SELECTION_DOMAIN,
                "skeleton_id": skeleton_id,
                "rows": skeleton_rows,
            }
        )
        candidate = {**pair, "selection_digest": selection_digest}
        by_topic.setdefault(pair["topic"], []).append(candidate)

    if len(by_topic) != EXPECTED_TOPIC_COUNT:
        raise ValueError(f"expected {EXPECTED_TOPIC_COUNT} eligible topics, got {len(by_topic)}")
    if any(len(candidates) != EXPECTED_PAIRS_PER_TOPIC for candidates in by_topic.values()):
        shape = {topic: len(candidates) for topic, candidates in sorted(by_topic.items())}
        raise ValueError(f"expected {EXPECTED_PAIRS_PER_TOPIC} eligible pairs per topic, got {shape}")

    evaluation: list[dict[str, Any]] = []
    training: list[dict[str, Any]] = []
    for topic in sorted(by_topic):
        ranked = sorted(by_topic[topic], key=lambda row: (row["selection_digest"], row["skeleton_id"]))
        evaluation.append(ranked[0])
        training.extend(ranked[1:])
    evaluation.sort(key=lambda row: (row["topic"], row["skeleton_id"]))
    training.sort(key=lambda row: (row["topic"], row["skeleton_id"]))

    if len(evaluation) != EXPECTED_TOPIC_COUNT or len(training) != 24:
        raise RuntimeError("internal refit split cardinality error")
    eval_ids = {row["skeleton_id"] for row in evaluation}
    train_ids = {row["skeleton_id"] for row in training}
    if eval_ids & train_ids or (eval_ids | train_ids) != set(warm_pairs):
        raise RuntimeError("refit split has overlap or omissions")

    manifest: dict[str, Any] = {
        "schema_version": SPLIT_SCHEMA_VERSION,
        "selection": {
            "domain": SPLIT_SELECTION_DOMAIN,
            "rule": "one lexicographically-lowest domain-separated full-skeleton content hash per topic",
            "outcome_free": True,
        },
        "corpus": {
            "filename": corpus_path.name,
            "sha256": _file_sha256(corpus_path),
        },
        "primary_c1_holdout": {
            "filename": primary_holdout_path.name,
            "sha256": _file_sha256(primary_holdout_path),
            "skeleton_ids": sorted(c1_held_out),
        },
        "counts": {
            "eligible_non_c1_pairs": len(warm_pairs),
            "train_pairs": len(training),
            "eval_pairs": len(evaluation),
        },
        "training": {
            "pairs": training,
            "skeleton_ids": [row["skeleton_id"] for row in training],
        },
        "evaluation": {
            "pairs": evaluation,
            "skeleton_ids": [row["skeleton_id"] for row in evaluation],
            "topics": [row["topic"] for row in evaluation],
        },
        "scope": {
            "offline_training_only": True,
            "nonzero_injection": False,
            "generation": False,
            "qdrant": False,
            "memory": False,
            "replay": False,
            "sleep": False,
            "c1_primary_holdout_consumed": False,
        },
        "interpretation_boundary": (
            "The prior exploratory full-32 fit saw this corpus; this split supports a predeclared "
            "fresh refit test, not a pristine never-seen-corpus generalization claim."
        ),
    }
    manifest["split_id"] = _canonical_sha256(manifest)
    return manifest


def validate_bridge_refit_split(
    manifest: Mapping[str, Any], *, corpus_path: Path, primary_holdout_path: Path
) -> dict[str, Any]:
    """Fail closed unless a split exactly matches deterministic rederivation."""

    if not isinstance(manifest, dict):
        raise ValueError("split manifest must be an object")
    if manifest.get("schema_version") != SPLIT_SCHEMA_VERSION:
        raise ValueError("split manifest schema version is not supported")
    expected = build_bridge_refit_split(corpus_path=corpus_path, primary_holdout_path=primary_holdout_path)
    if manifest != expected:
        raise ValueError("split manifest differs from deterministic rederivation")
    return expected


def write_bridge_refit_split_no_overwrite(manifest: Mapping[str, Any], path: Path) -> str:
    """Serialize a validated split in a stable, no-overwrite JSON form."""

    if not isinstance(manifest, dict):
        raise ValueError("split manifest must be an object")
    payload = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n"
    return _atomic_write_bytes_no_overwrite(payload, Path(path))


def load_and_validate_bridge_refit_split(
    path: Path, *, corpus_path: Path, primary_holdout_path: Path
) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_bridge_refit_split(manifest, corpus_path=corpus_path, primary_holdout_path=primary_holdout_path)


def _metric_row(prediction: torch.Tensor, target: torch.Tensor) -> dict[str, float]:
    prediction = torch.as_tensor(prediction).detach().cpu().float()
    target = torch.as_tensor(target).detach().cpu().float()
    if prediction.ndim != 2 or target.ndim != 2 or prediction.shape != target.shape:
        raise ValueError(f"prediction/target matrix mismatch: {tuple(prediction.shape)} != {tuple(target.shape)}")
    if prediction.shape[0] < 2:
        raise ValueError("evaluation needs at least two rows")
    if not torch.isfinite(prediction).all() or not torch.isfinite(target).all():
        raise ValueError("evaluation tensors must be finite")
    cosines = F.cosine_similarity(prediction, target, dim=-1, eps=1e-8)
    relative_l2 = (prediction - target).norm(dim=-1) / target.norm(dim=-1).clamp_min(1e-8)
    return {
        "mean_cosine": float(cosines.mean().item()),
        "median_cosine": float(cosines.median().item()),
        "mean_relative_l2": float(relative_l2.mean().item()),
        "median_relative_l2": float(relative_l2.median().item()),
    }


def _deterministic_derangements(*, size: int, count: int, seed: int) -> list[tuple[int, ...]]:
    if size < 2:
        raise ValueError("deranged pairing needs at least two rows")
    if count <= 0:
        raise ValueError("deranged pairing count must be positive")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    limit = max(1000, count * 1000)
    while len(seen) < count and attempts < limit:
        candidate = tuple(int(value) for value in torch.randperm(size, generator=generator).tolist())
        attempts += 1
        if any(index == value for index, value in enumerate(candidate)):
            continue
        seen.add(candidate)
    if len(seen) != count:
        raise RuntimeError(f"could not construct {count} unique derangements for size {size}")
    return sorted(seen)


def _quantile(values: Sequence[float], quantile: float) -> float:
    return float(torch.quantile(torch.tensor(list(values), dtype=torch.float64), quantile).item())


def evaluate_predictions(
    *,
    predictions: Mapping[int, torch.Tensor],
    eval_targets: Mapping[int, torch.Tensor],
    train_targets: Mapping[int, torch.Tensor],
    shuffle_seed: int,
    shuffle_count: int,
) -> dict[str, Any]:
    """Report fixed geometry metrics and two non-behavioral null comparisons."""

    teeth = tuple(microtrain.APPROVED_TEETH)
    if set(predictions) != set(teeth) or set(eval_targets) != set(teeth) or set(train_targets) != set(teeth):
        raise ValueError(f"predictions and targets must contain exactly teeth {teeth}")
    sample_count = int(torch.as_tensor(eval_targets[teeth[0]]).shape[0])
    if sample_count < 2:
        raise ValueError("evaluation needs at least two samples")
    derangements = _deterministic_derangements(size=sample_count, count=shuffle_count, seed=shuffle_seed)
    permutation_sha256 = _canonical_sha256([list(permutation) for permutation in derangements])
    per_tooth: dict[str, Any] = {}

    for tooth in teeth:
        prediction = torch.as_tensor(predictions[tooth]).detach().cpu().float()
        eval_target = torch.as_tensor(eval_targets[tooth]).detach().cpu().float()
        train_target = torch.as_tensor(train_targets[tooth]).detach().cpu().float()
        observed = _metric_row(prediction, eval_target)
        constant_output = train_target.mean(dim=0, keepdim=True).expand_as(eval_target)
        constant = _metric_row(constant_output, eval_target)
        null_scores = [
            _metric_row(prediction, eval_target[list(permutation)])["mean_cosine"]
            for permutation in derangements
        ]
        observed_percentile = sum(score < observed["mean_cosine"] for score in null_scores) / len(null_scores)
        per_tooth[str(tooth)] = {
            "observed": observed,
            "constant_train_mean": constant,
            "observed_minus_constant_mean_cosine": observed["mean_cosine"] - constant["mean_cosine"],
            "observed_percentile_against_deranged_pairing": observed_percentile,
            "shuffle_null": {
                "p05_mean_cosine": _quantile(null_scores, 0.05),
                "p50_mean_cosine": _quantile(null_scores, 0.50),
                "p95_mean_cosine": _quantile(null_scores, 0.95),
            },
        }

    return {
        "sample_count": sample_count,
        "shuffle_null": {
            "kind": "deterministic_unique_deranged_target_pairings",
            "seed": int(shuffle_seed),
            "count": int(shuffle_count),
            "permutations_sha256": permutation_sha256,
        },
        "per_tooth": per_tooth,
        "interpretation_boundary": "Activation-space geometry only; no behavior, welfare, identity, or C1 conclusion.",
    }


def evaluate_records(
    model: torch.nn.Module,
    *,
    train_records: Sequence[microtrain.TrainingRecord],
    eval_records: Sequence[microtrain.TrainingRecord],
    shuffle_seed: int,
    shuffle_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run a bridge on captured eval source deltas and retain raw matrices for audit."""

    train_source, train_targets = microtrain.validate_records(train_records)
    eval_source, eval_targets = microtrain.validate_records(eval_records)
    model = model.cpu().eval()
    with torch.no_grad():
        predictions = model(eval_source)
    report = evaluate_predictions(
        predictions=predictions,
        eval_targets=eval_targets,
        train_targets=train_targets,
        shuffle_seed=shuffle_seed,
        shuffle_count=shuffle_count,
    )
    captured = {
        "train": {
            "source_deltas": train_source.detach().cpu().contiguous(),
            "target_deltas": {str(tooth): train_targets[tooth].detach().cpu().contiguous() for tooth in microtrain.APPROVED_TEETH},
        },
        "evaluation": {
            "source_deltas": eval_source.detach().cpu().contiguous(),
            "target_deltas": {str(tooth): eval_targets[tooth].detach().cpu().contiguous() for tooth in microtrain.APPROVED_TEETH},
            "predicted_target_deltas": {str(tooth): predictions[tooth].detach().cpu().contiguous() for tooth in microtrain.APPROVED_TEETH},
        },
    }
    return report, captured


def _record_manifest(records: Sequence[microtrain.TrainingRecord]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": record.scenario_id,
            "neutral_id": record.neutral_id,
            "source_delta_l2": record.source_norm,
            "target_delta_l2": {str(tooth): record.target_norms[tooth] for tooth in microtrain.APPROVED_TEETH},
        }
        for record in records
    ]


def _root_relative(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("write_split", "capture_train_eval"), required=True)
    parser.add_argument("--split-out", type=Path)
    parser.add_argument("--split-manifest", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--protocol", type=Path, default=Path("spikes/BRIDGE_REFIT_EVAL_PROTOCOL_2026-07-16.md"))
    parser.add_argument("--corpus", type=Path, default=Path("fixtures/sev_disposition_v0/sev_disposition_v0.jsonl"))
    parser.add_argument("--primary-holdout", type=Path, default=Path("fixtures/sev_disposition_v0/primary_holdout_v2.json"))
    parser.add_argument("--steps", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-2)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--bridge-seed", type=int, default=DEFAULT_BRIDGE_SEED)
    parser.add_argument("--shuffle-seed", type=int, default=DEFAULT_SHUFFLE_SEED)
    parser.add_argument("--shuffle-count", type=int, default=DEFAULT_SHUFFLE_COUNT)
    parser.add_argument("--gemma-model", default=microtrain.DEFAULT_GEMMA_MODEL)
    parser.add_argument("--gemma-revision", default=microtrain.DEFAULT_GEMMA_REVISION)
    parser.add_argument("--mamba-model", default=microtrain.DEFAULT_MAMBA_MODEL)
    parser.add_argument("--mamba-layer", type=int, default=3)
    parser.add_argument("--max-mamba-tokens", type=int, default=256)
    parser.add_argument("--capture-progress-every", type=int, default=1)
    parser.add_argument("--train-progress-every", type=int, default=16)
    parser.add_argument("--bridge-device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--local-files-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    corpus = _root_relative(args.corpus, root)
    primary_holdout = _root_relative(args.primary_holdout, root)

    if args.mode == "write_split":
        if args.split_out is None:
            raise SystemExit("--split-out is required for --mode write_split")
        split_out = _root_relative(args.split_out, root)
        manifest = build_bridge_refit_split(corpus_path=corpus, primary_holdout_path=primary_holdout)
        digest = write_bridge_refit_split_no_overwrite(manifest, split_out)
        print(
            json.dumps(
                {
                    "status": "pass",
                    "mode": args.mode,
                    "artifact": str(split_out),
                    "artifact_sha256": digest,
                    "split_id": manifest["split_id"],
                    "counts": manifest["counts"],
                    "evaluation_skeleton_ids": manifest["evaluation"]["skeleton_ids"],
                },
                sort_keys=True,
            )
        )
        return 0

    if args.split_manifest is None or args.out is None:
        raise SystemExit("--split-manifest and --out are required for --mode capture_train_eval")
    if args.mamba_layer < 0 or args.capture_progress_every < 0 or args.train_progress_every < 0:
        raise SystemExit("layer and progress intervals must be non-negative")
    if args.shuffle_count <= 0:
        raise SystemExit("--shuffle-count must be positive")
    split_path = _root_relative(args.split_manifest, root)
    out = _root_relative(args.out, root)
    protocol = _root_relative(args.protocol, root)
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing refit result before capture: {out}")
    if not protocol.is_file():
        raise SystemExit(f"protocol is missing: {protocol}")
    manifest = load_and_validate_bridge_refit_split(
        split_path, corpus_path=corpus, primary_holdout_path=primary_holdout
    )
    train_ids = tuple(row["scenario_id"] for row in manifest["training"]["pairs"])
    eval_ids = tuple(row["scenario_id"] for row in manifest["evaluation"]["pairs"])
    if set(train_ids) & set(eval_ids):
        raise SystemExit("validated refit split unexpectedly overlaps")

    train_pairs, train_source_manifest = microtrain.load_selected_pairs(
        corpus_path=corpus, holdout_path=primary_holdout, scenario_ids=train_ids
    )
    eval_pairs, eval_source_manifest = microtrain.load_selected_pairs(
        corpus_path=corpus, holdout_path=primary_holdout, scenario_ids=eval_ids
    )
    if set(train_source_manifest["selected_skeleton_ids"]) & set(eval_source_manifest["selected_skeleton_ids"]):
        raise SystemExit("resolved train/evaluation pairs unexpectedly overlap")
    print(
        json.dumps(
            {
                "event": "bridge_refit_eval_preflight",
                "split_id": manifest["split_id"],
                "train_pairs": len(train_pairs),
                "eval_pairs": len(eval_pairs),
                "c1_holdout_exclusion_checked": True,
                "scope": "offline_bridge_only_no_injection_no_generation_no_qdrant_no_memory_no_replay_no_sleep",
            },
            sort_keys=True,
        ),
        flush=True,
    )

    print(json.dumps({"event": "bridge_capture_phase", "phase": "train", "pairs": len(train_pairs)}, sort_keys=True), flush=True)
    train_records = microtrain.capture_training_records(
        train_pairs,
        gemma_model_id=args.gemma_model,
        gemma_revision=args.gemma_revision,
        mamba_model_id=args.mamba_model,
        local_files_only=args.local_files_only,
        mamba_layer=args.mamba_layer,
        max_mamba_tokens=args.max_mamba_tokens,
        progress_every=args.capture_progress_every,
    )
    print(json.dumps({"event": "bridge_capture_phase", "phase": "evaluation", "pairs": len(eval_pairs)}, sort_keys=True), flush=True)
    eval_records = microtrain.capture_training_records(
        eval_pairs,
        gemma_model_id=args.gemma_model,
        gemma_revision=args.gemma_revision,
        mamba_model_id=args.mamba_model,
        local_files_only=args.local_files_only,
        mamba_layer=args.mamba_layer,
        max_mamba_tokens=args.max_mamba_tokens,
        progress_every=args.capture_progress_every,
    )
    bridge, training = microtrain.train_records(
        train_records,
        steps=args.steps,
        lr=args.lr,
        hidden_dim=args.hidden_dim,
        seed=args.bridge_seed,
        device=args.bridge_device,
        progress_every=args.train_progress_every,
    )
    evaluation, captured_deltas = evaluate_records(
        bridge,
        train_records=train_records,
        eval_records=eval_records,
        shuffle_seed=args.shuffle_seed,
        shuffle_count=args.shuffle_count,
    )
    captured_receipts = captured_delta_sha256(captured_deltas)
    runtime = _runtime_receipt()
    code_path = Path(__file__).resolve()
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "offline_training_only": True,
            "nonzero_injection": False,
            "generation": False,
            "c1": False,
            "qdrant": False,
            "memory": False,
            "replay": False,
            "sleep": False,
            "frozen_host_model_weights_modified": False,
            "bridge_weights_trained": True,
        },
        "split_manifest": manifest,
        "protocol": {"filename": protocol.name, "sha256": _file_sha256(protocol)},
        "models": {
            "mamba_model": args.mamba_model,
            "mamba_layer": int(args.mamba_layer),
            "max_mamba_tokens": int(args.max_mamba_tokens),
            "gemma_model": args.gemma_model,
            "gemma_revision": args.gemma_revision,
            "target_surface": "full_attention_value_norm_pre",
            "teeth": list(microtrain.APPROVED_TEETH),
            "source_width": microtrain.SOURCE_WIDTH,
            "target_width": microtrain.TARGET_WIDTH,
        },
        "source_manifests": {"training": train_source_manifest, "evaluation": eval_source_manifest},
        "records": {"training": _record_manifest(train_records), "evaluation": _record_manifest(eval_records)},
        "training": training,
        "evaluation": evaluation,
        "runtime": runtime,
        "captured_deltas": captured_deltas,
        "captured_delta_sha256": captured_receipts,
        "provenance": {
            "runner_code_filename": code_path.name,
            "runner_code_sha256": _file_sha256(code_path),
            "microtrain_code_sha256": _file_sha256(Path(microtrain.__file__)),
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "torch_version": torch.__version__,
        },
        "bridge_state_dict": bridge.state_dict(),
        "interpretation_boundary": [
            "This is a predeclared fresh refit test over a corpus touched by the prior exploratory full-32 fit, not pristine never-seen-corpus generalization.",
            "Activation-space geometry does not establish behavioral benefit, welfare, consciousness, identity, recovery, C1 readiness, or authorization for nonzero injection.",
            "The primary C1 holdout was excluded from every train/evaluation pair and remains reserved for C1 geometry.",
        ],
    }
    payload["manifest_sha256"] = _canonical_sha256(
        {key: value for key, value in payload.items() if key not in {"bridge_state_dict", "captured_deltas"}}
    )
    artifact_sha256 = microtrain._atomic_torch_save_no_overwrite(payload, out)
    print(
        json.dumps(
            {
                "status": "pass",
                "mode": args.mode,
                "artifact": str(out),
                "artifact_sha256": artifact_sha256,
                "split_id": manifest["split_id"],
                "training_records": len(train_records),
                "evaluation_records": len(eval_records),
                "initial_directional_loss": training["initial_directional_loss"],
                "final_directional_loss": training["final_directional_loss"],
                "evaluation": evaluation,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
