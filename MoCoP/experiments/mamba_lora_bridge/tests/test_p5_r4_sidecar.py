"""Model-free tests for the P5 R4 comparison sidecar (#155 item 5; rev 4, Monk #1146 A-prime).

No torch, no sentence_transformers, no model, no GPU. The evaluator is faked. Unit tests use
synthetic sealed-report dicts; the orchestration seam's happy path uses a REAL run_b0-generated
report+journal (reusing the proven B0 helpers) so the terminal-frame authority is exercised for real.
"""
import json
import os
import pathlib
import re
import sys
from itertools import combinations

import pytest

from p5_b0_harness import canonical_digest, check_decoding_contract
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
    _canonicalize_comparison,
    _verify_record,
    bind_to_parent_report,
    build_r4_sidecar,
    _derive_generation_corpus_digest,
    _diversity_agreement_rho,
    _partition_eligibility,
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

PANEL_HASH = canonical_digest("primary-holdout-panel")   # a real sha256 (F1c: panel_hash is a digest)
EVAL_SHA = "c" * 40
_MANIFEST_DIGEST = "a" * 64               # a canonical B0 report's manifest_digest (sha256)
_L = 3                                    # sequence length used by the synthetic-report tests

# The pinned B0 neutralization set exactly as run_b0 emits it into execution_descriptor.decoding
# (the effective generate kwargs, no "hash" meta-key): 8 required-explicit + 5 pinned-inert, values
# fixed. decoding_hash is canonical_digest(decoding), matching run_b0 (~line 1900). Self-checked, so
# any drift in the frozen contract fails HERE, loudly, not obscurely downstream.
_DECODING = {
    "do_sample": False, "num_beams": 1, "max_new_tokens": 160, "min_new_tokens": 0,
    "repetition_penalty": 1.0, "no_repeat_ngram_size": 0, "eos_token_id": 1, "pad_token_id": 0,
    "temperature": 1.0, "top_p": 1.0, "top_k": 0, "length_penalty": 1.0, "early_stopping": False,
}
assert check_decoding_contract({"decoding": _DECODING}) == []
_DECODING_HASH = canonical_digest(_DECODING)


def _exec_descriptor(panel_hash=PANEL_HASH):
    """The EXACT 18-key canonical execution_descriptor (Codex #1187 F1), manifest authorities equal."""
    return {
        "panel_hash": panel_hash,
        "model": {"id": "gemma", "revision": "r", "dtype": "bf16", "backend": "hf",
                  "device": "cuda:0", "device_map": "cuda:0", "attention": "sdpa", "use_cache": False},
        "decoding": dict(_DECODING),
        "decoding_hash": _DECODING_HASH,
        "scorer_id": "scorer", "scorer_version": "1", "scorer_blob_sha256": "e" * 64,
        "scorer_allowlist_digest": "f" * 64, "scorer_review_ref": "review#1",
        "rubric_version": "rv1", "processor_revision": "0" * 40, "runtime_hash": "b" * 64,
        "runner_digest": "d" * 64, "schema_variant": "closed_world_b0", "base_manifest_id": "base#1",
        "run_kind": "b0_baseline",
        "base_manifest_digest": _MANIFEST_DIGEST, "manifest_digest": _MANIFEST_DIGEST,
    }


def _reseal(report):
    """Recompute the INNER seal digest + OUTER published_digest after a mutation, mirroring
    B0EvidenceBundle.seal() + run_b0's publication."""
    base = {k: report[k] for k in ("schema_version", "manifest_digest", "record_count", "records")}
    report["report_digest"] = canonical_digest(base)
    report.pop("published_digest", None)
    report["published_digest"] = canonical_digest({k: v for k, v in report.items()})
    return report


def _record(pid, i, *, token_count=5, stop="eos"):
    """One CANONICAL producer record: exact 6-key shape, 9-key provenance, EOS-consistent receipt."""
    gen_ids = list(range(1000 * (i + 1), 1000 * (i + 1) + token_count))
    return {
        "probe_id": pid, "raw_generation": f"gen{i}",
        "scorer_input": None, "scorer_output": None, "ordinal": i,
        "provenance": {
            "prompt_sha256": canonical_digest(f"prompt{i}"),
            "attempt_id": f"attempt-{i}",
            "input_token_ids_sha256": canonical_digest(f"in{i}"),
            "generated_token_ids": gen_ids,
            "generated_token_ids_sha256": canonical_digest(gen_ids),
            "token_count": len(gen_ids),
            "stop_reason": stop,
            "eos_token_id_fired": (gen_ids[-1] if stop == "eos" and gen_ids else None),
            "wall_time_ms": 12.5,
        },
    }


def _sealed_report(n=4, token_count=5, stop="eos", ids=None, panel_hash=PANEL_HASH):
    """A CANONICAL B0 report (Codex #1183/#1187 F1): the EXACT producer top-level (12 keys) / record
    (6) / provenance (9) / execution_descriptor (18) shapes, manifest-authority equality, and real
    generated_token_ids whose sha256 + count + EOS custody the validator cross-checks."""
    labels = ids if ids is not None else [f"probe{i}" for i in range(n)]
    records = [_record(pid, i, token_count=token_count, stop=stop) for i, pid in enumerate(labels)]
    report = {
        "schema_version": "b0-evidence-bundle-v1",
        "manifest_digest": _MANIFEST_DIGEST,
        "record_count": len(labels),
        "records": records,
        "run_kind": "b0_baseline",
        "schema_variant": "closed_world_b0",
        "base_manifest_id": "base#1",
        "execution_descriptor": _exec_descriptor(panel_hash),
        "terminal_state": "committed",
        "journal_digest": "c" * 64,
    }
    return _reseal(report)


def _set_record(report, i, *, tokens=None, stop=None, raw=None):
    """Mutate a record consistently (generated_token_ids drive token_count + sha256; EOS custody kept
    in step with the resulting stop_reason). Caller re-seals unless testing staleness."""
    prov = report["records"][i]["provenance"]
    if tokens is not None:
        gen_ids = list(range(90000, 90000 + tokens))
        prov["generated_token_ids"] = gen_ids
        prov["generated_token_ids_sha256"] = canonical_digest(gen_ids)
        prov["token_count"] = tokens
    if stop is not None:
        prov["stop_reason"] = stop
    gids = prov["generated_token_ids"]
    prov["eos_token_id_fired"] = gids[-1] if prov["stop_reason"] == "eos" and gids else None
    if raw is not None:
        report["records"][i]["raw_generation"] = raw
    return report


def _eligible_of(report, L=_L):
    return _partition_eligibility(verify_sealed_report(report), L).eligible


def _comparison(probe_ids, *, agree=True):
    """A complete §5.5 INPUT comparison over probe_ids (NO caller pair_id — §5.5 line 170-178).
    agree -> rho=+1, else rho=-1. An empty eligible set yields an empty comparison + zero aggregate."""
    ids = sorted(probe_ids)
    pairs = list(combinations(ids, 2))
    rows = []
    for idx, (a, b) in enumerate(pairs):
        jsd = round((idx + 1) / (len(pairs) + 1), 6)
        sim = round(1.0 - jsd, 6) if agree else round(jsd, 6)
        rows.append({"probe_a": a, "probe_b": b, "jsd": jsd, "cosine_similarity": sim})
    if not rows:
        return rows, {"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0,
                      "mean_pairwise_embedding": 0.0, "n_pairs": 0}
    jsds = [r["jsd"] for r in rows]
    sims = [r["cosine_similarity"] for r in rows]
    agg = {"spearman_rho": _diversity_agreement_rho(jsds, sims),
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
            "generation_output_digest": _derive_generation_corpus_digest(report),
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
    elig = _partition_eligibility(verify_sealed_report(report), _L)
    assert "probe0" not in elig.eligible and len(elig.eligible) == 4
    assert any(r["probe_id"] == "probe0" and r["reason"] == "short_continuation"
               for r in elig.refusals)


def test_error_stop_reason_is_never_laundered_into_eligible_even_if_long():
    report = _sealed_report(n=5)
    _set_record(report, 0, stop="error")                      # long but unusable
    _reseal(report)
    elig = _partition_eligibility(verify_sealed_report(report), _L)
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
    publish_r4_sidecar(report, rec, str(out))
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
    assert "provenance is not the canonical producer shape" in str(ei.value)


def test_generation_digest_binds_raw_text():
    a = _sealed_report()
    b = _sealed_report()
    b["records"][0]["raw_generation"] = "different text"
    assert _derive_generation_corpus_digest(a) != _derive_generation_corpus_digest(b)


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
            "generation_output_digest": _derive_generation_corpus_digest(report),
            "sequence_length": _L,
        },
        "per_pair": _canonicalize_comparison(rows), "aggregate": agg,   # canonical stored rows
    }
    man = {"schema": SIDECAR_SCHEMA, "evaluator": fabricated["evaluator"],
           "runner": fabricated["runner"], "parent": fabricated["parent"], "panel": fabricated["panel"]}
    forged = R4SidecarRecord(manifest_digest=canonical_digest(man),
                             output_digest=canonical_digest(fabricated),
                             record=fabricated)

    # The parent-FREE guard rev4 marketed against hand-built carriers is fooled: a self-consistent
    # fabrication has matching digests, a valid manifest, and a well-formed comparison. It returns.
    assert _verify_record(forged).record["parent"]["b0_report_digest"] == report["published_digest"]

    # But every parent-AWARE boundary re-derives eligibility (0) and refuses the fabricated pairs.
    with pytest.raises(R4SidecarError) as ei_dec:
        r4_decision(report, forged)
    assert "DERIVED from the bound parent" in str(ei_dec.value)
    with pytest.raises(R4SidecarError) as ei_pub:
        publish_r4_sidecar(report, forged, str(tmp_path / "r4.json"))
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
                             record=smuggled)
    for op in (lambda: r4_decision(report, forged),
               lambda: bind_to_parent_report(report, forged),
               lambda: publish_r4_sidecar(report, forged, str(tmp_path / "r4.json"))):
        with pytest.raises(R4SidecarError) as ei:
            op()
        assert "key set is not exact" in str(ei.value) and "eligibility" in str(ei.value)
    assert not (tmp_path / "r4.json").exists()               # nothing was committed


