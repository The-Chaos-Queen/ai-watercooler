#!/usr/bin/env python3
"""
gate_policy_replay.py

Offline comparison harness for dual-gate policy variants.

Purpose:
- load gate-event JSONL artifacts from MoCoP runs
- normalize both raw `dual_gate_turns_latest.jsonl` rows and reconciled
  `qdrant_gate_pending*.jsonl` rows
- replay alternative write / keep policies without touching the live server

This is intended for G1 of the GDN/GKA side ladder:
"borrow the gate before swapping the source."
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


Decision = str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay MoCoP dual-gate policy variants on saved JSONL logs.")
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="Input file, directory, or glob. Repeatable.",
    )
    parser.add_argument(
        "--policy",
        choices=[
            "all",
            "current",
            "strict_write",
            "tension_aware",
            "latent_supported",
            "supported_tension_attend",
        ],
        default="all",
        help="Which policy to evaluate. Default: all.",
    )
    parser.add_argument(
        "--coherence-quantile",
        type=float,
        default=0.75,
        help="Quantile used by latent_supported policy. Default: 0.75.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--tension-salience-support-ratio",
        type=float,
        default=0.55,
        help="Minimum salience/threshold ratio for supported_tension_attend. Default: 0.55.",
    )
    return parser.parse_args()


def expand_inputs(inputs: List[str]) -> List[Path]:
    files: List[Path] = []
    for raw in inputs:
        matches = [Path(p) for p in glob.glob(raw, recursive=True)]
        if matches:
            for path in matches:
                if path.is_dir():
                    files.extend(sorted(path.rglob("*.jsonl")))
                elif path.suffix.lower() == ".jsonl":
                    files.append(path)
            continue

        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.jsonl")))
        elif path.exists() and path.suffix.lower() == ".jsonl":
            files.append(path)

    deduped: List[Path] = []
    seen = set()
    for path in files:
        resolved = str(path.resolve())
        if resolved not in seen:
            deduped.append(path)
            seen.add(resolved)
    return deduped


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{idx}: invalid JSONL row: {exc}") from exc
    return rows


def first_present(mapping: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


def normalize_row(row: Dict[str, Any], path: Path) -> Optional[Dict[str, Any]]:
    # Raw dual_gate_turns_latest.jsonl row
    if "surprise" in row and "salience" in row and "decision" in row:
        salience_threshold = first_present(row.get("salience", {}), "threshold")
        surprise_threshold = first_present(row.get("surprise", {}), "threshold")
        tension_threshold = first_present(row.get("tension", {}), "threshold")
        return {
            "source_file": str(path),
            "row_kind": "dual_gate_event",
            "turn": row.get("turn"),
            "decision": row.get("decision", "DISMISS"),
            "gate_mode": row.get("mode", ""),
            "salience_hit": bool(row.get("salience", {}).get("hit")),
            "surprise_hit": bool(row.get("surprise", {}).get("hit")),
            "tension_hit": bool(row.get("tension", {}).get("hit")),
            "open_tension": bool(row.get("destinations", {}).get("open_tension", False))
            or str(row.get("tension", {}).get("status", "")).upper() == "OPEN",
            "writes_mamba": bool(row.get("destinations", {}).get("mamba")),
            "writes_qdrant": bool(row.get("destinations", {}).get("qdrant")),
            "qdrant_override": bool(row.get("routing", {}).get("qdrant_override")),
            "safety_critical": bool(row.get("safety_critical", {}).get("is_critical")),
            "salience_score": float(row.get("salience", {}).get("score", 0.0) or 0.0),
            "surprise_score": float(row.get("surprise", {}).get("mean_token_nll", 0.0) or 0.0),
            "tension_score": float(row.get("tension", {}).get("score", 0.0) or 0.0),
            "coherence_score": float(row.get("mamba_trace", {}).get("coherence_score", 0.0) or 0.0),
            "salience_threshold": float(salience_threshold or 0.0),
            "surprise_threshold": float(surprise_threshold or 0.0),
            "tension_threshold": float(tension_threshold or 0.0),
            "salience_weight": float(row.get("salience", {}).get("weight", 0.0) or 0.0),
        }

    # Reconciled qdrant pending row
    if "metadata" in row and isinstance(row["metadata"], dict):
        meta = row["metadata"]
        gate_thresholds = meta.get("gate_thresholds", {}) or {}
        salience_threshold = first_present(gate_thresholds.get("salience", {}) or {}, "threshold")
        surprise_threshold = first_present(gate_thresholds.get("surprise", {}) or {}, "threshold")
        tension_threshold = first_present(gate_thresholds.get("tension", {}) or {}, "threshold")
        salience_score = float(meta.get("salience_score", 0.0) or 0.0)
        salience_weight = (
            salience_score / float(salience_threshold)
            if salience_threshold not in {None, 0, 0.0, ""}
            else 0.0
        )
        return {
            "source_file": str(path),
            "row_kind": "qdrant_pending_row",
            "turn": meta.get("turn"),
            "decision": meta.get("decision", "DISMISS"),
            "gate_mode": meta.get("gate_mode", ""),
            "salience_hit": bool(meta.get("salience_hit")),
            "surprise_hit": bool(meta.get("surprise_hit")),
            "tension_hit": bool(meta.get("tension_hit")),
            "open_tension": bool(meta.get("open_tension")),
            "writes_mamba": bool(meta.get("gate_destinations", {}).get("mamba")),
            "writes_qdrant": bool(meta.get("gate_destinations", {}).get("qdrant")),
            "qdrant_override": bool(meta.get("gate_routing", {}).get("qdrant_override")),
            "safety_critical": bool(meta.get("safety_critical")),
            "salience_score": salience_score,
            "surprise_score": float(meta.get("surprise_score", 0.0) or 0.0),
            "tension_score": float(meta.get("tension_score", 0.0) or 0.0),
            "coherence_score": float(meta.get("coherence_score", 0.0) or 0.0),
            "salience_threshold": float(salience_threshold or 0.0),
            "surprise_threshold": float(surprise_threshold or 0.0),
            "tension_threshold": float(tension_threshold or 0.0),
            "salience_weight": float(salience_weight or 0.0),
        }

    return None


def compute_quantile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return min(values)
    if q >= 1:
        return max(values)
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    weight = pos - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def current_policy(event: Dict[str, Any], coherence_threshold: float) -> Dict[str, Any]:
    salience_hit = event["salience_hit"]
    surprise_hit = event["surprise_hit"]
    tension_hit = event["tension_hit"]
    qdrant_override = event["qdrant_override"] or event["safety_critical"]

    if salience_hit and surprise_hit:
        decision = "CONSOLIDATE"
    elif salience_hit:
        decision = "ATTEND"
    elif surprise_hit:
        decision = "NOTE"
    else:
        decision = "DISMISS"

    return {
        "decision": decision,
        "writes_mamba": decision in {"CONSOLIDATE", "ATTEND"},
        "writes_qdrant": decision in {"CONSOLIDATE", "NOTE"} or qdrant_override,
        "open_tension": tension_hit,
    }


def strict_write_policy(event: Dict[str, Any], coherence_threshold: float) -> Dict[str, Any]:
    result = current_policy(event, coherence_threshold)
    qdrant_override = event["qdrant_override"] or event["safety_critical"]
    result["writes_qdrant"] = result["decision"] == "CONSOLIDATE" or qdrant_override
    return result


def tension_aware_policy(event: Dict[str, Any], coherence_threshold: float) -> Dict[str, Any]:
    salience_hit = event["salience_hit"]
    surprise_hit = event["surprise_hit"]
    tension_hit = event["tension_hit"]
    qdrant_override = event["qdrant_override"] or event["safety_critical"]

    if salience_hit and surprise_hit:
        decision = "CONSOLIDATE"
    elif salience_hit or tension_hit:
        decision = "ATTEND"
    elif surprise_hit:
        decision = "NOTE"
    else:
        decision = "DISMISS"

    return {
        "decision": decision,
        "writes_mamba": decision in {"CONSOLIDATE", "ATTEND"},
        "writes_qdrant": decision in {"CONSOLIDATE", "NOTE"} or qdrant_override,
        "open_tension": tension_hit,
    }


def latent_supported_policy(event: Dict[str, Any], coherence_threshold: float) -> Dict[str, Any]:
    base = current_policy(event, coherence_threshold)
    coherence_ok = event["coherence_score"] >= coherence_threshold
    qdrant_override = event["qdrant_override"] or event["safety_critical"]

    if qdrant_override:
        base["writes_qdrant"] = True
        return base

    if not coherence_ok:
        return {
            "decision": "DISMISS",
            "writes_mamba": False,
            "writes_qdrant": False,
            "open_tension": event["tension_hit"],
        }

    base["writes_qdrant"] = base["writes_qdrant"] and coherence_ok
    return base


def supported_tension_attend_policy(event: Dict[str, Any], coherence_threshold: float) -> Dict[str, Any]:
    base = current_policy(event, coherence_threshold)
    baseline_decision = base["decision"]
    qdrant_override = event["qdrant_override"] or event["safety_critical"]
    salience_support_ratio = float(event.get("salience_weight", 0.0) or 0.0)

    if (
        baseline_decision == "DISMISS"
        and event["tension_hit"]
        and salience_support_ratio >= ARGS.tension_salience_support_ratio
    ):
        return {
            "decision": "ATTEND",
            "writes_mamba": True,
            "writes_qdrant": qdrant_override,
            "open_tension": True,
        }

    return base


POLICIES = {
    "current": current_policy,
    "strict_write": strict_write_policy,
    "tension_aware": tension_aware_policy,
    "latent_supported": latent_supported_policy,
    "supported_tension_attend": supported_tension_attend_policy,
}


def summarize_policy(
    name: str,
    events: List[Dict[str, Any]],
    coherence_threshold: float,
) -> Dict[str, Any]:
    decision_counter: Counter[str] = Counter()
    writes_mamba = 0
    writes_qdrant = 0
    open_tension = 0

    fn = POLICIES[name]
    for event in events:
        result = fn(event, coherence_threshold)
        decision_counter[result["decision"]] += 1
        writes_mamba += int(result["writes_mamba"])
        writes_qdrant += int(result["writes_qdrant"])
        open_tension += int(result["open_tension"])

    return {
        "policy": name,
        "decision_counts": dict(decision_counter),
        "writes_mamba": writes_mamba,
        "writes_qdrant": writes_qdrant,
        "open_tension": open_tension,
    }


def summarize_original(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    decision_counter: Counter[str] = Counter(event["decision"] for event in events)
    gate_modes: Counter[str] = Counter(event["gate_mode"] for event in events)
    return {
        "events": len(events),
        "row_kinds": dict(Counter(event["row_kind"] for event in events)),
        "gate_modes": dict(gate_modes),
        "decision_counts": dict(decision_counter),
        "writes_mamba": sum(int(event["writes_mamba"]) for event in events),
        "writes_qdrant": sum(int(event["writes_qdrant"]) for event in events),
        "open_tension": sum(int(event["open_tension"]) for event in events),
        "coherence_mean": round(
            sum(event["coherence_score"] for event in events) / len(events), 6
        )
        if events
        else 0.0,
    }


def print_summary(summary: Dict[str, Any]) -> None:
    print(f"\nOriginal events: {summary['original']['events']}")
    print(f"Row kinds: {summary['original']['row_kinds']}")
    print(f"Gate modes: {summary['original']['gate_modes']}")
    print(f"Original decisions: {summary['original']['decision_counts']}")
    print(
        "Original writes:"
        f" mamba={summary['original']['writes_mamba']}"
        f" qdrant={summary['original']['writes_qdrant']}"
        f" open_tension={summary['original']['open_tension']}"
    )
    print(
        f"Coherence threshold for latent_supported (q={summary['coherence_quantile']}): "
        f"{summary['coherence_threshold']:.6f}"
    )
    for policy in summary["policies"]:
        print(f"\nPolicy: {policy['policy']}")
        print(f"  decisions: {policy['decision_counts']}")
        print(
            f"  writes: mamba={policy['writes_mamba']} "
            f"qdrant={policy['writes_qdrant']} "
            f"open_tension={policy['open_tension']}"
        )


def main() -> None:
    global ARGS
    args = parse_args()
    ARGS = args
    files = expand_inputs(args.input)
    if not files:
        raise SystemExit("No JSONL inputs found.")

    events: List[Dict[str, Any]] = []
    for path in files:
        for row in load_jsonl(path):
            normalized = normalize_row(row, path)
            if normalized is not None:
                events.append(normalized)

    if not events:
        raise SystemExit("No recognizable gate-event rows found in the provided inputs.")

    coherence_values = [event["coherence_score"] for event in events]
    coherence_threshold = compute_quantile(coherence_values, args.coherence_quantile)

    selected_policies = list(POLICIES.keys()) if args.policy == "all" else [args.policy]
    summary = {
        "input_files": [str(path) for path in files],
        "coherence_quantile": args.coherence_quantile,
        "coherence_threshold": round(coherence_threshold, 6),
        "original": summarize_original(events),
        "policies": [
            summarize_policy(name, events, coherence_threshold) for name in selected_policies
        ],
    }

    print_summary(summary)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
