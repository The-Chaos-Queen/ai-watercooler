#!/usr/bin/env python3
"""
sleep_decay_sweep.py - Sweep sleep decay factors on archived pending batches.

Purpose:
    Calibrate the provisional global decay factor used by sleep_reconcile.py
    against the current fixed classification thresholds and ethics gate logic.

Usage:
    python sleep_decay_sweep.py \
        --pending-path run_reincarnation/batch_a.jsonl \
        --pending-path run_reincarnation/batch_b.jsonl \
        --mamba-state mamba_bootstrap_state_latest.pt \
        --replay-device cuda \
        --json-out run_reincarnation/sleep_decay_sweep.json
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from sleep_ethics_gate import SleepEthicsGate, compute_recovery_score, measure_response_diversity
from sleep_reconcile import (
    DISCARD,
    KEEP,
    UNCERTAIN,
    WEAKEN,
    load_mamba_replay_stack,
    load_mamba_state,
    load_pending,
    phase1_decay,
    phase2_replay,
    phase3_classify,
)


DEFAULT_DECAY_VALUES = [0.70, 0.85, 0.90]


def parse_float_list(raw: str | None, default_values: list[float]) -> list[float]:
    if not raw:
        return list(default_values)
    values = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        values.append(float(text))
    if not values:
        raise ValueError("No numeric values parsed.")
    return values


def classify_ethics_verdict(diversity_ratio: float) -> str:
    if diversity_ratio >= 1.0:
        return "PASS"
    if diversity_ratio >= SleepEthicsGate.WARN_THRESHOLD:
        return "PASS"
    if diversity_ratio >= SleepEthicsGate.STOP_THRESHOLD:
        return "WARN"
    return "STOP"


def count_statuses(entries: list[dict]) -> dict[str, int]:
    return {
        KEEP: sum(1 for entry in entries if entry["_status"] == KEEP),
        UNCERTAIN: sum(1 for entry in entries if entry["_status"] == UNCERTAIN),
        WEAKEN: sum(1 for entry in entries if entry["_status"] == WEAKEN),
        DISCARD: sum(1 for entry in entries if entry["_status"] == DISCARD),
    }


def run_one_batch(
    pending_path: Path,
    decay_values: list[float],
    bootstrap_state: dict,
    replay_stack,
    strength_threshold: float,
    coherence_threshold: float,
    top_k: int,
) -> dict:
    entries = load_pending(pending_path)
    if not entries:
        raise SystemExit(f"No valid entries found in {pending_path}")

    diversity_pre = measure_response_diversity(entries)
    results = []
    for decay_factor in decay_values:
        decayed_entries = phase1_decay(copy.deepcopy(entries), decay_factor=decay_factor)
        scored_entries = phase2_replay(
            decayed_entries,
            bootstrap_state,
            top_k=top_k,
            replay_stack=replay_stack,
        )
        classified_entries = phase3_classify(
            copy.deepcopy(scored_entries),
            strength_threshold=strength_threshold,
            coherence_threshold=coherence_threshold,
        )
        counts = count_statuses(classified_entries)
        written_entries = [
            entry for entry in classified_entries if entry["_status"] in {KEEP, UNCERTAIN}
        ]
        diversity_post = measure_response_diversity(written_entries)
        diversity_ratio = (diversity_post / diversity_pre) if diversity_pre > 0 else 1.0
        same_space_replay_count = sum(
            1
            for entry in classified_entries
            if entry.get("_coherence_source") == "mamba_hidden_last_token_replay"
        )
        results.append(
            {
                "decay_factor": decay_factor,
                "entries_processed": len(classified_entries),
                "counts": counts,
                "entries_written": counts[KEEP] + counts[UNCERTAIN],
                "same_space_replay_count": same_space_replay_count,
                "diversity_pre": diversity_pre,
                "diversity_post": diversity_post,
                "diversity_ratio": diversity_ratio,
                "recovery_score": compute_recovery_score(diversity_pre, diversity_post),
                "ethics_verdict": classify_ethics_verdict(diversity_ratio),
            }
        )

    return {
        "pending_path": str(pending_path),
        "entries_processed": len(entries),
        "strength_threshold": strength_threshold,
        "coherence_threshold": coherence_threshold,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep sleep decay factors on archived batches with same-space replay."
    )
    parser.add_argument(
        "--pending-path",
        action="append",
        required=True,
        help="Archived pending JSONL batch. Repeat for multiple batches.",
    )
    parser.add_argument(
        "--mamba-state",
        default="mamba_bootstrap_state_latest.pt",
        help="Path to persisted bootstrap Mamba hidden-last-token state (.pt)",
    )
    parser.add_argument(
        "--replay-model-id",
        default="state-spaces/mamba-2.8b-hf",
        help="Mamba model used to replay entries into hidden_last_token space",
    )
    parser.add_argument(
        "--replay-device",
        default="auto",
        help="Device for replay model: auto, cpu, cuda, cuda:0, ...",
    )
    parser.add_argument(
        "--decay-values",
        help="Comma-separated decay values to test",
    )
    parser.add_argument(
        "--strength-threshold",
        type=float,
        default=0.30,
        help="Fixed strength threshold for Phase 3 classification",
    )
    parser.add_argument(
        "--coherence-threshold",
        type=float,
        default=0.12,
        help="Fixed coherence threshold for Phase 3 classification",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="How many replay lines phase2_replay should show per batch",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path to save sweep results as JSON",
    )
    args = parser.parse_args()

    decay_values = parse_float_list(args.decay_values, DEFAULT_DECAY_VALUES)
    bootstrap_state = load_mamba_state(args.mamba_state)
    if bootstrap_state is None:
        raise SystemExit(f"No Mamba state found at {args.mamba_state}")

    replay_stack = load_mamba_replay_stack(args.replay_model_id, args.replay_device)
    all_results = []
    print("[decay sweep]")
    for pending_path_str in args.pending_path:
        pending_path = Path(pending_path_str)
        print(f"\n[batch] {pending_path}")
        batch_result = run_one_batch(
            pending_path=pending_path,
            decay_values=decay_values,
            bootstrap_state=bootstrap_state,
            replay_stack=replay_stack,
            strength_threshold=args.strength_threshold,
            coherence_threshold=args.coherence_threshold,
            top_k=args.top_k,
        )
        all_results.append(batch_result)
        for result in batch_result["results"]:
            counts = result["counts"]
            print(
                "decay={decay:.2f} -> verdict={verdict} "
                "write={written} counts={keep}K/{uncertain}U/{weakened}W/{discard}D "
                "diversity={ratio:.2%} recovery={recovery:.3f} replay={replay}".format(
                    decay=result["decay_factor"],
                    verdict=result["ethics_verdict"],
                    written=result["entries_written"],
                    keep=counts[KEEP],
                    uncertain=counts[UNCERTAIN],
                    weakened=counts[WEAKEN],
                    discard=counts[DISCARD],
                    ratio=result["diversity_ratio"],
                    recovery=result["recovery_score"],
                    replay=result["same_space_replay_count"],
                )
            )

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.write_text(
            json.dumps(all_results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\n[ok] JSON -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
