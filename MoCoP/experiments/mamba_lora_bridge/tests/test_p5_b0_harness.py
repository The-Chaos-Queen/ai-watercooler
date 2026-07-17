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
    check_run_kind_applicable,
    estimate_null_channel,
    validate_b0_manifest,
)


class _EqStr(str):
    """A str subclass that compares equal to anything — the #1011 equality-override attacker."""

    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash("_eqstr_")


# The exact three-tier neutralization set (#155 contract rev5 e1b9f4a §3.1). Every tier-1 and
# tier-2 field must be present BY VALUE: an absent kwarg is resolved from the checkpoint's own
# generation_config, not a neutral default (WC #1103).
_DEC = {
    "do_sample": False, "num_beams": 1, "max_new_tokens": 160, "min_new_tokens": 0,
    "repetition_penalty": 1.0, "no_repeat_ngram_size": 0, "eos_token_id": [1, 106],
    "pad_token_id": 0,
    "temperature": 1.0, "top_p": 1.0, "top_k": 0, "length_penalty": 1.0, "early_stopping": False,
}


def _good():
    return {
        "schema_version": "closed_world_b0_v1",
        # Stage-NEUTRAL base (DQ1b §7): no run_kind, no self-referential base_manifest_digest.
        "schema_variant": "closed_world_b0",
        "base_manifest_id": "b0-base-2026-07-16-a",
        "model": {"id": "google/gemma-4-12B", "revision": "1dd69cd0" * 5, "dtype": "bf16"},
        "panel": {"hash": "panelhash"},
        "scorer": {"scorer_id": "b0_null_estimator", "version": "1",
                   "allowlist_digest": "a" * 64},
        "rubric": {"version": "rubric-v1"},
        "processor": {"revision": "proc-rev-1"},
        "decoding": {**_DEC, "hash": "dec-hash-1"},
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
# Closed-world top level + stage-neutral base (spec 6b2347e §2, §4).           #
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


# --- The base is stage-neutral: run_kind is NOT a base key (spec §2, acceptance 3) --------- #
@pytest.mark.parametrize("value", ["b0_baseline", "c1_alpha_zero", "c1_nonzero"])
def test_base_manifest_carrying_run_kind_is_refused(value):
    # No silent migration: a base carrying ANY run_kind is refused — including the previously
    # required "b0_baseline". run_kind moved to the attempt boundary so Stage A and Stage B can
    # share a byte-identical base (DQ1b §7); a stage-specific base cannot be smuggled back in.
    m = _good()
    m["run_kind"] = value
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("run_kind must NOT appear" in r for r in d.refusals)   # legible, not just "unknown"
    assert any("unknown key" in r for r in d.refusals)                # closed-world still fires


def test_base_manifest_carrying_its_own_digest_is_refused():
    # DQ1b owner ruling (WC #1078): base_manifest_digest is reference-only. A self-digesting base
    # would need an excluded-self-field rule — exactly the re-implementation divergence the ruling
    # exists to prevent.
    m = _good()
    m["base_manifest_digest"] = "a" * 64
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("reference-only" in r for r in d.refusals)


# --------------------------------------------------------------------------- #
# Decoding neutralization set (#155 rev5 e1b9f4a §3.1) — the WC #1103 repair.  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key", [
    "do_sample", "num_beams", "max_new_tokens", "min_new_tokens",
    "repetition_penalty", "no_repeat_ngram_size", "eos_token_id", "pad_token_id",
])
def test_absent_required_explicit_decoding_field_is_refused(key):
    # THE core regression. Absence is not neutrality: HF resolves an absent kwarg from the
    # CHECKPOINT'S generation_config (kwargs > generation_config > model.generation_config >
    # GenerationConfig()), which is vendor data that moves with `revision`. Every one of these must
    # be declared by value or the manifest does not actually pin decoding.
    m = _good()
    del m["decoding"][key]
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any(key in r and "absent" in r for r in d.refusals)


@pytest.mark.parametrize("key", ["temperature", "top_p", "top_k", "length_penalty",
                                 "early_stopping"])
def test_absent_pinned_inert_decoding_field_is_refused(key):
    # Inert under do_sample=False, but pinned so a future flip cannot silently inherit the
    # checkpoint's shipped sampler values (a real cached checkpoint ships temperature=0.7/top_p=0.8).
    m = _good()
    del m["decoding"][key]
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any(key in r for r in d.refusals)


@pytest.mark.parametrize("key", ["bad_words_ids", "force_words_ids", "suppress_tokens",
                                 "begin_suppress_tokens", "constraints", "penalty_alpha",
                                 "streamer", "assistant_model"])
def test_forbidden_present_decoding_field_is_refused(key):
    m = _good()
    m["decoding"][key] = "anything"
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any(key in r and "forbidden-present" in r for r in d.refusals)


def test_unknown_decoding_field_is_still_refused_as_not_consumed():
    # The #1095 property is KEPT, not loosened: a manifest may not declare a decoding field the
    # runner does not actually pass. This repair adds fields to what IS passed; it does not relax
    # the check that guards against declaring-without-passing.
    m = _good()
    m["decoding"]["typical_p"] = 0.9
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("not consumed by generate" in r for r in d.refusals)


