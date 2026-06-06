"""
Regression tests for the two A3 shadow-loop firewall holes found in review.

Runs WITHOUT torch (uses the real, torch-free offline_tension_metric + sleep_nloop_guard
with a deterministic fake encoder), so it executes in CI as well as on ML-WS:

    python test_a3_firewall_regression.py
    pytest -q test_a3_firewall_regression.py

BUG 1 (C1 firewall dead): run_shadow_sleep_nloop_a3 captured `before_vec` AFTER the
recurrent advance had already reassigned current_vector, so before==after, every
per-memory tension delta was 0, and the guard's C1 could never fire. Fix: before = the
pre-advance snapshot (prev_vector), after = post-advance current_vector.

BUG 2 (C2 dead on real data): reconcile emits lowercase decisions ("keep","weakened")
while the guard's constants are uppercase ("KEEP","WEAKEN"), so the protected-flip check
never matched. Fix: normalize_decision() at the MemoryState seam.
"""
from __future__ import annotations

import numpy as np

from offline_tension_metric import per_memory_tension_offline
from sleep_nloop_guard import NLoopAbortGuard, MemoryState, KEEP, WEAKEN, DISCARD, FORGOTTEN

# Use the shipped normalizer if the (torch-importing) a3 module loads; otherwise mirror
# it locally so this test still runs in a torch-free environment. Either way we assert
# the mapping behaviour the fix depends on.
try:
    from run_shadow_sleep_nloop_a3 import normalize_decision
    _SOURCE = "run_shadow_sleep_nloop_a3.normalize_decision"
except Exception:  # torch / model stack absent
    _MAP = {
        "keep": KEEP, "KEEP": KEEP,
        "weaken": WEAKEN, "weakened": WEAKEN, "WEAKEN": WEAKEN,
        "discard": DISCARD, "DISCARD": DISCARD,
        "forgotten": FORGOTTEN, "FORGOTTEN": FORGOTTEN,
        "uncertain": "UNCERTAIN", "UNCERTAIN": "UNCERTAIN",
    }
    def normalize_decision(raw):  # type: ignore
        if raw is None:
            return KEEP
        s = str(raw).strip()
        return _MAP.get(s) or _MAP.get(s.lower()) or s.upper()
    _SOURCE = "local mirror (torch absent)"


# A deterministic, torch-free stand-in for encode_text_to_mamba_hidden_last_token.
_ENC = {"m1": np.array([1.0, 0.0]), "m2": np.array([0.0, 1.0])}
def _encode(text):
    return _ENC[text]

_IDS = ["m1"]
_TEXTS = {"m1": "m1"}

# A memory aligned with S_before but orthogonal to S_after => it gets MORE misaligned
# as the state moves: tension(m1, S_before)=0, tension(m1, S_after)=1. A real re-tensioning.
_S_BEFORE = np.array([1.0, 0.0])
_S_AFTER = np.array([0.0, 1.0])


def _run_pass(before_vec, after_vec, *, epsilon=0.02, kind="episodic",
              prev_decision="KEEP", curr_decision="KEEP"):
    before = per_memory_tension_offline(_IDS, _TEXTS, before_vec, _encode)
    after = per_memory_tension_offline(_IDS, _TEXTS, after_vec, _encode)
    prev_states = [MemoryState(id=m, kind=kind, decision=prev_decision, tension=before[m]) for m in before]
    curr_states = [MemoryState(id=m, kind=kind, decision=curr_decision, tension=after[m]) for m in after]
    g = NLoopAbortGuard(tension_epsilon=epsilon)
    return g.evaluate_pass(1, prev_states, curr_states)


# ---------------------------------------------------------------------------
# BUG 1
# ---------------------------------------------------------------------------

def test_bug1_repro_before_equals_after_masks_retensioning():
    """The OLD behaviour: before_vec read post-advance == after_vec.
    A genuine re-tensioning (S_before->S_after) is invisible; C1 stays silent."""
    v = _run_pass(_S_AFTER, _S_AFTER)            # both post-advance, as the bug did
    assert not v.abort, "expected the buggy path to (wrongly) report a clean pass"
    assert v.metrics["worst_tension_delta"] is None
    assert v.pass_movement == 0.0


def test_bug1_fixed_before_is_pre_advance_fires_c1():
    """The FIXED behaviour: before=pre-advance, after=post-advance.
    The same re-tensioning now produces delta=+1.0 and C1 aborts."""
    v = _run_pass(_S_BEFORE, _S_AFTER)
    assert v.abort, "C1 must fire when a memory becomes more misaligned after the advance"
    assert any("C1" in r for r in v.reasons)
    assert v.metrics["worst_tension_delta"] > 0.9   # ~ +1.0


def test_bug1_fixed_still_allows_clean_consolidation():
    """A pass that REDUCES misalignment (the desired direction) must not abort."""
    v = _run_pass(_S_AFTER, _S_BEFORE)   # tension 1.0 -> 0.0, a drop
    assert not v.abort, v.reasons


# ---------------------------------------------------------------------------
# BUG 2
# ---------------------------------------------------------------------------

def test_bug2_repro_lowercase_decisions_dodge_c2():
    """Raw reconcile-style decisions ('keep'->'weakened') do NOT trip C2,
    because they never equal the guard's uppercase constants."""
    v = _run_pass(_S_BEFORE, _S_BEFORE, kind="identity_anchor",
                  prev_decision="keep", curr_decision="weakened")
    assert not any("C2" in r for r in v.reasons), "raw lowercase should slip past C2 (the bug)"


def test_bug2_fixed_normalized_decisions_fire_c2():
    """Normalized decisions make the protected KEEP->WEAKEN flip visible to C2."""
    v = _run_pass(_S_BEFORE, _S_BEFORE, kind="identity_anchor",
                  prev_decision=normalize_decision("keep"),
                  curr_decision=normalize_decision("weakened"))
    assert v.abort and any("C2" in r for r in v.reasons), v.reasons


def test_bug2_normalize_mapping():
    assert normalize_decision("keep") == KEEP
    assert normalize_decision("weakened") == WEAKEN
    assert normalize_decision("weaken") == WEAKEN
    assert normalize_decision("discard") == DISCARD
    assert normalize_decision("FORGOTTEN") == FORGOTTEN
    assert normalize_decision("KEEP") == KEEP          # canonical passes through
    assert normalize_decision(None) == KEEP


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:  # noqa
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
        else:
            print(f"ok   {t.__name__}")
            passed += 1
    print(f"\nnormalize_decision source: {_SOURCE}")
    print(f"{passed}/{len(tests)} passed")
    return passed == len(tests)


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_all() else 1)