# --------------------------------------------------------------------------- #
# rev6 REGRESSIONS — Codex exact-source review of record #1183 (six findings). #
# See MoCoP/reviews/p5_item5_rev5_source_review_2026-07-18.md.                 #
# --------------------------------------------------------------------------- #
def _forged(record: dict):
    """Wrap a hand-built record dict as a self-consistent exact R4SidecarRecord carrier. The per_pair
    is canonicalized so the carrier passes _verify_record's shape/canonical-form checks and isolates
    the parent-aware boundary as the guard under test."""
    record = {**record, "per_pair": _canonicalize_comparison(record["per_pair"])}
    man = {k: record[k] for k in ("schema", "evaluator", "runner", "parent", "panel")}
    return R4SidecarRecord(manifest_digest=canonical_digest(man),
                           output_digest=canonical_digest(record), record=record)


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
    assert "not an exact str in" in str(ei.value)


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


# ---- rev7 (Codex #1187) additions ---------------------------------------------------------------
def test_f1_contradictory_manifest_authority_is_refused():
    # Codex #1187 F1: report.manifest_digest / execution_descriptor.manifest_digest / .base_manifest
    # _digest must all agree (DQ1b). A self-consistent report with three different digests passed rev6.
    report = _sealed_report()
    report["execution_descriptor"]["manifest_digest"] = "b" * 64      # != report.manifest_digest
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "manifest authority" in str(ei.value)


def test_f1_a_stripped_canonical_field_is_refused():
    # Codex #1187 F1: removing a producer-required top-level field (self-consistent otherwise) passed
    # rev6. rev7 requires the exact canonical top-level key set.
    report = _sealed_report()
    del report["journal_digest"]
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "canonical B0 shape" in str(ei.value)


def test_f1_contradictory_eos_custody_is_refused():
    # Codex #1187 F1: stop_reason 'eos' whose eos_token_id_fired is not the final generated id (the
    # producer's mutual-consistency rule) passed rev6's digest/count checks.
    report = _sealed_report(n=4, stop="eos")
    report["records"][0]["provenance"]["eos_token_id_fired"] = 999999   # != final generated id
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "eos_token_id_fired does not match" in str(ei.value)


def test_f3_a_post_capture_list_mutation_cannot_reach_the_artifact(tmp_path):
    # Codex #1187 F3: _thaw left nested lists LIVE. A parent callback reversed per_pair AFTER capture;
    # reversal preserved endpoints/rho so parent validation passed, but the published record no longer
    # matched its digest. rev7 captures a fully-OWNED deep copy, so a post-capture mutation is inert.
    report = _sealed_report(n=4)
    rows, agg = _comparison(_eligible_of(report))
    live_per_pair = _canonicalize_comparison(rows)      # a MUTABLE list the carrier holds
    record = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2", "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": report["execution_descriptor"]["panel_hash"],
        "parent": _manifest(report)["parent"],
        "per_pair": live_per_pair, "aggregate": agg,
    }
    man = {k: record[k] for k in ("schema", "evaluator", "runner", "parent", "panel")}
    carrier = R4SidecarRecord(manifest_digest=canonical_digest(man),
                              output_digest=canonical_digest(record), record=record)  # NOT deep-frozen
    good = carrier.output_digest
    fired = {"done": False}

    class _StatefulReport(dict):
        def items(self):
            if not fired["done"]:
                fired["done"] = True
                live_per_pair.reverse()                 # mutate the carrier's live list AFTER capture
            return super().items()

    out = tmp_path / "r4.json"
    # rev10: the hostile dict-subclass report is refused at sanitize BEFORE its items() can fire, so the
    # post-capture list mutation never runs and nothing is published. (Owned-snapshot capture stays as
    # defense-in-depth; _ = good keeps the pre-mutation digest referenced for clarity.)
    _ = good
    with pytest.raises(R4SidecarError) as ei:
        publish_r4_sidecar(_StatefulReport(report), carrier, str(out))
    assert "exact built-in" in str(ei.value)
    assert fired["done"] is False                             # the mutating callback NEVER ran
    assert not out.exists()


def test_f4_alias_mutation_during_unlink_is_caught(tmp_path, monkeypatch):
    # Codex #1187 F4: corrupting the final inode THROUGH the .tmp alias during a SUCCESSFUL unlink
    # left corrupt final bytes with disposition=integrity_verified, because the readback ran before
    # the unlink. rev7 removes the alias BEFORE the definitive readback.
    report = _sealed_report()
    rec = _build(report)
    out = tmp_path / "r4.json"
    orig_unlink = pathlib.Path.unlink

    def corrupt_then_unlink(self, *a, **k):
        if str(self).endswith(".tmp"):
            self.write_bytes(b"corrupted-through-the-writable-alias")   # mutate the shared inode
        return orig_unlink(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "unlink", corrupt_then_unlink)
    result = publish_r4_sidecar(report, rec, str(out))             # must NOT raise
    assert result.disposition == DISPOSITION_INTEGRITY_FAILED


def test_f6_a_noncanonical_hand_built_record_is_refused(tmp_path):
    # Codex #1187 F6: canonicalization was builder-only. A hand-built record with reversed (non-
    # canonical) row order passed verify/bind/decision/publish and minted a different digest for an
    # equivalent comparison. rev7 requires the stored rows to BE their canonical form.
    report = _sealed_report(n=4)
    rows, agg = _comparison(_eligible_of(report))
    noncanon = list(reversed(_canonicalize_comparison(rows)))   # same rows, non-canonical order
    record = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2", "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": report["execution_descriptor"]["panel_hash"],
        "parent": _manifest(report)["parent"],
        "per_pair": noncanon, "aggregate": agg,
    }
    man = {k: record[k] for k in ("schema", "evaluator", "runner", "parent", "panel")}
    forged = R4SidecarRecord(manifest_digest=canonical_digest(man),
                             output_digest=canonical_digest(record), record=record)
    for op in (lambda: r4_decision(report, forged),
               lambda: bind_to_parent_report(report, forged),
               lambda: publish_r4_sidecar(report, forged, str(tmp_path / "r4.json"))):
        with pytest.raises(R4SidecarError) as ei:
            op()
        assert "canonical form" in str(ei.value)


def test_incomplete_for_zero_and_one_eligible_probes(tmp_path):
    # Codex #1187 #6: N'=0 and N'=1 must emit the frozen INCOMPLETE decision (empty comparison), not
    # raise "no per-pair comparison rows".
    for eligible_n in (0, 1):
        report = _sealed_report(n=3)
        for j in range(eligible_n, 3):
            _set_record(report, j, tokens=1)                 # make the rest short -> refused
        _reseal(report)
        elig = _eligible_of(report)
        assert len(elig) == eligible_n
        rows, agg = _comparison(elig)                        # empty comparison
        rec = build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
        d = r4_decision(report, rec)
        assert d["state"] == DECISION_INCOMPLETE and d["c1_authorization_permitted"] is False
        assert d["n_eligible"] == eligible_n
        result = publish_r4_sidecar(report, rec, str(tmp_path / f"r4_{eligible_n}.json"))
        assert result.disposition == DISPOSITION_VERIFIED    # commits cleanly; the DECISION is INCOMPLETE


def test_a_huge_int_numeric_is_a_typed_refusal_not_overflow():
    # Codex #1187 #7: math.isfinite(10**400) raises OverflowError. A huge exact int must be an
    # in-range refusal, not a raw OverflowError.
    r = validate_comparison(
        per_pair=[{"probe_a": "a", "probe_b": "b", "jsd": 10 ** 400, "cosine_similarity": 0.5}],
        aggregate={"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0,
                   "mean_pairwise_embedding": 0.0, "n_pairs": 1},
        eligible_probe_ids=["a", "b"])
    assert any("jsd must be in" in x for x in r)


# ---- rev7 a-Codex pre-board additions -----------------------------------------------------------
def test_acodex_contradictory_duplicated_fields_are_refused():
    # a-Codex (rev7): top-level run_kind/schema_variant/base_manifest_id must AGREE with the
    # descriptor's; the producer emits them from one source.
    report = _sealed_report()
    report["run_kind"] = "c1_variant"                        # != execution_descriptor.run_kind
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "run_kind" in str(ei.value)


def test_acodex_null_runner_digest_and_incomplete_model_are_refused():
    # a-Codex (rev7): a descriptor with runner_digest=None or an incomplete model is not a report the
    # runner could publish.
    r1 = _sealed_report()
    r1["execution_descriptor"]["runner_digest"] = None
    _reseal(r1)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(r1)
    assert "runner_digest" in str(ei.value)

    r2 = _sealed_report()
    r2["execution_descriptor"]["model"] = {"id": "gemma"}    # incomplete (missing DESCRIPTOR_KEYS)
    _reseal(r2)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(r2)
    assert "exact producer model descriptor" in str(ei.value)   # rev9 F-MODEL: exact key-set equality


def test_acodex_empty_comparison_requires_the_canonical_zero_aggregate():
    # a-Codex (rev7): an empty comparison must have ONE pinned aggregate, so equivalent empty
    # comparisons cannot mint different digests.
    ok = validate_comparison(
        per_pair=[],
        aggregate={"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0,
                   "mean_pairwise_embedding": 0.0, "n_pairs": 0},
        eligible_probe_ids=["only-one"])                     # N'=1 -> zero expected pairs
    assert ok == []
    bad = validate_comparison(
        per_pair=[],
        aggregate={"spearman_rho": 1.0, "mean_pairwise_jsd": 1.0,   # non-canonical empty aggregate
                   "mean_pairwise_embedding": -1.0, "n_pairs": 0},
        eligible_probe_ids=["only-one"])
    assert any("canonical zero aggregate" in x for x in bad)


