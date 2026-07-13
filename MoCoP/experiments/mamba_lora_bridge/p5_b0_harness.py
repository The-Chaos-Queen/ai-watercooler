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
from typing import Any, Mapping, Sequence

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
REQUIRED_B0_KEYS = frozenset({
    "schema_version",
    "run_kind",
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

# Values that count as "not really set" (a pre-launch failure). Case-insensitive.
_UNSET_STRINGS = {"", "tbd", "null", "none", "pending", "todo", "changeme"}


class B0ManifestError(ValueError):
    """A structural launch-refusal reason (bug or unsafe config), not a run outcome."""


def _is_unset(value: Any) -> bool:
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


def validate_b0_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Return a list of launch-refusal reasons ([] means clean). Never runs anything."""

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

    if manifest.get("run_kind") != B0_RUN_KIND:
        refusals.append(
            f"run_kind must be {B0_RUN_KIND!r} (got {manifest.get('run_kind')!r}); "
            "this harness authorizes B0 baseline only, never an injection run kind"
        )

    _check_no_component(manifest.get("components"), refusals)
    _check_pinned(manifest, refusals)
    _check_sev_disjointness(manifest.get("sev_ids"), refusals)
    _check_evidence_sink(manifest.get("evidence_sink"), refusals)
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
