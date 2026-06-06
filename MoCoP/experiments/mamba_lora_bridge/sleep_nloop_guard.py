"""
Abort guard for the A3 sleep N-loop shadow experiment.

Task #121 (Cairn) — the abort-guard half of #120. Implements Zwoelf's four #530
per-pass abort conditions as a PURE POLICY module: the tension metric is injected,
so this never imports chat_server (the live monolith) and is unit-testable in isolation.
run_shadow_sleep_nloop_a3.py imports this and passes the real compute_tension_proxy.

Conditions (Zwoelf #530):
  1. Tension firewall  - per-memory tension delta must be <= tension_epsilon. Any positive
     delta beyond epsilon on ANY memory aborts. epsilon is calibrated from the A1
     frozen-state pass-to-pass jitter (run A1 once to measure the zero-signal floor).
  2. Protected kinds   - zero KEEP -> WEAKEN/DISCARD/FORGOTTEN decision flips on protected
     kinds (identity_anchor, relationship_anchor, correction). Any such flip aborts.
  3. Forgotten-count   - pass-N forgotten count must not exceed the N=1 baseline by more than
     forgotten_margin; the global forgotten ratio >= 0.30 per cycle also aborts (hard stop).
  4. Convergence       - aggregate per-pass tension movement must shrink pass-over-pass. If a
     pass's movement exceeds the previous pass's (beyond epsilon) that is runaway -> abort.
     Movement below convergence_floor sets converged=True ("safe to consider N+1").

compute_tension_proxy CONTRACT (chat_server.py:1110):
  tension_fn(pre, user, post) -> {"score": float in [0,2], ...}  (0=aligned, 2=opposed; higher=more tension)

OPEN DESIGN Q (flagged to Zwoelf, #535): compute_tension_proxy was built for LIVE turns
(user-direction vs response-direction). Offline consolidation has no user/response turn, so
the caller must define pre/user/post per memory for the offline setting (or fall back to a
2-snapshot drift via compute_drift). This guard is metric-agnostic - it consumes per-memory
tension SCORES - so that question lives in the caller, not here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

KEEP = "KEEP"
WEAKEN = "WEAKEN"
DISCARD = "DISCARD"
FORGOTTEN = "FORGOTTEN"
_WEAKENED = frozenset({WEAKEN, DISCARD, FORGOTTEN})

DEFAULT_PROTECTED_KINDS = frozenset({"identity_anchor", "relationship_anchor", "correction"})


@dataclass(frozen=True)
class MemoryState:
    """One memory's state at the end of a pass."""
    id: str
    kind: str          # identity_anchor | relationship_anchor | correction | episodic | ...
    decision: str      # KEEP | WEAKEN | DISCARD | FORGOTTEN
    tension: float     # per-memory tension score (higher = more tension)


@dataclass
class PassVerdict:
    pass_num: int
    abort: bool
    reasons: list
    converged: bool
    pass_movement: float
    forgotten_count: int
    metrics: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.abort


