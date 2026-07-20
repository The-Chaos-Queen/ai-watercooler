"""Model-free causal trace custody for World Model Phase 3a.

This module is additive.  The Phase 2 trace and capture modules are frozen into
existing evidence bundles and must remain byte-for-byte stable.

The journal is a directory of immutable, hash-chained records.  A controlled
executor is called only after both a pre-action commit and an execution handoff
have been durably published.  Recovery never guesses across the handoff/receipt
gap: it requires authoritative reconciliation or records ``execution_unknown``.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


JOURNAL_SCHEMA_VERSION = "world-model-causal-journal-v1"
ARTIFACT_SCHEMA_VERSION = "world-model-causal-artifact-v1"
ONTOLOGY_SCHEMA_VERSION = "world-model-outcome-ontology-v1"
EXECUTION_ID_SCHEMA_VERSION = "world-model-execution-id-v1"
ZERO_SHA256 = "0" * 64

PREDICTION_STATUSES = frozenset(
    {"collected", "not_applicable", "not_collected", "estimator_failed"}
)
PREDICTION_REASONS = frozenset(
    {
        "collection_not_requested",
        "estimator_error",
        "estimator_not_applicable",
        "observer_disabled",
    }
)
EXECUTION_DISPOSITIONS = frozenset({"executed", "not_executed", "execution_unknown"})
EXECUTION_REASONS = frozenset(
    {
        "adapter_failure",
        "adapter_unavailable",
        "authoritative_receipt",
        "executor_refused",
        "handoff_not_published",
        "reconciled_not_started",
        "reconciliation_indeterminate",
    }
)
OUTCOME_SUPPORT_STATUSES = frozenset(
    {"in_support", "declared_other", "unknown", "out_of_support"}
)
STEP_STATUSES = frozenset(
    {
        "not_committed",
        "committed_not_executed",
        "execution_unknown",
        "executed_outcome_missing",
        "complete",
    }
)
RUN_STATUSES = frozenset({"open", "complete", "held"})
RUN_REASONS = frozenset(
    {
        "all_steps_observed",
        "planned_steps_uncommitted",
        "action_not_executed",
        "execution_unknown",
        "executed_outcome_missing",
        "multiple_incomplete_conditions",
    }
)
RECORD_TYPES = frozenset(
    {
        "run_header",
        "pre_action_commit",
        "execution_handoff",
        "action_receipt",
        "execution_resolution",
        "outcome",
        "run_ledger",
    }
)
FAULT_POINTS = frozenset(
    {
        "after_pre_action_commit",
        "after_execution_handoff",
        "after_execute_before_receipt",
        "after_action_receipt",
        "after_outcome",
        "after_execution_resolution",
        "before_run_ledger",
        "after_run_ledger",
    }
)
ARTIFACT_KINDS = frozenset(
    {
        "action",
        "estimator",
        "estimator_config",
        "execution_receipt",
        "executor",
        "observation",
        "outcome_source",
        "run_manifest",
        "state",
    }
)

ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        "journal_id",
        "run_id",
        "domain",
        "sequence",
        "previous_record_sha256",
        "record_type",
        "body",
        "record_sha256",
    }
)
ARTIFACT_FIELDS = frozenset(
    {"artifact_kind", "artifact_id", "schema_version", "content", "byte_length", "sha256"}
)
ONTOLOGY_FIELDS = frozenset(
    {
        "ontology_id",
        "schema_version",
        "labels",
        "other_label",
        "unknown_label",
        "scoring_policy",
        "sha256",
    }
)
PROBABILITY_FIELDS = frozenset({"label", "probability"})
HEADER_FIELDS = frozenset(
    {
        "created_at_ns",
        "durability_profile",
        "expected_step_ids",
        "manifest",
        "plan_sha256",
    }
)
COMMIT_FIELDS = frozenset(
    {
        "step_id",
        "committed_at_ns",
        "execution_id",
        "state",
        "candidate_actions",
        "candidate_action_set_sha256",
        "selected_action_id",
        "selected_action_sha256",
        "estimator",
        "estimator_config",
        "executor",
        "ontology",
        "prediction_status",
        "prediction_reason",
        "probabilities",
    }
)
HANDOFF_FIELDS = frozenset(
    {
        "step_id",
        "commit_record_sha256",
        "execution_id",
        "selected_action_sha256",
        "executor_sha256",
        "handed_off_at_ns",
    }
)
RECEIPT_FIELDS = frozenset(
    {
        "step_id",
        "commit_record_sha256",
        "handoff_record_sha256",
        "execution_id",
        "disposition",
        "reason",
        "received_at_ns",
        "receipt",
        "observation",
        "outcome_source",
        "raw_outcome_label",
    }
)
RESOLUTION_FIELDS = frozenset(
    {
        "step_id",
        "commit_record_sha256",
        "handoff_record_sha256",
        "execution_id",
        "disposition",
        "reason",
        "resolved_at_ns",
    }
)
OUTCOME_FIELDS = frozenset(
    {
        "step_id",
        "commit_record_sha256",
        "receipt_record_sha256",
        "observed_at_ns",
        "raw_outcome_label",
        "support_status",
        "scoring_label",
        "observation_sha256",
        "outcome_source_sha256",
    }
)
LEDGER_FIELDS = frozenset(
    {
        "closed_at_ns",
        "run_status",
        "reason",
        "chain_head_before_ledger",
        "counts",
        "step_statuses",
    }
)
LEDGER_COUNT_FIELDS = frozenset(
    {
        "planned",
        "uncommitted",
        "committed",
        "executed",
        "not_executed",
        "execution_unknown",
        "outcomes",
        "in_support",
        "declared_other",
        "unknown",
        "out_of_support",
    }
)
STEP_LEDGER_FIELDS = frozenset({"step_id", "status", "terminal_record_sha256"})

_RECORD_NAME = re.compile(r"^(?P<sequence>[0-9]{8})-(?P<sha>[0-9a-f]{64})\.json$")
_TEMP_NAME = re.compile(r"^\.record-[0-9a-f]{32}\.tmp$")
_LOCK_NAME = ".writer.lock"
DURABILITY_PROFILES = frozenset(
    {"fsync-file+atomic-link", "fsync-file+atomic-link+fsync-directory"}
)


class CausalJournalError(RuntimeError):
    """The journal cannot preserve or verify its Phase 3a contract."""


class InjectedJournalCrash(BaseException):
    """Deterministic test-only process-crash boundary."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the canonical JSON encoding used by every Phase 3a digest."""
    _validate_json_value(value, "value")
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _validate_json_value(value: Any, field: str) -> None:
    value_type = type(value)
    if value is None or value_type in {bool, str}:
        return
    if value_type is int:
        return
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError(f"{field} contains a non-finite number")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _validate_json_value(item, f"{field}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{field} contains a non-string object key")
            _validate_json_value(item, f"{field}.{key}")
        return
    raise ValueError(f"{field} contains unsupported type {value_type.__name__}")


