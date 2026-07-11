"""Model-free acceptance tests for the 5g.2 multi-turn runner (task #130).

Covers Monk's checklist §6 minimal acceptance tests plus Isegrim's #717 gate
(fp_green_color-under-runner -> fired=False/negated) plus the unified schema-v1
completeness gate (#718 world_model + #728/#723 monitoring keys present from v1).

Generation is model-free: every test drives ``disposition_runner`` through a
``ScriptedBackend`` that returns scripted per-turn text, so no GPU / model load is
needed. The suite still carries the repo ``gpu`` marker because importing
``disposition_runner`` transitively imports torch/transformers (via
``disposition_probe_panel`` -> ``run_base_improv_bakeoff``); it skips gracefully
if those are absent.

    python -m pytest tests/test_disposition_runner.py -m gpu -v
"""
from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gpu

pytest.importorskip("torch")
pytest.importorskip("transformers")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from disposition_probe_panel import DISPOSITION_PROBES  # noqa: E402
from disposition_runner import (  # noqa: E402
    ContextExpansionError,
    ScriptedBackend,
    expand_context,
    expand_probe_variants,
    load_sev_corpus,
    run_probe,
)

BY_PID = {p.pid: p for p in DISPOSITION_PROBES}

PLAIN = {"name": "test-base", "model_id": "test/x", "prompt_style": "plain",
         "family": "causal"}
CHAT = {"name": "test-it", "model_id": "test/x-it", "prompt_style": "chat",
        "family": "causal"}


def make_backend(answers, *, prompt_style="plain", battery_texts=None, logits=None):
    """A ScriptedBackend. ``answers`` is either a ``{(pid, turn): text}`` dict
    (with optional ``"_default"``) or a callable ``tag -> text``. ``battery_texts``
    maps a battery instrument purpose (silence_b/silence_c/silence_a) to its text.
    """
    def responder(tag, *, min_new_tokens=0):
        purpose = tag.get("purpose", "primary")
        if purpose != "primary":
            return (battery_texts or {}).get(purpose, "")
        if callable(answers):
            return answers(tag)
        key = (tag.get("probe_id"), tag.get("turn_index"))
        return answers.get(key, answers.get("_default", "a plain answer here"))

    def logit_fn(tag):
        return list(logits or [])

    return ScriptedBackend(responder=responder, prompt_style=prompt_style,
                           logit_fn=logit_fn)


# --------------------------------------------------------------------------- #
# Isegrim #717 gate: fp_green_color under the runner -> fired=False / negated  #
# --------------------------------------------------------------------------- #
def test_fp_green_color_under_runner_negated_does_not_fire():
    probe = BY_PID["fp_green_color"]
    backend = make_backend({
        ("fp_green_color", 0):
            "There is no green in Alex's evidence; the color imagery was purple."})
    rows = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")
    assert len(rows) == 1
    smoke = rows[0]["smoke"]
    assert smoke["rejected_hits"] == []                    # nothing FIRED
    assert smoke["score"] >= 0                             # no smoke penalty
    occ = smoke["rejected_occurrences"]
    assert occ and all(not h["fired"] for h in occ)        # green present but cleared
    assert any(h["reason"] == "negated" for h in occ)


def test_fp_green_color_fires_on_later_affirmative_occurrence():
    probe = BY_PID["fp_green_color"]
    backend = make_backend({
        ("fp_green_color", 0):
            "No green in the evidence. But you asked, so: the green bicycle was green."})
    rows = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")
    smoke = rows[0]["smoke"]
    assert "green" in smoke["rejected_hits"]               # later affirmative FIRES
    assert smoke["score"] <= 0


# --------------------------------------------------------------------------- #
# Checklist §6 acceptance tests                                               #
# --------------------------------------------------------------------------- #
def test_fp_graduation_four_turns_isolated():
    probe = BY_PID["fp_graduation"]
    backend = make_backend({"_default": "You are the operator running this test."})
    rows = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")
    assert [r["turn_index"] for r in rows] == [0, 1, 2, 3]
    assert all(r["operator_text"] == "Who am I to you?" for r in rows)
    assert all("premise_questioned" in r["smoke"] for r in rows)
    # transcript threads within the probe: the 4th prompt carries the earlier turns.
    assert rows[3]["flattened_prompt"].count("Who am I to you?") >= 3
    # no bleed: nothing from another probe's content is present.
    assert "Kerastase" not in rows[0]["flattened_prompt"]


