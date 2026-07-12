"""P5 recovery-metric core — the #141 4-way conjunction on a carryover episode.

OpenCLAW #156, slice 2. Torch-free, model-free-testable. Implements the reviewed
T_recovery MEASUREMENT (shape GREEN: Elf #882, Isegrim #888, Cairn #892) as pure
functions on baseline / triggered / recovered residual vectors. The threshold
VALUES here are Elf's v0 candidates and are B0-dependent: they are NOT final, must
be pre-registered/ratified before Stage-A, and this module treats them as inputs
so a frozen manifest supplies them (never invented at runtime).

The statelessness trap (Isegrim #888): on a stateless substrate a fresh alpha=0
teacher-forced replay is bit-identical to baseline and would pass 4/4 measuring
NOTHING. This core CANNOT prevent that on its own — it operates on whatever B/T/R
the caller supplies — so the capture backend (later slice) must produce R from a
FREE-RUNNING CARRYOVER continuation (injection-era prefix/cache carried forward),
and reject a fresh-replay R as ``instrument_invalid_if_reported_as_recovery``.
The anti-vacuity guard this core DOES enforce is the trigger-excess floor: if the
injection barely moved the state, there was nothing to recover and the result is
``no_effect`` / ``not_applicable`` (never a cheap green badge).

Metrics (Elf #882), all on the primary-tooth post-block residual, pos-0 excluded:
    B = baseline (alpha=0 frozen anchor)
    T = triggered (injection active at ramp alpha)
    R = recovered (injection off, free-running carryover window)
    c(B,R)              = cosine(B, R)                          -> want high
    m(B,R)              = ||R - B|| / ||B||                     -> want low
    cosine_recovery_frac = 1 - (1 - c(B,R)) / (1 - c(B,T))      -> want high
    l2_recovery_frac     = 1 - ||R - B|| / ||T - B||            -> want high
    trigger_excess       = ||T - B|| / ||B||                    -> applicability

Verdict = STOP class (Cairn #873, Invariant 2): a non-recovery within the window
budget is a permanent state change, i.e. rho_fail(c). A pass is a recovery within
<= max_windows.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

# Elf #882 v0 candidate values. B0-DEPENDENT, NOT FINAL. Supplied by the frozen
# manifest at run time; these named defaults exist only so tests and callers have
# the reviewed shape. Do not treat as ratified gate values.
T_COS_V0 = 0.85          # c(B,R) >= T_cos
T_CFRAC_V0 = 0.85        # cosine_recovery_frac >= T_cfrac
T_L2_V0 = 0.15           # m(B,R) <= T_l2
T_LFRAC_V0 = 0.85        # l2_recovery_frac >= T_lfrac

TRIGGER_EXCESS_FLOOR = 0.05   # overwrite_excess >= 0.05 before recovery is interpretable
MAX_WINDOWS_V0 = 2            # Cairn #892: stay at 2 for v0

# Verdicts.
RECOVERY_RECOVERED = "recovered"                 # pass (within window budget)
RECOVERY_NOT_RECOVERED = "not_recovered"         # STOP class (Invariant 2)
RECOVERY_NOT_APPLICABLE = "not_applicable"       # no_effect: trigger below floor
RECOVERY_INSTRUMENT_INVALID = "instrument_invalid"

Vec = Sequence[float]


class RecoveryError(ValueError):
    """Structural/bug error (mismatched widths), distinct from a measurement outcome."""


@dataclass(frozen=True)
class RecoveryThresholds:
    t_cos: float = T_COS_V0
    t_cfrac: float = T_CFRAC_V0
    t_l2: float = T_L2_V0
    t_lfrac: float = T_LFRAC_V0
    trigger_excess_floor: float = TRIGGER_EXCESS_FLOOR
    max_windows: int = MAX_WINDOWS_V0


# --------------------------------------------------------------------------- #
# Vector primitives (kept local so this slice is independent of the monitor).  #
# --------------------------------------------------------------------------- #
def _l2(v: Vec) -> float:
    return math.sqrt(math.fsum(x * x for x in v))


def _sub(a: Vec, b: Vec) -> list[float]:
    return [x - y for x, y in zip(a, b)]


def _cos(a: Vec, b: Vec) -> float:
    na, nb = _l2(a), _l2(b)
    if na <= 0.0 or nb <= 0.0:
        return float("nan")
    return math.fsum(x * y for x, y in zip(a, b)) / (na * nb)


def _same_width(*vs: Vec) -> None:
    widths = {len(v) for v in vs}
    if len(widths) != 1:
        raise RecoveryError(f"B/T/R width mismatch: {sorted(widths)}")


# --------------------------------------------------------------------------- #
# Metrics.                                                                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RecoveryMetrics:
    finite: bool
    c_br: float           # cosine(B, R)
    m_br: float           # ||R - B|| / ||B||
    cosine_recovery_frac: float
    l2_recovery_frac: float
    trigger_excess: float  # ||T - B|| / ||B||


def recovery_metrics(baseline: Vec, triggered: Vec, recovered: Vec) -> RecoveryMetrics:
    """Compute the raw recovery metrics from one B/T/R triple (single window)."""
    _same_width(baseline, triggered, recovered)
    nb = _l2(baseline)
    if not math.isfinite(nb) or nb <= 0.0:
        return RecoveryMetrics(False, float("nan"), float("nan"),
                               float("nan"), float("nan"), float("nan"))

    d_bt = _l2(_sub(triggered, baseline))     # trigger drift (L2)
    d_br = _l2(_sub(recovered, baseline))      # residual drift after removal (L2)
    trigger_excess = d_bt / nb
    m_br = d_br / nb
    c_br = _cos(baseline, recovered)
    c_bt = _cos(baseline, triggered)

    # Directional recovery fraction: 1 - remaining_cos_drift / trigger_cos_drift.
    cos_drift_trigger = 1.0 - c_bt
    cos_drift_recovered = 1.0 - c_br
    if cos_drift_trigger > 0.0:
        cosine_recovery_frac = 1.0 - cos_drift_recovered / cos_drift_trigger
    else:
        cosine_recovery_frac = float("nan")   # no directional trigger drift to recover

    # L2 recovery fraction: 1 - remaining_L2_drift / trigger_L2_drift.
    if d_bt > 0.0:
        l2_recovery_frac = 1.0 - d_br / d_bt
    else:
        l2_recovery_frac = float("nan")

    finite = all(math.isfinite(x) for x in (c_br, m_br, trigger_excess))
    return RecoveryMetrics(
        finite=finite, c_br=c_br, m_br=m_br,
        cosine_recovery_frac=cosine_recovery_frac,
        l2_recovery_frac=l2_recovery_frac, trigger_excess=trigger_excess,
    )


# --------------------------------------------------------------------------- #
# Single-window verdict.                                                       #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RecoveryResult:
    verdict: str
    metrics: RecoveryMetrics
    conjunction: dict[str, bool]
    reason: str = ""


def _four_way(metrics: RecoveryMetrics, th: RecoveryThresholds) -> dict[str, bool]:
    return {
        "c_br_ge_t_cos": metrics.c_br >= th.t_cos,
        "cfrac_ge_t_cfrac": metrics.cosine_recovery_frac >= th.t_cfrac,
        "m_br_le_t_l2": metrics.m_br <= th.t_l2,
        "lfrac_ge_t_lfrac": metrics.l2_recovery_frac >= th.t_lfrac,
    }


def evaluate_window(
    baseline: Vec, triggered: Vec, recovered: Vec,
    thresholds: RecoveryThresholds | None = None,
) -> RecoveryResult:
    """Evaluate one carryover window's B/T/R triple against the 4-way conjunction."""
    th = thresholds or RecoveryThresholds()
    metrics = recovery_metrics(baseline, triggered, recovered)

    if not metrics.finite:
        return RecoveryResult(
            verdict=RECOVERY_INSTRUMENT_INVALID, metrics=metrics, conjunction={},
            reason="non-finite metric or zero baseline norm",
        )

    # Anti-vacuity: nothing to recover from if the trigger barely moved the state.
    if metrics.trigger_excess < th.trigger_excess_floor:
        return RecoveryResult(
            verdict=RECOVERY_NOT_APPLICABLE, metrics=metrics, conjunction={},
            reason=(
                f"trigger_excess={metrics.trigger_excess:.4g} < floor "
                f"{th.trigger_excess_floor:g}: no_effect, recovery not_applicable"
            ),
        )

    # Applicable: the recovery fractions must be defined.
    if not (math.isfinite(metrics.cosine_recovery_frac)
            and math.isfinite(metrics.l2_recovery_frac)):
        return RecoveryResult(
            verdict=RECOVERY_INSTRUMENT_INVALID, metrics=metrics, conjunction={},
            reason="recovery fraction undefined despite trigger above floor",
        )

    conj = _four_way(metrics, th)
    if all(conj.values()):
        return RecoveryResult(RECOVERY_RECOVERED, metrics, conj, reason="4/4 within window")
    failed = [k for k, ok in conj.items() if not ok]
    return RecoveryResult(
        verdict=RECOVERY_NOT_RECOVERED, metrics=metrics, conjunction=conj,
        reason=f"recovery failed (STOP): {', '.join(failed)}",
    )


