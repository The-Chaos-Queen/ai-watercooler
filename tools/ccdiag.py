#!/usr/bin/env python3
"""
ccdiag.py — Claude Code session JSONL diagnostic & recovery tool.

Finds the longest valid conversation chain in a JSONL file and reports
orphaned forks (the bug where resume attaches to wrong parentUuid).

Usage:
  python ccdiag.py diagnose <session.jsonl>     # show chain structure + forks
  python ccdiag.py recover <session.jsonl>       # write cleaned JSONL (longest chain only)
  python ccdiag.py forks <session.jsonl>         # show only fork points with timestamps
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_messages(path: Path) -> list[dict]:
    """Load all JSON objects from a JSONL file."""
    messages = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                obj["_line"] = i
                messages.append(obj)
            except json.JSONDecodeError:
                pass
    return messages


def build_graph(messages: list[dict]) -> tuple[dict, dict, dict]:
    """Build parent->children graph and uuid->message index."""
    by_uuid: dict[str, dict] = {}
    children: dict[str | None, list[str]] = defaultdict(list)
    line_index: dict[str, int] = {}

    for msg in messages:
        uuid = msg.get("uuid")
        if not uuid:
            continue
        by_uuid[uuid] = msg
        parent = msg.get("parentUuid")
        children[parent].append(uuid)
        line_index[uuid] = msg["_line"]

    return by_uuid, dict(children), line_index


def find_longest_chain(by_uuid: dict, children: dict) -> list[str]:
    """Find the longest root-to-leaf chain (the 'true' conversation).

    Uses iterative approach — recursive DFS hits Python's stack limit on
    14k+ message conversations.
    """
    # Find roots (parentUuid is None or not in by_uuid)
    roots = []
    for uuid, msg in by_uuid.items():
        parent = msg.get("parentUuid")
        if parent is None or parent not in by_uuid:
            roots.append(uuid)

    if not roots:
        return []

    # Find all leaves (no children)
    leaves = [uuid for uuid in by_uuid if uuid not in children or not children[uuid]]

    # For each leaf, walk back to root and measure chain length
    best_chain: list[str] = []

    for leaf in leaves:
        chain = []
        current = leaf
        visited = set()
        while current and current in by_uuid and current not in visited:
            visited.add(current)
            chain.append(current)
            current = by_uuid[current].get("parentUuid")
        chain.reverse()
        if len(chain) > len(best_chain):
            best_chain = chain

    return best_chain


def find_forks(by_uuid: dict, children: dict) -> list[dict]:
    """Find nodes with multiple children (fork points)."""
    forks = []
    for parent_uuid, child_uuids in children.items():
        if parent_uuid is None:
            continue
        if len(child_uuids) > 1 and parent_uuid in by_uuid:
            parent_msg = by_uuid[parent_uuid]
            fork_info = {
                "parent_uuid": parent_uuid,
                "parent_line": parent_msg.get("_line"),
                "parent_ts": parent_msg.get("timestamp", ""),
                "parent_type": parent_msg.get("type", ""),
                "branches": len(child_uuids),
                "children": [],
            }
            for child_uuid in child_uuids:
                child_msg = by_uuid.get(child_uuid, {})
                fork_info["children"].append({
                    "uuid": child_uuid,
                    "line": child_msg.get("_line"),
                    "ts": child_msg.get("timestamp", ""),
                    "type": child_msg.get("type", ""),
                    "subtype": child_msg.get("subtype", ""),
                    "preview": str(child_msg.get("content", ""))[:100]
                        if isinstance(child_msg.get("content"), str)
                        else str(child_msg.get("message", {}).get("content", [{}])[0].get("text", ""))[:100]
                        if isinstance(child_msg.get("message", {}).get("content"), list)
                        else "",
                })
            forks.append(fork_info)
    return forks


def cmd_diagnose(path: Path):
    messages = load_messages(path)
    print(f"File: {path}")
    print(f"Total lines: {len(messages)}")
    print(f"File size: {path.stat().st_size / 1024 / 1024:.1f} MB")

    by_uuid, children, line_index = build_graph(messages)
    print(f"Messages with UUID: {len(by_uuid)}")

    # Count types
    types = defaultdict(int)
    for msg in messages:
        types[msg.get("type", "unknown")] += 1
    print(f"Message types: {dict(types)}")

    # Find chain
    chain = find_longest_chain(by_uuid, children)
    print(f"\nLongest chain: {len(chain)} messages")
    if chain:
        first = by_uuid[chain[0]]
        last = by_uuid[chain[-1]]
        print(f"  Start: L{first['_line']} {first.get('timestamp', '?')}")
        print(f"  End:   L{last['_line']} {last.get('timestamp', '?')}")

    orphaned = set(by_uuid.keys()) - set(chain)
    print(f"Orphaned messages (not on main chain): {len(orphaned)}")

    # Forks
    forks = find_forks(by_uuid, children)
    print(f"\nFork points: {len(forks)}")
    for fork in forks:
        print(f"\n  Fork at L{fork['parent_line']} ({fork['parent_ts']}) -> {fork['branches']} branches:")
        for child in fork["children"]:
            on_chain = child["uuid"] in chain
            tag = "MAIN" if on_chain else "ORPHAN"
            print(f"    [{tag}] L{child['line']} {child['ts']} [{child['type']}/{child['subtype']}]")
            if child["preview"]:
                print(f"           {child['preview'][:80]}...")

    # Bridge status events (session resumes)
    resumes = [m for m in messages if m.get("subtype") == "bridge_status"]
    print(f"\nSession resumes (bridge_status): {len(resumes)}")
    for r in resumes:
        parent = r.get("parentUuid", "")
        on_chain = r.get("uuid", "") in chain
        tag = "MAIN" if on_chain else "ORPHAN"
        print(f"  [{tag}] L{r['_line']} {r.get('timestamp', '?')} parent={parent[:12] if parent else 'None'}...")


def cmd_forks(path: Path):
    messages = load_messages(path)
    by_uuid, children, _ = build_graph(messages)
    chain = find_longest_chain(by_uuid, children)
    forks = find_forks(by_uuid, children)

    if not forks:
        print("No forks found. Session chain is clean.")
        return

    print(f"Found {len(forks)} fork point(s):\n")
    for fork in forks:
        print(f"Fork at L{fork['parent_line']} ({fork['parent_ts']})")
        for child in fork["children"]:
            on_chain = child["uuid"] in chain
            tag = "MAIN" if on_chain else "FORK"
            print(f"  [{tag}] L{child['line']} {child['ts']} {child['type']}/{child['subtype']}")
        print()


def cmd_recover(path: Path):
    messages = load_messages(path)
    by_uuid, children, _ = build_graph(messages)
    chain = find_longest_chain(by_uuid, children)
    chain_set = set(chain)

    if not chain:
        print("ERROR: No valid chain found.")
        return

    # Collect all lines that are on the main chain OR are non-uuid entries
    # (file-history-snapshots etc that belong to the chain)
    out_path = path.with_suffix(".recovered.jsonl")

    # Build a set of messageIds referenced by chain messages
    chain_message_ids = set()
    for uuid in chain:
        msg = by_uuid[uuid]
        mid = msg.get("uuid")
        if mid:
            chain_message_ids.add(mid)

    kept = 0
    skipped = 0
    with path.open("r", encoding="utf-8") as fin, \
         out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            try:
                obj = json.loads(line_stripped)
            except json.JSONDecodeError:
                fout.write(line)
                kept += 1
                continue

            uuid = obj.get("uuid")
            msg_type = obj.get("type", "")

            # Keep if: on the main chain, or is a non-chain structural entry
            # (file-history-snapshot, etc)
            if uuid and uuid in chain_set:
                fout.write(line)
                kept += 1
            elif not uuid and msg_type in ("file-history-snapshot",):
                fout.write(line)
                kept += 1
            elif not uuid:
                # Other non-uuid entries — keep them
                fout.write(line)
                kept += 1
            else:
                skipped += 1

    print(f"Recovered: {out_path}")
    print(f"  Kept: {kept} lines")
    print(f"  Skipped (orphaned forks): {skipped} lines")
    print(f"  Main chain length: {len(chain)} messages")
    first = by_uuid[chain[0]]
    last = by_uuid[chain[-1]]
    print(f"  Chain: {first.get('timestamp', '?')} -> {last.get('timestamp', '?')}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    cmd = sys.argv[1]
    path = Path(sys.argv[2])

    if not path.exists():
        print(f"ERROR: File not found: {path}")
        return 1

    if cmd == "diagnose":
        cmd_diagnose(path)
    elif cmd == "forks":
        cmd_forks(path)
    elif cmd == "recover":
        cmd_recover(path)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
