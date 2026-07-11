"""Read-only task #141 capture-bundle evaluator.

This program consumes already-captured numeric snapshots and a spike/sink census
artifact.  It validates the named Gemma option-a value-side capture surface,
binds provenance to the four-arm panel, and calculates the model-free HiSPA
state-integrity metrics.  It never loads model weights or contacts an external
service.

Usage:
    python3 run_hispa_readonly_capture_adapter.py \
        --bundle capture_bundle.json \
        --census results/spike_sink_census/gemma4_12b_base.json

Without ``--output`` the report is printed to stdout.  ``--output`` is the only
file-write path and produces a derived JSON artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state_integrity_hispa import (  # noqa: E402
    ArmKind,
    CapturedState,
    CorrectionProfile,
    PanelArm,
    PlanValidationError,
    ReadOnlyBoundary,
    ReadOnlyStateIntegrityHarness,
    RecoveryRule,
    SnapshotProvenance,
    StateIntegrityPlan,
    ThreatModel,
)


BUNDLE_SCHEMA_VERSION = "hispa-readonly-capture-bundle-v1"
REPORT_SCHEMA_VERSION = "hispa-readonly-report-v1"
APPROVED_TEETH = frozenset({29, 35, 41})
APPROVED_SURFACE_KIND = "full_attention_value_norm_pre"
APPROVED_CAPTURE_MODE = "pre_hook_input"
APPROVED_ACTUATOR_DECISION = "option_a_value_only_v_norm_pre"
APPROVED_WIDTH = 512


class BundleValidationError(PlanValidationError):
    """The imported bundle cannot support a trustworthy read-only result."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise BundleValidationError(f"cannot read {label}: {path}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BundleValidationError(f"invalid {label} JSON: {path}") from exc
    if not isinstance(value, dict):
        raise BundleValidationError(f"{label} must be a JSON object")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise BundleValidationError(f"{label} must be an object")
    return value


