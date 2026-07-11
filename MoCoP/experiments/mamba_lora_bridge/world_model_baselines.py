"""Offline baseline estimators for the world-model trace contract."""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from typing import Any, Mapping, Protocol, Sequence

from world_model_trace import ObservationProbability, PreActionCommit, canonical_sha256


class ProbabilityEstimator(Protocol):
    observation_space: tuple[str, ...]

    def predict(self, state_ref: str, action: str) -> tuple[ObservationProbability, ...]: ...


def _validated_space(observations: Sequence[str]) -> tuple[str, ...]:
    space = tuple(observations)
    if not space or any(not isinstance(item, str) or not item.strip() for item in space):
        raise ValueError("observation_space must contain non-empty strings")
    if any(item != item.strip() for item in space):
        raise ValueError("observation labels must not have surrounding whitespace")
    if len(space) != len(set(space)):
        raise ValueError("observation_space labels must be unique")
    return space


def _require_key(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a non-empty trimmed string")
    return value


class DirichletTabularEstimator:
    """Categorical ``P(observation | state, action)`` with symmetric smoothing."""

    def __init__(
        self,
        observation_space: Sequence[str],
        *,
        alpha: float = 1.0,
        estimator_id: str = "dirichlet-tabular-v1",
    ) -> None:
        self.observation_space = _validated_space(observation_space)
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
            raise ValueError("alpha must be a positive finite number")
        self.alpha = float(alpha)
        if not math.isfinite(self.alpha) or self.alpha <= 0.0:
            raise ValueError("alpha must be a positive finite number")
        self.estimator_id = _require_key(estimator_id, "estimator_id")
        self._counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    def update(
        self,
        state_ref: str,
        action: str,
        observation: str,
        *,
        weight: float = 1.0,
    ) -> None:
        key = (_require_key(state_ref, "state_ref"), _require_key(action, "action"))
        if observation not in self.observation_space:
            raise ValueError(f"unknown observation {observation!r}")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("weight must be a positive finite number")
        weight = float(weight)
        if not math.isfinite(weight) or weight <= 0.0:
            raise ValueError("weight must be a positive finite number")
        self._counts[key][observation] += weight

    def predict(self, state_ref: str, action: str) -> tuple[ObservationProbability, ...]:
        key = (_require_key(state_ref, "state_ref"), _require_key(action, "action"))
        counts = self._counts.get(key, Counter())
        denominator = math.fsum(counts.values()) + self.alpha * len(self.observation_space)
        return tuple(
            ObservationProbability(
                observation,
                (float(counts[observation]) + self.alpha) / denominator,
            )
            for observation in self.observation_space
        )

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
            status="committed",
            estimator_id=self.estimator_id,
            estimator_kind="baseline",
            probabilities=self.predict(state_ref, action),
        )

    def canonical_payload(self) -> dict[str, Any]:
        counts = [
            {
                "state_ref": state_ref,
                "action": action,
                "observation": observation,
                "weight": float(weight),
            }
            for (state_ref, action), observations in sorted(self._counts.items())
            for observation, weight in sorted(observations.items())
        ]
        return {
            "schema_version": "dirichlet-tabular-v1",
            "estimator_id": self.estimator_id,
            "alpha": self.alpha,
            "observation_space": list(self.observation_space),
            "counts": counts,
        }

    @classmethod
    def from_payload(cls, payload: Any) -> "DirichletTabularEstimator":
        expected = {
            "schema_version",
            "estimator_id",
            "alpha",
            "observation_space",
            "counts",
        }
        if not isinstance(payload, dict) or set(payload) != expected:
            raise ValueError("Dirichlet estimator payload fields mismatch")
        if payload["schema_version"] != "dirichlet-tabular-v1":
            raise ValueError("Dirichlet estimator schema_version mismatch")
        if not isinstance(payload["counts"], list):
            raise ValueError("Dirichlet estimator counts must be a list")
        estimator = cls(
            payload["observation_space"],
            alpha=payload["alpha"],
            estimator_id=payload["estimator_id"],
        )
        count_fields = {"state_ref", "action", "observation", "weight"}
        for row in payload["counts"]:
            if not isinstance(row, dict) or set(row) != count_fields:
                raise ValueError("Dirichlet estimator count fields mismatch")
            estimator.update(
                row["state_ref"],
                row["action"],
                row["observation"],
                weight=row["weight"],
            )
        if estimator.canonical_payload() != payload:
            raise ValueError("Dirichlet estimator payload is not canonical")
        return estimator


