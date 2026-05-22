"""
sleep_threshold_sweep.py - Sweep sleep reconciliation thresholds on one scored batch.

Purpose:
    Load a pending/reconciled JSONL batch, compute same-space replay scores once,
    then sweep Phase 3 strength/coherence thresholds without reloading Mamba for
    every trial.

Usage:
    python sleep_threshold_sweep.py \
        --pending-path qdrant_gate_pending.reconciled_20260325T223714.jsonl \
        --mamba-state mamba_bootstrap_state_latest.pt \
        --replay-device cuda
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from sleep_reconcile import (
    KEEP,
    UNCERTAIN,
    WEAKEN,
    DISCARD,
    load_pending,
    load_mamba_replay_stack,
    load_mamba_state,
    phase1_decay,
    phase2_replay,
    phase3_classify,
)


DEFAULT_STRENGTH_VALUES = [0.12, 0.14, 0.16, 0.18, 0.20, 0.24, 0.30]
DEFAULT_COHERENCE_VALUES = [0.10, 0.12, 0.13, 0.14, 0.15]


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


def entry_label(entry: dict) -> str:
    metadata = entry.get("metadata") or {}
    turn = metadata.get("turn", "?")
    user = str(metadata.get("user", "") or "").strip().replace("\n", " ")
    short_user = user[:48] + ("..." if len(user) > 48 else "")
    return f"turn {turn}: {short_user}"


def build_row_result(entries: list[dict]) -> list[str]:
    result = []
    for entry in entries:
        result.append(f"{entry['_status']}:{entry_label(entry)}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep sleep reconciliation thresholds on one replay-scored batch."
    )
    parser.add_argument("--pending-path", required=True, help="Path to archived pending JSONL batch")
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
        "--strength-values",
        help="Comma-separated strength thresholds to test",
    )
    parser.add_argument(
        "--coherence-values",
        help="Comma-separated coherence thresholds to test",
    )
    parser.add_argument(
        "--decay-factor",
        type=float,
        default=0.85,
        help="Decay factor applied before sweeping",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="How many replay lines phase2_replay should show",
    )
    parser.add_argument(
        "--only-writing",
        action="store_true",
        help="Only print threshold pairs that would write at least one entry",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path to save sweep results as JSON",
    )
    args = parser.parse_args()

    strength_values = parse_float_list(args.strength_values, DEFAULT_STRENGTH_VALUES)
    coherence_values = parse_float_list(args.coherence_values, DEFAULT_COHERENCE_VALUES)

    entries = load_pending(Path(args.pending_path))
    if not entries:
        print("[ok] No entries found.")
        return 0

    bootstrap_state = load_mamba_state(args.mamba_state)
    if bootstrap_state is None:
        raise SystemExit(f"No Mamba state found at {args.mamba_state}")

    replay_stack = load_mamba_replay_stack(args.replay_model_id, args.replay_device)
    scored_entries = phase2_replay(
        phase1_decay(entries, args.decay_factor),
        bootstrap_state,
        top_k=args.top_k,
        replay_stack=replay_stack,
    )

    print("\n[baseline entries]")
    for entry in scored_entries:
        print(
            f"- {entry_label(entry)} | "
            f"strength={entry['_strength']:.3f} "
            f"coherence={abs(entry['_coherence']):.3f} "
            f"tension={float(entry['metadata'].get('tension_score', 0.0) or 0.0):.3f}"
        )

    sweep_results = []
    print("\n[sweep]")
    for strength_threshold in strength_values:
        for coherence_threshold in coherence_values:
            classified = phase3_classify(
                copy.deepcopy(scored_entries),
                strength_threshold=strength_threshold,
                coherence_threshold=coherence_threshold,
            )
            counts = {
                KEEP: sum(1 for entry in classified if entry["_status"] == KEEP),
                UNCERTAIN: sum(1 for entry in classified if entry["_status"] == UNCERTAIN),
                WEAKEN: sum(1 for entry in classified if entry["_status"] == WEAKEN),
                DISCARD: sum(1 for entry in classified if entry["_status"] == DISCARD),
            }
            write_count = counts[KEEP] + counts[UNCERTAIN]
            row = {
                "strength_threshold": strength_threshold,
                "coherence_threshold": coherence_threshold,
                "write_count": write_count,
                "counts": counts,
                "entries": build_row_result(classified),
            }
            sweep_results.append(row)
            if args.only_writing and write_count == 0:
                continue
            print(
                f"strength={strength_threshold:.3f} coherence={coherence_threshold:.3f} "
                f"-> write={write_count} counts={counts} entries={row['entries']}"
            )

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.write_text(json.dumps(sweep_results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[ok] JSON -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
