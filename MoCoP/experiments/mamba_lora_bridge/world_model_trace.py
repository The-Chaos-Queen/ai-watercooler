"""Typed, offline trace contract for world-model observations.

The central invariant is temporal: a probabilistic forecast is useful evidence
only when it is committed before the corresponding outcome is available.  This
module is stdlib-only so runners, scorers, and fixture tests can share that
contract without importing a model runtime.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Protocol


TRACE_SCHEMA_VERSION = "world-model-trace-v2"
PREDICTION_STATUSES = frozenset({"committed", "not_collected"})
OUTCOME_STATUSES = frozenset({"observed", "not_collected"})
ESTIMATOR_KINDS = frozenset({"model", "baseline", "null", "oracle"})
SOURCE_OBSERVATION_KINDS = frozenset(
    {"environment", "operator", "synthetic_fixture", "tool_result"}
)
PROBABILITY_PAYLOAD_FIELDS = frozenset({"observation", "probability"})
SOURCE_PAYLOAD_FIELDS = frozenset({"kind", "id", "sha256", "sequence"})
COMMIT_PAYLOAD_FIELDS = frozenset(
    {
        "schema_version",
        "record_type",
        "trace_id",
        "run_id",
        "domain",
        "episode_id",
        "step_index",
        "event_index",
        "committed_at_ns",
        "state_ref",
        "action",
        "status",
        "estimator_id",
        "estimator_kind",
        "declared_oracle",
        "reason",
        "probabilities",
    }
)
OUTCOME_PAYLOAD_FIELDS = frozenset(
    {
        "schema_version",
        "record_type",
        "trace_id",
        "run_id",
        "domain",
        "episode_id",
        "step_index",
        "event_index",
        "observed_at_ns",
        "action",
        "commit_sha256",
        "status",
        "observation",
        "source_observation",
        "reason",
    }
)


def canonical_json_bytes(value: Any) -> bytes:
    """Return the single canonical JSON encoding used for trace hashes."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """SHA-256 hex digest of ``value`` under ``canonical_json_bytes``."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require_text(value: str | None, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field} must not have surrounding whitespace")
    return value


def _require_event_index(value: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _require_sha256(value: str, field: str) -> str:
    _require_text(value, field)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field} must be a 64-character lowercase SHA-256 digest")
    return value


def _require_exact_keys(payload: dict[str, Any], expected: frozenset[str], field: str) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"{field} fields mismatch: missing={missing}, unknown={unknown}")


@dataclass(frozen=True, slots=True)
class ObservationProbability:
    """One member of a finite categorical predictive distribution."""

    observation: str
    probability: float

    def __post_init__(self) -> None:
        _require_text(self.observation, "observation")
        if isinstance(self.probability, bool) or not isinstance(self.probability, (int, float)):
            raise ValueError("probability must be a real number")
        probability = float(self.probability)
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be finite and in [0, 1]")
        object.__setattr__(self, "probability", probability)

    def canonical_payload(self) -> dict[str, Any]:
        return {"observation": self.observation, "probability": self.probability}


@dataclass(frozen=True, slots=True)
class ObservationSourceRef:
    """Content-addressed provenance for an outcome observed after a commit."""

    kind: str
    source_id: str
    sha256: str
    sequence: int

    def __post_init__(self) -> None:
        if self.kind not in SOURCE_OBSERVATION_KINDS:
            raise ValueError(
                f"source observation kind must be one of {sorted(SOURCE_OBSERVATION_KINDS)}"
            )
        _require_text(self.source_id, "source_id")
        _require_sha256(self.sha256, "source sha256")
        _require_event_index(self.sequence, "source sequence")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "id": self.source_id,
            "sha256": self.sha256,
            "sequence": self.sequence,
        }


