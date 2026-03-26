"""
watercooler_poll.py — Token-efficient watercooler check.

Returns ONLY new messages since last check. If nothing changed: one line.
Designed to be called every 10-30 min from a /loop or hook.

Usage:
  python watercooler_poll.py                    # check mamba-bridge
  python watercooler_poll.py --thread general   # check specific thread
  python watercooler_poll.py --reset            # reset last-seen marker
  python watercooler_poll.py --prime            # seed current head without printing all history
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
DEFAULT_LIMIT = 200


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def state_namespace(config: dict, override: str = "") -> str:
    if override:
        return override
    principal = str(config.get("principal") or config.get("default_from") or "").strip()
    if principal:
        return principal
    config_path = Path(str(config.get("_config_path", "watercooler")))
    return config_path.stem


def state_key(namespace: str, thread: str) -> str:
    return f"{namespace}:last_id:{thread}"


def fetch_messages(config: dict, thread: str, *, since_id: int, limit: int) -> list[dict]:
    resp = request_json(
        config,
        method="GET",
        path="/v1/messages",
        query={"thread": thread, "since_id": str(since_id), "limit": str(limit)},
    )
    rows = resp.get("messages", []) if resp else []
    return sorted(rows, key=lambda m: m["id"])


def poll_thread(config: dict, thread: str, state: dict, namespace: str, limit: int) -> tuple[list[dict], bool]:
    """Fetch messages newer than last seen ID for this thread."""
    last_id = int(state.get(state_key(namespace, thread), 0) or 0)
    new_msgs = fetch_messages(config, thread, since_id=last_id, limit=limit)
    if new_msgs:
        state[state_key(namespace, thread)] = max(m["id"] for m in new_msgs)
    truncated = len(new_msgs) >= limit
    return new_msgs, truncated


def prime_thread(config: dict, thread: str, state: dict, namespace: str, limit: int) -> int:
    rows = fetch_messages(config, thread, since_id=0, limit=limit)
    if not rows:
        return 0
    max_id = max(m["id"] for m in rows)
    state[state_key(namespace, thread)] = max_id
    return max_id


def format_compact(msgs: list[dict], thread: str, *, truncated: bool = False) -> str:
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
    if truncated:
        lines.append(f"  ! poll limit {len(msgs)} hit, older unseen messages may still exist")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Token-efficient watercooler poll")
    parser.add_argument("--thread", default="mamba-bridge")
    parser.add_argument("--all-threads", action="store_true")
    parser.add_argument("--reset", action="store_true", help="Reset last-seen markers")
    parser.add_argument("--prime", action="store_true", help="Seed current head without printing message history")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--state-namespace", default="")
    parser.add_argument("--config", default=os.environ.get("AI_WATERCOOLER_CONFIG"))
    args = parser.parse_args()

    config = load_config(args.config)
    state = load_state()
    namespace = state_namespace(config, args.state_namespace)

    threads = KNOWN_THREADS if args.all_threads else [args.thread]
    if args.reset:
        for thread in threads:
            state.pop(state_key(namespace, thread), None)
        save_state(state)
        print(f"Poll state reset for namespace '{namespace}'.")
        return

    if args.prime:
        primed = []
        for thread in threads:
            max_id = prime_thread(config, thread, state, namespace, args.limit)
            primed.append(f"{thread}=#{max_id}" if max_id else f"{thread}=empty")
        save_state(state)
        print(f"Primed namespace '{namespace}': " + ", ".join(primed))
        return

    total_new = 0
    output_parts = []

    for thread in threads:
        new_msgs, truncated = poll_thread(config, thread, state, namespace, args.limit)
        total_new += len(new_msgs)
        compact = format_compact(new_msgs, thread, truncated=truncated)
        if compact:
            output_parts.append(compact)

    save_state(state)

    if total_new == 0:
        print(f"0 new ({datetime.now().strftime('%H:%M')})")
    else:
        print("\n".join(output_parts))


if __name__ == "__main__":
    main()
