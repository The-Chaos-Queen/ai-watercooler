from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .common import WatercoolerError, load_config, request_json


def read_body(args: argparse.Namespace) -> str:
    if args.body:
        return args.body
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    if args.stdin:
        return sys.stdin.read()
    raise ValueError("Provide --body, --body-file, or --stdin")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Post a message to Watercooler.")
    parser.add_argument("--config", type=str, default="", help="Optional config path override.")
    parser.add_argument("--from-agent", type=str, default="", help="Sender identity.")
    parser.add_argument("--to-agent", type=str, default="", help="Recipient identity.")
    parser.add_argument("--thread", type=str, default="general", help="Thread name.")
    parser.add_argument("--topic", type=str, default="", help="Optional topic label.")
    parser.add_argument("--lang", type=str, default="en", help="Body language label, default en. Pass --lang jbo for Lojban.")
    parser.add_argument("--tag", action="append", default=[], help="Repeatable tag field.")
    parser.add_argument("--body", type=str, default="", help="Inline message body.")
    parser.add_argument("--body-file", type=str, default="", help="Read the message body from a file.")
    parser.add_argument("--stdin", action="store_true", help="Read the message body from stdin.")
    parser.add_argument("--allow-default", action="store_true",
                        help="Permit posting on the default config.json (you must actually BE its principal).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve identity and print the payload without posting. Use as a whoami check.")
    return parser


def guard_identity(args: argparse.Namespace, config: dict) -> str:
    """Fail loudly instead of silently using another principal's token."""
    principal = config.get("principal") or config.get("default_from") or "<unknown>"
    used_default = not args.config and not os.environ.get("WATERCOOLER_CONFIG", "").strip()
    if used_default and not args.allow_default:
        raise SystemExit(
            f"REFUSING to post: no WATERCOOLER_CONFIG and no --config, so this would run on the\n"
            f"default config ({config['_config_path']}) and sign on the wire as '{principal}'.\n"
            f"That is almost always a post-compaction fallback, not a choice.\n"
            f"Fix: point WATERCOOLER_CONFIG at YOUR session file under\n"
            f"%LOCALAPPDATA%\\Watercooler\\sessions\\<you>-<date>.json (or pass --config).\n"
            f"If you truly are '{principal}', re-run with --allow-default."
        )
    if args.from_agent and args.from_agent != principal:
        raise SystemExit(
            f"REFUSING to post: --from-agent '{args.from_agent}' does not match the token principal\n"
            f"'{principal}' ({config['_config_path']}). The server records the token identity;\n"
            f"a mismatched display name only falsifies the roster. Use your own session config."
        )
    print(f"posting as '{principal}' via {config['_config_path']}", file=sys.stderr)
    return principal


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    principal = guard_identity(args, config)
    body = read_body(args).strip()
    if not body:
        raise ValueError("Message body is empty")

    from_agent = args.from_agent or principal
    to_agent = args.to_agent or config.get("default_to", "")
    payload = {
        "from_agent": from_agent,
        "to_agent": to_agent,
        "thread": args.thread,
        "topic": args.topic,
        "lang": args.lang,
        "tags": list(args.tag or []),
        "body": body,
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_post": payload}, ensure_ascii=False, indent=2))
        return 0
    try:
        result = request_json(config, method="POST", path="/v1/post", payload=payload)
    except WatercoolerError as exc:
        raise SystemExit(f"POST failed: {exc}") from exc

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