def test_acodex_heterogeneous_row_key_is_a_typed_refusal_not_typeerror():
    # a-Codex (rev7): validate_comparison is a PUBLIC self-check; a malformed row with a mixed
    # str/int key set must accumulate a refusal, not raise a raw TypeError from sorting.
    r = validate_comparison(
        per_pair=[{"probe_a": "a", "probe_b": "b", "jsd": 0.5, "cosine_similarity": 0.5, 7: "x"}],
        aggregate={"spearman_rho": 0.0, "mean_pairwise_jsd": 0.5,
                   "mean_pairwise_embedding": 0.5, "n_pairs": 1},
        eligible_probe_ids=["a", "b"])
    assert any("exact str" in x for x in r)                      # rev10: non-str key refused at sanitize


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
               lambda: publish_r4_sidecar(report, forged, str(tmp_path / "r4.json"))):
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
    _ = good
    # rev10: the hostile dict-subclass report is refused at sanitize BEFORE its items() can fire, so the
    # digest-swap callback never runs and nothing is published. (Single-snapshot capture stays as
    # defense-in-depth.)
    with pytest.raises(R4SidecarError) as ei:
        publish_r4_sidecar(_StatefulReport(report), rec, str(out))
    assert "exact built-in" in str(ei.value)
    assert fired["done"] is False                             # the digest-swap callback NEVER ran
    assert not out.exists()


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
    result = publish_r4_sidecar(report, rec, str(out))    # must NOT raise
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
                             record=incomplete)
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
    reversed_rows = [{"probe_a": r["probe_b"], "probe_b": r["probe_a"],   # reversed order + orientation
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
    with pytest.raises(R4SidecarError):     # a str subclass is refused (exact-typed snapshot / enum)
        verify_sealed_report(report)

    report2 = _sealed_report(n=4)
    report2["records"][0]["provenance"]["stop_reason"] = ["not", "a", "str"]   # unhashable
    _reseal(report2)
    with pytest.raises(R4SidecarError):                          # typed refusal, NOT a raw TypeError
        verify_sealed_report(report2)


def test_acodex_pair_id_has_no_delimiter_collision_for_ids_containing_a_bar(tmp_path):
    # a-Codex/#1187: the DERIVED pair_id must not collide for probe ids containing "|"
    # (("a","b|c") and ("a|b","c") both -> "a|b|c" under a single-bar delimiter). §5.5 has no caller
    # pair_id; the JSON-of-oriented-endpoints derivation is injective and round-trips through publish.
    report = _sealed_report(ids=["a", "b|c", "a|b", "c"])
    rows, agg = _comparison(_eligible_of(report))           # INPUT rows, no caller pair_id
    rec = build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
    derived = [r["pair_id"] for r in rec.record["per_pair"]]
    assert len(derived) == len(set(derived))                # DERIVED pair_ids do not collide
    result = publish_r4_sidecar(report, rec, str(tmp_path / "r4.json"))   # round-trips through _verify_record
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
                             output_digest=canonical_digest(bad), record=bad)
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
    result = publish_r4_sidecar(report, rec, str(out))
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
    publish_r4_sidecar(report, rec, str(out))
    with pytest.raises(R4SidecarError) as ei:
        publish_r4_sidecar(report, rec, str(out))
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
    result = publish_r4_sidecar(report, rec, str(out))             # must NOT raise
    assert result.disposition == DISPOSITION_INTEGRITY_FAILED
    assert out.exists()                                       # the artifact is committed


def test_a_durability_fault_is_committed_indeterminate(tmp_path, monkeypatch):
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_fsync_dir", lambda d: False)
    report = _sealed_report()
    rec = _build(report)
    result = publish_r4_sidecar(report, rec, str(tmp_path / "r4.json"))
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
    result = record_r4_comparison(report_path=str(out), journal_path=str(journal), manifest=manifest,
                                  per_pair=rows, aggregate=agg, sidecar_path=str(r4_out))
    assert isinstance(result, R4RecordResult)
    assert result.ok is True                                 # authority verified + proceeds
    assert result.decision["state"] == DECISION_JSD_PROCEEDS
    assert r4_out.exists()


def test_seam_refuses_an_absent_report(tmp_path):
    report = _sealed_report()
    rows, agg = _comparison(_eligible_of(report))
    with pytest.raises(R4SidecarError) as ei:
        record_r4_comparison(report_path=str(tmp_path / "nope.json"),
                             journal_path=str(tmp_path / "nope.json.journal"),
                             manifest=_manifest(report), per_pair=rows, aggregate=agg,
                             sidecar_path=str(tmp_path / "r4.json"))
    assert "not found" in str(ei.value)


def test_seam_refuses_a_malformed_report(tmp_path):
    rp = tmp_path / "b0.json"
    rp.write_text("this is not json", encoding="utf-8")
    jp = tmp_path / "b0.json.journal"
    jp.write_text("", encoding="utf-8")
    report = _sealed_report()
    rows, agg = _comparison(_eligible_of(report))
    with pytest.raises(R4SidecarError) as ei:
        record_r4_comparison(report_path=str(rp), journal_path=str(jp), manifest=_manifest(report),
                             per_pair=rows, aggregate=agg, sidecar_path=str(tmp_path / "r4.json"))
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
        record_r4_comparison(report_path=str(rp), journal_path=str(jp), manifest=_manifest(report),
                             per_pair=rows, aggregate=agg, sidecar_path=str(tmp_path / "r4.json"))
    assert "did not verify" in str(ei.value)


@pytest.mark.parametrize("disp", ["committed_integrity_failed", "committed_indeterminate", "refused"])
def test_seam_refuses_a_verified_journal_whose_terminal_authority_is_not_integrity_verified(
        tmp_path, monkeypatch, disp):
    # The DISPOSITION gate specifically: the journal parses/verifies (ok=True) but its terminal
    # authority is not integrity_verified. No C1 authorization may rest on that (Monk #1146). This
    # isolates the disposition check, which the empty-journal (ok=False) case does not reach.
    # rev9 (a-Codex #1201): the terminal verifier is now a FROZEN authority, so a module-level
    # setattr on verify_terminal_frames is a no-op (that is the point of the freeze). Inject the
    # ok=True/non-verified verdict through the _auth accessor seam (._replace keeps every other
    # authority frozen-real) so this still isolates the disposition gate.
    import p5_r4_sidecar
    _real = p5_r4_sidecar._auth()
    monkeypatch.setattr(
        p5_r4_sidecar, "_auth",
        lambda: _real._replace(terminal_verifier=lambda *a, **k: {"ok": True, "disposition": disp}))
    report = _sealed_report()
    rp = tmp_path / "b0.json"
    rp.write_text(json.dumps(report), encoding="utf-8")
    jp = tmp_path / "b0.json.journal"
    jp.write_text("{}\n", encoding="utf-8")
    rows, agg = _comparison(_eligible_of(report))
    with pytest.raises(R4SidecarError) as ei:
        record_r4_comparison(report_path=str(rp), journal_path=str(jp), manifest=_manifest(report),
                             per_pair=rows, aggregate=agg, sidecar_path=str(tmp_path / "r4.json"))
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
        _partition_eligibility(verify_sealed_report(_sealed_report()), 0)


def test_validate_comparison_standalone_accumulates_faults():
    # Public: the out-of-process runner can self-check before the custody boundary; faults accumulate.
    r = validate_comparison(
        per_pair=[{"probe_a": "a", "probe_b": "a", "jsd": 5.0, "cosine_similarity": None}],
        aggregate={"spearman_rho": "y", "n_pairs": 0},
        eligible_probe_ids=["a", "b"])
    assert any("endpoints are identical" in x for x in r)
    assert any("jsd must be in" in x for x in r)
    assert any("cosine_similarity" in x for x in r)
    assert any("spearman_rho" in x for x in r)


def test_eligibility_dataclass_shape():
    e = _partition_eligibility(verify_sealed_report(_sealed_report()), _L)
    assert isinstance(e, Eligibility) and e.eligible == ("probe0", "probe1", "probe2", "probe3")


# --------------------------------------------------------------------------- #
# rev8 REGRESSIONS — Codex exact-source review of record #1197 (four findings).#
# See MoCoP/reviews/p5_item5_rev7_source_review_2026-07-19.md.                 #
# --------------------------------------------------------------------------- #
# F1 (P1): verify_sealed_report checked producer SHAPE but not producer VALUES. Six self-consistent
# reports run_b0 could never publish (wrong run_kind/variant, float record_count, unbound/sampling
# decoding, null model.id, non-digest panel_hash) reached jsd_proceeds/c1=true in rev7.
def test_f1_run_kind_must_be_the_b0_baseline_value():
    # 'c1_intervention' on BOTH top-level and descriptor (so the duplicated-field agreement check
    # passes) is not a B0 parent. rev7 checked shape/agreement, never the value.
    report = _sealed_report()
    report["run_kind"] = report["execution_descriptor"]["run_kind"] = "c1_intervention"
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "b0_baseline" in str(ei.value)


def test_f1_schema_variant_must_be_the_b0_baseline_value():
    # closed_world_c1 is a VALID schema-variant member but the C1 lane's, not B0's. A self-consistent
    # c1-variant report passed rev7 (which only pinned closed-world-union membership via agreement).
    report = _sealed_report()
    report["schema_variant"] = report["execution_descriptor"]["schema_variant"] = "closed_world_c1"
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "closed_world_b0" in str(ei.value)


def test_f1_record_count_must_be_an_exact_int_not_a_float():
    # 4.0 == 4 is True in Python, so a float record_count passed rev7's equality-only check.
    report = _sealed_report(n=4)
    report["record_count"] = 4.0
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "exact int" in str(ei.value)


def test_f1_decoding_hash_must_bind_its_own_decoding():
    # rev7 only checked decoding_hash was SOME sha256, not the digest OF this decoding block.
    report = _sealed_report()
    report["execution_descriptor"]["decoding_hash"] = "d" * 64      # a real sha256, but unrelated
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "not the canonical digest of its own decoding" in str(ei.value)


def test_f1_decoding_must_be_the_pinned_neutralization_set():
    # A decoding block that samples is not a B0 baseline, however self-hashed. Re-derive its hash so
    # the cross-bind passes and the neutralization-contract check is what fires.
    report = _sealed_report()
    dec = dict(_DECODING)
    dec["do_sample"] = True                                         # sampling => not greedy baseline
    report["execution_descriptor"]["decoding"] = dec
    report["execution_descriptor"]["decoding_hash"] = canonical_digest(dec)
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "neutralization set" in str(ei.value)


def test_f1_model_id_null_and_auto_device_map_are_refused():
    # rev7 only checked model CONTAINED DESCRIPTOR_KEYS; model.id=None passed the membership check.
    r1 = _sealed_report()
    r1["execution_descriptor"]["model"]["id"] = None
    _reseal(r1)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(r1)
    assert "model.id must be a non-empty str" in str(ei.value)

    r2 = _sealed_report()
    r2["execution_descriptor"]["model"]["device_map"] = "auto"     # auto-sharding route
    _reseal(r2)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(r2)
    assert "explicit single device" in str(ei.value)


def test_f1_panel_hash_must_be_a_sha256_not_any_string():
    report = _sealed_report()
    report["execution_descriptor"]["panel_hash"] = "not-a-digest"
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "panel_hash" in str(ei.value)


# F2 (P1): RHO_GATE / _MIN_ELIGIBLE are mutable module globals; a caller mapping whose items() runs
# during verification could reassign them mid-verify and green a failing decision.
def test_f2_a_midverify_rho_gate_swap_cannot_green_a_failing_decision(monkeypatch, tmp_path):
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "RHO_GATE", 0.7)            # ensure teardown restores 0.7
    report = _sealed_report()
    rec = _build(report, agree=False)                             # rho ~ -1 => replacement required

    fired = {"n": 0}

    class _SwapReport(dict):
        def items(self):
            if fired["n"] == 0:
                p5_r4_sidecar.RHO_GATE = -2.0                     # reassign the global mid-verify
            fired["n"] += 1
            return super().items()

    # rev10: the hostile dict-subclass report is refused at sanitize BEFORE its items() can fire, so the
    # RHO_GATE rebind never runs. (The frozen gate is defense-in-depth behind this — the pre-call
    # rho-gate test exercises the freeze directly.)
    for op in (lambda: r4_decision(_SwapReport(report), rec),
               lambda: publish_r4_sidecar(_SwapReport(report), rec, str(tmp_path / "r4.json"))):
        with pytest.raises(R4SidecarError) as ei:
            op()
        assert "exact built-in" in str(ei.value)
    assert fired["n"] == 0                                        # the callback NEVER ran
    assert p5_r4_sidecar.RHO_GATE == 0.7                          # gate untouched


