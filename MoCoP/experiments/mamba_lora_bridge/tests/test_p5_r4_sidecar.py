"""Model-free tests for the P5 R4 comparison sidecar (#155 item 5, Monk WC #1128).

No torch, no sentence_transformers, no model, no GPU. The evaluator is faked: this module's job is
CUSTODY of a comparison, not the comparison.
"""
import json

import pytest

from p5_b0_harness import canonical_digest
from p5_r4_sidecar import (
    SIDECAR_SCHEMA,
    R4SidecarError,
    bind_to_parent_report,
    build_r4_sidecar,
    validate_sidecar_manifest,
)

PANEL_HASH = "primary-holdout-ff5e596304c6b8c4b93c"
B0_DIGEST = "a" * 64
GEN_DIGEST = "b" * 64
EVAL_SHA = "c" * 40


def _manifest(**over):
    m = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": {
            "evaluator_id": "sentence-transformers/all-MiniLM-L6-v2",
            "revision_sha": EVAL_SHA,
        },
        "runner": {"runner_id": "r4_compare_sidecar", "runner_digest": "d" * 64},
        "parent": {
            "b0_report_digest": B0_DIGEST,
            "generation_output_digest": GEN_DIGEST,
            "sequence_length": 160,
        },
        "panel": PANEL_HASH,
    }
    m.update(over)
    return m


def _pairs(n=3):
    return [{"pair_id": f"p{i}", "jsd": 0.1 * i, "embedding_similarity": 0.9 - 0.1 * i}
            for i in range(n)]


def _agg(rho=0.83):
    return {"spearman_rho": rho, "n_pairs": 3}


def _build(**over):
    kw = dict(panel_hash=PANEL_HASH, b0_report_digest=B0_DIGEST,
              generation_output_digest=GEN_DIGEST, per_pair=_pairs(), aggregate=_agg())
    kw.update(over)
    return build_r4_sidecar(kw.pop("manifest", _manifest()), **kw)


# --------------------------------------------------------------------------- #
# ACCEPT 1 — evaluator identity + IMMUTABLE revision.                          #
# --------------------------------------------------------------------------- #
def test_clean_sidecar_manifest_validates():
    assert validate_sidecar_manifest(_manifest()) == []


@pytest.mark.parametrize("rev", ["main", "master", "HEAD", "latest", "dev", "stable"])
def test_mutable_evaluator_ref_is_refused(rev):
    # The R4 comparison GATES C1. A mutable ref lets the evaluated artifact change while the
    # manifest reads identical — the same drift shape as the checkpoint generation_config (#1103):
    # vendor-controlled data moving under a frozen-looking manifest.
    m = _manifest(evaluator={"evaluator_id": "x", "revision_sha": rev})
    r = validate_sidecar_manifest(m)
    assert any("MUTABLE ref" in x for x in r)


@pytest.mark.parametrize("rev", ["", "tbd", "abc", "c" * 39, "c" * 41, "C" * 40, "z" * 40])
def test_non_immutable_evaluator_revision_is_refused(rev):
    m = _manifest(evaluator={"evaluator_id": "x", "revision_sha": rev})
    assert any("revision_sha" in x for x in validate_sidecar_manifest(m))


def test_missing_evaluator_provenance_is_refused():
    m = _manifest(evaluator={"evaluator_id": "x"})
    assert any("revision_sha" in x and "missing" in x for x in validate_sidecar_manifest(m))


def test_unknown_sidecar_key_is_refused():
    m = _manifest()
    m["surprise"] = 1
    assert any("unknown key" in x for x in validate_sidecar_manifest(m))


def test_runner_identity_is_required():
    # The sidecar's OWN provenance, not just the model's: a reader must know what executed it.
    m = _manifest(runner={"runner_id": "x"})
    assert any("runner_digest" in x for x in validate_sidecar_manifest(m))


# --------------------------------------------------------------------------- #
# ACCEPT 2 — same panel, same generations, NEVER a second generation.          #
# --------------------------------------------------------------------------- #
def test_sidecar_binds_the_same_generation_outputs():
    rec = _build()
    assert rec.record["parent"]["generation_output_digest"] == GEN_DIGEST
    assert rec.record["panel"] == PANEL_HASH


def test_a_second_generation_is_refused():
    # THE load-bearing check. If the embedding side scored a different corpus, the Spearman
    # correlation measures generation noise, not instrument agreement — and that number decides
    # whether JSD is admissible at all.
    with pytest.raises(R4SidecarError) as ei:
        _build(generation_output_digest="f" * 64)
    assert "never a second generation" in str(ei.value)


def test_wrong_parent_report_is_refused():
    with pytest.raises(R4SidecarError) as ei:
        _build(b0_report_digest="e" * 64)
    assert "does not describe that run" in str(ei.value)


def test_panel_drift_is_refused():
    with pytest.raises(R4SidecarError) as ei:
        _build(panel_hash="some-other-panel")
    assert "frozen SEV panel" in str(ei.value)


