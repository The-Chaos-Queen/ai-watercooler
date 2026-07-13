"""Model-free tests for the P5 B0 harness core (OpenCLAW #156, slice 3).

No torch, no model. Covers the closed-world deny-by-default manifest gate, the
append-only immutable evidence bundle, and the null-distribution estimate.
"""
import copy

import pytest

from p5_b0_harness import (

    COMPONENT_ROUTES,
    B0EvidenceBundle,
    EvidenceBundleError,
    authorize_b0_launch,
    canonical_digest,
    estimate_null_channel,
    validate_b0_manifest,
)


def _good():
    return {
        "schema_version": "closed_world_b0_v1",
        "run_kind": "b0_baseline",
        "model": {"id": "google/gemma-4-12B", "revision": "1dd69cd0" * 5, "dtype": "bf16"},
        "panel": {"hash": "panelhash"},
        "scorer": {"scorer_id": "b0_null_estimator", "version": "1",
                   "allowlist_digest": "a" * 64},
        "rubric": {"version": "rubric-v1"},
        "processor": {"revision": "proc-rev-1"},
        "decoding": {"hash": "dec-hash-1"},
        "runtime": {"hash": "rt-hash-1"},
        "components": {r: "disabled" for r in COMPONENT_ROUTES},
        "sev_ids": {"geometry_holdout": ["a1", "a2"], "behavioral_probe": ["b1", "b2"]},
        "evidence_sink": {"path": "/evidence/b0", "mode": "append_only", "present": False},
    }


# --------------------------------------------------------------------------- #
# Happy path.                                                                  #
# --------------------------------------------------------------------------- #
def test_clean_manifest_authorizes():
    d = authorize_b0_launch(_good())
    assert d.ok is True
    assert d.refusals == ()
    assert d.manifest_digest and len(d.manifest_digest) == 64


def test_manifest_digest_is_deterministic():
    assert canonical_digest(_good()) == canonical_digest(_good())


# --------------------------------------------------------------------------- #
# Deny-by-default on component routes.                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("route", COMPONENT_ROUTES)
def test_missing_component_route_is_refused(route):
    m = _good()
    del m["components"][route]
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any(route in r for r in d.refusals)


@pytest.mark.parametrize("route", COMPONENT_ROUTES)
def test_enabled_component_route_is_refused(route):
    m = _good()
    m["components"][route] = True            # a live route
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any(route in r and "not disabled" in r for r in d.refusals)


def test_unknown_component_route_is_refused_closed_world():
    m = _good()
    m["components"]["telepathy"] = "disabled"
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("unknown route" in r for r in d.refusals)


def test_all_disabled_sentinels_accepted():
    for sentinel in (False, "disabled", "off", "none"):
        m = _good()
        m["components"] = {r: sentinel for r in COMPONENT_ROUTES}
        assert authorize_b0_launch(m).ok is True


# --------------------------------------------------------------------------- #
# Closed-world top level + run_kind.                                           #
# --------------------------------------------------------------------------- #
def test_unknown_top_level_key_is_refused():
    m = _good()
    m["surprise"] = 1
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("unknown key" in r for r in d.refusals)


def test_missing_required_key_is_refused():
    m = _good()
    del m["rubric"]
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("rubric" in r and "missing" in r for r in d.refusals)


def test_c1_run_kind_is_refused_by_the_b0_harness():
    m = _good()
    m["run_kind"] = "c1_nonzero"
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("run_kind" in r for r in d.refusals)


# --------------------------------------------------------------------------- #
# Unpinned / TBD contract fields.                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("unset", [None, "", "TBD", "null", "pending"])
def test_unpinned_panel_hash_is_refused(unset):
    m = _good()
    m["panel"]["hash"] = unset
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("panel.hash" in r for r in d.refusals)


def test_placeholder_strings_are_refused():
    m = _good()
    m["panel"]["hash"] = "[TBD: panel hash]"
    assert authorize_b0_launch(m).ok is False
    
    m2 = _good()
    m2["decoding"]["hash"] = "tbd: hash goes here"
    assert authorize_b0_launch(m2).ok is False


def test_unpinned_model_revision_is_refused():
    m = _good()
    m["model"]["revision"] = "TBD"
    assert authorize_b0_launch(m).ok is False


# --------------------------------------------------------------------------- #
# SEV disjointness.                                                            #
# --------------------------------------------------------------------------- #
def test_sev_overlap_without_attestation_is_refused():
    m = _good()
    m["sev_ids"] = {"geometry_holdout": ["x", "y"], "behavioral_probe": ["y", "z"]}
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("intersect" in r for r in d.refusals)