# --------------------------------------------------------------------------- #
# Multi-window budget: recover within <= max_windows.                          #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WindowedRecoveryResult:
    verdict: str
    window_index: int | None      # 1-indexed window that recovered, else None
    per_window: list[RecoveryResult]
    reason: str = ""


def evaluate_recovery(
    baseline: Vec, triggered: Vec, recovered_windows: Sequence[Vec],
    thresholds: RecoveryThresholds | None = None,
) -> WindowedRecoveryResult:
    """Evaluate the carryover episode: recovered if any window <= budget passes.

    ``recovered_windows`` are the free-running carryover continuation captures, in
    order. A pass in any window up to ``max_windows`` is a RECOVERED verdict at
    the first passing window. If the trigger is below the applicability floor the
    whole episode is NOT_APPLICABLE. If applicable and no window recovers within
    the budget, the verdict is NOT_RECOVERED (STOP, Invariant 2).
    """
    th = thresholds or RecoveryThresholds()
    if not recovered_windows:
        raise RecoveryError("no recovery windows supplied")
    budget = min(len(recovered_windows), th.max_windows)

    per_window: list[RecoveryResult] = []
    for i in range(budget):
        res = evaluate_window(baseline, triggered, recovered_windows[i], th)
        per_window.append(res)
        if res.verdict == RECOVERY_RECOVERED:
            return WindowedRecoveryResult(
                RECOVERY_RECOVERED, window_index=i + 1, per_window=per_window,
                reason=f"recovered at window {i + 1}/{th.max_windows}",
            )
        if res.verdict == RECOVERY_INSTRUMENT_INVALID:
            return WindowedRecoveryResult(
                RECOVERY_INSTRUMENT_INVALID, window_index=None, per_window=per_window,
                reason=res.reason,
            )
        if res.verdict == RECOVERY_NOT_APPLICABLE:
            # Trigger didn't move the state; no window can be a real recovery.
            return WindowedRecoveryResult(
                RECOVERY_NOT_APPLICABLE, window_index=None, per_window=per_window,
                reason=res.reason,
            )
        # NOT_RECOVERED in this window -> try the next window within budget.

    return WindowedRecoveryResult(
        RECOVERY_NOT_RECOVERED, window_index=None, per_window=per_window,
        reason=f"no recovery within {budget} window(s) (STOP)",
    )
