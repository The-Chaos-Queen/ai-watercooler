from __future__ import annotations

import pytest

from archivist_mamba.schemas import EvidenceRef, MemoryCase, ValidationError, validate_case


def valid_case(**overrides):
    data = dict(
        id="case-1",
        title="Codex over-retrieves old logs",
        domain="meta",
        memory_type="case",
        outcome="partial",
        authority="extracted",
        status="active",
        agent="codex",
        project="mocop",
        topics=["codex", "retrieval"],
        summary="Codex searched historical logs when current repo inspection was enough.",
        confidence=0.7,
        evidence=[EvidenceRef(source_path="/tmp/session.jsonl", line_start=1, line_end=3, quote="Laura corrected this.")],
    )
    data.update(overrides)
    return MemoryCase(**data)


def test_valid_case_passes_validation():
    case = valid_case()

    validate_case(case)


def test_case_requires_evidence_ref():
    case = valid_case(evidence=[])

    with pytest.raises(ValidationError, match="evidence"):
        validate_case(case)


def test_case_confidence_must_be_unit_interval():
    case = valid_case(confidence=1.5)

    with pytest.raises(ValidationError, match="confidence"):
        validate_case(case)


def test_rule_case_requires_scope():
    case = valid_case(memory_type="rule", applies_when=[], does_not_apply_when=[])

    with pytest.raises(ValidationError, match="scope"):
        validate_case(case)


def test_roundtrip_preserves_nested_evidence():
    case = valid_case()

    restored = MemoryCase.from_json(case.to_json())

    assert restored == case
    assert restored.evidence[0].source_path == "/tmp/session.jsonl"
