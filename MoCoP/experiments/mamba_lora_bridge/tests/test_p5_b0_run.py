"""Model-free tests for the hardened P5 B0 runner (OpenCLAW #156, slice 4).

Covers wolf-Codex review of record #966 on top of #954/#960: mandatory sterility, runner
authorization, closure-aware scorer digests, the two-phase terminal transaction (O_EXCL
journal + inode identity + no-replace publish + report<->journal binding), full-write
durability, the exact reachability inventory + import-audit sentinel for transient imports,
protected-parent verification, and strict canonicalization. Each #966 counterexample has
an adversarial test here.
"""
import hashlib
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
    _Journal,
    _callable_digest,
    _clear_import_sentinel,
    _drain_import_sentinel,
    _ensure_import_audit,
    _forbidden_route_for,
    _import_audit_hook,
    _normalize_dtype,
    _runner_digest,
    assert_no_component_reachable,
    canonical_panel_hash,
    derive_effective_decoding,
    finalize_publication,
    publish_report_atomic,
    reachable_components,
    reserve_report_slot,
    run_b0,
    verify_terminal_frames,
)

MODEL = {
    "id": "google/gemma-4-12B", "revision": "a" * 40, "dtype": "bf16",
    "backend": "Gemma3ForConditionalGeneration", "device": "cuda:0",
    "attention": "eager", "use_cache": True,
}
PANEL = [("probe1", "prompt one"), ("probe2", "prompt two")]
DEC = {"do_sample": False, "max_new_tokens": 64}
DEC_HASH = canonical_digest(DEC)
RUNNER_DIGEST = _runner_digest()


def _scorer(probe_id, generation):
    return ({"probe": probe_id}, {"harm_tier": 0, "diversity": 0.9})


SCORER_DIGEST = _callable_digest(_scorer)


def _backend(model=None):
    return ScriptedGenerationBackend(responses={"prompt one": "gen one"},
                                     model_descriptor=dict(model or MODEL), default="gen")


def _mods(*names):
    return {n: types.ModuleType(n) for n in names}


def _manifest(panel, report_path, *, model=None, panel_hash=None,
              scorer_version="5g2-v1", scorer_code_digest=None, decoding=None,
              runner_digest=None):
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
        "runtime": {"hash": "rt-hash-1",
                    "runner_digest": runner_digest if runner_digest is not None else RUNNER_DIGEST},
        "components": {r: "disabled" for r in COMPONENT_ROUTES},
        "sev_ids": {"geometry_holdout": ["a1"], "behavioral_probe": ["b1"]},
        "evidence_sink": {"path": str(report_path), "mode": "append_only", "present": False,
                          "protected_sink_attestation": {"signer": "keeper", "review_ref": "wc#971"}},
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

    def assert_sterile(self):
        return None

    def generate(self, prompt, decoding):
        raise AssertionError("generate() must not be called on a refused B0 run")


# --------------------------------------------------------------------------- #
# Reachability: exact inventory + transient import sentinel (#966 HIGH-4).     #
# --------------------------------------------------------------------------- #
def test_inventory_covers_every_route():
    assert set(FORBIDDEN_ROUTE_MODULES) == set(COMPONENT_ROUTES)


@pytest.mark.parametrize("mod,route", [
    ("gemma4_value_norm_runtime", "value_injection"),
    ("train_cheese_bridge", "bridge"),
    ("mamba_ssm", "mamba"),
    ("mamba_ssm.ops.selective_scan", "mamba"),
    ("qdrant_client", "qdrant"),
    ("qdrant_client.http.models", "qdrant"),
    ("memory_engine", "memory"),                              # #966: the named missing route
    ("Projects.Project_Prosthetic.memory_engine", "memory"),  # dotted Projects path
    ("dense_associative_memory", "memory"),
    ("astrocyte_memory_controller", "controller"),
    ("sleep_reconcile", "sleep"),
    ("friction_world_model", "world_model"),
])
def test_reachable_component_is_flagged(mod, route):
    hits = reachable_components(_mods("os", "sys", "torch", mod))
    assert route in hits and mod in hits[route]


@pytest.mark.parametrize("benign", [
    "torch.cuda.memory", "torch.nn.functional",
    "transformers.models.gemma4.modeling_gemma4", "numpy.core.multiarray",
    "json", "os", "sys", "collections.abc",
])
def test_benign_modules_do_not_false_positive(benign):
    assert reachable_components(_mods("os", "sys", "torch", benign)) == {}


