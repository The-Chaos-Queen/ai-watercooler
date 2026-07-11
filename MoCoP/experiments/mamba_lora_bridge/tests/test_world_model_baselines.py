from __future__ import annotations

import pytest

from world_model_baselines import (
    DeclaredOracle,
    DeterministicActionShuffleNull,
    DirichletTabularEstimator,
    EmpiricalMarginalEstimator,
)


def _probabilities(estimator, state="s", action="left") -> dict[str, float]:
    return {item.observation: item.probability for item in estimator.predict(state, action)}


def _commit_kwargs() -> dict:
    return {
        "trace_id": "t",
        "run_id": "r",
        "domain": "ls20",
        "episode_id": "e",
        "step_index": 0,
        "event_index": 0,
        "committed_at_ns": 100,
        "state_ref": "s",
        "action": "left",
    }


def test_dirichlet_unseen_cell_is_uniform():
    estimator = DirichletTabularEstimator(("ok", "blocked"), alpha=1.0)
    assert _probabilities(estimator) == {"ok": 0.5, "blocked": 0.5}


def test_dirichlet_update_is_state_action_conditional_and_smoothed():
    estimator = DirichletTabularEstimator(("ok", "blocked"), alpha=1.0)
    estimator.update("s", "left", "ok")
    estimator.update("s", "left", "ok")
    estimator.update("s", "left", "blocked")
    assert _probabilities(estimator) == pytest.approx({"ok": 3 / 5, "blocked": 2 / 5})
    assert _probabilities(estimator, action="right") == {"ok": 0.5, "blocked": 0.5}


def test_dirichlet_commit_is_a_pre_action_baseline_commit():
    estimator = DirichletTabularEstimator(("ok", "blocked"))
    commit = estimator.commit(**_commit_kwargs())
    assert commit.status == "committed"
    assert commit.estimator_kind == "baseline"
    assert len(commit.sha256) == 64


def test_dirichlet_snapshot_roundtrip_is_exact_and_fail_closed():
    estimator = DirichletTabularEstimator(("ok", "blocked"), estimator_id="frozen")
    estimator.update("s", "left", "ok", weight=2)
    payload = estimator.canonical_payload()
    restored = DirichletTabularEstimator.from_payload(payload)
    assert restored.canonical_payload() == payload
    payload["answer_key"] = "ok"
    with pytest.raises(ValueError, match="fields mismatch"):
        DirichletTabularEstimator.from_payload(payload)


def test_declared_oracle_is_point_mass_and_cannot_hide_its_status():
    oracle = DeclaredOracle(("ok", "blocked"), {("s", "left"): "ok"})
    commit = oracle.commit(**_commit_kwargs())
    assert commit.estimator_kind == "oracle"
    assert commit.declared_oracle is True
    assert _probabilities(oracle) == {"ok": 1.0, "blocked": 0.0}


def test_action_shuffle_is_deterministic_order_independent_derangement():
    base = DirichletTabularEstimator(("ok", "blocked"))
    first = DeterministicActionShuffleNull(base, ("left", "right", "wait"), seed="fixed")
    second = DeterministicActionShuffleNull(base, ("wait", "left", "right"), seed="fixed")
    assert first.action_mapping == second.action_mapping
    assert all(source != target for source, target in first.action_mapping.items())
    assert first.estimator_id == second.estimator_id


def test_action_shuffle_predicts_from_the_permuted_action_and_marks_null():
    base = DirichletTabularEstimator(("ok", "blocked"))
    base.update("s", "left", "ok", weight=9)
    base.update("s", "right", "blocked", weight=9)
    null = DeterministicActionShuffleNull(base, ("left", "right"), seed="fixed")
    assert null.action_mapping == {"left": "right", "right": "left"}
    assert _probabilities(null, action="left")["blocked"] > 0.8
    commit = null.commit(**_commit_kwargs())
    assert commit.estimator_kind == "null"
    assert commit.declared_oracle is False


def test_empirical_marginal_null_ignores_state_and_action():
    null = EmpiricalMarginalEstimator(("ok", "blocked"), alpha=1.0)
    null.update("ok", weight=3)
    null.update("blocked")
    first = _probabilities(null, state="s1", action="left")
    second = _probabilities(null, state="s2", action="right")
    assert first == second == pytest.approx({"ok": 4 / 6, "blocked": 2 / 6})
    commit = null.commit(**_commit_kwargs())
    assert commit.estimator_kind == "null"
    assert commit.status == "committed"
    restored = EmpiricalMarginalEstimator.from_payload(null.canonical_payload())
    assert restored.canonical_payload() == null.canonical_payload()


def test_baselines_reject_unknown_labels_and_degenerate_shuffle():
    estimator = DirichletTabularEstimator(("ok", "blocked"))
    with pytest.raises(ValueError):
        estimator.update("s", "left", "unknown")
    with pytest.raises(ValueError):
        DeterministicActionShuffleNull(estimator, ("left",), seed="fixed")