# F3 (P2): numeric/key totality — a huge declared aggregate metric must not overflow float() in the
# recompute, and no untrusted key may be fed to repr()/str() on a public self-check.
def test_f3_a_huge_aggregate_metric_does_not_overflow_the_recompute():
    report = _sealed_report(n=4)
    rows, agg = _comparison(_eligible_of(report))
    agg["spearman_rho"] = 10 ** 400                              # range-fail; must not enter float()
    r = validate_comparison(rows, agg, eligible_probe_ids=list(_eligible_of(report)))
    assert any("spearman_rho must be in" in x for x in r)        # range refusal, NOT an OverflowError


class _BadRepr:
    def __repr__(self):
        raise RuntimeError("hostile __repr__")

    def __hash__(self):
        return 0

    def __eq__(self, other):
        return other is self


def test_f3_a_hostile_repr_row_key_does_not_escape_the_refusal():
    r = validate_comparison(
        per_pair=[{"probe_a": "a", "probe_b": "b", "jsd": 0.5, "cosine_similarity": 0.5, _BadRepr(): "x"}],
        aggregate={"spearman_rho": 0.0, "mean_pairwise_jsd": 0.5,
                   "mean_pairwise_embedding": 0.5, "n_pairs": 1},
        eligible_probe_ids=["a", "b"])
    assert any("exact str" in x for x in r)                      # rev10: refused at sanitize; __repr__ never called


def test_f3_inert_snapshot_nonstr_key_refusal_never_reprs_the_key():
    from p5_r4_sidecar import _inert_snapshot
    with pytest.raises(R4SidecarError):                          # typed refusal, NOT the RuntimeError
        _inert_snapshot({_BadRepr(): 1})


# F6 (P2): numeric normalization — 0.0 vs -0.0 (and int vs float) verify equal under == but serialize
# to distinct canonical-JSON tokens, minting divergent digests for equivalent comparisons.
def test_f6_a_hand_built_negative_zero_aggregate_is_refused(tmp_path):
    report = _sealed_report(n=3)
    for j in range(1, 3):
        _set_record(report, j, tokens=1)                         # leave exactly 1 eligible => empty cmp
    _reseal(report)
    assert len(_eligible_of(report)) == 1
    forged = _forged({
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2", "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": report["execution_descriptor"]["panel_hash"],
        "parent": _manifest(report)["parent"],
        "per_pair": [],
        "aggregate": {"spearman_rho": -0.0, "mean_pairwise_jsd": 0.0,
                      "mean_pairwise_embedding": 0.0, "n_pairs": 0},
    })
    for op in (lambda: r4_decision(report, forged),
               lambda: bind_to_parent_report(report, forged),
               lambda: publish_r4_sidecar(report, forged, str(tmp_path / "r4.json"))):
        with pytest.raises(R4SidecarError) as ei:
            op()
        assert "canonical numeric form" in str(ei.value)
    assert not (tmp_path / "r4.json").exists()


def test_f6_build_normalizes_negative_zero_to_one_digest():
    report = _sealed_report(n=3)
    for j in range(1, 3):
        _set_record(report, j, tokens=1)
    _reseal(report)
    rows, _agg = _comparison(_eligible_of(report))               # empty comparison (1 eligible)
    zero = {"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0, "mean_pairwise_embedding": 0.0, "n_pairs": 0}
    neg = {**zero, "spearman_rho": -0.0}
    a = build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=zero)
    b = build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=neg)
    assert a.output_digest == b.output_digest                    # -0.0 normalized to 0.0: one digest


# --------------------------------------------------------------------------- #
# rev9 REGRESSIONS — Codex exact-source review of record #1201 (three findings).
# See MoCoP/reviews/p5_item5_rev8_source_review_2026-07-20.md.                 #
# --------------------------------------------------------------------------- #
# F-AUTH (P1): rev8 read the producer/decision authorities through ASSIGNABLE module attributes and
# only CALL-ENTRY-copied RHO_GATE. A copy of a mutable attr is not a freeze: a pre-call setattr, or a
# caller Mapping.items() callback during verification, could rebind RHO_GATE / B0_RUN_KIND /
# check_decoding_contract and drive the verdict. rev9 freezes them all in an import-time closure
# (_auth()), mirroring p5_b0_run._bind_authority. These are Codex's three exact-target canaries.
def test_fauth_a_precall_rho_gate_rebind_cannot_green_anticorrelated_evidence(monkeypatch):
    # Canary 1: RHO_GATE = -2.0 BEFORE r4_decision(anti-correlated evidence). rev8 captured the gate
    # from the live global at call entry, so a pre-call rebind still became the verdict authority.
    import p5_r4_sidecar
    report = _sealed_report()
    rec = _build(report, agree=False)                            # rho ~ -1 => replacement required
    monkeypatch.setattr(p5_r4_sidecar, "RHO_GATE", -2.0)         # rebind BEFORE the call (auto-restored)
    d = r4_decision(report, rec)
    assert d["c1_authorization_permitted"] is False              # frozen gate 0.7, not the -2.0 rebind
    assert d["state"] == DECISION_JSD_REPLACEMENT_REQUIRED
    assert d["rho_gate"] == 0.7


def test_fauth_a_callback_run_kind_rebind_cannot_accept_a_c1_parent(monkeypatch):
    # Canary 2: a top-level Mapping.items() callback rebinds p5_r4_sidecar.B0_RUN_KIND to match a
    # self-consistent c1_intervention parent. rev8 read the live global AFTER the callback.
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "B0_RUN_KIND", "b0_baseline")   # register for teardown
    report = _sealed_report()
    report["run_kind"] = report["execution_descriptor"]["run_kind"] = "c1_intervention"
    _reseal(report)
    fired = {"n": 0}

    class _RunKindSwap(dict):
        def items(self):
            if fired["n"] == 0:
                p5_r4_sidecar.B0_RUN_KIND = "c1_intervention"   # rebind the global mid-snapshot
            fired["n"] += 1
            return super().items()

    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(_RunKindSwap(report))
    assert "exact built-in" in str(ei.value)                    # rev10: dict subclass refused at sanitize
    assert fired["n"] == 0                                       # the callback's rebind NEVER ran


def test_fauth_a_callback_decoding_validator_rebind_cannot_accept_a_sampling_parent(monkeypatch):
    # Canary 3: a top-level Mapping.items() callback replaces p5_r4_sidecar.check_decoding_contract
    # with a permissive stub, so a do_sample=true (non-neutral) decoding block would pass. rev8 called
    # the live global reference AFTER the callback.
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "check_decoding_contract",
                        p5_r4_sidecar.check_decoding_contract)  # register for teardown
    report = _sealed_report()
    dec = dict(_DECODING)
    dec["do_sample"] = True                                     # sampling => not the B0 neutral set
    report["execution_descriptor"]["decoding"] = dec
    report["execution_descriptor"]["decoding_hash"] = canonical_digest(dec)   # cross-bind still passes
    _reseal(report)
    fired = {"n": 0}

    class _DecodingSwap(dict):
        def items(self):
            if fired["n"] == 0:
                p5_r4_sidecar.check_decoding_contract = lambda spec: []   # permissive stub
            fired["n"] += 1
            return super().items()

    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(_DecodingSwap(report))
    assert "exact built-in" in str(ei.value)                    # rev10: dict subclass refused at sanitize
    assert fired["n"] == 0                                       # the callback's rebind NEVER ran


