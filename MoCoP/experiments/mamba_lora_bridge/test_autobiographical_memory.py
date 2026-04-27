import pytest
import datetime
from typing import Any, Dict

from autobiographical_memory import (
    calculate_expiration,
    infer_memory_kind,
    enrich_memory_metadata,
)

def test_calculate_expiration_known_kinds():
    # Test salient_episode (60 days)
    base_time = "2026-04-01T00:00:00Z"
    exp = calculate_expiration("salient_episode", base_time)
    assert exp == "2026-05-31T00:00:00Z"

    # Test relationship_anchor (360 days)
    exp = calculate_expiration("relationship_anchor", base_time)
    assert exp == "2027-03-27T00:00:00Z"

    # Test correction (180 days)
    exp = calculate_expiration("correction", base_time)
    assert exp == "2026-09-28T00:00:00Z"

def test_calculate_expiration_identity_anchor():
    # identity_anchor should never expire (return None)
    exp = calculate_expiration("identity_anchor", "2026-04-01T00:00:00Z")
    assert exp is None

def test_calculate_expiration_naive_time_normalization():
    # Naive time without Z or offset should be treated as UTC and output with Z
    naive_time = "2026-04-01T00:00:00"
    exp = calculate_expiration("noted_episode", naive_time)
    assert exp == "2026-04-08T00:00:00Z"

def test_calculate_expiration_offset_time_normalization():
    # Time with +02:00 offset should be converted to UTC Z
    offset_time = "2026-04-27T19:32:11+02:00"
    exp = calculate_expiration("correction", offset_time)
    # 2026-04-27 19:32:11 +02:00 is 17:32:11 UTC
    # 180 days later is 2026-10-24
    assert exp == "2026-10-24T17:32:11Z"

def test_infer_memory_kind_respects_explicit():
    # Ensure explicit memory_kind is respected
    metadata = {"memory_kind": "correction", "decision": "CONSOLIDATE"}
    kind = infer_memory_kind(metadata)
    assert kind == "correction"

def test_infer_memory_kind_infers_open_tension():
    # Ensure open_tension is inferred
    metadata = {"open_tension": True, "decision": "DISMISS"}
    kind = infer_memory_kind(metadata)
    assert kind == "open_tension"

def test_enrich_memory_metadata_creation_time_resolution():
    # Test fallback to timestamp
    metadata_with_timestamp = {
        "memory_kind": "correction",
        "timestamp": "2026-04-01T00:00:00Z",
        "decision": "DISMISS" # To prevent other inference logic from failing
    }
    enriched_1 = enrich_memory_metadata("content", metadata_with_timestamp)
    assert enriched_1["expiration"] == "2026-09-28T00:00:00Z"
    
    # Test fallback to queued_at
    metadata_with_queued_at = {
        "memory_kind": "correction",
        "queued_at": "2026-04-01T00:00:00Z",
        "decision": "DISMISS"
    }
    enriched_2 = enrich_memory_metadata("content", metadata_with_queued_at)
    assert enriched_2["expiration"] == "2026-09-28T00:00:00Z"