def _require_object(value: Any, fields: frozenset[str], field: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{field} must be an exact JSON object")
    if any(type(key) is not str for key in value):
        raise ValueError(f"{field} keys must be exact strings")
    actual = set(value)
    if actual != fields:
        raise ValueError(
            f"{field} fields mismatch: missing={sorted(fields - actual)}, "
            f"unknown={sorted(actual - fields)}"
        )
    return value


def _require_text(value: Any, field: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    return value


def _require_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _require_sha256(value: Any, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_exact_instance(value: Any, expected: type[Any], field: str) -> None:
    if type(value) is not expected:
        raise ValueError(f"{field} must be an exact {expected.__name__}")


@dataclass(frozen=True, slots=True, init=False)
class CanonicalArtifact:
    """An inline, content-addressed JSON artifact isolated from caller mutation."""

    artifact_kind: str
    artifact_id: str
    schema_version: str
    _content_json: str

    def __init__(
        self,
        artifact_kind: str,
        artifact_id: str,
        schema_version: str,
        content: Any,
    ) -> None:
        _require_text(artifact_kind, "artifact_kind")
        if artifact_kind not in ARTIFACT_KINDS:
            raise ValueError(f"artifact_kind must be one of {sorted(ARTIFACT_KINDS)}")
        _require_text(artifact_id, "artifact_id")
        _require_text(schema_version, "artifact schema_version")
        encoded = canonical_json_bytes(content).decode("utf-8")
        object.__setattr__(self, "artifact_kind", artifact_kind)
        object.__setattr__(self, "artifact_id", artifact_id)
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "_content_json", encoded)

    @property
    def content(self) -> Any:
        return json.loads(self._content_json)

    @property
    def byte_length(self) -> int:
        return len(self._content_json.encode("utf-8"))

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "content": self.content,
            "byte_length": self.byte_length,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self._hash_payload())

    def canonical_payload(self) -> dict[str, Any]:
        return {**self._hash_payload(), "sha256": self.sha256}

    @classmethod
    def from_payload(cls, payload: Any, *, field: str = "artifact") -> CanonicalArtifact:
        raw = _require_object(payload, ARTIFACT_FIELDS, field)
        artifact = cls(
            raw["artifact_kind"],
            raw["artifact_id"],
            raw["schema_version"],
            raw["content"],
        )
        _require_int(raw["byte_length"], f"{field} byte_length")
        _require_sha256(raw["sha256"], f"{field} sha256")
        if raw["byte_length"] != artifact.byte_length:
            raise ValueError(f"{field} byte_length does not match canonical content")
        if raw["sha256"] != artifact.sha256:
            raise ValueError(f"{field} sha256 does not match canonical content")
        return artifact


@dataclass(frozen=True, slots=True)
class OutcomeOntology:
    ontology_id: str
    labels: tuple[str, ...]
    other_label: str = "OTHER"
    unknown_label: str = "UNKNOWN"
    scoring_policy: str = "map-out-of-support-to-other-v1"

    def __post_init__(self) -> None:
        _require_text(self.ontology_id, "ontology_id")
        if type(self.labels) is not tuple or not self.labels:
            raise ValueError("ontology labels must be a non-empty exact tuple")
        for label in self.labels:
            _require_text(label, "ontology label")
        if len(self.labels) != len(set(self.labels)):
            raise ValueError("ontology labels must be unique")
        _require_text(self.other_label, "other_label")
        _require_text(self.unknown_label, "unknown_label")
        if self.other_label == self.unknown_label:
            raise ValueError("OTHER and UNKNOWN labels must be distinct")
        if self.other_label != "OTHER" or self.unknown_label != "UNKNOWN":
            raise ValueError("reserved ontology labels must be literal OTHER and UNKNOWN")
        if self.other_label not in self.labels or self.unknown_label not in self.labels:
            raise ValueError("ontology must contain its mandatory OTHER and UNKNOWN labels")
        _require_text(self.scoring_policy, "scoring_policy")
        if self.scoring_policy != "map-out-of-support-to-other-v1":
            raise ValueError("unsupported open-set scoring policy")

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "ontology_id": self.ontology_id,
            "schema_version": ONTOLOGY_SCHEMA_VERSION,
            "labels": list(self.labels),
            "other_label": self.other_label,
            "unknown_label": self.unknown_label,
            "scoring_policy": self.scoring_policy,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self._hash_payload())

    def canonical_payload(self) -> dict[str, Any]:
        return {**self._hash_payload(), "sha256": self.sha256}

    @classmethod
    def from_payload(cls, payload: Any) -> OutcomeOntology:
        raw = _require_object(payload, ONTOLOGY_FIELDS, "ontology")
        if raw["schema_version"] != ONTOLOGY_SCHEMA_VERSION:
            raise ValueError("ontology schema_version mismatch")
        labels = raw["labels"]
        if type(labels) is not list:
            raise ValueError("ontology labels must be a list")
        ontology = cls(
            ontology_id=raw["ontology_id"],
            labels=tuple(labels),
            other_label=raw["other_label"],
            unknown_label=raw["unknown_label"],
            scoring_policy=raw["scoring_policy"],
        )
        _require_sha256(raw["sha256"], "ontology sha256")
        if raw["sha256"] != ontology.sha256:
            raise ValueError("ontology sha256 mismatch")
        return ontology


@dataclass(frozen=True, slots=True)
class OutcomeProbability:
    label: str
    probability: float

    def __post_init__(self) -> None:
        _require_text(self.label, "probability label")
        if type(self.probability) not in {int, float}:
            raise ValueError("probability must be an exact int or float")
        probability = float(self.probability)
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be finite and in [0, 1]")
        object.__setattr__(self, "probability", probability)

    def canonical_payload(self) -> dict[str, Any]:
        return {"label": self.label, "probability": self.probability}


@dataclass(frozen=True, slots=True)
class Prediction:
    status: str
    probabilities: tuple[OutcomeProbability, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.status, "prediction status")
        if self.status not in PREDICTION_STATUSES:
            raise ValueError(f"prediction status must be one of {sorted(PREDICTION_STATUSES)}")
        if type(self.probabilities) is not tuple:
            raise ValueError("probabilities must be an exact tuple")
        for item in self.probabilities:
            _require_exact_instance(item, OutcomeProbability, "probability")
        ordered = tuple(sorted(self.probabilities, key=lambda item: item.label))
        object.__setattr__(self, "probabilities", ordered)
        labels = tuple(item.label for item in ordered)
        if len(labels) != len(set(labels)):
            raise ValueError("probability labels must be unique")
        if self.status == "collected":
            if self.reason is not None:
                raise ValueError("a collected prediction cannot carry a reason")
            total = math.fsum(item.probability for item in ordered)
            if not ordered or not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("collected probabilities must be non-empty and sum to 1")
        else:
            if ordered:
                raise ValueError("an uncollected prediction cannot carry probabilities")
            _require_text(self.reason, "prediction reason")
            if self.reason not in PREDICTION_REASONS:
                raise ValueError(
                    f"uncollected prediction reason must be one of {sorted(PREDICTION_REASONS)}"
                )

    def validate_for(self, ontology: OutcomeOntology) -> None:
        _require_exact_instance(ontology, OutcomeOntology, "ontology")
        if self.status != "collected":
            return
        labels = tuple(item.label for item in self.probabilities)
        if set(labels) != set(ontology.labels):
            raise ValueError("collected probabilities must cover the complete ontology")
        masses = {item.label: item.probability for item in self.probabilities}
        if masses[ontology.other_label] <= 0.0 or masses[ontology.unknown_label] <= 0.0:
            raise ValueError("OTHER and UNKNOWN must each receive positive committed mass")


@dataclass(frozen=True, slots=True)
class ExecutionEvidence:
    receipt: CanonicalArtifact
    observation: CanonicalArtifact
    outcome_source: CanonicalArtifact
    raw_outcome_label: str

    def __post_init__(self) -> None:
        for value, kind, field in (
            (self.receipt, "execution_receipt", "receipt"),
            (self.observation, "observation", "observation"),
            (self.outcome_source, "outcome_source", "outcome_source"),
        ):
            _require_exact_instance(value, CanonicalArtifact, field)
            if value.artifact_kind != kind:
                raise ValueError(f"{field} artifact_kind must be {kind!r}")
        _require_text(self.raw_outcome_label, "raw_outcome_label")


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """Commit-bound request handed to an authoritative action adapter."""

    execution_id: str
    commit_record_sha256: str
    step_id: str
    state_sha256: str
    candidate_action_set_sha256: str
    selected_action: CanonicalArtifact
    estimator_sha256: str
    estimator_config_sha256: str
    executor_sha256: str
    ontology_sha256: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.execution_id, "execution_id"),
            (self.commit_record_sha256, "commit_record_sha256"),
            (self.state_sha256, "state_sha256"),
            (self.candidate_action_set_sha256, "candidate_action_set_sha256"),
            (self.estimator_sha256, "estimator_sha256"),
            (self.estimator_config_sha256, "estimator_config_sha256"),
            (self.executor_sha256, "executor_sha256"),
            (self.ontology_sha256, "ontology_sha256"),
        ):
            _require_sha256(value, field)
        _require_text(self.step_id, "step_id")
        _require_exact_instance(self.selected_action, CanonicalArtifact, "selected_action")
        if self.selected_action.artifact_kind != "action":
            raise ValueError("selected_action artifact_kind must be 'action'")


@dataclass(frozen=True, slots=True)
class ActionResolution:
    disposition: str
    reason: str
    evidence: ExecutionEvidence | None = None

    def __post_init__(self) -> None:
        _require_text(self.disposition, "execution disposition")
        _require_text(self.reason, "execution reason")
        if self.disposition not in EXECUTION_DISPOSITIONS:
            raise ValueError(
                f"execution disposition must be one of {sorted(EXECUTION_DISPOSITIONS)}"
            )
        if self.reason not in EXECUTION_REASONS:
            raise ValueError(f"execution reason must be one of {sorted(EXECUTION_REASONS)}")
        if self.disposition == "executed":
            _require_exact_instance(self.evidence, ExecutionEvidence, "execution evidence")
            if self.reason != "authoritative_receipt":
                raise ValueError("executed disposition requires authoritative_receipt")
        elif self.evidence is not None:
            raise ValueError("non-executed dispositions cannot carry execution evidence")
        if self.disposition == "not_executed" and self.reason not in {
            "executor_refused",
            "handoff_not_published",
            "reconciled_not_started",
        }:
            raise ValueError("invalid not_executed reason")
        if self.disposition == "execution_unknown" and self.reason not in {
            "adapter_failure",
            "adapter_unavailable",
            "reconciliation_indeterminate",
        }:
            raise ValueError("invalid execution_unknown reason")


