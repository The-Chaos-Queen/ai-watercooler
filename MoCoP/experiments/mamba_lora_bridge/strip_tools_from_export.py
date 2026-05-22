#!/usr/bin/env python3
"""
strip_tools_from_export.py — Clean a Claude Code session export for Mamba trajectory analysis.

Removes:
  - Tool call blocks (Tool: Name + Input: {...} + output lines)
  - System turns entirely
  - /command turns (lines starting with <command-name>)
  - Control characters (SI, SO, etc.)
  - File-content line-number prefixes (e.g. "     1→")

Keeps:
  - User turns (text only)
  - Assistant turns (conversational text + thinking blocks, no tool calls)

Output format matches what trajectory_sequential.py expects:
  ## User
  text
  ## Assistant
  text

Author: Dedra
Date: 2026-04-07
"""

import re
import sys
from pathlib import Path


def is_tool_start(line: str) -> bool:
    return bool(re.match(r"^Tool: \w+", line))


def is_input_start(line: str) -> bool:
    return bool(re.match(r"^Input: \{", line))


def is_line_numbered(line: str) -> bool:
    """Matches tool output like '     1→---' or '    12→text'"""
    return bool(re.match(r"^\s+\d+→", line))


def is_command_turn(lines: list) -> bool:
    """Check if a turn is just a /command invocation."""
    text = "\n".join(lines).strip()
    return "<command-name>" in text and len(text) < 500


def strip_control_chars(text: str) -> str:
    """Remove non-printable control characters except newline and tab."""
    return re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)


def parse_turns(filepath: str):
    """Parse the export into (role, turn_number, lines) tuples."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    content = strip_control_chars(content)
    lines = content.split("\n")

    turns = []
    current_role = None
    current_num = None
    current_lines = []

    header_re = re.compile(r"^### (User|Assistant|System) \(Turn (\d+)\)")

    for line in lines:
        m = header_re.match(line)
        if m:
            if current_role is not None:
                turns.append((current_role, current_num, current_lines))
            current_role = m.group(1)
            current_num = int(m.group(2))
            current_lines = []
        elif current_role is not None:
            current_lines.append(line)

    if current_role is not None:
        turns.append((current_role, current_num, current_lines))

    return turns


def is_md_tool_start(line: str) -> bool:
    """Matches markdown-formatted tool calls like **Tool:** `Read`"""
    return bool(re.match(r"^\*\*Tool:\*\*\s*`\w+`", line))


def is_md_result_start(line: str) -> bool:
    """Matches **Result:**"""
    return bool(re.match(r"^\*\*Result:\*\*", line))


def clean_assistant_turn(lines: list) -> list:
    """Remove tool calls and their output from an assistant turn.

    Strategy: join all lines, then use regex to strip tool blocks.
    This is more robust than line-by-line parsing since tool output
    comes in many formats (raw, markdown-fenced, bare file paths, etc.)
    """
    cleaned = []
    i = 0
    skip_mode = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detect tool block starts
        if (is_tool_start(line) or is_md_tool_start(line)
                or stripped.startswith("Input: {")
                or is_md_result_start(line)):
            skip_mode = True
            i += 1
            continue

        # Inside a fence block while skipping
        if skip_mode and stripped.startswith("```"):
            i += 1  # skip opening fence
            while i < len(lines) and not lines[i].strip().startswith("```"):
                i += 1
            if i < len(lines):
                i += 1  # skip closing fence
            continue

        # Line-numbered tool output
        if is_line_numbered(line):
            skip_mode = True
            i += 1
            continue

        # Bare file paths (Glob output)
        if re.match(r"^[A-Z]:\\Users\\", line) and skip_mode:
            i += 1
            continue

        # "No files/matches found" artifacts
        if re.match(r"^(No (files|matches) found|Found \d+ (files|matches))", stripped):
            i += 1
            continue

        # Empty lines during skip mode — keep skipping
        if skip_mode and stripped == "":
            i += 1
            continue

        # JSON fragments (orphaned from tool input blocks)
        if skip_mode and re.match(r'^\s*["{\[}\]]', stripped):
            i += 1
            continue

        # Closing brace/bracket on its own line
        if skip_mode and stripped in ("}", "]", "},", "],"):
            i += 1
            continue

        # Non-empty, non-tool line — stop skipping
        skip_mode = False
        cleaned.append(line)
        i += 1

    # Collapse excessive blank lines
    result = "\n".join(cleaned)
    result = re.sub(r"\n{4,}", "\n\n\n", result)
    return result.split("\n")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.md> [output.md] [--start-turn N] [--end-turn N]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None

    # Parse optional turn range
    start_turn = 0
    end_turn = float("inf")
    for i, arg in enumerate(sys.argv):
        if arg == "--start-turn" and i + 1 < len(sys.argv):
            start_turn = int(sys.argv[i + 1])
        if arg == "--end-turn" and i + 1 < len(sys.argv):
            end_turn = int(sys.argv[i + 1])

    if output_path is None:
        stem = Path(input_path).stem
        output_path = str(Path(input_path).parent / f"{stem}_clean.md")

    turns = parse_turns(input_path)
    print(f"Parsed {len(turns)} turns from {input_path}")

    user_count = sum(1 for r, _, _ in turns if r == "User")
    assistant_count = sum(1 for r, _, _ in turns if r == "Assistant")
    system_count = sum(1 for r, _, _ in turns if r == "System")
    print(f"  User: {user_count}, Assistant: {assistant_count}, System: {system_count}")

    output_lines = []
    kept = 0
    skipped_system = 0
    skipped_command = 0

    for role, turn_num, lines in turns:
        if turn_num < start_turn or turn_num > end_turn:
            continue

        # Drop system turns
        if role == "System":
            skipped_system += 1
            continue

        # Drop /command turns
        if role == "User" and is_command_turn(lines):
            skipped_command += 1
            continue

        # Clean assistant turns
        if role == "Assistant":
            lines = clean_assistant_turn(lines)

        text = "\n".join(lines).strip()
        if not text:
            continue

        output_lines.append(f"## {role}")
        output_lines.append("")
        output_lines.append(text)
        output_lines.append("")
        kept += 1

    output_text = "\n".join(output_lines)
    Path(output_path).write_text(output_text, encoding="utf-8")

    print(f"\nOutput: {output_path}")
    print(f"Kept {kept} turns, skipped {skipped_system} system + {skipped_command} command turns")
    print(f"Output size: {len(output_text):,} chars")


if __name__ == "__main__":
    main()