def test_repetition_penalty_must_be_neutral_because_it_survives_greedy():
    # repetition_penalty is a LOGITS PROCESSOR, not a sampler: do_sample=False does not disable it.
    # A shipped 1.1 would reshape every B0 continuation invisibly.
    m = _good()
    m["decoding"]["repetition_penalty"] = 1.1
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("SURVIVES do_sample=False" in r for r in d.refusals)


def test_num_beams_must_be_one_because_beam_search_is_not_greedy():
    # A shipped num_beams>1 yields deterministic BEAM SEARCH under do_sample=False — still not
    # greedy, and invisible in a manifest that only pinned do_sample/max_new_tokens.
    m = _good()
    m["decoding"]["num_beams"] = 4
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("BEAM SEARCH" in r for r in d.refusals)


def test_sampling_manifest_is_refused():
    m = _good()
    m["decoding"]["do_sample"] = True
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("deterministic" in r for r in d.refusals)


def test_eos_token_id_accepts_the_checkpoint_list_form():
    # Real checkpoints ship eos_token_id as a LIST (one cached here ships [151645, 151643]), so
    # "pinned by value" must admit both forms.
    m = _good()
    m["decoding"]["eos_token_id"] = 1
    assert authorize_b0_launch(m).ok is True
    m["decoding"]["eos_token_id"] = [1, 106]
    assert authorize_b0_launch(m).ok is True


def test_use_cache_is_not_a_decoding_field():
    # use_cache is descriptor-homed (#966 B3, contract §3.4). Declaring it under decoding would be
    # two homes for one authority — the §4b alias mistake.
    m = _good()
    m["decoding"]["use_cache"] = False
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("not consumed by generate" in r for r in d.refusals)


# --- schema_variant: closed-world union, exact-str (acceptance 1) --------------------------- #
def test_missing_schema_variant_is_refused():
    m = _good()
    del m["schema_variant"]
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("schema_variant" in r and "missing" in r for r in d.refusals)


@pytest.mark.parametrize("value", ["", "tbd", "closed_world_b1", "b0", "CLOSED_WORLD_B0"])
def test_unknown_or_placeholder_schema_variant_is_refused(value):
    m = _good()
    m["schema_variant"] = value
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("schema_variant" in r for r in d.refusals)


def test_c1_variant_base_is_refused_by_the_b0_harness():
    # A well-formed variant this harness must still refuse to authorize: the C1-side required keys
    # are the C1 lane's, and are out of scope here (spec §5).
    m = _good()
    m["schema_variant"] = "closed_world_c1"
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("never a C1 stage" in r for r in d.refusals)


def test_equality_overriding_schema_variant_subclass_is_refused():
    # #1011 B3: `variant in SCHEMA_VARIANTS` consults __eq__, so a subclass that compares equal to
    # anything would satisfy the closed-world union test while carrying an arbitrary value.
    m = _good()
    m["schema_variant"] = _EqStr("closed_world_c1")
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("exact str" in r for r in d.refusals)


# --- base_manifest_id: required, non-placeholder (acceptance 2) ----------------------------- #
def test_missing_base_manifest_id_is_refused():
    m = _good()
    del m["base_manifest_id"]
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("base_manifest_id" in r and "missing" in r for r in d.refusals)


@pytest.mark.parametrize("value", ["", "  ", "TBD", "pending", "[tbd: assign at freeze]", None, 7])
def test_placeholder_base_manifest_id_is_refused(value):
    m = _good()
    m["base_manifest_id"] = value
    d = authorize_b0_launch(m)
    assert d.ok is False
    assert any("base_manifest_id" in r for r in d.refusals)


# --- Stage A/B sharing property, B0-executable form (spec §4a, acceptance 5) ---------------- #
def test_base_digest_is_computed_over_the_base_alone_and_contains_no_run_kind():
    # §4a(i). The property is STRUCTURAL: run_kind is not a base key, so the base digest cannot
    # depend on it. This pins the structure against reintroduction — if a future edit puts run_kind
    # back into the base, the digest starts varying by stage and Stage A/B can no longer share it.
    m = _good()
    assert "run_kind" not in m
    d = authorize_b0_launch(m)
    assert d.ok is True
    assert d.manifest_digest == canonical_digest(m)   # over the base alone, no attempt binding


def test_variant_drives_applicability_not_a_base_field():
    from p5_b0_harness import check_run_kind_applicable
    m = _good()
    assert check_run_kind_applicable(m, "b0_baseline") == []
    for kind in ("c1_alpha_zero", "c1_nonzero", "anything_else"):
        assert any("inapplicable" in r for r in check_run_kind_applicable(m, kind))


def test_equality_overriding_attempt_run_kind_is_refused():
    m = _good()
    r = check_run_kind_applicable(m, _EqStr("c1_nonzero"))
    assert any("exact str" in x for x in r)


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