class DurableActionAdapter(Protocol):
    """Executor contract required to cross the external side-effect boundary."""

    def execute(self, request: ExecutionRequest) -> ActionResolution: ...

    def reconcile(self, request: ExecutionRequest) -> ActionResolution: ...


@dataclass(frozen=True, slots=True)
class ActionAdapterBinding:
    """Inert pre-handoff binding; the opaque adapter is touched only after handoff."""

    executor_artifact_sha256: str
    adapter: DurableActionAdapter

    def __post_init__(self) -> None:
        _require_sha256(self.executor_artifact_sha256, "executor_artifact_sha256")
        if self.adapter is None:
            raise ValueError("adapter binding requires an opaque adapter")


@dataclass(frozen=True, slots=True, init=False)
class VerifiedRecord:
    sequence: int
    record_type: str
    record_sha256: str
    previous_record_sha256: str
    _body_json: str

    def __init__(self, payload: dict[str, Any]) -> None:
        object.__setattr__(self, "sequence", payload["sequence"])
        object.__setattr__(self, "record_type", payload["record_type"])
        object.__setattr__(self, "record_sha256", payload["record_sha256"])
        object.__setattr__(self, "previous_record_sha256", payload["previous_record_sha256"])
        object.__setattr__(
            self,
            "_body_json",
            canonical_json_bytes(payload["body"]).decode("utf-8"),
        )

    @property
    def body(self) -> dict[str, Any]:
        value = json.loads(self._body_json)
        if type(value) is not dict:  # guarded by the record validators
            raise AssertionError("verified record body is not an object")
        return value


@dataclass(frozen=True, slots=True)
class StepSnapshot:
    step_id: str
    status: str
    commit: VerifiedRecord | None = None
    handoff: VerifiedRecord | None = None
    receipt: VerifiedRecord | None = None
    resolution: VerifiedRecord | None = None
    outcome: VerifiedRecord | None = None

    @property
    def terminal_record_sha256(self) -> str | None:
        for record in (self.outcome, self.resolution, self.receipt, self.handoff, self.commit):
            if record is not None:
                return record.record_sha256
        return None


@dataclass(frozen=True, slots=True)
class JournalSnapshot:
    journal_id: str
    run_id: str
    domain: str
    manifest_sha256: str
    expected_step_ids: tuple[str, ...]
    records: tuple[VerifiedRecord, ...]
    steps: tuple[StepSnapshot, ...]
    run_status: str
    reason: str | None
    chain_head: str

    @property
    def closed(self) -> bool:
        return self.run_status != "open"


@dataclass(frozen=True, slots=True)
class ScoringRow:
    step_id: str
    raw_outcome_label: str
    scoring_label: str
    support_status: str
    probabilities: tuple[OutcomeProbability, ...]
    commit_record_sha256: str
    receipt_record_sha256: str
    outcome_record_sha256: str


def _artifact(payload: Any, kind: str, field: str) -> CanonicalArtifact:
    artifact = CanonicalArtifact.from_payload(payload, field=field)
    if artifact.artifact_kind != kind:
        raise ValueError(f"{field} artifact_kind must be {kind!r}")
    return artifact


def _probabilities_from_payload(payload: Any) -> tuple[OutcomeProbability, ...]:
    if type(payload) is not list:
        raise ValueError("probabilities must be a list")
    probabilities: list[OutcomeProbability] = []
    for raw in payload:
        item = _require_object(raw, PROBABILITY_FIELDS, "probability")
        probabilities.append(OutcomeProbability(item["label"], item["probability"]))
    return tuple(probabilities)


def _validate_header(body: Any) -> tuple[CanonicalArtifact, tuple[str, ...]]:
    raw = _require_object(body, HEADER_FIELDS, "run_header body")
    _require_int(raw["created_at_ns"], "created_at_ns")
    if raw["durability_profile"] not in DURABILITY_PROFILES:
        raise ValueError("run_header durability_profile is not recognized")
    manifest = _artifact(raw["manifest"], "run_manifest", "manifest")
    step_ids = raw["expected_step_ids"]
    if type(step_ids) is not list or not step_ids:
        raise ValueError("expected_step_ids must be a non-empty list")
    for step_id in step_ids:
        _require_text(step_id, "expected step_id")
    if len(step_ids) != len(set(step_ids)):
        raise ValueError("expected_step_ids must be unique")
    expected_plan = canonical_sha256({"expected_step_ids": step_ids})
    _require_sha256(raw["plan_sha256"], "plan_sha256")
    if raw["plan_sha256"] != expected_plan:
        raise ValueError("plan_sha256 does not bind expected_step_ids")
    return manifest, tuple(step_ids)


def _validate_commit(body: Any) -> None:
    raw = _require_object(body, COMMIT_FIELDS, "pre_action_commit body")
    _require_text(raw["step_id"], "step_id")
    _require_int(raw["committed_at_ns"], "committed_at_ns")
    _require_sha256(raw["execution_id"], "execution_id")
    _artifact(raw["state"], "state", "state")
    candidates = raw["candidate_actions"]
    if type(candidates) is not list or not candidates:
        raise ValueError("candidate_actions must be a non-empty list")
    actions = tuple(_artifact(item, "action", "candidate action") for item in candidates)
    ids = tuple(action.artifact_id for action in actions)
    if len(ids) != len(set(ids)) or tuple(sorted(ids)) != ids:
        raise ValueError("candidate actions must have unique, sorted artifact IDs")
    expected_set_hash = canonical_sha256([action.canonical_payload() for action in actions])
    if raw["candidate_action_set_sha256"] != expected_set_hash:
        raise ValueError("candidate_action_set_sha256 mismatch")
    selected_id = _require_text(raw["selected_action_id"], "selected_action_id")
    selected = {action.artifact_id: action for action in actions}.get(selected_id)
    if selected is None or raw["selected_action_sha256"] != selected.sha256:
        raise ValueError("selected action does not resolve within candidate_actions")
    _artifact(raw["estimator"], "estimator", "estimator")
    _artifact(raw["estimator_config"], "estimator_config", "estimator_config")
    _artifact(raw["executor"], "executor", "executor")
    ontology = OutcomeOntology.from_payload(raw["ontology"])
    prediction = Prediction(
        status=raw["prediction_status"],
        reason=raw["prediction_reason"],
        probabilities=_probabilities_from_payload(raw["probabilities"]),
    )
    prediction.validate_for(ontology)
    if raw["probabilities"] != [
        item.canonical_payload() for item in prediction.probabilities
    ]:
        raise ValueError("probabilities must be in canonical label order")


def _derive_execution_id(
    *,
    journal_id: str,
    run_id: str,
    domain: str,
    step_id: str,
    state_sha256: str,
    candidate_action_set_sha256: str,
    selected_action_sha256: str,
    estimator_sha256: str,
    estimator_config_sha256: str,
    executor_sha256: str,
    ontology_sha256: str,
    prediction_status: str,
    prediction_reason: str | None,
    probabilities: list[dict[str, Any]],
) -> str:
    return canonical_sha256(
        {
            "schema_version": EXECUTION_ID_SCHEMA_VERSION,
            "journal_id": journal_id,
            "run_id": run_id,
            "domain": domain,
            "step_id": step_id,
            "state_sha256": state_sha256,
            "candidate_action_set_sha256": candidate_action_set_sha256,
            "selected_action_sha256": selected_action_sha256,
            "estimator_sha256": estimator_sha256,
            "estimator_config_sha256": estimator_config_sha256,
            "executor_sha256": executor_sha256,
            "ontology_sha256": ontology_sha256,
            "prediction_status": prediction_status,
            "prediction_reason": prediction_reason,
            "probabilities": probabilities,
        }
    )


