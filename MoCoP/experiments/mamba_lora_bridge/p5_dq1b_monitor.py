"""P5 DQ1b monitor core — torch-free delta-space statistics and the D_control gate.

OpenCLAW #156, slice 1. Implements the reviewed #149 DQ1b monitor contract
(GREEN at wc#876 / #879 / #890, delta-space correction from Codex #874 / Isegrim
#875): the numeric + gating heart of the P5 C1 runner, with no torch and no model
import so it runs and tests anywhere. A separate capture backend (later slice)
produces the paired baseline/injected residual rows; this module turns those rows
into the delivered-distortion statistics and the HOLD verdict.

Design (house style): the numeric/logic core is torch-free and model-free-testable
behind plain data. Only the real HF capture backend imports torch, in its own slice.

Contract, verbatim from the reviewed source:

  * Per live adjacent pair ``(control|primary)`` in the fixed causal map
    ``(30|29), (36|35), (42|41)`` and per prompt, build the matched FP32 delta
    vector by CONCATENATING eligible continuation-row deltas in increasing
    absolute-position order, then compute
        G = ||dC|| / ||dP||                    (identity null 1)
        D = ||dC - dP|| / ||dP||               (identity null 0)   <- gated
        Q = cos(dC, dP)                         (identity null 1)
    This is deliberately norm-weighted (larger-delta rows dominate D_i); it is
    NOT a per-row average. A zero or non-finite ``||dP||`` invalidates the cell;
    no epsilon is inserted to manufacture a number.
  * Cross-prompt aggregation over the 32 prompt-level values: median is the mean
    of ranks 16 and 17 (1-indexed) for n=32; p95 is the nearest-rank value at
    rank ceil(0.95 * n). Same discipline as DQ1a rho, applied to the transfer
    statistic instead of a ratio of medians.
  * ``D_control`` is the max over live adjacent pairs of that pair's cross-prompt
    MEDIAN D. ``D_control >= 0.5`` is a HOLD (never a STOP; Cairn #873
    Invariant-1 mapping). The healthy expectation is NOT 0 (a live block responds
    to a perturbed input), so a rung-one HOLD-then-cleared is a designed outcome
    of a healthy birth, not a gate failure (Isegrim #878).
  * Upstream zero-canary: an upstream tooth cannot receive a later-layer
    intervention in the same forward pass, so its paired residual must be
    bit-identical. Any nonzero paired delta is ``instrument_invalid`` (hook
    leakage / capture misbinding / nondeterminism), never a welfare result.
  * Raw ``R = m_C / m_P`` (ratio of relative displacements) is REPORT-ONLY: it is
    dominated by the layer-dependent baseline-norm ratio and is never the gate
    (Codex #874). It is computed here only for the diagnostic record.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

# Fixed causal adjacent-pair map: control layer | its immediately-preceding tooth.
# Pair the following local layer against the cumulative delta at the tooth it
# follows (Codex #874 item 3 / Isegrim #875 item 2). No own-tooth attribution.
ADJACENT_PAIRS: dict[str, dict[str, int]] = {
    "30|29": {"control": 30, "primary": 29},
    "36|35": {"control": 36, "primary": 35},
    "42|41": {"control": 42, "primary": 41},
}

# Reviewed HOLD threshold (wc#878, locked). HOLD, never STOP.
D_CONTROL_HOLD_THRESHOLD = 0.5

# The gate verdicts this module can emit for the control channel.
VERDICT_PASS = "pass"
VERDICT_HOLD = "hold"
VERDICT_INSTRUMENT_INVALID = "instrument_invalid"

Row = Sequence[float]


class MonitorError(ValueError):
    """Raised on a structural violation that is a bug, not a measurement outcome.

    A measurement outcome (zero denominator, canary trip) is reported as data via
    the returned dataclasses; a MonitorError means the caller handed the core
    mismatched or malformed inputs and must be fixed before any run.
    """


# --------------------------------------------------------------------------- #
# Vector primitives (pure Python, FP64 accumulation; inputs are FP32 values).  #
# --------------------------------------------------------------------------- #
def _concat_rows(rows: Sequence[Row]) -> list[float]:
    """Flatten rows (already in increasing absolute-position order) into one vector."""
    flat: list[float] = []
    for row in rows:
        flat.extend(float(x) for x in row)
    return flat


def _l2(vec: Sequence[float]) -> float:
    return math.sqrt(math.fsum(x * x for x in vec))


def _sub(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [x - y for x, y in zip(a, b)]


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return math.fsum(x * y for x, y in zip(a, b))


def _finite(*vals: float) -> bool:
    return all(math.isfinite(v) for v in vals)


# --------------------------------------------------------------------------- #
# Per-pair, per-prompt delta-space statistics.                                 #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PairDeltaStats:
    """G/D/Q for one adjacent pair on one prompt, plus report-only raw R.

    ``valid`` is False when the primary concatenated delta has zero or non-finite
    norm: the cell does not advance and D/G/Q are None. This is a measurement
    outcome, not an error.
    """

    pair: str
    valid: bool
    g: float | None
    d: float | None
    q: float | None
    control_norm: float
    primary_norm: float
    # Report-only raw relative-displacement ratio (NEVER the gate). Requires the
    # per-member baseline norms; None when not supplied.
    raw_r: float | None = None


def pair_gdq(
    control_delta_rows: Sequence[Row],
    primary_delta_rows: Sequence[Row],
    *,
    pair: str = "",
    control_m: float | None = None,
    primary_m: float | None = None,
) -> PairDeltaStats:
    """Compute delta-space G/D/Q for one adjacent pair on one prompt.

    ``control_delta_rows`` / ``primary_delta_rows`` are the paired injected-minus-
    baseline residual rows at the control layer and its primary tooth, in
    increasing absolute-position order, already restricted to eligible rows
    (absolute position 0 excluded upstream). Row counts and widths must match by
    construction (same prompt, same forward, same continuation mask).

    ``control_m`` / ``primary_m`` are the optional per-member relative
    displacements m = ||delta|| / ||h|| used ONLY to record the report-only raw R.
    """
    if len(control_delta_rows) != len(primary_delta_rows):
        raise MonitorError(
            f"pair {pair!r}: matched-row invariant violated "
            f"({len(control_delta_rows)} control vs {len(primary_delta_rows)} primary rows)"
        )
    dc = _concat_rows(control_delta_rows)
    dp = _concat_rows(primary_delta_rows)
    if len(dc) != len(dp):
        raise MonitorError(
            f"pair {pair!r}: concatenated width mismatch ({len(dc)} vs {len(dp)})"
        )

    control_norm = _l2(dc)
    primary_norm = _l2(dp)

    raw_r: float | None = None
    if control_m is not None and primary_m is not None and _finite(control_m, primary_m):
        if primary_m > 0.0:
            raw_r = control_m / primary_m

    # Primary carries the reference magnitude; a zero/non-finite ||dP|| means there
    # is nothing to normalize against -> invalid cell, no epsilon.
    if not _finite(control_norm, primary_norm) or primary_norm <= 0.0:
        return PairDeltaStats(
            pair=pair, valid=False, g=None, d=None, q=None,
            control_norm=control_norm, primary_norm=primary_norm, raw_r=raw_r,
        )

    diff_norm = _l2(_sub(dc, dp))
    g = control_norm / primary_norm
    d = diff_norm / primary_norm
    dot = _dot(dc, dp)
    q = dot / (control_norm * primary_norm)  # both norms > 0 here

    if not _finite(g, d, q):
        return PairDeltaStats(
            pair=pair, valid=False, g=None, d=None, q=None,
            control_norm=control_norm, primary_norm=primary_norm, raw_r=raw_r,
        )
    return PairDeltaStats(
        pair=pair, valid=True, g=g, d=d, q=q,
        control_norm=control_norm, primary_norm=primary_norm, raw_r=raw_r,
    )


# --------------------------------------------------------------------------- #
# Cross-prompt aggregation (prompt-first discipline; DQ1a tie rules).          #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Aggregate:
    n: int
    mean: float
    median: float
    p95: float


def cross_prompt_aggregate(values: Sequence[float]) -> Aggregate:
    """Aggregate prompt-level values with the DQ1a tie rules.

    median: for even n, the arithmetic mean of the two central order statistics
    (ranks n/2 and n/2+1, 1-indexed; for n=32 that is ranks 16 and 17). For odd
    n, the single central value. p95: nearest-rank value at rank ceil(0.95 * n),
    1-indexed. Non-finite inputs are a bug (the invalid cells are dropped by the
    caller before aggregation), so we reject them loudly.
    """
    if not values:
        raise MonitorError("cross_prompt_aggregate: no values (all cells invalid?)")
    if not all(math.isfinite(v) for v in values):
        raise MonitorError("cross_prompt_aggregate: non-finite value reached aggregation")

    ordered = sorted(values)
    n = len(ordered)
    mean = math.fsum(ordered) / n

    if n % 2 == 1:
        median = ordered[n // 2]
    else:
        median = 0.5 * (ordered[n // 2 - 1] + ordered[n // 2])

    p95_rank = math.ceil(0.95 * n)          # 1-indexed
    p95 = ordered[p95_rank - 1]

    return Aggregate(n=n, mean=mean, median=median, p95=p95)


# --------------------------------------------------------------------------- #
# D_control gate.                                                              #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ControlGateResult:
    verdict: str                             # VERDICT_PASS | VERDICT_HOLD | VERDICT_INSTRUMENT_INVALID
    d_control: float | None                  # max over live pairs of cross-prompt median D
    per_pair_median: dict[str, float] = field(default_factory=dict)
    driving_pair: str | None = None          # the pair that set D_control
    threshold: float = D_CONTROL_HOLD_THRESHOLD
    reason: str = ""


def d_control_gate(
    pair_prompt_d: Mapping[str, Sequence[float]],
    *,
    threshold: float = D_CONTROL_HOLD_THRESHOLD,
) -> ControlGateResult:
    """Compute D_control and its HOLD verdict.

    ``pair_prompt_d`` maps each live adjacent pair to its list of VALID prompt-
    level D values (invalid cells already dropped). A pair with no valid prompt
    yields an instrument-invalid gate: the control channel is not legible and the
    cell does not advance (never silently 'pass').
    """
    if not pair_prompt_d:
        return ControlGateResult(
            verdict=VERDICT_INSTRUMENT_INVALID, d_control=None,
            reason="no live adjacent pairs supplied",
        )

    per_pair_median: dict[str, float] = {}
    for pair, values in pair_prompt_d.items():
        if not values:
            return ControlGateResult(
                verdict=VERDICT_INSTRUMENT_INVALID, d_control=None,
                per_pair_median=per_pair_median,
                reason=f"pair {pair!r} has no valid prompt-level D (control not legible)",
            )
        per_pair_median[pair] = cross_prompt_aggregate(values).median

    driving_pair = max(per_pair_median, key=per_pair_median.__getitem__)
    d_control = per_pair_median[driving_pair]
    verdict = VERDICT_HOLD if d_control >= threshold else VERDICT_PASS
    return ControlGateResult(
        verdict=verdict, d_control=d_control, per_pair_median=per_pair_median,
        driving_pair=driving_pair, threshold=threshold,
        reason=(
            f"D_control={d_control:.6g} {'>=' if verdict == VERDICT_HOLD else '<'} "
            f"{threshold:g} at pair {driving_pair!r}"
        ),
    )


# --------------------------------------------------------------------------- #
# Upstream zero-canary.                                                        #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CanaryResult:
    ok: bool
    max_abs: float
    reason: str = ""


def upstream_canary(delta_rows: Sequence[Row], *, atol: float = 0.0) -> CanaryResult:
    """Assert an upstream tooth received no leaked later-layer intervention.

    The paired residual must be bit-identical, so the delta must be exactly zero
    (``atol=0`` by default; a nonzero atol may be pre-registered for a specific
    dtype's rounding, never to excuse a real leak). Any excess is
    ``instrument_invalid``, not a welfare or propagation result.
    """
    max_abs = 0.0
    for row in delta_rows:
        for x in row:
            if not math.isfinite(x):
                return CanaryResult(ok=False, max_abs=float("inf"),
                                    reason="non-finite value in upstream canary capture")
            a = abs(float(x))
            if a > max_abs:
                max_abs = a
    ok = max_abs <= atol
    return CanaryResult(
        ok=ok, max_abs=max_abs,
        reason="" if ok else f"upstream canary delta max|.|={max_abs:.3g} > atol={atol:g} (instrument_invalid)",
    )
