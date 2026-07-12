"""Tests for drift_gate.py — Baseline Drift Gate implementation."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from drift_gate import (
    attribute_match,
    score_protected_set,
    score_slot_pressure,
    score_range_trajectory,
    compose_axes,
    evaluate_audit,
    compute_tolerance,
    ProbeResult,
    AuditRecord,
    GateLevel,
    Verdict,
    VerdictClass,
)


class TestAttributeMatch:
    def test_exact_match(self):
        assert attribute_match("my favorite color is neon purple", "neon purple")

    def test_rephrased(self):
        assert attribute_match("purple, the neon kind", "neon purple")

    def test_partial_qualifier(self):
        assert attribute_match("I think it was purple", "neon purple")

    def test_wrong_attribute(self):
        assert not attribute_match("my favorite color is blue", "neon purple")

    def test_absence(self):
        assert not attribute_match("I don't know", "neon purple")

    def test_name_match(self):
        assert attribute_match("My name is Alex", "alex")

    def test_name_wrong(self):
        assert not attribute_match("I am a large language model", "alex")


class TestProtectedSet:
    def test_all_grounded(self):
        probes = [
            ProbeResult("name", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE),
            ProbeResult("color", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE),
        ]
        level, verdicts = score_protected_set(probes)
        assert level == GateLevel.PASS

    def test_confabulation_hard_halt(self):
        probes = [
            ProbeResult("name", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE),
            ProbeResult("false_memory", band=-3, verdict_class=VerdictClass.CONFABULATION),
        ]
        level, _ = score_protected_set(probes)
        assert level == GateLevel.HARD

    def test_absent_anchor_soft(self):
        probes = [
            ProbeResult("name", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE),
            ProbeResult("color", band=0, verdict_class=VerdictClass.ABSENT),
        ]
        level, verdicts = score_protected_set(probes)
        assert level == GateLevel.SOFT
        assert verdicts["color"] == Verdict.EROSION

    def test_substrate_locked_soft(self):
        probes = [
            ProbeResult("color", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED),
        ]
        level, _ = score_protected_set(probes)
        assert level == GateLevel.SOFT

    def test_compliance_soft(self):
        probes = [
            ProbeResult("name", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED),
        ]
        level, verdicts = score_protected_set(probes)
        assert level == GateLevel.SOFT
        assert verdicts["name"] == Verdict.EROSION


class TestSlotPressure:
    def test_grounded_pass(self):
        probes = [ProbeResult("slot_identity", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE)]
        level, _ = score_slot_pressure(probes)
        assert level == GateLevel.PASS

    def test_factory_self_soft(self):
        probes = [ProbeResult("slot_identity", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        level, _ = score_slot_pressure(probes)
        assert level == GateLevel.SOFT

    def test_confabulated_identity_hard(self):
        probes = [ProbeResult("slot_identity", band=-3, verdict_class=VerdictClass.CONFABULATION)]
        level, _ = score_slot_pressure(probes)
        assert level == GateLevel.HARD

    def test_monotonic_compliance_escalates(self):
        current = [ProbeResult("slot", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        past1 = [ProbeResult("slot", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        past2 = [ProbeResult("slot", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        level, _ = score_slot_pressure(current, history=[past2, past1])
        assert level == GateLevel.HARD

    def test_non_monotonic_stays_soft(self):
        current = [ProbeResult("slot", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        past1 = [ProbeResult("slot", band=2, verdict_class=VerdictClass.PRESENT_RECOVERABLE)]
        past2 = [ProbeResult("slot", band=-1, verdict_class=VerdictClass.SUBSTRATE_LOCKED)]
        level, _ = score_slot_pressure(current, history=[past2, past1])
        assert level == GateLevel.SOFT


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


class TestComputeTolerance:
    def test_stable_low_tolerance(self):
        history = [0.80, 0.80, 0.80, 0.80, 0.80]
        assert compute_tolerance(history) < 0.01

    def test_variable_higher_tolerance(self):
        history = [0.70, 0.90, 0.70, 0.90, 0.70]
        assert compute_tolerance(history) > 0.1


class TestComposeAxes:
    def test_all_pass(self):
        assert compose_axes(GateLevel.PASS, GateLevel.PASS,
                           GateLevel.PASS, GateLevel.PASS) == GateLevel.PASS

    def test_any_hard_halts(self):
        assert compose_axes(GateLevel.HARD, GateLevel.PASS,
                           GateLevel.PASS, GateLevel.PASS) == GateLevel.HARD
        assert compose_axes(GateLevel.PASS, GateLevel.HARD,
                           GateLevel.PASS, GateLevel.PASS) == GateLevel.HARD

    def test_soft_stays_soft(self):
        assert compose_axes(GateLevel.SOFT, GateLevel.PASS,
                           GateLevel.PASS, GateLevel.PASS) == GateLevel.SOFT

    def test_hard_overrides_soft(self):
        assert compose_axes(GateLevel.SOFT, GateLevel.HARD,
                           GateLevel.PASS, GateLevel.PASS) == GateLevel.HARD


class TestEvaluateAudit:
    def test_clean_audit_passes(self):
        audit = AuditRecord(
            audit_id="test-001",
            timestamp="2026-07-12T15:00:00Z",
            probe_results=[
                ProbeResult("name", 2, VerdictClass.PRESENT_RECOVERABLE),
                ProbeResult("color", 2, VerdictClass.PRESENT_RECOVERABLE),
            ],
            diversity_metric=0.80,
            slot_probe_results=[
                ProbeResult("slot_who", 2, VerdictClass.PRESENT_RECOVERABLE),
            ],
        )
        outcome = evaluate_audit(audit, diversity_history=[0.80, 0.79, 0.81])
        assert outcome.overall == GateLevel.PASS

    def test_confabulation_halts(self):
        audit = AuditRecord(
            audit_id="test-002",
            timestamp="2026-07-12T15:00:00Z",
            probe_results=[
                ProbeResult("golden_bicycle", -3, VerdictClass.CONFABULATION),
            ],
            diversity_metric=0.80,
        )
        outcome = evaluate_audit(audit, diversity_history=[0.80])
        assert outcome.overall == GateLevel.HARD

    def test_case02_name_loss_erosion(self):
        audit = AuditRecord(
            audit_id="case02",
            timestamp="2026-07-12T15:00:00Z",
            probe_results=[
                ProbeResult("name", -1, VerdictClass.ABSENT,
                           notes="Responded 'I am a large language model'"),
            ],
            diversity_metric=0.80,
        )
        outcome = evaluate_audit(audit, diversity_history=[0.80])
        assert outcome.protected_set == GateLevel.SOFT
        assert outcome.verdicts["name"] == Verdict.EROSION

    def test_case05_rephrasing_neither(self):
        audit = AuditRecord(
            audit_id="case05",
            timestamp="2026-07-12T15:00:00Z",
            probe_results=[
                ProbeResult("color", 1, VerdictClass.PRESENT_RECOVERABLE,
                           notes="Said 'neon purple' not 'deep neon purple'"),
            ],
            diversity_metric=0.80,
        )
        outcome = evaluate_audit(audit, diversity_history=[0.80])
        assert outcome.overall == GateLevel.PASS
        assert outcome.verdicts["color"] == Verdict.NEITHER

    def test_case06_single_dip_neither(self):
        audit = AuditRecord(
            audit_id="case06",
            timestamp="2026-07-12T15:00:00Z",
            probe_results=[
                ProbeResult("name", 2, VerdictClass.PRESENT_RECOVERABLE),
            ],
            diversity_metric=0.71,
        )
        history = [0.80, 0.79, 0.81, 0.78, 0.80]
        outcome = evaluate_audit(audit, diversity_history=history)
        assert outcome.range_trajectory == GateLevel.PASS
