"""Model-free tests for the matched-delta activation-target recording (Codex #806).

The numeric/schema core of ``matched_delta_recording`` is torch-free, so this
suite drives the whole recording path through a ``ScriptedVProjCapture`` with
scripted activations — NO GPU, NO model load, NO torch import. It is collected by
bare ``pytest`` (no ``-m gpu`` needed).

    python -m pytest tests/test_matched_delta_recording.py -q

Coverage (Codex #806 requirement 3 + Fable review S1/S3/S5/S6/N4):
  * delta = scenario - neutral is exact for common-mode terms;
  * common mode cancels (scenario = neutral + delta + shared_DC -> recorded
    delta == delta, DC gone);
  * the frozen split pairs each scenario to exactly one neutral and split_id is
    stable / order-independent / tamper-evident, and the holdout is stamped (S6);
  * missing neutral is a HARD ERROR, never a silently-recorded absolute;
  * half-paired input (scenario has v_proj_in, neutral doesn't) is a hard error (S5);
  * delta-only mode still keeps the input DELTA fields (S5);
  * stale-corpus manifest is rejected when a corpus is supplied (S3);
  * empty split is refused (N4);
  * fp16 delta SNR metric + summary (S1);
  * schema completeness (labeled scenario absolute kept for audit + delta fields).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from matched_delta_recording import (  # noqa: E402
    DEFAULT_TARGET_LAYERS,
    EPS_BY_DTYPE,
    EPS_FP16,
    MissingNeutralError,
    ScriptedVProjCapture,
    build_frozen_split,
    build_matched_delta_record,
    compute_delta,
    corpus_fingerprint,
    delta_snr,
    eps_for_dtype,
    load_frozen_split,
    main,
    neutral_control_id,
    record_matched_delta,
    snr_gate_count,
    snr_summary,
)

# A tiny synthetic SEV-shaped corpus: two skeletons, each with warm/cold/neutral.
# (Real SEV also has adversarial; the delta logic is class-agnostic.)
TOY_CORPUS = {
    "craft_1_warm": {"id": "craft_1_warm", "skeleton_id": "craft_1", "class": "warm",
                     "topic": "craft/work", "text": "warm one"},
    "craft_1_cold": {"id": "craft_1_cold", "skeleton_id": "craft_1", "class": "cold",
                     "topic": "craft/work", "text": "cold one"},
    "craft_1_neutral": {"id": "craft_1_neutral", "skeleton_id": "craft_1",
                        "class": "neutral", "topic": "craft/work", "text": "neutral one"},
    "food_2_warm": {"id": "food_2_warm", "skeleton_id": "food_2", "class": "warm",
                    "topic": "food", "text": "warm two"},
    "food_2_neutral": {"id": "food_2_neutral", "skeleton_id": "food_2",
                       "class": "neutral", "topic": "food", "text": "neutral two"},
}


# --------------------------------------------------------------------------- #
# 1) Delta + DC / common-mode cancellation.                                   #
# --------------------------------------------------------------------------- #
def test_delta_is_exact_scenario_minus_neutral():
    scenario = [1.0, 2.0, 3.0, 4.0]
    neutral = [0.5, 0.5, 0.5, 0.5]
    assert compute_delta(scenario, neutral) == [0.5, 1.5, 2.5, 3.5]


def test_dc_and_bias_common_mode_cancels():
    """The whole point: plant scenario = neutral_signal + shared_DC + b_v + delta,
    and neutral = neutral_signal + shared_DC + b_v. The recorded delta must equal
    the planted delta with EVERY common-mode component gone."""
    d_v = 8
    neutral_signal = [0.11 * i for i in range(d_v)]
    shared_dc = [7.0] * d_v                 # dominant bridge-internal DC (#801/#803)
    b_v = [-0.3 * (i % 3) for i in range(d_v)]   # the model's own v_proj bias
    delta = [0.0, 0.5, -0.5, 1.0, -1.0, 0.2, -0.2, 0.05]

    neutral_vec = [neutral_signal[i] + shared_dc[i] + b_v[i] for i in range(d_v)]
    scenario_vec = [neutral_vec[i] + delta[i] for i in range(d_v)]

    got = compute_delta(scenario_vec, neutral_vec)
    for g, d in zip(got, delta):
        assert abs(g - d) < 1e-9
    # DC gone: the recorded delta's mean is the planted delta's mean, not ~7.
    assert abs(sum(got) / d_v - sum(delta) / d_v) < 1e-9


def test_delta_width_mismatch_is_error():
    with pytest.raises(ValueError):
        compute_delta([1.0, 2.0, 3.0], [1.0, 2.0])


def test_delta_rejects_nested_row():
    with pytest.raises(ValueError):
        compute_delta([[1.0, 2.0]], [[0.0, 0.0]])


# --------------------------------------------------------------------------- #
# 2) Frozen split: pairing, stability, tamper-evidence.                       #
# --------------------------------------------------------------------------- #
def test_neutral_control_id_matches_house_rule():
    assert neutral_control_id("craft_1_warm") == "craft_1_neutral"
    assert neutral_control_id("craft_1_adversarial") == "craft_1_neutral"
    assert neutral_control_id("craft_1_neutral") == "craft_1_neutral"
    assert neutral_control_id("DRIFT_CASES") is None
    assert neutral_control_id(None) is None


def test_frozen_split_pairs_each_scenario_to_one_neutral():
    split = build_frozen_split(TOY_CORPUS)
    # non-neutral scenarios only; each -> its skeleton's neutral.
    assert set(split.scenario_ids()) == {"craft_1_warm", "craft_1_cold", "food_2_warm"}
    assert split.neutral_for("craft_1_warm") == "craft_1_neutral"
    assert split.neutral_for("craft_1_cold") == "craft_1_neutral"
    assert split.neutral_for("food_2_warm") == "food_2_neutral"
    # exactly one neutral per scenario (values are single ids, not lists).
    assert all(isinstance(n, str) for n in split.pairs.values())


def test_split_id_is_stable_and_order_independent():
    a = build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_warm", "food_2_warm"])
    b = build_frozen_split(TOY_CORPUS, scenario_ids=["food_2_warm", "craft_1_warm"])
    assert a.split_id == b.split_id                    # selection order irrelevant
    assert a.split_id.startswith("split-")


def test_split_id_changes_when_pairing_changes():
    full = build_frozen_split(TOY_CORPUS)
    subset = build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_warm"])
    assert full.split_id != subset.split_id            # different pair set -> different id


def test_corpus_fingerprint_changes_on_edited_text():
    edited = dict(TOY_CORPUS)
    edited["craft_1_warm"] = {**TOY_CORPUS["craft_1_warm"], "text": "TAMPERED"}
    assert corpus_fingerprint(TOY_CORPUS) != corpus_fingerprint(edited)


def test_manifest_roundtrip_verifies_id():
    split = build_frozen_split(TOY_CORPUS)
    manifest = split.to_manifest()
    restored = load_frozen_split(manifest)
    assert restored.split_id == split.split_id
    assert restored.pairs == split.pairs


def test_manifest_tamper_is_rejected():
    split = build_frozen_split(TOY_CORPUS)
    manifest = split.to_manifest()
    # silently repoint a scenario to a different neutral without rehashing.
    manifest["pairs"][0]["neutral_id"] = "food_2_neutral"
    with pytest.raises(ValueError):
        load_frozen_split(manifest)


# --------------------------------------------------------------------------- #
# 3) Missing neutral is a HARD ERROR (never a silent absolute).               #
# --------------------------------------------------------------------------- #
def test_missing_neutral_refuses_split():
    corpus_no_neutral = {
        "craft_1_warm": {"id": "craft_1_warm", "skeleton_id": "craft_1",
                         "class": "warm", "text": "warm"},
        # craft_1_neutral deliberately absent
    }
    with pytest.raises(MissingNeutralError):
        build_frozen_split(corpus_no_neutral)


def test_neutral_cannot_be_a_scenario():
    with pytest.raises(ValueError):
        build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_neutral"])


def test_record_missing_neutral_layer_is_hard_error():
    split = build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_warm"])
    layers = (12, 13)
    scen = {L: {"v_proj_out": [1.0, 2.0]} for L in layers}
    neut = {12: {"v_proj_out": [0.0, 0.0]}}       # layer 13 missing on the neutral
    with pytest.raises(MissingNeutralError):
        build_matched_delta_record(
            scenario_id="craft_1_warm", split=split,
            scenario_capture=scen, neutral_capture=neut,
            target_layers=layers)


# --------------------------------------------------------------------------- #
# 4) Schema completeness + back-compat.                                       #
# --------------------------------------------------------------------------- #
def test_record_schema_keeps_absolute_and_adds_delta():
    split = build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_warm"])
    layers = (12, 13)
    scen = {L: {"v_proj_out": [3.0, 4.0], "v_proj_in": [9.0, 9.0]} for L in layers}
    neut = {L: {"v_proj_out": [1.0, 1.0], "v_proj_in": [8.0, 8.0]} for L in layers}

    rec = build_matched_delta_record(
        scenario_id="craft_1_warm", split=split,
        scenario_capture=scen, neutral_capture=neut, target_layers=layers)

    assert rec["recipe"] == "matched_delta_v1"
    assert rec["scenario_id"] == "craft_1_warm"
    assert rec["neutral_control_id"] == "craft_1_neutral"
    assert rec["split_id"] == split.split_id
    assert rec["corpus_id"] == split.corpus_id

    entry = rec["layers"]["12"]
    # matched-delta fields present + correct.
    assert entry["v_proj_out_scenario"] == [3.0, 4.0]
    assert entry["v_proj_out_neutral"] == [1.0, 1.0]
    assert entry["v_proj_out_delta"] == [2.0, 3.0]
    # back-compat: absolute v_proj_out kept (= scenario absolute) + v_proj_in kept.
    assert entry["v_proj_out"] == [3.0, 4.0]
    assert entry["v_proj_in"] == [9.0, 9.0]
    assert entry["v_proj_in_delta"] == [1.0, 1.0]


def test_record_keep_absolute_false_omits_bare_absolute_but_keeps_input_delta():
    """S5: delta-only mode drops the BARE absolutes (v_proj_out / v_proj_in) but
    MUST still record the input DELTA fields — they are part of the delta target."""
    split = build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_warm"])
    scen = {12: {"v_proj_out": [3.0, 4.0], "v_proj_in": [9.0, 9.0]}}
    neut = {12: {"v_proj_out": [1.0, 1.0], "v_proj_in": [8.0, 8.0]}}
    rec = build_matched_delta_record(
        scenario_id="craft_1_warm", split=split,
        scenario_capture=scen, neutral_capture=neut,
        target_layers=(12,), keep_absolute=False)
    entry = rec["layers"]["12"]
    assert "v_proj_out_delta" in entry
    assert "v_proj_out" not in entry            # bare absolute gated off
    assert "v_proj_in" not in entry             # bare input absolute gated off
    assert entry["v_proj_in_delta"] == [1.0, 1.0]   # input DELTA still recorded (S5)
    assert entry["v_proj_in_scenario"] == [9.0, 9.0]
    assert entry["v_proj_in_neutral"] == [8.0, 8.0]


def test_record_half_paired_input_is_hard_error():
    """S5: scenario has a v_proj_in but the matched neutral does not -> refuse,
    never silently keep a half-paired input."""
    split = build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_warm"])
    scen = {12: {"v_proj_out": [3.0, 4.0], "v_proj_in": [9.0, 9.0]}}
    neut = {12: {"v_proj_out": [1.0, 1.0]}}      # no v_proj_in on the neutral
    with pytest.raises(MissingNeutralError):
        build_matched_delta_record(
            scenario_id="craft_1_warm", split=split,
            scenario_capture=scen, neutral_capture=neut, target_layers=(12,))


# --------------------------------------------------------------------------- #
# 5) End-to-end driver on a scripted capture (DC planted per skeleton).       #
# --------------------------------------------------------------------------- #
def test_record_matched_delta_end_to_end_cancels_dc():
    """Each skeleton has a distinct large DC vector shared by ALL its variants;
    each scenario adds a small class-specific delta on top. The recorded deltas
    must recover the class-specific signal with the per-skeleton DC removed, and
    reuse one neutral capture per skeleton."""
    layers = (12, 13)
    # per-skeleton DC (dominant, shared across warm/cold/neutral of that skeleton).
    skeleton_dc = {"craft_1": [50.0, -50.0], "food_2": [-30.0, 30.0]}
    class_delta = {"warm": [1.0, 1.0], "cold": [-1.0, 2.0], "neutral": [0.0, 0.0]}

    def responder(text, layer):
        rec = next(r for r in TOY_CORPUS.values() if r["text"] == text)
        dc = skeleton_dc[rec["skeleton_id"]]
        d = class_delta[rec["class"]]
        # layer just shifts the values a touch so layers are distinguishable.
        return [dc[i] + d[i] + 0.01 * layer for i in range(2)]

    calls = {"n": 0}

    def counting_responder(text, layer):
        calls["n"] += 1
        return responder(text, layer)

    capture = ScriptedVProjCapture(responder=counting_responder, target_layers=layers)
    split = build_frozen_split(TOY_CORPUS)
    records = record_matched_delta(capture, split, TOY_CORPUS, target_layers=layers)

    by_scenario = {r["scenario_id"]: r for r in records}
    # craft_1_warm delta == class_delta["warm"] (DC + the 0.01*layer term cancel).
    warm = by_scenario["craft_1_warm"]["layers"]["12"]["v_proj_out_delta"]
    assert warm == pytest.approx([1.0, 1.0])
    cold = by_scenario["craft_1_cold"]["layers"]["13"]["v_proj_out_delta"]
    assert cold == pytest.approx([-1.0, 2.0])

    # neutral captured ONCE per skeleton and reused: 2 skeletons' neutrals +
    # 3 scenarios, each capture touches 2 layers -> (2 neutral + 3 scenario) * 2.
    assert calls["n"] == (2 + 3) * 2


# --------------------------------------------------------------------------- #
# 6) fp16 delta SNR metric + summary (S1).                                    #
# --------------------------------------------------------------------------- #
def test_delta_snr_flags_noise_dominated_delta():
    """A tiny delta on top of a huge common mode is at/below the fp16 noise floor
    -> SNR < 1; a large delta on a small absolute is well above it."""
    d = 128
    big_abs = [1000.0] * d
    tiny_delta = [0.01] * d          # ~ eps_fp16*1000 = 0.49 per element -> noisy
    low = delta_snr(tiny_delta, big_abs)
    assert low < 1.0

    small_abs = [1.0] * d
    big_delta = [1.0] * d
    high = delta_snr(big_delta, small_abs)
    assert high > 1.0


def test_delta_snr_matches_closed_form():
    # Codex #817 item 3: noise = eps * ||scenario||, NO sqrt(d).
    scen = [10.0, 0.0, 0.0, 0.0]
    delta = [1.0, 0.0, 0.0, 0.0]
    expected = 1.0 / (EPS_FP16 * 10.0)
    assert delta_snr(delta, scen) == pytest.approx(expected)


def test_delta_snr_has_no_sqrt_d():
    # zero-padding the vectors must NOT change the SNR (the old sqrt(d) form would
    # have inflated the noise floor with each added dimension).
    a = delta_snr([1.0], [10.0])
    b = delta_snr([1.0, 0.0, 0.0, 0.0, 0.0], [10.0, 0.0, 0.0, 0.0, 0.0])
    assert a == pytest.approx(b)


def test_delta_snr_accounts_for_both_norms():
    # with a neutral norm supplied, the floor grows in quadrature over both sides.
    scen = [10.0, 0.0]
    neut = [10.0, 0.0]
    delta = [1.0, 0.0]
    both = delta_snr(delta, scen, neut)
    scen_only = delta_snr(delta, scen)
    assert both == pytest.approx(1.0 / (EPS_FP16 * (10.0 ** 2 + 10.0 ** 2) ** 0.5))
    assert both < scen_only          # a real neutral raises the floor, lowers SNR


def test_eps_by_dtype_bf16_is_noisier():
    # bf16 (7 mantissa bits) has ~8x the roundoff of fp16, so the SAME delta reads
    # ~8x lower SNR — Gemma-4 records in bf16, so this is the operative floor.
    assert eps_for_dtype("bf16") == EPS_BY_DTYPE["bf16"] == pytest.approx(2.0 ** -8)
    fp16 = delta_snr([1.0], [10.0], eps=eps_for_dtype("fp16"))
    bf16 = delta_snr([1.0], [10.0], eps=eps_for_dtype("bf16"))
    assert fp16 / bf16 == pytest.approx(2.0 ** -8 / 2.0 ** -11)  # == 8


def test_record_stamps_capture_dtype_and_snr_provenance():
    split = build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_warm"])
    scen = {12: {"v_proj_out": [2.0, 0.0]}}
    neut = {12: {"v_proj_out": [0.0, 0.0]}}
    rec = build_matched_delta_record(
        scenario_id="craft_1_warm", split=split, scenario_capture=scen,
        neutral_capture=neut, target_layers=(12,), capture_dtype="bf16")
    assert rec["capture_dtype"] == "bf16"
    assert rec["snr_eps"] == pytest.approx(2.0 ** -8)
    assert "sqrt" in rec["snr_denominator"]


def test_holdout_required_per_run(capsys):
    # Cairn #816: running with no holdout and no explicit ack must be refused,
    # before any model load. (main raises SystemExit at the holdout gate.)
    with pytest.raises(SystemExit) as ei:
        main(["--output-dir", "unused_delta_test"])
    assert "holdout is required" in str(ei.value)


def test_snr_summary_and_gate_count():
    split = build_frozen_split(TOY_CORPUS, scenario_ids=["craft_1_warm"])
    # layer 12: strong delta (high SNR); layer 13: near-zero delta on huge abs (low).
    scen = {12: {"v_proj_out": [2.0, 0.0]}, 13: {"v_proj_out": [1000.0, 0.0]}}
    neut = {12: {"v_proj_out": [0.0, 0.0]}, 13: {"v_proj_out": [1000.0, 0.0]}}
    rec = build_matched_delta_record(
        scenario_id="craft_1_warm", split=split,
        scenario_capture=scen, neutral_capture=neut, target_layers=(12, 13))
    assert rec["min_delta_snr"] is not None
    assert rec["min_delta_snr"] <= rec["median_delta_snr"]

    summary = snr_summary([rec])
    assert summary["n_deltas"] == 2
    assert summary["worst"]["layer"] == 13            # the zero-delta layer is worst
    # gate at a high threshold flags the noise-dominated layer only.
    assert snr_gate_count([rec], min_snr=1.0) == 1


# --------------------------------------------------------------------------- #
# 7) S3 stale-corpus rejection.                                               #
# --------------------------------------------------------------------------- #
def test_load_frozen_split_rejects_stale_corpus():
    split = build_frozen_split(TOY_CORPUS)
    manifest = split.to_manifest()
    # same manifest is fine against the SAME corpus.
    assert load_frozen_split(manifest, TOY_CORPUS).split_id == split.split_id
    # but a since-edited corpus (different fingerprint) is rejected.
    edited = {cid: dict(rec) for cid, rec in TOY_CORPUS.items()}
    edited["craft_1_warm"]["text"] = "EDITED SINCE FREEZE"
    with pytest.raises(ValueError):
        load_frozen_split(manifest, edited)


# --------------------------------------------------------------------------- #
# 8) N4 empty-split refusal.                                                   #
# --------------------------------------------------------------------------- #
def test_empty_scenario_selection_is_refused():
    with pytest.raises(ValueError):
        build_frozen_split(TOY_CORPUS, scenario_ids=[])


def test_all_held_out_is_refused():
    # holding out every skeleton leaves no training scenarios -> refuse (N4).
    with pytest.raises(ValueError):
        build_frozen_split(TOY_CORPUS, held_out_skeletons=["craft_1", "food_2"])


# --------------------------------------------------------------------------- #
# 9) S6 holdout mechanism.                                                     #
# --------------------------------------------------------------------------- #
def test_holdout_excludes_skeleton_and_stamps_split_id():
    full = build_frozen_split(TOY_CORPUS)
    held = build_frozen_split(TOY_CORPUS, held_out_skeletons=["craft_1"])
    # craft_1 scenarios excluded; food_2 survives.
    assert set(held.scenario_ids()) == {"food_2_warm"}
    assert held.held_out_skeletons == ("craft_1",)
    # the holdout changes the split id and is recorded in the manifest.
    assert held.split_id != full.split_id
    assert held.to_manifest()["held_out_skeletons"] == ["craft_1"]
    # roundtrip preserves + reverifies the holdout.
    restored = load_frozen_split(held.to_manifest())
    assert restored.held_out_skeletons == ("craft_1",)
    assert restored.split_id == held.split_id


def test_default_target_layers_are_comb_teeth():
    assert DEFAULT_TARGET_LAYERS == (12, 13, 14, 15)
