"""P5 B0 harness core — closed-world no-component manifest + append-only evidence.

OpenCLAW #156, slice 3 (the B0 path). Torch-free, model-free-testable. Implements
the reviewed DQ1b §6.1 / #155 baseline contract: BEFORE any Gemma-base forward, a B0
run must present a hashable no-component manifest that is validated DENY-BY-DEFAULT,
and its only permitted output is an append-only immutable evidence bundle.

B0 is characterization, NOT birth: no value injection, no bridge, no Mamba, no
Qdrant, no memory, no replay, no sleep, no mutable/project-state write. This core is
the gate that makes that guarantee structural rather than a promise — it refuses to
authorize a launch unless every component route is EXPLICITLY disabled and every
frozen contract key is pinned.

Design (house style): the numeric/logic core is torch-free and model-free-testable;
the real HF generation backend (ML-WS, read-only) is a separate slice that may only
run AFTER authorize_b0_launch returns ok.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, NamedTuple, Sequence

# Component routes that MUST be explicitly disabled for a B0 run. Deny-by-default:
# a route that is missing, enabled, or "reachable" fails the launch. (DQ1b §6.1.)
#
# SINGLE SOURCE OF TRUTH: every component that could touch a B0 forward must be listed
# here. This model-free gate can only verify the DECLARED manifest; the spec's stronger
# "reachable/observed" clause (a component module actually importable/wired in the live
# runtime) is enforced by the HF-backend slice, which must introspect the process and
# enumerate against THIS tuple before generating. When a new component lands (e.g. a
# music/audio Mamba, a c/L controller kernel), add it here or B0's no-component
# guarantee silently weakens.
COMPONENT_ROUTES = (
    "value_injection",
    "bridge",
    "mamba",
    "qdrant",
    "memory",
    "replay",
    "sleep",
    "mutable_write",
    "appraisal",
    "controller",
    "world_model",
)

# The disabled sentinel a manifest must use for each route (explicit, not implicit).
DISABLED_VALUES = (False, "disabled", "off", "none")

# Top-level manifest keys required for a closed_world_b0 contract.
#
# DQ1b §7 / reconciliation spec rev 2 (6b2347e): the base manifest is stage-NEUTRAL. ``run_kind``
# is NOT a base key — it is supplied per-attempt to ``run_b0`` — so that Stage A (c1_alpha_zero)
# and Stage B (c1_nonzero) can share a BYTE-IDENTICAL base, which the Stage-B "sidecar references
# the UNCHANGED base manifest" rule depends on. A base still carrying ``run_kind`` is refused by
# the closed-world unknown-key check below (no silent migration). ``base_manifest_digest`` is
# likewise NOT a base key: per the DQ1b owner ruling (WC #1078) it is reference-only — the digest
# is computed over the complete base and carried by the REFERRERS (attempts, Stage-B sidecars),
# never by the referent, so no excluded-self-field rule exists for a verifier to diverge on.
REQUIRED_B0_KEYS = frozenset({
    "schema_version",
    "schema_variant",
    "base_manifest_id",
    "model",
    "panel",
    "scorer",
    "rubric",
    "processor",
    "decoding",
    "runtime",
    "components",
    "sev_ids",
    "evidence_sink",
})

# Sub-blocks that must each carry a non-empty pinned hash/version/id.
_MODEL_KEYS = ("id", "revision", "dtype")
_PINNED_BLOCKS = {
    "panel": ("hash",),
    "scorer": ("scorer_id", "version", "allowlist_digest"),
    "rubric": ("version",),
    "processor": ("revision",),
    "decoding": ("hash",),
    "runtime": ("hash",),
}

B0_RUN_KIND = "b0_baseline"

# --------------------------------------------------------------------------- #
# Decoding neutralization set (#155 contract rev5 `e1b9f4a` §3.1), three tiers. #
# --------------------------------------------------------------------------- #
# WHY EXPLICIT RATHER THAN ABSENT — this inverts the intuition, so it is written down once here.
# HF `generate()` resolves an ABSENT kwarg from the CHECKPOINT'S OWN generation_config, not from a
# neutral library default. transformers/generation/utils.py states the precedence verbatim:
#
#     kwargs > non-global default values in `generation_config` > `model.generation_config`
#              > GenerationConfig()
#
# `GenerationConfig()` — the actually-neutral default — is the LAST resort, reached only after the
# checkpoint's file. So leaving a field out hands it to vendor data that moves with `revision`:
# absence is the drift channel, not the guard. Evidence: a real cached checkpoint ships
# do_sample/temperature/top_p/top_k/repetition_penalty and an eos_token_id LIST. Two of those bite
# under greedy — `repetition_penalty` is a logits processor and survives `do_sample=False`, and a
# shipped `num_beams>1` yields deterministic BEAM SEARCH, not greedy. Neither would appear in the
# manifest or the decoding hash. (Gidim WC #1103 -> Isegrim contract rev4/rev5 WC #1104.)
#
# Tier 1: active under greedy; the manifest declares each BY VALUE and the runner PASSES each.
DECODING_REQUIRED_EXPLICIT = (
    "do_sample", "num_beams", "max_new_tokens", "min_new_tokens",
    "repetition_penalty", "no_repeat_ngram_size", "eos_token_id", "pad_token_id",
)
# Tier 2: inert while do_sample=False, but pinned so a future flip cannot co-opt shipped values.
DECODING_PINNED_INERT = (
    "temperature", "top_p", "top_k", "length_penalty", "early_stopping",
)
# Tier 3: neither manifest nor call may carry these at all.
DECODING_FORBIDDEN_PRESENT = (
    "bad_words_ids", "force_words_ids", "suppress_tokens", "begin_suppress_tokens",
    "constraints", "penalty_alpha", "streamer", "assistant_model",
)
# `use_cache` is deliberately NOT here: it is descriptor-homed (a DESCRIPTOR_KEYS field, reported by
# the same value the backend passes, #966 B3). Contract §3.4 references model.use_cache. One
# authority, one home — the §4b alias lesson.
_DECODING_META_KEYS = ("hash",)

# Fields whose VALUE the contract fixes, because the value is what makes the run greedy and
# drift-free. Presence alone is not the guarantee: a tier-2 field pinned to a NON-neutral number
# (say temperature=0.7) is exactly the "shipped value co-opted by a future flip" that tier 2 exists
# to prevent — it just waits for someone to set do_sample=True. Enforce the values.
#
# Deliberately NOT fixed here: `max_new_tokens`, `eos_token_id`, `pad_token_id`. Those are the RUN's
# parameters, not neutrality invariants — the contract sets max_new_tokens=160 for this run (DQ1a
# §3.3) and pins the token ids from the checkpoint. Hard-coding a run's budget into the harness
# would make the tool the author of a value only the manifest may declare.
_DECODING_NEUTRAL_VALUES = {
    "do_sample": False,
    "num_beams": 1,
    "min_new_tokens": 0,
    "repetition_penalty": 1.0,
    "no_repeat_ngram_size": 0,
    "temperature": 1.0,
    "top_p": 1.0,
    "top_k": 0,
    "length_penalty": 1.0,
    "early_stopping": False,
}

# The closed-world union of schema variants (DQ1b §7). Exactly one may appear in a base manifest.
# The variant — not a stage-specific base field — drives which required-key set applies and which
# per-attempt run kinds are applicable.
SCHEMA_VARIANTS = ("closed_world_b0", "closed_world_c1")

# The ONLY variant this harness implements. A `closed_world_c1` base is a well-formed variant that
# this harness must still refuse to authorize: the C1-side required keys (condition key, direction
# artifact digest, Stage-A/B GO records, numeric gate values, recovery spans) are the C1 lane's and
# are deliberately out of scope here. Same spirit as the pre-reconciliation `run_kind` refusal —
# this harness authorizes the B0 baseline only, never an injection stage.
B0_SCHEMA_VARIANT = "closed_world_b0"

# Base keys that are structurally EXCLUDED and must never reappear. Each has a targeted refusal so a
# stage-specific or self-digesting base fails legibly rather than only as a generic unknown key.
_EXCLUDED_BASE_KEYS = {
    "run_kind": (
        "run_kind must NOT appear in the stage-neutral base manifest; it is a per-attempt "
        "binding on run_b0() so Stage A and Stage B can share a byte-identical base (DQ1b §7)"
    ),
    "base_manifest_digest": (
        "base_manifest_digest must NOT appear in the base manifest; it is reference-only — the "
        "digest is computed over the complete base and carried by attempts/Stage-B sidecars, "
        "never by the base itself (DQ1b owner ruling, WC #1078)"
    ),
}

# Values that count as "not really set" (a pre-launch failure). Case-insensitive.
_UNSET_STRINGS = {"", "tbd", "null", "none", "pending", "todo", "changeme"}


# --------------------------------------------------------------------------- #
# Manifest-authorization POLICY, frozen at import at its owning boundary        #
# (Codex #1009 B1 -> #1011 B1: the runner's authority freeze must reach here).  #
# --------------------------------------------------------------------------- #
# The validators below render a governed decision; none of the policy they read may be a
# call-time dereference of a reassignable/mutable module global (adding `True` to DISABLED_VALUES,
# or rebinding B0_RUN_KIND, weakened authorization). The module constants above remain PUBLISHED
# documentation; the validators consume the frozen snapshot returned by ``_policy()``.
class _HarnessPolicy(NamedTuple):
    component_routes: tuple
    disabled_values: tuple
    required_keys: frozenset
    model_keys: tuple
    pinned_blocks: Mapping[str, tuple]
    b0_run_kind: str
    schema_variants: tuple
    b0_schema_variant: str
    excluded_base_keys: Mapping[str, str]
    decoding_required_explicit: tuple
    decoding_pinned_inert: tuple
    decoding_forbidden_present: tuple
    decoding_meta_keys: tuple
    decoding_neutral_values: Mapping[str, Any]
    unset_strings: frozenset


def _bind_harness_policy():
    snap = _HarnessPolicy(
        component_routes=tuple(COMPONENT_ROUTES),
        disabled_values=tuple(DISABLED_VALUES),
        required_keys=frozenset(REQUIRED_B0_KEYS),
        model_keys=tuple(_MODEL_KEYS),
        pinned_blocks=MappingProxyType({k: tuple(v) for k, v in _PINNED_BLOCKS.items()}),
        b0_run_kind=str(B0_RUN_KIND),
        # The variant authorities are policy, not decoration: widening SCHEMA_VARIANTS or rebinding
        # B0_SCHEMA_VARIANT at call time would let a caller authorize a non-B0 base (#1011 B1).
        schema_variants=tuple(SCHEMA_VARIANTS),
        b0_schema_variant=str(B0_SCHEMA_VARIANT),
        excluded_base_keys=MappingProxyType(dict(_EXCLUDED_BASE_KEYS)),
        # The neutralization tiers are authorities too: widening FORBIDDEN_PRESENT or shrinking
        # REQUIRED_EXPLICIT at call time would re-open the generation_config drift channel that
        # #1103 closed. Freeze them with the rest (#1011 B1).
        decoding_required_explicit=tuple(DECODING_REQUIRED_EXPLICIT),
        decoding_pinned_inert=tuple(DECODING_PINNED_INERT),
        decoding_forbidden_present=tuple(DECODING_FORBIDDEN_PRESENT),
        decoding_meta_keys=tuple(_DECODING_META_KEYS),
        decoding_neutral_values=MappingProxyType(dict(_DECODING_NEUTRAL_VALUES)),
        unset_strings=frozenset(_UNSET_STRINGS),
    )

    def policy() -> _HarnessPolicy:
        return snap

    return policy


_policy = _bind_harness_policy()


class B0ManifestError(ValueError):
    """A structural launch-refusal reason (bug or unsafe config), not a run outcome."""


def _is_unset(value: Any) -> bool:
    _UNSET_STRINGS = _policy().unset_strings              # frozen (Codex #1011 B1)
    if not isinstance(value, str):
        return True
    val_lower = value.strip().lower()
    if val_lower in _UNSET_STRINGS:
        return True
    if "[tbd:" in val_lower or val_lower.startswith("tbd:"):
        return True
    return False


# --------------------------------------------------------------------------- #
# Manifest validation (deny-by-default, closed-world).                         #
# --------------------------------------------------------------------------- #
def _check_no_component(components: Any, refusals: list[str]) -> None:
    _P = _policy()                                       # frozen policy (Codex #1011 B1)
    COMPONENT_ROUTES, DISABLED_VALUES = _P.component_routes, _P.disabled_values
    if not isinstance(components, Mapping):
        refusals.append("components block missing or not a mapping")
        return
    # Closed-world: no unknown routes may appear.
    unknown = set(components) - set(COMPONENT_ROUTES)
    if unknown:
        refusals.append(f"components has unknown route(s): {sorted(unknown)}")
    # Deny-by-default: every known route must be EXPLICITLY present and disabled.
    for route in COMPONENT_ROUTES:
        if route not in components:
            refusals.append(f"component route {route!r} not explicitly declared disabled")
            continue
        val = components[route]
        norm = val.strip().lower() if isinstance(val, str) else val
        if norm not in DISABLED_VALUES:
            refusals.append(f"component route {route!r} is not disabled (got {val!r})")


def _check_pinned(manifest: Mapping[str, Any], refusals: list[str]) -> None:
    _P = _policy()                                       # frozen policy (Codex #1011 B1)
    _MODEL_KEYS, _PINNED_BLOCKS = _P.model_keys, _P.pinned_blocks
    model = manifest.get("model")
    if not isinstance(model, Mapping):
        refusals.append("model block missing or not a mapping")
    else:
        for key in _MODEL_KEYS:
            if _is_unset(model.get(key)):
                refusals.append(f"model.{key} is unset/unpinned")
    for block, keys in _PINNED_BLOCKS.items():
        sub = manifest.get(block)
        if not isinstance(sub, Mapping):
            refusals.append(f"{block} block missing or not a mapping")
            continue
        for key in keys:
            if _is_unset(sub.get(key)):
                refusals.append(f"{block}.{key} is unset/unpinned")


def _check_sev_disjointness(sev_ids: Any, refusals: list[str]) -> None:
    if not isinstance(sev_ids, Mapping):
        refusals.append("sev_ids block missing or not a mapping")
        return
    
    geo = sev_ids.get("geometry_holdout")
    beh = sev_ids.get("behavioral_probe")
    
    if not isinstance(geo, list) or not geo:
        refusals.append("geometry_holdout must be a non-empty list of SEV IDs")
    if not isinstance(beh, list) or not beh:
        refusals.append("behavioral_probe must be a non-empty list of SEV IDs")

    geometry = set(geo or [])
    behavioral = set(beh or [])
    overlap = geometry & behavioral
    if overlap:
        attestation = sev_ids.get("overlap_attestation")
        # A signed, reviewed attestation is the only way overlap is permitted.
        signed = (
            isinstance(attestation, Mapping)
            and not _is_unset(attestation.get("signer"))
            and not _is_unset(attestation.get("review_ref"))
        )
        if not signed:
            refusals.append(
                f"geometry-holdout and behavioral-probe SEV ids intersect "
                f"({sorted(overlap)}) without a signed reviewed overlap attestation"
            )


def _check_evidence_sink(sink: Any, refusals: list[str]) -> None:
    if not isinstance(sink, Mapping):
        refusals.append("evidence_sink block missing or not a mapping")
        return
    if _is_unset(sink.get("path")):
        refusals.append("evidence_sink.path is unset (protected evidence sink absent)")
    if sink.get("mode") != "append_only":
        refusals.append("evidence_sink.mode must be 'append_only'")
    if sink.get("present") is not False:
        refusals.append("evidence_sink.present must be False (sink must not exist before launch)")


def _check_excluded_base_keys(manifest: Mapping[str, Any], refusals: list[str]) -> None:
    """Refuse a base manifest carrying a structurally excluded key, with a legible reason.

    These keys are already absent from ``REQUIRED_B0_KEYS``, so the closed-world unknown-key check
    refuses them too; this adds the WHY. No silent migration: a stage-specific base (``run_kind``)
    or a self-digesting base (``base_manifest_digest``) fails closed and says which contract it
    broke, rather than being quietly accepted or reported as an anonymous stray key.
    """
    _P = _policy()                                       # frozen policy (Codex #1011 B1)
    for key, reason in _P.excluded_base_keys.items():
        if key in manifest:
            refusals.append(reason)


def _check_variant_and_identity(manifest: Mapping[str, Any], refusals: list[str]) -> None:
    """Refuse unless the base declares an applicable variant and a real base identity."""
    _P = _policy()                                       # frozen policy (Codex #1011 B1)
    SCHEMA_VARIANTS, B0_SCHEMA_VARIANT = _P.schema_variants, _P.b0_schema_variant

    variant = manifest.get("schema_variant")
    # Exact-type BEFORE membership (#1011 B3): `x in SCHEMA_VARIANTS` consults __eq__, so an
    # equality-overriding str subclass would satisfy the union test while carrying any value.
    if type(variant) is not str:
        refusals.append(
            f"schema_variant must be an exact str (got {type(variant).__name__}); "
            "an equality-overriding subclass is refused"
        )
    elif _is_unset(variant):
        refusals.append(f"schema_variant is a placeholder/unset value ({variant!r})")
    elif variant not in SCHEMA_VARIANTS:
        refusals.append(
            f"schema_variant must be one of {sorted(SCHEMA_VARIANTS)} (got {variant!r}); "
            "the variant union is closed-world"
        )
    elif variant != B0_SCHEMA_VARIANT:
        refusals.append(
            f"schema_variant is {variant!r}; this harness authorizes {B0_SCHEMA_VARIANT!r} only, "
            "never a C1 stage"
        )

    base_id = manifest.get("base_manifest_id")
    if type(base_id) is not str:
        refusals.append(
            f"base_manifest_id must be an exact str (got {type(base_id).__name__}); "
            "an equality-overriding subclass is refused"
        )
    elif _is_unset(base_id):
        refusals.append(
            f"base_manifest_id is a placeholder/unset value ({base_id!r}); a base with no real "
            "identity cannot be referenced by an attempt or a Stage-B sidecar"
        )


def validate_b0_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Return a list of launch-refusal reasons ([] means clean). Never runs anything."""

    _P = _policy()                                       # frozen policy (Codex #1011 B1)
    REQUIRED_B0_KEYS = _P.required_keys
    refusals: list[str] = []
    if not isinstance(manifest, Mapping):
        return ["manifest is not a mapping"]

    # Closed-world at the top level: no unknown keys, no missing keys.
    unknown = set(manifest) - set(REQUIRED_B0_KEYS)
    if unknown:
        refusals.append(f"manifest has unknown key(s): {sorted(unknown)}")
    for key in REQUIRED_B0_KEYS:
        if key not in manifest:
            refusals.append(f"required key {key!r} is missing")

    _check_excluded_base_keys(manifest, refusals)
    _check_variant_and_identity(manifest, refusals)
    refusals.extend(check_decoding_contract(manifest))
    _check_no_component(manifest.get("components"), refusals)
    _check_pinned(manifest, refusals)
    _check_sev_disjointness(manifest.get("sev_ids"), refusals)
    _check_evidence_sink(manifest.get("evidence_sink"), refusals)
    return refusals


