"""Tests for the P0-4 provenance write-gate in autobiographical_memory.py.

The gate is a hard reject-on-missing-field guard on the Qdrant write path.
Gemma-era collections (mocop_gemma*) and MOCOP_PROVENANCE_STRICT=1 enforce
hard rejection; legacy collections warn-only so the running system is not
broken by the rollout.

Author: P0 security lane (OpenCLAW #138)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autobiographical_memory import (  # noqa: E402
    RECOMMENDED_PROVENANCE_FIELDS,
    REQUIRED_PROVENANCE_FIELDS,
    ProvenanceError,
    missing_provenance_fields,
    provenance_gate_is_strict,
    validate_provenance,
)


def _full_payload():
    """Full Tier 1 compliant payload with all 6 required fields."""
    return {
        "instance_id": "gemma_alex",
        "speaker_name": "Laura",
        "source_type": "organic_wolf_memory",
        "session_id": "session_2026_07_06",
        "created_at": "2026-07-06T12:00:00Z",
        "memory_kind": "attended_episode",
        "content": "a memory",
    }


# --------------------------------------------------------------------------- #
# missing_provenance_fields
# --------------------------------------------------------------------------- #

def test_full_payload_has_no_missing_fields():
    assert missing_provenance_fields(_full_payload()) == []


@pytest.mark.parametrize("field", REQUIRED_PROVENANCE_FIELDS)
def test_absent_field_is_missing(field):
    payload = _full_payload()
    del payload[field]
    assert missing_provenance_fields(payload) == [field]


@pytest.mark.parametrize("field", REQUIRED_PROVENANCE_FIELDS)
def test_none_field_is_missing(field):
    payload = _full_payload()
    payload[field] = None
    assert field in missing_provenance_fields(payload)


@pytest.mark.parametrize("field", REQUIRED_PROVENANCE_FIELDS)
def test_blank_string_field_is_missing(field):
    payload = _full_payload()
    payload[field] = "   "
    assert field in missing_provenance_fields(payload)


def test_empty_payload_reports_all_required():
    assert set(missing_provenance_fields({})) == set(REQUIRED_PROVENANCE_FIELDS)


# --------------------------------------------------------------------------- #
# strict-mode selection
# --------------------------------------------------------------------------- #

def test_gemma_collection_is_strict_by_name(monkeypatch):
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    assert provenance_gate_is_strict("mocop_gemma_private_alex") is True


def test_legacy_collection_is_lenient_by_name(monkeypatch):
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    assert provenance_gate_is_strict("mocop_private_vesper") is False
    assert provenance_gate_is_strict("exocortex") is False


def test_env_forces_strict(monkeypatch):
    monkeypatch.setenv("MOCOP_PROVENANCE_STRICT", "1")
    assert provenance_gate_is_strict("exocortex") is True


def test_env_forces_lenient(monkeypatch):
    monkeypatch.setenv("MOCOP_PROVENANCE_STRICT", "0")
    assert provenance_gate_is_strict("mocop_gemma_private_alex") is False


# --------------------------------------------------------------------------- #
# validate_provenance — the write gate
# --------------------------------------------------------------------------- #

def test_valid_payload_passes_gemma(monkeypatch):
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    assert validate_provenance(_full_payload(), collection_name="mocop_gemma_private_alex") == []


@pytest.mark.parametrize("field", REQUIRED_PROVENANCE_FIELDS)
def test_missing_field_rejected_on_gemma(field, monkeypatch):
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    del payload[field]
    with pytest.raises(ProvenanceError) as exc:
        validate_provenance(payload, collection_name="mocop_gemma_private_alex")
    assert field in str(exc.value)


def test_missing_field_warns_only_on_legacy(monkeypatch, caplog):
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    del payload["instance_id"]
    # Must NOT raise for a legacy collection; returns the missing list instead.
    missing = validate_provenance(payload, collection_name="mocop_private_vesper")
    assert missing == ["instance_id"]


def test_strict_env_rejects_even_legacy(monkeypatch):
    monkeypatch.setenv("MOCOP_PROVENANCE_STRICT", "1")
    payload = _full_payload()
    del payload["source_type"]
    with pytest.raises(ProvenanceError):
        validate_provenance(payload, collection_name="exocortex")


def test_explicit_strict_overrides_collection(monkeypatch):
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    del payload["speaker_name"]
    with pytest.raises(ProvenanceError):
        validate_provenance(payload, collection_name="legacy", strict=True)


def test_error_message_lists_all_missing(monkeypatch):
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    with pytest.raises(ProvenanceError) as exc:
        validate_provenance({"content": "x"}, collection_name="mocop_gemma_test")
    message = str(exc.value)
    for field in REQUIRED_PROVENANCE_FIELDS:
        assert field in message


# --------------------------------------------------------------------------- #
# Tier 2 recommended fields (warn-only)
# --------------------------------------------------------------------------- #

def test_missing_tier2_warns_but_does_not_block(monkeypatch, caplog):
    """Missing Tier 2 fields produce warnings but never block writes."""
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    # Tier 1 is complete but Tier 2 is empty — should pass and warn.
    validate_provenance(payload, collection_name="mocop_gemma_private_alex")
    # Check that warning was logged about missing Tier 2 fields.
    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING" and "recommended" in rec.message.lower()]
    assert len(warnings) > 0


def test_tier2_present_no_warning(monkeypatch, caplog):
    """When Tier 2 fields are present, no recommended-field warning."""
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    # Add all Tier 2 fields.
    for field in RECOMMENDED_PROVENANCE_FIELDS:
        payload[field] = f"test_{field}"
    validate_provenance(payload, collection_name="mocop_gemma_private_alex")
    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING" and "recommended" in rec.message.lower()]
    assert len(warnings) == 0


# --------------------------------------------------------------------------- #
# Field name aliases (backward compatibility)
# --------------------------------------------------------------------------- #

def test_session_alias_accepted(monkeypatch):
    """'session' is accepted as an alias for 'session_id'."""
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    del payload["session_id"]
    payload["session"] = "test_session"
    # Should pass without raising
    validate_provenance(payload, collection_name="mocop_gemma_private_alex")


def test_timestamp_alias_accepted(monkeypatch):
    """'timestamp' is accepted as an alias for 'created_at'."""
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    del payload["created_at"]
    payload["timestamp"] = "2026-07-06T12:00:00Z"
    # Should pass without raising
    validate_provenance(payload, collection_name="mocop_gemma_private_alex")


def test_queued_at_alias_accepted(monkeypatch):
    """'queued_at' is accepted as an alias for 'created_at'."""
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    del payload["created_at"]
    payload["queued_at"] = "2026-07-06T12:00:00Z"
    # Should pass without raising
    validate_provenance(payload, collection_name="mocop_gemma_private_alex")


def test_canonical_name_preferred_over_alias(monkeypatch):
    """When both canonical and alias present, both are valid."""
    monkeypatch.delenv("MOCOP_PROVENANCE_STRICT", raising=False)
    payload = _full_payload()
    payload["session"] = "alias_session"  # Also add the alias
    # Should still pass with both present
    validate_provenance(payload, collection_name="mocop_gemma_private_alex")
