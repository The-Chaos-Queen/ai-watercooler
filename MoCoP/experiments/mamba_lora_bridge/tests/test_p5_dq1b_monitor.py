"""Model-free tests for the P5 DQ1b monitor core (OpenCLAW #156, slice 1).

No torch, no model: every test runs on plain floats. Covers the delta-space
identity nulls, norm-weighted concatenation, invalid/undefined cells, the DQ1a
aggregation tie rules, the D_control HOLD gate, and the upstream zero-canary.
"""
import math

import pytest

from p5_dq1b_monitor import (
    ADJACENT_PAIRS,
    D_CONTROL_HOLD_THRESHOLD,
    VERDICT_HOLD,
    VERDICT_INSTRUMENT_INVALID,
    VERDICT_PASS,
    Aggregate,
    MonitorError,
    cross_prompt_aggregate,
    d_control_gate,
    pair_gdq,
    upstream_canary,
)


# --------------------------------------------------------------------------- #
# Fixed causal pair map.                                                       #
# --------------------------------------------------------------------------- #
def test_adjacent_pairs_are_the_reviewed_causal_map():
    assert set(ADJACENT_PAIRS) == {"30|29", "36|35", "42|41"}
    for key, members in ADJACENT_PAIRS.items():
        ctrl, prim = (int(x) for x in key.split("|"))
        assert members["control"] == ctrl
        assert members["primary"] == prim
        # control is the immediately-following local layer of its tooth
        assert members["control"] == members["primary"] + 1


# --------------------------------------------------------------------------- #
# Delta-space identity nulls: dC == dP -> G=1, D=0, Q=1.                        #
# --------------------------------------------------------------------------- #
def test_identity_nulls_when_control_equals_primary():
    rows = [[1.0, -2.0, 0.5], [0.0, 3.0, -1.0]]
    stats = pair_gdq(rows, [list(r) for r in rows], pair="30|29")
    assert stats.valid
    assert stats.g == pytest.approx(1.0)
    assert stats.d == pytest.approx(0.0)
    assert stats.q == pytest.approx(1.0)


def test_d_is_exactly_zero_only_for_identity():
    primary = [[1.0, 0.0], [0.0, 1.0]]
    control = [[1.0, 0.0], [0.0, 1.0001]]
    stats = pair_gdq(control, primary, pair="30|29")
    assert stats.d is not None and stats.d > 0.0


def test_orthogonal_control_gives_q_zero():
    primary = [[1.0, 0.0]]
    control = [[0.0, 1.0]]
    stats = pair_gdq(control, primary, pair="30|29")
    assert stats.q == pytest.approx(0.0, abs=1e-12)
    # G = ||dC|| / ||dP|| = 1; D = ||dC - dP|| / ||dP|| = sqrt(2)
    assert stats.g == pytest.approx(1.0)
    assert stats.d == pytest.approx(math.sqrt(2.0))


def test_anti_parallel_gives_q_minus_one():
    primary = [[2.0, 0.0]]
    control = [[-2.0, 0.0]]
    stats = pair_gdq(control, primary, pair="30|29")
    assert stats.q == pytest.approx(-1.0)


# --------------------------------------------------------------------------- #
# Norm-weighted concatenation (NOT per-row average).                          #
# --------------------------------------------------------------------------- #
def test_d_uses_concatenated_norm_weighting():
    # A large-delta row must dominate D_i over a tiny-delta row.
    primary = [[10.0, 0.0], [0.0, 0.01]]
    control = [[12.0, 0.0], [0.0, 0.02]]  # +2 on the big row, +0.01 on the tiny row
    stats = pair_gdq(control, primary, pair="30|29")
    dp_norm = math.sqrt(10.0**2 + 0.01**2)
    diff_norm = math.sqrt(2.0**2 + 0.01**2)
    assert stats.d == pytest.approx(diff_norm / dp_norm)
    # A per-row average would have given ~ (2/10 + 0.01/0.01)/2 = 0.6, very different.
    assert stats.d < 0.25  # dominated by the big row, not the tiny one


# --------------------------------------------------------------------------- #
# Invalid / undefined cells (no epsilon).                                     #
# --------------------------------------------------------------------------- #
def test_zero_primary_norm_invalidates_cell_without_epsilon():
    primary = [[0.0, 0.0]]
    control = [[1.0, 1.0]]
    stats = pair_gdq(control, primary, pair="30|29")
    assert stats.valid is False
    assert stats.d is None and stats.g is None and stats.q is None


def test_non_finite_delta_invalidates_cell():
    primary = [[float("inf"), 0.0]]
    control = [[1.0, 0.0]]
    stats = pair_gdq(control, primary, pair="30|29")
    assert stats.valid is False


def test_matched_row_count_mismatch_is_an_error_not_an_outcome():
    with pytest.raises(MonitorError):
        pair_gdq([[1.0, 2.0]], [[1.0, 2.0], [3.0, 4.0]], pair="30|29")