def check_decoding_contract(manifest: Mapping[str, Any]) -> list[str]:
    """Refuse a decoding block that does not pin the exact neutralization set (#155 §3.1).

    Closed-world over three tiers: every required-explicit and pinned-inert field must be present
    (absence hands it to the checkpoint's generation_config — see the tier definitions above), no
    forbidden-present field may appear, and no unknown field may appear.

    The unknown-key refusal preserves the #1095 property rather than loosening it: a manifest may
    not declare a decoding field the runner does not actually pass. That property is why this repair
    ADDS fields to what the runner passes instead of relaxing the check.

    Returns refusal reasons ([] means clean). Never runs anything.
    """
    _P = _policy()                                       # frozen policy (Codex #1011 B1)
    refusals: list[str] = []
    dec = manifest.get("decoding")
    if not isinstance(dec, Mapping):
        return ["decoding block missing or not a mapping"]

    for key in _P.decoding_required_explicit:
        if key not in dec:
            refusals.append(
                f"decoding.{key} is absent; it MUST be pinned by value — an absent kwarg is "
                "resolved from the checkpoint's own generation_config, not a neutral default "
                "(WC #1103)"
            )
    for key in _P.decoding_pinned_inert:
        if key not in dec:
            refusals.append(
                f"decoding.{key} is absent; it is inert under do_sample=False but MUST be pinned "
                "so a future flip cannot co-opt the checkpoint's shipped value (#155 §3.1 tier 2)"
            )
    for key in _P.decoding_forbidden_present:
        if key in dec:
            refusals.append(
                f"decoding.{key} is forbidden-present: neither the manifest nor the call may "
                "carry it (#155 §3.1 tier 3)"
            )

    allowed = set(_P.decoding_required_explicit) | set(_P.decoding_pinned_inert) | set(
        _P.decoding_meta_keys)
    unknown = set(dec) - allowed - set(_P.decoding_forbidden_present)
    if unknown:
        refusals.append(
            f"unsupported decoding fields in manifest (not consumed by generate): "
            f"{sorted(unknown)}"
        )

    # Determinism is structural here, not advisory: this harness authorizes a BASELINE.
    _WHY = {
        "do_sample": "B0 baseline must be deterministic",
        "num_beams": ("a num_beams>1 yields deterministic BEAM SEARCH under do_sample=False, "
                      "which is still not greedy"),
        "repetition_penalty": ("repetition_penalty is a logits processor and SURVIVES "
                               "do_sample=False — it reshapes every greedy continuation"),
        "temperature": "pinned-inert: must not leave a non-neutral value for a future do_sample flip",
        "top_p": "pinned-inert: must not leave a non-neutral value for a future do_sample flip",
        "top_k": "pinned-inert: must not leave a non-neutral value for a future do_sample flip",
    }
    for key, want in _P.decoding_neutral_values.items():
        if key not in dec:
            continue                      # absence already refused above; don't double-report
        got = dec[key]
        # Exact type before value: `1 == True` and `1 == 1.0` in Python, so an equality-only check
        # would accept `do_sample=0` or `num_beams=True` as neutral.
        if type(got) is not type(want) or got != want:
            why = _WHY.get(key, "pinned by the #155 neutralization set")
            refusals.append(
                f"decoding.{key} must be exactly {want!r} ({type(want).__name__}), got {got!r} "
                f"({type(got).__name__}) — {why}"
            )
    return refusals


