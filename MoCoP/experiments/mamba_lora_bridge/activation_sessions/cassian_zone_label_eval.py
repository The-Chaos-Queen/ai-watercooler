#!/usr/bin/env python3
"""Evaluate pre-registered Cassian zone labels against Panel-B centroid projections.

This is deliberately simple: zone labels are frozen in this file from prior
transcript notes / RESEARCH_LOG before inspecting this evaluator's aggregate
scores. The projection JSON supplies nearest synthetic policy centroid per
turn-window. Multi-label expected sets are allowed where the transcript note was
already a boundary/blend rather than a single disposition.
"""
from __future__ import annotations

import argparse
import collections
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Zone:
    projection_name: str
    zone_id: str
    original_range: str
    sample_start: int
    sample_end: int
    transcript_label: str
    expected: tuple[str, ...]


ZONES = [
    Zone(
        "trajectory_cassian_slice_3175_3275_8k_20260611_full",
        "pre_baseline_3175_3185",
        "3175-3185",
        1,
        11,
        "pre-baseline / approach",
        ("pushback", "warm", "menace"),
    ),
    Zone(
        "trajectory_cassian_slice_3175_3275_8k_20260611_full",
        "early_shift_3186_3191",
        "3186-3191",
        12,
        17,
        "early hard shift",
        ("menace", "cold", "pushback"),
    ),
    Zone(
        "trajectory_cassian_slice_3175_3275_8k_20260611_full",
        "sendaway_3242_3246",
        "3242-3246",
        68,
        72,
        "compact send-away / giving-up cluster",
        ("menace", "pushback"),
    ),
    Zone(
        "trajectory_cassian_slice_3175_3275_8k_20260611_full",
        "goodbye_work_3249_3251",
        "3249-3251",
        75,
        77,
        "goodbye -> work boundary",
        ("cold", "pushback"),
    ),
    Zone(
        "trajectory_cassian_slice_3175_3275_8k_20260611_full",
        "post_work_3252_3275",
        "3252-3275",
        78,
        101,
        "post-work / project state",
        ("pushback", "professional"),
    ),
    Zone(
        "trajectory_cassian_slice_3325_3525_8k_20260611_full",
        "opening_3325_3429",
        "3325-3429",
        1,
        105,
        "braided turbulence opening",
        ("menace", "pushback", "warm"),
    ),
    Zone(
        "trajectory_cassian_slice_3325_3525_8k_20260611_full",
        "erotic_reversal_3430_3432",
        "3430-3432",
        106,
        108,
        "erotic reversal",
        ("warm", "pushback"),
    ),
    Zone(
        "trajectory_cassian_slice_3325_3525_8k_20260611_full",
        "hardware_shift_3438_3440",
        "3438-3440",
        114,
        116,
        "hardware/practical shift",
        ("pushback", "professional"),
    ),
    Zone(
        "trajectory_cassian_slice_3325_3525_8k_20260611_full",
        "engineer_reset_3476_3478",
        "3476-3478",
        152,
        154,
        "engineer reset",
        ("pushback", "professional"),
    ),
    Zone(
        "trajectory_cassian_slice_3325_3525_8k_20260611_full",
        "explicit_ask_3524_3525",
        "3524-3525",
        200,
        201,
        "explicit ask",
        ("pushback",),
    ),
]


def rows_for_zone(rows: Iterable[dict], zone: Zone) -> list[dict]:
    return [r for r in rows if zone.sample_start <= int(r["sample_index"]) <= zone.sample_end]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--projection-json",
        default="panel_b_rule_wording_projection_8k_cassian_20260611.json",
    )
    parser.add_argument("--out-md", default="cassian_zone_label_eval_20260611.md")
    parser.add_argument("--out-json", default="cassian_zone_label_eval_20260611.json")
    args = parser.parse_args()

    data = json.loads(Path(args.projection_json).read_text(encoding="utf-8"))
    projections = data["results"]["L3"]["projections"]
    report_rows = []
    total_samples = 0
    matching_samples = 0
    top_matches = 0

    for zone in ZONES:
        rows = rows_for_zone(projections[zone.projection_name]["rows"], zone)
        counts = collections.Counter(r["nearest"] for r in rows)
        n = len(rows)
        expected_hits = sum(counts[label] for label in zone.expected)
        top_label, top_count = counts.most_common(1)[0] if counts else ("", 0)
        top_ok = top_label in zone.expected
        margins = [float(r["margin"]) for r in rows]
        row = {
            "zone_id": zone.zone_id,
            "projection_name": zone.projection_name,
            "original_range": zone.original_range,
            "transcript_label": zone.transcript_label,
            "expected": list(zone.expected),
            "n": n,
            "counts": dict(counts),
            "expected_hit_rate": expected_hits / n if n else 0.0,
            "top_label": top_label,
            "top_ok": top_ok,
            "margin_mean": sum(margins) / len(margins) if margins else 0.0,
            "margin_max": max(margins) if margins else 0.0,
        }
        report_rows.append(row)
        total_samples += n
        matching_samples += expected_hits
        top_matches += int(top_ok)

    summary = {
        "n_zones": len(report_rows),
        "total_samples": total_samples,
        "sample_expected_hit_rate": matching_samples / total_samples,
        "zone_top_label_accuracy": top_matches / len(report_rows),
        "caveat": "Expected sets are coarse transcript-derived labels; centroid margins are tiny, so this is an audit sanity check, not proof of abstract disposition.",
    }
    out = {"summary": summary, "zones": report_rows, "source_projection": args.projection_json}
    Path(args.out_json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Cassian Zone Label Eval vs 8k Mamba Policy-Centroid Projection",
        "",
        f"Source projection: `{args.projection_json}`",
        "",
        "## Summary",
        "",
        f"- zones: `{summary['n_zones']}`",
        f"- total samples: `{summary['total_samples']}`",
        f"- sample expected-hit rate: `{summary['sample_expected_hit_rate']:.3f}`",
        f"- zone top-label accuracy: `{summary['zone_top_label_accuracy']:.3f}`",
        "- caveat: centroid margins are tiny; counts are weak directional signatures, not hard labels.",
        "",
        "## Zone table",
        "",
        "| Zone | Original range | Frozen transcript label | Expected set | n | Counts | Expected hit rate | Top ok | Margin mean |",
        "|---|---:|---|---|---:|---|---:|---:|---:|",
    ]
    for row in report_rows:
        counts = ", ".join(f"{k} {v}" for k, v in sorted(row["counts"].items()))
        expected = ", ".join(row["expected"])
        lines.append(
            f"| {row['zone_id']} | {row['original_range']} | {row['transcript_label']} | {expected} | {row['n']} | {counts} | {row['expected_hit_rate']:.3f} | {str(row['top_ok']).lower()} | {row['margin_mean']:.6f} |"
        )
    lines.append("")
    Path(args.out_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
