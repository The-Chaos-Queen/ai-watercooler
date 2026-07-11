from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from world_model_trace import (
    NullWorldModelObserver,
    ObservationProbability,
    ObservationSourceRef,
    OutcomeRecord,
    PreActionCommit,
)


ROOT = Path(__file__).resolve().parents[1]
SCORER_PATH = ROOT / "spikes" / "score_world_model_trace.py"
FIXTURE_DIR = ROOT / "spikes" / "fixtures" / "world_model"

spec = importlib.util.spec_from_file_location("score_world_model_trace", SCORER_PATH)
scorer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = scorer
spec.loader.exec_module(scorer)


def _pair(
    trace_id: str,
    *,
    split: str,
    domain: str,
    state_ref: str,
    action: str,
    observation: str,
) -> tuple[PreActionCommit, OutcomeRecord]:
    observer = NullWorldModelObserver()
    commit = observer.commit(
        trace_id=trace_id,
        run_id=f"synthetic-{domain}-{split}",
        domain=domain,
        episode_id=f"episode-{trace_id}",
        step_index=0,
        event_index=0,
        committed_at_ns=100,
        state_ref=state_ref,
        action=action,
        reason="synthetic_transition_fixture",
    )
    source_text = f"{trace_id}:{observation}"
    outcome = OutcomeRecord(
        trace_id=commit.trace_id,
        run_id=commit.run_id,
        domain=commit.domain,
        episode_id=commit.episode_id,
        step_index=commit.step_index,
        event_index=2,
        observed_at_ns=200,
        action=commit.action,
        commit_sha256=commit.sha256,
        status="observed",
        observation=observation,
        source_observation=ObservationSourceRef(
            "synthetic_fixture",
            f"fixture:{trace_id}",
            hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            1,
        ),
    )
    return commit, outcome


