"""Model-free tests for the hardened P5 B0 runner (OpenCLAW #156, slice 4).

Covers the wolf-Codex review of record #954/#960: MANDATORY derived execution binding,
no-replace atomic publication with byte verification, O_EXCL append-only journal with
unique attempt ids + terminal events, the reviewed EXACT reachability inventory (retiring
both the dotless-basename and __file__-path heuristics), post-forward late-import
re-check, sterile-backend seam, and strict-JSON custody (NaN/object refused pre-publish).
Each blocker Codex reproduced has an adversarial test here.
"""
import json
import os
import sys
import types

import pytest

from p5_b0_harness import COMPONENT_ROUTES, EvidenceBundleError, canonical_digest
from p5_b0_run import (
    FORBIDDEN_ROUTE_MODULES,
    B0RunError,
    ScriptedGenerationBackend,
    _callable_digest,
    _normalize_dtype,
    assert_no_component_reachable,
    canonical_panel_hash,
    derive_effective_decoding,
    publish_report_atomic,
    reachable_components,
    reserve_report_slot,
    run_b0,
)

MODEL = {"id": "google/gemma-4-12B", "revision": "a" * 40, "dtype": "bf16"}
PANEL = [("probe1", "prompt one"), ("probe2", "prompt two")]
DEC = {"do_sample": False, "max_new_tokens": 64}
DEC_HASH = canonical_digest(DEC)


def _scorer(probe_id, generation):
    return ({"probe": probe_id}, {"harm_tier": 0, "diversity": 0.9})


SCORER_DIGEST = _callable_digest(_scorer)


def _backend(model=None):
    return ScriptedGenerationBackend(responses={"prompt one": "gen one"},
                                     model_descriptor=dict(model or MODEL), default="gen")


def _mods(*names):
    """A fake sys.modules mapping — reachability matches on NAME only now."""
    return {n: types.ModuleType(n) for n in names}


def _manifest(panel, report_path, *, model=None, panel_hash=None,
              scorer_version="5g2-v1", scorer_code_digest=None, decoding=None):
    dec = dict(decoding or DEC)
    dec_block = {**dec, "hash": canonical_digest(
        {"do_sample": bool(dec["do_sample"]), "max_new_tokens": int(dec["max_new_tokens"])})}
    return {
        "schema_version": "closed_world_b0_v1",
        "run_kind": "b0_baseline",
        "model": dict(model or MODEL),
        "panel": {"hash": panel_hash if panel_hash is not None else canonical_panel_hash(panel)},
        "scorer": {"version": scorer_version,
                   "code_digest": scorer_code_digest if scorer_code_digest is not None else SCORER_DIGEST},
        "rubric": {"version": "rubric-v1"},
        "processor": {"revision": "proc-rev-1"},
        "decoding": dec_block,
        "runtime": {"hash": "rt-hash-1"},
        "components": {r: "disabled" for r in COMPONENT_ROUTES},
        "sev_ids": {"geometry_holdout": ["a1"], "behavioral_probe": ["b1"]},
        "evidence_sink": {"path": str(report_path), "mode": "append_only", "present": False},
    }


def _run(manifest, panel, backend, out, **over):
    kw = dict(scorer=_scorer, scorer_version="5g2-v1", rubric_version="rubric-v1",
              processor_revision="proc-rev-1", decoding_hash=DEC_HASH,
              runtime_hash="rt-hash-1", report_path=out)
    kw.update(over)
    return run_b0(manifest, panel, backend, **kw)


class _ExplodingBackend:
    def descriptor(self):
        return dict(MODEL)

    def generate(self, prompt, decoding):
        raise AssertionError("generate() must not be called on a refused B0 run")


# --------------------------------------------------------------------------- #
# Reachability guard: reviewed EXACT inventory (#960 HIGH-4).                  #
# --------------------------------------------------------------------------- #
def test_inventory_covers_every_route():
    assert set(FORBIDDEN_ROUTE_MODULES) == set(COMPONENT_ROUTES)