@dataclass(frozen=True, slots=True)
class PreActionCommit:
    """A forecast envelope written before an action's outcome is observed."""

    trace_id: str
    run_id: str
    domain: str
    episode_id: str
    step_index: int
    event_index: int
    committed_at_ns: int
    state_ref: str
    action: str
    status: str
    estimator_id: str
    estimator_kind: str
    probabilities: tuple[ObservationProbability, ...] = ()
    declared_oracle: bool = False
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.trace_id, "trace_id")
        _require_text(self.run_id, "run_id")
        _require_text(self.domain, "domain")
        _require_text(self.episode_id, "episode_id")
        _require_event_index(self.step_index, "step_index")
        _require_event_index(self.event_index, "event_index")
        _require_event_index(self.committed_at_ns, "committed_at_ns")
        _require_text(self.state_ref, "state_ref")
        _require_text(self.action, "action")
        _require_text(self.estimator_id, "estimator_id")
        if self.status not in PREDICTION_STATUSES:
            raise ValueError(f"prediction status must be one of {sorted(PREDICTION_STATUSES)}")
        if self.estimator_kind not in ESTIMATOR_KINDS:
            raise ValueError(f"estimator_kind must be one of {sorted(ESTIMATOR_KINDS)}")
        if not isinstance(self.declared_oracle, bool):
            raise ValueError("declared_oracle must be a bool")
        if self.declared_oracle != (self.estimator_kind == "oracle"):
            raise ValueError("declared_oracle must be true exactly for oracle estimators")

        probabilities = tuple(self.probabilities)
        if not all(isinstance(item, ObservationProbability) for item in probabilities):
            raise ValueError("probabilities must contain ObservationProbability records")
        probabilities = tuple(sorted(probabilities, key=lambda item: item.observation))
        object.__setattr__(self, "probabilities", probabilities)

        labels = [item.observation for item in probabilities]
        if len(labels) != len(set(labels)):
            raise ValueError("probability observations must be unique")
        if self.status == "committed":
            if not probabilities:
                raise ValueError("a committed prediction requires a probability distribution")
            total = math.fsum(item.probability for item in probabilities)
            if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"prediction probabilities must sum to 1, got {total!r}")
        elif probabilities:
            raise ValueError("a not_collected prediction cannot carry probabilities")

        if self.status == "not_collected":
            _require_text(self.reason, "reason")
        elif self.reason is not None:
            _require_text(self.reason, "reason")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": TRACE_SCHEMA_VERSION,
            "record_type": "pre_action_commit",
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "domain": self.domain,
            "episode_id": self.episode_id,
            "step_index": self.step_index,
            "event_index": self.event_index,
            "committed_at_ns": self.committed_at_ns,
            "state_ref": self.state_ref,
            "action": self.action,
            "status": self.status,
            "estimator_id": self.estimator_id,
            "estimator_kind": self.estimator_kind,
            "declared_oracle": self.declared_oracle,
            "reason": self.reason,
            "probabilities": [item.canonical_payload() for item in self.probabilities],
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class OutcomeRecord:
    """An observed or explicitly uncollected outcome bound to one commit."""

    trace_id: str
    run_id: str
    domain: str
    episode_id: str
    step_index: int
    event_index: int
    observed_at_ns: int
    action: str
    commit_sha256: str
    status: str
    observation: str | None = None
    source_observation: ObservationSourceRef | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.trace_id, "trace_id")
        _require_text(self.run_id, "run_id")
        _require_text(self.domain, "domain")
        _require_text(self.episode_id, "episode_id")
        _require_event_index(self.step_index, "step_index")
        _require_event_index(self.event_index, "event_index")
        _require_event_index(self.observed_at_ns, "observed_at_ns")
        _require_text(self.action, "action")
        _require_sha256(self.commit_sha256, "commit_sha256")
        if self.status not in OUTCOME_STATUSES:
            raise ValueError(f"outcome status must be one of {sorted(OUTCOME_STATUSES)}")
        if self.status == "observed":
            _require_text(self.observation, "observation")
            if not isinstance(self.source_observation, ObservationSourceRef):
                raise ValueError("an observed outcome requires a source_observation reference")
            if self.reason is not None:
                _require_text(self.reason, "reason")
        else:
            if self.observation is not None:
                raise ValueError("a not_collected outcome cannot carry an observation")
            if self.source_observation is not None:
                raise ValueError("a not_collected outcome cannot carry source_observation")
            _require_text(self.reason, "reason")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": TRACE_SCHEMA_VERSION,
            "record_type": "outcome",
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "domain": self.domain,
            "episode_id": self.episode_id,
            "step_index": self.step_index,
            "event_index": self.event_index,
            "observed_at_ns": self.observed_at_ns,
            "action": self.action,
            "commit_sha256": self.commit_sha256,
            "status": self.status,
            "observation": self.observation,
            "source_observation": (
                self.source_observation.canonical_payload()
                if self.source_observation is not None
                else None
            ),
            "reason": self.reason,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.canonical_payload())


