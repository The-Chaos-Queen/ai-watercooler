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
import pathlib
import sys
import types

import pytest

import p5_b0_run

from p5_b0_harness import (
    COMPONENT_ROUTES,
    B0EvidenceBundle,
    EvidenceBundleError,
    canonical_digest,
)
from p5_b0_run import (
    FORBIDDEN_ROUTE_MODULES,
    B0RunError,
    ScriptedGenerationBackend,
    _Journal,
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
    load_allowlisted_scorer,
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


# The reviewed scorer is loaded content-first from the COMMITTED allowlist, whose path the runner
# derives INTERNALLY (there is deliberately no assignable path global — Codex #1003 BLOCKER-1).
# Tests locate the same committed file read-only, purely to build a matching manifest scorer block.
SCORER_ID = "b0_null_estimator"
SCORER_VERSION = "1"
_COMMITTED_ALLOWLIST = pathlib.Path(p5_b0_run.__file__).with_name("scorer_allowlist.json")
ALLOWLIST_DIGEST = canonical_digest(json.loads(_COMMITTED_ALLOWLIST.read_bytes()))
_DEFAULT_SCORER_BLOCK = {"scorer_id": SCORER_ID, "version": SCORER_VERSION,
                         "allowlist_digest": ALLOWLIST_DIGEST}


def _write_scorer_allowlist(tmp_path, source, *, scorer_id=SCORER_ID, version=SCORER_VERSION,
                            entrypoint="score", blob_override=None, module_path="custom_scorer.py",
                            review_ref="wc#test", module_name="custom_scorer.py"):
    """Write a scorer module + a matching allowlist under tmp_path; return (allowlist_path, block).

    The allowlist stores a module_path RELATIVE to the allowlist's own directory (the committed
    model — Codex #1000 BLOCKER-1). ``block`` is the manifest ``scorer`` block that binds it.
    ``blob_override`` forges blob_sha256; ``module_path`` can be forced (e.g. absolute or a
    traversal) to exercise path-confinement refusals; ``review_ref`` can be a placeholder.
    """
    mod = tmp_path / module_name
    mod.write_text(source, encoding="utf-8")
    blob = blob_override or hashlib.sha256(mod.read_bytes()).hexdigest()
    allow = {
        "schema_version": "b0_scorer_allowlist_v1",
        "scorers": [{
            "scorer_id": scorer_id, "version": version,
            "module_path": module_path, "entrypoint": entrypoint,
            "blob_sha256": blob, "review_ref": review_ref,
        }],
    }
    allow_path = tmp_path / "allowlist.json"
    allow_path.write_text(json.dumps(allow), encoding="utf-8")
    digest = canonical_digest(json.loads(allow_path.read_bytes()))
    block = {"scorer_id": scorer_id, "version": version, "allowlist_digest": digest}
    return allow_path, block


def _backend(model=None):
    return ScriptedGenerationBackend(responses={"prompt one": "gen one"},
                                     model_descriptor=dict(model or MODEL), default="gen")


def _mods(*names):
    return {n: types.ModuleType(n) for n in names}


def _manifest(panel, report_path, *, model=None, panel_hash=None,
              scorer_block=None, decoding=None, runner_digest=None):
    dec = dict(decoding or DEC)
    dec_block = {**dec, "hash": canonical_digest(
        {"do_sample": bool(dec["do_sample"]), "max_new_tokens": int(dec["max_new_tokens"])})}
    return {
        "schema_version": "closed_world_b0_v1",
        "run_kind": "b0_baseline",
        "model": dict(model or MODEL),
        "panel": {"hash": panel_hash if panel_hash is not None else canonical_panel_hash(panel)},
        "scorer": dict(scorer_block if scorer_block is not None else _DEFAULT_SCORER_BLOCK),
        "rubric": {"version": "rubric-v1"},
        "processor": {"revision": "proc-rev-1"},
        "decoding": dec_block,
        "runtime": {"hash": "rt-hash-1",
                    "runner_digest": runner_digest if runner_digest is not None else RUNNER_DIGEST},
        "components": {r: "disabled" for r in COMPONENT_ROUTES},
        "sev_ids": {"geometry_holdout": ["a1"], "behavioral_probe": ["b1"]},
        "evidence_sink": {"path": str(report_path), "mode": "append_only", "present": False,
                          "protected_sink_attestation": {
                              "signer": "keeper", "review_ref": "wc#971",
                              "digest": "a" * 64, "bound_path": str(report_path)}},
    }


def _run(manifest, panel, backend, out, **over):
    kw = dict(rubric_version="rubric-v1", processor_revision="proc-rev-1",
              decoding_hash=DEC_HASH, runtime_hash="rt-hash-1", report_path=out)
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
# Journal frame builders — every governed frame has an EXACT field set (Codex   #
# #1000/#1003 BLOCKER-2), so hand-built test journals must be schema-complete.  #
# Each builder emits a VALID frame; tests override/drop one field to isolate a  #
# single rejection.                                                             #
# --------------------------------------------------------------------------- #
H = "a" * 64                                    # a well-formed sha256 stand-in
RID = "r"
_SB = {"scorer_id": "b0_null_estimator", "version": "1", "blob_sha256": "b" * 64,
       "allowlist_digest": "c" * 64, "review_ref": "wc#1000"}


def _frame(event, **fields):
    return json.dumps({"event": event, **fields}, sort_keys=True) + "\n"


def _drop(line, *keys):
    """Re-emit a built frame with ``keys`` removed (to test 'missing required field')."""
    obj = json.loads(line)
    for k in keys:
        obj.pop(k, None)
    return json.dumps(obj, sort_keys=True) + "\n"


def _f_claim(**over):
    f = {"run_id": RID, "run_kind": "b0_baseline", "manifest_digest": H,
         "execution_descriptor_digest": H, "scorer_binding": dict(_SB), "utc": "T"}
    f.update(over)
    return _frame("claim", **f)


def _f_attempt(ordinal=0, probe="p0", run_id=RID, **over):
    f = {"attempt_id": f"{run_id}:{ordinal}", "ordinal": ordinal, "probe_id": probe,
         "prompt_sha256": H, "utc": "T"}
    f.update(over)
    return _frame("attempt", **f)


def _f_generated(ordinal=0, probe="p0", run_id=RID, **over):
    f = {"attempt_id": f"{run_id}:{ordinal}", "ordinal": ordinal, "probe_id": probe,
         "generation_sha256": H, "generation": "gen"}
    f.update(over)
    return _frame("generated", **f)


def _f_recorded(ordinal=0, probe="p0", run_id=RID, **over):
    f = {"attempt_id": f"{run_id}:{ordinal}", "ordinal": ordinal, "probe_id": probe}
    f.update(over)
    return _frame("recorded", **f)


def _f_cycle(ordinal=0, probe="p0"):
    return _f_attempt(ordinal, probe) + _f_generated(ordinal, probe) + _f_recorded(ordinal, probe)


def _f_sealing(**over):
    f = {"run_id": RID, "published_digest": H, "journal_digest_prefix": H, "utc": "T"}
    f.update(over)
    return _frame("sealing", **f)


def _f_terminal(event="completed", disposition="integrity_verified", report_bytes=None, **over):
    f = {"run_id": RID, "disposition": disposition, "published_digest": H,
         "report_bytes_sha256": (hashlib.sha256(report_bytes).hexdigest()
                                 if report_bytes is not None else H),
         "durability_warnings": [], "utc": "T"}
    f.update(over)
    return _frame(event, **f)


def _f_failed(**over):
    f = {"run_id": RID, "error_type": "B0RunError", "error": "boom", "utc": "T"}
    f.update(over)
    return _frame("failed", **f)


def _journal(tmp_path, body):
    j = tmp_path / "x.journal"
    j.write_text(body, encoding="utf-8")
    return j


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
    ed = published["execution_descriptor"]
    assert ed["scorer_id"] == SCORER_ID and ed["scorer_version"] == SCORER_VERSION
    assert ed["scorer_allowlist_digest"] == ALLOWLIST_DIGEST and ed["scorer_blob_sha256"]
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


def test_run_b0_refuses_allowlist_digest_mismatch(tmp_path):
    # The manifest binds the scorer to an allowlist by digest; a wrong digest is deny-by-default.
    out = tmp_path / "b0_report.json"
    block = {"scorer_id": SCORER_ID, "version": SCORER_VERSION, "allowlist_digest": "f" * 64}
    m = _manifest(PANEL, out, scorer_block=block)
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("allowlist_digest" in r for r in res.refusals)


def test_run_b0_refuses_scorer_id_not_in_allowlist(tmp_path):
    # No unlisted scorer, no hashed fallback: an id absent from the (correctly-bound) allowlist
    # is refused (spec §4 step 2).
    out = tmp_path / "b0_report.json"
    block = {"scorer_id": "not_reviewed", "version": SCORER_VERSION,
             "allowlist_digest": ALLOWLIST_DIGEST}
    m = _manifest(PANEL, out, scorer_block=block)
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("no allowlisted scorer" in r for r in res.refusals)


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


def test_run_b0_refuses_unpinned_scorer_block(tmp_path):
    # The scorer block is mandatory and must pin scorer_id/version/allowlist_digest (harness
    # deny-by-default); dropping allowlist_digest is a launch refusal.
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    del m["scorer"]["allowlist_digest"]
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("scorer.allowlist_digest" in r for r in res.refusals)


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
# Strict-JSON scorer-evidence custody is a BUNDLE invariant (#960 MED-5) and is tested there.
# It is deliberately NOT tested by injecting a hostile scorer through the governed run_b0: the
# governed entrypoint runs the COMMITTED scorer only (Codex #1003 BLOCKER-1) — there is no
# allowlist knob to substitute one, and re-adding a seam to test this would BE the back door.
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), object()])
def test_bundle_refuses_nonstrict_scorer_output(bad):
    b = B0EvidenceBundle(manifest_digest="a" * 64)
    with pytest.raises(EvidenceBundleError):
        b.record("p1", "gen", scorer_input={"probe": "p1"}, scorer_output={"score": bad})
    assert len(b) == 0                                   # nothing enters custody


