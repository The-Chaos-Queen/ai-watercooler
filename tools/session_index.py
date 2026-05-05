#!/usr/bin/env python3
"""
session_index.py — Extract structured summaries from Claude Code session JONLs.

Reads a raw session JSONL and produces a compact index entry: wolf name, dates,
files changed, tools used, watercooler posts, topics discussed, and key findings.

Designed to be run after a session ends (or any time). Appends to a per-project
index file that wolves can scan at boot in <500 tokens.

Usage:
  # Index a specific session:
  python session_index.py --jsonl ~/.claude/projects/.../09a95d9f.jsonl

  # Index all sessions in the project:
  python session_index.py --all

  # Read the index (what a wolf does at boot):
  python session_index.py --read
  python session_index.py --read --wolf purple
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

DEFAULT_PROJECT_DIR = Path.home() / ".claude" / "projects" / "C--Users-cerub-OneDrive-Dokumente-LLM"
DEFAULT_INDEX_FILE = Path("C:/Users/cerub/OneDrive/Dokumente/LLM/CHEESE_Memory/session_index.json")


def extract_session_summary(jsonl_path: Path) -> dict | None:
    """Extract a structured summary from a session JSONL."""
    wolf_name = ""
    session_id = ""
    timestamps = []
    tool_counts = Counter()
    files_written = set()
    files_edited = set()
    watercooler_posts = []
    user_messages = []
    assistant_text_samples = []
    topics = set()
    line_count = 0

    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line_count += 1
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = d.get("type", "")

                # Wolf identity
                if msg_type == "agent-name":
                    wolf_name = d.get("agentName", "")
                    session_id = d.get("sessionId", "")

                # Session ID fallback
                if not session_id and d.get("sessionId"):
                    session_id = d["sessionId"]

                # Timestamps from system messages
                if msg_type == "system":
                    ts = d.get("timestamp") or d.get("message", {}).get("timestamp")
                    if ts:
                        timestamps.append(str(ts))

                # Tool uses
                if msg_type == "assistant":
                    content = d.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for c in content:
                            if not isinstance(c, dict):
                                continue
                            if c.get("type") == "tool_use":
                                name = c.get("name", "unknown")
                                tool_counts[name] += 1
                                inp = c.get("input", {})

                                if name == "Write":
                                    fp = inp.get("file_path", "")
                                    if fp:
                                        files_written.add(fp)
                                elif name == "Edit":
                                    fp = inp.get("file_path", "")
                                    if fp:
                                        files_edited.add(fp)

                                # Detect watercooler posts
                                if name == "Bash":
                                    cmd = inp.get("command", "")
                                    if "watercooler" in cmd and ("post" in cmd or "/v1/post" in cmd):
                                        topic_match = re.search(r"topic['\"]:\s*['\"]([^'\"]+)", cmd)
                                        if topic_match:
                                            watercooler_posts.append(topic_match.group(1)[:80])
                                if name.startswith("mcp__claude_ai_Watercooler__post"):
                                    body = inp.get("body", "")
                                    watercooler_posts.append(body[:80] if body else "post")

                            elif c.get("type") == "text":
                                text = str(c.get("text", ""))
                                if len(text) > 20 and len(assistant_text_samples) < 50:
                                    assistant_text_samples.append(text[:200])

                # User messages for topic extraction
                if msg_type == "user":
                    content = d.get("message", {}).get("content", "")
                    if isinstance(content, str) and len(content) > 10:
                        user_messages.append(content[:200])
                    elif isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "text":
                                text = str(c.get("text", ""))
                                if len(text) > 10:
                                    user_messages.append(text[:200])

    except Exception as e:
        print(f"  Error reading {jsonl_path.name}: {e}", file=sys.stderr)
        return None

    if line_count < 5:
        return None

    # Extract topics from file paths
    for fp in files_written | files_edited:
        fp_lower = fp.lower().replace("\\", "/")
        if "mocop" in fp_lower:
            topics.add("MoCoP")
        if "watercooler" in fp_lower:
            topics.add("watercooler")
        if "exocortex" in fp_lower or "qdrant" in fp_lower:
            topics.add("exocortex")
        if "hurtig" in fp_lower:
            topics.add("hurtig.ai")
        if "cheese_memory" in fp_lower:
            topics.add("CHEESE")
        if "session_log" in fp_lower:
            topics.add("session-logs")
        if "sleep" in fp_lower:
            topics.add("sleep")
        if "bridge" in fp_lower or "mamba" in fp_lower:
            topics.add("bridge")
        if "theory" in fp_lower:
            topics.add("theory")

    # Extract key terms from assistant text
    key_terms = Counter()
    important_words = {
        "confirmed", "failed", "passed", "broken", "fixed", "proved",
        "discovered", "implemented", "deployed", "shipped", "validated",
        "bottleneck", "breakthrough", "blocker", "result", "finding",
    }
    for text in assistant_text_samples:
        words = text.lower().split()
        for w in words:
            w_clean = w.strip(".,;:!?\"'()[]{}*")
            if w_clean in important_words:
                key_terms[w_clean] += 1

    # Shorten file paths
    repo_prefix = "C:\\Users\\cerub\\OneDrive\\Dokumente\\LLM\\"
    repo_prefix_fwd = "C:/Users/cerub/OneDrive/Dokumente/LLM/"

    def shorten(fp):
        return fp.replace(repo_prefix, "").replace(repo_prefix_fwd, "").replace("\\", "/")

    # File modification date as proxy for session date
    stat = jsonl_path.stat()
    file_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")

    return {
        "session_id": session_id or jsonl_path.stem,
        "wolf": wolf_name or "unknown",
        "date": file_date,
        "lines": line_count,
        "size_mb": round(stat.st_size / (1024 * 1024), 1),
        "topics": sorted(topics),
        "tools_top5": [f"{name}:{count}" for name, count in tool_counts.most_common(5)],
        "files_written": sorted(shorten(f) for f in files_written)[:15],
        "files_edited": sorted(shorten(f) for f in files_edited)[:15],
        "watercooler_posts": watercooler_posts[:10],
        "key_signals": [f"{t}({n})" for t, n in key_terms.most_common(5)] if key_terms else [],
        "user_message_count": len(user_messages),
    }


def read_index(index_path: Path, wolf: str = "") -> list[dict]:
    """Read and optionally filter the session index."""
    if not index_path.exists():
        return []
    data = json.loads(index_path.read_text(encoding="utf-8"))
    entries = data.get("sessions", [])
    if wolf:
        entries = [e for e in entries if e.get("wolf", "").lower() == wolf.lower()]
    return entries


def print_index(entries: list[dict], verbose: bool = False):
    """Print the index in a scannable format."""
    for e in entries:
        wolf = e.get("wolf", "?")
        date = e.get("date", "?")
        topics = ", ".join(e.get("topics", []))
        size = e.get("size_mb", 0)
        sid = e.get("session_id", "?")[:8]

        print(f"  {date} | {wolf:15s} | {size:5.1f}MB | {topics}")

        if verbose:
            if e.get("files_written"):
                print(f"    wrote: {', '.join(e['files_written'][:5])}")
            if e.get("files_edited"):
                print(f"    edited: {', '.join(e['files_edited'][:5])}")
            if e.get("watercooler_posts"):
                print(f"    watercooler: {len(e['watercooler_posts'])} posts")
            if e.get("key_signals"):
                print(f"    signals: {', '.join(e['key_signals'])}")
            print()


def main():
    parser = argparse.ArgumentParser(description="Session index — structured summaries from JONLs")
    parser.add_argument("--jsonl", type=str, default="", help="Index a specific JSONL file")
    parser.add_argument("--all", action="store_true", help="Index all JONLs in the project")
    parser.add_argument("--read", action="store_true", help="Read the index")
    parser.add_argument("--wolf", type=str, default="", help="Filter by wolf name")
    parser.add_argument("--verbose", action="store_true", help="Show file details")
    parser.add_argument("--index-file", type=str, default=str(DEFAULT_INDEX_FILE))
    parser.add_argument("--project-dir", type=str, default=str(DEFAULT_PROJECT_DIR))
    args = parser.parse_args()

    index_path = Path(args.index_file)

    if args.read:
        entries = read_index(index_path, wolf=args.wolf)
        if not entries:
            print("  No index entries found." + (f" (wolf={args.wolf})" if args.wolf else ""))
            return 0
        print(f"  Session Index ({len(entries)} entries):")
        print_index(entries, verbose=args.verbose)
        return 0

    # Build/update index
    jsonl_files = []
    if args.jsonl:
        jsonl_files = [Path(args.jsonl)]
    elif args.all:
        project_dir = Path(args.project_dir)
        jsonl_files = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    else:
        print("Specify --jsonl <file>, --all, or --read")
        return 1

    # Load existing index
    existing = {}
    if index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        for e in data.get("sessions", []):
            existing[e.get("session_id", "")] = e

    new_count = 0
    for jsonl_path in jsonl_files:
        sid = jsonl_path.stem
        if sid in existing:
            # Check if file grew (session still running)
            old_lines = existing[sid].get("lines", 0)
            current_size = jsonl_path.stat().st_size
            if current_size == existing[sid].get("_raw_size", 0):
                continue

        print(f"  Indexing {jsonl_path.name}...")
        summary = extract_session_summary(jsonl_path)
        if summary:
            summary["_raw_size"] = jsonl_path.stat().st_size
            existing[summary["session_id"]] = summary
            new_count += 1

    # Sort by date
    sessions = sorted(existing.values(), key=lambda e: e.get("date", ""), reverse=True)

    # Write index
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_data = {
        "updated": datetime.now().isoformat(),
        "session_count": len(sessions),
        "sessions": sessions,
    }
    index_path.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print(f"\n  Index updated: {len(sessions)} sessions ({new_count} new/updated)")
    print(f"  Saved to {index_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
