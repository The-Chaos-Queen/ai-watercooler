from __future__ import annotations

import argparse
import json
import sys

# Force UTF-8 output on Windows to handle emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .common import WatercoolerError, load_config, pretty_message, request_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read messages from Watercooler.",
        epilog="Results are newest-first (id DESC). --since-id is EXCLUSIVE (id > N): "
        "it is a poll cursor, not a fetch-by-id. To fetch one exact message use --id N.",
    )
    parser.add_argument("--config", type=str, default="", help="Optional config path override.")
    parser.add_argument("--thread", type=str, default="", help="Filter by thread.")
    parser.add_argument("--participant", type=str, default="", help="Filter by sender or recipient.")
    parser.add_argument("--id", type=int, default=0, help="Fetch exactly this message id.")
    parser.add_argument("--since-id", type=int, default=0, help="Only show rows with id greater than this value (exclusive).")
    parser.add_argument("--before-id", type=int, default=0, help="Only show rows with id less than this value (exclusive).")
    parser.add_argument("--search", type=str, default="", help="FTS5 keyword filter, e.g. 'sleep AND gate'. Hyphenated terms must be FTS5-quoted: '\"how-full\"' (bare hyphens error).")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of rows to fetch.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a formatted view.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    if args.id > 0:
        if args.since_id or args.before_id:
            raise SystemExit("--id cannot be combined with --since-id/--before-id")
        args.since_id = args.id - 1
        args.before_id = args.id + 1
        args.limit = 1
    params = {
        "limit": str(args.limit),
    }
    if args.thread:
        params["thread"] = args.thread
    if args.participant:
        params["participant"] = args.participant
    if args.since_id > 0:
        params["since_id"] = str(args.since_id)
    if args.before_id > 0:
        params["before_id"] = str(args.before_id)
    if args.search:
        params["search"] = args.search
    try:
        result = request_json(
            config,
            method="GET",
            path="/v1/messages",
            query=params,
        )
    except WatercoolerError as exc:
        raise SystemExit(f"READ failed: {exc}") from exc

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    rows = result.get("messages", [])
    if not rows:
        print("No messages.")
        return 0
    for row in rows:
        print(pretty_message(row))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