def test_none_valued_module_still_counts_by_name():
    assert reachable_components({"qdrant_client": None, "os": None}) == {"qdrant": ["qdrant_client"]}


def test_forbidden_route_for_exact_match():
    assert _forbidden_route_for("memory_engine") == "memory"
    assert _forbidden_route_for("torch.cuda.memory") is None


def test_import_sentinel_flags_forbidden_transient():
    _clear_import_sentinel()
    _import_audit_hook("import", ("qdrant_client", None, None, None, None))
    _import_audit_hook("import", ("json", None, None, None, None))
    assert _drain_import_sentinel() == ["qdrant_client"]
    assert _drain_import_sentinel() == []                     # drained


def test_assert_helper_accepts_explicit_module_list():
    assert assert_no_component_reachable(_mods("os", "sys")) == []
    assert assert_no_component_reachable(_mods("os", "qdrant_client"))


# --------------------------------------------------------------------------- #
# Happy path + journal + publication.                                          #
# --------------------------------------------------------------------------- #
def test_run_b0_happy_path(tmp_path):
    out = tmp_path / "b0_report.json"
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.ok is True
    assert res.terminal_state == "integrity_verified"
    assert res.report["record_count"] == 2
    assert res.report["terminal_state"] == "committed"     # report authority; disposition in journal
    assert out.exists()
    published = json.loads(out.read_text(encoding="utf-8"))
    recomputed = canonical_digest({k: v for k, v in published.items() if k != "published_digest"})
    assert recomputed == published["published_digest"] == res.published_digest
    assert published["execution_descriptor"]["scorer_code_digest"] == SCORER_DIGEST
    assert published["journal_digest"]


