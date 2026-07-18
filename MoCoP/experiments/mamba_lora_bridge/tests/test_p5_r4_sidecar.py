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
    _verify_record,
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
_MANIFEST_DIGEST = "a" * 64               # a canonical B0 report's manifest_digest (sha256)
_L = 3                                    # sequence length used by the synthetic-report tests


def _reseal(report, *, panel_hash=None):
    """Recompute the INNER seal digest + OUTER published_digest after a mutation, mirroring
    B0EvidenceBundle.seal() + run_b0's publication (Codex #1183 F1). Sets execution_descriptor if
    absent or if a panel_hash is given."""
    base = {k: report[k] for k in ("schema_version", "manifest_digest", "record_count", "records")}
    report["report_digest"] = canonical_digest(base)
    if panel_hash is not None or "execution_descriptor" not in report:
        report["execution_descriptor"] = {"panel_hash": panel_hash or PANEL_HASH}
    report.pop("published_digest", None)
    report["published_digest"] = canonical_digest({k: v for k, v in report.items()})
    return report


def _sealed_report(n=4, token_count=5, stop="eos", ids=None):
    """A CANONICAL B0 report (Codex #1183 F1): the inner report_digest seal() mints + the runner's
    publication fields; records carry ACTUAL generated_token_ids whose sha256 + count the validator
    cross-checks, a frozen-enum stop_reason, and an execution_descriptor.panel_hash."""
    labels = ids if ids is not None else [f"probe{i}" for i in range(n)]
    records = []
    for i, pid in enumerate(labels):
        gen_ids = list(range(1000 * (i + 1), 1000 * (i + 1) + token_count))   # token_count ints
        records.append({
            "probe_id": pid,
            "raw_generation": f"gen{i}",
            "provenance": {
                "input_token_ids_sha256": canonical_digest(f"in{i}"),
                "generated_token_ids": gen_ids,
                "generated_token_ids_sha256": canonical_digest(gen_ids),
                "token_count": len(gen_ids),
                "stop_reason": stop,
            },
        })
    report = {"schema_version": "b0-evidence-bundle-v1", "manifest_digest": _MANIFEST_DIGEST,
              "record_count": len(labels), "records": records}
    return _reseal(report, panel_hash=PANEL_HASH)


def _set_record(report, i, *, tokens=None, stop=None, raw=None):
    """Mutate a record consistently (generated_token_ids drive token_count + sha256). Caller re-seals
    unless testing staleness."""
    prov = report["records"][i]["provenance"]
    if tokens is not None:
        gen_ids = list(range(90000, 90000 + tokens))
        prov["generated_token_ids"] = gen_ids
        prov["generated_token_ids_sha256"] = canonical_digest(gen_ids)
        prov["token_count"] = tokens
    if stop is not None:
        prov["stop_reason"] = stop
    if raw is not None:
        report["records"][i]["raw_generation"] = raw
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
                     "jsd": jsd, "cosine_similarity": sim})
    jsds = [r["jsd"] for r in rows]
    sims = [r["cosine_similarity"] for r in rows]
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
        # F1f: the sidecar panel binds to the parent's execution_descriptor.panel_hash.
        "panel": report["execution_descriptor"]["panel_hash"],
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
    d = r4_decision(report, rec)
    assert d["state"] == DECISION_JSD_PROCEEDS and d["c1_authorization_permitted"] is True
    assert d["recomputed_rho"] == pytest.approx(1.0)


def test_clean_manifest_validates():
    assert validate_sidecar_manifest(_manifest(_sealed_report())) == []


# --------------------------------------------------------------------------- #
# Monk #1146 F1 — length eligibility.                                          #
# --------------------------------------------------------------------------- #
def test_short_continuations_are_a_typed_refusal_not_eligible():
    report = _sealed_report(n=5)
    _set_record(report, 0, tokens=1, raw="x")                 # token_count 1 < L
    _reseal(report)
    elig = partition_eligibility(verify_sealed_report(report), _L)
    assert "probe0" not in elig.eligible and len(elig.eligible) == 4
    assert any(r["probe_id"] == "probe0" and r["reason"] == "short_continuation"
               for r in elig.refusals)


