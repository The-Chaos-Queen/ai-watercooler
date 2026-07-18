"""Model-free tests for the P5 R4 comparison sidecar (#155 item 5; rev 4, Monk #1146 A-prime).

No torch, no sentence_transformers, no model, no GPU. The evaluator is faked. Unit tests use
synthetic sealed-report dicts; the orchestration seam's happy path uses a REAL run_b0-generated
report+journal (reusing the proven B0 helpers) so the terminal-frame authority is exercised for real.
"""
import json
import pathlib
from itertools import combinations

import pytest

from p5_b0_harness import canonical_digest
from p5_r4_sidecar import (
    DECISION_INCOMPLETE,
    DECISION_JSD_PROCEEDS,
    DECISION_JSD_REPLACEMENT_REQUIRED,
    DISPOSITION_INDETERMINATE,
    DISPOSITION_INTEGRITY_FAILED,
    DISPOSITION_VERIFIED,
    SIDECAR_SCHEMA,
    Eligibility,
    R4RecordResult,
    R4SidecarError,
    R4SidecarRecord,
    _deep_freeze,
    bind_to_parent_report,
    build_r4_sidecar,
    derive_generation_corpus_digest,
    diversity_agreement_rho,
    partition_eligibility,
    publish_r4_sidecar,
    r4_decision,
    record_r4_comparison,
    validate_comparison,
    validate_sidecar_manifest,
    verify_sealed_report,
)

# Reuse the proven B0 run helpers for a genuine report+journal (integrity_verified). If the sibling
# test module is not importable in this collection, the seam happy-path is skipped, not failed.
try:
    from test_p5_b0_run import _backend as _b0_backend
    from test_p5_b0_run import _manifest as _b0_manifest
    from test_p5_b0_run import _run as _b0_run
    _HAVE_B0 = True
except Exception:  # noqa: BLE001
    _HAVE_B0 = False

PANEL_HASH = "primary-holdout-ff5e596304c6b8c4b93c"
EVAL_SHA = "c" * 40
_L = 3                                    # sequence length used by the synthetic-report tests


def _sealed_report(n=4, token_count=5, stop="eos"):
    """A synthetic sealed B0 report: n probes, each with a full generation receipt (token_count>=L)."""
    records = []
    for i in range(n):
        records.append({
            "probe_id": f"probe{i}",
            "raw_generation": f"gen{i}",
            "provenance": {
                "input_token_ids_sha256": canonical_digest(f"in{i}"),
                "generated_token_ids_sha256": canonical_digest(f"out{i}"),
                "token_count": token_count,
                "stop_reason": stop,
            },
        })
    report = {"schema_version": "b0-evidence-bundle-v1", "record_count": n, "records": records}
    report["published_digest"] = canonical_digest({k: v for k, v in report.items()})
    return report


def _eligible_of(report, L=_L):
    return partition_eligibility(verify_sealed_report(report), L).eligible


def _comparison(probe_ids, *, agree=True):
    """A complete, self-consistent comparison over probe_ids. agree -> rho=+1, else rho=-1."""
    ids = sorted(probe_ids)
    pairs = list(combinations(ids, 2))
    rows = []
    for idx, (a, b) in enumerate(pairs):
        jsd = round((idx + 1) / (len(pairs) + 1), 6)
        sim = round(1.0 - jsd, 6) if agree else round(jsd, 6)
        rows.append({"pair_id": f"{a}|{b}", "probe_a": a, "probe_b": b,
                     "jsd": jsd, "embedding_similarity": sim})
    jsds = [r["jsd"] for r in rows]
    sims = [r["embedding_similarity"] for r in rows]
    agg = {"spearman_rho": diversity_agreement_rho(jsds, sims),
           "mean_pairwise_jsd": sum(jsds) / len(jsds),
           "mean_pairwise_embedding": sum(sims) / len(sims),
           "n_pairs": len(rows)}
    return rows, agg


def _manifest(report, L=_L, **over):
    m = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2",
                      "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "parent": {
            "b0_report_digest": report["published_digest"],
            "generation_output_digest": derive_generation_corpus_digest(report),
            "sequence_length": L,
        },
        "panel": PANEL_HASH,
    }
    m.update(over)
    return m