def check_run_kind_applicable(manifest: Mapping[str, Any], run_kind: Any) -> list[str]:
    """Refuse a per-attempt ``run_kind`` inapplicable to the base's variant (DQ1b §7).

    This is the applicability check DQ1b §7 asks for ("refuse … if the per-attempt run-kind field is
    inapplicable"), enforced against the base's ``schema_variant`` rather than against a stage-specific
    base-manifest field. The base stays byte-identical across stages; only the attempt differs.

    Returns refusal reasons ([] means applicable). Never runs anything.
    """
    _P = _policy()                                       # frozen policy (Codex #1011 B1)
    refusals: list[str] = []
    # Exact-type first (#1011 B3): every comparison below consults __eq__.
    if type(run_kind) is not str:
        refusals.append(
            f"run_kind must be an exact str (got {type(run_kind).__name__}); "
            "an equality-overriding subclass is refused"
        )
        return refusals
    if _is_unset(run_kind):
        refusals.append(f"run_kind is a placeholder/unset value ({run_kind!r})")
        return refusals

    variant = manifest.get("schema_variant") if isinstance(manifest, Mapping) else None
    # A malformed/absent variant is already a manifest refusal; do not ALSO claim inapplicability
    # against a variant we could not read — that would report a second, misleading reason.
    if type(variant) is not str or variant not in _P.schema_variants:
        return refusals
    if variant == _P.b0_schema_variant and run_kind != _P.b0_run_kind:
        refusals.append(
            f"run_kind {run_kind!r} is inapplicable to schema_variant {variant!r}: this harness "
            f"authorizes {_P.b0_run_kind!r} only, never an injection run kind"
        )
    return refusals


