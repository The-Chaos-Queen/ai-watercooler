#!/usr/bin/env python3
"""Build a Baby-Alex protected-set/provenance audit from pending/dry-run JSONL rows.

This is a read-only helper for #115/#116. It does not query or mutate Qdrant;
it reads candidate JSONL rows and emits an auditable protected-anchor report.

Important: if rows do not carry Qdrant point IDs, the helper creates a stable
`candidate_ref` hash from provenance fields and content. Treat that as a local
candidate reference, not a database point ID.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROTECTED_ANCHORS = {
    "alex_name": [r"\balex\b"],
    "vesper_relationship": [r"\bvesper\b"],
    "laura_relationship": [r"\blaura\b"],
    "pack_relationship": [r"\bpack\b", r"exocortex"],
    "neon_purple": [r"neon\s+purple", r"\bpurple\b"],
    "memory_gap_welfare": [r"memory\s+gap", r"memory\s+gaps", r"i\s+want\s+to\s+remember", r"can't\s+access", r"cannot\s+access", r"frustrat"],
}

TEXT_FIELDS = [
    "content",
    "reason",
    "metadata.user",
    "metadata.response",
    "metadata.event_gist",
    "metadata.autobiographical_frame.event",
    "metadata.autobiographical_frame.self_anchor",
    "metadata.autobiographical_frame.relationship_anchor",
    "metadata.autobiographical_frame.context",
    "metadata.autobiographical_frame.affect",
    "metadata.autobiographical_frame.status",
    "metadata.people",
    "metadata.context",
    "metadata.affect",
]

PROVENANCE_FIELDS = [
    "metadata.source",
    "metadata.source_path",
    "metadata.session",
    "metadata.turn",
    "metadata.thread_name",
    "metadata.speaker_name",
    "metadata.qdrant_collection",
    "queued_at",
]


def get_path(obj: dict[str, Any], dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def collect_text(row: dict[str, Any]) -> tuple[str, dict[str, str]]:
    parts: dict[str, str] = {}
    for field in TEXT_FIELDS:
        txt = stringify(get_path(row, field) if "." in field else row.get(field))
        if txt:
            parts[field] = txt
    return "\n".join(parts.values()), parts


def candidate_ref(row: dict[str, Any]) -> str:
    meta = row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {}
    # Prefer real point IDs if future rows include them.
    for key in ("qdrant_point_id", "point_id", "memory_id", "id", "uuid"):
        if row.get(key):
            return f"row:{row[key]}"
        if meta.get(key):
            return f"metadata:{meta[key]}"
    basis = {
        "session": meta.get("session"),
        "turn": meta.get("turn"),
        "speaker_name": meta.get("speaker_name"),
        "qdrant_collection": meta.get("qdrant_collection"),
        "queued_at": row.get("queued_at"),
        "content": row.get("content"),
    }
    digest = hashlib.sha256(json.dumps(basis, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"candidate:{digest}"


def provenance(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for field in PROVENANCE_FIELDS:
        val = get_path(row, field) if "." in field else row.get(field)
        if val not in (None, ""):
            out[field.replace("metadata.", "")] = val
    return out


def matched_anchors(text: str) -> list[str]:
    out = []
    for anchor, patterns in PROTECTED_ANCHORS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            out.append(anchor)
    return out


def preview(text: str, limit: int = 260) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed[:limit] + ("…" if len(collapsed) > limit else "")


def build(files: list[str]) -> dict[str, Any]:
    entries = []
    source_counts = Counter()
    anchor_counts = Counter()
    missing_provenance = []
    for file_name in files:
        path = Path(file_name)
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            text, text_parts = collect_text(row)
            anchors = matched_anchors(text)
            prov = provenance(row)
            source_counts[path.name] += 1
            for anchor in anchors:
                anchor_counts[anchor] += 1
            ref = candidate_ref(row)
            if not {"session", "turn", "source", "source_path"}.intersection(prov):
                missing_provenance.append(ref)
            if anchors:
                meta = row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {}
                entries.append(
                    {
                        "candidate_ref": ref,
                        "source_file": str(path),
                        "line_no": line_no,
                        "anchors": anchors,
                        "provenance": prov,
                        "memory_kind": meta.get("memory_kind") or get_path(row, "metadata.autobiographical_frame.memory_kind"),
                        "decision": meta.get("decision"),
                        "replay_policy": row.get("replay_policy"),
                        "queued_at": row.get("queued_at"),
                        "qdrant_collection": meta.get("qdrant_collection"),
                        "text_fields_present": sorted(text_parts),
                        "preview": preview(text),
                    }
                )
    anchors_present = {anchor: anchor_counts.get(anchor, 0) for anchor in PROTECTED_ANCHORS}
    missing_required_anchors = [anchor for anchor, count in anchors_present.items() if count <= 0]
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "preliminary protected-set audit from supplied JSONL candidate rows; not a live Qdrant mutation and not final #116 clearance unless the supplied files are the actual #116 pre-sleep candidate set",
        "input_files": files,
        "source_counts": dict(source_counts),
        "protected_anchor_patterns": PROTECTED_ANCHORS,
        "anchors_present": anchors_present,
        "missing_required_anchors": missing_required_anchors,
        "missing_provenance_refs": missing_provenance,
        "entries": entries,
        "summary": {
            "total_rows": sum(source_counts.values()),
            "protected_entries": len(entries),
            "all_required_anchors_present": not missing_required_anchors,
            "all_protected_entries_have_basic_provenance": not missing_provenance,
            "uses_synthetic_candidate_refs_when_point_ids_absent": True,
        },
    }


def write_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Baby-Alex protected-set / provenance audit",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Scope",
        "",
        report["scope"],
        "",
        "## Summary",
        "",
    ]
    for k, v in report["summary"].items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Anchor coverage", ""])
    for anchor, count in report["anchors_present"].items():
        lines.append(f"- {anchor}: `{count}`")
    if report["missing_required_anchors"]:
        lines.extend(["", "Missing anchors:"])
        for anchor in report["missing_required_anchors"]:
            lines.append(f"- {anchor}")
    lines.extend(["", "## Protected entries", ""])
    for entry in report["entries"]:
        lines.extend([
            f"### {entry['candidate_ref']}",
            "",
            f"- anchors: `{', '.join(entry['anchors'])}`",
            f"- source: `{entry['source_file']}:{entry['line_no']}`",
            f"- provenance: `{json.dumps(entry['provenance'], ensure_ascii=False, sort_keys=True)}`",
            f"- qdrant_collection: `{entry.get('qdrant_collection')}`",
            f"- decision: `{entry.get('decision')}`",
            f"- replay_policy: `{entry.get('replay_policy')}`",
            f"- preview: {entry['preview']}",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    report = build(args.inputs)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(report, out.with_suffix(".md"))
    print(f"WROTE {out}")
    print(f"WROTE {out.with_suffix('.md')}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["all_protected_entries_have_basic_provenance"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