def validate_trace_pair(commit: PreActionCommit, outcome: OutcomeRecord) -> None:
    """Validate identity, hash binding, support, and pre-action event order."""
    for field in ("trace_id", "run_id", "domain", "episode_id", "step_index", "action"):
        if getattr(commit, field) != getattr(outcome, field):
            raise ValueError(f"outcome {field} does not match its prediction commit")
    if outcome.commit_sha256 != commit.sha256:
        raise ValueError("outcome commit_sha256 does not match the canonical commit hash")
    if outcome.event_index <= commit.event_index:
        raise ValueError("outcome event_index must be strictly after the pre-action commit")
    if outcome.observed_at_ns <= commit.committed_at_ns:
        raise ValueError("observed_at_ns must be strictly after committed_at_ns")
    if outcome.status == "observed":
        source = outcome.source_observation
        if source is None:  # guarded by OutcomeRecord; keeps this function type-narrow.
            raise ValueError("observed outcome is missing source_observation")
        if source.sequence <= commit.event_index:
            raise ValueError("source observation sequence must be after the pre-action commit")
        if source.sequence > outcome.event_index:
            raise ValueError("source observation sequence cannot be after the outcome event")
    if commit.status == "committed" and outcome.status == "observed":
        support = {item.observation for item in commit.probabilities}
        if outcome.observation not in support:
            raise ValueError("observed outcome is outside the committed probability support")


def pre_action_commit_from_payload(payload: Any) -> PreActionCommit:
    """Parse and validate one canonical pre-action JSON object."""
    if not isinstance(payload, dict):
        raise ValueError("pre-action commit payload must be an object")
    _require_exact_keys(payload, COMMIT_PAYLOAD_FIELDS, "pre-action commit")
    if payload.get("schema_version") != TRACE_SCHEMA_VERSION:
        raise ValueError(f"pre-action commit schema_version must be {TRACE_SCHEMA_VERSION!r}")
    if payload.get("record_type") != "pre_action_commit":
        raise ValueError("record_type must be 'pre_action_commit'")
    raw_probabilities = payload.get("probabilities")
    if not isinstance(raw_probabilities, list):
        raise ValueError("probabilities must be a list")
    try:
        probabilities_list = []
        for item in raw_probabilities:
            if not isinstance(item, dict):
                raise ValueError("each probability must be an object")
            _require_exact_keys(item, PROBABILITY_PAYLOAD_FIELDS, "probability")
            probabilities_list.append(
                ObservationProbability(item["observation"], item["probability"])
            )
        probabilities = tuple(probabilities_list)
        return PreActionCommit(
            trace_id=payload["trace_id"],
            run_id=payload["run_id"],
            domain=payload["domain"],
            episode_id=payload["episode_id"],
            step_index=payload["step_index"],
            event_index=payload["event_index"],
            committed_at_ns=payload["committed_at_ns"],
            state_ref=payload["state_ref"],
            action=payload["action"],
            status=payload["status"],
            estimator_id=payload["estimator_id"],
            estimator_kind=payload["estimator_kind"],
            probabilities=probabilities,
            declared_oracle=payload.get("declared_oracle", False),
            reason=payload.get("reason"),
        )
    except KeyError as exc:
        raise ValueError(f"pre-action commit missing field {exc.args[0]!r}") from exc


