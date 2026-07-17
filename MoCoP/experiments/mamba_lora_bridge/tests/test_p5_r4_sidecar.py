"""Model-free tests for the P5 R4 comparison sidecar (#155 item 5; Codex #1137 rev 2).

No torch, no sentence_transformers, no model, no GPU. The evaluator is faked: this module's job is
CUSTODY of a comparison, not the comparison. The parent bindings are DERIVED from a real sealed B0
report, so the tests build one rather than passing digests by hand.
"""
import json
from itertools import combinations

import pytest

from p5_b0_harness import canonical_digest
from p5_r4_sidecar import (
    SIDECAR_SCHEMA,
    R4SidecarError,
    R4SidecarRecord,
    bind_to_parent_report,
    build_r4_sidecar,
    derive_generation_corpus_digest,
    publish_r4_sidecar,
    spearman_rho,
    validate_comparison,
    validate_sidecar_manifest,
)

PANEL_HASH = "primary-holdout-ff5e596304c6b8c4b93c"
EVAL_SHA = "c" * 40


def _sealed_report(n=3):
    """A minimally realistic sealed B0 report: n probes, each with a generation receipt."""
    records = []
    for i in range(n):
        records.append({
            "probe_id": f"probe{i}",
            "raw_generation": f"gen{i}",
            "provenance": {
                "input_token_ids_sha256": canonical_digest(f"in{i}"),
                "generated_token_ids_sha256": canonical_digest(f"out{i}"),
                "token_count": 10 + i,
                "stop_reason": "eos",
            },
        })
    report = {"schema_version": "b0-evidence-bundle-v1", "record_count": n, "records": records}
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items()})
    return report


def _pairs_for(report):
    """A complete, self-consistent comparison over the report's probes."""
    ids = sorted(r["probe_id"] for r in report["records"])
    rows = []
    for a, b in combinations(ids, 2):
        # Deterministic, in-range, and correlated so recomputed rho is well-defined.
        h = int(canonical_digest(a + b)[:6], 16) / 0xFFFFFF
        rows.append({"pair_id": f"{a}|{b}", "jsd": round(0.2 + 0.5 * h, 6),
                     "embedding_similarity": round(0.9 - 0.5 * h, 6)})
    return rows


def _agg_for(rows):
    jsds = [r["jsd"] for r in rows]
    sims = [r["embedding_similarity"] for r in rows]
    return {
        "spearman_rho": spearman_rho(jsds, sims),
        "mean_pairwise_jsd": sum(jsds) / len(jsds),
        "mean_pairwise_embedding": sum(sims) / len(sims),
        "n_pairs": len(rows),
    }


def _manifest(report, **over):
    m = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {"evaluator_id": "sentence-transformers/all-MiniLM-L6-v2",
                      "revision_sha": EVAL_SHA},
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "parent": {
            "b0_report_digest": report["published_digest"],
            "generation_output_digest": derive_generation_corpus_digest(report),
            "sequence_length": 160,
        },
        "panel": PANEL_HASH,
    }
    m.update(over)
    return m


def _build(report=None, **over):
    report = report or _sealed_report()
    rows = over.pop("per_pair", None) or _pairs_for(report)
    agg = over.pop("aggregate", None) or _agg_for(rows)
    manifest = over.pop("manifest", None) or _manifest(report)
    return build_r4_sidecar(manifest, sealed_report=report, per_pair=rows, aggregate=agg)


# --------------------------------------------------------------------------- #
# Happy path.                                                                  #
# --------------------------------------------------------------------------- #
def test_clean_sidecar_builds_and_binds():
    report = _sealed_report()
    rec = _build(report)
    assert len(rec.output_digest) == 64
    link = bind_to_parent_report(report, rec)
    assert link["b0_published_digest"] == report["published_digest"]
    assert link["sidecar_output_digest"] == rec.output_digest


def test_clean_manifest_validates():
    assert validate_sidecar_manifest(_manifest(_sealed_report())) == []


# --------------------------------------------------------------------------- #
# Codex #1137 F1 — deep-frozen record; no stale seal.                          #
# --------------------------------------------------------------------------- #
def test_sealed_record_cannot_be_mutated_in_place():
    rec = _build()
    with pytest.raises((TypeError, AttributeError)):
        rec.record["evaluator"]["revision_sha"] = "0" * 40    # MappingProxyType is read-only
    with pytest.raises((TypeError, AttributeError)):
        rec.record["per_pair"][0]["jsd"] = 99                 # tuple/proxy, read-only


def test_a_stale_or_tampered_output_digest_cannot_link():
    rec = _build()
    forged = R4SidecarRecord(manifest_digest=rec.manifest_digest,
                             output_digest="0" * 64, record=rec.record)
    with pytest.raises(R4SidecarError) as ei:
        bind_to_parent_report(_sealed_report(), forged)
    assert "does not match the record content digest" in str(ei.value)


