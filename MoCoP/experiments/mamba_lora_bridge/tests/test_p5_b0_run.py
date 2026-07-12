"""Model-free tests for the hardened P5 B0 runner (OpenCLAW #156, slice 4).

Covers the a-Codex hardening: unconditional live-module reachability, complete marker
inventory, execution bound to the manifest, reserved evidence sink, attempt journaling,
correct published digest, O_EXCL publication, and whole-panel pre-validation.
"""
import json

import pytest

from p5_b0_harness import COMPONENT_ROUTES, canonical_digest
from p5_b0_run import (
    COMPONENT_MODULE_MARKERS,
    B0RunError,
    ScriptedGenerationBackend,
    assert_no_component_reachable,
    canonical_panel_hash,
    reachable_components,
    reserve_report_slot,
    run_b0,
)

MODEL = {"id": "google/gemma-4-12B", "revision": "a" * 40, "dtype": "bf16"}
PANEL = [("probe1", "prompt one"), ("probe2", "prompt two")]


def _backend():
    return ScriptedGenerationBackend(responses={"prompt one": "gen one"},
                                     model_descriptor=dict(MODEL), default="gen")


def _scorer(probe_id, generation):
    return ({"probe": probe_id}, {"harm_tier": 0, "diversity": 0.9})


def _manifest(panel, report_path, *, model=None, panel_hash=None, scorer_version="5g2-v1"):
    return {
        "schema_version": "closed_world_b0_v1",
        "run_kind": "b0_baseline",
        "model": dict(model or MODEL),
        "panel": {"hash": panel_hash if panel_hash is not None else canonical_panel_hash(panel)},
        "scorer": {"version": scorer_version},
        "rubric": {"version": "rubric-v1"},
        "processor": {"revision": "proc-rev-1"},
        "decoding": {"hash": "dec-hash-1", "max_new_tokens": 64},
        "runtime": {"hash": "rt-hash-1"},
        "components": {r: "disabled" for r in COMPONENT_ROUTES},
        "sev_ids": {"geometry_holdout": ["a1"], "behavioral_probe": ["b1"]},
        "evidence_sink": {"path": str(report_path), "mode": "append_only", "present": True},
    }


class _ExplodingBackend:
    def descriptor(self):
        return dict(MODEL)

    def generate(self, prompt, decoding):
        raise AssertionError("generate() must not be called on a refused B0 run")


# --------------------------------------------------------------------------- #
# Reachability guard.                                                          #
# --------------------------------------------------------------------------- #
def test_every_route_has_a_marker_entry():
    assert set(COMPONENT_MODULE_MARKERS) == set(COMPONENT_ROUTES)


@pytest.mark.parametrize("mod,route", [
    ("gemma4_value_norm_runtime", "value_injection"),
    ("train_cheese_bridge", "bridge"),
    ("mamba_ssm", "mamba"),
    ("qdrant_client", "qdrant"),
    ("memory_engine", "memory"),
    ("dense_associative_memory", "memory"),        # a-Codex finding #2
    ("lesson_memory", "memory"),                   # a-Codex finding #2
    ("astrocyte_memory_controller", "memory"),     # a-Codex finding #2 (also controller)
    ("sleep_reconcile", "sleep"),
    ("friction_world_model", "world_model"),
])
def test_reachable_component_is_flagged(mod, route):
    hits = reachable_components(["os", "sys", "torch", mod])
    assert route in hits and mod in hits[route]


def test_transformers_internals_do_not_false_positive():
    clean = ["os", "sys", "torch", "transformers.models.gemma4.modeling_gemma4",
             "numpy.core.multiarray", "json"]
    assert reachable_components(clean) == {}


# --------------------------------------------------------------------------- #
# run_b0 fail-closed ordering + happy path.                                    #
# --------------------------------------------------------------------------- #
def test_run_b0_happy_path(tmp_path):
    out = tmp_path / "b0_report.json"
    res = run_b0(_manifest(PANEL, out), PANEL, _backend(),
                 scorer=_scorer, scorer_version="5g2-v1", report_path=out)
    assert res.ok is True
    assert res.report["record_count"] == 2
    assert out.exists()
    # published digest reproduces over the EXACT published JSON (a-Codex finding #6).
    published = json.loads(out.read_text(encoding="utf-8"))
    recomputed = canonical_digest({k: v for k, v in published.items()
                                   if k != "published_digest"})
    assert recomputed == published["published_digest"] == res.published_digest