def _execution_id_from_commit(
    *, journal_id: str, run_id: str, domain: str, body: dict[str, Any]
) -> str:
    state = CanonicalArtifact.from_payload(body["state"], field="state")
    estimator = CanonicalArtifact.from_payload(body["estimator"], field="estimator")
    config = CanonicalArtifact.from_payload(
        body["estimator_config"], field="estimator_config"
    )
    executor = CanonicalArtifact.from_payload(body["executor"], field="executor")
    ontology = OutcomeOntology.from_payload(body["ontology"])
    return _derive_execution_id(
        journal_id=journal_id,
        run_id=run_id,
        domain=domain,
        step_id=body["step_id"],
        state_sha256=state.sha256,
        candidate_action_set_sha256=body["candidate_action_set_sha256"],
        selected_action_sha256=body["selected_action_sha256"],
        estimator_sha256=estimator.sha256,
        estimator_config_sha256=config.sha256,
        executor_sha256=executor.sha256,
        ontology_sha256=ontology.sha256,
        prediction_status=body["prediction_status"],
        prediction_reason=body["prediction_reason"],
        probabilities=body["probabilities"],
    )


def _execution_request(commit: VerifiedRecord) -> ExecutionRequest:
    body = commit.body
    selected = next(
        CanonicalArtifact.from_payload(item, field="candidate action")
        for item in body["candidate_actions"]
        if item["artifact_id"] == body["selected_action_id"]
    )
    return ExecutionRequest(
        execution_id=body["execution_id"],
        commit_record_sha256=commit.record_sha256,
        step_id=body["step_id"],
        state_sha256=body["state"]["sha256"],
        candidate_action_set_sha256=body["candidate_action_set_sha256"],
        selected_action=selected,
        estimator_sha256=body["estimator"]["sha256"],
        estimator_config_sha256=body["estimator_config"]["sha256"],
        executor_sha256=body["executor"]["sha256"],
        ontology_sha256=body["ontology"]["sha256"],
    )


def _validate_handoff(body: Any, commit: VerifiedRecord) -> None:
    raw = _require_object(body, HANDOFF_FIELDS, "execution_handoff body")
    commit_body = commit.body
    for field in ("step_id", "execution_id", "selected_action_sha256"):
        if raw[field] != commit_body[field]:
            raise ValueError(f"handoff {field} does not match its commit")
    if raw["commit_record_sha256"] != commit.record_sha256:
        raise ValueError("handoff commit_record_sha256 mismatch")
    executor = CanonicalArtifact.from_payload(commit_body["executor"], field="executor")
    if raw["executor_sha256"] != executor.sha256:
        raise ValueError("handoff executor_sha256 mismatch")
    if _require_int(raw["handed_off_at_ns"], "handed_off_at_ns") <= commit_body[
        "committed_at_ns"
    ]:
        raise ValueError("handoff must occur after commit")


def _validate_receipt(
    body: Any, commit: VerifiedRecord, handoff: VerifiedRecord
) -> ExecutionEvidence:
    raw = _require_object(body, RECEIPT_FIELDS, "action_receipt body")
    commit_body = commit.body
    if raw["step_id"] != commit_body["step_id"] or raw["execution_id"] != commit_body[
        "execution_id"
    ]:
        raise ValueError("receipt identity does not match its commit")
    if raw["commit_record_sha256"] != commit.record_sha256:
        raise ValueError("receipt commit_record_sha256 mismatch")
    if raw["handoff_record_sha256"] != handoff.record_sha256:
        raise ValueError("receipt handoff_record_sha256 mismatch")
    if raw["disposition"] != "executed" or raw["reason"] != "authoritative_receipt":
        raise ValueError("action receipt must be an authoritative executed receipt")
    if _require_int(raw["received_at_ns"], "received_at_ns") <= handoff.body[
        "handed_off_at_ns"
    ]:
        raise ValueError("receipt must occur after handoff")
    return ExecutionEvidence(
        receipt=_artifact(raw["receipt"], "execution_receipt", "receipt"),
        observation=_artifact(raw["observation"], "observation", "observation"),
        outcome_source=_artifact(raw["outcome_source"], "outcome_source", "outcome_source"),
        raw_outcome_label=raw["raw_outcome_label"],
    )


def _validate_resolution(
    body: Any, commit: VerifiedRecord, handoff: VerifiedRecord | None
) -> None:
    raw = _require_object(body, RESOLUTION_FIELDS, "execution_resolution body")
    commit_body = commit.body
    if raw["step_id"] != commit_body["step_id"] or raw["execution_id"] != commit_body[
        "execution_id"
    ]:
        raise ValueError("execution resolution identity mismatch")
    if raw["commit_record_sha256"] != commit.record_sha256:
        raise ValueError("execution resolution commit hash mismatch")
    expected_handoff = handoff.record_sha256 if handoff is not None else None
    if raw["handoff_record_sha256"] != expected_handoff:
        raise ValueError("execution resolution handoff hash mismatch")
    disposition = raw["disposition"]
    reason = raw["reason"]
    ActionResolution(disposition=disposition, reason=reason)
    lower_bound = (
        handoff.body["handed_off_at_ns"]
        if handoff is not None
        else commit_body["committed_at_ns"]
    )
    if _require_int(raw["resolved_at_ns"], "resolved_at_ns") <= lower_bound:
        raise ValueError("execution resolution must occur after its preceding boundary")
    if handoff is None and (disposition, reason) != (
        "not_executed",
        "handoff_not_published",
    ):
        raise ValueError("a commit-only resolution must record handoff_not_published")
    if handoff is not None and reason == "handoff_not_published":
        raise ValueError("handoff_not_published is invalid after a durable handoff")


def _classify_outcome(
    ontology: OutcomeOntology, raw_label: str
) -> tuple[str, str]:
    if raw_label == ontology.unknown_label:
        return "unknown", ontology.unknown_label
    if raw_label == ontology.other_label:
        return "declared_other", ontology.other_label
    if raw_label in ontology.labels:
        return "in_support", raw_label
    return "out_of_support", ontology.other_label


def _validate_outcome(
    body: Any,
    commit: VerifiedRecord,
    receipt: VerifiedRecord,
    evidence: ExecutionEvidence,
) -> None:
    raw = _require_object(body, OUTCOME_FIELDS, "outcome body")
    if raw["step_id"] != commit.body["step_id"]:
        raise ValueError("outcome step_id mismatch")
    if raw["commit_record_sha256"] != commit.record_sha256:
        raise ValueError("outcome commit_record_sha256 mismatch")
    if raw["receipt_record_sha256"] != receipt.record_sha256:
        raise ValueError("outcome receipt_record_sha256 mismatch")
    if _require_int(raw["observed_at_ns"], "observed_at_ns") <= receipt.body[
        "received_at_ns"
    ]:
        raise ValueError("outcome must be recorded after its receipt")
    if raw["raw_outcome_label"] != evidence.raw_outcome_label:
        raise ValueError("outcome raw label does not match retained receipt evidence")
    ontology = OutcomeOntology.from_payload(commit.body["ontology"])
    expected_support, expected_label = _classify_outcome(ontology, evidence.raw_outcome_label)
    if raw["support_status"] != expected_support or raw["scoring_label"] != expected_label:
        raise ValueError("outcome open-set classification mismatch")
    if raw["observation_sha256"] != evidence.observation.sha256:
        raise ValueError("outcome observation hash mismatch")
    if raw["outcome_source_sha256"] != evidence.outcome_source.sha256:
        raise ValueError("outcome source hash mismatch")


def _ledger_rows(steps: tuple[StepSnapshot, ...]) -> list[dict[str, Any]]:
    return [
        {
            "step_id": step.step_id,
            "status": step.status,
            "terminal_record_sha256": step.terminal_record_sha256,
        }
        for step in steps
    ]


def _ledger_counts(steps: tuple[StepSnapshot, ...]) -> dict[str, int]:
    outcomes = [step.outcome.body for step in steps if step.outcome is not None]
    return {
        "planned": len(steps),
        "uncommitted": sum(step.status == "not_committed" for step in steps),
        "committed": sum(step.commit is not None for step in steps),
        "executed": sum(step.receipt is not None for step in steps),
        "not_executed": sum(step.status == "committed_not_executed" for step in steps),
        "execution_unknown": sum(step.status == "execution_unknown" for step in steps),
        "outcomes": len(outcomes),
        "in_support": sum(item["support_status"] == "in_support" for item in outcomes),
        "declared_other": sum(
            item["support_status"] == "declared_other" for item in outcomes
        ),
        "unknown": sum(item["support_status"] == "unknown" for item in outcomes),
        "out_of_support": sum(
            item["support_status"] == "out_of_support" for item in outcomes
        ),
    }


def _held_reason(steps: tuple[StepSnapshot, ...]) -> str:
    conditions: set[str] = set()
    for step in steps:
        if step.status == "not_committed":
            conditions.add("planned_steps_uncommitted")
        elif step.status == "committed_not_executed":
            conditions.add("action_not_executed")
        elif step.status == "execution_unknown":
            conditions.add("execution_unknown")
        elif step.status == "executed_outcome_missing":
            conditions.add("executed_outcome_missing")
    if len(conditions) == 1:
        return next(iter(conditions))
    return "multiple_incomplete_conditions"


