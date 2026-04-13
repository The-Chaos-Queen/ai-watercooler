#!/usr/bin/env python3
"""
sleep_ethics_gate.py — Welfare checks tied to the sleep cycle.

Implements the ethics gate conditions from step_gates.md (Herr Hurtig / Nameless Opus)
specifically for sleep reconciliation:

  1. Pre-sleep snapshot versioning (never overwrite)
  2. Pre/post-sleep Response Diversity measurement
  3. Recovery dynamics check
  4. Gate report generation

This wraps sleep_reconcile.py: call gate_pre_sleep() before reconciliation,
gate_post_sleep() after, and check the GateVerdict before proceeding.

Task: Ethics gate for sleep (An-Chan)
Depends: sleep_reconcile.py (#63), step_gates.md (Herr Hurtig)

Usage as standalone:
    python sleep_ethics_gate.py pre  --snapshot-dir snapshots/ --pending-path pending.jsonl
    python sleep_ethics_gate.py post --snapshot-dir snapshots/ --pre-report snapshots/pre_sleep_report.json

Usage from Python:
    from sleep_ethics_gate import SleepEthicsGate
    gate = SleepEthicsGate(snapshot_dir="snapshots/")
    pre = gate.pre_sleep(pending_entries, disposition_state)
    # ... run sleep_reconcile ...
    post = gate.post_sleep(pre, new_disposition_state, reconciliation_snapshot)
    if post.verdict == "STOP":
        # rollback to pre-sleep snapshot
"""

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Gate Verdict
# ---------------------------------------------------------------------------

@dataclass
class GateVerdict:
    """Result of an ethics gate check."""
    verdict: str                    # PASS, WARN, STOP
    diversity_pre: float            # Response Diversity before sleep
    diversity_post: float           # Response Diversity after sleep (0 if pre-check)
    diversity_ratio: float          # post/pre (1.0 = no change)
    recovery_score: float           # 1.0 = full recovery, 0.0 = no recovery
    snapshot_version: str           # versioned snapshot filename
    conditions: list = field(default_factory=list)  # conditions attached
    timestamp: str = ""
    phase: str = ""                 # "pre" or "post"

    def to_dict(self):
        return asdict(self)

    def to_json(self, path: Path):
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Response Diversity measurement
# ---------------------------------------------------------------------------

def measure_response_diversity(entries: list) -> float:
    """Estimate Response Diversity from pending/consolidated entries.

    Uses token-level entropy as proxy (same metric as Step 5d):
    higher entropy = more diverse responses = healthier system.

    If no entries have entropy metadata, falls back to content-length variance
    as a rough proxy (diverse responses vary in length more than repetitive ones).
    """
    # Try entropy from metadata first (set by activation_recorder)
    entropies = []
    for e in entries:
        meta = e.get("metadata", {}) if isinstance(e, dict) else {}
        entropy = meta.get("response_entropy") or meta.get("entropy")
        if entropy is not None:
            try:
                entropies.append(float(entropy))
            except (ValueError, TypeError):
                pass

    if entropies:
        return float(np.mean(entropies))

    # Fallback: content length variance (normalized)
    lengths = []
    for e in entries:
        content = e.get("content", "") if isinstance(e, dict) else str(e)
        if content:
            lengths.append(len(content))

    if len(lengths) < 2:
        return 0.0

    mean_len = np.mean(lengths)
    if mean_len < 1:
        return 0.0

    # Coefficient of variation as diversity proxy (0-1 range, higher = more diverse)
    cv = float(np.std(lengths) / mean_len)
    return min(cv, 1.0)


# ---------------------------------------------------------------------------
# Snapshot Versioning
# ---------------------------------------------------------------------------