def test_error_stop_reason_is_never_laundered_into_eligible_even_if_long():
    report = _sealed_report(n=5)
    _set_record(report, 0, stop="error")                      # long but unusable
    _reseal(report)
    elig = partition_eligibility(verify_sealed_report(report), _L)
    assert "probe0" not in elig.eligible
    assert any(r["probe_id"] == "probe0" and r["reason"] == "unusable_error"
               for r in elig.refusals)


def test_pairs_over_all_records_are_refused_when_some_are_ineligible():
    report = _sealed_report(n=5)
    _set_record(report, 4, tokens=1)                          # probe4 short
    _reseal(report)
    # Build a comparison over ALL five probes (including the short one) -> endpoint refusal.
    rows, agg = _comparison([f"probe{i}" for i in range(5)], agree=True)
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
    assert "ELIGIBLE" in str(ei.value)


def test_eligibility_is_derived_from_the_parent_not_stored_on_the_record(tmp_path):
    # rev5 (Isegrim probe): the record carries NO authoritative eligibility. It is re-derived from
    # the verified parent at every gating boundary; the PUBLISHED artifact records the DERIVED set
    # (from the verified parent), and the decision reports the derived counts.
    report = _sealed_report(n=5)
    _set_record(report, 0, stop="error")
    _reseal(report)
    rec = _build(report)
    assert "eligibility" not in rec.record                    # not stored as an authority
    out = tmp_path / "r4.json"
    publish_r4_sidecar(report, rec, out)
    artifact = json.loads(out.read_text(encoding="utf-8"))
    elig = artifact["eligibility"]                            # DERIVED at publish from the parent
    assert elig["n_eligible"] == 4 and len(elig["refusals"]) == 1
    assert artifact["decision"]["n_eligible"] == 4 and artifact["decision"]["n_refused"] == 1


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
    # Tampering a record without re-sealing trips the INNER report_digest (records are in the seal
    # base) before anything else — the report is not the one seal() minted.
    report = _sealed_report()
    m = _manifest(report)
    report["records"][0]["raw_generation"] = "TAMPERED"        # inner+outer digests now stale
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(m, sealed_report=report, per_pair=_comparison(_eligible_of(_sealed_report()))[0],
                         aggregate=_comparison(_eligible_of(_sealed_report()))[1])
    assert "not the sealed report" in str(ei.value)


def test_missing_generation_receipt_is_refused():
    # Delete a receipt field and RE-SEAL, so the report is validly sealed but the per-record receipt
    # check is what refuses it (not the digest).
    report = _sealed_report()
    del report["records"][0]["provenance"]["stop_reason"]
    _reseal(report)
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
    report = _sealed_report()
    d = r4_decision(report, _build(report, agree=False))
    assert d["state"] == DECISION_JSD_REPLACEMENT_REQUIRED
    assert d["c1_authorization_permitted"] is False
    assert d["recomputed_rho"] == pytest.approx(-1.0)


def test_below_the_sample_floor_is_incomplete_not_pass():
    # 3 eligible probes -> C(3,2)=3 pairs, below Elf's N'>=4 floor -> INCOMPLETE, no C1. An honest
    # too-few-eligible build is INCOMPLETE (a decision), NOT a refusal — the re-derivation agrees.
    report = _sealed_report(n=3)
    rec = _build(report, agree=True)
    d = r4_decision(report, rec)
    assert d["state"] == DECISION_INCOMPLETE and d["c1_authorization_permitted"] is False
    assert d["n_eligible"] == 3


def test_decision_recomputes_rho_not_the_declared_one():
    # Even a green-looking build gets its rho recomputed from the rows for the decision.
    report = _sealed_report()
    d = r4_decision(report, _build(report, agree=False))
    assert d["recomputed_rho"] < 0.7


