from autobiographical_memory import enrich_memory_metadata
from sleep_flush import validate_record


def test_validate_record_preserves_outer_queued_at_for_legacy_rows():
    record = {
        "queued_at": "2026-04-01T00:00:00Z",
        "content": "Legacy pending row with enough content to survive validation.",
        "metadata": {
            "memory_kind": "correction",
            "decision": "DISMISS",
        },
    }

    ok, content, metadata, reason = validate_record(1, record)

    assert ok is True
    assert reason == ""
    assert metadata["queued_at"] == "2026-04-01T00:00:00Z"

    enriched = enrich_memory_metadata(content, metadata)
    assert enriched["expiration"] == "2026-09-28T00:00:00Z"


def test_validate_record_does_not_override_metadata_creation_time():
    record = {
        "queued_at": "2026-04-01T00:00:00Z",
        "content": "Pending row with metadata timestamp that must remain authoritative.",
        "metadata": {
            "memory_kind": "correction",
            "timestamp": "2026-04-10T00:00:00Z",
            "decision": "DISMISS",
        },
    }

    ok, content, metadata, _reason = validate_record(2, record)

    assert ok is True
    assert metadata["timestamp"] == "2026-04-10T00:00:00Z"
    assert "queued_at" not in metadata

    enriched = enrich_memory_metadata(content, metadata)
    assert enriched["expiration"] == "2026-10-07T00:00:00Z"