# --------------------------------------------------------------------------- #
# Codex #1137 F2 — snapshot once; a two-view input cannot smuggle strings past. #
# --------------------------------------------------------------------------- #
def test_two_view_sequence_is_snapshotted_before_validation():
    report = _sealed_report(n=2)          # exactly one pair; simplest complete set
    ids = sorted(r["probe_id"] for r in report["records"])
    good = [{"pair_id": f"{ids[0]}|{ids[1]}", "jsd": 0.3, "embedding_similarity": 0.7}]
    bad = [{"pair_id": f"{ids[0]}|{ids[1]}", "jsd": "XXX", "embedding_similarity": "YYY"}]

    class TwoView(list):
        """A real Sequence that yields valid rows on the FIRST iteration, garbage on the next."""
        def __init__(self):
            super().__init__(good)
            self._n = 0

        def __iter__(self):
            self._n += 1
            return iter(good if self._n == 1 else bad)

    agg = _agg_for(good)
    rec = build_r4_sidecar(_manifest(report), sealed_report=report,
                           per_pair=TwoView(), aggregate=agg)
    # Whatever was validated is EXACTLY what is sealed: the snapshot froze the first read.
    assert rec.record["per_pair"][0]["jsd"] == 0.3
    assert all(isinstance(r["jsd"], float) for r in rec.record["per_pair"])


# --------------------------------------------------------------------------- #
# Codex #1137 F3 — parent bindings DERIVED from the report, not self-attested.  #
# --------------------------------------------------------------------------- #
def test_generation_digest_is_derived_from_the_report_receipts():
    report = _sealed_report()
    d = derive_generation_corpus_digest(report)
    assert len(d) == 64
    # Change a single receipt -> the derived digest changes -> a stale manifest is refused.
    report2 = _sealed_report()
    report2["records"][1]["provenance"]["generated_token_ids_sha256"] = canonical_digest("changed")
    assert derive_generation_corpus_digest(report2) != d


def test_a_generation_digest_the_report_did_not_produce_is_refused():
    report = _sealed_report()
    m = _manifest(report)
    m["parent"]["generation_output_digest"] = "f" * 64      # not what the report produced
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(m, sealed_report=report, per_pair=_pairs_for(report),
                         aggregate=_agg_for(_pairs_for(report)))
    assert "never a second generation" in str(ei.value)


def test_a_report_digest_mismatch_is_refused():
    report = _sealed_report()
    m = _manifest(report)
    m["parent"]["b0_report_digest"] = "a" * 64
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(m, sealed_report=report, per_pair=_pairs_for(report),
                         aggregate=_agg_for(_pairs_for(report)))
    assert "does not describe that run" in str(ei.value)


def test_an_unsealed_report_is_refused():
    report = _sealed_report()
    del report["published_digest"]
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(_sealed_report()), sealed_report=report,
                         per_pair=_pairs_for(report), aggregate=_agg_for(_pairs_for(report)))
    assert "not sealed" in str(ei.value)


# --------------------------------------------------------------------------- #
# Codex #1137 F4 — range, completeness, recomputation.                         #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("field,value", [("jsd", -7.0), ("jsd", 1.5),
                                         ("embedding_similarity", 3.5),
                                         ("embedding_similarity", -1.5)])
def test_out_of_range_comparison_values_are_refused(field, value):
    report = _sealed_report()
    rows = _pairs_for(report)
    rows[0][field] = value
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows,
                         aggregate=_agg_for(rows))
    assert field in str(ei.value) and "must be in" in str(ei.value)


@pytest.mark.parametrize("rho", [2.0, -2.0])
def test_out_of_range_rho_is_refused(rho):
    report = _sealed_report()
    rows = _pairs_for(report)
    agg = _agg_for(rows)
    agg["spearman_rho"] = rho
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
    assert "spearman_rho must be in" in str(ei.value)


def test_incomplete_pair_set_is_refused():
    report = _sealed_report(n=4)          # C(4,2) = 6 pairs expected
    rows = _pairs_for(report)[:3]         # cherry-pick 3
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows,
                         aggregate=_agg_for(rows))
    assert "complete set is 6" in str(ei.value)


def test_a_fabricated_rho_unrelated_to_the_rows_is_refused():
    # The teeth: a caller declares an in-range, passing-looking rho that its rows do not support.
    report = _sealed_report()
    rows = _pairs_for(report)
    agg = _agg_for(rows)
    agg["spearman_rho"] = 0.999          # in range, but not what the rows compute to
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
    assert "recomputed from the rows" in str(ei.value)