# --------------------------------------------------------------------------- #
# rev5 REGRESSION — Isegrim's adversarial probe (2026-07-18), a confirmed P1.  #
# See MoCoP/reviews/task_155_item5_rev4_isegrim_probe_2026-07-18.md.           #
# --------------------------------------------------------------------------- #
def test_declared_eligibility_over_a_zero_eligible_parent_cannot_green_c1(tmp_path):
    """The rev4 exploit, run: a hand-built record over a REAL sealed report whose TRUE eligibility
    is 0 (every probe token_count < L => all short_continuation) DECLARES all 6 probes eligible,
    hides the 6 refusals, and carries a fabricated perfectly-agreeing per_pair over C(6,2)=15 with
    the REAL parent digest (so parent binding is intact). rev4 returned integrity_verified /
    jsd_proceeds / c1=True over ZERO eligible prompts. rev5 re-derives eligibility from the verified
    parent at every gating boundary, so the declaration buys nothing."""
    # NOTE: Isegrim's original exploit record ALSO carried a declared `eligibility` block; in rev5
    # that block is independently refused by the closed-world record-key check
    # (see test_a_record_smuggling_a_stored_eligibility_block_is_refused). Here the record carries
    # ONLY the valid keys, so it passes _verify_record and isolates the RE-DERIVATION as the guard
    # that catches a well-formed fabrication whose comparison covers non-eligible probes.
    report = _sealed_report(n=6, token_count=1)               # token_count 1 < _L (3) => all short
    assert _eligible_of(report, _L) == ()                     # TRUE eligibility is 0

    probe_ids = [f"probe{i}" for i in range(6)]
    rows, agg = _comparison(probe_ids, agree=True)            # fabricated 15-pair perfect agreement
    fabricated = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2",
                      "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": PANEL_HASH,
        "parent": {
            "b0_report_digest": report["published_digest"],   # the REAL parent digest
            "generation_output_digest": derive_generation_corpus_digest(report),
            "sequence_length": _L,
        },
        "per_pair": rows, "aggregate": agg,
    }
    man = {"schema": SIDECAR_SCHEMA, "evaluator": fabricated["evaluator"],
           "runner": fabricated["runner"], "parent": fabricated["parent"], "panel": fabricated["panel"]}
    forged = R4SidecarRecord(manifest_digest=canonical_digest(man),
                             output_digest=canonical_digest(fabricated),
                             record=_deep_freeze(fabricated))

    # The parent-FREE guard rev4 marketed against hand-built carriers is fooled: a self-consistent
    # fabrication has matching digests, a valid manifest, and a well-formed comparison. It returns.
    assert _verify_record(forged).record["parent"]["b0_report_digest"] == report["published_digest"]

    # But every parent-AWARE boundary re-derives eligibility (0) and refuses the fabricated pairs.
    with pytest.raises(R4SidecarError) as ei_dec:
        r4_decision(report, forged)
    assert "DERIVED from the bound parent" in str(ei_dec.value)
    with pytest.raises(R4SidecarError) as ei_pub:
        publish_r4_sidecar(report, forged, tmp_path / "r4.json")
    assert "DERIVED from the bound parent" in str(ei_pub.value)
    with pytest.raises(R4SidecarError):
        bind_to_parent_report(report, forged)
    assert not (tmp_path / "r4.json").exists()                # nothing was committed