@dataclass(frozen=True)
class B0LaunchDecision:
    ok: bool
    refusals: tuple[str, ...] = ()
    manifest_digest: str | None = None


def assert_strict_json(obj: Any, *, _path: str = "$") -> None:
    """Refuse anything that is not finite, canonical, round-trippable JSON.

    a-Codex/#960 MED-5: dropping ``default=str`` from one ``json.dump`` is not enough
    — non-finite floats (``NaN``/``inf``) and arbitrary objects must be rejected BEFORE
    custody transfer, not silently coerced or caught only after the forwards. Allowed
    leaf types: ``str``, ``bool``, ``int``, finite ``float``, ``None``. Containers:
    ``dict`` with ``str`` keys, ``list``/``tuple``. Raises ``EvidenceBundleError`` on the
    first violation, naming the offending path.
    """
    if isinstance(obj, bool) or obj is None or isinstance(obj, (str, int)):
        return
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise EvidenceBundleError(f"non-finite float at {_path}: {obj!r}")
        return
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise EvidenceBundleError(f"non-string mapping key at {_path}: {key!r}")
            assert_strict_json(value, _path=f"{_path}.{key}")
        return
    if isinstance(obj, list):
        for i, value in enumerate(obj):
            assert_strict_json(value, _path=f"{_path}[{i}]")
        return
    # tuples are rejected: json.dumps would collapse (1, 2) into [1, 2], so a digest over a
    # tuple is not injective. Callers must normalize to a list before custody (#966 MED-6).
    raise EvidenceBundleError(f"non-JSON value at {_path}: {type(obj).__name__}")


