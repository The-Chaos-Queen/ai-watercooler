from __future__ import annotations

from pathlib import Path

from archivist_mamba.retrieve_cases import rank_cases
from archivist_mamba.schemas import EvidenceRef, MemoryCase


def case(case_id, summary, *, domain="meta", memory_type="case", agent="codex", status="active", authority="extracted", topics=None):
    applies_when = ["prior context matters"] if memory_type == "rule" else []
    if topics is None:
        topics = ["codex", "logs"]
    return MemoryCase(
        id=case_id,
        title=summary[:40],
        domain=domain,
        memory_type=memory_type,
        outcome="partial",
        authority=authority,
        status=status,
        agent=agent,
        project="mocop",
        topics=topics,
        summary=summary,
        applies_when=applies_when,
        confidence=0.8,
        evidence=[EvidenceRef(source_path="fixture.jsonl")],
    )


def test_rank_cases_prefers_query_overlap_and_active_status():
    cases = [
        case("irrelevant", "A fiction character likes old libraries", domain="creative", memory_type="fiction", agent="claude", topics=["fiction", "libraries"]),
        case("stale", "Codex old logs retrieval rule", status="superseded"),
        case("active", "Codex should avoid old logs archaeology by default", memory_type="rule"),
    ]

    ranked = rank_cases("Codex old logs", cases, limit=2)

    assert [item.case.id for item in ranked] == ["active", "stale"]
    assert ranked[0].score > ranked[1].score


def test_rank_cases_honors_metadata_filters():
    cases = [
        case("codex", "Codex old logs", agent="codex"),
        case("claude", "Claude old logs", agent="claude"),
    ]

    ranked = rank_cases("old logs", cases, agent=["claude"])

    assert [item.case.id for item in ranked] == ["claude"]