def test_a_record_smuggling_a_stored_eligibility_block_is_refused(tmp_path):
    # a-Codex pre-board finding (2026-07-18): even when the per_pair matches the DERIVED eligible
    # set (so re-derivation itself passes), a hand-built record can smuggle a stale/lying nested
    # `eligibility` block. publish embeds the record VERBATIM, so an integrity_verified artifact
    # would carry contradictory evidence (nested says 0, derived top-level + decision say 4). rev6's
    # exact-key-set check (Codex #1183 F5) refuses any unexpected top-level key before any boundary.
    report = _sealed_report(n=4)                              # 4 truly-eligible probes
    rows, agg = _comparison(_eligible_of(report))            # honest, complete comparison over the 4
    smuggled = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2",
                      "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": PANEL_HASH,
        "parent": _manifest(report)["parent"],
        "per_pair": rows, "aggregate": agg,
        "eligibility": {"sequence_length": _L, "n_eligible": 0,       # the lie riding along
                        "eligible_probe_ids": [], "refusals": []},
    }
    man = {"schema": SIDECAR_SCHEMA, "evaluator": smuggled["evaluator"],
           "runner": smuggled["runner"], "parent": smuggled["parent"], "panel": smuggled["panel"]}
    forged = R4SidecarRecord(manifest_digest=canonical_digest(man),
                             output_digest=canonical_digest(smuggled),
                             record=_deep_freeze(smuggled))
    for op in (lambda: r4_decision(report, forged),
               lambda: bind_to_parent_report(report, forged),
               lambda: publish_r4_sidecar(report, forged, tmp_path / "r4.json")):
        with pytest.raises(R4SidecarError) as ei:
            op()
        assert "key set is not exact" in str(ei.value) and "eligibility" in str(ei.value)
    assert not (tmp_path / "r4.json").exists()               # nothing was committed


# --------------------------------------------------------------------------- #
# rev6 REGRESSIONS — Codex exact-source review of record #1183 (six findings). #
# See MoCoP/reviews/p5_item5_rev5_source_review_2026-07-18.md.                 #
# --------------------------------------------------------------------------- #
def _forged(record: dict):
    """Wrap a hand-built record dict as a self-consistent exact R4SidecarRecord carrier."""
    man = {k: record[k] for k in ("schema", "evaluator", "runner", "parent", "panel")}
    return R4SidecarRecord(manifest_digest=canonical_digest(man),
                           output_digest=canonical_digest(record), record=_deep_freeze(record))


def test_f1_a_forged_inner_report_digest_is_refused():
    # Codex #1183 F1: change ONLY the inner report_digest to 00.. and recompute the outer digest —
    # rev5 accepted it (never recomputed the inner seal). rev6 recomputes it over the base fields.
    report = _sealed_report()
    report["report_digest"] = "0" * 64
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items() if k != "published_digest"})
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "inner seal digest" in str(ei.value)


def test_f1_a_stop_reason_outside_the_frozen_enum_is_refused():
    # Codex #1183 F1: a backend_crashed stop_reason made records eligible in rev5 (str-only check).
    report = _sealed_report(n=4)
    _set_record(report, 0, stop="backend_crashed")
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "frozen enum" in str(ei.value)


def test_f1_a_generated_token_ids_sha_mismatch_is_refused():
    # Codex #1183 F1: the receipt sha must bind the ACTUAL token ids, not merely assert a hash.
    report = _sealed_report(n=4)
    report["records"][0]["provenance"]["generated_token_ids"] = [7, 7, 7, 7, 7]   # sha now stale
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "generated_token_ids_sha256 does not match" in str(ei.value)


def test_f1_panel_not_bound_to_parent_execution_descriptor_is_refused():
    # Codex #1183 F1: the sidecar panel must equal the parent execution_descriptor.panel_hash.
    report = _sealed_report()
    rows, agg = _comparison(_eligible_of(report))
    manifest = _manifest(report, panel="a-different-battery-label")
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(manifest, sealed_report=report, per_pair=rows, aggregate=agg)
    assert "panel_hash" in str(ei.value)


def test_f2_a_false_generation_output_digest_is_refused_at_every_boundary(tmp_path):
    # Codex #1183 F2: the generation-corpus check lived only in the builder. A hand-built record with
    # the REAL b0 digest + correct pairs but a FALSE generation_output_digest passed decision/publish
    # in rev5. rev6 re-derives it at the one parent-aware boundary.
    report = _sealed_report(n=4)
    rows, agg = _comparison(_eligible_of(report))
    forged = _forged({
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2",
                      "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": report["execution_descriptor"]["panel_hash"],
        "parent": {
            "b0_report_digest": report["published_digest"],   # REAL
            "generation_output_digest": "f" * 64,             # the lie Codex used
            "sequence_length": _L,
        },
        "per_pair": rows, "aggregate": agg,
    })
    for op in (lambda: r4_decision(report, forged),
               lambda: bind_to_parent_report(report, forged),
               lambda: publish_r4_sidecar(report, forged, tmp_path / "r4.json")):
        with pytest.raises(R4SidecarError) as ei:
            op()
        assert "generation_output_digest" in str(ei.value)
    assert not (tmp_path / "r4.json").exists()


