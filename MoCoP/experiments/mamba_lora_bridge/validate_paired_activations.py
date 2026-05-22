#!/usr/bin/env python3
"""
validate_paired_activations.py - sanity-check paired activation arrays before DFC training.

This is intentionally numpy-only so it can run locally without importing torch.
"""

import argparse
import json
from pathlib import Path
from typing import List

import numpy as np


def load_metadata(path: Path) -> List[dict]:
    if not path or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("metadata", [])


def duplicate_runs(metadata: List[dict], mamba_array: np.ndarray, qwen_array: np.ndarray) -> List[dict]:
    if not metadata:
        return []
    runs = []
    for label in sorted({item["label"] for item in metadata}):
        indices = [idx for idx, item in enumerate(metadata) if item["label"] == label]
        if not indices:
            continue
        start = indices[0]
        prev = indices[0]
        for cur in indices[1:]:
            same_pair = np.array_equal(mamba_array[cur], mamba_array[prev]) and np.array_equal(
                qwen_array[cur], qwen_array[prev]
            )
            if same_pair:
                prev = cur
                continue
            if prev > start:
                runs.append({
                    "label": label,
                    "sample_start": metadata[start].get("sample_num", start + 1),
                    "sample_end": metadata[prev].get("sample_num", prev + 1),
                    "turn_start": metadata[start].get("end_idx"),
                    "turn_end": metadata[prev].get("end_idx"),
                    "length": prev - start + 1,
                })
            start = prev = cur
        if prev > start:
            runs.append({
                "label": label,
                "sample_start": metadata[start].get("sample_num", start + 1),
                "sample_end": metadata[prev].get("sample_num", prev + 1),
                "turn_start": metadata[start].get("end_idx"),
                "turn_end": metadata[prev].get("end_idx"),
                "length": prev - start + 1,
            })
    return runs


def build_report(mamba_array: np.ndarray, qwen_array: np.ndarray, metadata: List[dict], min_unique_ratio: float) -> dict:
    if mamba_array.shape[0] != qwen_array.shape[0]:
        raise ValueError(f"row mismatch: mamba={mamba_array.shape[0]} qwen={qwen_array.shape[0]}")
    n_samples = int(mamba_array.shape[0])
    mamba_unique = int(np.unique(mamba_array, axis=0).shape[0])
    qwen_unique = int(np.unique(qwen_array, axis=0).shape[0])
    labels = sorted({item["label"] for item in metadata}) if metadata else []

    per_label = []
    for label in labels:
        indices = [idx for idx, item in enumerate(metadata) if item["label"] == label]
        per_label.append({
            "label": label,
            "samples": len(indices),
            "mamba_unique": int(np.unique(mamba_array[indices], axis=0).shape[0]),
            "qwen_unique": int(np.unique(qwen_array[indices], axis=0).shape[0]),
        })

    truncated_mamba = sum(1 for item in metadata if item.get("mamba_token_stats", {}).get("truncated"))
    truncated_qwen = sum(1 for item in metadata if item.get("qwen_token_stats", {}).get("truncated"))
    return {
        "n_samples": n_samples,
        "mamba_shape": list(mamba_array.shape),
        "qwen_shape": list(qwen_array.shape),
        "finite": bool(np.isfinite(mamba_array).all() and np.isfinite(qwen_array).all()),
        "min_unique_ratio": min_unique_ratio,
        "passes": (
            np.isfinite(mamba_array).all()
            and np.isfinite(qwen_array).all()
            and (mamba_unique / n_samples >= min_unique_ratio)
            and (qwen_unique / n_samples >= min_unique_ratio)
        ),
        "unique": {
            "mamba": mamba_unique,
            "qwen": qwen_unique,
            "mamba_ratio": mamba_unique / n_samples if n_samples else 0.0,
            "qwen_ratio": qwen_unique / n_samples if n_samples else 0.0,
        },
        "truncation": {
            "mamba_truncated_samples": truncated_mamba,
            "qwen_truncated_samples": truncated_qwen,
        },
        "per_label": per_label,
        "duplicate_runs": duplicate_runs(metadata, mamba_array, qwen_array),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate paired activation arrays before DFC training")
    parser.add_argument("--mamba-data", required=True)
    parser.add_argument("--qwen-data", required=True)
    parser.add_argument("--metadata", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--min-unique-ratio", type=float, default=0.5)
    args = parser.parse_args()

    mamba_array = np.load(args.mamba_data)
    qwen_array = np.load(args.qwen_data)
    metadata = load_metadata(Path(args.metadata)) if args.metadata else []
    report = build_report(mamba_array, qwen_array, metadata, args.min_unique_ratio)

    report_text = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(report_text, encoding="utf-8")
    print(report_text)
    return 0 if report["passes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