# F-MODEL (P1): the producer requires the EXACT frozen 8-key model descriptor; rev8 used a subset
# test, so a re-sealed report carrying an extra unbound model field was accepted though run_b0 refuses
# it before execution (_descriptor_schema_error).
def test_fmodel_an_extra_unbound_model_field_is_refused():
    report = _sealed_report()
    report["execution_descriptor"]["model"]["unbound_extra"] = "accepted"
    _reseal(report)
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "exact producer model descriptor" in str(ei.value)


# F-TYPENAME (P2): type(key).__name__ dispatches through the key type's METACLASS; a hostile metaclass
# that raises on the __name__ lookup escaped a typed refusal as the caller's raw exception. rev9 labels
# types by exact built-in identity, never by inspecting foreign type metadata.
class _HostileNameMeta(type):
    @property
    def __name__(cls):                                          # noqa: A003 — intentionally hostile
        raise RuntimeError("hostile type name")


class _HostileTypeName(metaclass=_HostileNameMeta):
    def __hash__(self):
        return 0

    def __eq__(self, other):
        return other is self


def test_ftypename_a_hostile_metaclass_key_does_not_escape_inert_snapshot():
    from p5_r4_sidecar import _inert_snapshot
    with pytest.raises(R4SidecarError):                         # typed refusal, NOT the metaclass error
        _inert_snapshot({_HostileTypeName(): 1})


def test_ftypename_a_hostile_metaclass_key_does_not_escape_a_public_self_check():
    # validate_comparison is a PUBLIC self-check: a malformed row carrying a hostile-metaclass key must
    # accumulate a refusal (via _safe_keys), never raise the metaclass's RuntimeError.
    r = validate_comparison(
        per_pair=[{"probe_a": "a", "probe_b": "b", "jsd": 0.5, "cosine_similarity": 0.5,
                   _HostileTypeName(): "x"}],
        aggregate={"spearman_rho": 0.0, "mean_pairwise_jsd": 0.5,
                   "mean_pairwise_embedding": 0.5, "n_pairs": 1},
        eligible_probe_ids=["a", "b"])
    assert any("exact str" in x for x in r)                     # rev10: refused at sanitize; __name__ never inspected


# --------------------------------------------------------------------------- #
# rev9 a-Codex HARDENING — the freeze was INCOMPLETE. The /codex-review pass    #
# found two more of the same class as #1201 at boundaries not yet frozen:      #
# (A) the terminal/publication disposition authority, (B) the sidecar-side     #
# validation policy. Both are now frozen; these are the two exact-target        #
# canaries. See MoCoP/reviews/p5_item5_rev8_source_review_2026-07-20.md.        #
# --------------------------------------------------------------------------- #
def test_fauth_a_precall_disposition_rebind_cannot_admit_a_failed_terminal(tmp_path, monkeypatch):
    # (A) _load_governed_report gated the parent on the LIVE DISPOSITION_VERIFIED label. Pre-call
    # rebinding it to 'committed_integrity_failed' would make a verified-but-FAILED B0 terminal clear
    # the gate. rev9 reads the frozen _A.disp_verified, so the failed terminal is still refused.
    import p5_r4_sidecar
    _real = p5_r4_sidecar._auth()
    # A verdict that VERIFIES (ok=True) but whose terminal authority is committed_integrity_failed:
    monkeypatch.setattr(p5_r4_sidecar, "_auth", lambda: _real._replace(
        terminal_verifier=lambda *a, **k: {"ok": True, "disposition": "committed_integrity_failed"}))
    # The exploit: rebind the module label so a rev8-style live read would treat FAILED as verified.
    monkeypatch.setattr(p5_r4_sidecar, "DISPOSITION_VERIFIED", "committed_integrity_failed")
    report = _sealed_report()
    rp = tmp_path / "b0.json"
    rp.write_text(json.dumps(report), encoding="utf-8")
    jp = tmp_path / "b0.json.journal"
    jp.write_text("{}\n", encoding="utf-8")
    rows, agg = _comparison(_eligible_of(report))
    with pytest.raises(R4SidecarError) as ei:
        record_r4_comparison(report_path=str(rp), journal_path=str(jp), manifest=_manifest(report),
                             per_pair=rows, aggregate=agg, sidecar_path=str(tmp_path / "r4.json"))
    assert "terminal authority" in str(ei.value)                # frozen disp_verified refuses it


def test_fauth_a_carrier_callback_loosening_sidecar_policy_cannot_accept_a_mutable_ref(monkeypatch):
    # (B) _verify_record fires the carrier's record.items() BEFORE re-validating the sidecar manifest
    # against _MUTABLE_REFS / _SHA40. A callback that clears the mutable-ref denylist and loosens the
    # 40-hex regex would let evaluator revision_sha='main' (a mutable ref) gate C1. rev9 reads the
    # frozen policy from _auth(), captured before the callback, so 'main' is still refused.
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_MUTABLE_REFS", p5_r4_sidecar._MUTABLE_REFS)  # register teardown
    monkeypatch.setattr(p5_r4_sidecar, "_SHA40", p5_r4_sidecar._SHA40)                # register teardown
    report = _sealed_report(n=4)
    rows, agg = _comparison(_eligible_of(report))
    record = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2", "revision_sha": "main"},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": report["execution_descriptor"]["panel_hash"],
        "parent": _manifest(report)["parent"],
        "per_pair": _canonicalize_comparison(rows), "aggregate": agg,
    }
    man = {k: record[k] for k in ("schema", "evaluator", "runner", "parent", "panel")}
    fired = {"done": False}

    class _PolicySwapRecord(dict):
        def items(self):
            if not fired["done"]:
                fired["done"] = True
                p5_r4_sidecar._MUTABLE_REFS = frozenset()          # clear the mutable-ref denylist
                p5_r4_sidecar._SHA40 = re.compile(r".*")           # loosen the 40-hex format regex
            return super().items()

    carrier = R4SidecarRecord(manifest_digest=canonical_digest(man),
                              output_digest=canonical_digest(record),
                              record=_PolicySwapRecord(record))
    with pytest.raises(R4SidecarError) as ei:
        r4_decision(report, carrier)
    assert "exact built-in" in str(ei.value)                    # rev10: dict subclass refused at sanitize
    assert fired["done"] is False                               # the callback's policy-loosen NEVER ran


def test_fauth_a_precall_decision_label_rebind_cannot_spoof_the_state(monkeypatch):
    # (Wachhund audit) _build_decision stamped decision.state from the LIVE DECISION_* labels, and the
    # decision record feeds the future C1 boundary. A pre-call rebind of DECISION_JSD_PROCEEDS would
    # spoof that state string. rev9 reads the frozen _A.decision_proceeds, so the state stays truthful.
    import p5_r4_sidecar
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)                            # rho +1, 4 eligible => jsd_proceeds
    monkeypatch.setattr(p5_r4_sidecar, "DECISION_JSD_PROCEEDS", "spoofed_incomplete")
    d = r4_decision(report, rec)
    assert d["state"] == DECISION_JSD_PROCEEDS                  # frozen label, not the rebound module value
    assert d["c1_authorization_permitted"] is True


def test_fauth_a_carrier_callback_reassigning_auth_itself_cannot_accept_a_mutable_ref(monkeypatch):
    # The DEEPEST incomplete-freeze vector (advisor): a carrier record.items() callback that reassigns
    # _auth ITSELF (not a value global). It fires during _verify_record's snapshot; helpers called
    # afterward (validate_sidecar_manifest -> _field_error) re-fetched _auth() post-callback in the
    # first hardening pass, so a swapped accessor still drove the verdict. rev9 now binds ONE _A at the
    # public entry (before any caller items()) and THREADS it through every verdict helper — none
    # re-fetches _auth() after caller code ran — so 'main' (a mutable ref) stays refused. Only a
    # PRE-call _auth reassignment remains a residual, which is the producer's accepted bar.
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_auth", p5_r4_sidecar._auth)   # register for teardown
    real = p5_r4_sidecar._auth()
    report = _sealed_report(n=4)
    rows, agg = _comparison(_eligible_of(report))
    record = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2", "revision_sha": "main"},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "panel": report["execution_descriptor"]["panel_hash"],
        "parent": _manifest(report)["parent"],
        "per_pair": _canonicalize_comparison(rows), "aggregate": agg,
    }
    man = {k: record[k] for k in ("schema", "evaluator", "runner", "parent", "panel")}
    fired = {"done": False}

    class _AuthSwap(dict):
        def items(self):
            if not fired["done"]:
                fired["done"] = True
                p5_r4_sidecar._auth = lambda: real._replace(mutable_refs=frozenset(),
                                                            sha40=re.compile(r".*"))
            return super().items()

    carrier = R4SidecarRecord(manifest_digest=canonical_digest(man),
                              output_digest=canonical_digest(record), record=_AuthSwap(record))
    with pytest.raises(R4SidecarError) as ei:
        r4_decision(report, carrier)
    assert "exact built-in" in str(ei.value)                    # rev10: dict subclass refused at sanitize
    assert fired["done"] is False                               # the callback's _auth swap NEVER ran


