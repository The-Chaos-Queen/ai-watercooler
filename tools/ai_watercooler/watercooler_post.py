from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import List

from common import load_config


def read_body(args: argparse.Namespace) -> str:
    if args.body:
        return args.body
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    if args.stdin:
        return sys.stdin.read()
    raise ValueError("Provide --body, --body-file, or --stdin")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Post a message to the AI watercooler.")
    parser.add_argument("--config", type=str, default="", help="Optional config path override.")
    parser.add_argument("--from-agent", type=str, default="", help="Sender identity.")
    parser.add_argument("--to-agent", type=str, default="", help="Recipient identity.")
    parser.add_argument("--thread", type=str, default="general", help="Thread name.")
    parser.add_argument("--topic", type=str, default="", help="Optional topic label.")
    parser.add_argument("--lang", type=str, default="jbo", help="Body language label, default jbo.")
    parser.add_argument("--tag", action="append", default=[], help="Repeatable tag field.")
    parser.add_argument("--body", type=str, default="", help="Inline message body.")
    parser.add_argument("--body-file", type=str, default="", help="Read the message body from a file.")
    parser.add_argument("--stdin", action="store_true", help="Read the message body from stdin.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    body = read_body(args).strip()
    if not body:
        raise ValueError("Message body is empty")

    from_agent = args.from_agent or config.get("default_from", "codex")
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
    request = urllib.request.Request(
        url=config["base_url"].rstrip("/") + "/v1/post",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Watercooler-Token": config["token"],
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"POST failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"POST failed: {exc}") from exc

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