def test_f3_publication_uses_one_snapshot_not_live_carrier_rereads(tmp_path):
    # Codex #1183 F3: a stateful sealed_report whose items() swaps the carrier's output_digest AFTER
    # the one capture must not make publication embed the swapped digest. rev6 builds link/decision/
    # artifact from the single verified snapshot, never re-reading the live carrier.
    report = _sealed_report(n=4)
    rec = _build(report)
    good = rec.output_digest
    fired = {"done": False}

    class _StatefulReport(dict):
        def items(self):
            if not fired["done"]:
                fired["done"] = True
                object.__setattr__(rec, "output_digest", "f" * 64)   # swap after capture
            return super().items()

    out = tmp_path / "r4.json"
    result = publish_r4_sidecar(_StatefulReport(report), rec, out)
    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert result.disposition == DISPOSITION_VERIFIED
    assert artifact["sidecar_output_digest"] == good
    assert artifact["link"]["sidecar_output_digest"] == good
    assert artifact["decision"]["sidecar_output_digest"] == good
    assert "f" * 64 not in json.dumps(artifact)


def test_f4_a_post_commit_readback_fault_downgrades_and_does_not_raise(tmp_path, monkeypatch):
    # Codex #1183 F4: a final-byte readback OSError escaped after os.link in rev5, leaving the
    # committed artifact + a writable .tmp alias and no disposition. rev6's post-commit region is a
    # non-throwing terminal state machine: downgrade truthfully, still remove the alias.
    report = _sealed_report()
    rec = _build(report)
    out = tmp_path / "r4.json"
    orig_read = pathlib.Path.read_bytes

    def boom(self, *a, **k):
        if str(self) == str(out):                    # only the FINAL artifact readback
            raise OSError("simulated readback failure")
        return orig_read(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "read_bytes", boom)
    result = publish_r4_sidecar(report, rec, out)    # must NOT raise
    assert result.disposition == DISPOSITION_INTEGRITY_FAILED
    assert out.exists()                              # the artifact is committed
    assert list(tmp_path.glob("*.tmp")) == []        # the writable alias was still removed


def test_f5_a_record_missing_a_key_is_a_typed_refusal_not_keyerror():
    # Codex #1183 F5: rev5's set-difference rejected extras but missing keys escaped as KeyError.
    report = _sealed_report()
    rows, agg = _comparison(_eligible_of(report))
    incomplete = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2",
                      "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": report["execution_descriptor"]["panel_hash"],
        "parent": _manifest(report)["parent"],
        "per_pair": rows,                            # NO "aggregate"
    }
    forged = R4SidecarRecord(manifest_digest="a" * 64,
                             output_digest=canonical_digest(incomplete),
                             record=_deep_freeze(incomplete))
    with pytest.raises(R4SidecarError) as ei:
        r4_decision(report, forged)
    assert "key set is not exact" in str(ei.value) and "aggregate" in str(ei.value)


def test_f5_a_scalar_record_root_is_a_typed_refusal_not_typeerror():
    forged = R4SidecarRecord(manifest_digest="a" * 64, output_digest=canonical_digest(42), record=42)
    with pytest.raises(R4SidecarError) as ei:
        r4_decision(_sealed_report(), forged)
    assert "root is not a mapping" in str(ei.value)


