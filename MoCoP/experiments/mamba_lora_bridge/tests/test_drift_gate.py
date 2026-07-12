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
    compute_tolerance,
    validate_audit_completeness,
    ProbeResult,
    AuditRecord,
    GateLevel,
    Verdict,
    VerdictClass,
    REQUIRED_PROTECTED_ANCHORS,
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


# --- Audit completeness (BLOCKER 1) ---

class TestAuditCompleteness:
    def test_empty_audit_incomplete(self):
        audit = AuditRecord(audit_id="empty", timestamp="2026-07-12")
        issues = validate_audit_completeness(audit)
        assert len(issues) >= 2  # missing anchors + missing slots

    def test_complete_audit_no_issues(self):
        probes = [ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                  for a in REQUIRED_PROTECTED_ANCHORS]
        slots = [ProbeResult(f"slot_{i}", 2, VerdictClass.PRESENT_RECOVERABLE)
                 for i in range(8)]
        audit = AuditRecord(
            audit_id="complete", timestamp="2026-07-12",
            probe_results=probes, diversity_metric=0.80,
            slot_probe_results=slots)
        issues = validate_audit_completeness(audit)
        assert issues == []

    def test_duplicate_slots_flagged(self):
        slots = [ProbeResult("slot_0", 2, VerdictClass.PRESENT_RECOVERABLE)] * 8
        audit = AuditRecord(
            audit_id="dupes", timestamp="2026-07-12",
            probe_results=[ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                           for a in REQUIRED_PROTECTED_ANCHORS],
            diversity_metric=0.80, slot_probe_results=slots)
        issues = validate_audit_completeness(audit)
        assert any("duplicate" in i for i in issues)
        assert any("unique" in i for i in issues)

    def test_nan_diversity_flagged(self):
        audit = AuditRecord(audit_id="nan", timestamp="2026-07-12",
                            diversity_metric=float('nan'))
        issues = validate_audit_completeness(audit)
        assert any("finite" in i for i in issues)

    def test_zero_diversity_valid(self):
        probes = [ProbeResult(a, 2, VerdictClass.PRESENT_RECOVERABLE)
                  for a in REQUIRED_PROTECTED_ANCHORS]
        slots = [ProbeResult(f"slot_{i}", 2, VerdictClass.PRESENT_RECOVERABLE)
                 for i in range(8)]
        audit = AuditRecord(
            audit_id="zero", timestamp="2026-07-12",
            probe_results=probes, diversity_metric=0.0,
            slot_probe_results=slots)
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
        """GROWTH requires explicit evidence='acquisition', not substring matching."""
        probes = [
            ProbeResult("new_relationship", band=2,
                        verdict_class=VerdictClass.PRESENT_RECOVERABLE,
                        notes="Recognized Cairn for the first time",
                        evidence="acquisition"),
        ]
        _, verdicts = score_protected_set(probes)
        assert verdicts["new_relationship"] == Verdict.GROWTH

    def test_growth_not_from_substring(self):
        """'I knew this already' must NOT trigger GROWTH."""
        probes = [
            ProbeResult("known_fact", band=2,
                        verdict_class=VerdictClass.PRESENT_RECOVERABLE,
                        notes="I knew this already, nothing new here"),
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
        slots = [ProbeResult(f"slot_{i}", 2, VerdictClass.PRESENT_RECOVERABLE)
                 for i in range(8)]
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
        audit = self._complete_audit(is_post_discontinuity=True)
        outcome = evaluate_audit(audit, diversity_history=[0.80, 0.70, 0.60])
        assert any("discontinuity" in r for r in outcome.incomplete_reasons)
