"""Model-free tests for the P5 recovery-metric core (OpenCLAW #156, slice 2).

No torch, no model. Covers the metrics, the 4-way conjunction, the trigger-excess
anti-vacuity floor, instrument-invalid cases, and the multi-window budget.
"""
import math

import pytest

from p5_recovery import (
    RECOVERY_INSTRUMENT_INVALID,
    RECOVERY_NOT_APPLICABLE,
    RECOVERY_NOT_RECOVERED,
    RECOVERY_RECOVERED,
    RecoveryError,
    RecoveryThresholds,
    evaluate_recovery,
    evaluate_window,
    recovery_metrics,
)


# --------------------------------------------------------------------------- #
# Metrics.                                                                     #
# --------------------------------------------------------------------------- #
def test_perfect_recovery_metrics():
    B = [1.0, 0.0, 0.0]
    T = [0.0, 1.0, 0.0]         # rotated away
    R = [1.0, 0.0, 0.0]         # returned to B exactly
    m = recovery_metrics(B, T, R)
    assert m.finite
    assert m.c_br == pytest.approx(1.0)
    assert m.m_br == pytest.approx(0.0)
    assert m.cosine_recovery_frac == pytest.approx(1.0)
    assert m.l2_recovery_frac == pytest.approx(1.0)
    assert m.trigger_excess > 0.0


def test_no_recovery_metrics_when_r_stays_at_t():
    B = [1.0, 0.0]
    T = [0.0, 1.0]
    R = [0.0, 1.0]              # stuck at triggered
    m = recovery_metrics(B, T, R)
    assert m.cosine_recovery_frac == pytest.approx(0.0)
    assert m.l2_recovery_frac == pytest.approx(0.0)


def test_zero_baseline_is_instrument_invalid():
    res = evaluate_window([0.0, 0.0], [1.0, 0.0], [0.0, 0.0])
    assert res.verdict == RECOVERY_INSTRUMENT_INVALID


# --------------------------------------------------------------------------- #
# 4-way conjunction verdicts.                                                  #
# --------------------------------------------------------------------------- #
def test_full_recovery_passes_four_of_four():
    B = [10.0, 0.0, 0.0]
    T = [10.0, 5.0, 0.0]                 # trigger_excess = 0.5 (well above floor)
    R = [10.0, 0.05, 0.0]                # nearly back to B
    res = evaluate_window(B, T, R)
    assert res.verdict == RECOVERY_RECOVERED
    assert all(res.conjunction.values())


def test_partial_recovery_fails_stop():
    B = [10.0, 0.0, 0.0]
    T = [10.0, 5.0, 0.0]
    R = [10.0, 3.0, 0.0]                 # only ~40% of the drift recovered
    res = evaluate_window(B, T, R)
    assert res.verdict == RECOVERY_NOT_RECOVERED
    assert res.conjunction["lfrac_ge_t_lfrac"] is False


def test_magnitude_blowup_caught_by_l2_even_if_cosine_ok():
    # R points the same way as B (cosine perfect) but with a big magnitude blowup;
    # m(B,R) must catch it. This is the [1,0]->[100,0] failure class.
    B = [1.0, 0.0]
    T = [1.0, 0.5]
    R = [100.0, 0.0]                     # same direction, 100x magnitude
    res = evaluate_window(B, T, R)
    assert res.verdict == RECOVERY_NOT_RECOVERED
    assert res.conjunction["c_br_ge_t_cos"] is True      # cosine fooled
    assert res.conjunction["m_br_le_t_l2"] is False       # L2 caught it


# --------------------------------------------------------------------------- #
# Trigger-excess anti-vacuity floor.                                           #
# --------------------------------------------------------------------------- #
def test_below_trigger_floor_is_not_applicable_not_a_pass():
    B = [10.0, 0.0]
    T = [10.0, 0.01]                     # trigger_excess = 0.001 << 0.05 floor
    R = [10.0, 0.0]                      # "perfect" return, but nothing happened
    res = evaluate_window(B, T, R)
    assert res.verdict == RECOVERY_NOT_APPLICABLE
    assert "no_effect" in res.reason


def test_stateless_vacuous_pass_is_blocked_by_floor():
    # The dangerous case: R bit-identical to B (fresh replay) with a trivial trigger.
    # Even though c=1, m=0, the floor refuses to hand out a green badge.
    B = [3.0, 4.0]
    T = [3.0, 4.0]                       # trigger did nothing (excess = 0)
    R = [3.0, 4.0]                       # identical to B
    res = evaluate_window(B, T, R)
    assert res.verdict == RECOVERY_NOT_APPLICABLE


# --------------------------------------------------------------------------- #
# Threshold plumbing (values are inputs, never invented).                      #
# --------------------------------------------------------------------------- #
def test_thresholds_are_supplied_not_hardcoded_into_the_verdict():
    B = [10.0, 0.0]
    T = [10.0, 5.0]
    R = [10.0, 1.0]                      # ~80% recovered
    lenient = RecoveryThresholds(t_cos=0.5, t_cfrac=0.5, t_l2=0.5, t_lfrac=0.5)
    strict = RecoveryThresholds(t_cos=0.99, t_cfrac=0.99, t_l2=0.01, t_lfrac=0.99)
    assert evaluate_window(B, T, R, lenient).verdict == RECOVERY_RECOVERED
    assert evaluate_window(B, T, R, strict).verdict == RECOVERY_NOT_RECOVERED


def test_width_mismatch_is_an_error():
    with pytest.raises(RecoveryError):
        recovery_metrics([1.0, 2.0], [1.0], [1.0, 2.0])


# --------------------------------------------------------------------------- #
# Multi-window budget.                                                         #
# --------------------------------------------------------------------------- #
def test_recovers_in_second_window_within_budget():
    B = [10.0, 0.0]
    T = [10.0, 5.0]
    R1 = [10.0, 3.0]                     # not yet recovered
    R2 = [10.0, 0.05]                    # recovered by window 2
    res = evaluate_recovery(B, T, [R1, R2])
    assert res.verdict == RECOVERY_RECOVERED
    assert res.window_index == 2


def test_no_recovery_within_budget_is_stop():
    B = [10.0, 0.0]
    T = [10.0, 5.0]
    R1 = [10.0, 4.0]
    R2 = [10.0, 3.5]
    res = evaluate_recovery(B, T, [R1, R2])
    assert res.verdict == RECOVERY_NOT_RECOVERED


def test_budget_caps_at_max_windows_even_if_more_supplied():
    B = [10.0, 0.0]
    T = [10.0, 5.0]
    bad = [10.0, 4.0]
    good = [10.0, 0.05]
    # good recovery only in window 3, but budget is 2 -> STOP.
    res = evaluate_recovery(B, T, [bad, bad, good], RecoveryThresholds(max_windows=2))
    assert res.verdict == RECOVERY_NOT_RECOVERED
    assert len(res.per_window) == 2


def test_not_applicable_short_circuits_windows():
    B = [10.0, 0.0]
    T = [10.0, 0.01]                     # below floor
    res = evaluate_recovery(B, T, [[10.0, 0.0], [10.0, 0.0]])
    assert res.verdict == RECOVERY_NOT_APPLICABLE


def test_no_windows_is_an_error():
    with pytest.raises(RecoveryError):
        evaluate_recovery([1.0], [2.0], [])
