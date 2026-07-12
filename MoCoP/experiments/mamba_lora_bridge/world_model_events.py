"""Strict semantic event contract for the World Model/controller boundary.

World events may identify people, rules, goals, topics, relationships, and
episodes. Those references stop at this module boundary. The deterministic
appraiser in ``modulatory_controller.py`` consumes only event kind, magnitude,
confidence, and attribution when constructing its numeric appraisal vector.

This module is stdlib-only and performs no model, Qdrant, or persistence work.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable

from world_model_trace import canonical_sha256


WORLD_EVENT_SCHEMA_VERSION = "world-event-v1"

WORLD_EVENT_KINDS = frozenset(
    {
        "affiliation_gain",
        "affiliation_loss",
        "control_available",
        "control_lost",
        "goal_blocked",
        "goal_progress",
        "norm_violation",
        "outcome_mismatch",
        "threat_cleared",
        "threat_observed",
    }
)
EVENT_ATTRIBUTIONS = frozenset({"environment", "other", "self", "unknown"})
SEMANTIC_REF_KINDS = frozenset(
    {"episode", "goal", "object", "person", "relationship", "rule", "topic"}
)
EVENT_SOURCE_KINDS = frozenset(
    {
        "environment",
        "memory",
        "operator",
        "synthetic_fixture",
        "tool_result",
        "world_model_trace",
    }
)

SEMANTIC_REF_FIELDS = frozenset({"kind", "id"})
EVENT_SOURCE_FIELDS = frozenset({"kind", "id", "sha256", "sequence"})
WORLD_EVENT_FIELDS = frozenset(
    {
        "schema_version",
        "event_id",
        "turn_index",
        "event_index",
        "kind",
        "magnitude",
        "confidence",
        "attribution",
        "source",
        "semantic_refs",
    }
)


def _require_exact_keys(
    payload: dict[str, Any], expected: frozenset[str], field: str
) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"{field} fields mismatch: missing={missing}, unknown={unknown}")


def _require_text(value: str | None, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field} must not have surrounding whitespace")
    return value


def _require_index(value: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _require_sha256(value: str, field: str) -> str:
    _require_text(value, field)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field} must be a 64-character lowercase SHA-256 digest")
    return value


def _require_unit_interval(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a real number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{field} must be finite and in [0, 1]")
    return result


@dataclass(frozen=True, slots=True)
class SemanticRef:
    """A semantic identifier that is forbidden beyond the appraisal boundary."""

    kind: str
    ref_id: str

    def __post_init__(self) -> None:
        if self.kind not in SEMANTIC_REF_KINDS:
            raise ValueError(
                f"semantic ref kind must be one of {sorted(SEMANTIC_REF_KINDS)}"
            )
        _require_text(self.ref_id, "semantic ref id")

    def canonical_payload(self) -> dict[str, Any]:
        return {"kind": self.kind, "id": self.ref_id}


@dataclass(frozen=True, slots=True)
class EventSourceRef:
    """Content-addressed provenance for a typed World Model event."""

    kind: str
    source_id: str
    sha256: str
    sequence: int

    def __post_init__(self) -> None:
        if self.kind not in EVENT_SOURCE_KINDS:
            raise ValueError(
                f"event source kind must be one of {sorted(EVENT_SOURCE_KINDS)}"
            )
        _require_text(self.source_id, "event source id")
        _require_sha256(self.sha256, "event source sha256")
        _require_index(self.sequence, "event source sequence")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "id": self.source_id,
            "sha256": self.sha256,
            "sequence": self.sequence,
        }


@dataclass(frozen=True, slots=True)
class WorldEvent:
    """One closed-world fact/event emitted at the semantic boundary."""

    event_id: str
    turn_index: int
    event_index: int
    kind: str
    magnitude: float
    confidence: float
    attribution: str
    source: EventSourceRef
    semantic_refs: tuple[SemanticRef, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.event_id, "event_id")
        _require_index(self.turn_index, "turn_index")
        _require_index(self.event_index, "event_index")
        if self.kind not in WORLD_EVENT_KINDS:
            raise ValueError(f"event kind must be one of {sorted(WORLD_EVENT_KINDS)}")
        object.__setattr__(
            self, "magnitude", _require_unit_interval(self.magnitude, "magnitude")
        )
        object.__setattr__(
            self, "confidence", _require_unit_interval(self.confidence, "confidence")
        )
        if self.attribution not in EVENT_ATTRIBUTIONS:
            raise ValueError(
                f"event attribution must be one of {sorted(EVENT_ATTRIBUTIONS)}"
            )
        if not isinstance(self.source, EventSourceRef):
            raise ValueError("source must be an EventSourceRef")

        refs = tuple(self.semantic_refs)
        if not all(isinstance(item, SemanticRef) for item in refs):
            raise ValueError("semantic_refs must contain SemanticRef records")
        refs = tuple(sorted(refs, key=lambda item: (item.kind, item.ref_id)))
        identities = [(item.kind, item.ref_id) for item in refs]
        if len(identities) != len(set(identities)):
            raise ValueError("semantic_refs must not contain duplicates")
        object.__setattr__(self, "semantic_refs", refs)

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": WORLD_EVENT_SCHEMA_VERSION,
            "event_id": self.event_id,
            "turn_index": self.turn_index,
            "event_index": self.event_index,
            "kind": self.kind,
            "magnitude": self.magnitude,
            "confidence": self.confidence,
            "attribution": self.attribution,
            "source": self.source.canonical_payload(),
            "semantic_refs": [item.canonical_payload() for item in self.semantic_refs],
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.canonical_payload())


def semantic_ref_from_payload(payload: Any) -> SemanticRef:
    if not isinstance(payload, dict):
        raise ValueError("semantic ref payload must be an object")
    _require_exact_keys(payload, SEMANTIC_REF_FIELDS, "semantic ref")
    return SemanticRef(kind=payload["kind"], ref_id=payload["id"])


def event_source_from_payload(payload: Any) -> EventSourceRef:
    if not isinstance(payload, dict):
        raise ValueError("event source payload must be an object")
    _require_exact_keys(payload, EVENT_SOURCE_FIELDS, "event source")
    return EventSourceRef(
        kind=payload["kind"],
        source_id=payload["id"],
        sha256=payload["sha256"],
        sequence=payload["sequence"],
    )


def world_event_from_payload(payload: Any) -> WorldEvent:
    """Parse a WorldEvent while rejecting missing, extra, or nested unknown fields."""
    if not isinstance(payload, dict):
        raise ValueError("world event payload must be an object")
    _require_exact_keys(payload, WORLD_EVENT_FIELDS, "world event")
    if payload.get("schema_version") != WORLD_EVENT_SCHEMA_VERSION:
        raise ValueError(
            f"world event schema_version must be {WORLD_EVENT_SCHEMA_VERSION!r}"
        )
    raw_refs = payload["semantic_refs"]
    if not isinstance(raw_refs, list):
        raise ValueError("semantic_refs must be a list")
    return WorldEvent(
        event_id=payload["event_id"],
        turn_index=payload["turn_index"],
        event_index=payload["event_index"],
        kind=payload["kind"],
        magnitude=payload["magnitude"],
        confidence=payload["confidence"],
        attribution=payload["attribution"],
        source=event_source_from_payload(payload["source"]),
        semantic_refs=tuple(semantic_ref_from_payload(item) for item in raw_refs),
    )


def validate_event_batch(events: Iterable[WorldEvent]) -> tuple[WorldEvent, ...]:
    """Return one deterministic event order and reject duplicate identities/positions."""
    records = tuple(events)
    if not all(isinstance(item, WorldEvent) for item in records):
        raise ValueError("events must contain WorldEvent records")

    event_ids = [item.event_id for item in records]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("event_id values must be unique within a batch")

    positions = [(item.turn_index, item.event_index) for item in records]
    if len(positions) != len(set(positions)):
        raise ValueError("turn_index/event_index positions must be unique within a batch")

    return tuple(
        sorted(records, key=lambda item: (item.turn_index, item.event_index, item.event_id))
    )