def test_run_b0_mid_run_failure_journals_failed_terminal(tmp_path):
    # A raise inside the governed forward leaves a 'failed' terminal frame and publishes NOTHING.
    out = tmp_path / "b0_report.json"

    class _Boom:
        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            return None

        def generate(self, prompt, decoding):
            raise B0RunError("forced mid-run failure")

    with pytest.raises(B0RunError):
        _run(_manifest(PANEL, out), PANEL, _Boom(), out)
    assert not out.exists()
    events = [json.loads(x) for x in
              (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "failed"
    assert "disposition" not in events[-1]               # pre-commit terminal carries no disposition
    assert verify_terminal_frames(tmp_path / "b0_report.json.journal")["ok"] is True


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
    j = _journal(tmp_path, _f_claim() + _f_sealing() + '{"event":"comp')
    r = verify_terminal_frames(j)
    assert r["ok"] is True and r["truncated_tail"] is True


def test_verify_terminal_frames_rejects_midfile_corruption(tmp_path):
    j = _journal(tmp_path, _f_claim() + "NOT JSON\n" + _f_terminal())
    r = verify_terminal_frames(j)
    assert r["ok"] is False and r.get("corruption_at") == 1


def test_verify_terminal_frames_rejects_failed_with_committed_disposition(tmp_path):
    # #975 P1: a 'failed' terminal carrying a committed disposition is impossible/tampered.
    j = _journal(tmp_path, _f_claim() + _f_sealing()
                 + _f_failed(disposition="integrity_verified"))
    r = verify_terminal_frames(j)
    assert r["ok"] is False and "committed disposition" in r["reason"]


def test_verify_terminal_frames_rejects_disposition_mismatch(tmp_path):
    # #975: a committed terminal whose disposition disagrees with its event is rejected.
    j = _journal(tmp_path, _f_claim() + _f_sealing()
                 + _f_terminal("completed", disposition="committed_indeterminate"))
    r = verify_terminal_frames(j)
    assert r["ok"] is False and "disposition must be" in r["reason"]


def test_verify_terminal_frames_rejects_terminal_missing_run_id(tmp_path):
    # #975: claim/sealing/terminal must carry a run_id.
    j = _journal(tmp_path, _f_claim() + _f_sealing() + _drop(_f_terminal(), "run_id"))
    r = verify_terminal_frames(j)
    assert r["ok"] is False and "missing run_id" in r["reason"]


def test_run_b0_rejects_tampered_failed_terminal(tmp_path, monkeypatch):
    # #975 P1 full-run canary: a same-inode co-writer flips the completed frame's event to
    # 'failed' while keeping disposition=integrity_verified. The impossible pair must be
    # rejected -> committed_indeterminate, NOT ok=True.
    import p5_b0_run as mod
    out = tmp_path / "b0_report.json"

    def tamper(self, obj):
        bad = dict(obj)
        bad["event"] = "failed"                          # keep disposition=integrity_verified
        line = (json.dumps(bad, sort_keys=True, allow_nan=False,
                           ensure_ascii=True) + "\n").encode("utf-8")
        mod._write_all(self._fd, line)
        os.fsync(self._fd)
        return "synced"

    monkeypatch.setattr(mod._Journal, "write_terminal_frame", tamper)
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.ok is False and res.terminal_state == "committed_indeterminate"
    events = [json.loads(x) for x in
              (tmp_path / "b0_report.json.journal").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "failed"               # tampered frame on disk, result rejected


def test_verify_terminal_frames_rejects_event_after_sealing(tmp_path):
    # round-7 RESIDUAL-A: an injected non-terminal frame between sealing and the terminal frame
    # is rejected (the prefix digest, pre-sealing only, cannot see it).
    j = _journal(tmp_path, _f_claim() + _f_sealing() + _f_attempt() + _f_terminal())
    r = verify_terminal_frames(j)
    assert r["ok"] is False and "after the sealing frame" in r["reason"]


@pytest.mark.parametrize("body,reason_sub", [
    ("", "empty"),
    (_f_attempt(), "not 'claim'"),
    (_f_claim() + _f_sealing(), "without a terminal"),
    (_f_claim() + _f_failed() + _f_terminal(), "more than one terminal"),
    (_f_claim() + _f_terminal(), "without a preceding 'sealing'"),
    (_f_claim() + _f_sealing(run_id="x") + _f_terminal(), "run_id inconsistent"),
])
def test_verify_terminal_frames_contract_violations(tmp_path, body, reason_sub):
    j = _journal(tmp_path, body)
    r = verify_terminal_frames(j)
    assert r["ok"] is False and reason_sub in r["reason"]


# --- protected-sink attestation (item-1a pre-run refusal) ---
def test_run_b0_refuses_without_protected_sink_attestation(tmp_path):
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    del m["evidence_sink"]["protected_sink_attestation"]
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any("protected_sink_attestation" in r for r in res.refusals)


# --- reviewed-scorer allowlist: content-first load (spec §4) ---
def test_load_allowlisted_scorer_happy(tmp_path):
    src = "def score(probe_id, generation):\n    return ({'p': probe_id}, {'v': 1})\n"
    allow_path, block = _write_scorer_allowlist(tmp_path, src)
    fn, binding, refusals = load_allowlisted_scorer({"scorer": block}, allow_path)
    assert refusals == [] and callable(fn)
    assert fn("p1", "g") == ({"p": "p1"}, {"v": 1})
    assert binding["scorer_id"] == SCORER_ID and binding["allowlist_digest"] == block["allowlist_digest"]


def test_load_allowlisted_scorer_blob_mismatch_refused(tmp_path):
    # The module bytes do not hash to the entry's blob_sha256 -> not the reviewed bytes.
    src = "def score(probe_id, generation):\n    return ({}, {})\n"
    allow_path, block = _write_scorer_allowlist(tmp_path, src, blob_override="a" * 64)
    fn, _binding, refusals = load_allowlisted_scorer({"scorer": block}, allow_path)
    assert fn is None and any("not the reviewed bytes" in r for r in refusals)


def test_load_allowlisted_scorer_non_function_entrypoint_refused(tmp_path):
    # An entrypoint that resolves to a non-function (a bare value) is refused.
    src = "score = 42\n"
    allow_path, block = _write_scorer_allowlist(tmp_path, src)
    fn, _binding, refusals = load_allowlisted_scorer({"scorer": block}, allow_path)
    assert fn is None and any("not resolve to a plain function" in r for r in refusals)


def test_load_allowlisted_scorer_forbidden_import_refused(tmp_path):
    # A reviewed scorer imports nothing; a forbidden import fired during exec (here via an audit
    # event, without leaving the module loaded) is a review-contract violation -> refused.
    src = ("import sys\n"
           "sys.audit('import', 'mamba_ssm', None, None, None, None)\n"
           "def score(probe_id, generation):\n    return ({}, {})\n")
    allow_path, block = _write_scorer_allowlist(tmp_path, src)
    fn, _binding, refusals = load_allowlisted_scorer({"scorer": block}, allow_path)
    assert fn is None and any("IMPORTED during scorer module load" in r for r in refusals)
    assert "mamba_ssm" not in sys.modules


def test_load_allowlisted_scorer_absolute_module_path_refused(tmp_path):
    # Codex #1000 BLOCKER-1: module_path must be relative to the committed allowlist dir.
    src = "def score(probe_id, generation):\n    return ({}, {})\n"
    allow_path, block = _write_scorer_allowlist(
        tmp_path, src, module_path=str(tmp_path / "custom_scorer.py"))
    fn, _binding, refusals = load_allowlisted_scorer({"scorer": block}, allow_path)
    assert fn is None and any("not absolute" in r for r in refusals)


def test_load_allowlisted_scorer_traversal_module_path_refused(tmp_path):
    # Codex #1000 BLOCKER-1: a ../ escape out of the committed allowlist directory is refused,
    # so an entry cannot point the loader at arbitrary code elsewhere on the filesystem.
    sub = tmp_path / "sub"
    sub.mkdir()
    outside = tmp_path / "evil.py"
    outside.write_text("def score(probe_id, generation):\n    return ({}, {})\n", encoding="utf-8")
    blob = hashlib.sha256(outside.read_bytes()).hexdigest()
    allow = {"schema_version": "b0_scorer_allowlist_v1", "scorers": [{
        "scorer_id": SCORER_ID, "version": SCORER_VERSION, "module_path": "../evil.py",
        "entrypoint": "score", "blob_sha256": blob, "review_ref": "wc#test"}]}
    allow_path = sub / "allowlist.json"
    allow_path.write_text(json.dumps(allow), encoding="utf-8")
    block = {"scorer_id": SCORER_ID, "version": SCORER_VERSION,
             "allowlist_digest": canonical_digest(json.loads(allow_path.read_bytes()))}
    fn, _binding, refusals = load_allowlisted_scorer({"scorer": block}, allow_path)
    assert fn is None and any("escapes" in r for r in refusals)


@pytest.mark.parametrize("ref", ["PENDING-codex", "pending", "TBD", ""])
def test_load_allowlisted_scorer_unresolved_review_ref_refused(tmp_path, ref):
    # Codex #1000 BLOCKER-3: an unresolved review authority (empty/TBD/PENDING) is refused locally,
    # so a scorer whose review has not landed cannot execute even if its bytes match.
    src = "def score(probe_id, generation):\n    return ({}, {})\n"
    allow_path, block = _write_scorer_allowlist(tmp_path, src, review_ref=ref)
    fn, _binding, refusals = load_allowlisted_scorer({"scorer": block}, allow_path)
    assert fn is None and any("unresolved" in r for r in refusals)


def test_run_b0_exposes_no_allowlist_authority_knob():
    # Codex #1000 BLOCKER-1 + #1003 BLOCKER-1: the governed entrypoint must expose NO way to
    # select the allowlist — neither a public parameter NOR an assignable module-level path
    # global. A caller that supplies both the allowlist and its digest proves agreement, not
    # review. The governed path is derived inline from the module's own __file__.
    import inspect as _inspect
    assert "allowlist_path" not in _inspect.signature(run_b0).parameters
    assert not hasattr(p5_b0_run, "DEFAULT_ALLOWLIST_PATH")
    path_globals = [n for n, v in vars(p5_b0_run).items()
                    if isinstance(v, pathlib.Path) and not n.startswith("__")]
    assert path_globals == [], f"assignable path global(s) are an alternate authority: {path_globals}"


def test_run_b0_governed_run_uses_the_committed_scorer(tmp_path):
    # The governed run binds the COMMITTED reviewed scorer — its blob hash and resolved review_ref
    # appear in the published execution_descriptor, and no fixture could have substituted them.
    out = tmp_path / "b0_report.json"
    res = _run(_manifest(PANEL, out), PANEL, _backend(), out)
    assert res.ok is True
    committed = json.loads(_COMMITTED_ALLOWLIST.read_bytes())["scorers"][0]
    ed = res.report["execution_descriptor"]
    assert ed["scorer_blob_sha256"] == committed["blob_sha256"]
    assert ed["scorer_review_ref"] == committed["review_ref"]
    assert "pending" not in ed["scorer_review_ref"].lower()


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

    def truncated(path, *, report_published_digest=None, committed_report_bytes=None):
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


def test_run_b0_accounts_for_import_during_sterile_lookup(tmp_path):
    # #980 import-audit BLOCKER: a forbidden import fired by the assert_sterile ATTRIBUTE lookup
    # (malicious __getattribute__) at run entry must be accounted, not discarded by a baseline drain.
    out = tmp_path / "b0_report.json"

    class _LookupImports:
        def __getattribute__(self, name):
            if name == "assert_sterile":
                sys.audit("import", "qdrant_client", None, None, None, None)
            return object.__getattribute__(self, name)

        def descriptor(self):
            return dict(MODEL)

        def assert_sterile(self):
            return None

        def generate(self, prompt, decoding):
            raise AssertionError("must not generate")

    res = _run(_manifest(PANEL, out), PANEL, _LookupImports(), out)
    assert res.ok is False and any("assert_sterile lookup" in r for r in res.refusals)
    assert not out.exists()


def test_verify_terminal_frames_rejects_non_object_frame(tmp_path):
    # #980: a JSON array/scalar frame ('[]') must be rejected, not crash with AttributeError.
    j = _journal(tmp_path, _f_claim() + "[]\n")
    r = verify_terminal_frames(j)
    assert r["ok"] is False and "non-object" in r["reason"]


def test_verify_terminal_frames_torn_no_newline_tail(tmp_path):
    # #980: a complete terminal JSON WITHOUT its trailing newline is a torn write -> truncated,
    # not a clean 'completed' terminal.
    j = _journal(tmp_path, _f_claim() + _f_sealing() + _f_terminal().rstrip("\n"))
    r = verify_terminal_frames(j)
    assert r["truncated_tail"] is True and r["terminal"] == "sealing"


def test_verify_terminal_frames_rejects_committed_terminal_without_sealing(tmp_path):
    # #980: EVERY committed terminal (not just 'completed') needs a preceding sealing.
    j = _journal(tmp_path, _f_claim() + _f_terminal("committed_integrity_failed",
                                                    disposition="committed_integrity_failed"))
    r = verify_terminal_frames(j)
    assert r["ok"] is False and "without a preceding 'sealing'" in r["reason"]


def test_verify_terminal_frames_rejects_unknown_event(tmp_path):
    # #980: arbitrary/injected event names are rejected.
    j = _journal(tmp_path, _f_claim() + _frame("sneaky", run_id=RID) + _f_sealing())
    r = verify_terminal_frames(j)
    assert r["ok"] is False and "unknown journal event" in r["reason"]


@pytest.mark.parametrize("body,reason_sub", [
    # GPT-5.5 #1: a valid event TYPE in an invalid ORDER is rejected by the sequence grammar.
    (_f_claim() + _f_sealing() + _f_sealing() + _f_terminal(), "sealing"),      # double sealing
    (_f_claim() + _f_generated() + _f_sealing() + _f_terminal(), "out-of-order"),   # gen before attempt
    (_f_claim() + _f_attempt(0, "p0") + _f_attempt(1, "p1")
        + _f_sealing() + _f_terminal(), "out-of-order"),                        # interleaved probes
    (_f_claim() + _f_attempt() + _f_recorded()
        + _f_sealing() + _f_terminal(), "out-of-order"),                        # recorded before generated
    # Codex #1000/#1003 BLOCKER-2: order is not a contract — cycle identity is bound.
    (_f_claim() + _f_attempt(0, "p0") + _f_generated(9, "other", run_id="evil")
        + _f_recorded(0, "p0") + _f_sealing() + _f_terminal(), "identity"),     # forged mid-cycle id
    (_f_claim() + _f_cycle(1, "p1") + _f_sealing() + _f_terminal(), "ordinal"),  # first ordinal != 0
    # #1003: attempt_id must be DERIVED from the run (run_id:ordinal), not arbitrary.
    (_f_claim() + _f_attempt(0, "p0", attempt_id="not-r:0")
        + _f_sealing() + _f_terminal(), "not run-derived"),
])
def test_verify_terminal_frames_grammar_rejects(tmp_path, body, reason_sub):
    j = _journal(tmp_path, body)
    r = verify_terminal_frames(j)
    assert r["ok"] is False and reason_sub in r["reason"]


@pytest.mark.parametrize("body,reason_sub", [
    # Codex #1003 BLOCKER-2 canaries: EXACT per-frame schemas — required fields present and
    # typed, no extras, digests unconditional.
    (_drop(_f_claim(), "run_kind", "manifest_digest", "execution_descriptor_digest",
           "scorer_binding", "utc"), "missing"),                    # underspecified claim
    (_f_claim(injected="smuggled") + _f_sealing() + _f_terminal(), "unexpected field"),
    (_f_claim() + _f_attempt() + _f_generated(generation_sha256="")
        + _f_recorded() + _f_sealing() + _f_terminal(), "generation_sha256"),   # empty digest
    (_f_claim() + _f_cycle() + _drop(_f_sealing(), "published_digest")
        + _f_terminal(), "missing published_digest"),               # digest-free sealing
    (_f_claim() + _f_cycle() + _f_sealing()
        + _drop(_f_terminal(), "report_bytes_sha256"), "missing report_bytes_sha256"),
    (_f_claim() + _f_cycle() + _f_sealing()
        + _f_terminal(durability_warnings="nope"), "durability_warnings"),      # wrong type
    (_f_claim(scorer_binding={"scorer_id": "x"}) + _f_sealing() + _f_terminal(), "missing"),
    (_f_claim(scorer_binding={**_SB, "review_ref": ""}) + _f_sealing()
        + _f_terminal(), "review_ref"),                             # claim binding must be bound
    (_f_claim(run_kind="not_b0") + _f_sealing() + _f_terminal(), "run_kind"),
])
def test_verify_terminal_frames_exact_schema_rejects(tmp_path, body, reason_sub):
    j = _journal(tmp_path, body)
    r = verify_terminal_frames(j)
    assert r["ok"] is False and reason_sub in r["reason"]


def test_verify_terminal_frames_grammar_accepts_full_cycle(tmp_path):
    # A well-ordered, identity-consistent, schema-complete journal passes (two probes).
    j = _journal(tmp_path, _f_claim() + _f_cycle(0, "p0") + _f_cycle(1, "p1")
                 + _f_sealing() + _f_terminal())
    assert verify_terminal_frames(j)["ok"] is True


def test_verify_terminal_frames_binds_report_bytes(tmp_path):
    # GPT-5.5 #2: the committed terminal's report_bytes_sha256 must match the committed report bytes.
    j = _journal(tmp_path, _f_claim() + _f_sealing() + _f_terminal(report_bytes=b"REPORT"))
    assert verify_terminal_frames(j, committed_report_bytes=b"REPORT")["ok"] is True
    r = verify_terminal_frames(j, committed_report_bytes=b"TAMPERED")
    assert r["ok"] is False and "report_bytes_sha256" in r["reason"]


@pytest.mark.parametrize("att,reason_sub", [
    ({"signer": "x", "review_ref": "x"}, "digest"),
    ({"signer": "x", "review_ref": "x", "digest": "a" * 64}, "bound_path"),
    ({"signer": "x", "review_ref": "x", "digest": "nothex", "bound_path": None}, "digest"),
])
def test_run_b0_refuses_weak_attestation(tmp_path, att, reason_sub):
    # #980: an arbitrary non-placeholder string is not an attestation — require a sha256 digest
    # and a binding to the actual sink path.
    out = tmp_path / "b0_report.json"
    m = _manifest(PANEL, out)
    if "bound_path" in att and att["bound_path"] is None:
        att = {**att, "bound_path": str(out)}                # isolate the digest-format refusal
    m["evidence_sink"]["protected_sink_attestation"] = att
    res = _run(m, PANEL, _ExplodingBackend(), out)
    assert res.ok is False and any(reason_sub in r for r in res.refusals)


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

    def boom(path, *, report_published_digest=None, committed_report_bytes=None):
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


def test_ensure_import_audit_fails_closed(monkeypatch):
    # #966 HIGH-4: an install failure must report False (fail-closed), never mark installed.
    import p5_b0_run as mod

    def _boom(hook):
        raise RuntimeError("cannot install audit hook")

    monkeypatch.setattr(mod, "_audit_installed", False)
    monkeypatch.setattr(mod.sys, "addaudithook", _boom)
    assert mod._ensure_import_audit() is False