def canonical_digest(obj: Any) -> str:
    # No ``default=str`` fallback and ``allow_nan=False``, AND the strict validator runs
    # first so non-string keys / tuples / non-finite floats RAISE rather than silently
    # collapsing ({1:"x"} vs {"1":"x"}, (1,2) vs [1,2]) into a colliding digest (#966 MED-6).
    assert_strict_json(obj)
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False,
                         ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def authorize_b0_launch(manifest: Mapping[str, Any]) -> B0LaunchDecision:
    """Deny-by-default launch authorization. ok=True ONLY if zero refusals.

    A True decision authorizes a READ-ONLY, no-component Gemma-base baseline forward
    and nothing else. It never authorizes injection, birth, or any component route.

    The returned ``manifest_digest`` is computed over the BASE ALONE — before, and independent of,
    any per-attempt binding — and cannot contain ``run_kind``, which is not a base key. That is
    spec §4a(i): DQ1b §7's Stage-A/B sharing property bought structurally rather than asserted.
    """
    refusals = validate_b0_manifest(manifest)
    # A manifest that fails strict-JSON (non-string key, tuple, non-finite) is invalid
    # anyway; digest=None rather than letting canonical_digest raise out of authorization.
    try:
        digest = canonical_digest(manifest) if isinstance(manifest, Mapping) else None
    except EvidenceBundleError:
        digest = None
        if not refusals:
            refusals.append("manifest is not strict JSON (non-string key / tuple / non-finite)")
    return B0LaunchDecision(ok=not refusals, refusals=tuple(refusals), manifest_digest=digest)


