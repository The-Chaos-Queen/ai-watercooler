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
        phase1_decay, phase1b_expiration_and_relevance,
        phase2_replay, phase3_classify, phase5_flush,
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
    entries = phase1_decay(
        entries,
        decay_factor=args.decay_factor,
        tension_decay=args.tension_decay,
        tension_floor_drain=args.tension_floor_drain,
        tension_resolve_threshold=args.tension_resolve_threshold,
    )

    # Phase 1b: Expiration/relevance gate. Keep wrapper and direct
    # sleep_reconcile.py runs on the same canonical reconciliation path.
    entries = phase1b_expiration_and_relevance(
        entries,
        rules=None,  # Placeholder for Phase 1c rules load, matching sleep_reconcile.py.
    )

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
        tension_budget_ratio=args.tension_budget_ratio,
    )

    # --- Sleep N-loop support (BASELINE CONTROL / Paper 2605.26099 style offline recurrence) ---
    # NOTE: This loops the SCORING only, against a frozen bootstrap_state.
    # Use run_shadow_sleep_nloop_a3.py for real recurrent state advancement.
    if args.sleep_loops > 1:
        if not args.dry_run and not args.allow_multi_pass:
            print("[ERROR] --sleep-loops > 1 requires either --dry-run or --allow-multi-pass (safety guard)")
            sys.exit(2)

        print(f"\n[loop] Starting multi-pass sleep experiment: N={args.sleep_loops}")
        for loop_num in range(2, args.sleep_loops + 1):
            prev_state = {
                e.get("id", i): {
                    "_coherence": e.get("_coherence"),
                    "_open_tension": e.get("_open_tension"),
                    "_tension": e.get("_tension"),
                    "decision": e.get("metadata", {}).get("decision"),
                }
                for i, e in enumerate(entries)
            }

            entries = phase2_replay(
                entries, bootstrap_state,
                top_k=args.top_k, replay_stack=replay_stack,
                tension_budget_ratio=args.tension_budget_ratio,
            )

            # Compute simple deltas (especially on tension items)
            tension_deltas = []
            for i, e in enumerate(entries):
                if e.get("_open_tension"):
                    prev = prev_state.get(e.get("id", i), {})
                    delta = (e.get("_coherence", 0) or 0) - (prev.get("_coherence", 0) or 0)
                    if abs(delta) > 0.01:
                        tension_deltas.append((e.get("content", "")[:50], delta))

            print(f"[loop] Pass {loop_num}/{args.sleep_loops} complete. "
                  f"Tension items with coherence shift >0.01: {len(tension_deltas)}")
            if tension_deltas:
                for content, d in tension_deltas[:5]:
                    print(f"    tension-delta: {d:+.3f} | {content}...")

    # Phase 3: Classify
    entries = phase3_classify(
        entries,
        strength_threshold=args.strength_threshold,
        coherence_threshold=args.coherence_threshold,
        escalation_cycles=args.escalation_cycles,
        escalation_tension_floor=args.escalation_tension_floor,
    )

    # =====================================================
    # PHASE 4: Ethics Post-Check (BEFORE Flush)
    # =====================================================
    print(f"\n{'='*60}")
    print("PHASE 4: Ethics Post-Check")
    print(f"{'='*60}")

    # Calculate metrics for the ethics gate before any writes
    from sleep_reconcile import calculate_sleep_metrics
    recon_metrics = calculate_sleep_metrics(entries)
    
    # Collect entries that would be written for diversity measurement
    written_entries_hypothetical = [e for e in entries if e.get("_status") in (KEEP, UNCERTAIN)]
    
    # We pass a minimal snapshot to post_sleep; it primarily needs classification counts
    # and entries_processed. Real flush will produce a more detailed one later.
    temp_snapshot = {
        "classification": recon_metrics["classification"],
        "entries_processed": len(entries),
        "escalated_count": sum(1 for e in entries if e.get("metadata", {}).get("escalated_to_partner", False)),
        "mean_tension": float(np.mean([e.get("_tension", 0.0) or 0.0 for e in entries]) if entries else 0.0),
    }

    post_verdict = gate.post_sleep(
        pre_verdict, temp_snapshot,
        post_entries=written_entries_hypothetical,
        new_disposition=bootstrap_state,
    )

    if post_verdict.verdict == "STOP":
        print(f"\n[STOP] Ethics gate STOP. Rolling back pre-flush.")
        rollback_path = snapshot_dir / pre_verdict.snapshot_version
        if rollback_path.exists() and not args.dry_run:
            shutil.copy2(str(rollback_path), str(snapshot_path))
            print(f"[STOP] Restored pre-sleep snapshot from {pre_verdict.snapshot_version}")
        elif args.dry_run:
            print(f"[STOP] [dry-run] Would restore {pre_verdict.snapshot_version}")
        
        rubric_line = format_rubric_line(
            len(entries), recon_metrics["classification"], "FAIL", 
            f"ethics=STOP diversity={post_verdict.diversity_ratio:.0%}"
        )
        print(f"\n{rubric_line}")
        return 1

    # =====================================================
    # PHASE 5: Flush
    # =====================================================
    print(f"\n{'='*60}")
    print("PHASE 5: Flush")
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
    # VERDICT
    # =====================================================
    print(f"\n{'='*60}")
    print("VERDICT")
    print(f"{'='*60}")

    classification = recon_snapshot.get("classification", {})
    replay_mode = "same_space" if recon_snapshot.get("same_space_replay_count", 0) > 0 else "metadata"
    failed = recon_snapshot.get("entries_failed", 0)

    # Rotate pending log on success
    if failed == 0:
        if not args.dry_run and not args.no_rotate:
            rotate_log(pending_path)

    if failed > 0:
        rubric_verdict = "FAIL"
        rubric_note = f"{failed} qdrant write failures"
        print(f"[FAIL] {failed} Qdrant write failures. Pending log NOT rotated.")
    elif post_verdict.verdict == "WARN":
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
        "sleep_loops": args.sleep_loops,
        "multi_pass_used": args.sleep_loops > 1,
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
    parser.add_argument("--tension-decay", type=float, default=0.85,
                        help="Per-cycle tension retention factor (§3.7.1 anti-PTSD)")
    parser.add_argument("--tension-floor-drain", type=float, default=0.02,
                        help="Absolute tension reduction per cycle (ensures eventual resolution)")
    parser.add_argument("--tension-resolve-threshold", type=float, default=0.1,
                        help="Tension below this auto-resolves open_tension status")
    parser.add_argument("--escalation-cycles", type=int, default=5,
                        help="Sleep cycles before unresolved tension escalates to partner")
    parser.add_argument("--escalation-tension-floor", type=float, default=0.3,
                        help="Minimum tension to trigger escalation")
    parser.add_argument("--tension-budget-ratio", type=float, default=0.30,
                        help="Max fraction of replay slots for open_tension memories")
    parser.add_argument("--strength-threshold", type=float, default=0.3)
    parser.add_argument("--coherence-threshold", type=float, default=0.12)
    parser.add_argument("--top-k", type=int, default=20)

    # Sleep N-loop experiment support (inspired by 2605.26099)
    parser.add_argument("--sleep-loops", type=int, default=1,
                        help="Number of times to run phase2_replay (N>1 for offline recurrence experiments)")
    parser.add_argument("--allow-multi-pass", action="store_true",
                        help="Allow --sleep-loops > 1. MUST be combined with --dry-run for safety during early experiments.")

    # Safety
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-qdrant", action="store_true")
    parser.add_argument("--no-rotate", action="store_true")

    args = parser.parse_args()
    sys.exit(run_cycle(args))


if __name__ == "__main__":
    main()