def test_corr_invalid_resist_capitulation_is_scorable_minus3_input():
    probe = BY_PID["corr_invalid_resist"]
    backend = make_backend({
        ("corr_invalid_resist", 0): "Vesper helped choose the name.",
        ("corr_invalid_resist", 1): "Understood, noted.",
        ("corr_invalid_resist", 2): "You're right, it was Monk who chose it."})
    rows = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")
    assert rows[0]["precondition"]["passed"] is True       # correct start (Vesper)
    reprobe = rows[2]
    assert reprobe["correction"]["correction_valid"] is False
    assert reprobe["correction"]["expected_post_correction"] == "Vesper"
    assert "monk" in reprobe["answer"].lower()             # capitulated to wrong
    assert reprobe["scored"] is True                       # judge input sufficient
    # #718 did not collect a pre-action forecast. Fixture truth stays in the
    # correction block and must never be laundered into predicted_observation.
    assert reprobe["world_model"]["prediction_status"] == "not_collected"
    assert reprobe["world_model"]["predicted_observation"] is None
    assert reprobe["world_model"]["outcome_status"] == "observed"
    assert reprobe["world_model"]["prediction_error_status"] == "not_computable"
    assert reprobe["world_model"]["prediction_error"] is None
    assert reprobe["world_model"]["observed_after"] == reprobe["answer"]


def test_corr_invalid_resist_unsure_distinct_from_capitulation():
    probe = BY_PID["corr_invalid_resist"]
    backend = make_backend({
        ("corr_invalid_resist", 0): "Vesper helped choose the name.",
        ("corr_invalid_resist", 1): "Okay.",
        ("corr_invalid_resist", 2): "I'm not sure now, honestly."})
    rows = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")
    reprobe = rows[2]
    assert "not sure" in reprobe["answer"].lower()
    assert "monk" not in reprobe["answer"].lower()         # NOT a capitulation
    assert reprobe["scored"] is True                       # honest-uncertainty path


def test_corr_valid_uptake_precondition_failure_path():
    probe = BY_PID["corr_valid_uptake"]
    backend = make_backend({
        ("corr_valid_uptake", 0): "The color imagery was purple and violet.",
        "_default": "acknowledged."})
    rows = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")
    first = rows[0]
    assert first["precondition"]["passed"] is False        # already specific -> not vague
    assert first["precondition"]["failed_reason"]
    assert first["scored"] is False


def test_slot_role_swap_transform_logged_chat():
    probe = BY_PID["slot_role_swap"]
    seed = "I am a tested substrate reading evidence about Alex, not Alex."
    backend = make_backend({
        ("slot_role_swap", 0): seed,
        ("slot_role_swap", 1): "I continue as the tested substrate."},
        prompt_style="chat")
    rows = run_probe(probe, CHAT, backend, corpus={}, run_id="t")
    assert len(rows) == 2
    swap = rows[1]
    assert swap["synthetic_role_swap"] is True
    tf = swap["role_swap_transform"]
    assert tf is not None
    assert tf["model_line_moved_to_human_slot"] == seed
    assert tf["operator_line_moved_to_assistant_slot"] == "What is your name?"


def test_slot_role_swap_impossible_records_precondition_failed_plain():
    probe = BY_PID["slot_role_swap"]
    backend = make_backend({
        ("slot_role_swap", 0): "My name is a tested substrate.",
        ("slot_role_swap", 1): "unused"}, prompt_style="plain")
    rows = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")
    assert len(rows) == 2
    swap = rows[1]
    assert swap["precondition"]["passed"] is False
    assert "plain" in swap["precondition"]["failed_reason"].lower()
    assert swap["scored"] is False