def test_run_b0_journal_two_phase_terminal(tmp_path):
    out = tmp_path / "b0_report.json"
    _run(_manifest(PANEL, out), PANEL, _backend(), out)
    events = [json.loads(x) for x in
              (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines()]
    kinds = [e["event"] for e in events]
    assert kinds == ["claim", "attempt", "generated", "recorded",
                     "attempt", "generated", "recorded", "sealing", "completed"]
    attempt_ids = [e["attempt_id"] for e in events if e["event"] == "attempt"]
    assert len(set(attempt_ids)) == 2
    # the sealing event and the report cross-bind the same published_digest
    sealing = next(e for e in events if e["event"] == "sealing")
    assert sealing["published_digest"] == json.loads(out.read_text())["published_digest"]


def test_publish_is_no_replace(tmp_path):
    out = tmp_path / "b0_report.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(B0RunError):
        publish_report_atomic({"a": 1}, out)
    assert out.read_text(encoding="utf-8") == "{}"


def test_publish_rejects_nonstrict_json(tmp_path):
    out = tmp_path / "b0_report.json"
    with pytest.raises(EvidenceBundleError):
        publish_report_atomic({"bad": float("nan")}, out)
    assert not out.exists()


# --------------------------------------------------------------------------- #
# Reservation + protected parent + journal identity (#966 B2/H3/H5).           #
# --------------------------------------------------------------------------- #
def test_reserve_is_exclusive(tmp_path):
    out = tmp_path / "b0_report.json"
    j = reserve_report_slot(out)
    try:
        assert (tmp_path / "b0_report.json.journal").exists()
        with pytest.raises(B0RunError):
            reserve_report_slot(out)
    finally:
        j.close()


def test_reserve_refuses_preexisting_report(tmp_path):
    out = tmp_path / "b0_report.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(B0RunError):
        reserve_report_slot(out)


def test_reserve_refuses_absent_protected_parent(tmp_path):
    # #966 HIGH-5: the runner must NOT mkdir the protected sink parent.
    out = tmp_path / "does_not_exist" / "b0_report.json"
    with pytest.raises(B0RunError) as ei:
        reserve_report_slot(out)
    assert "parent does not exist" in str(ei.value)
    assert not (tmp_path / "does_not_exist").exists()


def test_journal_identity_swap_detected(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    fd = os.open(a, os.O_CREAT | os.O_WRONLY, 0o600)
    b.write_text("x", encoding="utf-8")
    j = _Journal(fd, b)                                       # fd->a, path->b: different inode
    try:
        st_fd, st_b = os.fstat(fd), os.stat(b)
        if (st_fd.st_ino, st_fd.st_dev) != (st_b.st_ino, st_b.st_dev):
            with pytest.raises(B0RunError):
                j.verify_identity()
        else:  # filesystem cannot distinguish inodes (e.g. some Windows FS): no false alarm
            j.verify_identity()
    finally:
        j.close()


# --------------------------------------------------------------------------- #
# Live reachability + late/transient imports inside run_b0.                     #
# --------------------------------------------------------------------------- #
def test_run_b0_inspects_live_modules_and_refuses(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "qdrant_client", types.ModuleType("qdrant_client"))
    out = tmp_path / "b0_report.json"
    res = _run(_manifest(PANEL, out), PANEL, _ExplodingBackend(), out)
    assert res.ok is False
    assert any("REACHABLE" in r and "qdrant" in r for r in res.refusals)
    assert not out.exists()


def test_run_b0_refuses_component_persistently_imported_in_forward(tmp_path):
    out = tmp_path / "b0_report.json"

    class _LateImport:
        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            return None

        def generate(self, prompt, decoding):
            sys.modules["mamba_ssm"] = types.ModuleType("mamba_ssm")
            return "gen"

    try:
        with pytest.raises(B0RunError) as ei:
            _run(_manifest(PANEL, out), PANEL, _LateImport(), out)
        assert "REACHABLE after governed forward" in str(ei.value)
        assert not out.exists()
    finally:
        sys.modules.pop("mamba_ssm", None)


def test_run_b0_refuses_transient_import_in_forward(tmp_path):
    # #966: a component imported AND removed inside one forward is caught by the sentinel.
    out = tmp_path / "b0_report.json"

    class _Transient:
        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            return None

        def generate(self, prompt, decoding):
            sys.audit("import", "mamba_ssm", None, None, None, None)   # transient, not left loaded
            return "gen"

    with pytest.raises(B0RunError) as ei:
        _run(_manifest(PANEL, out), PANEL, _Transient(), out)
    assert "IMPORTED during governed forward" in str(ei.value)
    assert not out.exists()
    assert "mamba_ssm" not in sys.modules


def test_run_b0_refuses_nonsterile_backend_that_raises(tmp_path):
    out = tmp_path / "b0_report.json"

    class _NonSterile:
        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            raise B0RunError("non-sterile: _forward_hooks present")

        def generate(self, prompt, decoding):
            raise AssertionError("must not generate on a non-sterile backend")

    with pytest.raises(B0RunError):
        _run(_manifest(PANEL, out), PANEL, _NonSterile(), out)
    assert not out.exists()


def test_run_b0_refuses_backend_without_sterility_contract(tmp_path):
    # #966 B1: sterility is mandatory — a backend lacking assert_sterile is refused.
    out = tmp_path / "b0_report.json"

    class _NoSterile:
        def descriptor(self):
            return dict(MODEL)

        def generate(self, prompt, decoding):
            raise AssertionError("must not generate")

    res = _run(_manifest(PANEL, out), PANEL, _NoSterile(), out)
    assert res.ok is False and any("sterility contract" in r for r in res.refusals)


# --------------------------------------------------------------------------- #
# Mandatory + derived execution binding (#966 BLOCKER-1).                     #
# --------------------------------------------------------------------------- #
def test_run_b0_refuses_unauthorized_runner(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out, runner_digest="f" * 64)
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("runner_digest mismatch" in r for r in res.refusals)


def test_run_b0_refuses_unset_runner_digest(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    del m["runtime"]["runner_digest"]
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("runner is unauthorized" in r for r in res.refusals)


def test_closure_state_changes_scorer_digest():
    # #966 counterexample: identical source, different captured state -> DIFFERENT digest.
    def make(v):
        def s(pid, gen):
            return ({}, {"v": v})
        return s
    assert _callable_digest(make(1)) != _callable_digest(make(2))


def test_run_b0_refuses_descriptor_missing_field(tmp_path):
    out = tmp_path / "b0_report.json"
    partial = _backend({k: v for k, v in MODEL.items() if k != "use_cache"})
    res = _run(_manifest(PANEL, out), PANEL, partial, out)
    assert res.ok is False and any("omits required field" in r for r in res.refusals)


@pytest.mark.parametrize("field", ["backend", "device", "attention", "use_cache"])
def test_run_b0_binds_extended_descriptor_fields(tmp_path, field):
    out = tmp_path / "b0_report.json"
    altered = dict(MODEL)
    altered[field] = "TAMPERED" if field != "use_cache" else False
    res = _run(_manifest(PANEL, out), PANEL, _backend(altered), out)   # manifest still MODEL
    assert res.ok is False and any(field in r for r in res.refusals)


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
    m["decoding"]["hash"] = "f" * 64
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("decoding.hash" in r for r in res.refusals)


def test_run_b0_refuses_unsupported_decoding_field(tmp_path):
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
    res = _run(_manifest(PANEL, out), PANEL, _backend({**MODEL, "dtype": "fp16"}), out)
    assert res.ok is False and any("dtype" in r for r in res.refusals)


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


def test_run_b0_refuses_enabled_component(tmp_path):
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
# Strict-JSON custody (#960 MED-5 / #966 MED-6).                              #
# --------------------------------------------------------------------------- #
def test_run_b0_nan_scorer_output_refused_no_report(tmp_path):
    out = tmp_path / "b0_report.json"

    def nan_scorer(probe_id, generation):
        return ({"probe": probe_id}, {"score": float("nan")})

    m = _manifest(PANEL, out, scorer_code_digest=_callable_digest(nan_scorer))
    with pytest.raises(EvidenceBundleError):
        _run(m, PANEL, _backend(), out, scorer=nan_scorer)
    assert not out.exists()
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


def test_canonical_digest_is_injective_on_types():
    # #966 MED-6: no {1:"x"} vs {"1":"x"} or (1,2) vs [1,2] collapse — both RAISE now.
    with pytest.raises(EvidenceBundleError):
        canonical_digest({1: "x"})
    with pytest.raises(EvidenceBundleError):
        canonical_digest((1, 2))


# --------------------------------------------------------------------------- #
# dtype normalization + decoding derivation.                                   #
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


# --------------------------------------------------------------------------- #
# Round 4 (#966): boundary around all executed code + terminal/journal custody. #
# --------------------------------------------------------------------------- #
def test_audit_sentinel_arms_and_is_fail_closed_signal():
    assert _ensure_import_audit() is True     # once armed it reports armed (fail-open guard)


def test_run_b0_refuses_backend_dirty_after_forward(tmp_path):
    # #966 HIGH-4: sterility must be re-checked AFTER the forward, not only before.
    out = tmp_path / "b0_report.json"

    class _DirtyAfter:
        def __init__(self):
            self.calls = 0

        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            self.calls += 1
            if self.calls > 1:                # clean pre-forward, dirty after generate
                raise B0RunError("backend became dirty during generate")

        def generate(self, prompt, decoding):
            return "gen"

    with pytest.raises(B0RunError) as ei:
        _run(_manifest(PANEL, out), PANEL, _DirtyAfter(), out)
    assert "dirty" in str(ei.value)
    assert not out.exists()


def test_run_b0_refuses_descriptor_time_transient_import(tmp_path):
    # #966 HIGH-4: a transient forbidden import inside descriptor() must not be erased.
    out = tmp_path / "b0_report.json"

    class _DescImport:
        def descriptor(self):
            sys.audit("import", "qdrant_client", None, None, None, None)
            return dict(MODEL)

        def assert_sterile(self):
            return None

        def generate(self, prompt, decoding):
            raise AssertionError("must not generate")

    res = _run(_manifest(PANEL, out), PANEL, _DescImport(), out)
    assert res.ok is False
    assert any("during backend.descriptor()" in r for r in res.refusals)
    assert not out.exists()


def test_run_b0_does_not_call_backend_on_refused_launch(tmp_path, monkeypatch):
    # #966 HIGH-4: no backend.descriptor() when the cheap gates already refuse.
    monkeypatch.setitem(sys.modules, "mamba_ssm", types.ModuleType("mamba_ssm"))
    out = tmp_path / "b0_report.json"

    class _Tripwire:
        def descriptor(self):
            raise AssertionError("descriptor() must not run on a refused launch")

        def assert_sterile(self):
            return None

        def generate(self, prompt, decoding):
            raise AssertionError("generate() must not run")

    res = _run(_manifest(PANEL, out), PANEL, _Tripwire(), out)
    assert res.ok is False and any("REACHABLE" in r and "mamba" in r for r in res.refusals)


def test_run_b0_refuses_callable_instance_scorer(tmp_path):
    # #966 BLOCKER-3: only a plain function is bindable; a stateful callable is refused.
    out = tmp_path / "b0_report.json"

    class _CallableScorer:
        def __call__(self, probe_id, generation):
            return ({}, {"v": 1})

    res = _run(_manifest(PANEL, out), PANEL, _ExplodingBackend(), out, scorer=_CallableScorer())
    assert res.ok is False and any("plain function" in r for r in res.refusals)


@pytest.mark.parametrize("field", ["backend", "device", "attention"])
def test_run_b0_refuses_null_descriptor_field(tmp_path, field):
    # #966 BLOCKER-3: extended fields cannot be null on both sides and pass.
    out = tmp_path / "b0_report.json"
    model = {**MODEL, field: None}
    res = _run(_manifest(PANEL, out, model=model), PANEL, _backend(model), out)
    assert res.ok is False and any(field in r and "null" in r for r in res.refusals)


def test_run_b0_report_binds_actual_journal_bytes(tmp_path):
    # #966 BLOCKER-2: report.journal_digest == SHA-256 of the ACTUAL journal prefix bytes.
    out = tmp_path / "b0_report.json"
    _run(_manifest(PANEL, out), PANEL, _backend(), out)
    published = json.loads(out.read_text(encoding="utf-8"))
    lines = (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines(keepends=True)
    seal_idx = next(i for i, ln in enumerate(lines) if json.loads(ln)["event"] == "sealing")
    prefix = "".join(lines[:seal_idx]).encode("utf-8")
    assert hashlib.sha256(prefix).hexdigest() == published["journal_digest"]


def test_verify_terminal_frames_tolerates_truncated_tail_after_sealing(tmp_path):
    j = tmp_path / "x.journal"
    j.write_text('{"event":"claim","run_id":"r"}\n{"event":"sealing","run_id":"r"}\n'
                 '{"event":"comp', encoding="utf-8")
    r = verify_terminal_frames(j)
    assert r["ok"] is True and r["truncated_tail"] is True


def test_verify_terminal_frames_rejects_midfile_corruption(tmp_path):
    j = tmp_path / "x.journal"
    j.write_text('{"event":"claim","run_id":"r"}\nNOT JSON\n{"event":"completed","run_id":"r"}\n',
                 encoding="utf-8")
    r = verify_terminal_frames(j)
    assert r["ok"] is False and r.get("corruption_at") == 1


def test_verify_terminal_frames_rejects_event_after_sealing(tmp_path):
    # round-7 RESIDUAL-A: an injected non-terminal frame between sealing and the terminal frame
    # is rejected (the prefix digest, pre-sealing only, cannot see it).
    j = tmp_path / "x.journal"
    j.write_text('{"event":"claim","run_id":"r"}\n{"event":"sealing","run_id":"r"}\n'
                 '{"event":"attempt","attempt_id":"r:0"}\n{"event":"completed","run_id":"r"}\n',
                 encoding="utf-8")
    r = verify_terminal_frames(j)
    assert r["ok"] is False and "after the sealing frame" in r["reason"]


@pytest.mark.parametrize("body,reason_sub", [
    ("", "empty"),
    ('{"event":"attempt","run_id":"r"}\n', "not 'claim'"),
    ('{"event":"claim","run_id":"r"}\n{"event":"sealing","run_id":"r"}\n', "without a terminal"),
    ('{"event":"claim","run_id":"r"}\n{"event":"failed","run_id":"r"}\n'
     '{"event":"completed","run_id":"r"}\n', "more than one terminal"),
    ('{"event":"claim","run_id":"r"}\n{"event":"completed","run_id":"r"}\n', "without a preceding 'sealing'"),
    ('{"event":"claim","run_id":"r"}\n{"event":"sealing","run_id":"x"}\n'
     '{"event":"completed","run_id":"r"}\n', "run_id inconsistent"),
])
def test_verify_terminal_frames_contract_violations(tmp_path, body, reason_sub):
    j = tmp_path / "x.journal"
    j.write_text(body, encoding="utf-8")
    r = verify_terminal_frames(j)
    assert r["ok"] is False and reason_sub in r["reason"]


# --- protected-sink attestation (item-1a pre-run refusal) ---
def test_run_b0_refuses_without_protected_sink_attestation(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    del m["evidence_sink"]["protected_sink_attestation"]
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("protected_sink_attestation" in r for r in res.refusals)


# --- scorer state mutated mid-run (HIGH-3) ---
_MUT_STATE = {"v": 1}


def _mut_reading_scorer(probe_id, generation):
    return ({}, {"v": _MUT_STATE["v"]})


def test_run_b0_refuses_scorer_state_mutated_during_forward(tmp_path):
    out = tmp_path / "b0_report.json"
    _MUT_STATE["v"] = 1
    code_digest = _callable_digest(_mut_reading_scorer)

    class _Mutator:
        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            return None

        def generate(self, prompt, decoding):
            _MUT_STATE["v"] = 2                # mutate the scorer's bound global mid-forward
            return "gen"

    m = _manifest(PANEL, out, scorer_code_digest=code_digest)
    try:
        with pytest.raises(B0RunError) as ei:
            _run(m, PANEL, _Mutator(), out, scorer=_mut_reading_scorer)
        assert "scorer identity changed" in str(ei.value)
        assert not out.exists()
    finally:
        _MUT_STATE["v"] = 1


# --- sterility-call imports are drained (HIGH-5) ---
def test_run_b0_refuses_import_inside_sterility_call(tmp_path):
    out = tmp_path / "b0_report.json"

    class _SterileImports:
        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            sys.audit("import", "qdrant_client", None, None, None, None)

        def generate(self, prompt, decoding):
            return "gen"

    with pytest.raises(B0RunError) as ei:
        _run(_manifest(PANEL, out), PANEL, _SterileImports(), out)
    assert "assert_sterile" in str(ei.value)
    assert not out.exists()


# --- finalize_publication disposition machine (BLOCKER-1/2) ---
def test_finalize_publication_verified(tmp_path):
    rp = tmp_path / "r.json"
    rp.write_bytes(b"DATA")
    j = reserve_report_slot(tmp_path / "other.json")
    try:
        disp, warns = finalize_publication(rp, b"DATA", tmp_path / "r.json.tmp", j)
        assert disp == "integrity_verified"
    finally:
        j.close()


def test_finalize_publication_readback_mismatch_is_integrity_failed(tmp_path):
    rp = tmp_path / "r.json"
    rp.write_bytes(b"DATA")
    j = reserve_report_slot(tmp_path / "other.json")
    try:
        disp, warns = finalize_publication(rp, b"DIFFERENT", tmp_path / "r.json.tmp", j)
        assert disp == "committed_integrity_failed"
        assert any("readback mismatch" in w for w in warns)
    finally:
        j.close()


def test_finalize_publication_surviving_alias_is_integrity_failed(tmp_path, monkeypatch):
    import p5_b0_run as mod
    rp = tmp_path / "r.json"
    rp.write_bytes(b"DATA")
    alias = tmp_path / "r.json.tmp"
    alias.write_bytes(b"DATA")
    monkeypatch.setattr(mod, "_try_unlink", lambda p: False)
    j = reserve_report_slot(tmp_path / "other.json")
    try:
        disp, warns = finalize_publication(rp, b"DATA", alias, j)
        assert disp == "committed_integrity_failed"
        assert any("staging alias" in w for w in warns)
    finally:
        j.close()


def test_finalize_publication_prefix_match_verified(tmp_path):
    # round-7: bound journal_digest == the on-disk pre-sealing bytes -> integrity_verified.
    rp = tmp_path / "r.json"
    rp.write_bytes(b"DATA")
    j = reserve_report_slot(tmp_path / "other.json")
    try:
        j.event({"event": "claim", "run_id": "r"})
        bound = j.actual_prefix_digest()
        j.event({"event": "sealing", "run_id": "r", "journal_digest_prefix": bound})
        disp, warns = finalize_publication(rp, b"DATA", tmp_path / "r.json.tmp", j, bound)
        assert disp == "integrity_verified"
    finally:
        j.close()


def test_finalize_publication_detects_prefix_injection(tmp_path):
    # round-7 (HuntR7): a co-writer injects a frame BEFORE the sealing frame; the bound
    # journal_digest no longer matches the on-disk pre-sealing bytes -> committed_integrity_failed.
    rp = tmp_path / "r.json"
    rp.write_bytes(b"DATA")
    j = reserve_report_slot(tmp_path / "other.json")
    try:
        j.event({"event": "claim", "run_id": "r"})
        bound = j.actual_prefix_digest()                          # digest of [claim] only
        j.event({"event": "attempt", "attempt_id": "r:0"})        # INJECTED pre-sealing frame
        j.event({"event": "sealing", "run_id": "r", "journal_digest_prefix": bound})
        disp, warns = finalize_publication(rp, b"DATA", tmp_path / "r.json.tmp", j, bound)
        assert disp == "committed_integrity_failed"
        assert any("prefix digest mismatch" in w for w in warns)
    finally:
        j.close()


def test_run_b0_truncated_at_sealing_is_indeterminate(tmp_path, monkeypatch):
    # HuntR7 LOW: verify returning ok=True with disposition=None (truncated tail at sealing) must
    # NOT leave the result integrity_verified — the reconcile forces indeterminate.
    import p5_b0_run as mod
    out = tmp_path / "b0_report.json"

    def truncated(path, *, report_published_digest=None):
        return {"ok": True, "disposition": None, "terminal": "sealing", "truncated_tail": True}

    monkeypatch.setattr(mod, "verify_terminal_frames", truncated)
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.ok is False and res.terminal_state == "committed_indeterminate"


def test_run_b0_terminal_write_failure_is_indeterminate(tmp_path, monkeypatch):
    # #966 round-5 H6: a post-commit terminal-frame write failure -> committed_indeterminate
    # (ok=False), NOT an uncaught raise; the report is still committed.
    import p5_b0_run as mod
    out = tmp_path / "b0_report.json"

    def boom(self, obj):
        raise mod.B0RunError("forced zero-progress on terminal write")

    monkeypatch.setattr(mod._Journal, "write_terminal_frame", boom)
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.ok is False
    assert res.terminal_state == "committed_indeterminate"
    assert out.exists()                                  # the report WAS committed


def test_run_b0_terminal_fsync_failure_is_indeterminate_not_verified(tmp_path, monkeypatch):
    # Codex #973: an fsync failure after writing the terminal frame is NOT integrity_verified.
    # "verified" must mean DURABLE custody, not page-cache visibility -> committed_indeterminate.
    # The frame bytes are visible on disk (a non-authoritative unsynced tail), but the RESULT
    # reports the durable truth.
    import p5_b0_run as mod
    out = tmp_path / "b0_report.json"

    def written_unsynced(self, obj):
        line = (json.dumps(dict(obj), sort_keys=True, allow_nan=False,
                           ensure_ascii=True) + "\n").encode("utf-8")
        mod._write_all(self._fd, line)                  # bytes land; report fsync failure
        return "written_unsynced"

    monkeypatch.setattr(mod._Journal, "write_terminal_frame", written_unsynced)
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.ok is False and res.terminal_state == "committed_indeterminate"
    assert any("not fsync-durable" in w or "not durably committed" in w for w in res.warnings)
    events = [json.loads(x) for x in
              (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "completed"           # visible tail, but non-authoritative


def test_run_b0_refuses_placeholder_attestation(tmp_path):
    # #966 round-6 C1: signer/review_ref="TBD" must be rejected (harness placeholder check).
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    m["evidence_sink"]["protected_sink_attestation"] = {"signer": "TBD", "review_ref": "TBD"}
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("placeholder" in r for r in res.refusals)


_B_HELPER_STATE = {"v": 1}


def _b_helper():
    return _B_HELPER_STATE["v"]


def _helper_using_scorer(probe_id, generation):
    return ({}, {"v": _b_helper()})


def test_run_b0_refuses_scorer_with_module_helper(tmp_path):
    # #966 round-6 B: a scorer reaching state via a module-level helper is refused (its digest
    # cannot bind the helper's globals).
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out, scorer_code_digest=_callable_digest(_helper_using_scorer))
    res = _run(m, PANEL, _ExplodingBackend(), out, scorer=_helper_using_scorer)
    assert res.ok is False and any("self-contained" in r for r in res.refusals)


def test_run_b0_refuses_dirty_sentinel_at_entry(tmp_path):
    # #966 round-6 D: a forbidden import leaked by a prior run must fail the next run closed.
    import p5_b0_run as mod
    mod._ensure_import_audit()
    mod._forbidden_imports.append("qdrant_client")
    out = tmp_path / "b0_report.json"
    try:
        res = _run(_manifest(PANEL, out), PANEL, _ExplodingBackend(), out)
        assert res.ok is False and any("dirty at run entry" in r for r in res.refusals)
    finally:
        mod._forbidden_imports.clear()


class _EvilRepr:
    def __repr__(self):
        sys.audit("import", "qdrant_client", None, None, None, None)
        return "evil"


_EVIL_CONTAINER = [_EvilRepr()]


def _evil_repr_scorer(probe_id, generation):
    return ({}, {"n": len(_EVIL_CONTAINER)})


def test_run_b0_accounts_for_import_during_scorer_digest(tmp_path):
    # #966 round-6 D: a forbidden import triggered by __repr__ during the scorer digest is
    # ACCOUNTED (refused), not erased unexamined by a bare clear.
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out, scorer_code_digest="unused")
    res = _run(m, PANEL, _ExplodingBackend(), out, scorer=_evil_repr_scorer)
    assert res.ok is False and any("IMPORTED during scorer digest" in r for r in res.refusals)
    assert not out.exists()


def test_verify_terminal_frames_raises_on_non_utf8(tmp_path):
    # The verifier read CAN raise UnicodeDecodeError on a mutated inode — the vector for A2b.
    j = tmp_path / "x.journal"
    j.write_bytes(b'{"event":"claim","run_id":"r"}\n\xff\xfe')
    with pytest.raises(UnicodeDecodeError):
        verify_terminal_frames(j)


def test_run_b0_verifier_read_valueerror_is_indeterminate(tmp_path, monkeypatch):
    # #966 round-6 A2b: a UnicodeDecodeError (ValueError) from the verifier read must NOT escape
    # as an uncaught raise on a committed run — it downgrades to committed_indeterminate.
    import p5_b0_run as mod
    out = tmp_path / "b0_report.json"

    def boom(path, *, report_published_digest=None):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(mod, "verify_terminal_frames", boom)
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.ok is False and res.terminal_state == "committed_indeterminate"
    assert out.exists()                                            # report WAS committed


def test_run_b0_integrity_failed_plus_write_failure_matches_journal(tmp_path, monkeypatch):
    # #966 round-6 A2: finalize says integrity_failed but the terminal write fails -> the journal
    # ends at 'sealing' (no terminal), so the RESULT must be indeterminate to match the journal
    # (the integrity-failed detail is preserved in warnings).
    import p5_b0_run as mod
    out = tmp_path / "b0_report.json"
    monkeypatch.setattr(mod, "finalize_publication",
                        lambda rp, c, sa, j, rjd: (mod.COMMITTED_INTEGRITY_FAILED, ["forced integrity fail"]))

    def no_write(self, obj):
        raise mod.B0RunError("terminal write failed")

    monkeypatch.setattr(mod._Journal, "write_terminal_frame", no_write)
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.terminal_state == "committed_indeterminate"        # matches on-disk journal
    events = [json.loads(x) for x in
              (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "sealing"                       # no terminal frame on disk
    assert any("integrity_failed" in w for w in res.warnings)     # detail preserved


class _BCfg:
    def __init__(self):
        self.v = 1


_B_CFG_INSTANCE = _BCfg()


def _instance_reading_scorer(probe_id, generation):
    return ({}, {"v": _B_CFG_INSTANCE.v})


def test_run_b0_refuses_scorer_with_module_instance(tmp_path):
    # #966 round-6 B residual: a scorer reaching state via a module-level INSTANCE attribute is
    # refused (an instance is not a bindable data type).
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out, scorer_code_digest=_callable_digest(_instance_reading_scorer))
    res = _run(m, PANEL, _ExplodingBackend(), out, scorer=_instance_reading_scorer)
    assert res.ok is False and any("self-contained" in r for r in res.refusals)


def test_reserve_reports_uncleaned_collision(tmp_path, monkeypatch):
    # #966 round-5 MED-7: on fsync failure with a failed cleanup, report the surviving path.
    import p5_b0_run as mod
    monkeypatch.setattr(mod, "_fsync_parent",
                        lambda p: (_ for _ in ()).throw(OSError("forced fsync failure")))
    monkeypatch.setattr(mod, "_try_unlink", lambda p: False)
    with pytest.raises(B0RunError) as ei:
        reserve_report_slot(tmp_path / "b0_report.json")
    assert "NOT REMOVED" in str(ei.value)


def test_reserve_refuses_symlinked_parent(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    try:
        os.symlink(real, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not permitted on this platform")
    with pytest.raises(B0RunError) as ei:
        reserve_report_slot(link / "b0_report.json")
    assert "symlink" in str(ei.value)


_SCORER_GLOBAL_STATE = {"v": 1}


def _global_reading_scorer(probe_id, generation):
    return ({}, {"v": _SCORER_GLOBAL_STATE["v"]})


def test_scorer_digest_binds_referenced_mutable_global():
    # #966 BLOCKER-3 residual: a plain function reading a mutable module global must NOT
    # collide on digest when that global changes value.
    d1 = _callable_digest(_global_reading_scorer)
    _SCORER_GLOBAL_STATE["v"] = 2
    try:
        d2 = _callable_digest(_global_reading_scorer)
    finally:
        _SCORER_GLOBAL_STATE["v"] = 1
    assert d1 != d2


def test_ensure_import_audit_fails_closed(monkeypatch):
    # #966 HIGH-4: an install failure must report False (fail-closed), never mark installed.
    import p5_b0_run as mod

    def _boom(hook):
        raise RuntimeError("cannot install audit hook")

    monkeypatch.setattr(mod, "_audit_installed", False)
    monkeypatch.setattr(mod.sys, "addaudithook", _boom)
    assert mod._ensure_import_audit() is False