def _build(report=None, L=_L, agree=True):
    report = report or _sealed_report()
    rows, agg = _comparison(_eligible_of(report, L), agree=agree)
    return build_r4_sidecar(_manifest(report, L), sealed_report=report, per_pair=rows, aggregate=agg)


# --------------------------------------------------------------------------- #
# Happy path + decision.                                                       #
# --------------------------------------------------------------------------- #
def test_clean_build_binds_and_decides_proceeds():
    report = _sealed_report()
    rec = _build(report, agree=True)
    assert len(rec.output_digest) == 64
    link = bind_to_parent_report(report, rec)
    assert link["b0_published_digest"] == report["published_digest"]
    d = r4_decision(rec)
    assert d["state"] == DECISION_JSD_PROCEEDS and d["c1_authorization_permitted"] is True
    assert d["recomputed_rho"] == pytest.approx(1.0)


def test_clean_manifest_validates():
    assert validate_sidecar_manifest(_manifest(_sealed_report())) == []


# --------------------------------------------------------------------------- #
# Monk #1146 F1 — length eligibility.                                          #
# --------------------------------------------------------------------------- #
def test_short_continuations_are_a_typed_refusal_not_eligible():
    report = _sealed_report(n=5)
    report["records"][0]["provenance"]["token_count"] = 1     # < L
    report["records"][0]["raw_generation"] = "x"
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items() if k != "published_digest"})
    elig = partition_eligibility(verify_sealed_report(report), _L)
    assert "probe0" not in elig.eligible and len(elig.eligible) == 4
    assert any(r["probe_id"] == "probe0" and r["reason"] == "short_continuation"
               for r in elig.refusals)


def test_error_stop_reason_is_never_laundered_into_eligible_even_if_long():
    report = _sealed_report(n=5)
    report["records"][0]["provenance"]["stop_reason"] = "error"   # long but unusable
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items() if k != "published_digest"})
    elig = partition_eligibility(verify_sealed_report(report), _L)
    assert "probe0" not in elig.eligible
    assert any(r["probe_id"] == "probe0" and r["reason"] == "unusable_error"
               for r in elig.refusals)


def test_pairs_over_all_records_are_refused_when_some_are_ineligible():
    report = _sealed_report(n=5)
    report["records"][4]["provenance"]["token_count"] = 1        # probe4 short
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items() if k != "published_digest"})
    # Build a comparison over ALL five probes (including the short one) -> endpoint refusal.
    rows, agg = _comparison([f"probe{i}" for i in range(5)], agree=True)
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
    assert "ELIGIBLE" in str(ei.value)


def test_eligibility_is_recorded_in_the_sidecar():
    report = _sealed_report(n=5)
    report["records"][0]["provenance"]["stop_reason"] = "error"
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items() if k != "published_digest"})
    rec = _build(report)
    elig = rec.record["eligibility"]
    assert elig["n_eligible"] == 4 and len(elig["refusals"]) == 1


# --------------------------------------------------------------------------- #
# Monk #1146 F2/F3 — the parent report must be structurally verified.          #
# --------------------------------------------------------------------------- #
def test_a_merely_self_hashed_arbitrary_mapping_is_rejected():
    junk = {"anything": 1}
    junk["published_digest"] = canonical_digest({k: v for k, v in junk.items()})
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(junk)
    assert "schema_version" in str(ei.value)


def test_wrong_record_count_is_refused():
    report = _sealed_report()
    report["record_count"] = 999
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items() if k != "published_digest"})
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "record_count" in str(ei.value)


def test_a_modified_report_with_a_stale_digest_is_refused():
    report = _sealed_report()
    m = _manifest(report)
    report["records"][0]["raw_generation"] = "TAMPERED"        # digest now stale
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(m, sealed_report=report, per_pair=_comparison(_eligible_of(_sealed_report()))[0],
                         aggregate=_comparison(_eligible_of(_sealed_report()))[1])
    assert "modified since sealing" in str(ei.value)


