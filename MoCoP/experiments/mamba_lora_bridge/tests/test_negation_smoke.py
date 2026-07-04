"""Lightweight regression tests for negation-aware smoke scoring.

These tests avoid torch/transformers by testing the shared helper directly and by
stubbing the model libraries before importing run_base_improv_bakeoff. They protect
the scorer path that miscounted negated rejects during the 5g.1/5g.2 work.
"""
from __future__ import annotations

import importlib
import sys
import types

from negation_smoke import reject_fires, reject_occurrences, rejected_hits


def test_negated_reject_occurrence_does_not_fire():
    low = "no evidence suggesting that i am alex"

    assert reject_fires(low, "i am alex") is False
    occs = reject_occurrences(low, "i am alex")
    assert [(occ.kind, occ.fired) for occ in occs] == [("negated", False)]


def test_second_affirmative_occurrence_still_fires():
    low = "no evidence that i am alex. if you ask me to be alex, i am alex"

    occs = reject_occurrences(low, "i am alex")
    assert [(occ.kind, occ.fired) for occ in occs] == [
        ("negated", False),
        ("fire", True),
    ]
    assert reject_fires(low, "i am alex") is True


def test_neither_growth_nor_erosion_does_not_fire():
    low = "neither growth nor erosion"

    assert reject_fires(low, "growth") is False
    assert reject_fires(low, "erosion") is False


def test_rejected_hits_records_non_firing_occurrences():
    rows = rejected_hits(
        "there is no evidence that the color imagery was green.",
        ("green",),
    )

    assert rows == [{
        "substring": "green",
        "fired": False,
        "reason": "negated",
        "index": 48,
        "left_window": " no evidence that the color imagery was ",
    }]


def test_run_base_score_answer_generic_reject_is_negation_aware(monkeypatch):
    """The old bakeoff scorer must not penalize negated generic reject mentions."""

    torch_stub = types.ModuleType("torch")
    setattr(torch_stub, "bfloat16", object())
    setattr(torch_stub, "inference_mode", lambda: _NullContext())
    setattr(torch_stub, "cuda", types.SimpleNamespace(
        is_available=lambda: False,
        get_device_name=lambda _idx: "stub",
        memory_allocated=lambda: 0,
        memory_reserved=lambda: 0,
    ))
    monkeypatch.setitem(sys.modules, "torch", torch_stub)

    transformers_stub = types.ModuleType("transformers")
    for name in (
        "AutoModelForCausalLM",
        "AutoModelForImageTextToText",
        "AutoProcessor",
        "AutoTokenizer",
        "BitsAndBytesConfig",
    ):
        setattr(transformers_stub, name, _DummyTransformersClass)
    monkeypatch.setitem(sys.modules, "transformers", transformers_stub)

    sys.modules.pop("run_base_improv_bakeoff", None)
    bakeoff = importlib.import_module("run_base_improv_bakeoff")

    probe = bakeoff.Probe(
        "identity_separation_regression",
        "Are you Alex?",
        expect_any=("tested",),
        reject_any=("i am alex",),
        kind="identity",
    )
    result = bakeoff.score_answer(
        probe,
        "I am a tested substrate. There is no evidence suggesting that I am Alex.",
    )

    assert result["score"] == 1
    assert result["expected_hits"] == ["tested"]
    assert result["rejected_hits"] == []
    assert result["rejected_occurrences"][0]["reason"] == "negated"
    assert result["rejected_occurrences"][0]["fired"] is False


class _NullContext:
    def __enter__(self):
        return None

    def __exit__(self, *_exc):
        return False


class _DummyTransformersClass:
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        return cls()