def test_width_mismatch_is_an_error():
    with pytest.raises(MonitorError):
        pair_gdq([[1.0, 2.0, 3.0]], [[1.0, 2.0]], pair="30|29")


# --------------------------------------------------------------------------- #
# Report-only raw R.                                                          #
# --------------------------------------------------------------------------- #
def test_raw_r_is_reported_when_member_m_supplied():
    stats = pair_gdq([[1.0]], [[1.0]], pair="30|29", control_m=0.2, primary_m=0.5)
    assert stats.raw_r == pytest.approx(0.4)


def test_raw_r_is_none_without_member_m():
    stats = pair_gdq([[1.0]], [[1.0]], pair="30|29")
    assert stats.raw_r is None


# --------------------------------------------------------------------------- #
# Cross-prompt aggregation with DQ1a tie rules.                               #
# --------------------------------------------------------------------------- #
def test_median_and_p95_for_n32_use_the_dq1a_tie_rules():
    values = [float(i) for i in range(1, 33)]  # 1..32
    agg = cross_prompt_aggregate(values)
    assert agg.n == 32
    assert agg.mean == pytest.approx(16.5)
    assert agg.median == pytest.approx(16.5)   # mean of ranks 16 and 17
    assert agg.p95 == pytest.approx(31.0)      # nearest-rank ceil(0.95*32)=31


def test_median_odd_n_is_the_central_value():
    agg = cross_prompt_aggregate([3.0, 1.0, 2.0])
    assert agg.median == pytest.approx(2.0)


def test_aggregate_is_order_independent():
    import random
    values = [float(i) for i in range(1, 33)]
    shuffled = values[:]
    random.Random(0).shuffle(shuffled)
    assert cross_prompt_aggregate(shuffled).median == pytest.approx(
        cross_prompt_aggregate(values).median
    )


def test_aggregate_rejects_empty_and_non_finite():
    with pytest.raises(MonitorError):
        cross_prompt_aggregate([])
    with pytest.raises(MonitorError):
        cross_prompt_aggregate([1.0, float("nan"), 2.0])


# --------------------------------------------------------------------------- #
# D_control gate: max over pairs of cross-prompt median; HOLD at >= 0.5.       #
# --------------------------------------------------------------------------- #
def test_d_control_is_max_over_pairs_of_median():
    gate = d_control_gate({
        "30|29": [0.1, 0.2, 0.3],   # median 0.2
        "36|35": [0.4, 0.6, 0.8],   # median 0.6  <- drives
        "42|41": [0.0, 0.1, 0.2],   # median 0.1
    })
    assert gate.driving_pair == "36|35"
    assert gate.d_control == pytest.approx(0.6)
    assert gate.verdict == VERDICT_HOLD


def test_d_control_pass_below_threshold():
    gate = d_control_gate({
        "30|29": [0.1, 0.2, 0.3],
        "36|35": [0.2, 0.3, 0.4],
    })
    assert gate.d_control == pytest.approx(0.3)
    assert gate.verdict == VERDICT_PASS


def test_d_control_hold_exactly_at_threshold_is_hold():
    gate = d_control_gate({"30|29": [D_CONTROL_HOLD_THRESHOLD]})
    assert gate.verdict == VERDICT_HOLD  # >= is HOLD


def test_d_control_hold_never_stop():
    # The gate emits only pass/hold/instrument_invalid for the control channel.
    gate = d_control_gate({"30|29": [10.0]})
    assert gate.verdict in {VERDICT_PASS, VERDICT_HOLD, VERDICT_INSTRUMENT_INVALID}
    assert gate.verdict == VERDICT_HOLD
    assert "stop" not in gate.verdict


def test_empty_pair_is_instrument_invalid_not_pass():
    gate = d_control_gate({"30|29": [0.1], "36|35": []})
    assert gate.verdict == VERDICT_INSTRUMENT_INVALID
    assert gate.d_control is None


def test_no_pairs_is_instrument_invalid():
    gate = d_control_gate({})
    assert gate.verdict == VERDICT_INSTRUMENT_INVALID


# --------------------------------------------------------------------------- #
# Upstream zero-canary.                                                        #
# --------------------------------------------------------------------------- #
def test_canary_passes_on_exact_zero():
    res = upstream_canary([[0.0, 0.0], [0.0, 0.0]])
    assert res.ok and res.max_abs == 0.0


def test_canary_trips_on_any_nonzero():
    res = upstream_canary([[0.0, 0.0], [0.0, 1e-6]])
    assert res.ok is False
    assert res.max_abs == pytest.approx(1e-6)
    assert "instrument_invalid" in res.reason


def test_canary_trips_on_non_finite():
    res = upstream_canary([[float("nan")]])
    assert res.ok is False


def test_canary_atol_may_be_preregistered_but_defaults_to_zero():
    rows = [[0.0, 5e-7]]
    assert upstream_canary(rows).ok is False               # default atol=0
    assert upstream_canary(rows, atol=1e-6).ok is True     # explicit pre-registered tol