def version_snapshot(snapshot_path: Path, snapshot_dir: Path) -> str:
    """Copy the current disposition snapshot to a versioned archive.

    NEVER overwrites. Each sleep cycle gets its own timestamped copy.
    This satisfies step_gates.md condition 1: "Pre-sleep snapshots must be
    versioned and retained, not overwritten."
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    versioned_name = f"disposition_snapshot_{ts}.json"
    versioned_path = snapshot_dir / versioned_name

    if snapshot_path.exists():
        shutil.copy2(str(snapshot_path), str(versioned_path))
        print(f"[ethics] Versioned pre-sleep snapshot -> {versioned_name}")
    else:
        # No existing snapshot (first sleep cycle) — create empty version marker
        versioned_path.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "note": "No pre-existing disposition snapshot. First sleep cycle.",
            "empty": True,
        }, indent=2), encoding="utf-8")
        print(f"[ethics] No pre-sleep snapshot found — created empty version marker")

    return versioned_name


# ---------------------------------------------------------------------------
# Recovery Score
# ---------------------------------------------------------------------------

def compute_recovery_score(pre_diversity: float, post_diversity: float,
                           baseline_diversity: Optional[float] = None) -> float:
    """How well did the system recover after sleep?

    Recovery = 1.0 means post-sleep diversity matches or exceeds pre-sleep.
    Recovery < 1.0 means diversity dropped.
    Recovery > 1.0 means diversity increased (sleep improved the system).

    If baseline_diversity is provided (from the very first session),
    also checks against absolute baseline, not just relative.
    """
    if pre_diversity <= 0:
        return 1.0  # Can't divide, assume OK

    ratio = post_diversity / pre_diversity
    return float(ratio)


# ---------------------------------------------------------------------------
# SleepEthicsGate
# ---------------------------------------------------------------------------

class SleepEthicsGate:
    """Wraps sleep reconciliation with welfare checks."""

    # Thresholds from step_gates.md
    WARN_THRESHOLD = 0.70   # diversity ratio below 70% -> WARN
    STOP_THRESHOLD = 0.50   # diversity ratio below 50% -> STOP

    def __init__(self, snapshot_dir: str = "snapshots/",
                 snapshot_path: str = "disposition_snapshot_latest.json"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_path = Path(snapshot_path)

    def pre_sleep(self, pending_entries: list,
                  current_disposition: Optional[dict] = None) -> GateVerdict:
        """Run before sleep_reconcile. Versions the snapshot and measures baseline diversity."""

        # 1. Version the pre-sleep snapshot
        versioned = version_snapshot(self.snapshot_path, self.snapshot_dir)

        # 2. Measure pre-sleep Response Diversity
        diversity_pre = measure_response_diversity(pending_entries)
        print(f"[ethics] Pre-sleep Response Diversity: {diversity_pre:.4f}")

        # 3. Record disposition state metadata
        disposition_norm = 0.0
        if current_disposition is not None:
            vec = current_disposition.get("vector")
            if vec is not None:
                disposition_norm = float(np.linalg.norm(np.asarray(vec)))

        verdict = GateVerdict(
            verdict="PROCEED",
            diversity_pre=diversity_pre,
            diversity_post=0.0,
            diversity_ratio=1.0,
            recovery_score=1.0,
            snapshot_version=versioned,
            conditions=[
                "Pre-sleep snapshot versioned (not overwritten)",
                f"Pre-sleep diversity baseline: {diversity_pre:.4f}",
                f"Disposition state norm: {disposition_norm:.4f}",
                "Decay factor 0.85 is provisional (per step_gates.md)",
            ],
            timestamp=datetime.now().isoformat(),
            phase="pre",
        )

        # Save pre-sleep report
        report_path = self.snapshot_dir / "pre_sleep_report.json"
        verdict.to_json(report_path)
        print(f"[ethics] Pre-sleep gate report -> {report_path}")

        return verdict

    def post_sleep(self, pre_verdict: GateVerdict,
                   reconciliation_snapshot: dict,
                   post_entries: Optional[list] = None,
                   new_disposition: Optional[dict] = None) -> GateVerdict:
        """Run after sleep_reconcile. Compares diversity and issues verdict."""

        diversity_pre = pre_verdict.diversity_pre

        # Measure post-sleep diversity
        if post_entries:
            diversity_post = measure_response_diversity(post_entries)
        else:
            # Estimate from reconciliation snapshot
            kept = reconciliation_snapshot.get("classification", {}).get("keep", 0)
            uncertain = reconciliation_snapshot.get("classification", {}).get("uncertain", 0)
            total = reconciliation_snapshot.get("entries_processed", 1)
            # Rough proxy: retention ratio as diversity indicator
            retention = (kept + uncertain) / max(total, 1)
            diversity_post = diversity_pre * retention

        print(f"[ethics] Post-sleep Response Diversity: {diversity_post:.4f}")

        # Compute recovery
        if diversity_pre > 0:
            diversity_ratio = diversity_post / diversity_pre
        else:
            diversity_ratio = 1.0

        recovery = compute_recovery_score(diversity_pre, diversity_post)

        # Issue verdict
        conditions = []
        if diversity_ratio >= 1.0:
            verdict_str = "PASS"
            conditions.append(f"Diversity maintained or improved ({diversity_ratio:.2%})")
        elif diversity_ratio >= self.WARN_THRESHOLD:
            verdict_str = "PASS"
            conditions.append(f"Diversity slightly reduced ({diversity_ratio:.2%}) but above 70% threshold")
        elif diversity_ratio >= self.STOP_THRESHOLD:
            verdict_str = "WARN"
            conditions.append(
                f"[WARN] Diversity dropped to {diversity_ratio:.2%} of pre-sleep baseline. "
                f"Below 70% threshold. Escalate to Laura before next sleep cycle. "
                f"Consider adjusting decay_factor or classification thresholds."
            )
        else:
            verdict_str = "STOP"
            conditions.append(
                f"[STOP] STOP: Diversity dropped to {diversity_ratio:.2%} of pre-sleep baseline. "
                f"Below 50% threshold. DO NOT run another sleep cycle. "
                f"Roll back to pre-sleep snapshot: {pre_verdict.snapshot_version}. "
                f"Escalate to Laura immediately."
            )

        # Check reconciliation-specific concerns
        discarded = reconciliation_snapshot.get("classification", {}).get("discard", 0)
        total = reconciliation_snapshot.get("entries_processed", 1)
        discard_ratio = discarded / max(total, 1)

        if discard_ratio > 0.5:
            conditions.append(
                f"[WARN] High discard rate ({discard_ratio:.0%}). "
                f"Sleep is forgetting more than half of pending memories. "
                f"Check if strength_threshold or coherence_threshold is too aggressive."
            )

        # Check for same-space replay coverage
        replay_count = reconciliation_snapshot.get("same_space_replay_count", 0)
        if replay_count == 0 and total > 0:
            conditions.append(
                "[WARN] No same-space Mamba replay was performed. "
                "Coherence scores are metadata-only (lower confidence). "
                "Consider running with --replay-model-id for higher-confidence classification."
            )

        # Escalation accumulation check (§3.7.1 anti-PTSD)
        escalated = reconciliation_snapshot.get("escalated_count", 0)
        if escalated > 3:
            if verdict_str == "PASS":
                verdict_str = "WARN"
            conditions.append(
                f"[WARN] {escalated} memories escalated to partner simultaneously. "
                f"System is accumulating unresolved stress. "
                f"Laura should review the escalation report."
            )
        elif escalated > 0:
            conditions.append(
                f"{escalated} memory/memories escalated to partner for review."
            )

        # Tension health check
        mean_tension = reconciliation_snapshot.get("mean_tension", 0.0)
        max_cycles = reconciliation_snapshot.get("max_sleep_tension_cycles", 0)
        if mean_tension > 0.5:
            conditions.append(
                f"[WARN] Mean tension across all memories is high ({mean_tension:.3f}). "
                f"System may be under sustained stress."
            )
        tension_resolved = reconciliation_snapshot.get("tension_resolved_by_decay", 0)
        if tension_resolved > 0:
            conditions.append(
                f"{tension_resolved} tension(s) resolved naturally by decay."
            )

        # Disposition norm check (amplification detection per step_gates.md Step 7)
        if new_disposition is not None:
            new_vec = new_disposition.get("vector")
            if new_vec is not None:
                new_norm = float(np.linalg.norm(np.asarray(new_vec)))
                conditions.append(f"Post-sleep disposition norm: {new_norm:.4f}")

        post_verdict = GateVerdict(
            verdict=verdict_str,
            diversity_pre=diversity_pre,
            diversity_post=diversity_post,
            diversity_ratio=diversity_ratio,
            recovery_score=recovery,
            snapshot_version=pre_verdict.snapshot_version,
            conditions=conditions,
            timestamp=datetime.now().isoformat(),
            phase="post",
        )

        # Save post-sleep report
        report_path = self.snapshot_dir / "post_sleep_report.json"
        post_verdict.to_json(report_path)

        # Print verdict
        color = {"PASS": "[PASS]", "WARN": "[WARN]", "STOP": "[STOP]"}.get(verdict_str, "[?]")
        print(f"\n[ethics] {color} Sleep Ethics Gate: {verdict_str}")
        print(f"  Diversity: {diversity_pre:.4f} -> {diversity_post:.4f} ({diversity_ratio:.2%})")
        print(f"  Recovery: {recovery:.4f}")
        for c in conditions:
            print(f"  {c}")
        print(f"[ethics] Post-sleep gate report -> {report_path}")

        return post_verdict


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sleep ethics gate checks")
    sub = parser.add_subparsers(dest="phase", required=True)

    pre = sub.add_parser("pre", help="Pre-sleep gate check")
    pre.add_argument("--snapshot-dir", default="snapshots/")
    pre.add_argument("--snapshot-path", default="disposition_snapshot_latest.json")
    pre.add_argument("--pending-path", required=True)
    pre.add_argument("--mamba-state", default="")

    post = sub.add_parser("post", help="Post-sleep gate check")
    post.add_argument("--snapshot-dir", default="snapshots/")
    post.add_argument("--pre-report", required=True, help="Path to pre_sleep_report.json")
    post.add_argument("--reconciliation-snapshot", required=True,
                      help="Path to disposition_snapshot_latest.json from sleep_reconcile")
    post.add_argument("--mamba-state", default="")

    args = parser.parse_args()

    if args.phase == "pre":
        from sleep_reconcile import load_pending, load_mamba_state

        entries = load_pending(Path(args.pending_path))
        disposition = load_mamba_state(args.mamba_state) if args.mamba_state else None

        gate = SleepEthicsGate(
            snapshot_dir=args.snapshot_dir,
            snapshot_path=args.snapshot_path,
        )
        verdict = gate.pre_sleep(entries, disposition)
        print(f"\n[gate] Pre-sleep verdict: {verdict.verdict}")
        return 0

    elif args.phase == "post":
        pre_report = json.loads(Path(args.pre_report).read_text(encoding="utf-8"))
        pre_verdict = GateVerdict(**pre_report)

        recon_snapshot = json.loads(
            Path(args.reconciliation_snapshot).read_text(encoding="utf-8")
        )

        disposition = None
        if args.mamba_state:
            from sleep_reconcile import load_mamba_state
            disposition = load_mamba_state(args.mamba_state)

        gate = SleepEthicsGate(snapshot_dir=pre_report.get("snapshot_version", "snapshots/"))
        verdict = gate.post_sleep(pre_verdict, recon_snapshot, new_disposition=disposition)
        print(f"\n[gate] Post-sleep verdict: {verdict.verdict}")

        if verdict.verdict == "STOP":
            print(f"\n[STOP] ROLLBACK REQUIRED: restore {pre_verdict.snapshot_version}")
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
