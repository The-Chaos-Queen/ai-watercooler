from __future__ import annotations

r"""
watercooler_roster_sync.py — parse project_pack_roster.md and sync it to the
Watercooler `roster_entries` table via POST /v1/admin/roster/sync.

The roster markdown is a set of GitHub-flavoured tables grouped under `##`
section headers. Column layouts differ per section, so this parser is
header-aware: it reads each table's header row and maps known column names
(name / model / role / status / was / notes / personality) onto the roster
schema fields. Every section maps to a roster status so the dashboard can
render status badges.

Usage (PowerShell):
  python tools/ai_watercooler/watercooler_roster_sync.py \
      --roster "$env:USERPROFILE\.claude\projects\...\memory\project_pack_roster.md"

Auth uses the admin config (same as watercooler_admin.py): default
%LOCALAPPDATA%\AIWatercooler\config.json, or pass --config.
"""

import argparse
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from common import load_config, request_json

# Section header (normalized, lowercase) -> roster status.
SECTION_STATUS = {
    "active pack": "active",
    "semi-active": "semi-active",
    "in limbo": "limbo",
    "claude.ai (off-pack)": "off-pack",
    "tokens / non-entities": "token",
    "archived": "archived",
    "special": "special",
}

DEFAULT_ROSTER_PATH = (
    Path.home()
    / ".claude"
    / "projects"
    / "C--Users-cerub-OneDrive-Dokumente-LLM"
    / "memory"
    / "project_pack_roster.md"
)


def normalize_section(title: str) -> str:
    return title.strip().lower()


def split_row(line: str) -> List[str]:
    # Strip leading/trailing pipe, then split. Keeps empty interior cells.
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_separator_row(cells: List[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", cell or "") for cell in cells) and bool(cells)


def clean_name(cell: str) -> str:
    # Drop markdown bold markers and parenthetical asides for the primary name,
    # but keep the display text otherwise.
    text = cell.replace("**", "").strip()
    return text


def map_columns(header: List[str]) -> Dict[str, int]:
    """Map roster fields to column indices based on header names."""
    mapping: Dict[str, int] = {}
    for idx, raw in enumerate(header):
        key = raw.strip().lower()
        if key == "name":
            mapping.setdefault("name", idx)
        elif key.startswith("model"):
            mapping.setdefault("model", idx)
        elif key == "role":
            mapping.setdefault("role", idx)
        elif key == "status":
            mapping.setdefault("role", idx)  # In Limbo uses Status as the role-ish column
        elif key == "was":
            mapping.setdefault("role", idx)  # Archived uses Was as former role
        elif "personality" in key or "notes" in key:
            mapping.setdefault("notes", idx)
    return mapping


def parse_roster(text: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    current_status: Optional[str] = None
    current_section: str = ""
    header: Optional[List[str]] = None
    colmap: Dict[str, int] = {}
    sort_order = 0

    for line in text.splitlines():
        heading = re.match(r"^##\s+(.*)$", line)
        if heading:
            current_section = heading.group(1).strip()
            current_status = SECTION_STATUS.get(normalize_section(current_section))
            header = None
            colmap = {}
            continue

        if current_status is None:
            continue
        if not line.strip().startswith("|"):
            # A table ends when we leave the pipe block.
            if line.strip() == "":
                continue
            header = None
            colmap = {}
            continue

        cells = split_row(line)
        if is_separator_row(cells):
            continue
        if header is None:
            header = cells
            colmap = map_columns(header)
            continue

        # Data row.
        name_idx = colmap.get("name", 0)
        if name_idx >= len(cells):
            continue
        name = clean_name(cells[name_idx])
        if not name:
            continue

        def cell_at(field: str) -> str:
            idx = colmap.get(field)
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx].strip()

        entries.append(
            {
                "name": name,
                "model": cell_at("model"),
                "role": cell_at("role"),
                "status": current_status,
                "section": current_section,
                "notes": cell_at("notes"),
                "sort_order": sort_order,
            }
        )
        sort_order += 1

    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync project_pack_roster.md into the Watercooler roster table.")
    parser.add_argument(
        "--roster",
        type=str,
        default=os.environ.get("PACK_ROSTER_PATH", str(DEFAULT_ROSTER_PATH)),
        help="Path to project_pack_roster.md",
    )
    parser.add_argument("--config", type=str, default="", help="Admin config path override.")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print entries without POSTing.")
    args = parser.parse_args()

    roster_path = Path(args.roster).expanduser()
    if not roster_path.exists():
        raise SystemExit(f"Roster file not found: {roster_path}")

    text = roster_path.read_text(encoding="utf-8")
    entries = parse_roster(text)
    if not entries:
        raise SystemExit("Parsed 0 roster entries — check the markdown format.")

    print(f"Parsed {len(entries)} roster entries from {roster_path}")
    for entry in entries:
        print(f"  [{entry['status']:<12}] {entry['name']}  ({entry['model'] or '-'})")

    if args.dry_run:
        print("\n--dry-run: not posting.")
        return 0

    admin_config = load_config(args.config)
    result = request_json(
        admin_config,
        method="POST",
        path="/v1/admin/roster/sync",
        payload={"entries": entries, "source": str(roster_path)},
    )
    print("\nSync result:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