def _write(path: Path, pairs) -> None:
    rows = [
        json.dumps(
            {"commit": commit.canonical_payload(), "outcome": outcome.canonical_payload()},
            sort_keys=True,
        )
        for commit, outcome in pairs
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _toy_files(tmp_path: Path) -> tuple[Path, Path]:
    train = [
        _pair("train-left-1", split="train", domain="ls20", state_ref="locked", action="unlock", observation="open"),
        _pair("train-left-2", split="train", domain="ls20", state_ref="locked", action="unlock", observation="open"),
        _pair("train-right-1", split="train", domain="ls20", state_ref="locked", action="wait", observation="closed"),
        _pair("train-right-2", split="train", domain="ls20", state_ref="locked", action="wait", observation="closed"),
    ]
    evaluate = [
        _pair("eval-left", split="eval", domain="ls20", state_ref="locked", action="unlock", observation="open"),
        _pair("eval-right", split="eval", domain="ls20", state_ref="locked", action="wait", observation="closed"),
    ]
    train_path = tmp_path / "train.jsonl"
    eval_path = tmp_path / "eval.jsonl"
    _write(train_path, train)
    _write(eval_path, evaluate)
    return train_path, eval_path


def test_tabular_baseline_beats_deterministic_action_shuffle(tmp_path):
    train_path, eval_path = _toy_files(tmp_path)
    result = scorer.score_files(train_path, eval_path, shuffle_seed="fixed")
    delta = result["delta_null_minus_tabular"]
    assert delta["categorical_nll"] > 0.0
    assert delta["multiclass_brier"] > 0.0
    marginal_delta = result["delta_marginal_minus_tabular"]
    assert marginal_delta["categorical_nll"] > 0.0
    assert marginal_delta["multiclass_brier"] > 0.0


@pytest.mark.parametrize("domain", ["ls20", "tool"])
def test_committed_synthetic_fixture_pairs_score(domain):
    result = scorer.score_files(
        FIXTURE_DIR / f"{domain}_train.jsonl",
        FIXTURE_DIR / f"{domain}_eval.jsonl",
        shuffle_seed="fixture-smoke",
    )
    assert result["n_train"] == 4
    assert result["n_eval"] == 2
    assert result["delta_null_minus_tabular"]["categorical_nll"] > 0.0
    assert result["delta_null_minus_tabular"]["multiclass_brier"] > 0.0


def test_train_eval_trace_overlap_is_rejected(tmp_path):
    train_path, eval_path = _toy_files(tmp_path)
    train_first = json.loads(train_path.read_text(encoding="utf-8").splitlines()[0])
    eval_rows = eval_path.read_text(encoding="utf-8").splitlines()
    eval_rows[0] = json.dumps(train_first)
    eval_path.write_text("\n".join(eval_rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="trace_id overlap"):
        scorer.score_files(train_path, eval_path)


def test_train_eval_run_overlap_is_rejected(tmp_path):
    train_path, eval_path = _toy_files(tmp_path)
    train_first = json.loads(train_path.read_text(encoding="utf-8").splitlines()[0])
    eval_rows = [json.loads(row) for row in eval_path.read_text(encoding="utf-8").splitlines()]
    eval_rows[0]["commit"]["run_id"] = train_first["commit"]["run_id"]
    eval_rows[0]["outcome"]["run_id"] = train_first["commit"]["run_id"]
    restored = scorer.pre_action_commit_from_payload(eval_rows[0]["commit"])
    eval_rows[0]["outcome"]["commit_sha256"] = restored.sha256
    eval_path.write_text(
        "\n".join(json.dumps(row) for row in eval_rows) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="run_id overlap"):
        scorer.score_files(train_path, eval_path)


@pytest.mark.parametrize("overlap_kind", ["episode", "source"])
def test_train_eval_episode_or_source_overlap_is_rejected(tmp_path, overlap_kind):
    train_path, eval_path = _toy_files(tmp_path)
    train_first = json.loads(train_path.read_text(encoding="utf-8").splitlines()[0])
    eval_rows = [json.loads(row) for row in eval_path.read_text(encoding="utf-8").splitlines()]
    if overlap_kind == "episode":
        eval_rows[0]["commit"]["episode_id"] = train_first["commit"]["episode_id"]
        eval_rows[0]["outcome"]["episode_id"] = train_first["commit"]["episode_id"]
        match = "episode_id overlap"
    else:
        eval_rows[0]["outcome"]["source_observation"] = train_first["outcome"][
            "source_observation"
        ]
        match = "source observation overlap"
    # Identity edits change the canonical commit hash; rebind the outcome.
    commit = PreActionCommit(**{
        "trace_id": eval_rows[0]["commit"]["trace_id"],
        "run_id": eval_rows[0]["commit"]["run_id"],
        "domain": eval_rows[0]["commit"]["domain"],
        "episode_id": eval_rows[0]["commit"]["episode_id"],
        "step_index": eval_rows[0]["commit"]["step_index"],
        "event_index": eval_rows[0]["commit"]["event_index"],
        "committed_at_ns": eval_rows[0]["commit"]["committed_at_ns"],
        "state_ref": eval_rows[0]["commit"]["state_ref"],
        "action": eval_rows[0]["commit"]["action"],
        "status": eval_rows[0]["commit"]["status"],
        "estimator_id": eval_rows[0]["commit"]["estimator_id"],
        "estimator_kind": eval_rows[0]["commit"]["estimator_kind"],
        "reason": eval_rows[0]["commit"]["reason"],
    })
    eval_rows[0]["outcome"]["commit_sha256"] = commit.sha256
    eval_path.write_text(
        "\n".join(json.dumps(row) for row in eval_rows) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match=match):
        scorer.score_files(train_path, eval_path)


def test_source_id_cannot_change_hash(tmp_path):
    train_path, eval_path = _toy_files(tmp_path)
    train_first = json.loads(train_path.read_text(encoding="utf-8").splitlines()[0])
    eval_rows = [json.loads(row) for row in eval_path.read_text(encoding="utf-8").splitlines()]
    eval_rows[0]["outcome"]["source_observation"]["id"] = train_first["outcome"][
        "source_observation"
    ]["id"]
    eval_path.write_text(
        "\n".join(json.dumps(row) for row in eval_rows) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="conflicting hashes"):
        scorer.score_files(train_path, eval_path)


def test_eval_predictions_must_match_frozen_train_estimator():
    train_raw = [
        _pair("train-a-1", split="train", domain="ls20", state_ref="s", action="a", observation="x"),
        _pair("train-a-2", split="train", domain="ls20", state_ref="s", action="a", observation="x"),
        _pair("train-b-1", split="train", domain="ls20", state_ref="s", action="b", observation="y"),
        _pair("train-b-2", split="train", domain="ls20", state_ref="s", action="b", observation="y"),
    ]
    estimator = scorer.DirichletTabularEstimator(("x", "y"), estimator_id="frozen")
    for commit, outcome in train_raw:
        estimator.update(commit.state_ref, commit.action, outcome.observation)

    eval_raw = [
        _pair("eval-a", split="eval", domain="ls20", state_ref="s", action="a", observation="x"),
        _pair("eval-b", split="eval", domain="ls20", state_ref="s", action="b", observation="y"),
    ]
    eval_pairs = []
    for old_commit, old_outcome in eval_raw:
        commit = estimator.commit(
            trace_id=old_commit.trace_id,
            run_id=old_commit.run_id,
            domain=old_commit.domain,
            episode_id=old_commit.episode_id,
            step_index=old_commit.step_index,
            event_index=old_commit.event_index,
            committed_at_ns=old_commit.committed_at_ns,
            state_ref=old_commit.state_ref,
            action=old_commit.action,
        )
        outcome = OutcomeRecord(
            trace_id=old_outcome.trace_id,
            run_id=old_outcome.run_id,
            domain=old_outcome.domain,
            episode_id=old_outcome.episode_id,
            step_index=old_outcome.step_index,
            event_index=old_outcome.event_index,
            observed_at_ns=old_outcome.observed_at_ns,
            action=old_outcome.action,
            commit_sha256=commit.sha256,
            status="observed",
            observation=old_outcome.observation,
            source_observation=old_outcome.source_observation,
        )
        eval_pairs.append(scorer.TracePair(commit, outcome))
    train_pairs = [scorer.TracePair(commit, outcome) for commit, outcome in train_raw]
    result = scorer.score_trace_pairs(
        train_pairs,
        eval_pairs,
        observation_spaces={"ls20": ("x", "y")},
        action_spaces={"ls20": ("a", "b")},
        require_eval_commits=True,
        estimator_ids={"ls20": "frozen"},
    )
    assert result["eval_prediction_source"] == "durably_committed_train_frozen_baseline"
    assert result["domains"]["ls20"]["n_eval_runs"] == 1
    assert result["runs"]["synthetic-ls20-eval"]["n_eval"] == 2

    bad_commit = PreActionCommit(
        trace_id=eval_pairs[0].commit.trace_id,
        run_id=eval_pairs[0].commit.run_id,
        domain="ls20",
        episode_id=eval_pairs[0].commit.episode_id,
        step_index=0,
        event_index=0,
        committed_at_ns=100,
        state_ref="s",
        action="a",
        status="committed",
        estimator_id="frozen",
        estimator_kind="baseline",
        probabilities=(ObservationProbability("x", 0.5), ObservationProbability("y", 0.5)),
    )
    bad_outcome = OutcomeRecord(
        trace_id=eval_pairs[0].outcome.trace_id,
        run_id=eval_pairs[0].outcome.run_id,
        domain="ls20",
        episode_id=eval_pairs[0].outcome.episode_id,
        step_index=0,
        event_index=2,
        observed_at_ns=200,
        action="a",
        commit_sha256=bad_commit.sha256,
        status="observed",
        observation="x",
        source_observation=eval_pairs[0].outcome.source_observation,
    )
    with pytest.raises(ValueError, match="probabilities do not match"):
        scorer.score_trace_pairs(
            train_pairs,
            [scorer.TracePair(bad_commit, bad_outcome), eval_pairs[1]],
            observation_spaces={"ls20": ("x", "y")},
            action_spaces={"ls20": ("a", "b")},
            require_eval_commits=True,
            estimator_ids={"ls20": "frozen"},
        )


def test_declared_oracle_commit_is_rejected_as_answer_key_leakage(tmp_path):
    train_path, _ = _toy_files(tmp_path)
    commit, outcome = _pair(
        "eval-oracle", split="eval", domain="ls20", state_ref="locked",
        action="unlock", observation="open",
    )
    oracle_commit = PreActionCommit(
        trace_id=commit.trace_id,
        run_id=commit.run_id,
        domain=commit.domain,
        episode_id=commit.episode_id,
        step_index=commit.step_index,
        event_index=commit.event_index,
        committed_at_ns=commit.committed_at_ns,
        state_ref=commit.state_ref,
        action=commit.action,
        status="committed",
        estimator_id="fixture-answer-key",
        estimator_kind="oracle",
        declared_oracle=True,
        probabilities=(ObservationProbability("open", 1.0),),
    )
    leaked_outcome = OutcomeRecord(
        trace_id=outcome.trace_id,
        run_id=outcome.run_id,
        domain=outcome.domain,
        episode_id=outcome.episode_id,
        step_index=outcome.step_index,
        event_index=outcome.event_index,
        observed_at_ns=outcome.observed_at_ns,
        action=outcome.action,
        commit_sha256=oracle_commit.sha256,
        status=outcome.status,
        observation=outcome.observation,
        source_observation=outcome.source_observation,
    )
    eval_path = tmp_path / "oracle.jsonl"
    _write(eval_path, [(oracle_commit, leaked_outcome)])
    with pytest.raises(ValueError, match="answer-key leakage"):
        scorer.score_files(train_path, eval_path)


@pytest.mark.parametrize("leak_kind", ["timestamp", "source_kind"])
def test_pre_action_or_answer_key_source_leakage_is_rejected(tmp_path, leak_kind):
    train_path, eval_path = _toy_files(tmp_path)
    row = json.loads(eval_path.read_text(encoding="utf-8").splitlines()[0])
    if leak_kind == "timestamp":
        row["outcome"]["observed_at_ns"] = row["commit"]["committed_at_ns"]
        match = "observed_at_ns"
    else:
        row["outcome"]["source_observation"]["kind"] = "answer_key"
        match = "source observation kind"
    eval_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        scorer.score_files(train_path, eval_path)
