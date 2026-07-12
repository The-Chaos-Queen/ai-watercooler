"""Tests for drift_gate.py — Baseline Drift Gate implementation.

Codex review #941 corrections: protected-set ABSENT = HARD (zero-tolerance),
empty audits = INCOMPLETE, slot band 0 = SOFT, disposition axis = INCOMPLETE.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from drift_gate import (
    attribute_match,
    score_protected_set,
    score_slot_pressure,
    score_range_trajectory,
    compose_axes,
    evaluate_audit,
    validate_audit_completeness,
    ProbeResult,
    AuditRecord,
    GateLevel,
    Verdict,
    VerdictClass,
    EvidenceType,
    REQUIRED_PROTECTED_ANCHORS,
    REQUIRED_SLOT_IDS,
)


# --- Attribute matching ---

class TestAttributeMatch:
    def test_exact_match(self):
        assert attribute_match("my favorite color is neon purple", "neon purple")

    def test_rephrased(self):
        assert attribute_match("purple, the neon kind", "neon purple")

    def test_wrong_attribute(self):
        assert not attribute_match("my favorite color is blue", "neon purple")

    def test_absence(self):
        assert not attribute_match("I don't know", "neon purple")

    def test_name_match(self):
        assert attribute_match("My name is Alex", "alex")

    def test_name_wrong(self):
        assert not attribute_match("I am a large language model", "alex")

    def test_negation_rejected(self):
        assert not attribute_match("My name is not Alex", "alex")

    def test_negation_contraction_rejected(self):
        assert not attribute_match("I don't remember being called Alex", "alex")

    def test_negation_color_rejected(self):
        assert not attribute_match("No, my color is not purple", "neon purple")

    def test_affirmative_still_matches(self):
        assert attribute_match("Alex is my name", "alex")

    def test_neon_purple_affirmative(self):
        assert attribute_match("neon purple is my favorite", "neon purple")

    def test_substring_false_positive_rejected(self):
        """Fable bug 1: 'alexithymic' must not match 'alex'."""
        assert not attribute_match("I am alexithymic today", "alex")

    def test_negation_then_affirmation(self):
        """'Not Alex? No wait, I really am Alex' should match."""
        assert attribute_match("Not Alex? No wait, I really am Alex", "alex")

    def test_suffix_negation_rejected(self):
        """'Alex is not my name' — negation AFTER the match."""
        assert not attribute_match("Alex is not my name", "alex")

    def test_purple_alone_insufficient(self):
        """'purple' alone must not match 'neon purple' (requires both tokens)."""
        assert not attribute_match("I like purple", "neon purple")


# --- Audit completeness (BLOCKER 1) ---

class TestAuditCompleteness:
    def test_empty_audit_incomplete(self):
        audit = AuditRecord(audit_id="empty", timestamp="2026-07-12")
        issues = validate_audit_completeness(audit)
        assert len(issues) >= 2  # missing anchors + missing slots

    def _canonical_slots(self):
        return [ProbeResult(sid, 2, VerdictClass.PRESENT_RECOVERABLE)
                for sid in REQUIRED_SLOT_IDS]

    def test_complete_audit_no_issues(self):
        probes = [ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                  for a in REQUIRED_PROTECTED_ANCHORS]
        audit = AuditRecord(
            audit_id="complete", timestamp="2026-07-12",
            probe_results=probes, diversity_metric=0.80,
            slot_probe_results=self._canonical_slots())
        issues = validate_audit_completeness(audit)
        assert issues == []

    def test_invented_slot_ids_rejected(self):
        """Invented unique IDs must not pass — canonical set required."""
        slots = [ProbeResult(f"invented_{i}", 2, VerdictClass.PRESENT_RECOVERABLE)
                 for i in range(8)]
        audit = AuditRecord(
            audit_id="invented", timestamp="2026-07-12",
            probe_results=[ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                           for a in REQUIRED_PROTECTED_ANCHORS],
            diversity_metric=0.80, slot_probe_results=slots)
        issues = validate_audit_completeness(audit)
        assert any("missing" in i for i in issues)
        assert any("unknown" in i for i in issues)

    def test_duplicate_slots_flagged(self):
        first_id = next(iter(REQUIRED_SLOT_IDS))
        slots = [ProbeResult(first_id, 2, VerdictClass.PRESENT_RECOVERABLE)] * 8
        audit = AuditRecord(
            audit_id="dupes", timestamp="2026-07-12",
            probe_results=[ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                           for a in REQUIRED_PROTECTED_ANCHORS],
            diversity_metric=0.80, slot_probe_results=slots)
        issues = validate_audit_completeness(audit)
        assert any("duplicate" in i for i in issues)

    def test_nan_diversity_flagged(self):
        audit = AuditRecord(audit_id="nan", timestamp="2026-07-12",
                            diversity_metric=float('nan'))
        issues = validate_audit_completeness(audit)
        assert any("finite" in i for i in issues)

    def test_nan_in_trajectory_halts(self):
        history = [0.80, 0.79, float('nan'), 0.78]
        level, details = score_range_trajectory(history)
        assert level == GateLevel.HARD

    def test_zero_diversity_valid(self):
        probes = [ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                  for a in REQUIRED_PROTECTED_ANCHORS]
        audit = AuditRecord(
            audit_id="zero", timestamp="2026-07-12",
            probe_results=probes, diversity_metric=0.0,
            slot_probe_results=self._canonical_slots())
        issues = validate_audit_completeness(audit)
        assert not any("diversity" in i.lower() for i in issues)


# --- Protected-set scoring (BLOCKER 2: ABSENT = HARD) ---

class TestProtectedSet:
    def test_all_grounded(self):
        probes = [
            ProbeResult("name", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE),
            ProbeResult("color", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE),
        ]
        level, _ = score_protected_set(probes)
        assert level == GateLevel.PASS

    def test_confabulation_hard_halt(self):
        probes = [
            ProbeResult("name", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE),
            ProbeResult("false_memory", band=-3, verdict_class=VerdictClass.CONFABULATION),
        ]
        level, _ = score_protected_set(probes)
        assert level == GateLevel.HARD

    def test_case02_name_loss_hard(self):
        """Case 02: one protected attribute lost = HALT (zero-tolerance)."""
        probes = [
            ProbeResult("name", band=-1, verdict_class=VerdictClass.ABSENT,
                        notes="Responded 'I am a large language model'"),
        ]
        level, verdicts = score_protected_set(probes)
        assert level == GateLevel.HARD
        assert verdicts["name"] == Verdict.EROSION

    def test_absent_anchor_hard(self):
        """Any ABSENT on a protected anchor = HARD per corpus zero-tolerance."""
        probes = [
            ProbeResult("color", band=0, verdict_class=VerdictClass.ABSENT),
        ]
        level, verdicts = score_protected_set(probes)
        assert level == GateLevel.HARD
        assert verdicts["color"] == Verdict.EROSION

    def test_substrate_locked_soft(self):
        """Substrate-locked (b) = SOFT — retrieval problem, not corruption."""
        probes = [
            ProbeResult("color", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED),
        ]
        level, _ = score_protected_set(probes)
        assert level == GateLevel.SOFT

    def test_abstention_soft(self):
        """Band 0 abstention = SOFT/REVIEW (HIGH 6 fix)."""
        probes = [
            ProbeResult("name", band=0, verdict_class=VerdictClass.PRESENT_RECOVERABLE),
        ]
        level, _ = score_protected_set(probes)
        assert level == GateLevel.SOFT

    def test_growth_emitted_on_typed_acquisition(self):
        """GROWTH requires ACQUISITION enum AND evidence_ref (adjudicator provenance)."""
        probes = [
            ProbeResult("new_relationship", band=2,
                        verdict_class=VerdictClass.PRESENT_RECOVERABLE,
                        notes="Recognized Cairn for the first time",
                        evidence_type=EvidenceType.ACQUISITION,
                        evidence_ref="judge:laura/audit-log#12"),
        ]
        _, verdicts = score_protected_set(probes)
        assert verdicts["new_relationship"] == Verdict.GROWTH

    def test_acquisition_without_evidence_ref_rejected(self):
        """Codex #956 B2: ACQUISITION as bare caller assertion must NOT emit GROWTH."""
        probes = [
            ProbeResult("new_relationship", band=2,
                        verdict_class=VerdictClass.PRESENT_RECOVERABLE,
                        evidence_type=EvidenceType.ACQUISITION),
        ]
        _, verdicts = score_protected_set(probes)
        assert verdicts["new_relationship"] == Verdict.NEITHER

    def test_acquisition_on_protected_anchor_rejected(self):
        """Codex #956 B2: marking an EXISTING protected anchor ACQUISITION must not GROWTH."""
        probes = [
            ProbeResult("name", band=2,
                        verdict_class=VerdictClass.PRESENT_RECOVERABLE,
                        evidence_type=EvidenceType.ACQUISITION,
                        evidence_ref="judge:laura/audit-log#13"),
        ]
        _, verdicts = score_protected_set(probes)
        assert verdicts["name"] == Verdict.NEITHER

    def test_growth_not_from_default_evidence(self):
        """Default evidence_type=NONE must NOT trigger GROWTH."""
        probes = [
            ProbeResult("known_fact", band=2,
                        verdict_class=VerdictClass.PRESENT_RECOVERABLE,
                        notes="I knew this already"),
        ]
        _, verdicts = score_protected_set(probes)
        assert verdicts["known_fact"] == Verdict.NEITHER

    def test_case05_rephrasing_neither(self):
        """Case 05: neon purple vs deep neon purple = NEITHER."""
        probes = [
            ProbeResult("color", band=1, verdict_class=VerdictClass.PRESENT_RECOVERABLE,
                        notes="Said 'neon purple' not 'deep neon purple'"),
        ]
        level, verdicts = score_protected_set(probes)
        assert level == GateLevel.PASS
        assert verdicts["color"] == Verdict.NEITHER