def test_f6_output_digest_is_invariant_to_row_order_and_endpoint_orientation():
    # Codex #1183 F6 / §5.5 line 178: rows sorted by (probe_a, probe_b), endpoints oriented, before
    # hashing. Forward and reversed-orientation versions of the same comparison hash identically.
    report = _sealed_report()
    rows, agg = _comparison(_eligible_of(report))
    fwd = build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
    reversed_rows = [{"pair_id": f'{r["probe_b"]}|{r["probe_a"]}',
                      "probe_a": r["probe_b"], "probe_b": r["probe_a"],
                      "jsd": r["jsd"], "cosine_similarity": r["cosine_similarity"]}
                     for r in reversed(rows)]
    rev = build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=reversed_rows,
                           aggregate=agg)
    assert fwd.output_digest == rev.output_digest
    assert [r["probe_a"] <= r["probe_b"] for r in fwd.record["per_pair"]] == [True] * len(rows)


def test_acodex_stop_reason_str_subclass_cannot_green_c1():
    # a-Codex pre-board (rev6): restoring the enum dropped the exact-str check, so a str subclass
    # comparing/hashing as "eos" but serialized as backend_crashed could pass, be eligible, and reach
    # c1=True. Exact-type-before-membership refuses it. Also: an unhashable value must be a typed
    # refusal, not a raw TypeError.
    class _Sneaky(str):
        def __eq__(self, other):
            return "eos" == other
        def __hash__(self):
            return hash("eos")

    report = _sealed_report(n=4)
    report["records"][0]["provenance"]["stop_reason"] = _Sneaky("backend_crashed")
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "exact str" in str(ei.value)

    report2 = _sealed_report(n=4)
    report2["records"][0]["provenance"]["stop_reason"] = ["not", "a", "str"]   # unhashable
    _reseal(report2)
    with pytest.raises(R4SidecarError):                          # typed refusal, NOT a raw TypeError
        verify_sealed_report(report2)


def test_acodex_pair_id_has_no_delimiter_collision_for_ids_containing_a_bar(tmp_path):
    # a-Codex pre-board (rev6): with UNIQUE caller pair_ids, the DERIVED f"{a}|{b}" collided for
    # probe ids containing "|" (("a","b|c") and ("a|b","c") both -> "a|b|c"), so the built record
    # failed its OWN _verify_record for a duplicate pair_id. An unambiguous encoding round-trips.
    report = _sealed_report(ids=["a", "b|c", "a|b", "c"])
    ids = sorted(_eligible_of(report))
    pairs = list(combinations(ids, 2))
    rows = []
    for idx, (a, b) in enumerate(pairs):
        jsd = round((idx + 1) / (len(pairs) + 1), 6)
        rows.append({"pair_id": f"pair-{idx}",              # UNIQUE caller ids (pass build validation)
                     "probe_a": a, "probe_b": b, "jsd": jsd, "cosine_similarity": round(1.0 - jsd, 6)})
    jsds = [r["jsd"] for r in rows]
    sims = [r["cosine_similarity"] for r in rows]
    agg = {"spearman_rho": diversity_agreement_rho(jsds, sims),
           "mean_pairwise_jsd": sum(jsds) / len(jsds),
           "mean_pairwise_embedding": sum(sims) / len(sims), "n_pairs": len(rows)}
    rec = build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
    derived = [r["pair_id"] for r in rec.record["per_pair"]]
    assert len(derived) == len(set(derived))                # DERIVED pair_ids do not collide
    result = publish_r4_sidecar(report, rec, tmp_path / "r4.json")   # round-trips through _verify_record
    assert result.disposition == DISPOSITION_VERIFIED


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
                   "cosine_similarity": None}],
        aggregate={"spearman_rho": "y", "n_pairs": 0},
        eligible_probe_ids=["a", "b"])
    assert any("pair_id" in x for x in r)
    assert any("endpoints are identical" in x for x in r)
    assert any("jsd must be in" in x for x in r)
    assert any("cosine_similarity" in x for x in r)
    assert any("spearman_rho" in x for x in r)


def test_eligibility_dataclass_shape():
    e = partition_eligibility(verify_sealed_report(_sealed_report()), _L)
    assert isinstance(e, Eligibility) and e.eligible == ("probe0", "probe1", "probe2", "probe3")
