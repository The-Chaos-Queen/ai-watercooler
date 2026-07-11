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
from typing import Any, Sequence


BRIDGE_DIR = Path(__file__).resolve().parents[1]
if str(BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_DIR))

from world_model_baselines import (  # noqa: E402
    DeterministicActionShuffleNull,
    DirichletTabularEstimator,
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


def score_trace_pairs(
    train_pairs: Sequence[TracePair],
    eval_pairs: Sequence[TracePair],
    *,
    alpha: float = 1.0,
    shuffle_seed: str = "world-model-phase1-v1",
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
    train_sources = {
        (pair.outcome.source_observation.source_id, pair.outcome.source_observation.sha256)
        for pair in train_pairs
        if pair.outcome.source_observation is not None
    }
    eval_sources = {
        (pair.outcome.source_observation.source_id, pair.outcome.source_observation.sha256)
        for pair in eval_pairs
        if pair.outcome.source_observation is not None
    }
    source_overlap = sorted(train_sources & eval_sources)
    if source_overlap:
        raise ValueError(f"train/eval source observation overlap: {source_overlap}")

    domains = sorted({pair.commit.domain for pair in train_pairs})
    estimators: dict[str, DirichletTabularEstimator] = {}
    nulls: dict[str, DeterministicActionShuffleNull] = {}
    for domain in domains:
        domain_train = [pair for pair in train_pairs if pair.commit.domain == domain]
        raw_observations = {pair.outcome.observation for pair in domain_train}
        actions = sorted({pair.commit.action for pair in domain_train})
        if None in raw_observations:
            raise ValueError(f"domain {domain!r} contains an unobserved training outcome")
        observations = sorted(
            observation for observation in raw_observations if observation is not None
        )
        if len(observations) < 2:
            raise ValueError(f"domain {domain!r} requires at least two training outcomes")
        if len(actions) < 2:
            raise ValueError(f"domain {domain!r} requires at least two training actions")
        estimator = DirichletTabularEstimator(
            tuple(observations), alpha=alpha, estimator_id=f"dirichlet-tabular-v1:{domain}"
        )
        for pair in domain_train:
            estimator.update(
                pair.commit.state_ref,
                pair.commit.action,
                pair.outcome.observation,
            )
        estimators[domain] = estimator
        nulls[domain] = DeterministicActionShuffleNull(
            estimator, actions, seed=f"{shuffle_seed}:{domain}"
        )

    tabular_nll: list[float] = []
    tabular_brier: list[float] = []
    null_nll: list[float] = []
    null_brier: list[float] = []
    per_domain: dict[str, dict[str, Any]] = {}
    for pair in eval_pairs:
        domain = pair.commit.domain
        if domain not in estimators:
            raise ValueError(f"eval domain {domain!r} has no training partition")
        observation = pair.outcome.observation
        if observation is None:
            raise ValueError(f"eval trace {pair.commit.trace_id!r} has no observed outcome")
        estimator = estimators[domain]
        null = nulls[domain]
        if observation not in estimator.observation_space:
            raise ValueError(
                f"eval observation {observation!r} was absent from domain {domain!r} training"
            )
        tabular_probabilities = estimator.predict(pair.commit.state_ref, pair.commit.action)
        null_probabilities = null.predict(pair.commit.state_ref, pair.commit.action)
        scores = (
            categorical_nll(tabular_probabilities, observation),
            multiclass_brier(tabular_probabilities, observation),
            categorical_nll(null_probabilities, observation),
            multiclass_brier(null_probabilities, observation),
        )
        tabular_nll.append(scores[0])
        tabular_brier.append(scores[1])
        null_nll.append(scores[2])
        null_brier.append(scores[3])
        bucket = per_domain.setdefault(
            domain,
            {
                "n_eval": 0,
                "tabular_nll": [],
                "tabular_brier": [],
                "null_nll": [],
                "null_brier": [],
                "action_mapping": null.action_mapping,
            },
        )
        bucket["n_eval"] += 1
        bucket["tabular_nll"].append(scores[0])
        bucket["tabular_brier"].append(scores[1])
        bucket["null_nll"].append(scores[2])
        bucket["null_brier"].append(scores[3])

    for bucket in per_domain.values():
        bucket["metrics"] = {
            "tabular": {
                "categorical_nll": _mean(bucket.pop("tabular_nll")),
                "multiclass_brier": _mean(bucket.pop("tabular_brier")),
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

    metrics = {
        "tabular": {
            "categorical_nll": _mean(tabular_nll),
            "multiclass_brier": _mean(tabular_brier),
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
        "metric_contract": {
            "categorical_nll": {"unit": "nats", "lower_is_better": True},
            "multiclass_brier": {
                "unit": "squared_probability",
                "lower_is_better": True,
            },
            "delta_definition": "action_shuffle_null_minus_tabular",
        },
        "metrics": metrics,
        "delta_null_minus_tabular": {
            metric: metrics["action_shuffle_null"][metric] - metrics["tabular"][metric]
            for metric in ("categorical_nll", "multiclass_brier")
        },
        "domains": per_domain,
    }


def score_files(
    train_path: Path,
    eval_path: Path,
    *,
    alpha: float = 1.0,
    shuffle_seed: str = "world-model-phase1-v1",
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
