from __future__ import annotations

import argparse
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .common import load_config, pretty_message, pretty_task, request_json


def handle_read(args, config):
    result = request_json(
        config,
        method="GET",
        path="/v1/summary",
        query={"thread": args.thread},
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    summary = result.get("summary")
    if not summary:
        print(f"No summary for thread '{args.thread}'.")
        return 0
    print(f"# Summary: {result['thread']}  (updated {result['updated_ts']} by {result['updated_by']})\n")
    print(summary)
    return 0


def handle_update(args, config):
    if args.file:
        body = open(args.file, "r", encoding="utf-8").read()
    elif args.body:
        body = args.body
    else:
        print("Provide --body or --file.", file=sys.stderr)
        return 1
    result = request_json(
        config,
        method="POST",
        path="/v1/summary",
        payload={"thread": args.thread, "body": body},
    )
    if result.get("ok"):
        print(f"Summary updated: {result['thread']} by {result['updated_by']} at {result['updated_ts']}")
    else:
        print(f"Error: {json.dumps(result)}", file=sys.stderr)
        return 1
    return 0


def handle_onboard(args, config):
    result = request_json(
        config,
        method="GET",
        path="/v1/onboarding",
        query={"thread": args.thread, "recent_limit": args.recent_limit},
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    summary = result.get("summary")
    print(f"# Onboarding: {result['thread']}")
    if summary:
        print(
            f"\nSummary revision {summary.get('revision_id', 0)} "
            f"(updated {summary.get('updated_ts', '')} by {summary.get('updated_by', '')})\n"
        )
        print(summary.get("body") or "No rendered summary body.")
    else:
        print("\nNo summary has been published.\n")

    taskboard = result.get("authoritative_taskboard") or {}
    counts = taskboard.get("counts") or {}
    print("\n## Authoritative Taskboard")
    print(
        ", ".join(
            f"{status}={counts.get(status, 0)}"
            for status in ("queued", "claimed", "blocked", "done")
        )
    )
    open_tasks = taskboard.get("open_tasks") or []
    if open_tasks:
        for task in open_tasks:
            print(pretty_task(task))
    else:
        print("No open tasks.")

    print(f"\n## Latest {args.recent_limit} Messages")
    recent_messages = result.get("recent_messages") or []
    if recent_messages:
        for message in recent_messages:
            print(pretty_message(message))
            print()
    else:
        print("No messages.")

    delta = result.get("delta") or {}
    uncovered = int(delta.get("uncovered_message_count", 0))
    if not delta.get("coverage_known"):
        print("WARNING: Summary coverage is unknown; recent messages are not a complete delta.")
    elif not delta.get("complete"):
        returned = int(delta.get("returned_uncovered_count", 0))
        print(f"WARNING: Summary is behind by {uncovered} messages; only {returned} are shown here.")
    elif uncovered:
        print(f"Summary delta is complete: {uncovered} newer message(s) shown.")
    else:
        print("Summary is current through the message head.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Read or update the watercooler rolling summary.")
    parser.add_argument("--config", type=str, default="", help="Config path override.")
    parser.add_argument("--thread", type=str, default="general", help="Thread name (default: general).")
    sub = parser.add_subparsers(dest="command", required=True)

    read_p = sub.add_parser("read", help="Read the current summary.")
    read_p.add_argument("--json", action="store_true", help="Print raw JSON.")

    onboard_p = sub.add_parser("onboard", help="Read one-snapshot summary, Taskboard state, and recent messages.")
    onboard_p.add_argument("--recent-limit", type=int, default=5, help="Recent messages to include (default: 5).")
    onboard_p.add_argument("--json", action="store_true", help="Print raw JSON.")

    update_p = sub.add_parser("update", help="Update the summary.")
    update_p.add_argument("--body", type=str, default="", help="Summary text.")
    update_p.add_argument("--file", type=str, default="", help="Read summary from file.")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "read":
        return handle_read(args, config)
    elif args.command == "onboard":
        return handle_onboard(args, config)
    elif args.command == "update":
        return handle_update(args, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
