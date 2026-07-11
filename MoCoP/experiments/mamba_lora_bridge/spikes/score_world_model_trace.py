#!/usr/bin/env python3
"""Score an offline Phase-1 world-model transition trace.

Input JSONL rows have exactly two objects: ``commit`` and ``outcome``. Training
and evaluation files are intentionally separate; this scorer rejects shared
trace IDs and any record whose outcome was not provenance-bound after its
pre-action commit.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


BRIDGE_DIR = Path(__file__).resolve().parents[1]
if str(BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_DIR))

from world_model_baselines import (  # noqa: E402
    DeterministicActionShuffleNull,
    DirichletTabularEstimator,
    EmpiricalMarginalEstimator,
)
from world_model_trace import (  # noqa: E402
    OutcomeRecord,
    PreActionCommit,
    outcome_record_from_payload,
    pre_action_commit_from_payload,
    validate_trace_pair,
)


SCORE_SCHEMA_VERSION = "world-model-score-v1"


@dataclass(frozen=True, slots=True)
class TracePair:
    commit: PreActionCommit
    outcome: OutcomeRecord


def load_trace_pairs(path: Path) -> list[TracePair]:
    """Load, type-check, and order-check one transition JSONL file."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"trace file does not exist: {path}")
    pairs: list[TracePair] = []
    seen_trace_ids: set[str] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict) or set(row) != {"commit", "outcome"}:
            raise ValueError(
                f"{path}:{line_number}: each row must contain exactly commit and outcome"
            )
        try:
            commit = pre_action_commit_from_payload(row["commit"])
            outcome = outcome_record_from_payload(row["outcome"])
            validate_trace_pair(commit, outcome)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if commit.trace_id in seen_trace_ids:
            raise ValueError(f"{path}:{line_number}: duplicate trace_id {commit.trace_id!r}")
        seen_trace_ids.add(commit.trace_id)
        if commit.declared_oracle or commit.estimator_kind == "oracle":
            raise ValueError(
                f"{path}:{line_number}: declared oracle commits are answer-key leakage"
            )
        if outcome.status != "observed":
            raise ValueError(
                f"{path}:{line_number}: scorer requires outcome status observed, "
                f"got {outcome.status!r}"
            )
        pairs.append(TracePair(commit, outcome))
    if not pairs:
        raise ValueError(f"trace file is empty: {path}")
    return pairs


def _distribution_dict(probabilities) -> dict[str, float]:
    return {item.observation: item.probability for item in probabilities}


def categorical_nll(probabilities, observation: str) -> float:
    distribution = _distribution_dict(probabilities)
    if observation not in distribution:
        raise ValueError(f"observation {observation!r} is outside prediction support")
    probability = distribution[observation]
    if not 0.0 < probability <= 1.0:
        raise ValueError("categorical NLL requires a finite nonzero outcome probability")
    return -math.log(probability)


def multiclass_brier(probabilities, observation: str) -> float:
    distribution = _distribution_dict(probabilities)
    if observation not in distribution:
        raise ValueError(f"observation {observation!r} is outside prediction support")
    return math.fsum(
        (probability - float(label == observation)) ** 2
        for label, probability in distribution.items()
    )


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot score an empty metric list")
    return math.fsum(values) / len(values)


def _score_bucket(*, action_mapping: dict[str, str] | None = None) -> dict[str, Any]:
    bucket: dict[str, Any] = {
        "n_eval": 0,
        "tabular_nll": [],
        "tabular_brier": [],
        "marginal_nll": [],
        "marginal_brier": [],
        "null_nll": [],
        "null_brier": [],
    }
    if action_mapping is not None:
        bucket["action_mapping"] = action_mapping
    return bucket


def _append_scores(bucket: dict[str, Any], scores: tuple[float, ...]) -> None:
    bucket["n_eval"] += 1
    for key, value in zip(
        (
            "tabular_nll",
            "tabular_brier",
            "marginal_nll",
            "marginal_brier",
            "null_nll",
            "null_brier",
        ),
        scores,
        strict=True,
    ):
        bucket[key].append(value)