def _validate_ledger(body: Any, steps: tuple[StepSnapshot, ...], previous_hash: str) -> str:
    raw = _require_object(body, LEDGER_FIELDS, "run_ledger body")
    _require_int(raw["closed_at_ns"], "closed_at_ns")
    if raw["run_status"] not in {"complete", "held"}:
        raise ValueError("closed run_status must be complete or held")
    if raw["reason"] not in RUN_REASONS:
        raise ValueError("run ledger reason is not recognized")
    if raw["chain_head_before_ledger"] != previous_hash:
        raise ValueError("run ledger does not bind the preceding chain head")
    counts = _require_object(raw["counts"], LEDGER_COUNT_FIELDS, "ledger counts")
    for field, value in counts.items():
        _require_int(value, f"ledger counts.{field}")
    expected_counts = _ledger_counts(steps)
    if counts != expected_counts:
        raise ValueError("run ledger counts do not match the verified step ledger")
    rows = raw["step_statuses"]
    if type(rows) is not list:
        raise ValueError("step_statuses must be a list")
    for row in rows:
        parsed = _require_object(row, STEP_LEDGER_FIELDS, "step ledger row")
        if parsed["status"] not in STEP_STATUSES:
            raise ValueError("step ledger row has an unknown status")
        if parsed["terminal_record_sha256"] is not None:
            _require_sha256(parsed["terminal_record_sha256"], "terminal_record_sha256")
    if rows != _ledger_rows(steps):
        raise ValueError("run ledger rows do not match the verified journal")
    complete = all(step.status == "complete" for step in steps)
    expected_status = "complete" if complete else "held"
    expected_reason = "all_steps_observed" if complete else _held_reason(steps)
    if raw["run_status"] != expected_status or raw["reason"] != expected_reason:
        raise ValueError("run ledger status/reason does not match its completeness state")
    if counts["outcomes"] != sum(
        counts[name] for name in ("in_support", "declared_other", "unknown", "out_of_support")
    ):
        raise ValueError("every retained outcome must appear in the scoring denominator")
    if counts["planned"] != counts["uncommitted"] + counts["committed"]:
        raise ValueError("planned-step ledger does not close")
    if counts["committed"] != sum(
        counts[name] for name in ("executed", "not_executed", "execution_unknown")
    ):
        raise ValueError("committed-step ledger does not close")
    if counts["executed"] != counts["outcomes"]:
        raise ValueError("every executed step must retain exactly one outcome")
    return raw["run_status"]


def _record_payload_without_hash(
    *,
    journal_id: str,
    run_id: str,
    domain: str,
    sequence: int,
    previous_record_sha256: str,
    record_type: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "journal_id": journal_id,
        "run_id": run_id,
        "domain": domain,
        "sequence": sequence,
        "previous_record_sha256": previous_record_sha256,
        "record_type": record_type,
        "body": body,
    }