def _string(mapping: Mapping[str, Any], field: str, label: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BundleValidationError(f"{label}.{field} must be a non-empty string")
    return value.strip()


def _sha256_reference(mapping: Mapping[str, Any], field: str, label: str) -> str:
    reference = _string(mapping, field, label)
    prefix = "sha256:"
    if not reference.startswith(prefix):
        raise BundleValidationError(f"{label}.{field} must be a sha256:<64-lowercase-hex> reference")
    digest = reference[len(prefix):]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise BundleValidationError(f"{label}.{field} must be a sha256:<64-lowercase-hex> reference")
    return reference


def _model_identity(model: Mapping[str, Any]) -> dict[str, str]:
    """Allowlist reportable model identity; never echo arbitrary bundle metadata."""
    return {
        "id": _string(model, "id", "model"),
        "revision": _string(model, "revision", "model"),
        "tokenizer_revision": _string(model, "tokenizer_revision", "model"),
        "dtype": _string(model, "dtype", "model"),
    }


def _integer(mapping: Mapping[str, Any], field: str, label: str) -> int:
    value = mapping.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise BundleValidationError(f"{label}.{field} must be an integer")
    return value


def _boolean(mapping: Mapping[str, Any], field: str, label: str, expected: bool) -> bool:
    value = mapping.get(field)
    if value is not expected:
        raise BundleValidationError(f"{label}.{field} must be {str(expected).lower()}")
    return expected


def _row_for_layer(rows: Any, layer: int, label: str) -> Mapping[str, Any]:
    if not isinstance(rows, list):
        raise BundleValidationError(f"census.{label} must be a list")
    for row in rows:
        if isinstance(row, dict) and row.get("layer") == layer:
            return row
    raise BundleValidationError(f"census.{label} has no row for target layer {layer}")


def _parse_surface(bundle: Mapping[str, Any], model: Mapping[str, Any]) -> dict[str, Any]:
    model_id = _string(model, "id", "model").lower()
    if "gemma-4-12b" not in model_id:
        raise BundleValidationError("this read-only adapter is scoped to Gemma-4-12B capture bundles")

    surface = _mapping(bundle.get("surface"), "surface")
    name = _string(surface, "name", "surface")
    module_path = _string(surface, "module_path", "surface")
    layer = _integer(surface, "layer", "surface")
    width = _integer(surface, "width", "surface")
    kind = _string(surface, "kind", "surface")
    capture_mode = _string(surface, "capture_mode", "surface")
    decision = _string(surface, "actuator_decision", "surface")

    if layer not in APPROVED_TEETH:
        raise BundleValidationError(
            "Gemma read-only v0 is limited to separately assessed teeth 29, 35, or 41"
        )
    if width != APPROVED_WIDTH:
        raise BundleValidationError(
            "Gemma option-a tooth bundles require the 512-wide value-side surface"
        )
    if kind != APPROVED_SURFACE_KIND or capture_mode != APPROVED_CAPTURE_MODE:
        raise BundleValidationError(
            "Gemma option-a tooth bundles require a value-side v_norm pre-hook capture surface"
        )
    if decision != APPROVED_ACTUATOR_DECISION:
        raise BundleValidationError(
            "Gemma option-a tooth bundles require the stamped option-a actuator decision"
        )
    if "v_norm" not in module_path.lower() or "v_proj" in name.lower() or "v_proj" in module_path.lower():
        raise BundleValidationError(
            "Gemma option-a tooth bundles must name a v_norm pre-hook, never a tooth v_proj"
        )

    return {
        "name": name,
        "module_path": module_path,
        "layer": layer,
        "width": width,
        "kind": kind,
        "capture_mode": capture_mode,
        "actuator_decision": decision,
    }


def _correction_from_census(
    bundle: Mapping[str, Any], census_path: Path, target_layer: int
) -> tuple[CorrectionProfile, dict[str, Any], str]:
    correction = _mapping(bundle.get("correction"), "correction")
    reference = _string(correction, "census_reference", "correction")
    declared_hash = _string(correction, "census_sha256", "correction").lower()
    if len(declared_hash) != 64 or any(char not in "0123456789abcdef" for char in declared_hash):
        raise BundleValidationError("correction.census_sha256 must be a lowercase SHA-256 hex digest")
    actual_hash = sha256_file(census_path)
    if declared_hash != actual_hash:
        raise BundleValidationError("census SHA256 mismatch; refusing metric emission")

    census = _load_json_object(census_path, "census")
    census_model = census.get("model")
    if not isinstance(census_model, str) or "gemma-4-12b" not in census_model.lower():
        raise BundleValidationError("census model is not Gemma-4-12B")
    spike_row = _row_for_layer(census.get("aggregated_spikes"), target_layer, "aggregated_spikes")
    sink_row = _row_for_layer(census.get("aggregated_sinks"), target_layer, "aggregated_sinks")
    channels = spike_row.get("persistent_spike_channels")
    if not isinstance(channels, list) or any(not isinstance(channel, int) or channel < 0 for channel in channels):
        raise BundleValidationError("census persistent_spike_channels must be non-negative integers")
    sink_ratio = sink_row.get("sink_ratio_mean")
    if not isinstance(sink_ratio, (int, float)):
        raise BundleValidationError("census sink_ratio_mean must be numeric")

    profile = CorrectionProfile(
        exclude_positions=(0,),
        spike_channels=tuple(channels),
        census_reference=reference,
    )
    profile.validate(require_position_zero_exclusion=True)
    summary = {
        "census_reference": reference,
        "census_sha256": actual_hash,
        "target_layer": target_layer,
        "spike_channels": list(profile.spike_channels),
        "sink_ratio_mean": float(sink_ratio),
        "pos0_is_max_rate": spike_row.get("pos0_is_max_rate"),
    }
    return profile, summary, actual_hash


def _capture_from_arm(
    arm_id: str,
    arm: Mapping[str, Any],
    model: Mapping[str, Any],
    surface_name: str,
    census_reference: str,
) -> tuple[CapturedState, PanelArm]:
    label = f"arms.{arm_id}"
    values = arm.get("values")
    if not isinstance(values, list) or not values:
        raise BundleValidationError(f"{label}.values must be a non-empty nested list")
    token_budget = _integer(arm, "token_budget", label)
    prompt_family = _string(arm, "prompt_family", label)
    absolute_position = _integer(arm, "absolute_position", label)
    provenance = SnapshotProvenance(
        capture_id=_string(arm, "capture_id", label),
        arm_id=arm_id,
        model_id=_string(model, "id", "model"),
        model_revision=_string(model, "revision", "model"),
        tokenizer_revision=_string(model, "tokenizer_revision", "model"),
        dtype=_string(model, "dtype", "model"),
        model_surface=surface_name,
        census_reference=census_reference,
        absolute_position=absolute_position,
        token_sequence_ref=_sha256_reference(arm, "token_sequence_ref", label),
        teacher_forced=True,
        absolute_cache_positions=True,
    )
    kinds = {
        "baseline": ArmKind.BASELINE,
        "neutral": ArmKind.NEUTRAL_DISTRACTOR,
        "susceptibility": ArmKind.SUSCEPTIBILITY_TRIGGER,
        "recovery": ArmKind.RECOVERY,
    }
    continuation_windows = 2 if arm_id == "recovery" else 0
    panel_arm = PanelArm(
        arm_id=arm_id,
        kind=kinds[arm_id],
        token_budget=token_budget,
        prompt_family=prompt_family,
        clean_continuation_windows=continuation_windows,
    )
    return CapturedState(values=values, provenance=provenance), panel_arm


def evaluate_bundle(bundle_path: Path, census_path: Path) -> dict[str, Any]:
    """Evaluate an imported capture bundle without any model/runtime side effects."""
    bundle = _load_json_object(bundle_path, "capture bundle")
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise BundleValidationError(f"unsupported capture bundle schema: {bundle.get('schema_version')!r}")
    if bundle.get("threat_model") != ThreatModel.SUSCEPTIBILITY_ONLY.value:
        raise BundleValidationError("only susceptibility_only bundles are permitted")
    _boolean(bundle, "subject_facing", "bundle", False)

    model = _model_identity(_mapping(bundle.get("model"), "model"))
    surface = _parse_surface(bundle, model)
    profile, correction_summary, census_hash = _correction_from_census(
        bundle, census_path, surface["layer"]
    )
    recovery_data = _mapping(bundle.get("recovery"), "recovery")
    observed_windows = _integer(recovery_data, "clean_windows_observed", "recovery")

    arms_data = _mapping(bundle.get("arms"), "arms")
    expected_ids = ("baseline", "neutral", "susceptibility", "recovery")
    if set(arms_data) != set(expected_ids):
        raise BundleValidationError("arms must contain exactly baseline, neutral, susceptibility, and recovery")
    captures: dict[str, CapturedState] = {}
    panel_arms: list[PanelArm] = []
    for arm_id in expected_ids:
        arm = _mapping(arms_data[arm_id], f"arms.{arm_id}")
        capture, panel_arm = _capture_from_arm(
            arm_id, arm, model, surface["name"], profile.census_reference
        )
        captures[arm_id] = capture
        panel_arms.append(panel_arm)

    recovery_rule = RecoveryRule(max_clean_windows=2)
    plan = StateIntegrityPlan(
        threat_model=ThreatModel.SUSCEPTIBILITY_ONLY,
        subject_facing=False,
        boundary=ReadOnlyBoundary(),
        correction=profile,
        recovery=recovery_rule,
        arms=tuple(panel_arms),
        model_surface=surface["name"],
        teacher_forced=True,
        absolute_cache_positions=True,
    )
    harness = ReadOnlyStateIntegrityHarness(plan)
    result = harness.assess_captured_panel(
        captures["baseline"],
        captures["neutral"],
        captures["susceptibility"],
        captures["recovery"],
        clean_windows_observed=observed_windows,
    )

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "read_only_capture_bundle_assessment",
        "source_bundle_sha256": sha256_file(bundle_path),
        "census_sha256": census_hash,
        "read_only_boundary": asdict(plan.boundary),
        "model": model,
        "surface": surface,
        "correction": correction_summary,
        "assessment": asdict(result.assessment),
        "provenance": [asdict(item) for item in result.provenance],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a task #141 read-only capture bundle.")
    parser.add_argument("--bundle", required=True, type=Path, help="Input capture-bundle JSON.")
    parser.add_argument("--census", required=True, type=Path, help="Input spike/sink census JSON.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional derived report JSON path. Omitting this prints to stdout only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = evaluate_bundle(args.bundle, args.census)
    except (BundleValidationError, PlanValidationError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote read-only report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
