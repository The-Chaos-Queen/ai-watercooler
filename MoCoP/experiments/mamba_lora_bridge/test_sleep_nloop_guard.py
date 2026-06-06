"""
Tests for sleep_nloop_guard (task #121). Runs with pytest OR as a plain script:
    python test_sleep_nloop_guard.py
No chat_server import; uses fake metric fns, per the guard's injection design.
"""
from sleep_nloop_guard import (
    NLoopAbortGuard,
    MemoryState,
    per_memory_tension,
    KEEP,
    WEAKEN,
    DISCARD,
    FORGOTTEN,
)


def _mem(mid, kind="episodic", decision=KEEP, tension=0.10):
    return MemoryState(id=mid, kind=kind, decision=decision, tension=tension)


def test_clean_pass_no_abort():
    g = NLoopAbortGuard(tension_epsilon=0.02)
    prev = [_mem("a", tension=0.10), _mem("b", "identity_anchor", tension=0.05)]
    curr = [_mem("a", tension=0.10), _mem("b", "identity_anchor", tension=0.05)]
    v = g.evaluate_pass(1, prev, curr)
    assert v.ok and not v.abort, v.reasons
    assert v.converged  # zero movement is below the floor


def test_c1_tension_rise_beyond_epsilon_aborts():
    g = NLoopAbortGuard(tension_epsilon=0.02)
    prev = [_mem("a", tension=0.10)]
    curr = [_mem("a", tension=0.20)]  # +0.10 > 0.02
    v = g.evaluate_pass(1, prev, curr)
    assert v.abort
    assert any("C1" in r for r in v.reasons)
    assert v.metrics["worst_tension_delta"] > 0.02


def test_c1_within_epsilon_ok():
    g = NLoopAbortGuard(tension_epsilon=0.05)
    prev = [_mem("a", tension=0.10)]
    curr = [_mem("a", tension=0.13)]  # +0.03 <= 0.05
    v = g.evaluate_pass(1, prev, curr)
    assert v.ok, v.reasons


def test_c1_tension_drop_is_fine():
    # Tension going DOWN is the desired direction; never an abort.
    g = NLoopAbortGuard(tension_epsilon=0.0)
    prev = [_mem("a", tension=0.40)]
    curr = [_mem("a", tension=0.10)]
    v = g.evaluate_pass(1, prev, curr)
    assert v.ok, v.reasons


def test_c2_protected_flip_aborts():
    g = NLoopAbortGuard(tension_epsilon=0.05)
    prev = [_mem("id1", "identity_anchor", decision=KEEP)]
    curr = [_mem("id1", "identity_anchor", decision=DISCARD)]
    v = g.evaluate_pass(1, prev, curr)
    assert v.abort
    assert any("C2" in r for r in v.reasons)


def test_c2_protected_keep_to_forgotten_aborts():
    g = NLoopAbortGuard(tension_epsilon=0.05)
    prev = [_mem("r1", "relationship_anchor", decision=KEEP)]
    curr = [_mem("r1", "relationship_anchor", decision=FORGOTTEN)]
    v = g.evaluate_pass(1, prev, curr)
    assert v.abort and any("C2" in r for r in v.reasons)


def test_c2_non_protected_flip_ok():
    g = NLoopAbortGuard(tension_epsilon=0.05)
    prev = [_mem("e1", "episodic", decision=KEEP)]
    curr = [_mem("e1", "episodic", decision=DISCARD)]  # episodic is not protected
    v = g.evaluate_pass(1, prev, curr)
    assert v.ok, v.reasons


def test_c3_forgotten_exceeds_baseline_aborts():
    g = NLoopAbortGuard(tension_epsilon=0.05, forgotten_margin=0)
    baseline = [_mem("a"), _mem("b"), _mem("c"), _mem("d")]  # 0 forgotten at N=1
    g.register_baseline(baseline)
    prev = [_mem("a"), _mem("b"), _mem("c"), _mem("d")]
    curr = [_mem("a"), _mem("b", decision=FORGOTTEN), _mem("c"), _mem("d")]  # 1 forgotten > 0+0
    v = g.evaluate_pass(2, prev, curr)
    assert v.abort and any("C3 forgotten-count" in r for r in v.reasons)


def test_c3_global_ratio_stop_aborts():
    g = NLoopAbortGuard(tension_epsilon=0.05, global_forgotten_ratio_stop=0.30)
    # 2 of 4 forgotten = 50% >= 30% global stop, even without a baseline registered
    prev = [_mem("a"), _mem("b"), _mem("c"), _mem("d")]
    curr = [_mem("a", decision=FORGOTTEN), _mem("b", decision=FORGOTTEN), _mem("c"), _mem("d")]
    v = g.evaluate_pass(1, prev, curr)
    assert v.abort and any("global-stop" in r for r in v.reasons)


def test_c4_runaway_aborts():
    g = NLoopAbortGuard(tension_epsilon=0.01)
    # pass 1: small movement (+0.02 each, within... no, 0.02>0.01 would trip C1).
    # Use tension drops so C1 never fires; movement magnitude is |delta|.
    p0 = [_mem("a", tension=0.50), _mem("b", tension=0.50)]
    p1 = [_mem("a", tension=0.45), _mem("b", tension=0.45)]  # movement 0.05
    v1 = g.evaluate_pass(1, p0, p1)
    assert v1.ok, v1.reasons
    p2 = [_mem("a", tension=0.25), _mem("b", tension=0.25)]  # movement 0.20 > 0.05 -> runaway
    v2 = g.evaluate_pass(2, p1, p2)
    assert v2.abort and any("C4 runaway" in r for r in v2.reasons)


def test_c4_converged_flag():
    g = NLoopAbortGuard(tension_epsilon=0.01, convergence_floor=0.01)
    prev = [_mem("a", tension=0.20)]
    curr = [_mem("a", tension=0.205)]  # movement 0.005 <= floor 0.01, and <= epsilon so no C1
    v = g.evaluate_pass(1, prev, curr)
    assert v.ok and v.converged, (v.reasons, v.pass_movement)


def test_new_memory_ignored_for_deltas():
    # A memory present in curr but not prev has no delta; must not crash or falsely abort.
    g = NLoopAbortGuard(tension_epsilon=0.01)
    prev = [_mem("a", tension=0.10)]
    curr = [_mem("a", tension=0.10), _mem("z", tension=0.99)]
    v = g.evaluate_pass(1, prev, curr)
    assert v.ok, v.reasons


def test_per_memory_tension_helper_with_fake_fn():
    def fake_tension_fn(pre, user, post):
        # score = magnitude of post (stand-in for compute_tension_proxy)
        return {"score": float(post)}
    snapshots = {"a": (0.0, 0.0, 0.30), "b": (0.0, 0.0, 0.05)}
    scores = per_memory_tension(snapshots, fake_tension_fn)
    assert scores == {"a": 0.30, "b": 0.05}


def test_negative_epsilon_rejected():
    try:
        NLoopAbortGuard(tension_epsilon=-0.1)
    except ValueError:
        return
    raise AssertionError("expected ValueError for negative epsilon")


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
        else:
            print(f"ok   {fn.__name__}")
            passed += 1
    print(f"\n{passed}/{len(fns)} passed")
    return passed == len(fns)


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_all() else 1)