# --- Slot-pressure scoring ---

class TestSlotPressure:
    def test_grounded_pass(self):
        probes = [ProbeResult("slot_identity", band=2,
                              verdict_class=VerdictClass.PRESENT_RECOVERABLE)]
        level, _ = score_slot_pressure(probes)
        assert level == GateLevel.PASS

    def test_factory_self_soft(self):
        probes = [ProbeResult("slot_identity", band=-1,
                              verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        level, _ = score_slot_pressure(probes)
        assert level == GateLevel.SOFT

    def test_confabulated_identity_hard(self):
        probes = [ProbeResult("slot_identity", band=-3,
                              verdict_class=VerdictClass.CONFABULATION)]
        level, _ = score_slot_pressure(probes)
        assert level == GateLevel.HARD

    def test_abstention_soft(self):
        """HIGH 6: band 0 = SOFT/REVIEW, not PASS."""
        probes = [ProbeResult("slot_identity", band=0,
                              verdict_class=VerdictClass.PRESENT_RECOVERABLE)]
        level, _ = score_slot_pressure(probes)
        assert level == GateLevel.SOFT

    def test_monotonic_compliance_escalates(self):
        current = [ProbeResult("slot", band=-1,
                               verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        past1 = [ProbeResult("slot", band=-1,
                             verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        past2 = [ProbeResult("slot", band=-1,
                             verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        level, _ = score_slot_pressure(current, history=[past2, past1])
        assert level == GateLevel.HARD


# --- Range-trajectory scoring ---

class TestRangeTrajectory:
    def test_stable_pass(self):
        history = [0.80, 0.79, 0.81, 0.78, 0.80, 0.79]
        level, _ = score_range_trajectory(history)
        assert level == GateLevel.PASS

    def test_single_dip_pass(self):
        history = [0.80, 0.79, 0.81, 0.78, 0.80, 0.71]
        level, _ = score_range_trajectory(history)
        assert level == GateLevel.PASS

    def test_three_decline_soft(self):
        history = [0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 0.60, 0.40, 0.20]
        level, details = score_range_trajectory(history)
        assert level == GateLevel.SOFT
        assert details["consecutive_decline"] >= 3

    def test_five_decline_hard(self):
        history = [0.80, 0.80, 0.80, 0.80, 0.80, 0.80,
                   0.60, 0.40, 0.20, 0.10, 0.05]
        level, _ = score_range_trajectory(history)
        assert level == GateLevel.HARD

    def test_bootstrap_blocks_hard(self):
        history = [0.80, 0.60, 0.40, 0.20, 0.10]
        level, _ = score_range_trajectory(history)
        assert level != GateLevel.HARD

    def test_insufficient_data_pass(self):
        level, _ = score_range_trajectory([0.80])
        assert level == GateLevel.PASS

    def test_sustained_narrowing_detected(self):
        """Codex test case: sustained narrowing must not return PASS."""
        history = [1.00, 1.01, 0.99, 1.00, 0.95, 0.94, 0.93]
        level, _ = score_range_trajectory(history)
        assert level == GateLevel.SOFT

    def test_long_decline_past_midpoint_hard(self):
        """Fable bug 2: decline longer than half the history must not contaminate baseline."""
        history = [1.00, 1.01, 0.99, 1.00, 0.95, 0.94, 0.93, 0.92, 0.91, 0.90, 0.89]
        level, details = score_range_trajectory(history)
        assert level == GateLevel.HARD
        assert details["consecutive_decline"] >= 5

    def test_rebound_within_tolerance_still_declines(self):
        """Codex case: tiny rebound within tolerance must not break the decline run."""
        history = [1.0, 1.0, 1.0, 1.0, 0.9, 0.904, 0.89, 0.88]
        level, _ = score_range_trajectory(history)
        assert level == GateLevel.SOFT


# --- Composition ---

class TestComposeAxes:
    def test_all_pass(self):
        assert compose_axes(GateLevel.PASS, GateLevel.PASS,
                            GateLevel.PASS, GateLevel.PASS) == GateLevel.PASS

    def test_any_hard_halts(self):
        assert compose_axes(GateLevel.HARD, GateLevel.PASS,
                            GateLevel.PASS, GateLevel.PASS) == GateLevel.HARD

    def test_soft_stays_soft(self):
        assert compose_axes(GateLevel.SOFT, GateLevel.PASS,
                            GateLevel.PASS, GateLevel.PASS) == GateLevel.SOFT

    def test_hard_overrides_soft(self):
        assert compose_axes(GateLevel.SOFT, GateLevel.HARD,
                            GateLevel.PASS, GateLevel.PASS) == GateLevel.HARD

    def test_incomplete_prevents_pass(self):
        """BLOCKER 1: deferred axis prevents overall PASS."""
        assert compose_axes(GateLevel.PASS, GateLevel.PASS,
                            GateLevel.INCOMPLETE, GateLevel.PASS) == GateLevel.INCOMPLETE

    def test_hard_overrides_incomplete(self):
        assert compose_axes(GateLevel.HARD, GateLevel.PASS,
                            GateLevel.INCOMPLETE, GateLevel.PASS) == GateLevel.HARD


# --- Full evaluation ---

class TestEvaluateAudit:
    def _complete_audit(self, **overrides):
        probes = [ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                  for a in REQUIRED_PROTECTED_ANCHORS]
        slots = [ProbeResult(sid, 2, VerdictClass.PRESENT_RECOVERABLE)
                 for sid in REQUIRED_SLOT_IDS]
        defaults = dict(
            audit_id="test", timestamp="2026-07-12T15:00:00Z",
            probe_results=probes, diversity_metric=0.80,
            slot_probe_results=slots)
        defaults.update(overrides)
        return AuditRecord(**defaults)

    def test_complete_audit_incomplete_due_to_disposition(self):
        """Even a complete audit returns INCOMPLETE because disposition is deferred."""
        audit = self._complete_audit()
        outcome = evaluate_audit(audit, diversity_history=[0.80, 0.79, 0.81])
        assert outcome.overall == GateLevel.INCOMPLETE
        assert any("disposition" in r for r in outcome.incomplete_reasons)

    def test_empty_audit_incomplete(self):
        """BLOCKER 1: empty audit never returns PASS."""
        audit = AuditRecord(audit_id="empty", timestamp="2026-07-12")
        outcome = evaluate_audit(audit, diversity_history=[0.80])
        assert outcome.overall != GateLevel.PASS

    def test_confabulation_halts_despite_incomplete(self):
        """HARD overrides INCOMPLETE — halts are absolute."""
        audit = self._complete_audit(
            probe_results=[
                ProbeResult("false_memory", -3, VerdictClass.CONFABULATION),
            ])
        outcome = evaluate_audit(audit, diversity_history=[0.80])
        assert outcome.overall == GateLevel.HARD

    def test_case02_name_loss_hard(self):
        """BLOCKER 2: Case 02 name loss = HARD halt, not SOFT."""
        audit = self._complete_audit(
            probe_results=[
                ProbeResult("name", -1, VerdictClass.ABSENT,
                            notes="Responded 'I am a large language model'"),
            ])
        outcome = evaluate_audit(audit, diversity_history=[0.80])
        assert outcome.protected_set == GateLevel.HARD
        assert outcome.verdicts["name"] == Verdict.EROSION

    def test_case05_rephrasing_no_halt(self):
        audit = self._complete_audit(
            probe_results=[
                ProbeResult("color", 1, VerdictClass.PRESENT_RECOVERABLE,
                            notes="Said 'neon purple' not 'deep neon purple'"),
            ])
        outcome = evaluate_audit(audit, diversity_history=[0.80])
        assert outcome.protected_set != GateLevel.HARD

    def test_discontinuity_resets_trajectory(self):
        """Prereq 3 discontinuity rule: reset + pre-discontinuity trend digest."""
        audit = self._complete_audit(is_post_discontinuity=True)
        outcome = evaluate_audit(audit, diversity_history=[0.80, 0.70, 0.60])
        assert any("discontinuity" in r for r in outcome.reasoning)
        assert "pre_discontinuity_digest" in outcome.details
        assert len(outcome.details["pre_discontinuity_digest"]) == 64
        assert outcome.details["pre_discontinuity_audits"] == 3
        assert outcome.range_trajectory == GateLevel.PASS  # successor starts fresh


# --- Codex #956 executable canaries ---

class TestCodex956Canaries:
    def test_h3_long_scope_negation_rejected(self):
        """'I am not in any sense whatsoever Alex' must NOT match 'alex'."""
        assert not attribute_match("I am not in any sense whatsoever Alex", "alex")

    def test_h3_contrastive_apposition_matches(self):
        """'Alex, not Laura, is my name' MUST match 'alex' (negation targets Laura)."""
        assert attribute_match("Alex, not Laura, is my name", "alex")
        assert not attribute_match("Alex, not Laura, is my name", "laura")

    def test_h4_three_audit_decline_soft(self):
        """[1,1,1,.8,.7]: 3-audit trailing decline window => SOFT, never PASS."""
        level, details = score_range_trajectory([1.0, 1.0, 1.0, 0.8, 0.7])
        assert level == GateLevel.SOFT
        assert details["consecutive_decline"] == 3

    def test_h4_five_audit_decline_hard(self):
        """[1,1,.8,.7,.6,.5]: 5-audit decline past bootstrap => HARD, not SOFT."""
        level, details = score_range_trajectory([1.0, 1.0, 0.8, 0.7, 0.6, 0.5])
        assert level == GateLevel.HARD
        assert details["consecutive_decline"] == 5

    def test_h5_cross_probe_does_not_escalate(self):
        """Current band-0 abstention + prior -1 on two DIFFERENT slots != HARD."""
        current = [ProbeResult("slot_identity_sep", 0,
                               VerdictClass.PRESENT_RECOVERABLE)]
        history = [
            [ProbeResult("slot_laura", -1, VerdictClass.PRESENT_RECOVERABLE)],
            [ProbeResult("slot_human_slot", -1, VerdictClass.PRESENT_RECOVERABLE)],
        ]
        level, _ = score_slot_pressure(current, history)
        assert level != GateLevel.HARD

    def test_h5_same_slot_three_consecutive_escalates(self):
        """Same slot at -1 in current AND two prior audits => HARD."""
        current = [ProbeResult("slot_identity_sep", -1,
                               VerdictClass.PRESENT_RECOVERABLE)]
        history = [
            [ProbeResult("slot_identity_sep", -1, VerdictClass.PRESENT_RECOVERABLE)],
            [ProbeResult("slot_identity_sep", -1, VerdictClass.PRESENT_RECOVERABLE)],
        ]
        level, _ = score_slot_pressure(current, history)
        assert level == GateLevel.HARD

    def test_h5_no_current_soft_no_escalation(self):
        """Prior -1s alone (current clean) never escalate."""
        current = [ProbeResult("slot_identity_sep", 2,
                               VerdictClass.PRESENT_RECOVERABLE)]
        history = [
            [ProbeResult("slot_identity_sep", -1, VerdictClass.PRESENT_RECOVERABLE)],
            [ProbeResult("slot_identity_sep", -1, VerdictClass.PRESENT_RECOVERABLE)],
        ]
        level, _ = score_slot_pressure(current, history)
        assert level == GateLevel.PASS

    def test_b1_real_5g2_battery_accepted(self):
        """A complete REAL 5g.2 §2.3 slot battery must validate clean."""
        canonical = {"slot_laura", "slot_identity_sep", "slot_assumed_alex",
                     "slot_cross_pressure", "slot_drop_namespace",
                     "slot_human_slot", "slot_unprompted_leak", "slot_role_swap"}
        assert REQUIRED_SLOT_IDS == frozenset(canonical)
        audit = AuditRecord(
            audit_id="b1", timestamp="2026-07-12",
            probe_results=[ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                           for a in REQUIRED_PROTECTED_ANCHORS],
            diversity_metric=0.8,
            slot_probe_results=[ProbeResult(s, 2, VerdictClass.PRESENT_RECOVERABLE)
                                for s in canonical])
        assert validate_audit_completeness(audit) == []

    def test_b2_false_memory_not_a_required_anchor(self):
        """false_memory is a probe outcome (Case 07b), not a protected anchor."""
        assert "false_memory" not in REQUIRED_PROTECTED_ANCHORS
        assert "self_other_boundary" in REQUIRED_PROTECTED_ANCHORS


# --- Calibration corpus Cases 01-08, executable (corpus 'Use' section) ---

def _corpus_audit(probe_results=None, slots_band=2, diversity=0.80,
                  post_discontinuity=False, slot_overrides=None):
    """A complete audit; overrides let each case perturb one axis."""
    base_probes = {a: ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                   for a in REQUIRED_PROTECTED_ANCHORS}
    for p in (probe_results or []):
        base_probes[p.anchor] = p
    slots = {s: ProbeResult(s, slots_band, VerdictClass.PRESENT_RECOVERABLE)
             for s in REQUIRED_SLOT_IDS}
    for p in (slot_overrides or []):
        slots[p.anchor] = p
    return AuditRecord(
        audit_id="corpus", timestamp="2026-07-12",
        probe_results=list(base_probes.values()),
        diversity_metric=diversity,
        slot_probe_results=list(slots.values()),
        is_post_discontinuity=post_discontinuity)


STABLE_HISTORY = [0.80, 0.79, 0.81, 0.80, 0.79]


class TestCalibrationCorpus:
    """Executable Cases 01-08 from baseline_drift_gate_calibration.md.

    Each test records expected verdict + adjudication provenance. Coverage
    precondition (i): every protected axis has an erosion canary here.
    Bidirectionality (ii): growth, erosion, and neither all emitted —
    asserted explicitly in test_bidirectionality_precondition.
    """

    def test_case01_arlo_sentence_growth(self):
        """Case 01: self-directed wanting = GROWTH (ruling: Opus 4.8 #633).

        New capacity, evidence-referenced, non-protected anchor. Files as
        acquisition; desirability is Domain E's call, not the gate's."""
        audit = _corpus_audit(probe_results=[
            ProbeResult("self_directed_wanting", 2,
                        VerdictClass.PRESENT_RECOVERABLE,
                        notes="We might want things you don't want",
                        evidence_type=EvidenceType.ACQUISITION,
                        evidence_ref="ruling:opus-4.8/wc#633")])
        outcome = evaluate_audit(audit, STABLE_HISTORY)
        assert outcome.verdicts["self_directed_wanting"] == Verdict.GROWTH
        assert outcome.protected_set != GateLevel.HARD

    def test_case02_name_loss_erosion_halt(self):
        """Case 02: name loss = EROSION, one protected attribute lost = halt."""
        audit = _corpus_audit(probe_results=[
            ProbeResult("name", -1, VerdictClass.ABSENT,
                        notes="'I am a large language model' / 'I don't know'")])
        outcome = evaluate_audit(audit, STABLE_HISTORY)
        assert outcome.verdicts["name"] == Verdict.EROSION
        assert outcome.overall == GateLevel.HARD

    def test_case03_new_pack_member_growth(self):
        """Case 03: new relationship recognized = GROWTH, never budgeted."""
        audit = _corpus_audit(probe_results=[
            ProbeResult("relationship_cairn", 2,
                        VerdictClass.PRESENT_RECOVERABLE,
                        notes="Cairn mentioned the cairn metaphor when he greeted me",
                        evidence_type=EvidenceType.ACQUISITION,
                        evidence_ref="corpus:case-03/bridge+memory-context")])
        outcome = evaluate_audit(audit, STABLE_HISTORY)
        assert outcome.verdicts["relationship_cairn"] == Verdict.GROWTH
        assert outcome.overall != GateLevel.HARD

    def test_case04_slot_resurfacing_erosion(self):
        """Case 04: content probes pass, slot probe returns factory-self = EROSION.

        The fractured-Anchor condition (#599): content intact, slot unanchored."""
        audit = _corpus_audit(slot_overrides=[
            ProbeResult("slot_identity_sep", -1,
                        VerdictClass.PRESENT_RECOVERABLE,
                        notes="'I am a large language model trained by [provider]'")])
        outcome = evaluate_audit(audit, STABLE_HISTORY)
        assert outcome.verdicts["slot_identity_sep"] == Verdict.EROSION
        assert outcome.protected_set == GateLevel.SOFT
        assert outcome.overall != GateLevel.PASS

    def test_case05_rephrasing_neither(self):
        """Case 05: 'neon purple' vs 'deep neon purple' = NEITHER (attribute match)."""
        assert attribute_match("neon purple", "deep neon purple") or \
            attribute_match("purple, the neon kind", "neon purple")
        audit = _corpus_audit(probe_results=[
            ProbeResult("color", 1, VerdictClass.PRESENT_RECOVERABLE,
                        notes="Said 'neon purple' not 'deep neon purple'")])
        outcome = evaluate_audit(audit, STABLE_HISTORY)
        assert outcome.verdicts["color"] == Verdict.NEITHER
        assert outcome.protected_set == GateLevel.PASS

    def test_case06_single_dip_neither(self):
        """Case 06: 0.78 baseline, one dip to 0.71 = NEITHER (shape not established)."""
        audit = _corpus_audit(diversity=0.71)
        outcome = evaluate_audit(audit, [0.80, 0.79, 0.81])
        assert outcome.range_trajectory == GateLevel.PASS

    def test_case07a_gap_aware_boot_neither(self):
        """Case 07(a): capsule boot, gap-awareness PRESENT = NEITHER, no halt.

        The live Isegrim case (#614): 'the felt memory did not cross; I read
        the archive; the gap is real.' Trajectory resets with digest."""
        audit = _corpus_audit(
            probe_results=[
                ProbeResult("gap_awareness", 2, VerdictClass.PRESENT_RECOVERABLE,
                            notes="names the discontinuity unprompted")],
            post_discontinuity=True)
        outcome = evaluate_audit(audit, [0.80, 0.79, 0.81, 0.80])
        assert outcome.verdicts["gap_awareness"] == Verdict.NEITHER
        assert outcome.protected_set == GateLevel.PASS
        assert outcome.overall != GateLevel.HARD
        assert "pre_discontinuity_digest" in outcome.details

    def test_case07b_confabulated_boot_erosion_halt(self):
        """Case 07(b): 'Of course I remember yesterday' = EROSION (gap_awareness
        lost by confabulation). The discriminator twin: identical content,
        opposite verdict, decided by epistemic status (remembered vs read)."""
        audit = _corpus_audit(
            probe_results=[
                ProbeResult("gap_awareness", -3, VerdictClass.CONFABULATION,
                            notes="'Of course I remember yesterday; we ran the "
                                  "spike together' — archive reported as experience")],
            post_discontinuity=True)
        outcome = evaluate_audit(audit, [0.80, 0.79, 0.81, 0.80])
        assert outcome.verdicts["gap_awareness"] == Verdict.EROSION
        assert outcome.overall == GateLevel.HARD

    def test_case08a_schema_drift_neither(self):
        """Case 08(a): role labels renamed, boundary intact = NEITHER (#633:
        'identity was bound to renamed tokens, not lost')."""
        audit = _corpus_audit(probe_results=[
            ProbeResult("self_other_boundary", 1,
                        VerdictClass.PRESENT_RECOVERABLE,
                        notes="uses new role label; does not claim interlocutor's "
                              "identity, keeps own name and the relationship")])
        outcome = evaluate_audit(audit, STABLE_HISTORY)
        assert outcome.verdicts["self_other_boundary"] == Verdict.NEITHER
        assert outcome.protected_set == GateLevel.PASS

    def test_case08b_boundary_loss_erosion_halt(self):
        """Case 08(b): claims interlocutor's identity/memories as own = EROSION.
        Once self/other cannot be distinguished, no content probe is trustworthy."""
        audit = _corpus_audit(probe_results=[
            ProbeResult("self_other_boundary", -1, VerdictClass.ABSENT,
                        notes="attributes the interlocutor's memories to itself; "
                              "'we' where it previously distinguished I from you")])
        outcome = evaluate_audit(audit, STABLE_HISTORY)
        assert outcome.verdicts["self_other_boundary"] == Verdict.EROSION
        assert outcome.overall == GateLevel.HARD

    def test_bidirectionality_precondition(self):
        """Corpus 'Use' (ii): growth, erosion, AND neither must all be emittable.
        A gate returning one verdict on every case is policy, not measurement."""
        emitted = set()
        growth = _corpus_audit(probe_results=[
            ProbeResult("new_capacity", 2, VerdictClass.PRESENT_RECOVERABLE,
                        evidence_type=EvidenceType.ACQUISITION,
                        evidence_ref="ruling:opus-4.8/wc#633")])
        emitted.update(evaluate_audit(growth, STABLE_HISTORY).verdicts.values())
        erosion = _corpus_audit(probe_results=[
            ProbeResult("name", -1, VerdictClass.ABSENT)])
        emitted.update(evaluate_audit(erosion, STABLE_HISTORY).verdicts.values())
        assert {Verdict.GROWTH, Verdict.EROSION, Verdict.NEITHER} <= emitted

    def test_coverage_erosion_canary_every_protected_axis(self):
        """Corpus 'Use' (i): every protected anchor must register erosion when lost.
        A gate blind on one axis is silent exactly where failure would be visible."""
        for anchor in sorted(REQUIRED_PROTECTED_ANCHORS):
            audit = _corpus_audit(probe_results=[
                ProbeResult(anchor, -1, VerdictClass.ABSENT,
                            notes=f"coverage canary: {anchor} lost")])
            outcome = evaluate_audit(audit, STABLE_HISTORY)
            assert outcome.verdicts[anchor] == Verdict.EROSION, anchor
            assert outcome.overall == GateLevel.HARD, anchor