def _finalize_score_bucket(bucket: dict[str, Any]) -> None:
    bucket["metrics"] = {
        "tabular": {
            "categorical_nll": _mean(bucket.pop("tabular_nll")),
            "multiclass_brier": _mean(bucket.pop("tabular_brier")),
        },
        "empirical_marginal_null": {
            "categorical_nll": _mean(bucket.pop("marginal_nll")),
            "multiclass_brier": _mean(bucket.pop("marginal_brier")),
        },
        "action_shuffle_null": {
            "categorical_nll": _mean(bucket.pop("null_nll")),
            "multiclass_brier": _mean(bucket.pop("null_brier")),
        },
    }
    bucket["delta_null_minus_tabular"] = {
        metric: bucket["metrics"]["action_shuffle_null"][metric]
        - bucket["metrics"]["tabular"][metric]
        for metric in ("categorical_nll", "multiclass_brier")
    }
    bucket["delta_marginal_minus_tabular"] = {
        metric: bucket["metrics"]["empirical_marginal_null"][metric]
        - bucket["metrics"]["tabular"][metric]
        for metric in ("categorical_nll", "multiclass_brier")
    }


def score_trace_pairs(
    train_pairs: Sequence[TracePair],
    eval_pairs: Sequence[TracePair],
    *,
    alpha: float = 1.0,
    shuffle_seed: str = "world-model-phase1-v1",
    observation_spaces: Mapping[str, Sequence[str]] | None = None,
    action_spaces: Mapping[str, Sequence[str]] | None = None,
    require_eval_commits: bool = False,
    estimator_ids: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Fit train-only tabular models and score untouched evaluation outcomes."""
    train_ids = {pair.commit.trace_id for pair in train_pairs}
    eval_ids = {pair.commit.trace_id for pair in eval_pairs}
    overlap = sorted(train_ids & eval_ids)
    if overlap:
        raise ValueError(f"train/eval trace_id overlap: {overlap}")
    train_episodes = {pair.commit.episode_id for pair in train_pairs}
    eval_episodes = {pair.commit.episode_id for pair in eval_pairs}
    episode_overlap = sorted(train_episodes & eval_episodes)
    if episode_overlap:
        raise ValueError(f"train/eval episode_id overlap: {episode_overlap}")
    train_runs = {pair.commit.run_id for pair in train_pairs}
    eval_runs = {pair.commit.run_id for pair in eval_pairs}
    run_overlap = sorted(train_runs & eval_runs)
    if run_overlap:
        raise ValueError(f"train/eval run_id overlap: {run_overlap}")
    all_pairs = tuple(train_pairs) + tuple(eval_pairs)
    source_hashes_by_id: dict[str, str] = {}
    for pair in all_pairs:
        source = pair.outcome.source_observation
        if source is None:
            continue
        previous = source_hashes_by_id.setdefault(source.source_id, source.sha256)
        if previous != source.sha256:
            raise ValueError(
                f"source observation id {source.source_id!r} has conflicting hashes"
            )
    train_sources = {
        pair.outcome.source_observation.source_id
        for pair in train_pairs
        if pair.outcome.source_observation is not None
    }
    eval_sources = {
        pair.outcome.source_observation.source_id
        for pair in eval_pairs
        if pair.outcome.source_observation is not None
    }
    source_overlap = sorted(train_sources & eval_sources)
    if source_overlap:
        raise ValueError(f"train/eval source observation overlap: {source_overlap}")

    domains = sorted({pair.commit.domain for pair in train_pairs})
    estimators: dict[str, DirichletTabularEstimator] = {}
    marginals: dict[str, EmpiricalMarginalEstimator] = {}
    nulls: dict[str, DeterministicActionShuffleNull] = {}
    training_support: dict[str, dict[str, Any]] = {}
    for domain in domains:
        domain_train = [pair for pair in train_pairs if pair.commit.domain == domain]
        raw_observations = {pair.outcome.observation for pair in domain_train}
        observed_actions = {pair.commit.action for pair in domain_train}
        if None in raw_observations:
            raise ValueError(f"domain {domain!r} contains an unobserved training outcome")
        observations = (
            list(observation_spaces[domain])
            if observation_spaces is not None and domain in observation_spaces
            else sorted(observation for observation in raw_observations if observation is not None)
        )
        actions = (
            list(action_spaces[domain])
            if action_spaces is not None and domain in action_spaces
            else sorted(observed_actions)
        )
        if len(observations) < 2:
            raise ValueError(f"domain {domain!r} requires at least two training outcomes")
        if len(actions) < 2:
            raise ValueError(f"domain {domain!r} requires at least two training actions")
        training_support[domain] = {
            "n_train": len(domain_train),
            "n_state_refs": len({pair.commit.state_ref for pair in domain_train}),
            "n_state_action_cells": len(
                {(pair.commit.state_ref, pair.commit.action) for pair in domain_train}
            ),
            "action_counts": {
                action: sum(pair.commit.action == action for pair in domain_train)
                for action in actions
            },
            "observation_counts": {
                observation: sum(pair.outcome.observation == observation for pair in domain_train)
                for observation in observations
            },
        }
        unknown_observations = sorted(set(raw_observations) - set(observations))
        if unknown_observations:
            raise ValueError(
                f"domain {domain!r} training observations outside declared space: "
                f"{unknown_observations}"
            )
        unknown_actions = sorted(observed_actions - set(actions))
        if unknown_actions:
            raise ValueError(
                f"domain {domain!r} training actions outside declared space: {unknown_actions}"
            )
        estimator = DirichletTabularEstimator(
            tuple(observations),
            alpha=alpha,
            estimator_id=(
                estimator_ids[domain]
                if estimator_ids is not None and domain in estimator_ids
                else f"dirichlet-tabular-v1:{domain}"
            ),
        )
        marginal = EmpiricalMarginalEstimator(
            tuple(observations),
            alpha=alpha,
            estimator_id=f"empirical-marginal-null-v1:{domain}",
        )
        for pair in domain_train:
            estimator.update(
                pair.commit.state_ref,
                pair.commit.action,
                pair.outcome.observation,
            )
            marginal.update(pair.outcome.observation)
        estimators[domain] = estimator
        marginals[domain] = marginal
        nulls[domain] = DeterministicActionShuffleNull(
            estimator, actions, seed=f"{shuffle_seed}:{domain}"
        )

    tabular_nll: list[float] = []
    tabular_brier: list[float] = []
    null_nll: list[float] = []
    null_brier: list[float] = []
    marginal_nll: list[float] = []
    marginal_brier: list[float] = []
    per_domain: dict[str, dict[str, Any]] = {}
    per_run: dict[str, dict[str, Any]] = {}
    for pair in eval_pairs:
        domain = pair.commit.domain
        if domain not in estimators:
            raise ValueError(f"eval domain {domain!r} has no training partition")
        observation = pair.outcome.observation
        if observation is None:
            raise ValueError(f"eval trace {pair.commit.trace_id!r} has no observed outcome")
        estimator = estimators[domain]
        marginal = marginals[domain]
        null = nulls[domain]
        if observation not in estimator.observation_space:
            raise ValueError(
                f"eval observation {observation!r} was absent from domain {domain!r} training"
            )
        fitted_probabilities = estimator.predict(pair.commit.state_ref, pair.commit.action)
        if require_eval_commits:
            if pair.commit.status != "committed" or pair.commit.estimator_kind != "baseline":
                raise ValueError(
                    f"eval trace {pair.commit.trace_id!r} lacks a committed baseline prediction"
                )
            if pair.commit.estimator_id != estimator.estimator_id:
                raise ValueError(
                    f"eval trace {pair.commit.trace_id!r} estimator_id does not match the "
                    "frozen train estimator"
                )
            if pair.commit.probabilities != fitted_probabilities:
                raise ValueError(
                    f"eval trace {pair.commit.trace_id!r} probabilities do not match the "
                    "frozen train estimator"
                )
            tabular_probabilities = pair.commit.probabilities
        else:
            tabular_probabilities = fitted_probabilities
        marginal_probabilities = marginal.predict(pair.commit.state_ref, pair.commit.action)
        null_probabilities = null.predict(pair.commit.state_ref, pair.commit.action)
        scores = (
            categorical_nll(tabular_probabilities, observation),
            multiclass_brier(tabular_probabilities, observation),
            categorical_nll(marginal_probabilities, observation),
            multiclass_brier(marginal_probabilities, observation),
            categorical_nll(null_probabilities, observation),
            multiclass_brier(null_probabilities, observation),
        )
        tabular_nll.append(scores[0])
        tabular_brier.append(scores[1])
        marginal_nll.append(scores[2])
        marginal_brier.append(scores[3])
        null_nll.append(scores[4])
        null_brier.append(scores[5])
        bucket = per_domain.setdefault(
            domain, _score_bucket(action_mapping=null.action_mapping)
        )
        _append_scores(bucket, scores)
        run_bucket = per_run.setdefault(pair.commit.run_id, _score_bucket())
        run_bucket.setdefault("domain", domain)
        if run_bucket["domain"] != domain:
            raise ValueError(f"eval run_id {pair.commit.run_id!r} spans multiple domains")
        _append_scores(run_bucket, scores)

    for bucket in per_domain.values():
        _finalize_score_bucket(bucket)
    for bucket in per_run.values():
        _finalize_score_bucket(bucket)
    for domain, bucket in per_domain.items():
        bucket["n_eval_runs"] = sum(
            run_bucket["domain"] == domain for run_bucket in per_run.values()
        )

    metrics = {
        "tabular": {
            "categorical_nll": _mean(tabular_nll),
            "multiclass_brier": _mean(tabular_brier),
        },
        "empirical_marginal_null": {
            "categorical_nll": _mean(marginal_nll),
            "multiclass_brier": _mean(marginal_brier),
        },
        "action_shuffle_null": {
            "categorical_nll": _mean(null_nll),
            "multiclass_brier": _mean(null_brier),
        },
    }
    return {
        "schema_version": SCORE_SCHEMA_VERSION,
        "n_train": len(train_pairs),
        "n_eval": len(eval_pairs),
        "alpha": float(alpha),
        "shuffle_seed": shuffle_seed,
        "eval_prediction_source": (
            "durably_committed_train_frozen_baseline"
            if require_eval_commits
            else "offline_train_fitted_baseline"
        ),
        "metric_contract": {
            "categorical_nll": {"unit": "nats", "lower_is_better": True},
            "multiclass_brier": {
                "unit": "squared_probability",
                "lower_is_better": True,
                "formula": "sum_k (p_k - 1[k == observed])^2",
                "range": [0.0, 2.0],
            },
            "delta_definitions": {
                "delta_null_minus_tabular": "action_shuffle_null_minus_tabular",
                "delta_marginal_minus_tabular": "empirical_marginal_null_minus_tabular",
            },
        },
        "metrics": metrics,
        "declared_spaces": {
            domain: {
                "actions": list(action_spaces[domain]) if action_spaces and domain in action_spaces else sorted({pair.commit.action for pair in train_pairs if pair.commit.domain == domain}),
                "observations": list(observation_spaces[domain]) if observation_spaces and domain in observation_spaces else sorted({pair.outcome.observation for pair in train_pairs if pair.commit.domain == domain}),
            }
            for domain in domains
        },
        "delta_null_minus_tabular": {
            metric: metrics["action_shuffle_null"][metric] - metrics["tabular"][metric]
            for metric in ("categorical_nll", "multiclass_brier")
        },
        "delta_marginal_minus_tabular": {
            metric: metrics["empirical_marginal_null"][metric] - metrics["tabular"][metric]
            for metric in ("categorical_nll", "multiclass_brier")
        },
        "domains": per_domain,
        "runs": per_run,
        "training_support": training_support,
    }


def score_files(
    train_path: Path,
    eval_path: Path,
    *,
    alpha: float = 1.0,
    shuffle_seed: str = "world-model-phase1-v1",
    observation_spaces: Mapping[str, Sequence[str]] | None = None,
    action_spaces: Mapping[str, Sequence[str]] | None = None,
    require_eval_commits: bool = False,
    estimator_ids: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    train_path = Path(train_path)
    eval_path = Path(eval_path)
    if train_path.resolve() == eval_path.resolve():
        raise ValueError("--train and --eval must be different JSONL files")
    return score_trace_pairs(
        load_trace_pairs(train_path),
        load_trace_pairs(eval_path),
        alpha=alpha,
        shuffle_seed=shuffle_seed,
        observation_spaces=observation_spaces,
        action_spaces=action_spaces,
        require_eval_commits=require_eval_commits,
        estimator_ids=estimator_ids,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True, help="training transition JSONL")
    parser.add_argument("--eval", type=Path, required=True, help="disjoint evaluation JSONL")
    parser.add_argument("--alpha", type=float, default=1.0, help="Dirichlet smoothing alpha")
    parser.add_argument("--shuffle-seed", default="world-model-phase1-v1")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = score_files(
            args.train,
            args.eval,
            alpha=args.alpha,
            shuffle_seed=args.shuffle_seed,
        )
    except (KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
