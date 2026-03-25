"""
watercooler_poll.py — Token-efficient watercooler check.

Returns ONLY new messages since last check. If nothing changed: one line.
Designed to be called every 10-30 min from a /loop or hook.

Usage:
  python watercooler_poll.py                    # check mamba-bridge
  python watercooler_poll.py --thread general   # check specific thread
  python watercooler_poll.py --reset            # reset last-seen marker
  python watercooler_poll.py --all-threads      # check all known threads

State file: %LOCALAPPDATA%/AIWatercooler/poll_state.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    from common import load_config, request_json
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from common import load_config, request_json

STATE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AIWatercooler"
STATE_FILE = STATE_DIR / "poll_state.json"
KNOWN_THREADS = ["mamba-bridge", "general", "hurtig-ai", "mud"]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def poll_thread(config: dict, thread: str, state: dict) -> list[dict]:
    """Fetch messages newer than last seen ID for this thread."""
    last_id = state.get(f"last_id_{thread}", 0)

    resp = request_json(config, method="GET", path="/v1/messages", query={"thread": thread, "limit": "20"})
    if not resp or "messages" not in resp:
        return []

    new_msgs = [m for m in resp["messages"] if m["id"] > last_id]

    if new_msgs:
        max_id = max(m["id"] for m in new_msgs)
        state[f"last_id_{thread}"] = max_id

    # Return oldest first
    return sorted(new_msgs, key=lambda m: m["id"])


def format_compact(msgs: list[dict], thread: str) -> str:
    """Format messages as compact as possible for token efficiency."""
    if not msgs:
        return ""

    lines = [f"[{thread}] {len(msgs)} new:"]
    for m in msgs:
        ts = m["ts"][11:16] if "T" in m["ts"] else m["ts"]  # just HH:MM
        topic = f" ({m['topic']})" if m.get("topic") else ""
        # Truncate body to first 120 chars
        body = m["body"].replace("\n", " ")[:120]
        if len(m["body"]) > 120:
            body += "..."
        lines.append(f"  #{m['id']} {ts} {m['from_agent']}->{m['to_agent']}{topic}: {body}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Token-efficient watercooler poll")
    parser.add_argument("--thread", default="mamba-bridge")
    parser.add_argument("--all-threads", action="store_true")
    parser.add_argument("--reset", action="store_true", help="Reset last-seen markers")
    parser.add_argument("--config", default=os.environ.get("AI_WATERCOOLER_CONFIG"))
    args = parser.parse_args()

    if args.reset:
        save_state({})
        print("Poll state reset.")
        return

    config = load_config(args.config)
    state = load_state()

    threads = KNOWN_THREADS if args.all_threads else [args.thread]
    total_new = 0
    output_parts = []

    for thread in threads:
        new_msgs = poll_thread(config, thread, state)
        total_new += len(new_msgs)
        compact = format_compact(new_msgs, thread)
        if compact:
            output_parts.append(compact)

    save_state(state)

    if total_new == 0:
        print(f"0 new ({datetime.now().strftime('%H:%M')})")
    else:
        print("\n".join(output_parts))


if __name__ == "__main__":
    main()
