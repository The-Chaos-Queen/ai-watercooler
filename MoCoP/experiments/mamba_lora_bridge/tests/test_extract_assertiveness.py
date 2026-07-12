"""Model-free tests for the negative-valence (assertiveness) extraction plumbing.

No torch, no model: exercises the generalized ``training_pairs`` split logic and the
torch-free hormone-axis registry (the custody wall config). The actual Gemma capture
+ Method-A extraction is the GPU path (ML-WS) and is not covered here.
"""
import types

import pytest

from sev_primary_holdout import (
    HORMONE_AXIS_SPECS,
    hormone_axis_spec,
    training_pairs,
    training_warm_neutral_pairs,
)

CLASSES = ("warm", "cold", "adversarial", "neutral")


def _corpus(skeletons):
    corpus = {}
    for sk in skeletons:
        for cls in CLASSES:
            rid = f"{sk}_{cls}"
            corpus[rid] = {
                "id": rid, "skeleton_id": sk, "class": cls,
                "topic": "topic", "text": f"{sk} {cls} text", "notes": "",
            }
    return corpus


def _holdout(held_out, warm_pairs=None):
    return types.SimpleNamespace(
        held_out_skeletons=tuple(held_out),
        corpus_id="corpus-x",
        manifest_id="manifest-x",
        frozen_split=types.SimpleNamespace(pairs=dict(warm_pairs or {}), split_id="split-x"),
    )


# --------------------------------------------------------------------------- #
# training_pairs generalization.                                               #
# --------------------------------------------------------------------------- #
def test_adversarial_pairs_exclude_holdout_skeletons():
    corpus = _corpus(["a1", "a2", "a3"])
    holdout = _holdout(held_out=["a3"])
    pairs = training_pairs(corpus, holdout, positive_class="adversarial")
    assert [p[0] for p in pairs] == ["a1", "a2"]           # a3 excluded
    assert all("a3" not in p[0] for p in pairs)


def test_adversarial_pairs_are_adversarial_minus_neutral_texts():
    corpus = _corpus(["a1"])
    holdout = _holdout(held_out=[])
    (skeleton, positive_text, neutral_text), = training_pairs(
        corpus, holdout, positive_class="adversarial"
    )
    assert skeleton == "a1"
    assert positive_text == "a1 adversarial text"
    assert neutral_text == "a1 neutral text"


def test_adversarial_does_not_require_frozen_split_pairs():
    # The frozen split is warm-keyed; adversarial must not need it (empty pairs ok).
    corpus = _corpus(["a1", "a2"])
    holdout = _holdout(held_out=[], warm_pairs={})   # no warm pairs at all
    pairs = training_pairs(corpus, holdout, positive_class="adversarial")
    assert len(pairs) == 2


def test_warm_still_enforces_frozen_split_integrity():
    corpus = _corpus(["a1", "a2"])
    good = _holdout(held_out=[], warm_pairs={"a1_warm": "a1_neutral", "a2_warm": "a2_neutral"})
    assert len(training_pairs(corpus, good, positive_class="warm")) == 2

    # A wrong warm->neutral mapping must be caught (integrity guard preserved).
    bad = _holdout(held_out=[], warm_pairs={"a1_warm": "a2_neutral", "a2_warm": "a2_neutral"})
    with pytest.raises(ValueError):
        training_pairs(corpus, bad, positive_class="warm")


def test_warm_neutral_backward_compat_delegates():
    corpus = _corpus(["a1"])
    holdout = _holdout(held_out=[], warm_pairs={"a1_warm": "a1_neutral"})
    assert training_warm_neutral_pairs(corpus, holdout) == training_pairs(
        corpus, holdout, positive_class="warm"
    )


def test_neutral_as_positive_class_is_rejected():
    corpus = _corpus(["a1"])
    with pytest.raises(ValueError):
        training_pairs(corpus, _holdout([]), positive_class="neutral")


def test_unknown_positive_class_is_rejected():
    corpus = _corpus(["a1"])
    with pytest.raises(ValueError):
        training_pairs(corpus, _holdout([]), positive_class="banana")


# --------------------------------------------------------------------------- #
# Hormone-axis registry: the custody wall.                                     #
# --------------------------------------------------------------------------- #
def test_warm_axis_is_c1_admissible():
    spec = hormone_axis_spec("warm")
    assert spec["c1_admissible"] is True
    assert spec["injection_admissible"] is True
    assert spec["metaphor"] == "oxytocin"
    assert spec["artifact_schema_version"] == "gemma-g0b-value-norm-pre-v3"


def test_adversarial_axis_is_walled_from_c1():
    spec = hormone_axis_spec("adversarial")
    assert spec["c1_admissible"] is False
    assert spec["injection_admissible"] is False
    assert spec["axis"] == "assertiveness_agency"
    assert spec["metaphor"] == "testosterone"          # metaphor only
    assert spec["family"] == "negative_valence_atlas"


def test_every_negative_valence_axis_is_walled():
    for name, spec in HORMONE_AXIS_SPECS.items():
        if name == "warm":
            continue
        assert spec["c1_admissible"] is False, name
        assert spec["injection_admissible"] is False, name
        assert spec["family"] == "negative_valence_atlas", name


def test_hormone_axis_spec_is_a_copy_not_the_registry():
    spec = hormone_axis_spec("adversarial")
    spec["c1_admissible"] = True                        # mutate the copy
    assert HORMONE_AXIS_SPECS["adversarial"]["c1_admissible"] is False


def test_unknown_axis_raises():
    with pytest.raises(ValueError):
        hormone_axis_spec("banana")
