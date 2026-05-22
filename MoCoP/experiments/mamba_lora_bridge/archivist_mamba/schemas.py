from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Domain = Literal["work", "creative", "personal", "relationship", "research", "meta", "unknown"]
MemoryType = Literal[
    "case",
    "decision",
    "rule",
    "failure",
    "preference",
    "workflow",
    "reference",
    "fiction",
    "hypothesis",
    "open_question",
    "raw_summary",
]
Outcome = Literal["success", "failure", "partial", "unknown", "not_applicable"]
Authority = Literal["raw", "extracted", "curated", "canonical"]
Status = Literal["active", "superseded", "contested", "stale", "unknown"]

VALID_DOMAINS = set(Domain.__args__)  # type: ignore[attr-defined]
VALID_MEMORY_TYPES = set(MemoryType.__args__)  # type: ignore[attr-defined]
VALID_OUTCOMES = set(Outcome.__args__)  # type: ignore[attr-defined]
VALID_AUTHORITIES = set(Authority.__args__)  # type: ignore[attr-defined]
VALID_STATUSES = set(Status.__args__)  # type: ignore[attr-defined]


class ValidationError(ValueError):
    """Raised when a memory case violates the Archivist schema."""


@dataclass(frozen=True)
class EvidenceRef:
    source_path: str
    source_type: str = "unknown"
    turn_start: int | None = None
    turn_end: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    quote: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "EvidenceRef":
        return cls(**data)


@dataclass(frozen=True)
class MemoryCase:
    id: str
    title: str
    domain: Domain
    memory_type: MemoryType
    outcome: Outcome
    authority: Authority = "extracted"
    status: Status = "active"
    agent: str = "unknown"
    project: str = "unknown"
    topics: list[str] = field(default_factory=list)
    summary: str = ""
    conditions: list[str] = field(default_factory=list)
    attempt: str = ""
    result: str = ""
    failure_modes: list[str] = field(default_factory=list)
    applies_when: list[str] = field(default_factory=list)
    does_not_apply_when: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    contradicted_by: list[str] = field(default_factory=list)
    confidence: float = 0.5
    event_date: str = ""
    extracted_at: str = ""
    evidence: list[EvidenceRef] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "MemoryCase":
        payload = dict(data)
        payload["evidence"] = [
            item if isinstance(item, EvidenceRef) else EvidenceRef.from_json(item)
            for item in payload.get("evidence", [])
        ]
        return cls(**payload)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_case(case: MemoryCase) -> None:
    if not case.id.strip():
        raise ValidationError("id is required")
    if not case.title.strip():
        raise ValidationError("title is required")
    if not case.summary.strip():
        raise ValidationError("summary is required")
    if case.domain not in VALID_DOMAINS:
        raise ValidationError(f"invalid domain: {case.domain}")
    if case.memory_type not in VALID_MEMORY_TYPES:
        raise ValidationError(f"invalid memory_type: {case.memory_type}")
    if case.outcome not in VALID_OUTCOMES:
        raise ValidationError(f"invalid outcome: {case.outcome}")
    if case.authority not in VALID_AUTHORITIES:
        raise ValidationError(f"invalid authority: {case.authority}")
    if case.status not in VALID_STATUSES:
        raise ValidationError(f"invalid status: {case.status}")
    if not 0.0 <= float(case.confidence) <= 1.0:
        raise ValidationError("confidence must be between 0.0 and 1.0")
    if not case.evidence:
        raise ValidationError("at least one evidence ref is required")
    for ref in case.evidence:
        if not ref.source_path.strip():
            raise ValidationError("evidence source_path is required")
    if case.memory_type == "rule" and not (case.applies_when or case.does_not_apply_when):
        raise ValidationError("rule cases require scope via applies_when or does_not_apply_when")