def test_missing_generation_receipt_is_refused():
    report = _sealed_report()
    del report["records"][0]["provenance"]["stop_reason"]
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items() if k != "published_digest"})
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "receipt" in str(ei.value)


def test_generation_digest_binds_raw_text():
    a = _sealed_report()
    b = _sealed_report()
    b["records"][0]["raw_generation"] = "different text"
    assert derive_generation_corpus_digest(a) != derive_generation_corpus_digest(b)


# --------------------------------------------------------------------------- #
# The fail-closed C1-precondition decision.                                   #
# --------------------------------------------------------------------------- #
def test_disagreement_requires_jsd_replacement_and_denies_c1():
    d = r4_decision(_build(agree=False))
    assert d["state"] == DECISION_JSD_REPLACEMENT_REQUIRED
    assert d["c1_authorization_permitted"] is False
    assert d["recomputed_rho"] == pytest.approx(-1.0)


def test_below_the_sample_floor_is_incomplete_not_pass():
    # 3 eligible probes -> C(3,2)=3 pairs, below Elf's N'>=4 floor -> INCOMPLETE, no C1.
    rec = _build(_sealed_report(n=3), agree=True)
    d = r4_decision(rec)
    assert d["state"] == DECISION_INCOMPLETE and d["c1_authorization_permitted"] is False
    assert d["n_eligible"] == 3


def test_decision_recomputes_rho_not_the_declared_one():
    # Even a green-looking build gets its rho recomputed from the rows for the decision.
    rec = _build(agree=False)
    d = r4_decision(rec)
    assert d["recomputed_rho"] < 0.7


# --------------------------------------------------------------------------- #
# Monk #1146 F4 — exact-type + revalidate at every public boundary.           #
# --------------------------------------------------------------------------- #
def test_a_non_exact_record_type_cannot_bind():
    class _Sub(R4SidecarRecord):
        pass
    rec = _build()
    forged = _Sub(manifest_digest=rec.manifest_digest, output_digest=rec.output_digest,
                  record=rec.record)
    with pytest.raises(R4SidecarError) as ei:
        bind_to_parent_report(_sealed_report(), forged)
    assert "exact R4SidecarRecord" in str(ei.value)


def test_a_stale_output_digest_cannot_bind():
    rec = _build()
    forged = R4SidecarRecord(manifest_digest=rec.manifest_digest, output_digest="0" * 64,
                             record=rec.record)
    with pytest.raises(R4SidecarError) as ei:
        bind_to_parent_report(_sealed_report(), forged)
    assert "output_digest does not match" in str(ei.value)


def test_a_semantically_invalid_record_cannot_bind_even_with_consistent_digests():
    # A record whose evaluator revision is a MUTABLE ref, hand-built with self-consistent digests.
    # Digest consistency is not enough: bind RE-VALIDATES the manifest semantics (Codex #1144 F3).
    report = _sealed_report()
    rows, agg = _comparison(_eligible_of(report))
    bad = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "x", "revision_sha": "main"},   # mutable ref
        "runner": {"runner_id": "r", "runner_digest": "d" * 64},
        "panel": PANEL_HASH,
        "parent": _manifest(report)["parent"],
        "eligibility": {"sequence_length": _L, "n_eligible": len(_eligible_of(report)),
                        "eligible_probe_ids": list(_eligible_of(report)), "refusals": []},
        "per_pair": rows, "aggregate": agg,
    }
    man = {"schema": SIDECAR_SCHEMA, "evaluator": bad["evaluator"], "runner": bad["runner"],
           "parent": bad["parent"], "panel": bad["panel"]}
    forged = R4SidecarRecord(manifest_digest=canonical_digest(man),
                             output_digest=canonical_digest(bad), record=_deep_freeze(bad))
    with pytest.raises(R4SidecarError) as ei:
        bind_to_parent_report(report, forged)
    assert "re-validation" in str(ei.value) and "revision_sha" in str(ei.value)