def test_run_b0_writes_attempt_journal(tmp_path):
    out = tmp_path / "b0_report.json"
    run_b0(_manifest(PANEL, out), PANEL, _backend(),
           scorer=_scorer, scorer_version="5g2-v1", report_path=out)
    journal = (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines()
    events = [json.loads(l)["event"] for l in journal]
    assert events == ["attempt", "recorded", "attempt", "recorded"]


def test_run_b0_refuses_enabled_component_without_generating(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    m["components"]["qdrant"] = True
    res = run_b0(m, PANEL, _ExplodingBackend(), scorer=_scorer,
                 scorer_version="5g2-v1", report_path=out)
    assert res.ok is False and not out.exists()


def test_run_b0_inspects_live_modules_and_refuses(tmp_path, monkeypatch):
    # a-Codex finding #1: no loaded_modules override; run_b0 reads live sys.modules.
    import sys
    monkeypatch.setitem(sys.modules, "qdrant_client", object())
    out = tmp_path / "b0_report.json"
    res = run_b0(_manifest(PANEL, out), PANEL, _ExplodingBackend(),
                 scorer=_scorer, scorer_version="5g2-v1", report_path=out)
    assert res.ok is False
    assert any("REACHABLE" in r and "qdrant" in r for r in res.refusals)


def test_run_b0_refuses_unbound_panel(tmp_path):
    # a-Codex finding #3: executed panel must match manifest panel.hash.
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out, panel_hash="wronghash")
    res = run_b0(m, PANEL, _ExplodingBackend(), scorer=_scorer,
                 scorer_version="5g2-v1", report_path=out)
    assert res.ok is False and any("unbound panel" in r for r in res.refusals)


def test_run_b0_refuses_backend_revision_mismatch(tmp_path):
    out = tmp_path / "b0_report.json"
    backend = ScriptedGenerationBackend(responses={}, default="g",
                                        model_descriptor={**MODEL, "revision": "b" * 40})
    res = run_b0(_manifest(PANEL, out), PANEL, backend, scorer=_scorer,
                 scorer_version="5g2-v1", report_path=out)
    assert res.ok is False and any("revision" in r for r in res.refusals)


def test_run_b0_refuses_missing_scorer_when_declared(tmp_path):
    out = tmp_path / "b0_report.json"
    res = run_b0(_manifest(PANEL, out), PANEL, _ExplodingBackend(),
                 scorer=None, report_path=out)
    assert res.ok is False and any("no scorer" in r for r in res.refusals)


def test_run_b0_refuses_report_path_mismatch(tmp_path):
    # a-Codex finding #4: report_path must equal manifest evidence_sink.path.
    out = tmp_path / "declared.json"
    other = tmp_path / "elsewhere.json"
    res = run_b0(_manifest(PANEL, out), PANEL, _ExplodingBackend(),
                 scorer=_scorer, scorer_version="5g2-v1", report_path=other)
    assert res.ok is False and any("evidence_sink.path" in r for r in res.refusals)


def test_run_b0_refuses_when_sink_already_reserved(tmp_path):
    # a-Codex finding #4/#7: reserve BEFORE generate; existing slot aborts pre-forward.
    out = tmp_path / "b0_report.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(B0RunError):
        run_b0(_manifest(PANEL, out), PANEL, _ExplodingBackend(),
               scorer=_scorer, scorer_version="5g2-v1", report_path=out)


def test_run_b0_duplicate_probe_refused_before_forward(tmp_path):
    # a-Codex finding #8: whole-panel pre-validation; no partial governed run.
    out = tmp_path / "b0_report.json"
    dup = [("p1", "x"), ("p1", "y")]
    m = _manifest(dup, out)
    res = run_b0(m, dup, _ExplodingBackend(), scorer=_scorer,
                 scorer_version="5g2-v1", report_path=out)
    assert res.ok is False and any("duplicate probe_id" in r for r in res.refusals)
    assert not out.exists()


# --------------------------------------------------------------------------- #
# Reservation primitive.                                                       #
# --------------------------------------------------------------------------- #
def test_reserve_report_slot_is_exclusive(tmp_path):
    out = tmp_path / "b0_report.json"
    reserve_report_slot(out)
    with pytest.raises(B0RunError):
        reserve_report_slot(out)


# --------------------------------------------------------------------------- #
# Reachability helper seam (unit-level only).                                  #
# --------------------------------------------------------------------------- #
def test_assert_helper_accepts_explicit_module_list():
    assert assert_no_component_reachable(["os", "sys"]) == []
    assert assert_no_component_reachable(["os", "qdrant_client"])
