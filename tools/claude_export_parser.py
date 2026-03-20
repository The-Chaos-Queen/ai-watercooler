#!/usr/bin/env python3
"""
Claude Conversation Export Parser
==================================
Parses the conversations.json from Anthropic's data export
into readable Markdown files.

Usage:
    python claude_export_parser.py conversations.json --list
    python claude_export_parser.py conversations.json --search "Rimmon"
    python claude_export_parser.py conversations.json --export <uuid> [-o output.md]
    python claude_export_parser.py conversations.json --export-all [-o output_dir]

Author: Laura + Claude Code
Date: 2026-03-19
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_export(path: str) -> list[dict]:
    """Load the conversations.json export file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected format: expected list, got {type(data).__name__}")


def extract_text(message: dict) -> str:
    """Extract readable text from a message's content blocks."""
    # Try top-level text first
    text = message.get("text", "")
    if text and text.strip():
        return text.strip()

    # Otherwise assemble from content blocks
    content = message.get("content", [])
    parts = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text" and block.get("text"):
                parts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_name = block.get("name", "unknown_tool")
                tool_input = block.get("input", {})
                if isinstance(tool_input, dict):
                    # Show a compact summary
                    summary = json.dumps(tool_input, ensure_ascii=False)
                    if len(summary) > 200:
                        summary = summary[:200] + "..."
                    parts.append(f"[Tool: {tool_name}({summary})]")
                else:
                    parts.append(f"[Tool: {tool_name}]")
            elif block.get("type") == "tool_result":
                result_text = block.get("text", block.get("content", ""))
                if isinstance(result_text, list):
                    result_text = " ".join(
                        b.get("text", "") for b in result_text if isinstance(b, dict)
                    )
                if result_text and len(str(result_text)) > 300:
                    result_text = str(result_text)[:300] + "..."
                parts.append(f"[Result: {result_text}]")
            elif block.get("type") == "thinking":
                thinking = block.get("thinking", "")
                if thinking:
                    preview = thinking[:150] + "..." if len(thinking) > 150 else thinking
                    parts.append(f"[Thinking: {preview}]")
        elif isinstance(block, str):
            parts.append(block)

    return "\n".join(parts).strip()


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable date/time."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return ts or "?"


def conversation_to_markdown(conv: dict, include_metadata: bool = True) -> str:
    """Convert a single conversation to Markdown format."""
    lines = []

    name = conv.get("name") or "(Unnamed Conversation)"
    uuid = conv.get("uuid", "?")
    created = format_timestamp(conv.get("created_at", ""))
    updated = format_timestamp(conv.get("updated_at", ""))
    summary = conv.get("summary", "")

    if include_metadata:
        lines.append(f"# {name}")
        lines.append("")
        lines.append(f"*UUID: {uuid}*  ")
        lines.append(f"*Created: {created} | Updated: {updated}*")
        if summary:
            lines.append(f"*Summary: {summary}*")
        lines.append("")
        lines.append("---")
        lines.append("")

    messages = conv.get("chat_messages", [])
    for msg in messages:
        sender = msg.get("sender", "unknown")
        ts = format_timestamp(msg.get("created_at", ""))
        text = extract_text(msg)

        if not text:
            continue

        # Format sender
        if sender == "human":
            label = "**You**"
        elif sender == "assistant":
            label = "**Claude**"
        else:
            label = f"**{sender}**"

        lines.append(f"{label} *({ts})*")
        lines.append("")
        lines.append(text)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """Create a safe filename from a conversation name."""
    if not name:
        return "unnamed"
    # Remove/replace problematic characters
    clean = re.sub(r'[<>:"/\\|?*]', '', name)
    clean = re.sub(r'\s+', '_', clean.strip())
    clean = clean[:max_length]
    return clean or "unnamed"


def cmd_list(conversations: list[dict]):
    """List all conversations with metadata."""
    print(f"{'Date':12s} {'Msgs':>5s}  {'Name'}")
    print("-" * 70)
    for conv in sorted(conversations, key=lambda c: c.get("created_at", ""), reverse=True):
        msgs = len(conv.get("chat_messages", []))
        name = conv.get("name") or "(unnamed)"
        created = format_timestamp(conv.get("created_at", ""))[:10]
        uuid = conv.get("uuid", "?")[:8]
        print(f"{created:12s} {msgs:5d}  [{uuid}] {name[:60]}")