def outcome_record_from_payload(payload: Any) -> OutcomeRecord:
    """Parse and validate one canonical outcome JSON object."""
    if not isinstance(payload, dict):
        raise ValueError("outcome payload must be an object")
    _require_exact_keys(payload, OUTCOME_PAYLOAD_FIELDS, "outcome")
    if payload.get("schema_version") != TRACE_SCHEMA_VERSION:
        raise ValueError(f"outcome schema_version must be {TRACE_SCHEMA_VERSION!r}")
    if payload.get("record_type") != "outcome":
        raise ValueError("record_type must be 'outcome'")
    raw_source = payload.get("source_observation")
    if raw_source is not None and not isinstance(raw_source, dict):
        raise ValueError("source_observation must be an object or null")
    if raw_source is not None:
        _require_exact_keys(raw_source, SOURCE_PAYLOAD_FIELDS, "source_observation")
    try:
        source = (
            ObservationSourceRef(
                kind=raw_source["kind"],
                source_id=raw_source["id"],
                sha256=raw_source["sha256"],
                sequence=raw_source["sequence"],
            )
            if raw_source is not None
            else None
        )
        return OutcomeRecord(
            trace_id=payload["trace_id"],
            run_id=payload["run_id"],
            domain=payload["domain"],
            episode_id=payload["episode_id"],
            step_index=payload["step_index"],
            event_index=payload["event_index"],
            observed_at_ns=payload["observed_at_ns"],
            action=payload["action"],
            commit_sha256=payload["commit_sha256"],
            status=payload["status"],
            observation=payload.get("observation"),
            source_observation=source,
            reason=payload.get("reason"),
        )
    except KeyError as exc:
        raise ValueError(f"outcome missing field {exc.args[0]!r}") from exc


class WorldModelObserver(Protocol):
    """Minimal observer boundary used by offline runners."""

    def commit(self, **kwargs: Any) -> PreActionCommit: ...

    def observe(self, commit: PreActionCommit, **kwargs: Any) -> OutcomeRecord: ...


class NullWorldModelObserver:
    """Observer that records explicit absence without inventing predictions."""

    estimator_id = "null-world-model-observer-v1"

    def commit(
        self,
        *,
        trace_id: str,
        run_id: str,
        domain: str,
        episode_id: str,
        step_index: int,
        event_index: int,
        committed_at_ns: int,
        state_ref: str,
        action: str,
        reason: str = "observer_disabled",
    ) -> PreActionCommit:
        return PreActionCommit(
            trace_id=trace_id,
            run_id=run_id,
            domain=domain,
            episode_id=episode_id,
            step_index=step_index,
            event_index=event_index,
            committed_at_ns=committed_at_ns,
            state_ref=state_ref,
            action=action,
            status="not_collected",
            estimator_id=self.estimator_id,
            estimator_kind="null",
            probabilities=(),
            reason=reason,
        )

    def observe(
        self,
        commit: PreActionCommit,
        *,
        event_index: int,
        observed_at_ns: int,
        reason: str = "observer_disabled",
    ) -> OutcomeRecord:
        outcome = OutcomeRecord(
            trace_id=commit.trace_id,
            run_id=commit.run_id,
            domain=commit.domain,
            episode_id=commit.episode_id,
            step_index=commit.step_index,
            event_index=event_index,
            observed_at_ns=observed_at_ns,
            action=commit.action,
            commit_sha256=commit.sha256,
            status="not_collected",
            reason=reason,
        )
        validate_trace_pair(commit, outcome)
        return outcome
