from __future__ import annotations

from dataclasses import FrozenInstanceError
import math

import pytest

from world_model_events import (
    EventSourceRef,
    SemanticRef,
    WorldEvent,
    validate_event_batch,
    world_event_from_payload,
)


def _source(
    source_id: str = "fixture-source", sequence: int = 0, digest_char: str = "a"
) -> EventSourceRef:
    return EventSourceRef(
        kind="synthetic_fixture",
        source_id=source_id,
        sha256=digest_char * 64,
        sequence=sequence,
    )


def _event(**overrides) -> WorldEvent:
    values = {
        "event_id": "event-1",
        "turn_index": 2,
        "event_index": 3,
        "kind": "threat_observed",
        "magnitude": 0.75,
        "confidence": 0.8,
        "attribution": "environment",
        "source": _source(),
        "semantic_refs": (
            SemanticRef("topic", "topic-private"),
            SemanticRef("person", "person-private"),
        ),
    }
    values.update(overrides)
    return WorldEvent(**values)


def test_world_event_roundtrip_is_canonical_and_immutable():
    event = _event()
    assert [item["kind"] for item in event.canonical_payload()["semantic_refs"]] == [
        "person",
        "topic",
    ]
    restored = world_event_from_payload(event.canonical_payload())
    assert restored == event
    assert restored.sha256 == event.sha256

    with pytest.raises(FrozenInstanceError):
        event.magnitude = 0.1


@pytest.mark.parametrize("location", ["event", "source", "semantic_ref"])
def test_payload_parser_rejects_unknown_fields_at_every_level(location):
    payload = _event().canonical_payload()
    if location == "event":
        payload["entity_id"] = "smuggled"
    elif location == "source":
        payload["source"]["topic"] = "smuggled"
    else:
        payload["semantic_refs"][0]["episode"] = "smuggled"

    with pytest.raises(ValueError, match="fields mismatch"):
        world_event_from_payload(payload)


@pytest.mark.parametrize("field", ["magnitude", "confidence"])
@pytest.mark.parametrize("value", [-0.01, 1.01, math.inf, -math.inf, math.nan, True])
def test_event_rejects_invalid_numeric_fields(field, value):
    with pytest.raises(ValueError):
        _event(**{field: value})


def test_event_rejects_unknown_enums_and_bad_source_digest():
    with pytest.raises(ValueError, match="event kind"):
        _event(kind="emotion_label")
    with pytest.raises(ValueError, match="attribution"):
        _event(attribution="laura")
    with pytest.raises(ValueError, match="semantic ref kind"):
        SemanticRef("hormone", "oxytocin")
    with pytest.raises(ValueError, match="SHA-256"):
        EventSourceRef("operator", "source", "not-a-digest", 0)


def test_event_rejects_duplicate_semantic_refs():
    ref = SemanticRef("person", "person-private")
    with pytest.raises(ValueError, match="duplicates"):
        _event(semantic_refs=(ref, ref))


def test_event_batch_has_one_order_and_rejects_duplicate_identity_or_position():
    first = _event(event_id="a", turn_index=1, event_index=2)
    second = _event(event_id="b", turn_index=1, event_index=1)
    assert validate_event_batch([first, second]) == (second, first)

    with pytest.raises(ValueError, match="event_id"):
        validate_event_batch([first, _event(event_id="a", turn_index=4, event_index=4)])
    with pytest.raises(ValueError, match="positions"):
        validate_event_batch([first, _event(event_id="c", turn_index=1, event_index=2)])


def test_event_batch_rejects_untyped_records():
    with pytest.raises(ValueError, match="WorldEvent"):
        validate_event_batch([_event(), {"kind": "threat_observed"}])