class EmpiricalMarginalEstimator:
    """Categorical train-only ``P(observation)`` null with symmetric smoothing."""

    def __init__(
        self,
        observation_space: Sequence[str],
        *,
        alpha: float = 1.0,
        estimator_id: str = "empirical-marginal-null-v1",
    ) -> None:
        self.observation_space = _validated_space(observation_space)
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
            raise ValueError("alpha must be a positive finite number")
        self.alpha = float(alpha)
        if not math.isfinite(self.alpha) or self.alpha <= 0.0:
            raise ValueError("alpha must be a positive finite number")
        self.estimator_id = _require_key(estimator_id, "estimator_id")
        self._counts: Counter[str] = Counter()

    def update(self, observation: str, *, weight: float = 1.0) -> None:
        if observation not in self.observation_space:
            raise ValueError(f"unknown observation {observation!r}")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError("weight must be a positive finite number")
        weight = float(weight)
        if not math.isfinite(weight) or weight <= 0.0:
            raise ValueError("weight must be a positive finite number")
        self._counts[observation] += weight

    def predict(self, state_ref: str, action: str) -> tuple[ObservationProbability, ...]:
        _require_key(state_ref, "state_ref")
        _require_key(action, "action")
        denominator = math.fsum(self._counts.values()) + self.alpha * len(
            self.observation_space
        )
        return tuple(
            ObservationProbability(
                observation,
                (float(self._counts[observation]) + self.alpha) / denominator,
            )
            for observation in self.observation_space
        )

    def commit(self, **kwargs) -> PreActionCommit:
        return PreActionCommit(
            **kwargs,
            status="committed",
            estimator_id=self.estimator_id,
            estimator_kind="null",
            probabilities=self.predict(kwargs["state_ref"], kwargs["action"]),
        )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "empirical-marginal-null-v1",
            "estimator_id": self.estimator_id,
            "alpha": self.alpha,
            "observation_space": list(self.observation_space),
            "counts": [
                {"observation": observation, "weight": float(weight)}
                for observation, weight in sorted(self._counts.items())
            ],
        }

    @classmethod
    def from_payload(cls, payload: Any) -> "EmpiricalMarginalEstimator":
        expected = {
            "schema_version",
            "estimator_id",
            "alpha",
            "observation_space",
            "counts",
        }
        if not isinstance(payload, dict) or set(payload) != expected:
            raise ValueError("marginal estimator payload fields mismatch")
        if payload["schema_version"] != "empirical-marginal-null-v1":
            raise ValueError("marginal estimator schema_version mismatch")
        if not isinstance(payload["counts"], list):
            raise ValueError("marginal estimator counts must be a list")
        estimator = cls(
            payload["observation_space"],
            alpha=payload["alpha"],
            estimator_id=payload["estimator_id"],
        )
        for row in payload["counts"]:
            if not isinstance(row, dict) or set(row) != {"observation", "weight"}:
                raise ValueError("marginal estimator count fields mismatch")
            estimator.update(row["observation"], weight=row["weight"])
        if estimator.canonical_payload() != payload:
            raise ValueError("marginal estimator payload is not canonical")
        return estimator


class DeclaredOracle:
    """Explicitly labelled point-mass oracle; never confusable with a model score."""

    def __init__(
        self,
        observation_space: Sequence[str],
        outcomes: Mapping[tuple[str, str], str],
        *,
        estimator_id: str = "declared-oracle-v1",
    ) -> None:
        self.observation_space = _validated_space(observation_space)
        self.estimator_id = _require_key(estimator_id, "estimator_id")
        self._outcomes: dict[tuple[str, str], str] = {}
        for (state_ref, action), observation in outcomes.items():
            key = (_require_key(state_ref, "state_ref"), _require_key(action, "action"))
            if observation not in self.observation_space:
                raise ValueError(f"oracle outcome {observation!r} is outside observation_space")
            self._outcomes[key] = observation

    def predict(self, state_ref: str, action: str) -> tuple[ObservationProbability, ...]:
        key = (_require_key(state_ref, "state_ref"), _require_key(action, "action"))
        if key not in self._outcomes:
            raise KeyError(f"oracle has no declared outcome for {key!r}")
        expected = self._outcomes[key]
        return tuple(
            ObservationProbability(observation, float(observation == expected))
            for observation in self.observation_space
        )

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
            status="committed",
            estimator_id=self.estimator_id,
            estimator_kind="oracle",
            declared_oracle=True,
            probabilities=self.predict(state_ref, action),
        )


class DeterministicActionShuffleNull:
    """Null estimator that predicts using a deterministic derangement of actions."""

    def __init__(
        self,
        estimator: ProbabilityEstimator,
        actions: Sequence[str],
        *,
        seed: str,
    ) -> None:
        self.estimator = estimator
        self.observation_space = estimator.observation_space
        self.seed = _require_key(seed, "seed")
        action_set = {_require_key(action, "action") for action in actions}
        if len(action_set) < 2:
            raise ValueError("action-shuffle null requires at least two unique actions")
        ordered = sorted(
            action_set,
            key=lambda action: hashlib.sha256(f"{self.seed}\0{action}".encode("utf-8")).hexdigest(),
        )
        offset_digest = hashlib.sha256(f"{self.seed}\0offset".encode("utf-8")).hexdigest()
        offset = 1 + int(offset_digest, 16) % (len(ordered) - 1)
        self._mapping = {
            action: ordered[(index + offset) % len(ordered)]
            for index, action in enumerate(ordered)
        }
        mapping_hash = canonical_sha256({"seed": self.seed, "mapping": self._mapping})
        self.estimator_id = f"action-shuffle-null-v1:{mapping_hash[:16]}"

    @property
    def action_mapping(self) -> dict[str, str]:
        return dict(self._mapping)

    def predict(self, state_ref: str, action: str) -> tuple[ObservationProbability, ...]:
        action = _require_key(action, "action")
        if action not in self._mapping:
            raise KeyError(f"action {action!r} is outside the declared shuffle set")
        return self.estimator.predict(state_ref, self._mapping[action])

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
            status="committed",
            estimator_id=self.estimator_id,
            estimator_kind="null",
            probabilities=self.predict(state_ref, action),
        )