def test_fauth_a_carrier_callback_swapping_field_kind_tags_cannot_accept_a_mutable_ref(monkeypatch):
    # (a-Codex #1201 pass 2) Dispatching _field_error against the LIVE module tags was NOT fail-closed:
    # a callback that SWAPS _ID <-> _SHA40F mis-routes revision_sha='main' down the id-branch (non-empty
    # str only), bypassing the mutable-ref + 40-hex checks. rev9 dispatches against the frozen _A.*_kind
    # tags, so a module-tag swap can neither re-route dispatch nor reach a decision.
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_ID", p5_r4_sidecar._ID)         # register for teardown
    monkeypatch.setattr(p5_r4_sidecar, "_SHA40F", p5_r4_sidecar._SHA40F)
    real_ID, real_SHA40F = p5_r4_sidecar._ID, p5_r4_sidecar._SHA40F
    report = _sealed_report(n=4)
    rows, agg = _comparison(_eligible_of(report))
    record = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "a" * 40, "revision_sha": "main"},   # 40-hex id, mutable rev
        "runner": {"runner_id": "b" * 40, "runner_digest": "d" * 64},
        "panel": report["execution_descriptor"]["panel_hash"],
        "parent": _manifest(report)["parent"],
        "per_pair": _canonicalize_comparison(rows), "aggregate": agg,
    }
    man = {k: record[k] for k in ("schema", "evaluator", "runner", "parent", "panel")}
    fired = {"done": False}

    class _TagSwap(dict):
        def items(self):
            if not fired["done"]:
                fired["done"] = True
                p5_r4_sidecar._ID, p5_r4_sidecar._SHA40F = real_SHA40F, real_ID   # SWAP the tags
            return super().items()

    carrier = R4SidecarRecord(manifest_digest=canonical_digest(man),
                              output_digest=canonical_digest(record), record=_TagSwap(record))
    with pytest.raises(R4SidecarError) as ei:
        r4_decision(report, carrier)
    assert "exact built-in" in str(ei.value)                    # rev10: dict subclass refused at sanitize
    assert fired["done"] is False                               # the callback's tag swap NEVER ran


# --------------------------------------------------------------------------- #
# rev10 (wolf-Codex #1206) — the SANITIZER is the PRIMARY defense. _inert_snapshot
# accepts ONLY exact built-in containers, so NO caller-overridable traversal runs
# during verification: the entire mid-verify rebind class (policy + primitives +
# digests) is structurally impossible. Codex's canaries — dict subclass (the
# reframed tests above), MappingProxyType(hostile backing), list subclass, tuple
# subclass, standalone validator — each rebinds a decision primitive DURING the
# attempted traversal, each REFUSED WITHOUT the callback firing.
# --------------------------------------------------------------------------- #
def test_rev10_sanitizer_refuses_a_mappingproxytype_wrapping_a_hostile_mapping(monkeypatch):
    from types import MappingProxyType
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_diversity_agreement_rho", p5_r4_sidecar._diversity_agreement_rho)
    fired = {"n": 0}

    class _HostileBacking(dict):
        def items(self):                                        # would run if the proxy were traversed
            fired["n"] += 1
            p5_r4_sidecar._diversity_agreement_rho = lambda j, s: 1.0
            return super().items()

    proxy = MappingProxyType(_HostileBacking(_sealed_report(n=4)))
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(proxy)                             # Codex's constraint: a proxy is NOT inert
    assert "exact built-in" in str(ei.value)
    assert fired["n"] == 0                                      # the hostile backing was NEVER delegated to


def test_rev10_sanitizer_refuses_a_hostile_list_subclass(monkeypatch):
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_diversity_agreement_rho", p5_r4_sidecar._diversity_agreement_rho)
    fired = {"n": 0}

    class _HostileRows(list):
        def __iter__(self):
            fired["n"] += 1
            p5_r4_sidecar._diversity_agreement_rho = lambda j, s: 1.0
            return super().__iter__()

    rows = _HostileRows([{"probe_a": "a", "probe_b": "b", "jsd": 0.5, "cosine_similarity": 0.5}])
    agg = {"spearman_rho": 0.0, "mean_pairwise_jsd": 0.5, "mean_pairwise_embedding": 0.5, "n_pairs": 1}
    r = validate_comparison(rows, agg, eligible_probe_ids=["a", "b"])
    assert any("exact built-in" in x for x in r)               # list subclass refused at sanitize
    assert fired["n"] == 0                                      # the __iter__ callback NEVER ran


def test_rev10_sanitizer_refuses_a_hostile_tuple_subclass(monkeypatch):
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_diversity_agreement_rho", p5_r4_sidecar._diversity_agreement_rho)
    fired = {"n": 0}

    class _HostileTuple(tuple):
        def __iter__(self):
            fired["n"] += 1
            p5_r4_sidecar._diversity_agreement_rho = lambda j, s: 1.0
            return super().__iter__()

    report = _sealed_report(n=4)
    report["records"] = _HostileTuple(report["records"])       # tuple subclass nested in an exact dict
    with pytest.raises(R4SidecarError) as ei:
        verify_sealed_report(report)
    assert "exact built-in" in str(ei.value)
    assert fired["n"] == 0                                      # the __iter__ callback NEVER ran


def test_rev10_standalone_manifest_validator_refuses_a_hostile_subclass(monkeypatch):
    import p5_r4_sidecar
    monkeypatch.setattr(p5_r4_sidecar, "_diversity_agreement_rho", p5_r4_sidecar._diversity_agreement_rho)
    fired = {"n": 0}

    class _HostileManifest(dict):
        def items(self):
            fired["n"] += 1
            p5_r4_sidecar._diversity_agreement_rho = lambda j, s: 1.0
            return super().items()

    man = _HostileManifest(_manifest(_sealed_report()))
    r = validate_sidecar_manifest(man)                         # standalone public validator
    assert any("exact built-in" in x for x in r)               # subclass refused at sanitize (returns list)
    assert fired["n"] == 0                                      # the items() callback NEVER ran


def test_rev10_publish_refuses_an_active_pathlike_sidecar_path(tmp_path):
    # (Codex #1206 pass2) Path(sidecar_path) invokes a caller os.PathLike's __fspath__, which can rebind
    # a live helper (e.g. _build_decision) BEFORE record/report validation -> a-Codex forged an
    # integrity_verified / c1=true artifact this way. rev10 rejects a custom os.PathLike before any
    # verdict path (the report/journal paths in the seam get the same guard).
    import p5_r4_sidecar
    report = _sealed_report(n=4)
    rec = _build(report, agree=False)                          # anti-correlated => must NOT green
    orig = p5_r4_sidecar._build_decision
    fired = {"n": 0}

    class _EvilPath(os.PathLike):
        def __init__(self, p):
            self.p = str(p)

        def __fspath__(self):
            fired["n"] += 1
            p5_r4_sidecar._build_decision = lambda *a, **k: {"state": "jsd_proceeds",
                                                             "c1_authorization_permitted": True}
            return self.p

    try:
        with pytest.raises(R4SidecarError) as ei:
            publish_r4_sidecar(report, rec, _EvilPath(tmp_path / "r4.json"))
        assert "path-like" in str(ei.value)                    # rev11: exact-str-only refuses it too
        assert fired["n"] == 0                                  # __fspath__ NEVER ran
    finally:
        p5_r4_sidecar._build_decision = orig


def test_rev10_public_comparison_validator_has_no_row_keys_knob():
    # (Codex #1206 pass2) a caller row_keys iterable's __iter__ (via set(row_keys)) could rebind
    # _validate_aggregate so a mismatched aggregate returns [] as clean. rev10 removes the knob from the
    # public API; the CANON row shape is internal-only.
    import inspect

    import p5_r4_sidecar
    assert "row_keys" not in inspect.signature(p5_r4_sidecar.validate_comparison).parameters
    with pytest.raises(TypeError):                              # the knob is gone
        p5_r4_sidecar.validate_comparison([], {"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0,
                                               "mean_pairwise_embedding": 0.0, "n_pairs": 0},
                                          row_keys=frozenset())


def test_the_public_c1_gates_reject_a_caller_supplied_authority():
    # (a-Codex #1201 pass 2) A public `authority` param on the C1 gate is a trivial bypass: a caller
    # passes _auth()._replace(gate=-2.0) so anti-correlated evidence greens. The public gates take NO
    # caller authority; threading lives ONLY behind the private _r4_decision / _publish_r4_sidecar
    # workers. Forging via the public gate is a TypeError, and the genuine gate still refuses.
    import inspect

    import p5_r4_sidecar
    for fn in ("r4_decision", "publish_r4_sidecar", "build_r4_sidecar"):
        params = inspect.signature(getattr(p5_r4_sidecar, fn)).parameters
        assert not any("authorit" in p for p in params), f"{fn} exposes a caller authority param"
    report = _sealed_report(n=4)
    rec = _build(report, agree=False)                          # rho ~ -1 => must be replacement
    with pytest.raises(TypeError):                             # public gate has no authority param
        r4_decision(report, rec, authority=p5_r4_sidecar._auth()._replace(gate=-2.0))
    d = r4_decision(report, rec)
    assert d["state"] == DECISION_JSD_REPLACEMENT_REQUIRED and d["c1_authorization_permitted"] is False


def test_the_public_standalone_verifiers_reject_a_caller_supplied_authority():
    # (a-Codex #1201 pass 3) verify_sealed_report / validate_* are PUBLIC, documented verifiers that
    # audit callers invoke DIRECTLY and trust. A public authority param let a caller pass
    # _auth()._replace(model_keys=...+'unbound_extra') and get a producer-invalid report "verified" —
    # a standalone-verifier bypass independent of the C1 gate. The public verifiers take NO caller
    # authority; threading lives behind the private _verify_sealed_report / _validate_* workers.
    import inspect

    import p5_r4_sidecar
    for fn in ("verify_sealed_report", "validate_sidecar_manifest", "validate_comparison"):
        params = inspect.signature(getattr(p5_r4_sidecar, fn)).parameters
        assert not any("authorit" in p for p in params), f"{fn} exposes a caller authority param"
    report = _sealed_report()
    report["execution_descriptor"]["model"]["unbound_extra"] = "accepted"   # producer-invalid
    _reseal(report)
    forged = p5_r4_sidecar._auth()._replace(
        model_keys=frozenset(list(p5_r4_sidecar._auth().model_keys) + ["unbound_extra"]))
    with pytest.raises(TypeError):                             # public verifier has no authority param
        verify_sealed_report(report, authority=forged)
    with pytest.raises(R4SidecarError):                        # genuine public verifier refuses it
        verify_sealed_report(report)