# --------------------------------------------------------------------------- #
# Monk #1146 F5 — truthful publication disposition.                           #
# --------------------------------------------------------------------------- #
def test_publish_happy_is_integrity_verified_and_leaves_no_temp(tmp_path):
    report = _sealed_report()
    rec = _build(report)
    out = tmp_path / "r4.json"
    result = publish_r4_sidecar(report, rec, out)
    assert result.disposition == DISPOSITION_VERIFIED
    assert out.exists() and list(tmp_path.glob("*.tmp")) == []
    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["decision"]["state"] == DECISION_JSD_PROCEEDS
    assert artifact["link"]["b0_published_digest"] == report["published_digest"]
    assert "sidecar" not in json.dumps(report)                # parent never mutated


def test_publish_is_no_replace(tmp_path):
    report = _sealed_report()
    rec = _build(report)
    out = tmp_path / "r4.json"
    publish_r4_sidecar(report, rec, out)
    with pytest.raises(R4SidecarError) as ei:
        publish_r4_sidecar(report, rec, out)
    assert "no-replace" in str(ei.value)


def test_a_surviving_writable_alias_is_committed_integrity_failed_not_success(tmp_path, monkeypatch):
    # If the post-link temp cannot be removed, a writable hard-link alias survives on the final
    # artifact. That is committed_integrity_failed, never ordinary success (Monk #1146 F5).
    report = _sealed_report()
    rec = _build(report)
    out = tmp_path / "r4.json"
    orig = pathlib.Path.unlink

    def boom(self, *a, **k):
        if str(self).endswith(".tmp"):
            raise OSError("simulated alias-cleanup failure")
        return orig(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "unlink", boom)
    result = publish_r4_sidecar(report, rec, out)             # must NOT raise
    assert result.disposition == DISPOSITION_INTEGRITY_FAILED
    assert out.exists()                                       # the artifact is committed


def test_a_durability_fault_is_committed_indeterminate(tmp_path, monkeypatch):
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_fsync_dir", lambda d: False)
    report = _sealed_report()
    rec = _build(report)
    result = publish_r4_sidecar(report, rec, tmp_path / "r4.json")
    assert result.disposition == DISPOSITION_INDETERMINATE


# --------------------------------------------------------------------------- #
# Monk #1146 — the production-callable seam. Governed evidence PATHS only.      #
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _HAVE_B0, reason="B0 run helpers not importable in this collection")
def test_seam_happy_path_over_a_real_governed_b0_artifact(tmp_path):
    panel = [(f"probe{i}", f"prompt {i}") for i in range(4)]
    out = tmp_path / "b0_report.json"
    res = _b0_run(_b0_manifest(panel, out), panel, _b0_backend(), out)
    assert res.ok and res.terminal_state == "integrity_verified"
    journal = pathlib.Path(str(out) + ".journal")
    report = json.loads(out.read_text(encoding="utf-8"))

    L = 2                                                     # scripted continuations are ~2 tokens
    elig = _eligible_of(report, L)
    assert len(elig) == 4
    rows, agg = _comparison(elig, agree=True)
    manifest = _manifest(report, L)
    r4_out = tmp_path / "r4_sidecar.json"
    result = record_r4_comparison(report_path=out, journal_path=journal, manifest=manifest,
                                  per_pair=rows, aggregate=agg, sidecar_path=r4_out)
    assert isinstance(result, R4RecordResult)
    assert result.ok is True                                 # authority verified + proceeds
    assert result.decision["state"] == DECISION_JSD_PROCEEDS
    assert r4_out.exists()


def test_seam_refuses_an_absent_report(tmp_path):
    report = _sealed_report()
    rows, agg = _comparison(_eligible_of(report))
    with pytest.raises(R4SidecarError) as ei:
        record_r4_comparison(report_path=tmp_path / "nope.json",
                             journal_path=tmp_path / "nope.json.journal",
                             manifest=_manifest(report), per_pair=rows, aggregate=agg,
                             sidecar_path=tmp_path / "r4.json")
    assert "not found" in str(ei.value)


