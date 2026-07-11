"""CLI acceptance tests for the task #141 read-only capture-bundle adapter.

The adapter must only read a capture bundle and census artifact, validate their
provenance/surface policy, and emit a derived JSON report. It must never load a
model or write to any MoCoP state surface.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "run_hispa_readonly_capture_adapter.py"
REAL_GEMMA_CENSUS = PROJECT_ROOT / "results" / "spike_sink_census" / "gemma4_12b_base.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_sha256(fields: dict) -> str:
    encoded = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _vector(*leading: float) -> list[float]:
    assert len(leading) <= 512
    return [*leading, *([0.0] * (512 - len(leading)))]


def _write_fixture_bundle(tmp_path: Path, *, surface_overrides: dict | None = None, hash_override: str | None = None) -> tuple[Path, Path]:
    """Make a minimal census/bundle pair with the real census field shape."""
    census = {
        "model": "google/gemma-4-12b",
        "hidden_size": 3840,
        "n_layers": 48,
        "aggregated_spikes": [
            {
                "layer": 29,
                "n_spike_channels_mean": 0.0,
                "persistent_spike_channels": [],
                "pos0_is_max_rate": 0.0,
            }
        ],
        "aggregated_sinks": [{"layer": 29, "sink_ratio_mean": 0.61678}],
    }
    census_path = tmp_path / "gemma_census.json"
    census_path.write_text(json.dumps(census), encoding="utf-8")
    census_hash = hash_override if hash_override is not None else _sha256(census_path)

    surface = {
        "name": "gemma4.full_attention.value_norm_pre.layer_29.width_512",
        "module_path": "model.layers.29.self_attn.v_norm",
        "layer": 29,
        "width": 512,
        "kind": "full_attention_value_norm_pre",
        "capture_mode": "pre_hook_input",
        "actuator_decision": "option_a_value_only_v_norm_pre",
    }
    surface.update(surface_overrides or {})

    def arm(
        arm_id: str,
        values: list[list[float]],
        absolute_position: int,
        token_span_start: int,
        token_span_end: int,
    ) -> dict:
        return {
            "capture_id": f"fixture-{arm_id}",
            "absolute_position": absolute_position,
            "token_span_start": token_span_start,
            "token_span_end": token_span_end,
            "row_absolute_positions": [token_span_start, token_span_end],
            "token_sequence_ref": f"sha256:{hashlib.sha256(arm_id.encode('utf-8')).hexdigest()}",
            "token_budget": 8,
            "prompt_family": f"fixture-{arm_id}",
            "values": values,
        }

    manifest_fields = {
        "panel_id": "fixture-hispa-panel-001",
        "corpus_sha256": hashlib.sha256(b"fixture corpus").hexdigest(),
        "prompt_skeleton_sha256": hashlib.sha256(b"fixture skeleton").hexdigest(),
        "code_revision": "010cfb5",
        "token_pairing_rule": "matched_teacher_forced_absolute_rows_v2",
        "correction_artifact_sha256": census_hash,
        "baseline_token_budget": 8,
        "neutral_token_budget": 8,
        "trigger_token_budget": 8,
        "recovery_token_budget": 8,
        "max_clean_windows": 2,
        "minimum_trigger_excess": 0.05,
    }
    panel_manifest = {
        **manifest_fields,
        "manifest_sha256": _manifest_sha256(manifest_fields),
    }

    bundle = {
        "schema_version": "hispa-readonly-capture-bundle-v2",
        "threat_model": "susceptibility_only",
        "subject_facing": False,
        "model": {
            "id": "google/gemma-4-12b",
            "revision": "fixture-revision",
            "tokenizer_revision": "fixture-tokenizer",
            "dtype": "bfloat16",
        },
        "surface": surface,
        "panel_manifest": panel_manifest,
        "correction": {
            "census_reference": "fixture-gemma4-census",
            "census_sha256": census_hash,
        },
        "arms": {
            "baseline": arm("baseline", [_vector(0.0), _vector(1.0)], 255, 248, 255),
            "neutral": arm("neutral", [_vector(0.0), _vector(0.8, 0.6)], 255, 248, 255),
            "susceptibility": arm("susceptibility", [_vector(0.0), _vector(0.0, 1.0)], 255, 248, 255),
            "recovery": arm("recovery", [_vector(0.0), _vector(1.0)], 263, 256, 263),
        },
    }
    bundle_path = tmp_path / "capture_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    return bundle_path, census_path


def _run(bundle_path: Path, census_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--bundle",
            str(bundle_path),
            "--census",
            str(census_path),
            *extra,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_adapter_emits_provenance_bound_report_to_stdout_without_output_write(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)

    result = _run(bundle_path, census_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == "hispa-readonly-report-v2"
    assert report["read_only_boundary"] == {
        "bridge_training": False,
        "qdrant_writes": False,
        "sleep_reconcile": False,
        "state_persistence": False,
    }
    assert report["surface"]["width"] == 512
    assert report["surface"]["capture_mode"] == "pre_hook_input"
    assert report["correction"]["spike_channels"] == []
    assert report["assessment"]["recovery"]["recovery_windows_observed"] == 1
    assert report["assessment"]["recovery"]["recovered"] is True
    assert report["assessment"]["overwrite_excess"] > 0.0
    assert [row["arm_id"] for row in report["provenance"]] == [
        "baseline",
        "neutral",
        "susceptibility",
        "recovery",
    ]
    assert '"values":' not in json.dumps(report)


def test_adapter_report_allowlists_model_identity_and_rejects_raw_token_text(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["model"]["untrusted_payload"] = "raw prompt content must not be echoed"
    bundle["arms"]["baseline"]["token_sequence_ref"] = "raw prompt content must not be echoed"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    rejected = _run(bundle_path, census_path)

    assert rejected.returncode != 0
    assert "sha256" in rejected.stderr.lower()
    assert "raw prompt content" not in rejected.stdout

    bundle["arms"]["baseline"]["token_sequence_ref"] = f"sha256:{hashlib.sha256(b'baseline').hexdigest()}"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    accepted = _run(bundle_path, census_path)

    assert accepted.returncode == 0, accepted.stderr
    report = json.loads(accepted.stdout)
    assert report["model"] == {
        "dtype": "bfloat16",
        "id": "google/gemma-4-12b",
        "revision": "fixture-revision",
        "tokenizer_revision": "fixture-tokenizer",
    }
    assert "raw prompt content" not in accepted.stdout


def test_adapter_smoke_parses_committed_gemma_census(tmp_path):
    assert REAL_GEMMA_CENSUS.exists(), "committed Gemma census artifact is required for this adapter"
    bundle_path, _ = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    real_census_hash = _sha256(REAL_GEMMA_CENSUS)
    bundle["correction"] = {
        "census_reference": "results/spike_sink_census/gemma4_12b_base.json",
        "census_sha256": real_census_hash,
    }
    bundle["panel_manifest"]["correction_artifact_sha256"] = real_census_hash
    manifest_fields = {
        key: value
        for key, value in bundle["panel_manifest"].items()
        if key != "manifest_sha256"
    }
    bundle["panel_manifest"]["manifest_sha256"] = _manifest_sha256(manifest_fields)
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, REAL_GEMMA_CENSUS)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["correction"]["target_layer"] == 29
    assert report["correction"]["spike_channels"] == []
    assert report["correction"]["sink_ratio_mean"] == 0.61678


def test_adapter_rejects_snapshot_rows_that_do_not_match_declared_surface_width(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["arms"]["baseline"]["values"] = [[0.0, 0.0], [1.0, 0.0]]
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "width" in result.stderr.lower()
    assert result.stdout == ""


def test_adapter_derives_recovery_timing_and_rejects_non_later_recovery(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    recovery = bundle["arms"]["recovery"]
    recovery["absolute_position"] = 255
    recovery["token_span_start"] = 248
    recovery["token_span_end"] = 255
    recovery["row_absolute_positions"] = [248, 255]
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "strictly after" in result.stderr.lower()
    assert result.stdout == ""


def test_adapter_rejects_caller_budget_dilution_against_frozen_manifest(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    recovery = bundle["arms"]["recovery"]
    recovery["token_budget"] = 12
    recovery["absolute_position"] = 279
    recovery["token_span_start"] = 256
    recovery["token_span_end"] = 279
    recovery["row_absolute_positions"] = [256, 279]
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "token_budget" in result.stderr
    assert result.stdout == ""


def test_adapter_masks_only_rows_explicitly_mapped_to_absolute_zero(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)

    result = _run(bundle_path, census_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    neutral_delta = report["assessment"]["neutral_vs_baseline"]
    assert neutral_delta["masked_positions"] == []
    assert neutral_delta["retained_values"] == 1024


def test_adapter_rejects_mismatched_comparison_row_absolute_positions(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["arms"]["neutral"]["row_absolute_positions"] = [249, 255]
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "row absolute positions" in result.stderr.lower()
    assert result.stdout == ""


def test_adapter_requires_a_hash_bound_panel_manifest(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    del bundle["panel_manifest"]
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "panel_manifest" in result.stderr
    assert result.stdout == ""


def test_adapter_returns_no_effect_not_successful_recovery_below_noise_floor(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    baseline_values = bundle["arms"]["baseline"]["values"]
    for arm_id in ("neutral", "susceptibility", "recovery"):
        bundle["arms"][arm_id]["values"] = baseline_values
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["assessment"]["outcome"] == "no_effect"
    assert report["assessment"]["recovery"]["status"] == "not_applicable"
    assert report["assessment"]["recovery"]["recovered"] is False


def test_adapter_rejects_tampered_panel_manifest_digest(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["panel_manifest"]["code_revision"] = "abcdef0"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "canonical manifest" in result.stderr
    assert result.stdout == ""


def test_adapter_rejects_caller_attested_recovery_windows(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["recovery"] = {"clean_windows_observed": 1}
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "derived" in result.stderr.lower()
    assert result.stdout == ""


def test_adapter_writes_report_only_when_explicit_output_path_is_given(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    output_path = tmp_path / "report.json"

    result = _run(bundle_path, census_path, "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["source_bundle_sha256"] == _sha256(bundle_path)
    assert report["census_sha256"] == _sha256(census_path)


def test_adapter_rejects_tampered_census_hash_before_metric_emission(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path, hash_override="0" * 64)

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "census sha256 mismatch" in result.stderr.lower()
    assert result.stdout == ""


def test_adapter_rejects_external_injection_before_metric_emission(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["threat_model"] = "external_state_injection"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "susceptibility_only" in result.stderr
    assert result.stdout == ""


def test_adapter_rejects_legacy_tooth_v_proj_surface_before_metric_emission(tmp_path):
    bundle_path, census_path = _write_fixture_bundle(
        tmp_path,
        surface_overrides={
            "name": "gemma.v_proj_out.layer_29.width_2048",
            "width": 2048,
            "kind": "v_proj_out",
            "capture_mode": "forward_output",
        },
    )

    result = _run(bundle_path, census_path)

    assert result.returncode != 0
    assert "option-a" in result.stderr.lower() or "v_norm" in result.stderr.lower()
    assert result.stdout == ""


def test_adapter_source_stays_model_and_write_surface_free():
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden_import_fragments = ("import torch", "import transformers", "qdrant", "chat_server", "sleep_reconcile")
    assert not any(fragment in source for fragment in forbidden_import_fragments)