@pytest.mark.parametrize("mod,route", [
    ("gemma4_value_norm_runtime", "value_injection"),
    ("train_cheese_bridge", "bridge"),
    ("mamba_ssm", "mamba"),                        # external site-packages package
    ("mamba_ssm.ops.selective_scan", "mamba"),     # its dotted submodule
    ("qdrant_client", "qdrant"),                    # external site-packages package
    ("qdrant_client.http.models", "qdrant"),        # dotted submodule -> top-level hit
    ("dense_associative_memory", "memory"),
    ("lesson_memory", "memory"),
    ("astrocyte_memory_controller", "controller"),
    ("sleep_reconcile", "sleep"),
    ("friction_world_model", "world_model"),
    ("gate_policy_replay", "replay"),
])
def test_reachable_component_is_flagged(mod, route):
    hits = reachable_components(_mods("os", "sys", "torch", mod))
    assert route in hits and mod in hits[route]


@pytest.mark.parametrize("benign", [
    "torch.cuda.memory",           # basename 'memory' must NOT fire (the old substring bug)
    "torch.nn.functional",
    "transformers.models.gemma4.modeling_gemma4",
    "numpy.core.multiarray",
    "json", "os", "sys", "collections.abc",
])
def test_benign_modules_do_not_false_positive(benign):
    assert reachable_components(_mods("os", "sys", "torch", benign)) == {}


def test_none_valued_module_still_counts_by_name():
    # A None entry in sys.modules (attempted import) is still reachability by NAME.
    assert reachable_components({"qdrant_client": None, "os": None}) == {"qdrant": ["qdrant_client"]}


def test_assert_helper_accepts_explicit_module_list():
    assert assert_no_component_reachable(_mods("os", "sys")) == []
    assert assert_no_component_reachable(_mods("os", "qdrant_client"))


# --------------------------------------------------------------------------- #
# run_b0 happy path + journal + publication.                                   #
# --------------------------------------------------------------------------- #
def test_run_b0_happy_path(tmp_path):
    out = tmp_path / "b0_report.json"
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.ok is True
    assert res.report["record_count"] == 2
    assert out.exists()
    published = json.loads(out.read_text(encoding="utf-8"))
    recomputed = canonical_digest({k: v for k, v in published.items() if k != "published_digest"})
    assert recomputed == published["published_digest"] == res.published_digest
    # execution descriptor is journaled into the report for audit.
    assert published["execution_descriptor"]["scorer_code_digest"] == SCORER_DIGEST
    assert published["execution_descriptor"]["decoding"] == DEC


