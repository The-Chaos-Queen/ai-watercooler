"""Crash-safe, append-only capture for real world-model transitions.

The paired v2 trace format is convenient for scoring but cannot prove that a
forecast existed before the action. This journal writes and fsyncs a separate
pre-action record before the caller may invoke an environment or tool. Complete
journals can then be materialized into the existing paired format offline.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from world_model_trace import (
    NullWorldModelObserver,
    ObservationSourceRef,
    OutcomeRecord,
    PreActionCommit,
    canonical_json_bytes,
    canonical_sha256,
    outcome_record_from_payload,
    pre_action_commit_from_payload,
    validate_trace_pair,
)


JOURNAL_SCHEMA_VERSION = "world-model-journal-v1"
CAPTURE_SOURCE_KINDS = frozenset({"environment", "tool_context", "tool_result"})
HEADER_FIELDS = frozenset(
    {"journal_schema_version", "record_type", "manifest_sha256"}
)
SOURCE_FIELDS = frozenset({"kind", "id", "sha256", "sequence", "payload"})
PRE_ACTION_FIELDS = frozenset(
    {
        "journal_schema_version",
        "record_type",
        "manifest_sha256",
        "state_source",
        "commit",
    }
)
OUTCOME_FIELDS = frozenset(
    {
        "journal_schema_version",
        "record_type",
        "manifest_sha256",
        "outcome_source",
        "outcome",
    }
)


def _require_sha256(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{field} must be a 64-character lowercase SHA-256 digest")
    return value


def _require_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a non-empty trimmed string")
    return value


def _require_exact_fields(payload: dict[str, Any], expected: frozenset[str], field: str) -> None:
    actual = set(payload)
    if actual != expected:
        raise ValueError(
            f"{field} fields mismatch: missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def canonical_action(name: str, arguments: dict[str, Any] | None = None) -> str:
    """Return the exact action key used by commits and declared action spaces."""
    _require_text(name, "action name")
    arguments = {} if arguments is None else arguments
    if not isinstance(arguments, dict):
        raise ValueError("action arguments must be an object")
    return canonical_json_bytes({"arguments": arguments, "name": name}).decode("ascii")


def derive_trace_id(
    *,
    run_id: str,
    domain: str,
    episode_id: str,
    step_index: int,
    state_source_sha256: str,
    action: str,
) -> str:
    identity = {
        "run_id": run_id,
        "domain": domain,
        "episode_id": episode_id,
        "step_index": step_index,
        "state_source_sha256": state_source_sha256,
        "action": action,
    }
    return f"{domain}:{canonical_sha256(identity)}"


@dataclass(frozen=True, slots=True)
class CapturedSource:
    kind: str
    source_id: str
    sequence: int
    payload: Any

    def __post_init__(self) -> None:
        if self.kind not in CAPTURE_SOURCE_KINDS:
            raise ValueError(f"capture source kind must be one of {sorted(CAPTURE_SOURCE_KINDS)}")
        _require_text(self.source_id, "source_id")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 0:
            raise ValueError("source sequence must be a non-negative integer")
        canonical_json_bytes(self.payload)

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.payload)

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "id": self.source_id,
            "sha256": self.sha256,
            "sequence": self.sequence,
            "payload": self.payload,
        }


@dataclass(frozen=True, slots=True)
class PendingTransition:
    commit: PreActionCommit
    state_source: CapturedSource


@dataclass(frozen=True, slots=True)
class CapturedTracePair:
    commit: PreActionCommit
    outcome: OutcomeRecord
    state_source: CapturedSource
    outcome_source: CapturedSource | None


class DurableTraceJournal:
    """Single-writer journal with an fsync barrier before every action."""

    def __init__(self, path: Path, *, manifest_sha256: str) -> None:
        self.path = Path(path)
        _require_sha256(manifest_sha256, "manifest_sha256")
        self.manifest_sha256 = manifest_sha256
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._next_event_index = 0
        self._pending: PendingTransition | None = None
        self._append_record(
            {
                "journal_schema_version": JOURNAL_SCHEMA_VERSION,
                "record_type": "header",
                "manifest_sha256": manifest_sha256,
            },
            create=True,
        )

    def _append_record(self, record: dict[str, Any], *, create: bool = False) -> None:
        mode = "xb" if create else "ab"
        with self.path.open(mode) as handle:
            handle.write(canonical_json_bytes(record) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())

    def begin(
        self,
        *,
        observer: Any,
        run_id: str,
        domain: str,
        episode_id: str,
        step_index: int,
        state_ref: str,
        action: str,
        state_source_kind: str,
        state_source_id: str,
        state_source_payload: Any,
    ) -> PendingTransition:
        if self._pending is not None:
            raise RuntimeError("cannot begin a second transition while one is pending")
        state_source = CapturedSource(
            state_source_kind,
            state_source_id,
            self._next_event_index,
            state_source_payload,
        )
        commit_event_index = state_source.sequence + 1
        trace_id = derive_trace_id(
            run_id=run_id,
            domain=domain,
            episode_id=episode_id,
            step_index=step_index,
            state_source_sha256=state_source.sha256,
            action=action,
        )
        commit_kwargs = {
            "trace_id": trace_id,
            "run_id": run_id,
            "domain": domain,
            "episode_id": episode_id,
            "step_index": step_index,
            "event_index": commit_event_index,
            "committed_at_ns": time.time_ns(),
            "state_ref": state_ref,
            "action": action,
        }
        if isinstance(observer, NullWorldModelObserver):
            commit_kwargs["reason"] = "real_transition_collection"
        commit = observer.commit(**commit_kwargs)
        record = {
            "journal_schema_version": JOURNAL_SCHEMA_VERSION,
            "record_type": "pre_action_commit",
            "manifest_sha256": self.manifest_sha256,
            "state_source": state_source.canonical_payload(),
            "commit": commit.canonical_payload(),
        }
        self._append_record(record)
        pending = PendingTransition(commit, state_source)
        self._pending = pending
        return pending

    def finish(
        self,
        pending: PendingTransition,
        *,
        observation: str,
        outcome_source_kind: str,
        outcome_source_id: str,
        outcome_source_payload: Any,
    ) -> OutcomeRecord:
        if pending is not self._pending:
            raise RuntimeError("pending transition does not belong to this journal")
        if outcome_source_kind not in {"environment", "tool_result"}:
            raise ValueError("outcome source kind must be environment or tool_result")
        source = CapturedSource(
            outcome_source_kind,
            outcome_source_id,
            pending.commit.event_index + 1,
            outcome_source_payload,
        )
        observed_at_ns = max(time.time_ns(), pending.commit.committed_at_ns + 1)
        outcome = OutcomeRecord(
            trace_id=pending.commit.trace_id,
            run_id=pending.commit.run_id,
            domain=pending.commit.domain,
            episode_id=pending.commit.episode_id,
            step_index=pending.commit.step_index,
            event_index=source.sequence + 1,
            observed_at_ns=observed_at_ns,
            action=pending.commit.action,
            commit_sha256=pending.commit.sha256,
            status="observed",
            observation=observation,
            source_observation=ObservationSourceRef(
                source.kind,
                source.source_id,
                source.sha256,
                source.sequence,
            ),
        )
        validate_trace_pair(pending.commit, outcome)
        self._append_record(
            {
                "journal_schema_version": JOURNAL_SCHEMA_VERSION,
                "record_type": "outcome",
                "manifest_sha256": self.manifest_sha256,
                "outcome_source": source.canonical_payload(),
                "outcome": outcome.canonical_payload(),
            }
        )
        self._next_event_index = outcome.event_index + 1
        self._pending = None
        return outcome

    def capture(
        self,
        *,
        execute: Callable[[], tuple[str, str, str, Any]],
        **begin_kwargs: Any,
    ) -> OutcomeRecord:
        """Commit durably, then invoke ``execute`` exactly once.

        ``execute`` returns ``(observation, source_kind, source_id, payload)``.
        Exceptions deliberately leave an orphan commit, which is not scoreable.
        """
        pending = self.begin(**begin_kwargs)
        observation, source_kind, source_id, payload = execute()
        return self.finish(
            pending,
            observation=observation,
            outcome_source_kind=source_kind,
            outcome_source_id=source_id,
            outcome_source_payload=payload,
        )


def _captured_source_from_payload(payload: Any, *, field: str) -> CapturedSource:
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be an object")
    _require_exact_fields(payload, SOURCE_FIELDS, field)
    source = CapturedSource(
        kind=payload["kind"],
        source_id=payload["id"],
        sequence=payload["sequence"],
        payload=payload["payload"],
    )
    if source.sha256 != payload["sha256"]:
        raise ValueError(f"{field} sha256 does not match its canonical payload")
    return source


def load_journal(path: Path, *, expected_manifest_sha256: str) -> list[CapturedTracePair]:
    """Validate a complete journal and return its materializable trace pairs."""
    path = Path(path)
    _require_sha256(expected_manifest_sha256, "expected_manifest_sha256")
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read journal {path}: {exc}") from exc
    if not raw_lines:
        raise ValueError(f"journal is empty: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw_lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number}: journal record must be an object")
        records.append(record)

    header = records[0]
    _require_exact_fields(header, HEADER_FIELDS, "journal header")
    if header["journal_schema_version"] != JOURNAL_SCHEMA_VERSION:
        raise ValueError("journal schema version mismatch")
    if header["record_type"] != "header":
        raise ValueError("journal must begin with a header")
    if header["manifest_sha256"] != expected_manifest_sha256:
        raise ValueError("journal manifest hash mismatch")

    pending: tuple[PreActionCommit, CapturedSource] | None = None
    pairs: list[CapturedTracePair] = []
    expected_event = 0
    for record in records[1:]:
        if record.get("manifest_sha256") != expected_manifest_sha256:
            raise ValueError("journal record manifest hash mismatch")
        record_type = record.get("record_type")
        if record_type == "pre_action_commit":
            _require_exact_fields(record, PRE_ACTION_FIELDS, "pre-action journal record")
            if pending is not None:
                raise ValueError("journal contains a second commit before an outcome")
            source = _captured_source_from_payload(record["state_source"], field="state_source")
            commit = pre_action_commit_from_payload(record["commit"])
            if source.sequence != expected_event or commit.event_index != source.sequence + 1:
                raise ValueError("pre-action source/commit event sequence is non-monotonic")
            expected_trace_id = derive_trace_id(
                run_id=commit.run_id,
                domain=commit.domain,
                episode_id=commit.episode_id,
                step_index=commit.step_index,
                state_source_sha256=source.sha256,
                action=commit.action,
            )
            if commit.trace_id != expected_trace_id:
                raise ValueError("commit trace_id does not bind the pre-action source")
            pending = (commit, source)
        elif record_type == "outcome":
            _require_exact_fields(record, OUTCOME_FIELDS, "outcome journal record")
            if pending is None:
                raise ValueError("journal outcome has no preceding commit")
            outcome = outcome_record_from_payload(record["outcome"])
            if outcome.status != "observed":
                raise ValueError("materializable journals require observed outcomes")
            source = _captured_source_from_payload(
                record["outcome_source"], field="outcome_source"
            )
            commit, state_source = pending
            if source.sequence != commit.event_index + 1:
                raise ValueError("outcome source event sequence is non-monotonic")
            if outcome.event_index != source.sequence + 1:
                raise ValueError("outcome event sequence is non-monotonic")
            reference = outcome.source_observation
            if reference is None or reference.canonical_payload() != {
                key: value for key, value in source.canonical_payload().items() if key != "payload"
            }:
                raise ValueError("outcome source reference does not bind the captured payload")
            validate_trace_pair(commit, outcome)
            pairs.append(CapturedTracePair(commit, outcome, state_source, source))
            expected_event = outcome.event_index + 1
            pending = None
        else:
            raise ValueError(f"unknown journal record_type {record_type!r}")
    if pending is not None:
        raise ValueError("journal ends with an orphan pre-action commit")
    if not pairs:
        raise ValueError("journal contains no complete transitions")
    return pairs


def paired_trace_bytes(pairs: list[CapturedTracePair]) -> bytes:
    if not pairs:
        raise ValueError("cannot materialize an empty trace")
    rows = [
        canonical_json_bytes(
            {
                "commit": pair.commit.canonical_payload(),
                "outcome": pair.outcome.canonical_payload(),
            }
        )
        for pair in pairs
    ]
    return b"\n".join(rows) + b"\n"