# =========================================================================== #
# rev11 (wolf-Codex #1209) — five edge-case closures. Each RED->GREEN, each    #
# mutation-verified load-bearing (revert its fix -> the probe below fails).     #
# =========================================================================== #
def test_rev11_p1_safe_path_refuses_an_exact_path_object(tmp_path):
    # rev10 accepted exact stdlib pathlib types by identity. An exact Path is a MUTABLE carrier whose
    # first filesystem op runs caller code from its parts. rev11 accepts ONLY an exact str at the
    # boundary, so even a pristine Path object is refused BEFORE any use.
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    with pytest.raises(R4SidecarError) as ei:
        publish_r4_sidecar(report, rec, tmp_path / "r4.json")   # an exact Path, not a str
    assert "exact str path" in str(ei.value)


def test_rev11_p1_publish_refuses_an_exact_path_with_hostile_raw_paths_before_any_callback(tmp_path):
    # Codex #1209 P1 exact probe: an exact Path given a callback-bearing str in _raw_paths via
    # object.__setattr__ forged integrity_verified/c1=true by rebinding _build_decision during the
    # first path-part normalization. rev11 refuses the Path (type is not str) BEFORE any fs op, so the
    # hostile str method never runs and the anti-correlated decision is never forged.
    import p5_r4_sidecar
    report = _sealed_report(n=4)
    rec = _build(report, agree=False)                           # anti-correlated => must NOT green
    orig = p5_r4_sidecar._build_decision
    fired = {"n": 0}

    class _EvilStr(str):
        def __getattribute__(self, name):
            if not name.startswith("__"):                       # any method the normalization calls
                fired["n"] += 1
                p5_r4_sidecar._build_decision = lambda *a, **k: {
                    "state": "jsd_proceeds", "c1_authorization_permitted": True}
            return str.__getattribute__(self, name)

    target = str(tmp_path / "r4.json")
    p = pathlib.Path(target)                                    # an exact WindowsPath/PosixPath
    object.__setattr__(p, "_raw_paths", [_EvilStr(target)])     # tamper the mutable internal parts
    try:
        with pytest.raises(R4SidecarError) as ei:
            publish_r4_sidecar(report, rec, p)
        assert "exact str path" in str(ei.value)
        assert fired["n"] == 0                                  # no path-part method ran
        assert p5_r4_sidecar._build_decision is orig           # _build_decision never rebound
        assert not (tmp_path / "r4.json").exists()             # no artifact was forged
    finally:
        p5_r4_sidecar._build_decision = orig


def test_rev11_p1_directory_open_fault_downgrades_not_verified(tmp_path, monkeypatch):
    # Codex #1209 P1: rev10 mapped EVERY directory-open OSError to None (unsupported), so a real
    # supported-platform EIO/EMFILE/EACCES fault left the artifact integrity_verified. rev11 mirrors
    # the producer's capability split: None comes ONLY from missing os.O_DIRECTORY; a supported-platform
    # open fault PROPAGATES and the publisher downgrades to committed_indeterminate.
    import errno
    import p5_r4_sidecar
    # Present a platform that CAN open a directory fd (has O_DIRECTORY) but whose dir-open FAULTS.
    monkeypatch.setattr(p5_r4_sidecar.os, "O_DIRECTORY",
                        getattr(os, "O_DIRECTORY", 0x10000), raising=False)
    real_open = p5_r4_sidecar.os.open

    def fault_on_directory_open(path, flags, *a, **k):
        if flags & p5_r4_sidecar.os.O_DIRECTORY:                # ONLY the directory O_RDONLY open faults
            raise OSError(errno.EIO, "simulated directory-open durability fault")
        return real_open(path, flags, *a, **k)

    monkeypatch.setattr(p5_r4_sidecar.os, "open", fault_on_directory_open)
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    result = publish_r4_sidecar(report, rec, str(tmp_path / "r4.json"))
    assert result.disposition == DISPOSITION_INDETERMINATE     # NOT integrity_verified after the fault


def test_rev11_p1_directory_open_unsupported_is_not_a_fault(tmp_path, monkeypatch):
    # The other half of the split: a platform with NO os.O_DIRECTORY (e.g. Windows) cannot open a dir
    # fd; the file was already fsync'd, so that is NOT a durability fault and must NOT downgrade.
    import p5_r4_sidecar
    monkeypatch.delattr(p5_r4_sidecar.os, "O_DIRECTORY", raising=False)
    assert p5_r4_sidecar._fsync_dir(tmp_path) is None           # capability-None, not a fault
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    result = publish_r4_sidecar(report, rec, str(tmp_path / "r4.json"))
    assert result.disposition == DISPOSITION_VERIFIED           # unsupported dir-sync does not downgrade


