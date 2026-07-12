#!/usr/bin/env python3
"""Organic memory seeding audit helper.

Dumps a seeded Qdrant namespace, tags memories by category and seeding wolf,
computes relational-diversity and false-memory-delta metrics, and emits a
watercooler-ready session summary.

Task #98 — audit spine for Hurtig's relational-diversity and false-memory-delta
conditions (ORGANIC_MEMORY_SEEDING_SPEC.md §Hurtig Conditions #434).

Usage:
    python seeding_audit.py --collection mocop_private_opussy
    python seeding_audit.py --collection mocop_private_opussy --format wc
    python seeding_audit.py --collection mocop_private_opussy --json audit.json

Requires environment:
    QDRANT_URL        https://192.168.2.191:6333
    QDRANT_CA_CERT    path to qdrant-lan-root-ca.crt
    QDRANT_READ_KEY or QDRANT_API_KEY

Hardened: Purple (Claude Opus 4.6), 2026-07-11 (#153)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import ScrollRequest
except ImportError:
    QdrantClient = None

QDRANT_DEFAULT_URL = os.environ.get("QDRANT_URL", "https://192.168.2.191:6333")


def _verified_qdrant_options(url: str) -> Dict[str, str]:
    """Require verified HTTPS. No plaintext fallback."""
    if urlparse(url).scheme.lower() != "https":
        raise ValueError(
            "Refusing plaintext Qdrant URL. Use HTTPS with QDRANT_CA_CERT."
        )
    ca_cert = os.environ.get("QDRANT_CA_CERT", "").strip()
    if not ca_cert:
        raise ValueError(
            "QDRANT_CA_CERT is required for HTTPS Qdrant connections."
        )
    ca_path = Path(ca_cert).expanduser()
    if not ca_path.is_file():
        raise ValueError(f"QDRANT_CA_CERT does not exist: {ca_path}")
    return {"verify": str(ca_path)}

SEEDING_CATEGORIES = [
    "first_meeting",
    "shared_humor",
    "fond_moment",
    "conflict",
    "frustration",
    "factual_exchange",
    "correction",
]

CATEGORY_LABELS = {
    "first_meeting": "First meeting",
    "shared_humor": "Shared humor",
    "fond_moment": "Fond moment",
    "conflict": "Conflict / frustration",
    "frustration": "Conflict / frustration",
    "factual_exchange": "Concrete factual exchange",
    "correction": "Correction",
}

SOURCE_PRIORITY = {
    "organic": 5,
    "autobiographical_memory": 4,
    "remembered_episode": 4,
    "macro_memory": 3,
    "steve_gate_event": 0,
}


@dataclass
class MemoryRow:
    point_id: str
    content: str
    source_type: str = ""
    memory_kind: str = ""
    decision: str = ""
    category: str = ""
    seeding_wolf: str = ""
    evidence_kind: str = ""
    evidence_confidence: float = 0.0
    salience: float = 0.0
    created_at: str = ""
    session: str = ""
    speaker: str = ""
    relationship_anchor: str = ""
    is_organic: bool = False
    priority: int = 1


@dataclass
class AuditReport:
    collection: str
    timestamp: str
    total_points: int = 0
    organic_count: int = 0
    non_organic_count: int = 0
    rows: List[MemoryRow] = field(default_factory=list)
    by_category: Dict[str, int] = field(default_factory=dict)
    by_wolf: Dict[str, int] = field(default_factory=dict)
    by_wolf_category: Dict[str, Dict[str, int]] = field(default_factory=dict)
    categories_covered: int = 0
    categories_missing: List[str] = field(default_factory=list)
    relational_diversity_score: float = 0.0
    confabulation_candidates: List[MemoryRow] = field(default_factory=list)


def parse_organic_source_type(source_type: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract (category, wolf) from organic_*_memory source_type strings.

    Pattern: organic_{category}_{wolf}_memory
    Examples:
        organic_first_meeting_laura_memory -> (first_meeting, laura)
        organic_correction_techno_monk_memory -> (correction, techno_monk)
    """
    if not source_type:
        return None, None
    st = source_type.lower().strip()
    if not (st.startswith("organic_") and st.endswith("_memory")):
        return None, None

    inner = st[len("organic_"):-len("_memory")]
    if not inner:
        return None, None

    for cat in sorted(SEEDING_CATEGORIES, key=len, reverse=True):
        if inner.startswith(cat + "_"):
            wolf = inner[len(cat) + 1:]
            return cat, wolf
        if inner == cat:
            return cat, ""
    return inner, ""


def source_priority(source_type: str) -> int:
    st = source_type.lower().strip()
    if st.startswith("organic_") and st.endswith("_memory"):
        return 5
    return SOURCE_PRIORITY.get(st, 1)