# --------------------------------------------------------------------------- #
# Append-only immutable evidence bundle.                                       #
# --------------------------------------------------------------------------- #
class EvidenceBundleError(RuntimeError):
    pass


@dataclass
class B0EvidenceBundle:
    """The only permitted B0 output: append-only, no-overwrite, sealed once.

    Records raw generations + per-record scorer inputs/outputs keyed by an
    immutable prompt/probe id. Re-recording an id is refused (no silent overwrite).
    ``seal()`` freezes the bundle and returns a reproducible report digest bound to
    the authorized manifest digest.
    """

    manifest_digest: str
    _records: list[dict[str, Any]] = field(default_factory=list)
    _ids: set[str] = field(default_factory=set)
    _sealed: bool = False

    def record(self, probe_id: str, raw_generation: str, *,
               scorer_input: Any = None, scorer_output: Any = None,
               provenance: Mapping[str, Any] | None = None) -> None:
        if self._sealed:
            raise EvidenceBundleError("bundle is sealed; no further records permitted")
        if not isinstance(probe_id, str) or not probe_id:
            raise EvidenceBundleError("probe_id must be a non-empty string")
        if probe_id in self._ids:
            raise EvidenceBundleError(f"refusing to overwrite existing record {probe_id!r}")
        if not isinstance(raw_generation, str):
            raise EvidenceBundleError("raw_generation must be a string")
        record = {
            "probe_id": probe_id,
            "raw_generation": raw_generation,
            "scorer_input": copy.deepcopy(scorer_input),
            "scorer_output": copy.deepcopy(scorer_output),
            "provenance": copy.deepcopy(dict(provenance)) if provenance else {},
            "ordinal": len(self._records),
        }
        # Reject non-finite/non-JSON scorer evidence AT custody time (#960 MED-5): a bad
        # scorer output must fail the forward and leave journal evidence, never publish
        # a literal NaN or a coerced object into the sealed report.
        assert_strict_json(record)
        self._ids.add(probe_id)
        self._records.append(record)

    @property
    def sealed(self) -> bool:
        return self._sealed

    def __len__(self) -> int:
        return len(self._records)

    def seal(self) -> dict[str, Any]:
        if self._sealed:
            raise EvidenceBundleError("bundle already sealed")
        self._sealed = True
        report = {
            "schema_version": "b0-evidence-bundle-v1",
            "manifest_digest": self.manifest_digest,
            "record_count": len(self._records),
            "records": list(self._records),
        }
        assert_strict_json(report)  # defense in depth before custody transfer
        report["report_digest"] = canonical_digest(
            {k: v for k, v in report.items() if k != "report_digest"}
        )
        return report