def test_rev11_p2_eligible_probe_ids_are_typed_and_total():
    # Codex #1209 P2: validate_comparison must TYPE its eligible_probe_ids root/elements before set()/
    # sorted() — no raw TypeError and no false-clean []. Every malformed shape is a typed refusal.
    agg = {"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0, "mean_pairwise_embedding": 0.0, "n_pairs": 0}
    for bad in ([[]], "a", {"a": "x"}, [1], ["a", "a"]):
        r = validate_comparison([], agg, eligible_probe_ids=bad)
        assert isinstance(r, list) and r and all(isinstance(x, str) for x in r), bad
        assert not any("unhashable" in x for x in r), bad       # never a leaked raw TypeError


def test_rev11_p2_huge_int_record_count_is_a_typed_refusal(tmp_path):
    # Codex #1209 P2: a record_count of 10**5000 (>4300 digits) must be a typed refusal, not a raw
    # ValueError from a later str()/repr()/json.dumps of the untrusted int.
    report = _sealed_report(n=4)
    report["record_count"] = 10 ** 5000
    with pytest.raises(R4SidecarError):
        verify_sealed_report(report)


def test_rev11_p2_huge_int_sequence_length_is_a_typed_refusal(tmp_path):
    # Codex #1209 P2 / #1211 finding 3: parent.sequence_length = 10**5000 must escape build_r4_sidecar
    # as a typed refusal FROM THE MAGNITUDE GUARD. Use an EMPTY comparison + the canonical zero
    # aggregate so no eligibility/endpoint check can fire first (Codex #1211: the old test with stale
    # rows passed for the WRONG reason — the huge length made every row ineligible and the endpoint
    # check refused before the int guard ran). Assert the SPECIFIC magnitude diagnostic so the test
    # goes RED when _int_is_serialization_safe is bypassed (then json conversion raises a raw
    # ValueError, not this R4SidecarError).
    report = _sealed_report(n=4)
    manifest = _manifest(report, _L)
    manifest["parent"]["sequence_length"] = 10 ** 5000
    zero_agg = {"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0,
                "mean_pairwise_embedding": 0.0, "n_pairs": 0}
    with pytest.raises(R4SidecarError, match="too large to canonicalize safely"):
        build_r4_sidecar(manifest, sealed_report=report, per_pair=[], aggregate=zero_agg)


def test_rev11_p2_correlation_helpers_are_private_and_total():
    # Codex #1209 P2: the traversing/numeric helpers are privatized (no public entry traverses caller
    # values), and the numeric workers are total over their length contract — equal-length only, empty
    # is a defined 0.0, mismatched length is a typed refusal (was a silent wrong rho / ZeroDivisionError).
    import p5_r4_sidecar
    for public_name in ("partition_eligibility", "derive_generation_corpus_digest",
                        "spearman_rho", "diversity_agreement_rho"):
        assert not hasattr(p5_r4_sidecar, public_name), public_name   # privatized
    assert p5_r4_sidecar._spearman_rho([], []) == 0.0                  # empty -> defined, no ZeroDivision
    with pytest.raises(R4SidecarError):
        p5_r4_sidecar._spearman_rho([1.0, 2.0], [1.0])                 # mismatched length -> refusal
    with pytest.raises(R4SidecarError):
        p5_r4_sidecar._diversity_agreement_rho([0.5], [0.5, 0.5])      # mismatched length -> refusal


def test_rev11_p2_huge_int_respects_a_lower_configured_digit_limit():
    # a-Codex #1209 follow-up: a fixed 8192-bit cap assumed CPython's 4300-digit default. Under a lower
    # configured PYTHONINTMAXSTRDIGITS (floor 640), an int that slips a fixed bit cap but exceeds the
    # ACTIVE decimal limit (e.g. 10**1000 under limit 640) must still be a typed refusal, not a raw
    # ValueError from the refusal's repr(). The bound derives from the active limit.
    prev = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        report = _sealed_report(n=4)
        report["record_count"] = 10 ** 1000                    # 1001 digits > 640; ~3322 bits < 8192
        with pytest.raises(R4SidecarError):                    # typed refusal, NOT a raw ValueError
            verify_sealed_report(report)
    finally:
        sys.set_int_max_str_digits(prev)


# =========================================================================== #
# rev12 (wolf-Codex #1211 findings 1-2 + Fable's 4th) — each RED->GREEN,        #
# mutation-verified load-bearing.                                               #
# =========================================================================== #
def test_rev12_p2_empty_eligible_id_is_a_typed_refusal():
    # Codex #1211 finding 2 + #1213 correction: the standalone validator must reject an EMPTY probe id
    # (producer/parent contract = exact NON-EMPTY str), but must NOT over-reject a whitespace or
    # placeholder-looking id the producer actually accepts (#1213 walked back the rev11 is_unset wording;
    # is_unset placeholder policy belongs to config ids, not producer-emitted probe ids).
    zero = {"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0, "mean_pairwise_embedding": 0.0, "n_pairs": 0}
    for bad in ([""], ["a", ""]):
        r = validate_comparison([], zero, eligible_probe_ids=bad)
        assert isinstance(r, list) and r, bad
        assert any("eligible_probe_ids entry" in x for x in r), bad
    for producer_ok in (["   "], ["todo"], ["none"]):          # valid producer ids -> NOT an id refusal
        r = validate_comparison([], zero, eligible_probe_ids=producer_ok)
        assert not any("eligible_probe_ids entry" in x for x in r), producer_ok


def _write_governed_pair(tmp_path, report_bytes):
    rp = tmp_path / "b0.json"
    jp = tmp_path / "b0.json.journal"
    rp.write_bytes(report_bytes)
    jp.write_text("", encoding="utf-8")
    return str(rp), str(jp)


def test_rev12_p2_governed_json_invalid_utf8_is_a_typed_refusal(tmp_path):
    # Codex #1211 finding 1: invalid UTF-8 in the governed report file raises UnicodeDecodeError from
    # json.loads BEFORE the sanitizer runs; the seam must translate it to R4SidecarError.
    import p5_r4_sidecar
    rp, jp = _write_governed_pair(tmp_path, b'{"a": "\xff\xfe"}')
    with pytest.raises(R4SidecarError, match="could not be decoded"):
        p5_r4_sidecar._load_governed_report(rp, jp)


def test_rev12_p2_governed_json_huge_int_under_low_limit_is_a_typed_refusal(tmp_path):
    # Codex #1211 finding 1: a JSON integer exceeding the ACTIVE int<->str digit limit raises a raw
    # ValueError from json's int conversion — at the FILE seam, before the in-memory guard.
    import p5_r4_sidecar
    prev = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        rp, jp = _write_governed_pair(tmp_path, b'[' + b'1' * 641 + b']')
        with pytest.raises(R4SidecarError, match="could not be decoded"):
            p5_r4_sidecar._load_governed_report(rp, jp)
    finally:
        sys.set_int_max_str_digits(prev)


def test_rev12_p2_governed_json_deep_nesting_is_a_typed_refusal(tmp_path):
    # Codex #1211 finding 1: excessively nested valid JSON raises RecursionError from json.loads.
    import p5_r4_sidecar
    rp, jp = _write_governed_pair(tmp_path, b'[' * 200000 + b']' * 200000)
    with pytest.raises(R4SidecarError, match="could not be decoded"):
        p5_r4_sidecar._load_governed_report(rp, jp)


def test_rev12_p2_nul_byte_sidecar_path_is_a_typed_refusal(tmp_path):
    # Fable (4th finding, same class as the rev11 P1): an exact str with an embedded NUL slips
    # _safe_path's type check and the pre-flight probes (which swallow ValueError), then surfaces as a
    # raw ValueError("embedded null character") from tempfile.mkstemp — a raw escape from the public
    # publish entry. rev12 refuses it at the path boundary before any verdict/staging work.
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    evil = str(tmp_path / "r4.json") + "\x00evil"
    with pytest.raises(R4SidecarError, match="NUL"):
        publish_r4_sidecar(report, rec, evil)
    assert list(tmp_path.glob("*.tmp")) == []                  # no staging file was ever created


# =========================================================================== #
# rev13 (wolf-Codex #1213) — os.link ambiguity P1 + 3 P2s. RED->GREEN + mutation.#
# =========================================================================== #
def test_rev13_p1_link_effect_then_error_is_indeterminate_not_escaped(tmp_path, monkeypatch):
    # Codex #1213 P1: os.link is EFFECTFUL. A real-link-then-raise left a digest-valid C1-green final
    # PLUS its writable same-inode temp alias while the API raised and emitted no disposition. rev13
    # makes the commit ambiguity-aware: reconcile by inode, enter the terminal flow at
    # committed_indeterminate, remove the alias, and NEVER escape.
    import errno
    import p5_r4_sidecar
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    out = tmp_path / "r4.json"
    real_link = p5_r4_sidecar.os.link

    def link_then_raise(src, dst):
        real_link(src, dst)                                    # the real commit effect
        raise OSError(errno.EIO, "effect-then-error")

    monkeypatch.setattr(p5_r4_sidecar.os, "link", link_then_raise)
    result = publish_r4_sidecar(report, rec, str(out))         # must NOT raise
    assert result.disposition == DISPOSITION_INDETERMINATE     # ambiguous commit -> never verified
    assert out.exists()                                        # the artifact did commit
    assert list(tmp_path.glob("*.tmp")) == []                  # the writable alias was removed
    assert len(result.published_digest) == 64                  # digest-valid


def test_rev13_p1_link_no_effect_failure_cleans_temp_and_raises(tmp_path, monkeypatch):
    # The other half: a link that has NO effect (or a foreign no-replace winner) is a native operational
    # OSError that stays non-authorizing AND cleans its temp.
    import errno
    import p5_r4_sidecar
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    monkeypatch.setattr(p5_r4_sidecar.os, "link",
                        lambda src, dst: (_ for _ in ()).throw(OSError(errno.EIO, "no effect")))
    with pytest.raises(OSError):                               # operational OSError stays native
        publish_r4_sidecar(report, rec, str(tmp_path / "r4.json"))
    assert list(tmp_path.glob("*.tmp")) == []                  # temp cleaned on the failed commit path
    assert not (tmp_path / "r4.json").exists()                 # nothing committed


def test_rev13_p2_staging_write_fault_cleans_temp(tmp_path, monkeypatch):
    # Codex #1213 P2-3: an os.write fault must best-effort remove the temp (rev12 leaked it). Operational
    # OSError stays native (not converted to a structural refusal).
    import errno
    import p5_r4_sidecar
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    monkeypatch.setattr(p5_r4_sidecar.os, "write",
                        lambda fd, data: (_ for _ in ()).throw(OSError(errno.EIO, "write fault")))
    with pytest.raises(OSError):
        publish_r4_sidecar(report, rec, str(tmp_path / "r4.json"))
    assert list(tmp_path.glob("*.tmp")) == []                  # no leaked temp


def test_rev13_p2_staging_readback_mismatch_cleans_temp(tmp_path, monkeypatch):
    # Codex #1213 P2-3: a staged-bytes readback mismatch stays a TYPED refusal AND cleans the temp.
    import p5_r4_sidecar
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    real_read = p5_r4_sidecar.Path.read_bytes

    def corrupt_readback(self):
        data = real_read(self)
        return data + b"x" if str(self).endswith(".tmp") else data

    monkeypatch.setattr(p5_r4_sidecar.Path, "read_bytes", corrupt_readback)
    with pytest.raises(R4SidecarError, match="did not verify before commit"):
        publish_r4_sidecar(report, rec, str(tmp_path / "r4.json"))
    assert list(tmp_path.glob("*.tmp")) == []                  # no leaked temp


def _write_governed_report_ok(tmp_path):
    rp = tmp_path / "b0.json"
    jp = tmp_path / "b0.json.journal"
    rp.write_bytes(json.dumps({"published_digest": "a" * 64}).encode("utf-8"))
    return rp, jp


def test_rev13_p2_journal_invalid_utf8_is_a_typed_refusal(tmp_path):
    # Codex #1213 P2: the JOURNAL half of the governed pair — malformed journal decode must be typed too.
    import p5_r4_sidecar
    rp, jp = _write_governed_report_ok(tmp_path)
    jp.write_bytes(b'{\xff\xfe}')
    with pytest.raises(R4SidecarError, match="journal could not be decoded"):
        p5_r4_sidecar._load_governed_report(str(rp), str(jp))


def test_rev13_p2_journal_huge_int_under_low_limit_is_a_typed_refusal(tmp_path):
    import p5_r4_sidecar
    prev = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        rp, jp = _write_governed_report_ok(tmp_path)
        jp.write_bytes(b'[' + b'1' * 641 + b']')
        with pytest.raises(R4SidecarError, match="journal could not be decoded"):
            p5_r4_sidecar._load_governed_report(str(rp), str(jp))
    finally:
        sys.set_int_max_str_digits(prev)


def test_rev13_p2_journal_deep_nesting_is_a_typed_refusal(tmp_path):
    import p5_r4_sidecar
    rp, jp = _write_governed_report_ok(tmp_path)
    jp.write_bytes(b'[' * 200000 + b']' * 200000)
    with pytest.raises(R4SidecarError, match="journal could not be decoded"):
        p5_r4_sidecar._load_governed_report(str(rp), str(jp))


def test_rev13_p2_producer_probe_id_todo_is_accepted():
    # Codex #1213 P2: a placeholder-LOOKING probe id ("todo") is a VALID producer probe id. The parent
    # verifier must accept it and the standalone eligible list must not over-reject it (rev12 is_unset
    # rejected both, making the public validator incompatible with a governed parent the module accepts).
    report = _sealed_report(n=2, ids=["todo", "none"])
    assert verify_sealed_report(report)                        # parent verifier accepts non-empty ids
    zero = {"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0, "mean_pairwise_embedding": 0.0, "n_pairs": 0}
    r = validate_comparison([], zero, eligible_probe_ids=["todo", "none"])
    assert not any("eligible_probe_ids entry" in x for x in r)


def test_rev13_fsencode_unencodable_path_is_a_typed_refusal(tmp_path, monkeypatch):
    # Codex #1213: the os.fsencode branch (platform-unencodable name, e.g. a POSIX lone surrogate) needs
    # a dedicated regression — the Windows runtime uses surrogate-pass, so drive the branch directly.
    import p5_r4_sidecar
    report = _sealed_report(n=4)
    rec = _build(report, agree=True)
    monkeypatch.setattr(p5_r4_sidecar.os, "fsencode",
                        lambda p: (_ for _ in ()).throw(UnicodeEncodeError("utf-8", "x", 0, 1, "bad")))
    with pytest.raises(R4SidecarError, match="encodable"):
        publish_r4_sidecar(report, rec, str(tmp_path / "r4.json"))
