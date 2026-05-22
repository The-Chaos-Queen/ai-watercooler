from __future__ import annotations

from pathlib import Path

from archivist_mamba.case_store import append_cases, filter_cases, iter_cases
from archivist_mamba.schemas import EvidenceRef, MemoryCase


def make_case(case_id="case-1", **overrides):
    data = dict(
        id=case_id,
        title="Codex retrieval correction",
        domain="meta",
        memory_type="case",
        outcome="partial",
        authority="extracted",
        status="active",
        agent="codex",
        project="mocop",
        topics=["codex", "retrieval"],
        summary="Codex should not search old logs by default.",
        confidence=0.8,
        evidence=[EvidenceRef(source_path="fixture.jsonl", line_start=2, line_end=5)],
    )
    data.update(overrides)
    return MemoryCase(**data)


def test_append_and_iter_cases_roundtrip(tmp_path: Path):
    path = tmp_path / "cases.jsonl"
    case = make_case()

    written = append_cases(path, [case])
    restored = list(iter_cases(path))

    assert written == 1
    assert restored == [case]


def test_append_cases_validates_before_writing(tmp_path: Path):
    path = tmp_path / "cases.jsonl"
    invalid = make_case(summary="")

    try:
        append_cases(path, [invalid])
    except ValueError:
        pass

    assert not path.exists()


def test_filter_cases_matches_domain_type_agent_status():
    cases = [
        make_case("a", domain="meta", memory_type="rule", agent="codex", status="active", applies_when=["prior context matters"]),
        make_case("b", domain="creative", memory_type="fiction", agent="claude", status="active"),
        make_case("c", domain="meta", memory_type="case", agent="codex", status="superseded"),
    ]

    filtered = list(filter_cases(cases, domain=["meta"], memory_type=["rule", "case"], agent=["codex"], status=["active"]))

    assert [case.id for case in filtered] == ["a"]