def test_a_fabricated_mean_is_refused():
    report = _sealed_report()
    rows = _pairs_for(report)
    agg = _agg_for(rows)
    agg["mean_pairwise_jsd"] = agg["mean_pairwise_jsd"] + 0.1
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows, aggregate=agg)
    assert "mean_pairwise_jsd" in str(ei.value) and "recomputed" in str(ei.value)


def test_non_numeric_comparison_is_refused():
    report = _sealed_report(n=2)
    ids = sorted(r["probe_id"] for r in report["records"])
    rows = [{"pair_id": f"{ids[0]}|{ids[1]}", "jsd": "not-a-number",
             "embedding_similarity": "also-not"}]
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows,
                         aggregate={"spearman_rho": 0.0, "mean_pairwise_jsd": 0.0,
                                    "mean_pairwise_embedding": 0.0, "n_pairs": 1})
    assert "jsd must be a finite number" in str(ei.value)


def test_spearman_rho_matches_a_known_case():
    # Perfect inverse rank order -> rho = -1.
    assert spearman_rho([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)
    assert spearman_rho([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)
    # A constant axis has no rank correlation -> 0.0 (not a division error).
    assert spearman_rho([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) == 0.0


def test_duplicate_pair_ids_are_refused():
    report = _sealed_report(n=3)
    rows = _pairs_for(report)
    rows[1]["pair_id"] = rows[0]["pair_id"]
    with pytest.raises(R4SidecarError) as ei:
        build_r4_sidecar(_manifest(report), sealed_report=report, per_pair=rows,
                         aggregate=_agg_for(rows))
    assert "duplicates pair_id" in str(ei.value)


def test_validate_comparison_standalone_accumulates_faults():
    r = validate_comparison(
        per_pair=[{"pair_id": "", "jsd": 5.0, "embedding_similarity": None}],
        aggregate={"spearman_rho": "y", "n_pairs": 0})
    assert any("pair_id" in x for x in r)
    assert any("jsd must be in" in x for x in r)
    assert any("embedding_similarity" in x for x in r)
    assert any("spearman_rho" in x for x in r)


# --------------------------------------------------------------------------- #
# Codex #1137 F1 (revision) — evaluator provenance still strict.               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("rev", ["main", "HEAD", "latest", 123, "", "c" * 39, "C" * 40])
def test_bad_evaluator_revision_is_refused(rev):
    m = _manifest(_sealed_report(), evaluator={"evaluator_id": "x", "revision_sha": rev})
    assert any("revision_sha" in x for x in validate_sidecar_manifest(m))


@pytest.mark.parametrize("bad", ["160", 160.0, True, 0, -1, None])
def test_sequence_length_must_be_exact_positive_int(bad):
    report = _sealed_report()
    m = _manifest(report)
    m["parent"]["sequence_length"] = bad
    assert any("sequence_length" in x for x in validate_sidecar_manifest(m))


# --------------------------------------------------------------------------- #
# Codex #1137 F5 — atomic no-replace publication + terminal disposition.       #
# --------------------------------------------------------------------------- #
def test_publish_writes_an_atomic_artifact_bound_to_the_parent(tmp_path):
    report = _sealed_report()
    rec = _build(report)
    out = tmp_path / "r4_sidecar.json"
    committed, digest = publish_r4_sidecar(report, rec, out)
    assert out.exists()
    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["disposition"] == "r4_comparison_recorded"
    assert artifact["published_digest"] == digest
    # The artifact binds the parent WITHOUT the parent being mutated.
    assert artifact["link"]["b0_published_digest"] == report["published_digest"]
    assert "sidecar" not in json.dumps(report)
    # Bytes on disk are exactly the committed bytes, and the digest recomputes.
    assert out.read_bytes() == committed
    recomputed = canonical_digest({k: v for k, v in artifact.items() if k != "published_digest"})
    assert recomputed == digest


def test_publish_is_no_replace(tmp_path):
    report = _sealed_report()
    rec = _build(report)
    out = tmp_path / "r4_sidecar.json"
    publish_r4_sidecar(report, rec, out)
    with pytest.raises(R4SidecarError) as ei:
        publish_r4_sidecar(report, rec, out)      # second publish must not clobber
    assert "no-replace" in str(ei.value)


def test_publish_refuses_a_stale_record(tmp_path):
    report = _sealed_report()
    rec = _build(report)
    forged = R4SidecarRecord(manifest_digest=rec.manifest_digest,
                             output_digest="0" * 64, record=rec.record)
    with pytest.raises(R4SidecarError):
        publish_r4_sidecar(report, forged, tmp_path / "r4.json")


# --------------------------------------------------------------------------- #
# Scope lock (Monk #1128): out-of-process, no evaluator/torch import.          #
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
