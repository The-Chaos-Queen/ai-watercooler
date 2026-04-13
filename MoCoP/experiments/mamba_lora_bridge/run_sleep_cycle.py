#!/usr/bin/env python3
"""
run_sleep_cycle.py — Complete sleep cycle operator.

Orchestrates: ethics pre-check -> reconciliation -> ethics post-check -> rollback on STOP.
Emits one-line result per sleep_pass_fail_rubric.md format.

NOT for the live Steve hot path. Run manually between sessions or via cron.
Deployment to Steve is Techno-Monk's call.

Usage:
    python run_sleep_cycle.py --pending-path qdrant_gate_pending.jsonl --dry-run
    python run_sleep_cycle.py --pending-path pending.jsonl --skip-qdrant
    python run_sleep_cycle.py --pending-path pending.jsonl --mamba-state mamba_bootstrap_state_latest.pt

OpenCLAW #69
Author: Anda-Conda
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def run_cycle(args):
    pending_path = Path(args.pending_path)
    snapshot_dir = Path(args.snapshot_dir)
    snapshot_path = Path(args.snapshot_path)

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # --- Import components ---
    from sleep_reconcile import (
        load_pending, load_failure_packets, attach_failure_packets, load_mamba_state,
        phase1_decay, phase2_replay, phase3_classify, phase5_flush,
        load_mamba_replay_stack, rotate_log,
        KEEP, UNCERTAIN, WEAKEN, DISCARD,
    )
    from sleep_ethics_gate import SleepEthicsGate

    # --- Load pending entries ---
    entries = load_pending(pending_path)
    if not entries:
        print("[cycle] No pending entries. Nothing to do.")
        print(format_rubric_line(0, {}, "SKIP", "no entries"))
        return 0

    failure_packets = load_failure_packets(Path(args.failure_path))
    entries, failure_attached = attach_failure_packets(entries, failure_packets)
    if failure_packets:
        print(
            f"[cycle] Loaded {len(failure_packets)} failure packets "
            f"({failure_attached} matched to pending entries)"
        )

    print(f"[cycle] Starting sleep cycle: {len(entries)} entries")
    print(f"[cycle] dry_run={args.dry_run}, skip_qdrant={args.skip_qdrant}")

    # --- Load Mamba state ---
    bootstrap_state = load_mamba_state(args.mamba_state)
    if bootstrap_state is not None:
        print(f"[cycle] Mamba state loaded from {args.mamba_state}")
    else:
        print(f"[cycle] No Mamba state — coherence will use metadata fallback")

    # =====================================================
    # PHASE 0: Ethics Pre-Check
    # =====================================================
    print(f"\n{'='*60}")
    print("PHASE 0: Ethics Pre-Check")
    print(f"{'='*60}")

    gate = SleepEthicsGate(
        snapshot_dir=str(snapshot_dir),
        snapshot_path=str(snapshot_path),
    )
    pre_verdict = gate.pre_sleep(entries, bootstrap_state)
    print(f"[cycle] Pre-sleep verdict: {pre_verdict.verdict}")

    # =====================================================
    # PHASES 1-3: Reconciliation
    # =====================================================
    print(f"\n{'='*60}")
    print("PHASES 1-3: Reconciliation")
    print(f"{'='*60}")

    # Phase 1: Decay
    entries = phase1_decay(entries, args.decay_factor)

    # Phase 2: Replay
    replay_stack = None
    if bootstrap_state is not None and not args.skip_replay:
        try:
            replay_stack = load_mamba_replay_stack(args.replay_model_id, args.replay_device)
            print(f"[cycle] Replay model loaded: {args.replay_model_id}")
        except Exception as exc:
            print(f"[cycle] Could not load replay model: {exc}")

    entries = phase2_replay(
        entries, bootstrap_state,
        top_k=args.top_k, replay_stack=replay_stack,
    )

    # Phase 3: Classify
    entries = phase3_classify(
        entries,
        strength_threshold=args.strength_threshold,
        coherence_threshold=args.coherence_threshold,
    )

    # =====================================================
    # PHASE 4: Flush (conditional on ethics)
    # =====================================================
    print(f"\n{'='*60}")
    print("PHASE 4: Flush + Ethics Post-Check")
    print(f"{'='*60}")

    # Build Qdrant sink
    sink_fn = None
    if not args.dry_run and not args.skip_qdrant:
        try:
            from sleep_flush import create_sink
            sink_fn = create_sink(args.host, args.port, args.collection, args.embedding_model)
        except Exception as exc:
            print(f"[cycle] Could not create Qdrant sink: {exc}")

    # Determine snapshot output path
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    cycle_snapshot_path = snapshot_dir / f"disposition_snapshot_cycle_{ts}.json"
    cycle_residue_path = snapshot_dir / f"sleep_residue_cycle_{ts}.jsonl"

    # Run flush
    recon_snapshot = phase5_flush(
        entries, sink_fn, cycle_snapshot_path,
        mamba_state_path=args.mamba_state,
        residue_path=cycle_residue_path,
        dry_run=args.dry_run,
    )

    # =====================================================
    # PHASE 5: Ethics Post-Check
    # =====================================================
    print(f"\n{'='*60}")
    print("PHASE 5: Ethics Post-Check")
    print(f"{'='*60}")

    # Collect written entries for diversity measurement
    written_entries = [e for e in entries if e["_status"] in (KEEP, UNCERTAIN)]
    post_verdict = gate.post_sleep(
        pre_verdict, recon_snapshot,
        post_entries=written_entries,
        new_disposition=bootstrap_state,
    )

    # =====================================================
    # VERDICT + ROLLBACK
    # =====================================================
    print(f"\n{'='*60}")
    print("VERDICT")
    print(f"{'='*60}")

    classification = recon_snapshot.get("classification", {})
    replay_mode = "same_space" if recon_snapshot.get("same_space_replay_count", 0) > 0 else "metadata"
    failed = recon_snapshot.get("entries_failed", 0)

    if post_verdict.verdict == "STOP":
        print(f"\n[STOP] Ethics gate STOP. Rolling back.")
        rollback_path = snapshot_dir / pre_verdict.snapshot_version
        if rollback_path.exists() and not args.dry_run:
            shutil.copy2(str(rollback_path), str(snapshot_path))
            print(f"[STOP] Restored pre-sleep snapshot from {pre_verdict.snapshot_version}")
        elif args.dry_run:
            print(f"[STOP] [dry-run] Would restore {pre_verdict.snapshot_version}")
        else:
            print(f"[STOP] WARNING: rollback snapshot not found at {rollback_path}")

        # Do NOT rotate pending log on STOP — entries need to be reprocessed
        rubric_verdict = "FAIL"
        rubric_note = f"ethics={post_verdict.verdict} diversity={post_verdict.diversity_ratio:.0%}"
    elif failed > 0:
        rubric_verdict = "FAIL"
        rubric_note = f"{failed} qdrant write failures"
        print(f"[FAIL] {failed} Qdrant write failures. Pending log NOT rotated.")
    else:
        # Rotate pending log on success
        if not args.dry_run and not args.no_rotate:
            rotate_log(pending_path)

        if post_verdict.verdict == "WARN":
            rubric_verdict = "WARN"
            rubric_note = f"ethics={post_verdict.verdict} diversity={post_verdict.diversity_ratio:.0%}"
        else:
            rubric_verdict = "PASS"
            rubric_note = ""

    # =====================================================
    # ONE-LINE RUBRIC OUTPUT
    # =====================================================
    rubric_line = format_rubric_line(
        len(entries), classification, rubric_verdict, rubric_note,
        written=recon_snapshot.get("entries_written", 0),
        failed=failed,
        replay=replay_mode,
    )
    print(f"\n{rubric_line}")

    # Save cycle report
    cycle_report = {
        "timestamp": datetime.now().isoformat(),
        "entries_processed": len(entries),
        "failure_packets_loaded": len(failure_packets),
        "failure_packets_attached": failure_attached,
        "classification": classification,
        "entries_written": recon_snapshot.get("entries_written", 0),
        "entries_failed": failed,
        "replay_mode": replay_mode,
        "ethics_pre": pre_verdict.to_dict(),
        "ethics_post": post_verdict.to_dict(),
        "reconciliation": recon_snapshot,
        "rubric_verdict": rubric_verdict,
        "rubric_line": rubric_line,
        "dry_run": args.dry_run,
    }
    report_path = snapshot_dir / f"sleep_cycle_report_{ts}.json"
    if not args.dry_run:
        report_path.write_text(
            json.dumps(cycle_report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"[cycle] Report -> {report_path}")
    else:
        print(f"[cycle] [dry-run] Would save report to {report_path}")

    return 1 if rubric_verdict == "FAIL" else 0


def format_rubric_line(n_entries, classification, verdict, note="",
                       written=0, failed=0, replay="metadata"):
    """One-line rubric format per sleep_pass_fail_rubric.md."""
    date = datetime.now().strftime("%Y-%m-%d")
    k = classification.get("keep", 0)
    u = classification.get("uncertain", 0)
    w = classification.get("weakened", 0)
    d = classification.get("discard", 0)
    line = (
        f"Sleep cycle {date}: {n_entries} entries, "
        f"{k}K/{u}U/{w}W/{d}D, "
        f"{written} written, {failed} failed, "
        f"replay={replay}, {verdict}"
    )
    if note:
        line += f" ({note})"
    return line


def main():
    parser = argparse.ArgumentParser(
        description="Complete sleep cycle: ethics pre-check -> reconcile -> ethics post-check"
    )
    parser.add_argument("--pending-path", required=True)
    parser.add_argument("--failure-path", default="failure_log.jsonl")
    parser.add_argument("--mamba-state", default="mamba_bootstrap_state_latest.pt")
    parser.add_argument("--snapshot-dir", default="snapshots/")
    parser.add_argument("--snapshot-path", default="disposition_snapshot_latest.json")

    # Qdrant
    parser.add_argument("--host", default="192.168.2.191")
    parser.add_argument("--port", type=int, default=6333)
    parser.add_argument("--collection", default="exocortex")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2")

    # Replay
    parser.add_argument("--replay-model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--replay-device", default="auto")
    parser.add_argument("--skip-replay", action="store_true")

    # Thresholds
    parser.add_argument("--decay-factor", type=float, default=0.85)
    parser.add_argument("--strength-threshold", type=float, default=0.3)
    parser.add_argument("--coherence-threshold", type=float, default=0.12)
    parser.add_argument("--top-k", type=int, default=20)

    # Safety
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-qdrant", action="store_true")
    parser.add_argument("--no-rotate", action="store_true")

    args = parser.parse_args()
    sys.exit(run_cycle(args))


if __name__ == "__main__":
    main()