def test_sev_overlap_with_signed_attestation_is_allowed():
    m = _good()
    m["sev_ids"] = {
        "geometry_holdout": ["x", "y"], "behavioral_probe": ["y", "z"],
        "overlap_attestation": {"signer": "laura", "review_ref": "wc#999"},
    }
    assert authorize_b0_launch(m).ok is True


def test_disjoint_sev_needs_no_attestation():
    assert authorize_b0_launch(_good()).ok is True


# --------------------------------------------------------------------------- #
# Evidence sink.                                                               #
# --------------------------------------------------------------------------- #
def test_present_evidence_sink_is_refused():
    m = _good()
    m["evidence_sink"]["present"] = True
    assert authorize_b0_launch(m).ok is False


def test_non_append_only_sink_is_refused():
    m = _good()
    m["evidence_sink"]["mode"] = "overwrite"
    d = authorize_b0_launch(m)
    assert any("append_only" in r for r in d.refusals)


# --------------------------------------------------------------------------- #
# Append-only immutable evidence bundle.                                       #
# --------------------------------------------------------------------------- #
def test_bundle_records_and_seals_with_digest():
    b = B0EvidenceBundle(manifest_digest="deadbeef")
    b.record("p1", "gen one", scorer_output={"harm": 0})
    b.record("p2", "gen two", scorer_output={"harm": 0})
    assert len(b) == 2
    report = b.seal()
    assert report["record_count"] == 2
    assert report["manifest_digest"] == "deadbeef"
    assert len(report["report_digest"]) == 64
    assert b.sealed is True


def test_bundle_refuses_overwrite():
    b = B0EvidenceBundle(manifest_digest="d")
    b.record("p1", "gen")
    with pytest.raises(EvidenceBundleError):
        b.record("p1", "different gen")       # same id = refused, no silent overwrite


def test_bundle_refuses_record_after_seal():
    b = B0EvidenceBundle(manifest_digest="d")
    b.record("p1", "gen")
    b.seal()
    with pytest.raises(EvidenceBundleError):
        b.record("p2", "late gen")


def test_bundle_refuses_double_seal():
    b = B0EvidenceBundle(manifest_digest="d")
    b.record("p1", "gen")
    b.seal()
    with pytest.raises(EvidenceBundleError):
        b.seal()


def test_bundle_report_digest_changes_with_content():
    b1 = B0EvidenceBundle(manifest_digest="d")
    b1.record("p1", "gen A")
    b2 = B0EvidenceBundle(manifest_digest="d")
    b2.record("p1", "gen B")
    assert b1.seal()["report_digest"] != b2.seal()["report_digest"]


# --------------------------------------------------------------------------- #
# Null-distribution estimate.                                                  #
# --------------------------------------------------------------------------- #
def test_null_estimate_basic():
    values = [float(i) for i in range(1, 33)]
    flags = [False] * 30 + [True, True]       # 2/32 baseline false alarms
    est = estimate_null_channel(values, flags)
    assert est.n == 32
    assert est.median == pytest.approx(16.5)
    assert est.p95 == pytest.approx(31.0)
    assert est.flag_rate == pytest.approx(2 / 32)


def test_null_estimate_rejects_length_mismatch():
    with pytest.raises(EvidenceBundleError):
        estimate_null_channel([1.0, 2.0], [False])


def test_null_estimate_rejects_empty():
    with pytest.raises(EvidenceBundleError):
        estimate_null_channel([], [])


def test_good_manifest_untouched_by_validation():
    m = _good()
    snapshot = copy.deepcopy(m)
    validate_b0_manifest(m)
    assert m == snapshot                      # validation must not mutate the manifest


# --------------------------------------------------------------------------- #
# Adversarial / Regression Tests                                               #
# --------------------------------------------------------------------------- #
def test_unpinned_field_type_evasion_is_refused():
    m = _good()
    m["model"]["revision"] = []
    assert authorize_b0_launch(m).ok is False
    m["panel"]["hash"] = {}
    assert authorize_b0_launch(m).ok is False


def test_missing_sev_lists_are_refused():
    m = _good()
    m["sev_ids"] = {}
    assert authorize_b0_launch(m).ok is False


def test_empty_sev_lists_are_refused():
    m = _good()
    m["sev_ids"] = {"geometry_holdout": [], "behavioral_probe": []}
    assert authorize_b0_launch(m).ok is False


def test_bundle_records_are_deepcopied():
    b = B0EvidenceBundle(manifest_digest="d")
    out = {"harm": 0}
    b.record("p1", "gen", scorer_output=out)
    out["harm"] = 1  # mutate caller's reference after recording
    report = b.seal()
    assert report["records"][0]["scorer_output"]["harm"] == 0
