from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from common import load_config, request_json


def stale_items(report: Dict[str, Any], *, min_age_days: float) -> List[Dict[str, Any]]:
    items = report.get("blocked", {}).get("items", [])
    return [
        item
        for item in items
        if item.get("recommended_review") and float(item.get("blocked_age_days") or 0.0) >= min_age_days
    ]


def format_report_body(report: Dict[str, Any], items: List[Dict[str, Any]], *, project: str, max_items: int) -> str:
    blocked = report.get("blocked", {})
    lines = [
        f"OpenCLAW liveness report for {project or 'all projects'}: "
        f"blocked={blocked.get('count', 0)}, "
        f"median_age={blocked.get('median_age_days', 0)}d, "
        f"p95_age={blocked.get('p95_age_days', 0)}d, "
        f"oldest={blocked.get('oldest_age_days', 0)}d.",
    ]
    if not items:
        lines.append("No blocked cards currently meet the watchdog review threshold.")
        return "\n".join(lines)
    lines.append("Review recommended:")
    for item in items[:max_items]:
        signals = ",".join(item.get("signals", [])) or "none"
        lines.append(
            f"- #{item.get('id')} age={item.get('blocked_age_days')}d "
            f"last={item.get('last_event_age_days')}d signals={signals}: {item.get('title')}"
        )
        reason = str(item.get("blocked_reason") or "").strip()
        if reason:
            lines.append(f"  blocked={reason}")
    if len(items) > max_items:
        lines.append(f"...and {len(items) - max_items} more. Run `openclaw.py liveness --project {project}` for full detail.")
    lines.append("Diagnostic only: use audited lifecycle commands for any repair; watchdog does not mutate tasks.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report-only OpenCLAW blocked-card liveness watchdog.")
    parser.add_argument("--config", type=str, default="", help="Session/service config path.")
    parser.add_argument("--project", type=str, default="MoCoP")
    parser.add_argument("--thread", type=str, default="mamba-bridge")
    parser.add_argument("--min-age-days", type=float, default=7.0)
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true", help="Print the message instead of posting it.")
    parser.add_argument("--always-post", action="store_true", help="Post even when no cards meet the threshold.")
    parser.add_argument("--json", action="store_true", help="Print raw liveness JSON and do not post.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    report = request_json(
        config,
        method="GET",
        path="/v1/tasks/liveness",
        query={"project": args.project},
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    items = stale_items(report, min_age_days=args.min_age_days)
    body = format_report_body(report, items, project=args.project, max_items=max(1, args.max_items))
    if args.dry_run or (not items and not args.always_post):
        print(body)
        return 0

    result = request_json(
        config,
        method="POST",
        path="/v1/post",
        payload={
            "to_agent": "all",
            "thread": args.thread,
            "topic": "OpenCLAW liveness watchdog",
            "lang": "en",
            "body": body,
            "tags": ["openclaw", "board-hygiene", "liveness"],
        },
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
