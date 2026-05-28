"""Tests for offline_tension_metric. Runs with or without pytest:

    python test_offline_tension_metric.py
    pytest -q test_offline_tension_metric.py
"""
from __future__ import annotations

import numpy as np

from offline_tension_metric import (
    cosine,
    memory_tension,
    per_memory_tension_offline,
    tension_deltas,
    calibrate_epsilon_from_a1,
)


def test_cosine_aligned_orthogonal_opposed():
    assert abs(cosine([1, 0, 0], [2, 0, 0]) - 1.0) < 1e-9
    assert abs(cosine([1, 0, 0], [0, 1, 0]) - 0.0) < 1e-9
    assert abs(cosine([1, 0, 0], [-1, 0, 0]) + 1.0) < 1e-9


def test_cosine_zero_vector_is_zero():
    assert cosine([0, 0, 0], [1, 1, 1]) == 0.0


def test_memory_tension_scale():
    # aligned -> 0, orthogonal -> 1, opposed -> 2  (1 - cosine)
    assert abs(memory_tension([1, 0], [3, 0]) - 0.0) < 1e-6
    assert abs(memory_tension([1, 0], [0, 1]) - 1.0) < 1e-6
    assert abs(memory_tension([1, 0], [-1, 0]) - 2.0) < 1e-6


def test_per_memory_tension_offline_uses_injected_encoder_and_skips_empty():
    # fake encoder: maps text -> a fixed vector
    table = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])}
    encode = lambda t: table[t]
    state = np.array([1.0, 0.0])
    scores = per_memory_tension_offline(
        memory_ids=["m1", "m2", "m3"],
        memory_texts={"m1": "a", "m2": "b", "m3": "   "},  # m3 empty -> skipped
        state_vec=state,
        encode_fn=encode,
    )
    assert set(scores) == {"m1", "m2"}        # empty memory skipped
    assert abs(scores["m1"] - 0.0) < 1e-6     # aligned with state
    assert abs(scores["m2"] - 1.0) < 1e-6     # orthogonal to state


def test_tension_deltas_only_shared_ids():
    before = {"m1": 0.10, "m2": 0.50, "gone": 0.9}
    after = {"m1": 0.18, "m2": 0.40, "new": 0.1}
    deltas = tension_deltas(before, after)
    assert set(deltas) == {"m1", "m2"}
    assert abs(deltas["m1"] - 0.08) < 1e-6    # rose (would breach a small epsilon)
    assert abs(deltas["m2"] + 0.10) < 1e-6    # fell (safe)


def test_calibrate_epsilon_frozen_state_is_floor():
    # frozen state -> identical tension every pass -> zero jitter -> epsilon == floor
    frozen = [{"m1": 0.3, "m2": 0.7}, {"m1": 0.3, "m2": 0.7}, {"m1": 0.3, "m2": 0.7}]
    eps = calibrate_epsilon_from_a1(frozen, safety_factor=3.0, floor=1e-6)
    assert eps == 1e-6


def test_calibrate_epsilon_scales_with_jitter():
    # max pass-to-pass |delta| is 0.02 (m2: 0.70 -> 0.72) -> eps = 3 * 0.02 = 0.06
    passes = [{"m1": 0.30, "m2": 0.70}, {"m1": 0.31, "m2": 0.72}, {"m1": 0.31, "m2": 0.71}]
    eps = calibrate_epsilon_from_a1(passes, safety_factor=3.0, floor=1e-6)
    assert abs(eps - 0.06) < 1e-9


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  ok  {t.__name__}")
    print(f"\n{passed}/{len(tests)} passed")
    return passed == len(tests)


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_all() else 1)