def test_run_b0_journal_has_unique_attempts_and_terminal_completed(tmp_path):
    out = tmp_path / "b0_report.json"
    _run(_manifest(PANEL, out), PANEL, _backend(), out)
    lines = (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    kinds = [e["event"] for e in events]
    assert kinds == ["claim", "attempt", "generated", "recorded",
                     "attempt", "generated", "recorded", "completed"]
    attempt_ids = [e["attempt_id"] for e in events if e["event"] == "attempt"]
    assert len(set(attempt_ids)) == 2                       # unique per probe
    assert events[0]["runner_digest"] and events[-1]["report_bytes_sha256"]


def test_publish_is_no_replace(tmp_path):
    out = tmp_path / "b0_report.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(B0RunError):
        publish_report_atomic({"a": 1}, out)
    assert out.read_text(encoding="utf-8") == "{}"          # untouched


def test_publish_verifies_and_rejects_nonstrict_json(tmp_path):
    out = tmp_path / "b0_report.json"
    with pytest.raises(EvidenceBundleError):
        publish_report_atomic({"bad": float("nan")}, out)
    assert not out.exists()


# --------------------------------------------------------------------------- #
# Reservation primitive (#960 BLOCKER-1 / HIGH-3).                            #
# --------------------------------------------------------------------------- #
def test_reserve_is_exclusive(tmp_path):
    out = tmp_path / "b0_report.json"
    fd, journal = reserve_report_slot(out)
    os.close(fd)
    assert journal.exists()
    with pytest.raises(B0RunError):
        reserve_report_slot(out)


def test_reserve_refuses_preexisting_report(tmp_path):
    out = tmp_path / "b0_report.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(B0RunError):
        reserve_report_slot(out)


def test_run_b0_refuses_when_report_preexists(tmp_path):
    out = tmp_path / "b0_report.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(B0RunError):
        _run(_manifest(PANEL, out), PANEL, _ExplodingBackend(), out)


# --------------------------------------------------------------------------- #
# Reachability inside run_b0: live pre-forward + late-import re-check.         #
# --------------------------------------------------------------------------- #
def test_run_b0_inspects_live_modules_and_refuses(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "qdrant_client", types.ModuleType("qdrant_client"))
    out = tmp_path / "b0_report.json"
    res = _run(_manifest(PANEL, out), PANEL, _ExplodingBackend(), out)
    assert res.ok is False
    assert any("REACHABLE" in r and "qdrant" in r for r in res.refusals)
    assert not out.exists()


def test_run_b0_refuses_component_imported_during_forward(tmp_path):
    # #960 HIGH-4: a backend that imports a forbidden module INSIDE generate is caught by
    # the post-forward re-check; the run raises and publishes no sealed report.
    out = tmp_path / "b0_report.json"

    class _LateImport:
        def descriptor(self):
            return dict(MODEL)

        def generate(self, prompt, decoding):
            sys.modules["mamba_ssm"] = types.ModuleType("mamba_ssm")
            return "gen"

    try:
        with pytest.raises(B0RunError) as ei:
            _run(_manifest(PANEL, out), PANEL, _LateImport(), out)
        assert "REACHABLE during the governed forward" in str(ei.value)
        assert not out.exists()
    finally:
        sys.modules.pop("mamba_ssm", None)


def test_run_b0_refuses_nonsterile_backend(tmp_path):
    out = tmp_path / "b0_report.json"

    class _NonSterile:
        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            raise B0RunError("non-sterile model: _forward_hooks present")

        def generate(self, prompt, decoding):
            raise AssertionError("must not generate on a non-sterile backend")

    with pytest.raises(B0RunError):
        _run(_manifest(PANEL, out), PANEL, _NonSterile(), out)
    assert not out.exists()


# --------------------------------------------------------------------------- #
# Mandatory + derived execution binding (#960 BLOCKER-2).                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("missing", [
    "rubric_version", "processor_revision", "decoding_hash", "runtime_hash",
])
def test_run_b0_refuses_missing_mandatory_binding(tmp_path, missing):
    out = tmp_path / "b0_report.json"
    res = _run(_manifest(PANEL, out), PANEL, _ExplodingBackend(), out, **{missing: None})
    assert res.ok is False
    assert any("mandatory" in r and missing.split("_")[0] in r for r in res.refusals)


def test_run_b0_refuses_scorer_code_digest_mismatch(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out, scorer_code_digest="deadbeef")
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("code_digest" in r for r in res.refusals)


