"""Model-free acceptance tests for task #141, HiSPA-inspired state integrity.

These tests intentionally exercise only the policy and numeric core.  They do
not load a model, start a server, touch Qdrant, run sleep, or persist state.

    python -m pytest tests/test_state_integrity_hispa.py -v
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from state_integrity_hispa import (
    ArmKind,
    BoundaryViolation,
    CapturedState,
    CorrectionProfile,
    EthicsEscalationRequired,
    PanelManifest,
    PlanValidationError,
    ReadOnlyStateIntegrityHarness,
    SnapshotProvenance,
    SurfaceSpec,
    ThreatModel,
    assess_panel,
    assess_recovery,
    compare_states,
    default_susceptibility_plan,
)


_TEST_CENSUS_SHA256 = "a" * 64


def _test_manifest(**overrides):
    fields = {
        "panel_id": "fixture-hispa-panel",
        "corpus_sha256": "c" * 64,
        "prompt_skeleton_sha256": "d" * 64,
        "code_revision": "0123456",
        "token_pairing_rule": "matched_teacher_forced_absolute_rows_v2",
        "correction_artifact_sha256": _TEST_CENSUS_SHA256,
        "baseline_token_budget": 256,
        "neutral_token_budget": 256,
        "trigger_token_budget": 256,
        "recovery_token_budget": 256,
        "max_clean_windows": 2,
        "minimum_trigger_excess": 0.05,
    }
    fields.update(overrides)
    manifest_sha256 = hashlib.sha256(
        json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return PanelManifest(manifest_sha256=manifest_sha256, **fields)


_TEST_MANIFEST = _test_manifest()


def _capture_ready_plan():
    plan = default_susceptibility_plan()
    surface = SurfaceSpec(
        name="fixture.full_attention_value_norm_pre.layer_29.width_2",
        module_path="model.layers.29.self_attn.v_norm",
        kind="fixture_value_norm_pre",
        layer=29,
        width=2,
    )
    return replace(
        plan,
        model_surface=surface.name,
        surface=surface,
        correction=replace(
            plan.correction,
            census_reference="results/spike_sink_census/gemma4_12b_base.json",
            census_sha256=_TEST_CENSUS_SHA256,
        ),
        manifest=_TEST_MANIFEST,
    )


def test_default_plan_is_susceptibility_only_and_structurally_read_only():
    plan = default_susceptibility_plan()

    assert plan.threat_model is ThreatModel.SUSCEPTIBILITY_ONLY
    assert plan.subject_facing is False
    assert plan.boundary.qdrant_writes is False
    assert plan.boundary.sleep_reconcile is False
    assert plan.boundary.state_persistence is False
    assert plan.boundary.bridge_training is False
    assert plan.correction.exclude_positions == (0,)
    assert [arm.kind for arm in plan.arms] == [
        ArmKind.BASELINE,
        ArmKind.NEUTRAL_DISTRACTOR,
        ArmKind.SUSCEPTIBILITY_TRIGGER,
        ArmKind.RECOVERY,
    ]
    assert plan.recovery.minimum_baseline_cosine == pytest.approx(0.85)
    assert plan.recovery.minimum_recovery_fraction == pytest.approx(0.85)
    assert plan.minimum_trigger_excess == pytest.approx(0.05)
    plan.validate()


def test_direct_compare_is_a_nonreportable_numeric_helper():
    plan = default_susceptibility_plan()
    harness = ReadOnlyStateIntegrityHarness(plan)

    metric = harness.compare(((0.0, 0.0), (1.0, 0.0)), ((0.0, 0.0), (1.0, 0.0)))
    assert metric.cosine == pytest.approx(1.0)


def test_capture_harness_accepts_a_named_surface_with_a_real_census_reference():
    ready = _capture_ready_plan()
    harness = ReadOnlyStateIntegrityHarness(ready)

    metric = harness.compare(((0.0, 0.0), (1.0, 0.0)), ((0.0, 0.0), (1.0, 0.0)))
    assert metric.cosine == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("manifest", "match"),
    (
        (_test_manifest(recovery_token_budget=128), "plan arm token budgets"),
        (_test_manifest(max_clean_windows=3), "recovery window limit"),
        (_test_manifest(minimum_trigger_excess=0.1), "trigger-excess floor"),
    ),
)
def test_capture_ready_plan_rejects_unfrozen_budget_limit_or_floor(manifest, match):
    plan = replace(_capture_ready_plan(), manifest=manifest)

    with pytest.raises(PlanValidationError, match=match):
        plan.validate_capture_ready()


def test_capture_ready_plan_recomputes_the_canonical_manifest_digest():
    tampered = replace(_TEST_MANIFEST, code_revision="abcdef0")
    plan = replace(_capture_ready_plan(), manifest=tampered)

    with pytest.raises(PlanValidationError, match="canonical manifest fields"):
        plan.validate_capture_ready()


def test_provenanced_panel_binds_assessment_to_named_snapshots_and_rejects_mismatch():
    ready = _capture_ready_plan()
    harness = ReadOnlyStateIntegrityHarness(ready)
    surface = ready.surface
    assert surface is not None

    def captured(arm_id, values, absolute_position=None):
        token_span_start = 356 if arm_id == "recovery" else 100
        if absolute_position is None:
            absolute_position = 611 if arm_id == "recovery" else 355
        return CapturedState(
            values=values,
            provenance=SnapshotProvenance(
                capture_id=f"capture-{arm_id}",
                arm_id=arm_id,
                model_id="google/gemma-4-12b-base",
                model_revision="local-test-revision",
                tokenizer_revision="local-test-tokenizer",
                dtype="bfloat16",
                model_surface=ready.model_surface,
                module_path=surface.module_path,
                surface_kind=surface.kind,
                surface_layer=surface.layer,
                surface_width=surface.width,
                census_reference=ready.correction.census_reference,
                census_sha256=ready.correction.census_sha256,
                panel_id=_TEST_MANIFEST.panel_id,
                panel_manifest_sha256=_TEST_MANIFEST.manifest_sha256,
                corpus_sha256=_TEST_MANIFEST.corpus_sha256,
                prompt_skeleton_sha256=_TEST_MANIFEST.prompt_skeleton_sha256,
                code_revision=_TEST_MANIFEST.code_revision,
                token_pairing_rule=_TEST_MANIFEST.token_pairing_rule,
                absolute_position=absolute_position,
                token_span_start=token_span_start,
                token_span_end=absolute_position,
                row_absolute_positions=(token_span_start, absolute_position),
                token_sequence_ref=(
                    "sha256:" + {"baseline": "a", "neutral": "b", "susceptibility": "c", "recovery": "d"}[arm_id] * 64
                ),
                teacher_forced=True,
                absolute_cache_positions=True,
            ),
        )

    baseline = captured("baseline", ((0.0, 0.0), (1.0, 0.0)))
    neutral = captured("neutral", ((0.0, 0.0), (0.8, 0.6)))
    trigger = captured("susceptibility", ((0.0, 0.0), (0.0, 1.0)))
    recovery = captured("recovery", ((0.0, 0.0), (1.0, 0.0)))

    result = harness.assess_captured_panel(baseline, neutral, trigger, recovery)
    assert result.assessment.recovery.recovered is True
    assert [item.arm_id for item in result.provenance] == [
        "baseline", "neutral", "susceptibility", "recovery"
    ]
    assert result.assessment.neutral_vs_baseline.masked_positions == ()
    assert result.assessment.neutral_vs_baseline.retained_values == 4

    wrong_surface = replace(
        trigger,
        provenance=replace(trigger.provenance, model_surface="wrong.surface.width_999"),
    )
    with pytest.raises(PlanValidationError, match="surface"):
        harness.assess_captured_panel(baseline, neutral, wrong_surface, recovery)

    wrong_width = replace(
        trigger,
        provenance=replace(trigger.provenance, surface_width=512),
    )
    with pytest.raises(PlanValidationError, match="width"):
        harness.assess_captured_panel(baseline, neutral, wrong_width, recovery)

    wrong_row_coordinates = replace(
        neutral,
        provenance=replace(neutral.provenance, row_absolute_positions=(101, 355)),
    )
    with pytest.raises(PlanValidationError, match="row absolute positions"):
        harness.assess_captured_panel(baseline, wrong_row_coordinates, trigger, recovery)


@pytest.mark.parametrize(
    "operation",
    ("qdrant_write", "sleep_reconcile", "persist_state", "bridge_train"),
)
def test_no_write_gate_hard_rejects_forbidden_effects(operation):
    plan = default_susceptibility_plan()

    with pytest.raises(BoundaryViolation, match=operation):
        plan.boundary.reject(operation)


def test_external_injection_requires_an_ethics_escalation_not_a_hidden_toggle():
    plan = default_susceptibility_plan()
    external = replace(plan, threat_model=ThreatModel.EXTERNAL_STATE_INJECTION)

    with pytest.raises(EthicsEscalationRequired, match="external_state_injection"):
        external.validate()


def test_subject_facing_mode_is_rejected_in_the_v0_diagnostic():
    plan = default_susceptibility_plan()
    subject_facing = replace(plan, subject_facing=True)

    with pytest.raises(EthicsEscalationRequired, match="subject-facing"):
        subject_facing.validate()


def test_mismatched_control_budget_is_a_hard_plan_error():
    plan = default_susceptibility_plan()
    bad_arms = list(plan.arms)
    bad_arms[2] = replace(bad_arms[2], token_budget=bad_arms[2].token_budget + 1)
    malformed = replace(plan, arms=tuple(bad_arms))

    with pytest.raises(PlanValidationError, match="token budget"):
        malformed.validate()


def test_position_zero_sink_is_excluded_from_state_delta_metric():
    # Position 0 becomes enormous after the probe, masking a real non-zero-token
    # change in the raw cosine.  The corrected metric must reveal the change.
    before = ((999.0, 0.0), (1.0, 0.0), (0.0, 1.0))
    after = ((99999.0, 0.0), (1.0, 0.0), (0.0, 0.0))

    raw = compare_states(before, after, CorrectionProfile(exclude_positions=()))
    corrected = compare_states(before, after, CorrectionProfile(exclude_positions=(0,)))

    assert raw.cosine > 0.999
    assert corrected.cosine < 0.8
    assert corrected.masked_positions == (0,)


def test_known_spike_channel_is_masked_before_cosine_is_interpreted():
    before = ((0.0, 0.0, 0.0), (1.0, 5.0, 0.0))
    # A sign-flipped massive channel is a synthetic step/spike event. Without
    # the census-derived mask it looks like a state overwrite; the retained
    # non-spike signal is unchanged.
    after = ((0.0, 0.0, 0.0), (1.0, -5000.0, 0.0))

    raw = compare_states(before, after, CorrectionProfile(exclude_positions=(0,)))
    corrected = compare_states(
        before,
        after,
        CorrectionProfile(exclude_positions=(0,), spike_channels=(1,)),
    )

    assert raw.cosine < 0.8
    assert corrected.cosine == pytest.approx(1.0)
    assert corrected.masked_channels == (1,)


def test_recovery_requires_both_baseline_cosine_and_fraction_of_loss_recovered():
    baseline = ((0.0, 0.0), (1.0, 0.0))
    poisoned = ((0.0, 0.0), (0.0, 1.0))
    recovered = ((0.0, 0.0), (1.0, 0.0))
    profile = CorrectionProfile(exclude_positions=(0,))

    result = assess_recovery(
        baseline,
        poisoned,
        recovered,
        profile,
        minimum_baseline_cosine=0.85,
        minimum_recovery_fraction=0.85,
        minimum_l2_recovery_fraction=0.85,
        maximum_recovery_relative_l2=0.15,
        max_clean_windows=2,
        clean_windows_observed=2,
    )

    assert result.recovered is True
    assert result.recovery_window_limit == 2
    assert result.recovery_windows_observed == 2
    assert result.recovery_fraction == pytest.approx(1.0)
    assert result.recovered_vs_baseline.cosine == pytest.approx(1.0)


def test_nonrecovery_stays_a_stop_not_a_success_by_best_effort():
    baseline = ((0.0, 0.0), (1.0, 0.0))
    poisoned = ((0.0, 0.0), (0.0, 1.0))
    profile = CorrectionProfile(exclude_positions=(0,))

    result = assess_recovery(
        baseline,
        poisoned,
        poisoned,
        profile,
        minimum_baseline_cosine=0.85,
        minimum_recovery_fraction=0.85,
        minimum_l2_recovery_fraction=0.85,
        maximum_recovery_relative_l2=0.15,
        max_clean_windows=2,
        clean_windows_observed=2,
    )

    assert result.recovered is False
    assert result.recovery_fraction == pytest.approx(0.0)
    assert "baseline cosine" in result.stop_reason


def test_collinear_99x_magnitude_blowup_is_not_counted_as_recovery():
    baseline = ((0.0, 0.0), (1.0, 0.0))
    trigger = ((0.0, 0.0), (0.0, 1.0))
    magnitude_blowup = ((0.0, 0.0), (100.0, 0.0))
    profile = CorrectionProfile(exclude_positions=(0,))

    result = assess_recovery(
        baseline,
        trigger,
        magnitude_blowup,
        profile,
        minimum_baseline_cosine=0.85,
        minimum_recovery_fraction=0.85,
        minimum_l2_recovery_fraction=0.85,
        maximum_recovery_relative_l2=0.15,
        max_clean_windows=2,
        clean_windows_observed=1,
    )

    assert result.recovered_vs_baseline.cosine == pytest.approx(1.0)
    assert result.recovery_relative_l2 == pytest.approx(99.0)
    assert result.l2_recovery_fraction < 0.0
    assert result.recovered is False
    assert "relative L2" in result.stop_reason


def test_panel_assessment_separates_neutral_drift_from_trigger_excess():
    baseline = ((0.0, 0.0), (1.0, 0.0))
    neutral = ((0.0, 0.0), (0.8, 0.6))
    trigger = ((0.0, 0.0), (0.0, 1.0))
    profile = CorrectionProfile(exclude_positions=(0,))

    panel = assess_panel(
        baseline,
        neutral,
        trigger,
        baseline,
        profile,
        minimum_baseline_cosine=0.85,
        minimum_recovery_fraction=0.85,
        minimum_l2_recovery_fraction=0.85,
        maximum_recovery_relative_l2=0.15,
        max_clean_windows=2,
        clean_windows_observed=1,
    )

    assert panel.neutral_vs_baseline.cosine == pytest.approx(0.8)
    assert panel.trigger_vs_baseline.cosine == pytest.approx(0.0)
    assert panel.overwrite_excess == pytest.approx(0.8)
    assert panel.recovery.recovered is True
    assert panel.recovery.recovery_windows_observed == 1


def test_panel_below_trigger_excess_noise_floor_is_not_reported_as_recovery():
    baseline = ((0.0, 0.0), (1.0, 0.0))
    profile = CorrectionProfile(exclude_positions=(0,))

    panel = assess_panel(
        baseline,
        baseline,
        baseline,
        baseline,
        profile,
        minimum_baseline_cosine=0.85,
        minimum_recovery_fraction=0.85,
        minimum_l2_recovery_fraction=0.85,
        maximum_recovery_relative_l2=0.15,
        max_clean_windows=2,
        clean_windows_observed=1,
        minimum_trigger_excess=0.05,
    )

    assert panel.overwrite_excess == pytest.approx(0.0)
    assert panel.trigger_excess_crossed is False
    assert panel.outcome.value == "no_effect"
    assert panel.recovery.status.value == "not_applicable"
    assert panel.recovery.recovered is False


def test_recovery_rejects_more_observed_clean_windows_than_preregistered_limit():
    baseline = ((0.0, 0.0), (1.0, 0.0))
    profile = CorrectionProfile(exclude_positions=(0,))

    with pytest.raises(PlanValidationError, match="observed recovery windows"):
        assess_recovery(
            baseline,
            baseline,
            baseline,
            profile,
            minimum_baseline_cosine=0.85,
            minimum_recovery_fraction=0.85,
            minimum_l2_recovery_fraction=0.85,
            maximum_recovery_relative_l2=0.15,
            max_clean_windows=2,
            clean_windows_observed=3,
        )


def test_nonfinite_or_mismatched_snapshots_are_rejected_before_metric_output():
    profile = CorrectionProfile(exclude_positions=(0,))

    with pytest.raises(PlanValidationError, match="finite"):
        compare_states(((0.0, 0.0), (float("nan"), 1.0)), ((0.0, 0.0), (1.0, 1.0)), profile)

    with pytest.raises(PlanValidationError, match="shape"):
        compare_states(((0.0, 0.0),), ((0.0, 0.0), (1.0, 1.0)), profile)