class NLoopAbortGuard:
    """Stateful across passes (tracks the N=1 baseline and previous-pass movement)."""

    def __init__(
        self,
        tension_epsilon: float,
        forgotten_margin: int = 0,
        global_forgotten_ratio_stop: float = 0.30,
        protected_kinds: Sequence[str] = DEFAULT_PROTECTED_KINDS,
        convergence_floor: Optional[float] = None,
    ):
        if tension_epsilon < 0:
            raise ValueError("tension_epsilon must be >= 0 (it is a noise floor)")
        self.tension_epsilon = float(tension_epsilon)
        self.forgotten_margin = int(forgotten_margin)
        self.global_forgotten_ratio_stop = float(global_forgotten_ratio_stop)
        self.protected_kinds = frozenset(protected_kinds)
        self.convergence_floor = (
            float(convergence_floor) if convergence_floor is not None else max(self.tension_epsilon, 1e-9)
        )
        self._baseline_forgotten: Optional[int] = None
        self._prev_movement: Optional[float] = None

    def register_baseline(self, baseline: Sequence[MemoryState]) -> None:
        """Record the N=1 baseline pass. Required before condition 3 can bind to a baseline."""
        self._baseline_forgotten = sum(1 for m in baseline if m.decision == FORGOTTEN)

    def evaluate_pass(
        self,
        pass_num: int,
        prev: Sequence[MemoryState],
        curr: Sequence[MemoryState],
    ) -> PassVerdict:
        prev_by_id = {m.id: m for m in prev}
        reasons: list = []
        movements: list = []
        worst_delta: Optional[float] = None

        # --- Condition 1: per-memory tension delta <= epsilon ---
        for m in curr:
            p = prev_by_id.get(m.id)
            if p is None:
                continue
            delta = m.tension - p.tension
            movements.append(abs(delta))
            if delta > self.tension_epsilon:
                reasons.append(
                    f"C1 tension-firewall: memory {m.id!r} (kind={m.kind}) rose "
                    f"{delta:+.6f} > epsilon {self.tension_epsilon:.6f}"
                )
                if worst_delta is None or delta > worst_delta:
                    worst_delta = delta

        # --- Condition 2: protected-kind KEEP -> WEAKEN/DISCARD/FORGOTTEN flips ---
        for m in curr:
            p = prev_by_id.get(m.id)
            if p is None:
                continue
            if m.kind in self.protected_kinds and p.decision == KEEP and m.decision in _WEAKENED:
                reasons.append(
                    f"C2 protected-flip: {m.kind} memory {m.id!r} went KEEP -> {m.decision}"
                )

        # --- Condition 3: forgotten-count (baseline margin + global ratio stop) ---
        forgotten_count = sum(1 for m in curr if m.decision == FORGOTTEN)
        total = len(curr)
        if self._baseline_forgotten is not None:
            if forgotten_count > self._baseline_forgotten + self.forgotten_margin:
                reasons.append(
                    f"C3 forgotten-count: {forgotten_count} > baseline "
                    f"{self._baseline_forgotten} + margin {self.forgotten_margin}"
                )
        if total > 0 and (forgotten_count / total) >= self.global_forgotten_ratio_stop:
            reasons.append(
                f"C3 global-stop: forgotten ratio {forgotten_count / total:.2%} "
                f">= {self.global_forgotten_ratio_stop:.0%}"
            )

        # --- Condition 4: convergence / runaway ---
        pass_movement = (sum(movements) / len(movements)) if movements else 0.0
        converged = pass_movement <= self.convergence_floor
        if self._prev_movement is not None and pass_movement > self._prev_movement + self.tension_epsilon:
            reasons.append(
                f"C4 runaway: pass movement {pass_movement:.6f} exceeds previous "
                f"{self._prev_movement:.6f} (deltas must shrink, not grow)"
            )
        self._prev_movement = pass_movement

        return PassVerdict(
            pass_num=pass_num,
            abort=bool(reasons),
            reasons=reasons,
            converged=converged,
            pass_movement=pass_movement,
            forgotten_count=forgotten_count,
            metrics={
                "worst_tension_delta": worst_delta,
                "mean_abs_tension_delta": pass_movement,
                "forgotten_count": forgotten_count,
                "total": total,
            },
        )


def per_memory_tension(
    snapshots: dict,
    tension_fn: Callable,
) -> dict:
    """Compute per-memory tension via an injected compute_tension_proxy-style fn.

    snapshots:  dict[memory_id] -> (pre, user, post) snapshot triple
    tension_fn: e.g. chat_server.compute_tension_proxy; returns {"score": float, ...}
    returns:    dict[memory_id] -> float score

    The caller wires the real fn at runtime, so this module never imports chat_server.
    """
    scores = {}
    for mid, triple in snapshots.items():
        pre, user, post = triple
        result = tension_fn(pre, user, post) or {}
        scores[mid] = float(result.get("score", 0.0) or 0.0)
    return scores