def test_run_b0_refuses_derived_decoding_hash_mismatch(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    m["decoding"]["hash"] = "f" * 64                     # not the derived hash
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("decoding.hash" in r for r in res.refusals)


def test_run_b0_refuses_unsupported_decoding_field(tmp_path):
    # #960 BLOCKER-2: temperature is accepted-but-ignored by generate -> ban it.
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    m["decoding"]["temperature"] = 0.7
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("unsupported decoding fields" in r for r in res.refusals)


def test_run_b0_refuses_nondeterministic_decoding(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out, decoding={"do_sample": True, "max_new_tokens": 64})
    res = _run(m, PANEL, _ExplodingBackend(), out,
               decoding_hash=canonical_digest({"do_sample": True, "max_new_tokens": 64}))
    assert res.ok is False and any("deterministic" in r for r in res.refusals)


def test_run_b0_refuses_dtype_mismatch(tmp_path):
    out = tmp_path / "b0_report.json"
    backend = _backend({**MODEL, "dtype": "fp16"})       # self-refusing dtype
    res = _run(_manifest(PANEL, out), PANEL, backend, out)
    assert res.ok is False and any("dtype" in r for r in res.refusals)


def test_run_b0_refuses_backend_revision_mismatch(tmp_path):
    out = tmp_path / "b0_report.json"
    backend = _backend({**MODEL, "revision": "b" * 40})
    res = _run(_manifest(PANEL, out), PANEL, backend, out)
    assert res.ok is False and any("revision" in r for r in res.refusals)


def test_run_b0_refuses_unbound_panel(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out, panel_hash="wronghash")
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("unbound panel" in r for r in res.refusals)


def test_run_b0_refuses_missing_scorer(tmp_path):
    out = tmp_path / "b0_report.json"
    res = _run(_manifest(PANEL, out), PANEL, _ExplodingBackend(), out, scorer=None)
    assert res.ok is False and any("scorer is mandatory" in r for r in res.refusals)


def test_run_b0_refuses_report_path_mismatch(tmp_path):
    out = tmp_path / "declared.json"
    other = tmp_path / "elsewhere.json"
    res = _run(_manifest(PANEL, out), PANEL, _ExplodingBackend(), out, report_path=other)
    assert res.ok is False and any("evidence_sink.path" in r for r in res.refusals)


def test_run_b0_refuses_enabled_component_without_generating(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    m["components"]["qdrant"] = True
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and not out.exists()


def test_run_b0_duplicate_probe_refused_before_forward(tmp_path):
    out = tmp_path / "b0_report.json"
    dup = [("p1", "x"), ("p1", "y")]
    res = _run(_manifest(dup, out), dup, _ExplodingBackend(), out)
    assert res.ok is False and any("duplicate probe_id" in r for r in res.refusals)
    assert not out.exists()


# --------------------------------------------------------------------------- #
# Strict-JSON custody: NaN / object refused before publish (#960 MED-5).      #
# --------------------------------------------------------------------------- #
def test_run_b0_nan_scorer_output_refused_no_report(tmp_path):
    out = tmp_path / "b0_report.json"

    def nan_scorer(probe_id, generation):
        return ({"probe": probe_id}, {"score": float("nan")})

    m = _manifest(PANEL, out, scorer_code_digest=_callable_digest(nan_scorer))
    with pytest.raises(EvidenceBundleError):
        _run(m, PANEL, _backend(), out, scorer=nan_scorer)
    assert not out.exists()
    # a failed run leaves the journal with a terminal 'failed' event.
    events = [json.loads(x) for x in
              (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "failed"


def test_run_b0_object_scorer_output_refused_no_report(tmp_path):
    out = tmp_path / "b0_report.json"

    def obj_scorer(probe_id, generation):
        return ({"probe": probe_id}, {"score": object()})

    m = _manifest(PANEL, out, scorer_code_digest=_callable_digest(obj_scorer))
    with pytest.raises(EvidenceBundleError):
        _run(m, PANEL, _backend(), out, scorer=obj_scorer)
    assert not out.exists()


# --------------------------------------------------------------------------- #
# dtype normalization (#960 BLOCKER-2 self-refusal fix).                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw,norm", [
    ("bfloat16", "bf16"), ("torch.bfloat16", "bf16"), ("bf16", "bf16"),
    ("float16", "fp16"), ("float32", "fp32"),
])
def test_normalize_dtype(raw, norm):
    assert _normalize_dtype(raw) == norm


def test_derive_effective_decoding_drops_extras():
    m = {"decoding": {"do_sample": False, "max_new_tokens": 32, "hash": "x", "temperature": 0.7}}
    assert derive_effective_decoding(m) == {"do_sample": False, "max_new_tokens": 32}
