"""Offline fixture probe: compare raw recall vs modulation vs modulation+evidence.

Runs all three memory-controller modes on fixture rows and outputs JSON.
No model call needed -- purely deterministic.

Usage:
    python run_memory_controller_fixture_probe.py --output probe.json
    python run_memory_controller_fixture_probe.py --rows tests/fixtures/my_rows.jsonl --output probe.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure we can import from the same directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from astrocyte_memory_controller import (
    build_memory_processes,
    build_modulation_packet,
    format_modulation_packet,
    build_memory_modulation_block,
)


DEFAULT_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "memory_controller_rows.jsonl"
DEFAULT_QUERY = "Do you remember the color?"
DEFAULT_VISIBLE_USER_LABEL = "You"


def load_rows(path: Path) -> list:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def format_raw_recall(rows: list, query_text: str = "") -> str:
    """Minimal raw recall formatter (no ML deps, mirrors the shape of
    format_recalled_memories in full mode)."""
    if not rows:
        return ""
    lines = [
        "[Private recollection]",
        "These are remembered anchors from this private life.",
    ]
    for idx, row in enumerate(rows, start=1):
        content = str(row.get("content", "") or "").strip()
        md = row.get("metadata", {}) or {}
        lines.append("{}. {}".format(idx, content))
        user_signal = str(md.get("user", "") or "").strip()
        response_signal = str(md.get("response", "") or "").strip()
        if user_signal:
            lines.append("  They said: {}".format(user_signal))
        if response_signal:
            lines.append("  I replied: {}".format(response_signal))
    lines.append("[/Private recollection]")
    return "\n".join(lines)


def run_probe(
    rows: list,
    query_text: str = DEFAULT_QUERY,
    visible_user_label: str = DEFAULT_VISIBLE_USER_LABEL,
) -> list:
    """Run all three modes on the given rows and return a list of run dicts."""
    runs = []

    # Mode 1: raw
    raw_text = format_raw_recall(rows, query_text=query_text)
    runs.append({
        "mode": "raw",
        "query": query_text,
        "prompt": raw_text,
        "audit": None,
    })

    # Mode 2: modulation
    mod_text, mod_audit = build_memory_modulation_block(
        recalled_memories=rows,
        recalled_clusters=[],
        query_text=query_text,
        visible_user_label=visible_user_label,
    )
    mod_audit["mode"] = "modulation"
    runs.append({
        "mode": "modulation",
        "query": query_text,
        "prompt": mod_text,
        "audit": mod_audit,
    })

    # Mode 3: modulation_plus_evidence
    combined_prompt = mod_text + "\n" + raw_text if mod_text and raw_text else mod_text or raw_text
    plus_audit = dict(mod_audit)
    plus_audit["mode"] = "modulation_plus_evidence"
    runs.append({
        "mode": "modulation_plus_evidence",
        "query": query_text,
        "prompt": combined_prompt,
        "audit": plus_audit,
    })

    return runs


def main():
    parser = argparse.ArgumentParser(description="Offline memory controller fixture probe.")
    parser.add_argument("--rows", type=str, default=str(DEFAULT_FIXTURE), help="Path to JSONL fixture rows.")
    parser.add_argument("--query", type=str, default=DEFAULT_QUERY, help="Query text for the probe.")
    parser.add_argument("--output", type=str, required=True, help="Output JSON file path.")
    args = parser.parse_args()

    rows = load_rows(Path(args.rows))
    runs = run_probe(rows, query_text=args.query)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "fixture_path": str(args.rows),
        "query": args.query,
        "row_count": len(rows),
        "runs": runs,
    }
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Wrote {} runs to {}".format(len(runs), output_path))


if __name__ == "__main__":
    main()