# --------------------------------------------------------------------------- #
# ACCEPT 3 — per-pair + aggregate output, SHA-256 bound.                       #
# --------------------------------------------------------------------------- #
def test_per_pair_and_aggregate_are_emitted_and_digested():
    rec = _build()
    assert len(rec.record["per_pair"]) == 3
    assert rec.record["aggregate"]["spearman_rho"] == 0.83
    assert len(rec.output_digest) == 64
    assert rec.output_digest == canonical_digest(rec.record)


def test_output_digest_is_deterministic_and_content_bound():
    a = _build()
    b = _build()
    assert a.output_digest == b.output_digest
    c = _build(aggregate=_agg(rho=0.42))
    assert c.output_digest != a.output_digest      # a different verdict is a different artifact


def test_empty_comparison_is_refused():
    with pytest.raises(R4SidecarError) as ei:
        _build(per_pair=[])
    assert "decides nothing" in str(ei.value)


@pytest.mark.parametrize("missing", ["pair_id", "jsd", "embedding_similarity"])
def test_incomplete_pair_row_is_refused(missing):
    row = {"pair_id": "p0", "jsd": 0.1, "embedding_similarity": 0.9}
    row.pop(missing)
    with pytest.raises(R4SidecarError) as ei:
        _build(per_pair=[row])
    assert missing in str(ei.value)


def test_non_finite_rho_is_refused_before_custody():
    # Strict JSON before custody (#960 MED-5): a NaN rho must fail here, not publish. A NaN
    # compares false against any threshold, so it would silently read as "rho < 0.7 did not fire".
    with pytest.raises(Exception) as ei:
        _build(aggregate={"spearman_rho": float("nan"), "n_pairs": 3})
    assert "non-finite" in str(ei.value)


# --------------------------------------------------------------------------- #
# ACCEPT 4 — bind parent + sidecar digests WITHOUT mutating the sealed report. #
# --------------------------------------------------------------------------- #
def _sealed():
    return {"schema_version": "b0-evidence-bundle-v1", "record_count": 2,
            "published_digest": B0_DIGEST}


def test_link_binds_both_digests_without_mutating_the_parent():
    sealed = _sealed()
    before = json.dumps(sealed, sort_keys=True)
    rec = _build()
    link = bind_to_parent_report(sealed, rec)
    # The primary report is published O_EXCL/no-replace and its published_digest covers its own
    # contents: writing the sidecar INTO it would either break that digest or force a recompute,
    # and then the sealed artifact is no longer the thing that was sealed.
    assert json.dumps(sealed, sort_keys=True) == before
    assert "sidecar_output_digest" not in sealed
    # The link lives in the REFERRER and carries both digests (the referent<-referrer direction the
    # DQ1b owner ruled for base manifests, WC #1078).
    assert link["b0_published_digest"] == B0_DIGEST
    assert link["sidecar_output_digest"] == rec.output_digest
    assert link["sidecar_manifest_digest"] == rec.manifest_digest
    assert link["evaluator_revision_sha"] == EVAL_SHA
    assert link["link_digest"] == canonical_digest(
        {k: v for k, v in link.items() if k != "link_digest"})


def test_link_to_an_unsealed_report_is_refused():
    with pytest.raises(R4SidecarError) as ei:
        bind_to_parent_report({"record_count": 0}, _build())
    assert "not sealed" in str(ei.value)


def test_link_to_a_different_sealed_report_is_refused():
    sealed = {"published_digest": "9" * 64}
    with pytest.raises(R4SidecarError) as ei:
        bind_to_parent_report(sealed, _build())
    assert "does not match" in str(ei.value)


# --------------------------------------------------------------------------- #
# Scope lock (Monk #1128): out-of-process, no evaluator import.                #
# --------------------------------------------------------------------------- #
def test_sidecar_imports_no_evaluator_and_no_torch():
    # The evaluator is a reviewed OUT-OF-PROCESS B0 evidence sidecar. This module validates and
    # journals the comparison; it must never perform it, so it must never import the model stack.
    # (Monk #1128 scope lock, which also rules that sentence_transformers does NOT belong in
    # COMPONENT_ROUTES/FORBIDDEN_ROUTE_MODULES — those govern the monitor process.)
    import sys

    import p5_r4_sidecar  # noqa: F401
    bad = [m for m in sys.modules
           if m.split(".")[0] in ("torch", "sentence_transformers", "transformers", "numpy")]
    assert bad == []


def test_sidecar_source_does_not_reference_the_evaluator_library():
    import inspect

    import p5_r4_sidecar
    src = inspect.getsource(p5_r4_sidecar)
    # The evaluator is NAMED in prose/manifests (it must be pinned by id), but never imported or
    # called from here.
    assert "import sentence_transformers" not in src
    assert "SentenceTransformer(" not in src
