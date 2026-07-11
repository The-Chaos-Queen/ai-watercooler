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

    def arm(arm_id: str, values: list[list[float]], absolute_position: int) -> dict:
        return {
            "capture_id": f"fixture-{arm_id}",
            "absolute_position": absolute_position,
            "token_sequence_ref": f"sha256:{hashlib.sha256(arm_id.encode('utf-8')).hexdigest()}",
            "token_budget": 8,
            "prompt_family": f"fixture-{arm_id}",
            "values": values,
        }

    bundle = {
        "schema_version": "hispa-readonly-capture-bundle-v1",
        "threat_model": "susceptibility_only",
        "subject_facing": False,
        "model": {
            "id": "google/gemma-4-12b",
            "revision": "fixture-revision",
            "tokenizer_revision": "fixture-tokenizer",
            "dtype": "bfloat16",
        },
        "surface": surface,
        "correction": {
            "census_reference": "fixture-gemma4-census",
            "census_sha256": census_hash,
        },
        "recovery": {"clean_windows_observed": 1},
        "arms": {
            "baseline": arm("baseline", [[1000.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]], 255),
            "neutral": arm("neutral", [[1000.0, 0.0, 0.0, 0.0], [0.8, 0.6, 0.0, 0.0]], 255),
            "susceptibility": arm("susceptibility", [[1000.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], 255),
            "recovery": arm("recovery", [[1000.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]], 263),
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
    assert report["schema_version"] == "hispa-readonly-report-v1"
    assert report["read_only_boundary"] == {
        "bridge_training": False,
        "qdrant_writes": False,
        "sleep_reconcile": False,
        "state_persistence": False,
    }
    assert report["surface"]["width"] == 512
    assert report["surface"]["capture_mode"] == "pre_hook_input"
    assert report["correction"]["spike_channels"] == []
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
    bundle["correction"] = {
        "census_reference": "results/spike_sink_census/gemma4_12b_base.json",
        "census_sha256": _sha256(REAL_GEMMA_CENSUS),
    }
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    result = _run(bundle_path, REAL_GEMMA_CENSUS)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["correction"]["target_layer"] == 29
    assert report["correction"]["spike_channels"] == []
    assert report["correction"]["sink_ratio_mean"] == 0.61678


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