def _verify_envelope(
    payload: Any,
    *,
    expected_sequence: int,
    expected_previous: str,
    journal_id: str | None,
    run_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    raw = _require_object(payload, ENVELOPE_FIELDS, "journal record")
    if raw["schema_version"] != JOURNAL_SCHEMA_VERSION:
        raise ValueError("journal schema_version mismatch")
    if raw["record_type"] not in RECORD_TYPES:
        raise ValueError("unknown journal record_type")
    _require_text(raw["journal_id"], "journal_id")
    _require_text(raw["run_id"], "run_id")
    _require_text(raw["domain"], "domain")
    _require_int(raw["sequence"], "record sequence")
    _require_sha256(raw["previous_record_sha256"], "previous_record_sha256")
    _require_sha256(raw["record_sha256"], "record_sha256")
    if raw["sequence"] != expected_sequence:
        raise ValueError("journal record sequence is non-monotonic")
    if raw["previous_record_sha256"] != expected_previous:
        raise ValueError("journal record hash chain is broken")
    if journal_id is not None and raw["journal_id"] != journal_id:
        raise ValueError("journal_id changed within journal")
    if run_id is not None and raw["run_id"] != run_id:
        raise ValueError("run_id changed within journal")
    if domain is not None and raw["domain"] != domain:
        raise ValueError("domain changed within journal")
    base = {key: raw[key] for key in ENVELOPE_FIELDS if key != "record_sha256"}
    if raw["record_sha256"] != canonical_sha256(base):
        raise ValueError("journal record_sha256 mismatch")
    return raw


def _analyze_records(
    records: tuple[dict[str, Any], ...], *, expected_manifest_sha256: str
) -> JournalSnapshot:
    if not records:
        raise ValueError("causal journal contains no records")
    verified: list[VerifiedRecord] = []
    previous = ZERO_SHA256
    journal_id = run_id = domain = None
    for sequence, payload in enumerate(records):
        raw = _verify_envelope(
            payload,
            expected_sequence=sequence,
            expected_previous=previous,
            journal_id=journal_id,
            run_id=run_id,
            domain=domain,
        )
        if sequence == 0:
            journal_id, run_id, domain = raw["journal_id"], raw["run_id"], raw["domain"]
        record = VerifiedRecord(raw)
        verified.append(record)
        previous = record.record_sha256
    assert journal_id is not None and run_id is not None and domain is not None
    if verified[0].record_type != "run_header":
        raise ValueError("causal journal must begin with run_header")
    manifest, expected_steps = _validate_header(verified[0].body)
    _require_sha256(expected_manifest_sha256, "expected_manifest_sha256")
    if manifest.sha256 != expected_manifest_sha256:
        raise ValueError("run manifest hash mismatch")

    completed: list[StepSnapshot] = []
    current: StepSnapshot | None = None
    next_step = 0
    ledger: VerifiedRecord | None = None
    for record in verified[1:]:
        if ledger is not None:
            raise ValueError("run_ledger must be the terminal journal record")
        body = record.body
        if record.record_type == "pre_action_commit":
            if current is not None:
                raise ValueError("new commit encountered before prior step became terminal")
            if next_step >= len(expected_steps):
                raise ValueError("journal commits more steps than its frozen plan")
            _validate_commit(body)
            expected_execution_id = _execution_id_from_commit(
                journal_id=journal_id,
                run_id=run_id,
                domain=domain,
                body=body,
            )
            if body["execution_id"] != expected_execution_id:
                raise ValueError("execution_id does not bind the complete pre-action commit")
            if body["step_id"] != expected_steps[next_step]:
                raise ValueError("journal step order differs from frozen plan")
            current = StepSnapshot(body["step_id"], "committed_not_executed", commit=record)
        elif record.record_type == "execution_handoff":
            if current is None or current.commit is None or current.handoff is not None:
                raise ValueError("execution_handoff has no unique pending commit")
            _validate_handoff(body, current.commit)
            current = StepSnapshot(
                current.step_id,
                "execution_unknown",
                commit=current.commit,
                handoff=record,
            )
        elif record.record_type == "action_receipt":
            if current is None or current.commit is None or current.handoff is None:
                raise ValueError("action_receipt has no handed-off commit")
            if current.receipt is not None or current.resolution is not None:
                raise ValueError("duplicate action terminal record")
            _validate_receipt(body, current.commit, current.handoff)
            current = StepSnapshot(
                current.step_id,
                "executed_outcome_missing",
                commit=current.commit,
                handoff=current.handoff,
                receipt=record,
            )
        elif record.record_type == "execution_resolution":
            if current is None or current.commit is None or current.receipt is not None:
                raise ValueError("execution_resolution has no unresolved commit")
            _validate_resolution(body, current.commit, current.handoff)
            status = (
                "committed_not_executed"
                if body["disposition"] == "not_executed"
                else "execution_unknown"
            )
            terminal = StepSnapshot(
                current.step_id,
                status,
                commit=current.commit,
                handoff=current.handoff,
                resolution=record,
            )
            completed.append(terminal)
            current = None
            next_step += 1
        elif record.record_type == "outcome":
            if current is None or current.commit is None or current.receipt is None:
                raise ValueError("outcome has no executed receipt")
            evidence = _validate_receipt(
                current.receipt.body,
                current.commit,
                current.handoff,  # type: ignore[arg-type]
            )
            _validate_outcome(body, current.commit, current.receipt, evidence)
            terminal = StepSnapshot(
                current.step_id,
                "complete",
                commit=current.commit,
                handoff=current.handoff,
                receipt=current.receipt,
                outcome=record,
            )
            completed.append(terminal)
            current = None
            next_step += 1
        elif record.record_type == "run_ledger":
            if current is not None:
                raise ValueError("run_ledger cannot seal a nonterminal committed step")
            ledger = record
        else:
            raise ValueError(f"unexpected record_type {record.record_type!r}")

    steps = list(completed)
    if current is not None:
        steps.append(current)
        next_step += 1
    for step_id in expected_steps[next_step:]:
        steps.append(StepSnapshot(step_id, "not_committed"))
    step_tuple = tuple(steps)
    if tuple(step.step_id for step in step_tuple) != expected_steps:
        raise ValueError("verified step ledger does not match frozen plan")
    run_status = "open"
    reason: str | None = None
    if ledger is not None:
        run_status = _validate_ledger(ledger.body, step_tuple, ledger.previous_record_sha256)
        reason = ledger.body["reason"]
    return JournalSnapshot(
        journal_id=journal_id,
        run_id=run_id,
        domain=domain,
        manifest_sha256=manifest.sha256,
        expected_step_ids=expected_steps,
        records=tuple(verified),
        steps=step_tuple,
        run_status=run_status,
        reason=reason,
        chain_head=verified[-1].record_sha256,
    )


def _read_record_directory(path: Path) -> tuple[dict[str, Any], ...]:
    try:
        entries = list(os.scandir(path))
    except OSError as exc:
        raise ValueError(f"cannot read causal journal directory {path}: {exc}") from exc
    record_paths: list[tuple[int, str, Path]] = []
    for entry in entries:
        name = entry.name
        if name == _LOCK_NAME or _TEMP_NAME.fullmatch(name):
            continue
        match = _RECORD_NAME.fullmatch(name)
        if match is None or not entry.is_file(follow_symlinks=False):
            raise ValueError(f"unexpected causal journal entry {name!r}")
        record_paths.append((int(match["sequence"]), match["sha"], Path(entry.path)))
    record_paths.sort(key=lambda item: item[0])
    records: list[dict[str, Any]] = []
    for expected, (sequence, filename_sha, record_path) in enumerate(record_paths):
        if sequence != expected:
            raise ValueError("causal journal record filenames contain a sequence gap")
        try:
            data = record_path.read_bytes()
        except OSError as exc:
            raise ValueError(f"cannot read causal journal record {record_path.name}: {exc}") from exc
        if not data.endswith(b"\n") or data.count(b"\n") != 1:
            raise ValueError(f"causal journal record {record_path.name} is torn or multi-line")
        try:
            payload = json.loads(data[:-1].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid causal journal record {record_path.name}") from exc
        _validate_json_value(payload, "journal record")
        if canonical_json_bytes(payload) + b"\n" != data:
            raise ValueError(f"causal journal record {record_path.name} is not canonical JSON")
        if type(payload) is not dict:
            raise ValueError("causal journal record root must be an object")
        if payload.get("record_sha256") != filename_sha:
            raise ValueError("causal journal filename does not bind record_sha256")
        records.append(payload)
    return tuple(records)


def load_causal_journal(
    path: Path, *, expected_manifest_sha256: str, require_closed: bool = False
) -> JournalSnapshot:
    """Verify a Phase 3a journal without mutating or recovering it."""
    snapshot = _analyze_records(
        _read_record_directory(Path(path)),
        expected_manifest_sha256=expected_manifest_sha256,
    )
    if require_closed and not snapshot.closed:
        raise ValueError("causal journal has no terminal run_ledger")
    return snapshot


def scoring_rows(
    path: Path, *, expected_manifest_sha256: str
) -> tuple[ScoringRow, ...]:
    """Materialize all outcomes, including open-set rows, from a complete run.

    Held, open, unpredicted, or execution-uncertain runs refuse as a whole so a
    caller cannot silently shrink the frozen denominator.
    """
    snapshot = load_causal_journal(
        Path(path),
        expected_manifest_sha256=expected_manifest_sha256,
        require_closed=True,
    )
    if snapshot.run_status != "complete":
        raise ValueError("only a complete causal journal is scoreable")
    rows: list[ScoringRow] = []
    for step in snapshot.steps:
        if step.commit is None or step.receipt is None or step.outcome is None:
            raise ValueError("complete journal contains an incomplete step")
        commit = step.commit.body
        if commit["prediction_status"] != "collected":
            raise ValueError("complete journal contains an uncollected prediction")
        outcome = step.outcome.body
        rows.append(
            ScoringRow(
                step_id=step.step_id,
                raw_outcome_label=outcome["raw_outcome_label"],
                scoring_label=outcome["scoring_label"],
                support_status=outcome["support_status"],
                probabilities=_probabilities_from_payload(commit["probabilities"]),
                commit_record_sha256=step.commit.record_sha256,
                receipt_record_sha256=step.receipt.record_sha256,
                outcome_record_sha256=step.outcome.record_sha256,
            )
        )
    return tuple(rows)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise CausalJournalError("os.write made no progress")
        view = view[written:]


def _fsync_directory(path: Path) -> None:
    if hasattr(os, "O_DIRECTORY"):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _durability_profile() -> str:
    if hasattr(os, "O_DIRECTORY"):
        return "fsync-file+atomic-link+fsync-directory"
    return "fsync-file+atomic-link"


def _lock_writer(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise CausalJournalError("causal journal already has an active writer") from exc
    else:
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise CausalJournalError("causal journal already has an active writer") from exc


def _unlock_writer(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)


def _open_writer_lock(path: Path) -> int:
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path / _LOCK_NAME, flags, 0o600)
    try:
        if os.fstat(fd).st_size == 0:
            _write_all(fd, b"1")
            os.fsync(fd)
        _lock_writer(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _normalize_fault_points(value: frozenset[str] | None) -> frozenset[str]:
    if value is None:
        return frozenset()
    if type(value) is not frozenset:
        raise ValueError("fault_points must be an exact frozenset")
    for point in value:
        _require_text(point, "fault point")
        if point not in FAULT_POINTS:
            raise ValueError(f"unknown fault point {point!r}")
    return value


class CausalTraceJournal:
    """Exclusive writer and recovery state machine for one causal journal."""

    def __init__(
        self,
        *,
        path: Path,
        expected_manifest_sha256: str,
        lock_fd: int,
        snapshot: JournalSnapshot,
        fault_points: frozenset[str] | None = None,
    ) -> None:
        self.path = path
        self.expected_manifest_sha256 = expected_manifest_sha256
        self._lock_fd = lock_fd
        self._snapshot = snapshot
        self._fault_points = _normalize_fault_points(fault_points)
        self._closed_handle = False
        self._poisoned = False
        self._directory_identity = self._path_identity(path)
        self._lock_identity = self._fd_identity(lock_fd)
        self._last_time_ns = max(
            (
                value
                for record in snapshot.records
                for key, value in record.body.items()
                if key.endswith("_at_ns") and type(value) is int
            ),
            default=0,
        )

    @classmethod
    def create(
        cls,
        path: Path,
        *,
        journal_id: str,
        run_id: str,
        domain: str,
        manifest: CanonicalArtifact,
        expected_step_ids: tuple[str, ...],
        fault_points: frozenset[str] | None = None,
    ) -> CausalTraceJournal:
        path = Path(path)
        _require_text(journal_id, "journal_id")
        _require_text(run_id, "run_id")
        _require_text(domain, "domain")
        _require_exact_instance(manifest, CanonicalArtifact, "manifest")
        if manifest.artifact_kind != "run_manifest":
            raise ValueError("manifest artifact_kind must be 'run_manifest'")
        if type(expected_step_ids) is not tuple or not expected_step_ids:
            raise ValueError("expected_step_ids must be a non-empty exact tuple")
        for step_id in expected_step_ids:
            _require_text(step_id, "expected step_id")
        if len(expected_step_ids) != len(set(expected_step_ids)):
            raise ValueError("expected_step_ids must be unique")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir()
        _fsync_directory(path.parent)
        lock_fd = _open_writer_lock(path)
        try:
            placeholder = object.__new__(cls)
            placeholder.path = path
            placeholder.expected_manifest_sha256 = manifest.sha256
            placeholder._lock_fd = lock_fd
            placeholder._snapshot = None
            placeholder._fault_points = _normalize_fault_points(fault_points)
            placeholder._closed_handle = False
            placeholder._poisoned = False
            placeholder._directory_identity = placeholder._path_identity(path)
            placeholder._lock_identity = placeholder._fd_identity(lock_fd)
            placeholder._last_time_ns = 0
            body = {
                "created_at_ns": placeholder._stamp(),
                "durability_profile": _durability_profile(),
                "expected_step_ids": list(expected_step_ids),
                "manifest": manifest.canonical_payload(),
                "plan_sha256": canonical_sha256(
                    {"expected_step_ids": list(expected_step_ids)}
                ),
            }
            placeholder._publish_initial(journal_id, run_id, domain, body)
            snapshot = load_causal_journal(
                path, expected_manifest_sha256=manifest.sha256
            )
            placeholder._snapshot = snapshot
            return placeholder
        except BaseException:
            try:
                _unlock_writer(lock_fd)
            finally:
                os.close(lock_fd)
            raise

    @classmethod
    def reopen(
        cls,
        path: Path,
        *,
        expected_manifest_sha256: str,
        fault_points: frozenset[str] | None = None,
    ) -> CausalTraceJournal:
        path = Path(path)
        _require_sha256(expected_manifest_sha256, "expected_manifest_sha256")
        lock_fd = _open_writer_lock(path)
        try:
            snapshot = load_causal_journal(
                path, expected_manifest_sha256=expected_manifest_sha256
            )
            if snapshot.closed:
                raise CausalJournalError("cannot reopen a terminal causal journal")
            return cls(
                path=path,
                expected_manifest_sha256=expected_manifest_sha256,
                lock_fd=lock_fd,
                snapshot=snapshot,
                fault_points=fault_points,
            )
        except BaseException:
            try:
                _unlock_writer(lock_fd)
            finally:
                os.close(lock_fd)
            raise

    @property
    def snapshot(self) -> JournalSnapshot:
        self._require_live()
        return self._snapshot

    def _stamp(self) -> int:
        stamp = max(time.time_ns(), self._last_time_ns + 1)
        self._last_time_ns = stamp
        return stamp

    def _checkpoint(self, name: str) -> None:
        if name in self._fault_points:
            raise InjectedJournalCrash(name)

    def _require_live(self) -> None:
        if self._closed_handle:
            raise CausalJournalError("causal journal writer handle is closed")
        if self._poisoned:
            raise CausalJournalError("causal journal writer is poisoned by a publication fault")

    @staticmethod
    def _fd_identity(fd: int) -> tuple[int, int]:
        stat = os.fstat(fd)
        return stat.st_dev, stat.st_ino

    @staticmethod
    def _path_identity(path: Path) -> tuple[int, int]:
        stat = os.stat(path, follow_symlinks=False)
        return stat.st_dev, stat.st_ino

    def _verify_identity(self) -> None:
        try:
            directory_identity = self._path_identity(self.path)
            lock_identity = self._path_identity(self.path / _LOCK_NAME)
        except OSError as exc:
            raise CausalJournalError("causal journal custody path vanished") from exc
        if directory_identity != self._directory_identity:
            raise CausalJournalError("causal journal directory identity changed")
        if lock_identity != self._lock_identity or self._fd_identity(
            self._lock_fd
        ) != self._lock_identity:
            raise CausalJournalError("causal journal writer-lock identity changed")

    def _verify_current(self) -> None:
        self._require_live()
        self._verify_identity()
        current = load_causal_journal(
            self.path, expected_manifest_sha256=self.expected_manifest_sha256
        )
        if current.records != self._snapshot.records:
            raise CausalJournalError("causal journal changed outside its owned writer")

    def _publish_initial(
        self, journal_id: str, run_id: str, domain: str, body: dict[str, Any]
    ) -> None:
        base = _record_payload_without_hash(
            journal_id=journal_id,
            run_id=run_id,
            domain=domain,
            sequence=0,
            previous_record_sha256=ZERO_SHA256,
            record_type="run_header",
            body=body,
        )
        payload = {**base, "record_sha256": canonical_sha256(base)}
        _analyze_records(
            (payload,), expected_manifest_sha256=self.expected_manifest_sha256
        )
        self._publish_payload(base)

    def _publish(self, record_type: str, body: dict[str, Any]) -> VerifiedRecord:
        self._verify_current()
        snapshot = self._snapshot
        base = _record_payload_without_hash(
            journal_id=snapshot.journal_id,
            run_id=snapshot.run_id,
            domain=snapshot.domain,
            sequence=len(snapshot.records),
            previous_record_sha256=snapshot.chain_head,
            record_type=record_type,
            body=body,
        )
        payload = {**base, "record_sha256": canonical_sha256(base)}
        current_payloads = _read_record_directory(self.path)
        _analyze_records(
            (*current_payloads, payload),
            expected_manifest_sha256=self.expected_manifest_sha256,
        )
        self._publish_payload(base)
        self._snapshot = load_causal_journal(
            self.path, expected_manifest_sha256=self.expected_manifest_sha256
        )
        return self._snapshot.records[-1]

    def _publish_payload(self, base: dict[str, Any]) -> None:
        self._require_live()
        record_hash = canonical_sha256(base)
        payload = {**base, "record_sha256": record_hash}
        data = canonical_json_bytes(payload) + b"\n"
        final_name = f"{base['sequence']:08d}-{record_hash}.json"
        final_path = self.path / final_name
        temp_path = self.path / f".record-{uuid.uuid4().hex}.tmp"
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        fd = -1
        try:
            fd = os.open(temp_path, flags, 0o600)
            _write_all(fd, data)
            os.fsync(fd)
            os.close(fd)
            fd = -1
            os.link(temp_path, final_path)
            _fsync_directory(self.path)
            os.unlink(temp_path)
            _fsync_directory(self.path)
        except BaseException:
            self._poisoned = True
            if fd >= 0:
                os.close(fd)
            raise

    def run_step(
        self,
        *,
        step_id: str,
        state: CanonicalArtifact,
        candidate_actions: tuple[CanonicalArtifact, ...],
        selected_action_id: str,
        estimator: CanonicalArtifact,
        estimator_config: CanonicalArtifact,
        executor: CanonicalArtifact,
        ontology: OutcomeOntology,
        prediction: Prediction,
        adapter_binding: ActionAdapterBinding,
    ) -> StepSnapshot:
        """Commit and hand off one planned action, then retain its actual outcome."""
        self._require_live()
        if self._snapshot.closed:
            raise CausalJournalError("cannot append to a terminal causal journal")
        _require_text(step_id, "step_id")
        _require_text(selected_action_id, "selected_action_id")
        _require_exact_instance(adapter_binding, ActionAdapterBinding, "adapter_binding")
        unresolved = next(
            (
                step
                for step in self._snapshot.steps
                if step.commit is not None
                and step.outcome is None
                and step.resolution is None
            ),
            None,
        )
        if unresolved is not None:
            raise CausalJournalError("recover the pending step before starting another")
        pending = next(
            (step for step in self._snapshot.steps if step.status == "not_committed"),
            None,
        )
        if pending is None:
            raise CausalJournalError("all frozen run-plan steps are already terminal")
        if step_id != pending.step_id:
            raise ValueError("step_id is not the next member of the frozen run plan")
        _require_exact_instance(state, CanonicalArtifact, "state")
        _require_exact_instance(estimator, CanonicalArtifact, "estimator")
        _require_exact_instance(estimator_config, CanonicalArtifact, "estimator_config")
        _require_exact_instance(executor, CanonicalArtifact, "executor")
        _require_exact_instance(ontology, OutcomeOntology, "ontology")
        _require_exact_instance(prediction, Prediction, "prediction")
        for artifact, kind, field in (
            (state, "state", "state"),
            (estimator, "estimator", "estimator"),
            (estimator_config, "estimator_config", "estimator_config"),
            (executor, "executor", "executor"),
        ):
            if artifact.artifact_kind != kind:
                raise ValueError(f"{field} artifact_kind must be {kind!r}")
        prediction.validate_for(ontology)
        if type(candidate_actions) is not tuple or not candidate_actions:
            raise ValueError("candidate_actions must be a non-empty exact tuple")
        for action in candidate_actions:
            _require_exact_instance(action, CanonicalArtifact, "candidate action")
            if action.artifact_kind != "action":
                raise ValueError("candidate action artifact_kind must be 'action'")
        actions = tuple(sorted(candidate_actions, key=lambda item: item.artifact_id))
        action_ids = tuple(action.artifact_id for action in actions)
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("candidate action IDs must be unique")
        selected = {action.artifact_id: action for action in actions}.get(selected_action_id)
        if selected is None:
            raise ValueError("selected_action_id is not in candidate_actions")
        if adapter_binding.executor_artifact_sha256 != executor.sha256:
            raise ValueError("adapter is not bound to the committed executor artifact")
        action_payloads = [action.canonical_payload() for action in actions]
        action_set_sha256 = canonical_sha256(action_payloads)
        probability_payloads = [
            item.canonical_payload() for item in prediction.probabilities
        ]
        execution_id = _derive_execution_id(
            journal_id=self._snapshot.journal_id,
            run_id=self._snapshot.run_id,
            domain=self._snapshot.domain,
            step_id=step_id,
            state_sha256=state.sha256,
            candidate_action_set_sha256=action_set_sha256,
            selected_action_sha256=selected.sha256,
            estimator_sha256=estimator.sha256,
            estimator_config_sha256=estimator_config.sha256,
            executor_sha256=executor.sha256,
            ontology_sha256=ontology.sha256,
            prediction_status=prediction.status,
            prediction_reason=prediction.reason,
            probabilities=probability_payloads,
        )
        commit_body = {
            "step_id": step_id,
            "committed_at_ns": self._stamp(),
            "execution_id": execution_id,
            "state": state.canonical_payload(),
            "candidate_actions": action_payloads,
            "candidate_action_set_sha256": action_set_sha256,
            "selected_action_id": selected.artifact_id,
            "selected_action_sha256": selected.sha256,
            "estimator": estimator.canonical_payload(),
            "estimator_config": estimator_config.canonical_payload(),
            "executor": executor.canonical_payload(),
            "ontology": ontology.canonical_payload(),
            "prediction_status": prediction.status,
            "prediction_reason": prediction.reason,
            "probabilities": probability_payloads,
        }
        commit = self._publish("pre_action_commit", commit_body)
        request = _execution_request(commit)
        self._checkpoint("after_pre_action_commit")
        handoff = self._publish(
            "execution_handoff",
            {
                "step_id": step_id,
                "commit_record_sha256": commit.record_sha256,
                "execution_id": execution_id,
                "selected_action_sha256": selected.sha256,
                "executor_sha256": executor.sha256,
                "handed_off_at_ns": self._stamp(),
            },
        )
        self._checkpoint("after_execution_handoff")
        self._verify_current()
        adapter = adapter_binding.adapter
        try:
            resolution = adapter.execute(request)
            self._checkpoint("after_execute_before_receipt")
            if type(resolution) is not ActionResolution:
                raise ValueError("adapter execute result must be an exact ActionResolution")
        except Exception:
            resolution = self._reconcile_adapter(adapter, request)
        self._apply_resolution(commit, handoff, resolution)
        return next(step for step in self._snapshot.steps if step.step_id == step_id)

    def _reconcile_adapter(
        self,
        adapter: DurableActionAdapter,
        request: ExecutionRequest,
    ) -> ActionResolution:
        try:
            resolution = adapter.reconcile(request)
            if type(resolution) is not ActionResolution:
                raise ValueError("adapter reconcile result must be an exact ActionResolution")
            return resolution
        except Exception:
            return ActionResolution("execution_unknown", "adapter_failure")

    def _apply_resolution(
        self,
        commit: VerifiedRecord,
        handoff: VerifiedRecord | None,
        resolution: ActionResolution,
    ) -> None:
        _require_exact_instance(resolution, ActionResolution, "action resolution")
        if resolution.disposition == "executed":
            if handoff is None:
                raise CausalJournalError("executed result cannot precede execution_handoff")
            evidence = resolution.evidence
            if evidence is None:  # guarded by ActionResolution
                raise AssertionError("executed resolution lacks evidence")
            receipt = self._publish(
                "action_receipt",
                {
                    "step_id": commit.body["step_id"],
                    "commit_record_sha256": commit.record_sha256,
                    "handoff_record_sha256": handoff.record_sha256,
                    "execution_id": commit.body["execution_id"],
                    "disposition": "executed",
                    "reason": "authoritative_receipt",
                    "received_at_ns": self._stamp(),
                    "receipt": evidence.receipt.canonical_payload(),
                    "observation": evidence.observation.canonical_payload(),
                    "outcome_source": evidence.outcome_source.canonical_payload(),
                    "raw_outcome_label": evidence.raw_outcome_label,
                },
            )
            self._checkpoint("after_action_receipt")
            self._append_outcome(commit, receipt)
            self._checkpoint("after_outcome")
            return
        self._publish(
            "execution_resolution",
            {
                "step_id": commit.body["step_id"],
                "commit_record_sha256": commit.record_sha256,
                "handoff_record_sha256": (
                    handoff.record_sha256 if handoff is not None else None
                ),
                "execution_id": commit.body["execution_id"],
                "disposition": resolution.disposition,
                "reason": resolution.reason,
                "resolved_at_ns": self._stamp(),
            },
        )
        self._checkpoint("after_execution_resolution")

    def _append_outcome(self, commit: VerifiedRecord, receipt: VerifiedRecord) -> None:
        if self._snapshot.records[-1].record_sha256 != receipt.record_sha256:
            raise CausalJournalError("receipt is not the current unresolved chain head")
        handoff = next(
            step.handoff
            for step in self._snapshot.steps
            if step.step_id == commit.body["step_id"]
        )
        if handoff is None:
            raise AssertionError("verified receipt has no handoff")
        evidence = _validate_receipt(receipt.body, commit, handoff)
        ontology = OutcomeOntology.from_payload(commit.body["ontology"])
        support_status, scoring_label = _classify_outcome(
            ontology, evidence.raw_outcome_label
        )
        self._publish(
            "outcome",
            {
                "step_id": commit.body["step_id"],
                "commit_record_sha256": commit.record_sha256,
                "receipt_record_sha256": receipt.record_sha256,
                "observed_at_ns": self._stamp(),
                "raw_outcome_label": evidence.raw_outcome_label,
                "support_status": support_status,
                "scoring_label": scoring_label,
                "observation_sha256": evidence.observation.sha256,
                "outcome_source_sha256": evidence.outcome_source.sha256,
            },
        )

    def recover_pending(
        self, adapter_binding: ActionAdapterBinding | None = None
    ) -> StepSnapshot | None:
        """Resolve the sole nonterminal step conservatively after a process crash."""
        self._require_live()
        pending = next(
            (
                step
                for step in self._snapshot.steps
                if step.commit is not None
                and step.outcome is None
                and step.resolution is None
            ),
            None,
        )
        if pending is None:
            return None
        if pending.resolution is not None:
            return pending
        if pending.commit is None:
            raise AssertionError("pending step has no commit")
        if pending.handoff is None:
            self._apply_resolution(
                pending.commit,
                None,
                ActionResolution("not_executed", "handoff_not_published"),
            )
        elif pending.receipt is not None:
            self._append_outcome(pending.commit, pending.receipt)
        else:
            commit_body = pending.commit.body
            executor = CanonicalArtifact.from_payload(commit_body["executor"], field="executor")
            if adapter_binding is not None:
                _require_exact_instance(
                    adapter_binding, ActionAdapterBinding, "adapter_binding"
                )
            if (
                adapter_binding is None
                or adapter_binding.executor_artifact_sha256 != executor.sha256
            ):
                resolution = ActionResolution("execution_unknown", "adapter_unavailable")
            else:
                resolution = self._reconcile_adapter(
                    adapter_binding.adapter, _execution_request(pending.commit)
                )
            self._apply_resolution(pending.commit, pending.handoff, resolution)
        return next(step for step in self._snapshot.steps if step.step_id == pending.step_id)

    def close_run(
        self, adapter_binding: ActionAdapterBinding | None = None
    ) -> JournalSnapshot:
        """Resolve any crash boundary, publish the exact completeness ledger, and close."""
        self._require_live()
        if self._snapshot.closed:
            raise CausalJournalError("causal journal already has a terminal ledger")
        self.recover_pending(adapter_binding)
        steps = self._snapshot.steps
        complete = all(step.status == "complete" for step in steps)
        status = "complete" if complete else "held"
        reason = "all_steps_observed" if complete else _held_reason(steps)
        self._checkpoint("before_run_ledger")
        self._publish(
            "run_ledger",
            {
                "closed_at_ns": self._stamp(),
                "run_status": status,
                "reason": reason,
                "chain_head_before_ledger": self._snapshot.chain_head,
                "counts": _ledger_counts(steps),
                "step_statuses": _ledger_rows(steps),
            },
        )
        self._checkpoint("after_run_ledger")
        snapshot = self._snapshot
        self.close_handle()
        return snapshot

    def close_handle(self) -> None:
        """Release the writer without inventing a terminal run state."""
        if self._closed_handle:
            return
        try:
            _unlock_writer(self._lock_fd)
        finally:
            os.close(self._lock_fd)
            self._closed_handle = True

    def __enter__(self) -> CausalTraceJournal:
        self._require_live()
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close_handle()