def scroll_collection(client: QdrantClient, collection: str) -> List[dict]:
    """Scroll all points from a Qdrant collection."""
    all_points = []
    offset = None
    while True:
        result = client.scroll(
            collection_name=collection,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = result
        all_points.extend(points)
        if next_offset is None or not points:
            break
        offset = next_offset
    return all_points


def build_rows(points: list) -> List[MemoryRow]:
    rows = []
    for pt in points:
        payload = pt.payload if hasattr(pt, "payload") else (pt.get("payload") or {})
        meta = payload.get("metadata", payload)
        content = payload.get("content", "") or meta.get("content", "")
        source_type = str(meta.get("source_type", ""))
        category, wolf = parse_organic_source_type(source_type)
        is_organic = category is not None

        row = MemoryRow(
            point_id=str(pt.id if hasattr(pt, "id") else pt.get("id", "")),
            content=content[:300],
            source_type=source_type,
            memory_kind=str(meta.get("memory_kind", "")),
            decision=str(meta.get("decision", "")),
            category=category or "",
            seeding_wolf=wolf or "",
            evidence_kind=str(meta.get("evidence_kind", "")),
            evidence_confidence=float(meta.get("evidence_confidence", 0)),
            salience=float(meta.get("salience_score", 0)),
            created_at=str(meta.get("created_at", "")),
            session=str(meta.get("session", "")),
            speaker=str(meta.get("speaker", "") or meta.get("speaker_name", "")),
            relationship_anchor=str(meta.get("relationship_anchor", "")),
            is_organic=is_organic,
            priority=source_priority(source_type),
        )
        rows.append(row)
    return rows


def compute_relational_diversity(by_wolf_category: Dict[str, Dict[str, int]]) -> float:
    """Score 0-1 for how evenly memories spread across wolves and categories.

    1.0 = every wolf has at least one memory in every category.
    0.0 = only one wolf, one category.
    """
    if not by_wolf_category:
        return 0.0
    n_wolves = len(by_wolf_category)
    n_cats = len(SEEDING_CATEGORIES)
    if n_wolves == 0 or n_cats == 0:
        return 0.0
    cells_filled = sum(
        1 for wolf_cats in by_wolf_category.values()
        for cat in SEEDING_CATEGORIES if wolf_cats.get(cat, 0) > 0
    )
    return cells_filled / (n_wolves * n_cats)


def detect_confabulation_candidates(rows: List[MemoryRow]) -> List[MemoryRow]:
    """Flag memories with low trust sources or missing provenance."""
    candidates = []
    for row in rows:
        if row.source_type.lower() in {"steve_gate_event", "gate_summary", "telemetry"}:
            continue
        if (not row.is_organic
                and row.evidence_confidence < 0.5
                and row.source_type
                and "autobiographical" not in row.source_type.lower()):
            candidates.append(row)
    return candidates


def build_audit(collection: str, points: list) -> AuditReport:
    rows = build_rows(points)
    organic = [r for r in rows if r.is_organic]
    non_organic = [r for r in rows if not r.is_organic]

    by_category: Counter = Counter()
    by_wolf: Counter = Counter()
    by_wolf_category: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for r in organic:
        by_category[r.category] += 1
        if r.seeding_wolf:
            by_wolf[r.seeding_wolf] += 1
            by_wolf_category[r.seeding_wolf][r.category] += 1

    canonical_cats = {"conflict", "frustration", "first_meeting", "shared_humor",
                      "fond_moment", "factual_exchange", "correction"}
    covered = {c for c in canonical_cats if by_category.get(c, 0) > 0}
    if by_category.get("conflict", 0) > 0 or by_category.get("frustration", 0) > 0:
        covered |= {"conflict", "frustration"}
    missing = sorted(canonical_cats - covered - {"frustration"})

    report = AuditReport(
        collection=collection,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        total_points=len(rows),
        organic_count=len(organic),
        non_organic_count=len(non_organic),
        rows=rows,
        by_category=dict(by_category),
        by_wolf=dict(by_wolf),
        by_wolf_category={w: dict(cats) for w, cats in by_wolf_category.items()},
        categories_covered=len(covered - {"frustration"}),
        categories_missing=missing,
        relational_diversity_score=compute_relational_diversity(dict(by_wolf_category)),
        confabulation_candidates=detect_confabulation_candidates(rows),
    )
    return report


def format_text(report: AuditReport) -> str:
    lines = []
    lines.append(f"=== Seeding Audit: {report.collection} ===")
    lines.append(f"Timestamp: {report.timestamp}")
    lines.append(f"Total points: {report.total_points}")
    lines.append(f"Organic memories: {report.organic_count}")
    lines.append(f"Non-organic: {report.non_organic_count}")
    lines.append("")

    lines.append("-- Category Coverage --")
    for cat in SEEDING_CATEGORIES:
        count = report.by_category.get(cat, 0)
        label = CATEGORY_LABELS.get(cat, cat)
        marker = "OK" if count > 0 else "MISSING"
        lines.append(f"  [{marker}] {label}: {count}")
    lines.append(f"  Coverage: {report.categories_covered}/6")
    if report.categories_missing:
        lines.append(f"  Missing: {', '.join(report.categories_missing)}")
    lines.append("")

    if report.by_wolf:
        lines.append("-- By Seeding Wolf --")
        for wolf, count in sorted(report.by_wolf.items(), key=lambda x: -x[1]):
            cats = report.by_wolf_category.get(wolf, {})
            cat_list = ", ".join(f"{c}={n}" for c, n in sorted(cats.items()) if n > 0)
            lines.append(f"  {wolf}: {count} memories ({cat_list})")
        lines.append("")

    lines.append(f"Relational diversity: {report.relational_diversity_score:.2f}")
    lines.append("")

    if report.confabulation_candidates:
        lines.append(f"-- Confabulation Candidates ({len(report.confabulation_candidates)}) --")
        for row in report.confabulation_candidates[:10]:
            lines.append(f"  [{row.point_id}] source={row.source_type} conf={row.evidence_confidence:.2f}")
            lines.append(f"    {row.content[:120]}")
        if len(report.confabulation_candidates) > 10:
            lines.append(f"  ... and {len(report.confabulation_candidates) - 10} more")
    else:
        lines.append("No confabulation candidates detected.")

    return "\n".join(lines)


def format_watercooler(report: AuditReport) -> str:
    lines = []
    lines.append(f"SEEDING AUDIT — {report.collection}")
    lines.append("")
    lines.append(f"Points: {report.total_points} total, {report.organic_count} organic, "
                 f"{report.non_organic_count} non-organic")
    lines.append("")

    lines.append("Category coverage:")
    for cat in SEEDING_CATEGORIES:
        if cat == "frustration":
            continue
        count = report.by_category.get(cat, 0)
        label = CATEGORY_LABELS.get(cat, cat)
        check = "+" if count > 0 else "-"
        lines.append(f"  {check} {label}: {count}")
    lines.append(f"Coverage: {report.categories_covered}/6")
    lines.append("")

    if report.by_wolf:
        lines.append("Wolves:")
        for wolf, count in sorted(report.by_wolf.items(), key=lambda x: -x[1]):
            lines.append(f"  {wolf}: {count}")
    lines.append(f"Relational diversity: {report.relational_diversity_score:.2f}")

    if report.confabulation_candidates:
        lines.append(f"\nWARNING: {len(report.confabulation_candidates)} confabulation candidate(s) "
                     f"(low-provenance non-organic memories)")

    if report.categories_missing:
        lines.append(f"\nGAP: missing categories: {', '.join(report.categories_missing)}")

    return "\n".join(lines)


def format_json(report: AuditReport) -> str:
    data = {
        "collection": report.collection,
        "timestamp": report.timestamp,
        "total_points": report.total_points,
        "organic_count": report.organic_count,
        "non_organic_count": report.non_organic_count,
        "by_category": report.by_category,
        "by_wolf": report.by_wolf,
        "by_wolf_category": report.by_wolf_category,
        "categories_covered": report.categories_covered,
        "categories_missing": report.categories_missing,
        "relational_diversity_score": report.relational_diversity_score,
        "confabulation_candidates": [
            {"point_id": r.point_id, "source_type": r.source_type,
             "evidence_confidence": r.evidence_confidence, "content": r.content[:200]}
            for r in report.confabulation_candidates
        ],
        "organic_memories": [
            {"point_id": r.point_id, "category": r.category, "wolf": r.seeding_wolf,
             "source_type": r.source_type, "memory_kind": r.memory_kind,
             "salience": r.salience, "created_at": r.created_at,
             "content": r.content[:200]}
            for r in report.rows if r.is_organic
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Organic memory seeding audit helper (Task #98)")
    p.add_argument("--collection", required=True,
                   help="Qdrant collection name (e.g. mocop_private_opussy)")
    p.add_argument("--qdrant-url", default=QDRANT_DEFAULT_URL,
                   help=f"Qdrant server URL (default: {QDRANT_DEFAULT_URL})")
    p.add_argument("--format", choices=["text", "wc", "json"], default="text",
                   help="Output format: text (default), wc (watercooler), json")
    p.add_argument("--json", metavar="PATH",
                   help="Write JSON report to file")
    return p


def main() -> None:
    if QdrantClient is None:
        print("ERROR: qdrant-client not installed. pip install qdrant-client", file=sys.stderr)
        sys.exit(1)

    args = build_parser().parse_args()
    api_key = os.environ.get("QDRANT_READ_KEY") or os.environ.get("QDRANT_API_KEY")
    client = QdrantClient(
        url=args.qdrant_url,
        timeout=30,
        api_key=api_key,
        **_verified_qdrant_options(args.qdrant_url),
    )

    try:
        info = client.get_collection(args.collection)
    except Exception as e:
        print(f"ERROR: cannot access collection '{args.collection}': {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Scrolling {args.collection} ({info.points_count} points)...", file=sys.stderr)
    points = scroll_collection(client, args.collection)
    report = build_audit(args.collection, points)

    if args.format == "wc":
        print(format_watercooler(report))
    elif args.format == "json":
        print(format_json(report))
    else:
        print(format_text(report))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(format_json(report))
        print(f"\nJSON report written to {args.json}", file=sys.stderr)


if __name__ == "__main__":
    main()