def test_seam_refuses_a_malformed_report(tmp_path):
    rp = tmp_path / "b0.json"
    rp.write_text("this is not json", encoding="utf-8")
    jp = tmp_path / "b0.json.journal"
    jp.write_text("", encoding="utf-8")
    report = _sealed_report()
    rows, agg = _comparison(_eligible_of(report))
    with pytest.raises(R4SidecarError) as ei:
        record_r4_comparison(report_path=rp, journal_path=jp, manifest=_manifest(report),
                             per_pair=rows, aggregate=agg, sidecar_path=tmp_path / "r4.json")
    assert "not valid JSON" in str(ei.value)


def test_seam_refuses_a_journal_that_fails_to_verify(tmp_path):
    # A well-formed sealed report, but the journal does not verify (empty) -> ok=False path.
    report = _sealed_report()
    rp = tmp_path / "b0.json"
    rp.write_text(json.dumps(report), encoding="utf-8")
    jp = tmp_path / "b0.json.journal"
    jp.write_text("", encoding="utf-8")
    rows, agg = _comparison(_eligible_of(report))
    with pytest.raises(R4SidecarError) as ei:
        record_r4_comparison(report_path=rp, journal_path=jp, manifest=_manifest(report),
                             per_pair=rows, aggregate=agg, sidecar_path=tmp_path / "r4.json")
    assert "did not verify" in str(ei.value)


@pytest.mark.parametrize("disp", ["committed_integrity_failed", "committed_indeterminate", "refused"])
def test_seam_refuses_a_verified_journal_whose_terminal_authority_is_not_integrity_verified(
        tmp_path, monkeypatch, disp):
    # The DISPOSITION gate specifically: the journal parses/verifies (ok=True) but its terminal
    # authority is not integrity_verified. No C1 authorization may rest on that (Monk #1146). This
    # isolates the disposition check, which the empty-journal (ok=False) case does not reach.
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "verify_terminal_frames",
                        lambda *a, **k: {"ok": True, "disposition": disp})
    report = _sealed_report()
    rp = tmp_path / "b0.json"
    rp.write_text(json.dumps(report), encoding="utf-8")
    jp = tmp_path / "b0.json.journal"
    jp.write_text("{}\n", encoding="utf-8")
    rows, agg = _comparison(_eligible_of(report))
    with pytest.raises(R4SidecarError) as ei:
        record_r4_comparison(report_path=rp, journal_path=jp, manifest=_manifest(report),
                             per_pair=rows, aggregate=agg, sidecar_path=tmp_path / "r4.json")
    assert "terminal authority" in str(ei.value)


# --------------------------------------------------------------------------- #
# Scope lock (Monk #1128/#1146): out-of-process, no evaluator/torch import.     #
# --------------------------------------------------------------------------- #
def test_sidecar_imports_no_evaluator_and_no_torch():
    import sys

    import p5_r4_sidecar  # noqa: F401
    bad = [m for m in sys.modules
           if m.split(".")[0] in ("torch", "sentence_transformers", "transformers", "numpy")]
    assert bad == []


def test_sidecar_source_never_constructs_the_evaluator():
    import inspect

    import p5_r4_sidecar
    src = inspect.getsource(p5_r4_sidecar)
    assert "import sentence_transformers" not in src
    assert "SentenceTransformer(" not in src


def test_partition_rejects_a_bad_sequence_length():
    with pytest.raises(R4SidecarError):
        partition_eligibility(verify_sealed_report(_sealed_report()), 0)


def test_validate_comparison_standalone_accumulates_faults():
    # Public: the out-of-process runner can self-check before the custody boundary; faults accumulate.
    r = validate_comparison(
        per_pair=[{"pair_id": "", "probe_a": "a", "probe_b": "a", "jsd": 5.0,
                   "embedding_similarity": None}],
        aggregate={"spearman_rho": "y", "n_pairs": 0},
        eligible_probe_ids=["a", "b"])
    assert any("pair_id" in x for x in r)
    assert any("endpoints are identical" in x for x in r)
    assert any("jsd must be in" in x for x in r)
    assert any("embedding_similarity" in x for x in r)
    assert any("spearman_rho" in x for x in r)


def test_eligibility_dataclass_shape():
    e = partition_eligibility(verify_sealed_report(_sealed_report()), _L)
    assert isinstance(e, Eligibility) and e.eligible == ("probe0", "probe1", "probe2", "probe3")
