"""Deterministic appraisal and modulatory-controller reference kernel.

The semantic World Model emits ``WorldEvent`` records. ``appraise_events`` maps
those records into a closed numeric vector. ``step_controller`` then updates a
small session-local kappa state and separate regulatory reserve/load state.

The controller accepts no text, entity identifiers, topics, episode identifiers,
embeddings, model handles, Qdrant clients, or persistence paths. It is a model-free
contract kernel, not runtime bridge integration.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import math
from typing import Any, Iterable

from world_model_events import WorldEvent, validate_event_batch


APPRAISAL_SCHEMA_VERSION = "appraisal-vector-v1"
KAPPA_SCHEMA_VERSION = "modulatory-kappa-v1"
REGULATORY_SCHEMA_VERSION = "regulatory-state-v1"
CONTROLLER_STEP_SCHEMA_VERSION = "modulatory-controller-step-v1"

APPRAISAL_FIELDS = frozenset(
    {
        "schema_version",
        "predicted_harm",
        "prediction_error",
        "controllability",
        "goal_progress",
        "norm_violation",
        "affiliation_delta",
    }
)
APPRAISAL_VALUE_FIELDS = APPRAISAL_FIELDS - {"schema_version"}
KAPPA_FIELDS = frozenset(
    {"schema_version", "affiliation", "agency", "vigilance"}
)
REGULATORY_FIELDS = frozenset({"schema_version", "reserve", "load"})


def _require_exact_keys(
    payload: dict[str, Any], expected: frozenset[str], field: str
) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"{field} fields mismatch: missing={missing}, unknown={unknown}")


def _require_range(value: float, low: float, high: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a real number")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{field} must be finite and in [{low}, {high}]")
    return result


def _require_text(value: str | None, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field} must not have surrounding whitespace")
    return value


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True, slots=True)
class AppraisalVector:
    """Content-free controller inputs derived from semantic events."""

    predicted_harm: float = 0.0
    prediction_error: float = 0.0
    controllability: float = 0.5
    goal_progress: float = 0.0
    norm_violation: float = 0.0
    affiliation_delta: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "predicted_harm",
            _require_range(self.predicted_harm, 0.0, 1.0, "predicted_harm"),
        )
        object.__setattr__(
            self,
            "prediction_error",
            _require_range(self.prediction_error, 0.0, 1.0, "prediction_error"),
        )
        object.__setattr__(
            self,
            "controllability",
            _require_range(self.controllability, 0.0, 1.0, "controllability"),
        )
        object.__setattr__(
            self,
            "goal_progress",
            _require_range(self.goal_progress, -1.0, 1.0, "goal_progress"),
        )
        object.__setattr__(
            self,
            "norm_violation",
            _require_range(self.norm_violation, 0.0, 1.0, "norm_violation"),
        )
        object.__setattr__(
            self,
            "affiliation_delta",
            _require_range(self.affiliation_delta, -1.0, 1.0, "affiliation_delta"),
        )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": APPRAISAL_SCHEMA_VERSION,
            "predicted_harm": self.predicted_harm,
            "prediction_error": self.prediction_error,
            "controllability": self.controllability,
            "goal_progress": self.goal_progress,
            "norm_violation": self.norm_violation,
            "affiliation_delta": self.affiliation_delta,
        }


@dataclass(frozen=True, slots=True)
class KappaState:
    """Turn-persistent, session-decaying control intensities."""

    affiliation: float = 0.0
    agency: float = 0.0
    vigilance: float = 0.0

    def __post_init__(self) -> None:
        for item in fields(self):
            object.__setattr__(
                self,
                item.name,
                _require_range(getattr(self, item.name), 0.0, 1.0, item.name),
            )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": KAPPA_SCHEMA_VERSION,
            "affiliation": self.affiliation,
            "agency": self.agency,
            "vigilance": self.vigilance,
        }


@dataclass(frozen=True, slots=True)
class RegulatoryState:
    """Versionable reserve/load values; this module does not persist them."""

    reserve: float = 1.0
    load: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "reserve", _require_range(self.reserve, 0.0, 1.0, "reserve")
        )
        object.__setattr__(self, "load", _require_range(self.load, 0.0, 1.0, "load"))

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": REGULATORY_SCHEMA_VERSION,
            "reserve": self.reserve,
            "load": self.load,
        }


@dataclass(frozen=True, slots=True)
class ControllerConfig:
    """Provisional engineering rates for the deterministic reference kernel."""

    affiliation_retention: float = 0.82
    affiliation_gain: float = 0.48
    affiliation_loss: float = 0.58
    repair_gain: float = 0.24
    agency_retention: float = 0.80
    agency_gain: float = 0.46
    agency_loss: float = 0.58
    vigilance_retention: float = 0.62
    vigilance_gain: float = 0.68
    vigilance_recovery: float = 0.30
    reserve_recovery: float = 0.08
    reserve_depletion: float = 0.12
    load_retention: float = 0.94
    load_gain: float = 0.12
    load_recovery: float = 0.07

    def __post_init__(self) -> None:
        for item in fields(self):
            _require_range(getattr(self, item.name), 0.0, 1.0, item.name)


DEFAULT_CONTROLLER_CONFIG = ControllerConfig()


@dataclass(frozen=True, slots=True)
class AppraisalAuditRecord:
    """Semantic-side audit link; never accepted by ``step_controller``."""

    event_id: str
    rule_id: str
    appraisal_field: str
    contribution: float

    def __post_init__(self) -> None:
        _require_text(self.event_id, "audit event_id")
        _require_text(self.rule_id, "audit rule_id")
        if self.appraisal_field not in APPRAISAL_VALUE_FIELDS:
            raise ValueError(
                f"audit appraisal_field must be one of {sorted(APPRAISAL_VALUE_FIELDS)}"
            )
        object.__setattr__(
            self,
            "contribution",
            _require_range(self.contribution, -1.0, 1.0, "audit contribution"),
        )


@dataclass(frozen=True, slots=True)
class AppraisalResult:
    """Numeric appraisal plus a separate inspectable rule-firing trace."""

    vector: AppraisalVector
    audit: tuple[AppraisalAuditRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.vector, AppraisalVector):
            raise ValueError("vector must be an AppraisalVector")
        audit = tuple(self.audit)
        if not all(isinstance(item, AppraisalAuditRecord) for item in audit):
            raise ValueError("audit must contain AppraisalAuditRecord records")
        object.__setattr__(self, "audit", audit)


@dataclass(frozen=True, slots=True)
class ControllerStep:
    """One controller transition with no semantic identifiers or audit records."""

    kappa: KappaState
    regulatory: RegulatoryState

    def __post_init__(self) -> None:
        if not isinstance(self.kappa, KappaState):
            raise ValueError("kappa must be a KappaState")
        if not isinstance(self.regulatory, RegulatoryState):
            raise ValueError("regulatory must be a RegulatoryState")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_STEP_SCHEMA_VERSION,
            "kappa": self.kappa.canonical_payload(),
            "regulatory": self.regulatory.canonical_payload(),
        }


def appraisal_from_payload(payload: Any) -> AppraisalVector:
    if not isinstance(payload, dict):
        raise ValueError("appraisal payload must be an object")
    _require_exact_keys(payload, APPRAISAL_FIELDS, "appraisal")
    if payload.get("schema_version") != APPRAISAL_SCHEMA_VERSION:
        raise ValueError(
            f"appraisal schema_version must be {APPRAISAL_SCHEMA_VERSION!r}"
        )
    return AppraisalVector(
        predicted_harm=payload["predicted_harm"],
        prediction_error=payload["prediction_error"],
        controllability=payload["controllability"],
        goal_progress=payload["goal_progress"],
        norm_violation=payload["norm_violation"],
        affiliation_delta=payload["affiliation_delta"],
    )


def kappa_from_payload(payload: Any) -> KappaState:
    if not isinstance(payload, dict):
        raise ValueError("kappa payload must be an object")
    _require_exact_keys(payload, KAPPA_FIELDS, "kappa")
    if payload.get("schema_version") != KAPPA_SCHEMA_VERSION:
        raise ValueError(f"kappa schema_version must be {KAPPA_SCHEMA_VERSION!r}")
    return KappaState(
        affiliation=payload["affiliation"],
        agency=payload["agency"],
        vigilance=payload["vigilance"],
    )


def regulatory_from_payload(payload: Any) -> RegulatoryState:
    if not isinstance(payload, dict):
        raise ValueError("regulatory payload must be an object")
    _require_exact_keys(payload, REGULATORY_FIELDS, "regulatory state")
    if payload.get("schema_version") != REGULATORY_SCHEMA_VERSION:
        raise ValueError(
            f"regulatory schema_version must be {REGULATORY_SCHEMA_VERSION!r}"
        )
    return RegulatoryState(reserve=payload["reserve"], load=payload["load"])


def appraise_events(events: Iterable[WorldEvent]) -> AppraisalResult:
    """Apply the frozen v1 rule table without reading semantic references."""
    records = validate_event_batch(events)
    harm = 0.0
    error = 0.0
    control_balance = 0.0
    goal_progress = 0.0
    norm_violation = 0.0
    affiliation_delta = 0.0
    audit: list[AppraisalAuditRecord] = []

    def record(
        event: WorldEvent, rule_id: str, appraisal_field: str, contribution: float
    ) -> None:
        audit.append(
            AppraisalAuditRecord(
                event_id=event.event_id,
                rule_id=rule_id,
                appraisal_field=appraisal_field,
                contribution=contribution,
            )
        )

    for event in records:
        weighted = event.magnitude * event.confidence
        if event.kind == "threat_observed":
            harm += weighted
            record(event, "threat.raise_harm", "predicted_harm", weighted)
        elif event.kind == "threat_cleared":
            harm -= weighted
            record(event, "threat.clear_harm", "predicted_harm", -weighted)
        elif event.kind == "outcome_mismatch":
            error += weighted
            record(event, "outcome.raise_error", "prediction_error", weighted)
        elif event.kind == "control_available":
            control_balance += weighted
            record(event, "control.raise", "controllability", 0.5 * weighted)
        elif event.kind == "control_lost":
            control_balance -= weighted
            record(event, "control.lower", "controllability", -0.5 * weighted)
        elif event.kind == "goal_progress":
            goal_progress += weighted
            record(event, "goal.progress", "goal_progress", weighted)
        elif event.kind == "goal_blocked":
            goal_progress -= weighted
            record(event, "goal.blocked", "goal_progress", -weighted)
        elif event.kind == "norm_violation":
            contribution = weighted if event.attribution == "self" else 0.0
            norm_violation += contribution
            rule_id = (
                "norm.self_violation"
                if event.attribution == "self"
                else "norm.non_self_no_guilt"
            )
            record(event, rule_id, "norm_violation", contribution)
        elif event.kind == "affiliation_gain":
            affiliation_delta += weighted
            record(event, "affiliation.gain", "affiliation_delta", weighted)
        elif event.kind == "affiliation_loss":
            affiliation_delta -= weighted
            record(event, "affiliation.loss", "affiliation_delta", -weighted)

    vector = AppraisalVector(
        predicted_harm=_clip(harm),
        prediction_error=_clip(error),
        controllability=_clip(0.5 + 0.5 * control_balance),
        goal_progress=_clip(goal_progress, -1.0, 1.0),
        norm_violation=_clip(norm_violation),
        affiliation_delta=_clip(affiliation_delta, -1.0, 1.0),
    )
    return AppraisalResult(vector=vector, audit=tuple(audit))


def begin_session(regulatory: RegulatoryState | None = None) -> ControllerStep:
    """Reset session-local kappa while carrying only validated reserve/load values."""
    return ControllerStep(
        kappa=KappaState(),
        regulatory=regulatory if regulatory is not None else RegulatoryState(),
    )


def step_controller(
    kappa: KappaState,
    regulatory: RegulatoryState,
    appraisal: AppraisalVector,
    config: ControllerConfig = DEFAULT_CONTROLLER_CONFIG,
) -> ControllerStep:
    """Advance the bounded reference controller by one turn."""
    if not isinstance(kappa, KappaState):
        raise ValueError("kappa must be a KappaState")
    if not isinstance(regulatory, RegulatoryState):
        raise ValueError("regulatory must be a RegulatoryState")
    if not isinstance(appraisal, AppraisalVector):
        raise ValueError("appraisal must be an AppraisalVector")
    if not isinstance(config, ControllerConfig):
        raise ValueError("config must be a ControllerConfig")

    positive_affiliation = max(0.0, appraisal.affiliation_delta)
    negative_affiliation = max(0.0, -appraisal.affiliation_delta)
    repair_drive = appraisal.norm_violation * appraisal.controllability
    affiliation = _clip(
        config.affiliation_retention * kappa.affiliation
        + config.affiliation_gain * positive_affiliation
        + config.repair_gain * repair_drive
        - config.affiliation_loss * negative_affiliation
    )

    blocked_goal = max(0.0, -appraisal.goal_progress)
    control_need = max(
        appraisal.predicted_harm, blocked_goal, appraisal.norm_violation
    )
    agency_drive = appraisal.controllability * control_need
    agency_suppression = (1.0 - appraisal.controllability) * control_need
    agency = _clip(
        config.agency_retention * kappa.agency
        + config.agency_gain * agency_drive
        - config.agency_loss * agency_suppression
    )

    vigilance_drive = _clip(
        0.7 * appraisal.predicted_harm + 0.3 * appraisal.prediction_error
    )
    vigilance_recovery = (
        regulatory.reserve
        * (1.0 - vigilance_drive)
        * (1.0 - 0.5 * regulatory.load)
    )
    vigilance = _clip(
        config.vigilance_retention * kappa.vigilance
        + config.vigilance_gain * vigilance_drive
        - config.vigilance_recovery * vigilance_recovery
    )

    depletion_pressure = vigilance_drive * (
        0.25 + 0.75 * (1.0 - appraisal.controllability)
    )
    reserve_recovery = (
        (1.0 - vigilance_drive) * (1.0 - regulatory.load)
    )
    reserve = _clip(
        regulatory.reserve
        + config.reserve_recovery * reserve_recovery
        - config.reserve_depletion * depletion_pressure
    )

    unrecovered_activation = vigilance * (1.0 - appraisal.controllability)
    load = _clip(
        config.load_retention * regulatory.load
        + config.load_gain * unrecovered_activation
        - config.load_recovery
        * (1.0 - vigilance_drive)
        * regulatory.reserve
    )

    return ControllerStep(
        kappa=KappaState(
            affiliation=affiliation,
            agency=agency,
            vigilance=vigilance,
        ),
        regulatory=RegulatoryState(reserve=reserve, load=load),
    )
