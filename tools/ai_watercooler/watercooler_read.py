from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

# Force UTF-8 output on Windows to handle emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from common import load_config, pretty_message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read messages from the AI watercooler.")
    parser.add_argument("--config", type=str, default="", help="Optional config path override.")
    parser.add_argument("--thread", type=str, default="", help="Filter by thread.")
    parser.add_argument("--participant", type=str, default="", help="Filter by sender or recipient.")
    parser.add_argument("--since-id", type=int, default=0, help="Only show rows with id greater than this value.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of rows to fetch.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a formatted view.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    params = {
        "limit": str(args.limit),
    }
    if args.thread:
        params["thread"] = args.thread
    if args.participant:
        params["participant"] = args.participant
    if args.since_id > 0:
        params["since_id"] = str(args.since_id)
    query = urllib.parse.urlencode(params)
    url = config["base_url"].rstrip("/") + "/v1/messages"
    if query:
        url += "?" + query

    request = urllib.request.Request(
        url=url,
        headers={"X-Watercooler-Token": config["token"]},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"READ failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
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
