from __future__ import annotations

import argparse
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from common import load_config, request_json


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Read or update the watercooler rolling summary.")
    parser.add_argument("--config", type=str, default="", help="Config path override.")
    parser.add_argument("--thread", type=str, default="mamba-bridge", help="Thread name (default: mamba-bridge).")
    sub = parser.add_subparsers(dest="command", required=True)

    read_p = sub.add_parser("read", help="Read the current summary.")
    read_p.add_argument("--json", action="store_true", help="Print raw JSON.")

    update_p = sub.add_parser("update", help="Update the summary.")
    update_p.add_argument("--body", type=str, default="", help="Summary text.")
    update_p.add_argument("--file", type=str, default="", help="Read summary from file.")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "read":
        return handle_read(args, config)
    elif args.command == "update":
        return handle_update(args, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
