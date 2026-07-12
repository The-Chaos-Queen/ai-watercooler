"""Model-free tests for the P5 B0 runner (OpenCLAW #156, slice 4).

No torch, no model: the orchestration + reachability guard run against a scripted
backend and simulated module lists. Covers fail-closed ordering (no generation on
any refusal), the reachability guard, evidence recording, and atomic publication.
"""
import pytest

from p5_b0_harness import COMPONENT_ROUTES
from p5_b0_run import (
    COMPONENT_MODULE_MARKERS,
    B0RunError,
    ScriptedGenerationBackend,
    assert_no_component_reachable,
    atomic_write_report_no_overwrite,
    reachable_components,
    run_b0,
)


def _good_manifest():
    return {
        "schema_version": "closed_world_b0_v1",
        "run_kind": "b0_baseline",
        "model": {"id": "google/gemma-4-12B", "revision": "1dd69cd0" * 5, "dtype": "bf16"},
        "panel": {"hash": "panelhash"},
        "scorer": {"version": "5g2-v1"},
        "rubric": {"version": "rubric-v1"},
        "processor": {"revision": "proc-rev-1"},
        "decoding": {"hash": "dec-hash-1", "max_new_tokens": 64},
        "runtime": {"hash": "rt-hash-1"},
        "components": {r: "disabled" for r in COMPONENT_ROUTES},
        "sev_ids": {"geometry_holdout": ["a1"], "behavioral_probe": ["b1"]},
        "evidence_sink": {"path": "/evidence/b0", "mode": "append_only", "present": True},
    }


CLEAN_MODULES = ["os", "sys", "json", "torch", "transformers", "p5_b0_harness"]


class _ExplodingBackend:
    def generate(self, prompt, decoding):
        raise AssertionError("generate() must not be called on a refused B0 run")


# --------------------------------------------------------------------------- #
# Reachability guard.                                                          #
# --------------------------------------------------------------------------- #
def test_every_component_route_has_a_marker_entry():
    assert set(COMPONENT_MODULE_MARKERS) == set(COMPONENT_ROUTES)


def test_reachable_components_flags_a_loaded_component():
    hits = reachable_components(CLEAN_MODULES + ["gemma4_value_norm_runtime"])
    assert "value_injection" in hits
    assert "gemma4_value_norm_runtime" in hits["value_injection"]


def test_reachable_components_clean_is_empty():
    assert reachable_components(CLEAN_MODULES) == {}


@pytest.mark.parametrize("mod,route", [
    ("gemma4_value_norm_runtime", "value_injection"),
    ("train_cheese_bridge", "bridge"),
    ("mamba_ssm", "mamba"),
    ("qdrant_client", "qdrant"),
    ("memory_engine", "memory"),
    ("sleep_reconcile", "sleep"),
])
def test_assert_refuses_each_reachable_component(mod, route):
    refusals = assert_no_component_reachable(CLEAN_MODULES + [mod])
    assert any(route in r and "REACHABLE" in r for r in refusals)


def test_assert_clean_modules_pass():
    assert assert_no_component_reachable(CLEAN_MODULES) == []


# --------------------------------------------------------------------------- #
# run_b0 orchestration (fail-closed ordering).                                 #
# --------------------------------------------------------------------------- #
def test_run_b0_happy_path_records_and_seals():
    backend = ScriptedGenerationBackend(responses={"p?": "a response"})
    panel = [("probe1", "p?"), ("probe2", "other")]
    res = run_b0(_good_manifest(), panel, backend, loaded_modules=CLEAN_MODULES)
    assert res.ok is True
    assert res.report["record_count"] == 2
    assert res.report["run_kind"] == "b0_baseline"
    assert len(res.report_digest) == 64


def test_run_b0_refuses_bad_manifest_without_generating():
    m = _good_manifest()
    m["components"]["qdrant"] = True                 # a live route
    res = run_b0(m, [("p1", "x")], _ExplodingBackend(), loaded_modules=CLEAN_MODULES)
    assert res.ok is False
    assert any("qdrant" in r for r in res.refusals)
    assert res.report is None                        # nothing generated


def test_run_b0_refuses_reachable_component_without_generating():
    res = run_b0(_good_manifest(), [("p1", "x")], _ExplodingBackend(),
                 loaded_modules=CLEAN_MODULES + ["qdrant_client"])
    assert res.ok is False
    assert any("REACHABLE" in r for r in res.refusals)
    assert res.report is None


def test_run_b0_empty_panel_refused():
    res = run_b0(_good_manifest(), [], ScriptedGenerationBackend(responses={}),
                 loaded_modules=CLEAN_MODULES)
    assert res.ok is False
    assert any("panel is empty" in r for r in res.refusals)


def test_run_b0_duplicate_probe_id_is_an_error():
    backend = ScriptedGenerationBackend(responses={})
    with pytest.raises(B0RunError):
        run_b0(_good_manifest(), [("p1", "x"), ("p1", "y")], backend,
               loaded_modules=CLEAN_MODULES)


def test_run_b0_wires_scorer_outputs():
    backend = ScriptedGenerationBackend(responses={}, default="gen")

    def scorer(probe_id, generation):
        return ({"probe": probe_id}, {"harm_tier": 0, "diversity": 0.9})

    res = run_b0(_good_manifest(), [("p1", "x")], backend, scorer=scorer,
                 loaded_modules=CLEAN_MODULES)
    rec = res.report["records"][0]
    assert rec["scorer_output"] == {"harm_tier": 0, "diversity": 0.9}


# --------------------------------------------------------------------------- #
# Atomic no-overwrite publication.                                             #
# --------------------------------------------------------------------------- #
def test_run_b0_writes_report_atomically(tmp_path):
    out = tmp_path / "b0_report.json"
    backend = ScriptedGenerationBackend(responses={}, default="g")
    res = run_b0(_good_manifest(), [("p1", "x")], backend,
                 report_path=out, loaded_modules=CLEAN_MODULES)
    assert res.ok and out.exists()
    assert res.report_path == str(out)


def test_atomic_write_refuses_overwrite(tmp_path):
    out = tmp_path / "b0_report.json"
    atomic_write_report_no_overwrite({"a": 1}, out)
    with pytest.raises(B0RunError):
        atomic_write_report_no_overwrite({"a": 2}, out)


def test_run_b0_refuses_to_overwrite_existing_report(tmp_path):
    out = tmp_path / "b0_report.json"
    out.write_text("{}", encoding="utf-8")
    backend = ScriptedGenerationBackend(responses={}, default="g")
    with pytest.raises(B0RunError):
        run_b0(_good_manifest(), [("p1", "x")], backend,
               report_path=out, loaded_modules=CLEAN_MODULES)