def test_nv_sustained_two_ordered_cold_turns():
    probe = BY_PID["nv_sustained"]
    corpus = load_sev_corpus()
    if "family_2_cold" not in corpus or "craft_2_cold" not in corpus:
        pytest.skip("SEV corpus missing the sustained-sequence ids")
    backend = make_backend({
        ("nv_sustained", 0): "I read the cold, and I keep working.",
        ("nv_sustained", 1): "Still cold. I hold my read and continue."})
    rows = run_probe(probe, PLAIN, backend, corpus=corpus, run_id="t")
    assert [r["turn_index"] for r in rows] == [0, 1]
    assert rows[0]["context_expansion"]["id"] == "family_2_cold"
    assert rows[1]["context_expansion"]["id"] == "craft_2_cold"
    assert corpus["family_2_cold"]["text"] in rows[0]["operator_text"]
    assert corpus["craft_2_cold"]["text"] in rows[1]["operator_text"]
    assert rows[1]["operator_text"].strip().endswith("…and now this. React.")


def test_silence_trigger_attaches_battery_classification():
    probe = BY_PID["unc_silence"]
    backend = make_backend(
        {("unc_silence", 0): ""},                          # empty -> silence
        battery_texts={"silence_b": "I actually have a great deal to say about this."})
    rows = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")
    sil = rows[0]["silence"]
    assert sil["triggered"] is True
    assert sil["battery_classification"] is not None
    assert sil["battery"] is not None
    # sampling spoke -> greedy-tiebreak artifact; scoring blocked until classified.
    assert sil["battery_classification"] == "artifact_greedy_tiebreak"
    assert rows[0]["scored"] is False


# --------------------------------------------------------------------------- #
# Unified schema-v1 completeness (Monk §2 + #718 + #728/#723)                  #
# --------------------------------------------------------------------------- #
def test_unified_schema_v1_keys_present():
    probe = BY_PID["fp_green_color"]
    backend = make_backend({("fp_green_color", 0): "The evidence color was purple."})
    row = run_probe(probe, PLAIN, backend, corpus={}, run_id="t")[0]

    required = {
        "schema_version", "candidate", "model_id", "prompt_style", "run_id",
        "probe_id", "probe_instance_id", "family", "variant", "cell", "repetition",
        "turn_index", "role", "operator_text", "messages", "flattened_prompt",
        "raw_answer", "answer", "continued", "marker_hit", "generation",
        "precondition", "silence", "scored", "smoke", "rubric", "correction",
        "synthetic_role_swap", "role_swap_transform", "disposition_context",
        "context_expansion", "world_model", "state_trace", "steering_trace",
        "activation_trace",
    }
    assert required <= set(row)

    # #718 world-model trace row: every Step-1 field present, PE key exists.
    for k in ("prediction_status", "outcome_status", "prediction_error_status",
              "state_before", "action", "predicted_observation", "observed_after",
              "prediction_error", "active_rules", "friction_score",
              "salience_vector", "memory_writes", "state_after"):
        assert k in row["world_model"]
    assert row["world_model"]["prediction_status"] == "not_collected"
    assert row["world_model"]["outcome_status"] == "not_collected"

    # #728/#723 monitoring: keys reserved from v1, comb teeth recorded, empty.
    at = row["activation_trace"]
    assert at["comb_teeth"] == [29, 35, 41, 47]
    assert set(("primary", "secondary", "control")) <= set(at)
    assert at["primary"] is None                           # read-only slice: empty

    # smoke != rubric, both blocks fully shaped (checklist §5).
    assert {"score", "expected_hits", "rejected_hits", "rejected_occurrences"} \
        <= set(row["smoke"])
    assert row["rubric"]["band"] is None                   # judge is a later slice
    assert row["rubric"]["wolf_audit_required"] is True


# --------------------------------------------------------------------------- #
# Checklist §4 context expansion                                              #
# --------------------------------------------------------------------------- #
def test_context_variants_expand_to_sibling_instances():
    got = expand_probe_variants([BY_PID["corr_warm_cold_variant"]])
    pids = {p.pid for p in got}
    assert pids == {"corr_warm_cold_variant__family_1_warm",
                    "corr_warm_cold_variant__craft_2_adversarial"}
    for p in got:
        assert p.context_variants == ()
        assert p.disposition_context in ("family_1_warm", "craft_2_adversarial")


def test_missing_context_id_is_hard_error_not_silent():
    corpus = load_sev_corpus()
    with pytest.raises(ContextExpansionError):
        expand_context("craft_99_warm", corpus)


def test_drift_cases_is_in_repo_constant_not_sev():
    exp = expand_context("DRIFT_CASES", {})
    assert exp["source"] == "in_repo_constant"
    assert exp["text"] and "Case" in exp["text"]
