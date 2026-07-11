from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from world_model_trace import (
    NullWorldModelObserver,
    ObservationProbability,
    ObservationSourceRef,
    OutcomeRecord,
    PreActionCommit,
    outcome_record_from_payload,
    pre_action_commit_from_payload,
    validate_trace_pair,
)


def _commit(**overrides) -> PreActionCommit:
    values = {
        "trace_id": "trace-1",
        "run_id": "run-1",
        "domain": "ls20",
        "episode_id": "episode-1",
        "step_index": 0,
        "event_index": 4,
        "committed_at_ns": 400,
        "state_ref": "state:s0",
        "action": "look",
        "status": "committed",
        "estimator_id": "fixture-model",
        "estimator_kind": "model",
        "probabilities": (
            ObservationProbability("clear", 0.75),
            ObservationProbability("blocked", 0.25),
        ),
    }
    values.update(overrides)
    return PreActionCommit(**values)


def _outcome(commit: PreActionCommit, **overrides) -> OutcomeRecord:
    values = {
        "trace_id": commit.trace_id,
        "run_id": commit.run_id,
        "domain": commit.domain,
        "episode_id": commit.episode_id,
        "step_index": commit.step_index,
        "event_index": commit.event_index + 1,
        "observed_at_ns": commit.committed_at_ns + 100,
        "action": commit.action,
        "commit_sha256": commit.sha256,
        "status": "observed",
        "observation": "clear",
        "source_observation": ObservationSourceRef(
            "synthetic_fixture", "fixture:clear", "1" * 64, commit.event_index + 1
        ),
    }
    values.update(overrides)
    return OutcomeRecord(**values)


def test_commit_is_immutable_and_probability_order_has_one_hash():
    first = _commit()
    second = _commit(probabilities=tuple(reversed(first.probabilities)))
    assert first.sha256 == second.sha256
    assert [item.observation for item in first.probabilities] == ["blocked", "clear"]
    with pytest.raises(FrozenInstanceError):
        first.action = "move"  # type: ignore[misc]


@pytest.mark.parametrize(
    "probabilities",
    [
        (ObservationProbability("a", 0.2), ObservationProbability("b", 0.2)),
        (ObservationProbability("a", 0.5), ObservationProbability("a", 0.5)),
        (),
    ],
)
def test_committed_probability_distribution_is_strict(probabilities):
    with pytest.raises(ValueError):
        _commit(probabilities=probabilities)


def test_probability_rejects_nonfinite_and_out_of_range():
    for value in (float("nan"), float("inf"), -0.1, 1.1):
        with pytest.raises(ValueError):
            ObservationProbability("bad", value)


def test_statuses_cannot_smuggle_values():
    with pytest.raises(ValueError):
        _commit(status="not_collected", reason="disabled")
    commit = _commit()
    with pytest.raises(ValueError):
        _outcome(commit, status="not_collected", observation="clear", reason="disabled")
    with pytest.raises(ValueError):
        _outcome(commit, status="observed", observation=None)


def test_oracle_declaration_matches_estimator_kind():
    with pytest.raises(ValueError):
        _commit(estimator_kind="oracle", declared_oracle=False)
    oracle = _commit(estimator_kind="oracle", declared_oracle=True)
    assert oracle.declared_oracle is True


def test_pair_validation_binds_hash_identity_support_and_order():
    commit = _commit()
    validate_trace_pair(commit, _outcome(commit))
    with pytest.raises(ValueError, match="strictly after"):
        validate_trace_pair(commit, _outcome(commit, event_index=commit.event_index))
    with pytest.raises(ValueError, match="canonical commit hash"):
        validate_trace_pair(commit, _outcome(commit, commit_sha256="0" * 64))
    with pytest.raises(ValueError, match="outside"):
        validate_trace_pair(commit, _outcome(commit, observation="unknown"))


def test_pair_validation_requires_timestamp_and_source_after_commit():
    commit = _commit()
    with pytest.raises(ValueError, match="observed_at_ns"):
        validate_trace_pair(commit, _outcome(commit, observed_at_ns=commit.committed_at_ns))
    early_source = ObservationSourceRef(
        "synthetic_fixture", "fixture:early", "2" * 64, commit.event_index
    )
    with pytest.raises(ValueError, match="source observation sequence"):
        validate_trace_pair(commit, _outcome(commit, source_observation=early_source))


def test_answer_key_is_not_an_allowed_observation_source():
    with pytest.raises(ValueError, match="source observation kind"):
        ObservationSourceRef("answer_key", "fixture:key", "3" * 64, 1)


def test_canonical_payload_roundtrip_preserves_hashes():
    commit = _commit()
    outcome = _outcome(commit)
    restored_commit = pre_action_commit_from_payload(commit.canonical_payload())
    restored_outcome = outcome_record_from_payload(outcome.canonical_payload())
    assert restored_commit.sha256 == commit.sha256
    assert restored_outcome.sha256 == outcome.sha256
    validate_trace_pair(restored_commit, restored_outcome)


def test_null_observer_records_absence_without_fixture_truth():
    observer = NullWorldModelObserver()
    commit = observer.commit(
        trace_id="trace-null",
        run_id="run-null",
        domain="tool",
        episode_id="episode-null",
        step_index=2,
        event_index=8,
        committed_at_ns=800,
        state_ref="state:s2",
        action="wait",
    )
    outcome = observer.observe(commit, event_index=9, observed_at_ns=900)
    assert commit.status == "not_collected"
    assert commit.probabilities == ()
    assert outcome.status == "not_collected"
    assert outcome.observation is None
    validate_trace_pair(commit, outcome)
