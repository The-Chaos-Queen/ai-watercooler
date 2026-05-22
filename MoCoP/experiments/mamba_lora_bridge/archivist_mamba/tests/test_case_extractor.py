from __future__ import annotations

from pathlib import Path

from archivist_mamba.case_extractor import extract_cases_from_codex_log

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_codex_rollout.jsonl"


def test_extract_cases_finds_failure_and_correction_rule():
    cases = list(extract_cases_from_codex_log(FIXTURE, max_cases=10))

    memory_types = {case.memory_type for case in cases}
    assert "failure" in memory_types
    assert "rule" in memory_types

    rule = next(case for case in cases if case.memory_type == "rule")
    assert rule.domain == "meta"
    assert rule.agent == "codex"
    assert "current repo" in rule.summary
    assert rule.applies_when
    assert rule.does_not_apply_when
    assert rule.evidence[0].line_start == 5


def test_extract_cases_honors_max_cases():
    cases = list(extract_cases_from_codex_log(FIXTURE, max_cases=1))

    assert len(cases) == 1