def cmd_search(conversations: list[dict], query: str):
    """Search across all conversations for a text query."""
    query_lower = query.lower()
    results = []

    for conv in conversations:
        conv_name = conv.get("name") or "(unnamed)"
        conv_uuid = conv.get("uuid", "?")

        for msg in conv.get("chat_messages", []):
            text = extract_text(msg)
            if query_lower in text.lower():
                sender = msg.get("sender", "?")
                ts = format_timestamp(msg.get("created_at", ""))

                # Find context around match
                idx = text.lower().index(query_lower)
                start = max(0, idx - 80)
                end = min(len(text), idx + len(query) + 80)
                snippet = text[start:end].replace("\n", " ")
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."

                results.append({
                    "conv_name": conv_name,
                    "conv_uuid": conv_uuid,
                    "sender": sender,
                    "timestamp": ts,
                    "snippet": snippet,
                })

    if not results:
        print(f'No results for "{query}"')
        return

    print(f'Found {len(results)} matches for "{query}":\n')
    for r in results:
        sender_label = "You" if r["sender"] == "human" else "Claude"
        print(f"  [{r['conv_uuid'][:8]}] {r['conv_name'][:40]}")
        print(f"    {sender_label} ({r['timestamp']})")
        print(f"    {r['snippet']}")
        print()


def cmd_export(conversations: list[dict], uuid_prefix: str, output: str = None):
    """Export a single conversation to Markdown."""
    # Find conversation by UUID (prefix match)
    conv = None
    for c in conversations:
        if c.get("uuid", "").startswith(uuid_prefix):
            conv = c
            break

    if not conv:
        print(f'No conversation found matching UUID "{uuid_prefix}"')
        sys.exit(1)

    md = conversation_to_markdown(conv)

    if output:
        Path(output).write_text(md, encoding="utf-8")
        print(f"Exported to: {output}")
    else:
        print(md)


def cmd_export_all(conversations: list[dict], output_dir: str = None):
    """Export all conversations to individual Markdown files."""
    out_dir = Path(output_dir or "claude_conversations")
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for conv in conversations:
        msgs = conv.get("chat_messages", [])
        if not msgs:
            continue

        name = conv.get("name") or ""
        created = format_timestamp(conv.get("created_at", ""))[:10]
        uuid_short = conv.get("uuid", "unknown")[:8]
        safe_name = sanitize_filename(name)

        filename = f"{created}_{uuid_short}_{safe_name}.md"
        filepath = out_dir / filename

        md = conversation_to_markdown(conv)
        filepath.write_text(md, encoding="utf-8")
        count += 1

    print(f"Exported {count} conversations to: {out_dir}")


def cmd_stats(conversations: list[dict]):
    """Show statistics about the export."""
    total_msgs = 0
    total_human = 0
    total_assistant = 0
    total_chars_human = 0
    total_chars_assistant = 0

    for conv in conversations:
        for msg in conv.get("chat_messages", []):
            total_msgs += 1
            text = extract_text(msg)
            if msg.get("sender") == "human":
                total_human += 1
                total_chars_human += len(text)
            elif msg.get("sender") == "assistant":
                total_assistant += 1
                total_chars_assistant += len(text)

    dates = [c.get("created_at", "")[:10] for c in conversations if c.get("created_at")]
    date_range = f"{min(dates)} to {max(dates)}" if dates else "?"

    print(f"Conversations:    {len(conversations)}")
    print(f"Date range:       {date_range}")
    print(f"Total messages:   {total_msgs}")
    print(f"  You:            {total_human} ({total_chars_human:,} chars)")
    print(f"  Claude:         {total_assistant} ({total_chars_assistant:,} chars)")
    print(f"  Avg per conv:   {total_msgs / max(len(conversations), 1):.0f} messages")


def main():
    parser = argparse.ArgumentParser(
        description="Parse Anthropic Claude conversation exports"
    )
    parser.add_argument("input", help="Path to conversations.json")
    parser.add_argument("--list", action="store_true", help="List all conversations")
    parser.add_argument("--stats", action="store_true", help="Show export statistics")
    parser.add_argument("--search", metavar="QUERY", help="Search across all conversations")
    parser.add_argument("--export", metavar="UUID", help="Export a single conversation (UUID or prefix)")
    parser.add_argument("--export-all", action="store_true", help="Export all conversations to Markdown files")
    parser.add_argument("-o", "--output", help="Output file or directory")

    args = parser.parse_args()

    conversations = load_export(args.input)

    if args.list:
        cmd_list(conversations)
    elif args.stats:
        cmd_stats(conversations)
    elif args.search:
        cmd_search(conversations, args.search)
    elif args.export:
        cmd_export(conversations, args.export, args.output)
    elif args.export_all:
        cmd_export_all(conversations, args.output)
    else:
        # Default: show stats + list
        cmd_stats(conversations)
        print()
        cmd_list(conversations)


if __name__ == "__main__":
    main()
