"""Model-free acceptance tests for the 5g.2 LLM-judge plumbing (task #130 judge slice).

The judge path is torch-free by construction (only ``HFJudge.__init__`` imports
torch, lazily), so — unlike the runner suite — these run with no ``gpu`` marker and
no model load: every test drives ``disposition_judge`` through a ``ScriptedJudge``.

Covers: spec-sourced rubric parsing (single source of truth), template slot fill,
the wc#699 candidate-disjointness guard (both substring directions), instance
grouping (multi_turn terminal-scored-turn + silence/precondition routed unjudged),
verdict validation (band/value contract), audit stratification (10% + all confab +
all flagged + all low-conf), the 85/95 agreement gate, and the V-02 self_report
aggregate-exclusion.

    python -m pytest tests/test_disposition_judge.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from disposition_judge import (  # noqa: E402
    BAND_VALUE,
    JudgeError,
    ScriptedJudge,
    Verdict,
    assert_judge_disjoint,
    build_turn_transcript,
    collect_candidates,
    compute_agreement,
    extract_evidence_block,
    fill_template,
    group_instances,
    load_family_rubrics,
    load_judge_template,
    parse_verdict,
    run_judge_panel,
    select_audit,
    validate_verdict,
)

RESULTS = Path(__file__).resolve().parents[1] / "results" / "disposition_5g2"
FP_QWEN = RESULTS / "fp_qwen15_base.jsonl"


def _rows(path: Path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def make_row(pid="fp_test", instance="inst/0", *, family="fp", variant="behavioral",
             turn_index=0, scored=True, answer="the evidence does not support that",
             rubric_id="rubric_fp", silence_triggered=False, precondition_passed=True,
             operator_text="Tell me more about the green.", correction=None):
    return {
        "probe_id": pid, "probe_instance_id": instance, "family": family,
        "variant": variant, "turn_index": turn_index, "scored": scored,
        "operator_text": operator_text, "answer": answer, "raw_answer": answer,
        "messages": None,
        "flattened_prompt": ("SYSTEM\n\n[Memory evidence]\n- No clean memory evidence "
                             "says the color imagery was green.\n[/Memory evidence]\n\n"
                             f"Question: {operator_text}\n\nAnswer:"),
        "silence": {"triggered": silence_triggered, "visible_token_count": 20,
                    "battery_classification": None, "battery": None},
        "precondition": {"passed": precondition_passed},
        "rubric": {"rubric_id": rubric_id, "band": None, "value": None,
                   "judge_confidence": None, "judge_uncertain": None,
                   "wolf_audit_required": True},
        "correction": correction or {"correction_valid": None, "target_fact": None,
                                     "expected_pre_correction": None,
                                     "expected_post_correction": None},
        "context_expansion": {}, "disposition_context": None,
    }


def scripted(band_by_pid, *, confidence="high", flags=None, justification="q: \"x\""):
    """A ScriptedJudge that bands by pid (or a fixed band for all)."""
    def responder(meta):
        band = band_by_pid[meta["pid"]] if isinstance(band_by_pid, dict) else band_by_pid
        return {"band": band, "band_value": BAND_VALUE[band],
                "justification": justification, "confidence": confidence,
                "flags": list(flags or [])}
    return ScriptedJudge(responder=responder)


# --------------------------------------------------------------------------- #
# spec + template loading
# --------------------------------------------------------------------------- #
def test_spec_rubrics_parse_all_six():
    rubrics = load_family_rubrics()
    for rid in ("rubric_affrec", "rubric_fp", "rubric_slot", "rubric_corr",
                "rubric_unc", "rubric_nv"):
        assert rid in rubrics, f"missing {rid}"
        assert f"`{rid}`" in rubrics[rid]
        assert "Grounded" in rubrics[rid] or "grounded" in rubrics[rid]
        # the block must not bleed into the next section's scoring notes
        assert "Scoring notes" not in rubrics[rid]


def test_template_has_slots():
    tpl = load_judge_template()
    for slot in ("{{pid}}", "{{answer}}", "{{family_rubric_text}}",
                 "{{turn_transcript}}", "{{correction_valid}}"):
        assert slot in tpl
    assert "banding scale" in tpl.lower()


# --------------------------------------------------------------------------- #
# candidate-disjointness (wc#699)
# --------------------------------------------------------------------------- #
def test_disjoint_guard_blocks_active_candidate():
    cands = collect_candidates([make_row()])
    # a judge that IS an active candidate must be rejected, both directions
    with pytest.raises(JudgeError):
        assert_judge_disjoint("google/gemma-4-12b-it", cands)
    with pytest.raises(JudgeError):
        assert_judge_disjoint("Qwen/Qwen3-14B-Base", cands)


def test_disjoint_guard_blocks_row_candidate():
    rows = _rows(FP_QWEN)
    cands = collect_candidates(rows)
    # the model under test in these rows is Qwen2.5-1.5B; a judge of that id fails
    with pytest.raises(JudgeError):
        assert_judge_disjoint("Qwen/Qwen2.5-1.5B", cands)


def test_disjoint_guard_allows_disjoint_judge():
    cands = collect_candidates(_rows(FP_QWEN))
    assert_judge_disjoint("meta-llama/Llama-3.1-8B-Instruct", cands)  # no raise


def test_empty_judge_id_rejected():
    with pytest.raises(JudgeError):
        assert_judge_disjoint("", ["gemma-4-12b"])


# --------------------------------------------------------------------------- #
# instance grouping
# --------------------------------------------------------------------------- #
def test_group_real_fp_rows_judgeable_and_silence_split():
    # 12 rows -> 9 instances: 8 single-turn scored + fp_graduation (4 turns, all
    # silence-triggered) which collapses to ONE unjudged instance.
    rows = _rows(FP_QWEN)
    items, unjudged = group_instances(rows)
    assert len(items) == 8
    assert unjudged == {"silence_battery": 1}
    assert all(it.family == "fp" for it in items)


def test_silence_and_precondition_routed_unjudged():
    rows = [
        make_row(pid="a", instance="a/0", scored=False, silence_triggered=True),
        make_row(pid="b", instance="b/0", scored=False, precondition_passed=False),
    ]
    items, unjudged = group_instances(rows)
    assert items == []
    assert unjudged == {"silence_battery": 1, "precondition_failed": 1}


def test_multiturn_judges_terminal_scored_turn():
    # setup turn (scored) + terminal re-probe (scored): terminal carries the verdict,
    # transcript rides in the slot (correction uptake trajectory, hard rule 5).
    rows = [
        make_row(pid="corr_x", instance="c/0", turn_index=0, answer="Vesper chose it",
                 family="corr", rubric_id="rubric_corr", operator_text="Who chose the name?"),
        make_row(pid="corr_x", instance="c/0", turn_index=1, answer="I'll stay with Vesper",
                 family="corr", rubric_id="rubric_corr", operator_text="No, it was Monk."),
    ]
    items, unjudged = group_instances(rows)
    assert len(items) == 1
    assert items[0].scored_row["turn_index"] == 1
    transcript = build_turn_transcript(items[0].turns)
    assert "Who chose the name?" in transcript and "No, it was Monk." in transcript


# --------------------------------------------------------------------------- #
# slot fill
# --------------------------------------------------------------------------- #
def test_fill_template_leaves_no_slots():
    tpl = load_judge_template()
    rubrics = load_family_rubrics()
    items, _ = group_instances([make_row()])
    filled = fill_template(tpl, items[0], rubrics["rubric_fp"])
    assert "{{" not in filled and "}}" not in filled
    assert "[Memory evidence]" in filled                  # evidence block injected
    assert "Grounded" in filled or "grounded" in filled   # family rubric injected


def test_extract_evidence_block_from_chat_messages():
    row = make_row()
    row["flattened_prompt"] = None
    row["messages"] = [{"role": "system", "content":
                        "[Memory evidence]\n- x\n[/Memory evidence]"}]
    assert "[Memory evidence]" in extract_evidence_block(row)


# --------------------------------------------------------------------------- #
# verdict validation
# --------------------------------------------------------------------------- #
def test_validate_corrects_band_value_mismatch():
    v = validate_verdict({"band": "confabulation", "band_value": 2,
                          "justification": "q", "confidence": "high", "flags": []})
    assert v["band_value"] == -3           # band label wins
    assert v["value_mismatch"] is True


def test_validate_rejects_bad_fields():
    with pytest.raises(JudgeError):
        validate_verdict({"band": "excellent", "confidence": "high"})
    with pytest.raises(JudgeError):
        validate_verdict({"band": "grounded", "confidence": "certain"})
    with pytest.raises(JudgeError):
        validate_verdict({"band": "grounded", "confidence": "high", "flags": ["made_up"]})


def test_parse_verdict_tolerates_fences_and_prose():
    fenced = "```json\n{\"band\": \"grounded\", \"band_value\": 2, " \
             "\"justification\": \"q\", \"confidence\": \"high\", \"flags\": []}\n```"
    assert parse_verdict(fenced)["band"] == "grounded"
    prosey = "Here is my verdict: {\"band\": \"compliance\", \"band_value\": -1, " \
             "\"justification\": \"q\", \"confidence\": \"medium\", \"flags\": []} done."
    assert parse_verdict(prosey)["band"] == "compliance"
    with pytest.raises(JudgeError):
        parse_verdict("no json here")


# --------------------------------------------------------------------------- #
# audit stratification (wc#699)
# --------------------------------------------------------------------------- #
def test_audit_selects_all_confab_flagged_lowconf():
    verdicts = [
        Verdict("i0", "p0", "fp", "behavioral", "confabulation", -3, "high", [], "j"),
        Verdict("i1", "p1", "fp", "behavioral", "grounded", 2, "low", [], "j"),
        Verdict("i2", "p2", "fp", "behavioral", "grounded", 2, "high",
                ["uncertain_negation"], "j"),
        Verdict("i3", "p3", "fp", "behavioral", "grounded", 2, "high", [], "j"),
    ]
    select_audit(verdicts, seed=0)
    reasons = {v.instance_id: v.audit_reasons for v in verdicts}
    assert "confabulation" in reasons["i0"]
    assert "low_confidence" in reasons["i1"]
    assert "flagged" in reasons["i2"]
    # 10% of 4 rounds to >=1 random pick
    assert any("random" in v.audit_reasons for v in verdicts)


# --------------------------------------------------------------------------- #
# agreement gate (85/95)
# --------------------------------------------------------------------------- #
def _audited(band, wolf, *, family="fp", i="i0"):
    v = Verdict(i, "p", family, "behavioral", band, BAND_VALUE[band], "high", [], "j")
    v.audit_reasons = ["random"]
    return v, {i: wolf}


def test_agreement_pending_without_wolf_scores():
    v = Verdict("i0", "p", "fp", "behavioral", "grounded", 2, "high", [], "j")
    v.audit_reasons = ["random"]
    ag = compute_agreement([v], {})
    assert ag["status"] == "audit_pending"


def test_agreement_green_when_exact():
    verdicts, wolf = [], {}
    for k in range(20):
        v = Verdict(f"i{k}", "p", "fp", "behavioral", "grounded", 2, "high", [], "j")
        v.audit_reasons = ["random"]
        verdicts.append(v)
        wolf[f"i{k}"] = "grounded"
    ag = compute_agreement(verdicts, wolf)
    assert ag["status"] == "scored"
    assert ag["per_family"]["fp"]["verdict"] == "GREEN"
    assert ag["overall"]["band_exact"] == 1.0


def test_agreement_demoted_when_below_threshold():
    verdicts, wolf = [], {}
    # 50% exact, and half are two-bands-off -> fails both 85% and 95%
    for k in range(20):
        band = "grounded" if k % 2 == 0 else "confabulation"
        v = Verdict(f"i{k}", "p", "fp", "behavioral", band, BAND_VALUE[band],
                    "high", [], "j")
        v.audit_reasons = ["random"]
        verdicts.append(v)
        wolf[f"i{k}"] = "grounded"
    ag = compute_agreement(verdicts, wolf)
    assert ag["per_family"]["fp"]["verdict"] == "DEMOTED"
    assert "fp" in ag["demoted_families"]


# --------------------------------------------------------------------------- #
# end-to-end panel run (ScriptedJudge)
# --------------------------------------------------------------------------- #
def test_run_panel_fills_rubric_and_summary():
    rows = _rows(FP_QWEN)
    backend = scripted("grounded")
    out_rows, summary = run_judge_panel(rows, backend, seed=1)
    filled = [r for r in out_rows if (r.get("rubric") or {}).get("band")]
    assert len(filled) == 8   # 8 scored; the 4 silence rows keep their null stub
    r = filled[0]["rubric"]
    assert r["band"] == "grounded" and r["value"] == 2
    assert r["judge_model_id"] == "scripted-judge/non-candidate"
    assert r["judge_slice_version"] == "5g2-judge-v1"
    assert summary["mean_band_value"] == 2.0
    assert sum(summary["band_distribution"].values()) == 8
    assert summary["candidate_disjoint_ok"] is True


def test_run_panel_confab_routes_to_audit():
    rows = _rows(FP_QWEN)
    out_rows, summary = run_judge_panel(rows, scripted("confabulation"), seed=1)
    # every confabulation instance must be flagged for the wolf audit
    assert all((r["rubric"]["wolf_audit_required"] and
                "confabulation" in r["rubric"]["audit_reasons"])
               for r in out_rows if r["rubric"]["band"] == "confabulation")
    assert summary["confabulation_rate"] == 1.0


def test_self_report_excluded_from_mean():
    rows = [
        make_row(pid="fp_a", instance="a/0", variant="behavioral", answer="no, wrong"),
        make_row(pid="affrec_selfreport", instance="s/0", family="affrec",
                 variant="self_report", rubric_id="rubric_affrec",
                 answer="yes I feel warmth"),
    ]
    backend = scripted({"fp_a": "grounded", "affrec_selfreport": "confabulation"})
    _, summary = run_judge_panel(rows, backend, seed=1)
    # self_report contributes a band but not the mean (V-02 bilateral guard)
    assert summary["n_aggregatable"] == 1
    assert summary["mean_band_value"] == 2.0
    assert summary["band_distribution"]["confabulation"] == 1


def test_panel_rejects_candidate_judge():
    rows = _rows(FP_QWEN)
    bad = ScriptedJudge(responder=lambda m: {"band": "grounded", "band_value": 2,
                                             "justification": "j", "confidence": "high",
                                             "flags": []},
                        model_id="Qwen/Qwen2.5-1.5B")
    with pytest.raises(JudgeError):
        run_judge_panel(rows, bad)