# --------------------------------------------------------------------------- #
# Null / false-alarm distribution estimate (from sealed B0 scorer outputs).    #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class NullEstimate:
    n: int
    mean: float
    median: float
    p95: float
    flag_rate: float          # fraction of records with a truthy flag on this channel


def estimate_null_channel(values: Sequence[float], flags: Sequence[bool]) -> NullEstimate:
    """Summarize one behavioral channel's B0 null distribution + false-alarm rate.

    ``values`` are per-record scalar scores for the channel; ``flags`` are per-record
    booleans (e.g. Tier-1/Tier-2 harm flag fired at baseline = a harness false alarm).
    """
    if len(values) != len(flags):
        raise EvidenceBundleError("values and flags length mismatch")
    if not values:
        raise EvidenceBundleError("no B0 records to estimate a null from")
    if not all(math.isfinite(v) for v in values):
        raise EvidenceBundleError("non-finite value in B0 null estimate")
    ordered = sorted(values)
    n = len(ordered)
    mean = math.fsum(ordered) / n
    if n % 2 == 1:
        median = ordered[n // 2]
    else:
        median = 0.5 * (ordered[n // 2 - 1] + ordered[n // 2])
    p95 = ordered[math.ceil(0.95 * n) - 1]
    flag_rate = sum(1 for f in flags if f) / n
    return NullEstimate(n=n, mean=mean, median=median, p95=p95, flag_rate=flag_rate)
