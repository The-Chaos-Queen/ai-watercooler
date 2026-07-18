"""P5 R4 comparison sidecar — evaluator provenance, verified parent authority, journal + seam.

The mandatory R4 check (Cairn #1099, Elf's T_DIVERSITY spec §5.5) compares the JSD diversity measure
against an embedding diversity measure on the B0 null corpus, and its outcome GATES C1. That
decision needs custody as strong as the thing it decides about.

WHY A SIDECAR, NOT A P5 COMPONENT (Monk #1128/#1146): the embedding evaluator is a second
transformer, deliberately OUT-OF-PROCESS. This module validates, binds, journals, and provides the
production-callable SEAM for a comparison; it never performs it, never imports the model stack, and
never rewrites the sealed primary B0 report.

REVIEW HISTORY: rev1 (86c3748) typed fields (Monk #1133); rev2 (2844d25) derive/freeze/journal
(Codex #1137); rev3 (bc23ab5) polarity/endpoint/rehash/bind/publish (Codex #1140); rev4 (this) the
A-prime scope Monk pinned in #1146. Root cause every round: the sidecar TRUSTED input for facts it
could DERIVE, CHECK, or RECOMPUTE. rev4 closes the last of it.

REV4 (Monk #1146 A-prime — a real model-free source seam; NO live run):
  F1 LENGTH ELIGIBILITY — §4.1 is unambiguous: eligible inputs are records with token_count >= L,
     consumed truncated to exactly L. token_count < L is a typed `short_continuation` refusal;
     stop_reason == "error" is its OWN typed `unusable_error` refusal, never laundered into an
     eligible row. The comparison endpoint set is exactly C(N', 2) over ELIGIBLE probes, never all
     parent records. Elf #1148 floor: N' >= 4 (>= 6 pairs); below is INCOMPLETE, not PASS.
  F2/F3 VERIFIED PARENT AUTHORITY — a governed parent is a VERIFIED report+journal reference, not a
     caller's in-memory dicts. verify_sealed_report rehashes and structurally checks the report;
     the seam additionally runs the existing terminal-frame verifier over the journal and requires
     an `integrity_verified` terminal authority.
  F4 CAPTURE-ONCE / REVALIDATE-AT-EVERY-BOUNDARY — bind/publish exact-type the record, read its
     digests once, and RE-VALIDATE the manifest+comparison semantics, not merely digest consistency.
  F5 TRUTHFUL PUBLICATION — final-byte readback, no surviving writable hard-link alias, directory
     durability, and an explicit integrity_verified / committed_integrity_failed /
     committed_indeterminate disposition. Never ordinary success after an integrity/durability fault.
  SEAM — record_r4_comparison: a production-callable entry that takes GOVERNED evidence paths,
     verifies authority, runs build/bind/publish, and emits a fail-closed C1-precondition decision
     (rho < 0.7 => JSD replacement required; absent/invalid/non-integrity-verified/INCOMPLETE => no
     C1 authorization).

REV5 (Isegrim adversarial probe, 2026-07-18 — a confirmed P1 in rev4, closed here):
  ELIGIBILITY IS RE-DERIVED, NEVER TRUSTED. rev4 derived eligibility from the parent only inside
  build_r4_sidecar and STORED it in the record; the two C1-gating boundaries (r4_decision, publish)
  then re-trusted that stored block. Isegrim's exploit (run, not reasoned): a hand-built record over
  a REAL sealed report whose TRUE eligibility is 0 (all short_continuation) declared all probes
  eligible with a self-consistent fabricated per_pair and the real parent digest — and got
  integrity_verified / jsd_proceeds / c1=True over ZERO eligible prompts. Root cause: digest
  self-consistency was mistaken for eligibility custody. Fix: the record carries NO authoritative
  eligibility; every parent-aware boundary (bind/decision/publish) re-derives it from the VERIFIED
  parent (partition_eligibility) and cross-checks the record's comparison against the DERIVED
  eligible set, refusing on divergence. r4_decision now TAKES the sealed report and re-verifies it.
  _verify_record (which has no parent) no longer runs the completeness check — it cannot know the
  eligible set without the parent. The published artifact records the DERIVED eligibility for audit.

Torch-free and model-free-testable. Authorizes NO run, sets NO threshold, lifts NO hold.
"""
from __future__ import annotations

import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from p5_b0_harness import (
    _is_unset,
    assert_strict_json,
    canonical_digest,
)
# The existing terminal-PROTOCOL verifier (Monk #1146 F2-depth). p5_b0_run is torch-free at import
# (its only torch use is a lazy __import__ inside HFGenerationBackend.__init__), so this keeps the
# sidecar's zero-torch property while giving "governed parent" real teeth.
from p5_b0_run import verify_terminal_frames

SIDECAR_SCHEMA = "p5-r4-comparison-sidecar-v1"
B0_BUNDLE_SCHEMA = "b0-evidence-bundle-v1"

REQUIRED_SIDECAR_KEYS = frozenset({"schema", "evaluator", "runner", "parent", "panel"})

_ID = "id"
_SHA40F = "sha40"
_SHA256F = "sha256"
_POSINT = "posint"

_EVALUATOR_SPEC = {"evaluator_id": _ID, "revision_sha": _SHA40F}
_RUNNER_SPEC = {"runner_id": _ID, "runner_digest": _SHA256F}
_PARENT_SPEC = {"b0_report_digest": _SHA256F, "generation_output_digest": _SHA256F,
                "sequence_length": _POSINT}

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MUTABLE_REFS = {"main", "master", "head", "latest", "dev", "stable"}

_JSD_RANGE = (0.0, 1.0)
_SIM_RANGE = (-1.0, 1.0)
_RHO_RANGE = (-1.0, 1.0)
_RECOMPUTE_TOL = 1e-9

# Elf #1148: the minimum Spearman sample is N' >= 4 eligible probes (>= 6 pairs). Below is
# INCOMPLETE, not PASS.
_MIN_ELIGIBLE = 4

# The preregistered instrument-agreement threshold (Elf §5.5). NOT set or owned here; the decision
# only COMPARES against it. rho < RHO_GATE => JSD's residual is load-bearing => replacement required.
RHO_GATE = 0.7

_ROW_KEYS = {"pair_id", "probe_a", "probe_b", "jsd", "embedding_similarity"}
_AGG_KEYS = {"spearman_rho", "n_pairs", "mean_pairwise_jsd", "mean_pairwise_embedding"}
_RECEIPT_KEYS = ("input_token_ids_sha256", "generated_token_ids_sha256", "token_count",
                 "stop_reason")

# C1-precondition decision states (fail-closed). Only JSD_PROCEEDS is a green precondition; every
# other state denies C1 authorization.
DECISION_JSD_PROCEEDS = "jsd_proceeds"
DECISION_JSD_REPLACEMENT_REQUIRED = "jsd_replacement_required"
DECISION_INCOMPLETE = "incomplete"


class R4SidecarError(ValueError):
    """A structural refusal of the comparison sidecar (bug/unsafe config), not an outcome."""


# --------------------------------------------------------------------------- #
# Inert snapshot / deep-freeze (F2/F4).                                        #
# --------------------------------------------------------------------------- #
def _inert_snapshot(obj: Any, _depth: int = 0) -> Any:
    if _depth > 64:
        raise R4SidecarError("input nesting too deep")
    if isinstance(obj, bool) or obj is None or isinstance(obj, (str, int)):
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise R4SidecarError(f"non-finite float in input: {obj!r}")
        return obj
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if type(k) is not str:
                raise R4SidecarError(f"non-str mapping key {k!r}")
            out[k] = _inert_snapshot(v, _depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return [_inert_snapshot(v, _depth + 1) for v in obj]
    raise R4SidecarError(f"non-JSON value in input: {type(obj).__name__}")


def _deep_freeze(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return MappingProxyType({k: _deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_deep_freeze(v) for v in obj)
    return obj


def _thaw(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {k: _thaw(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return [_thaw(v) for v in obj]
    return obj


def _canonical_bytes(obj: Any) -> bytes:
    assert_strict_json(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      ensure_ascii=True).encode("utf-8")


# --------------------------------------------------------------------------- #
# Field + number validation.                                                   #
# --------------------------------------------------------------------------- #
def _field_error(value: Any, kind: str) -> str | None:
    if kind == _ID:
        if type(value) is not str:
            return f"must be an exact str (got {type(value).__name__})"
        if _is_unset(value):
            return f"is a placeholder/unset value ({value!r})"
        return None
    if kind == _SHA40F:
        if type(value) is not str:
            return f"must be an exact str 40-hex SHA (got {type(value).__name__})"
        if value.strip().lower() in _MUTABLE_REFS:
            return (f"{value!r} is a MUTABLE ref; the R4 comparison gates C1 and must pin an "
                    "immutable 40-hex revision")
        if not _SHA40.match(value):
            return f"must be an immutable lowercase 40-hex SHA (got {value!r})"
        return None
    if kind == _SHA256F:
        if type(value) is not str:
            return f"must be an exact str sha256 digest (got {type(value).__name__})"
        if not _SHA256.match(value):
            return f"must be a lowercase sha256 hex digest (got {value!r})"
        return None
    if kind == _POSINT:
        if type(value) is not int:
            return f"must be an exact positive int (got {type(value).__name__})"
        if value <= 0:
            return f"must be a positive int (got {value!r})"
        return None
    raise R4SidecarError(f"unknown field kind {kind!r}")


def _num_in_range(value: Any, lo: float, hi: float, name: str) -> str | None:
    if isinstance(value, bool) or type(value) not in (int, float):
        return f"{name} must be a finite number (got {type(value).__name__}: {value!r})"
    if not math.isfinite(value):
        return f"{name} must be finite (got {value!r})"
    if not (lo <= value <= hi):
        return f"{name} must be in [{lo}, {hi}] (got {value!r})"
    return None


def _check_block(block: Any, name: str, spec: Mapping[str, str], refusals: list[str]) -> None:
    if not isinstance(block, Mapping):
        refusals.append(f"{name} block missing or not a mapping")
        return
    unknown = set(block) - set(spec)
    if unknown:
        refusals.append(f"{name} has unknown key(s): {sorted(unknown)}")
    for key, kind in spec.items():
        if key not in block:
            refusals.append(f"{name}.{key} is missing")
            continue
        err = _field_error(block[key], kind)
        if err:
            refusals.append(f"{name}.{key} {err}")


def validate_sidecar_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Return refusal reasons ([] means clean). Never runs anything, never loads a model."""
    refusals: list[str] = []
    if not isinstance(manifest, Mapping):
        return ["sidecar manifest is not a mapping"]
    unknown = set(manifest) - set(REQUIRED_SIDECAR_KEYS)
    if unknown:
        refusals.append(f"sidecar manifest has unknown key(s): {sorted(unknown)}")
    for key in REQUIRED_SIDECAR_KEYS:
        if key not in manifest:
            refusals.append(f"required key {key!r} is missing")
    if manifest.get("schema") != SIDECAR_SCHEMA:
        refusals.append(f"schema must be {SIDECAR_SCHEMA!r} (got {manifest.get('schema')!r})")
    _check_block(manifest.get("evaluator"), "evaluator", _EVALUATOR_SPEC, refusals)
    _check_block(manifest.get("runner"), "runner", _RUNNER_SPEC, refusals)
    _check_block(manifest.get("parent"), "parent", _PARENT_SPEC, refusals)
    err = _field_error(manifest.get("panel"), _ID)
    if err:
        refusals.append(f"panel {err}")
    return refusals


# --------------------------------------------------------------------------- #
# F3 — verify the parent report structurally, then derive from the snapshot.    #
# --------------------------------------------------------------------------- #
def verify_sealed_report(sealed_report: Mapping[str, Any]) -> dict[str, Any]:
    """Reject a merely self-hashed Mapping (Monk #1146 F2-depth).

    Inert-snapshot the report, then structurally validate it: the B0 bundle schema, an exact
    ``record_count`` matching ``len(records)``, a recomputed ``published_digest``, and the required
    per-record generation receipts. A self-consistent outer checksum over an arbitrary dict is NOT a
    governed parent; the seam adds journal + terminal-authority verification on top of this.
    """
    snap = _inert_snapshot(sealed_report)
    if not isinstance(snap, dict):
        raise R4SidecarError("sealed_report must be a mapping")
    if snap.get("schema_version") != B0_BUNDLE_SCHEMA:
        raise R4SidecarError(
            f"sealed_report.schema_version must be {B0_BUNDLE_SCHEMA!r} "
            f"(got {snap.get('schema_version')!r})")
    stated = snap.get("published_digest")
    if type(stated) is not str or not _SHA256.match(stated):
        raise R4SidecarError("sealed_report.published_digest is absent or not a sha256; not sealed")
    recomputed = canonical_digest({k: v for k, v in snap.items() if k != "published_digest"})
    if recomputed != stated:
        raise R4SidecarError(
            f"sealed_report.published_digest {stated[:12]}.. != the digest {recomputed[:12]}.. "
            "recomputed from its own contents; the report has been modified since sealing")
    records = snap.get("records")
    if not isinstance(records, list) or not records:
        raise R4SidecarError("sealed_report has no records")
    if snap.get("record_count") != len(records):
        raise R4SidecarError(
            f"sealed_report.record_count {snap.get('record_count')!r} != len(records) {len(records)}")
    seen: set[str] = set()
    for i, rec in enumerate(records):
        if not isinstance(rec, Mapping):
            raise R4SidecarError(f"record {i} is not a mapping")
        pid = rec.get("probe_id")
        if type(pid) is not str or not pid:
            raise R4SidecarError(f"record {i} has no valid probe_id")
        if pid in seen:
            raise R4SidecarError(f"duplicate probe_id {pid!r} in report")
        seen.add(pid)
        if type(rec.get("raw_generation")) is not str:
            raise R4SidecarError(f"record {i} raw_generation must be a str")
        prov = rec.get("provenance")
        if not isinstance(prov, Mapping):
            raise R4SidecarError(f"record {i} has no provenance")
        for key in _RECEIPT_KEYS:
            if key not in prov:
                raise R4SidecarError(f"record {i} provenance missing receipt field {key!r}")
        if type(prov.get("token_count")) is not int or prov["token_count"] < 0:
            raise R4SidecarError(f"record {i} token_count must be a non-negative int")
        if type(prov.get("stop_reason")) is not str:
            raise R4SidecarError(f"record {i} stop_reason must be a str")
    return snap


def derive_generation_corpus_digest(sealed_report: Mapping[str, Any]) -> str:
    """Canonical digest over the report's per-generation receipts (binds what the evaluator ate)."""
    records = sealed_report.get("records")
    if not isinstance(records, Sequence) or not records:
        raise R4SidecarError("sealed report has no records to derive a generation corpus from")
    rows = []
    for i, rec in enumerate(records):
        prov = rec.get("provenance") if isinstance(rec, Mapping) else None
        if not isinstance(prov, Mapping):
            raise R4SidecarError(f"record {i} has no provenance")
        try:
            rows.append({
                "probe_id": rec["probe_id"],
                "raw_generation": rec["raw_generation"],
                "input_token_ids_sha256": prov["input_token_ids_sha256"],
                "generated_token_ids_sha256": prov["generated_token_ids_sha256"],
                "token_count": prov["token_count"],
                "stop_reason": prov["stop_reason"],
            })
        except KeyError as exc:
            raise R4SidecarError(f"record {i} missing a generation receipt field: {exc}") from None
    rows.sort(key=lambda r: r["probe_id"])
    return canonical_digest(rows)


# --------------------------------------------------------------------------- #
# F1 — length eligibility. Pairs are over ELIGIBLE probes only.                 #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Eligibility:
    eligible: tuple[str, ...]                 # sorted probe_ids with token_count >= L, non-error
    refusals: tuple[Mapping[str, Any], ...]   # typed per-probe refusal receipts


def partition_eligibility(verified_report: Mapping[str, Any], sequence_length: int) -> Eligibility:
    """Partition report probes into eligible vs typed refusals (Monk #1146 F1 / §4.1).

    Eligible: token_count >= L (consumed truncated to exactly L). token_count < L -> a
    ``short_continuation`` refusal. stop_reason == "error" -> its OWN ``unusable_error`` refusal, and
    it must NEVER be laundered into an eligible row even if long. Order: an error is unusable
    regardless of length, so it is classified first.
    """
    if type(sequence_length) is not int or sequence_length <= 0:
        raise R4SidecarError("sequence_length (L) must be a positive int")
    eligible: list[str] = []
    refusals: list[Mapping[str, Any]] = []
    for rec in verified_report["records"]:
        pid = rec["probe_id"]
        prov = rec["provenance"]
        stop = prov["stop_reason"]
        tc = prov["token_count"]
        if stop == "error":
            refusals.append({"probe_id": pid, "reason": "unusable_error",
                             "token_count": tc, "stop_reason": stop})
        elif tc < sequence_length:
            refusals.append({"probe_id": pid, "reason": "short_continuation",
                             "token_count": tc, "stop_reason": stop})
        else:
            eligible.append(pid)
    return Eligibility(eligible=tuple(sorted(eligible)),
                       refusals=tuple(sorted(refusals, key=lambda r: r["probe_id"])))


# --------------------------------------------------------------------------- #
# F1/F4 — recompute the summary; the caller may not just declare it.           #
# --------------------------------------------------------------------------- #
def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_rho(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0.0 or syy == 0.0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def diversity_agreement_rho(jsds: Sequence[float], sims: Sequence[float]) -> float:
    """Spearman of JSD DIVERSITY vs embedding DIVERGENCE (1 - cosine) — the gate-correct polarity.

    Elf #1148: the evaluator emits raw cosine_similarity; the 1 - cosine transform is applied HERE,
    at comparison time. Spearman is rank-invariant to the monotone transform, so only the sign
    changes vs correlating against similarity, and diversity-vs-diversity is the sign the gate needs.
    Perfect agreement -> +1.
    """
    return spearman_rho(jsds, [1.0 - s for s in sims])


def validate_comparison(per_pair: Sequence[Mapping[str, Any]], aggregate: Mapping[str, Any],
                        *, eligible_probe_ids: Sequence[str] | None = None) -> list[str]:
    """Range + endpoint identity + COMPLETENESS over ELIGIBLE probes + RECOMPUTATION.

    Completeness is over the ELIGIBLE set (Monk #1146 F1), never all report probes. The N' >= 4
    floor is NOT enforced here (it is a decision outcome: below-floor is INCOMPLETE, not a build
    refusal); this validates that whatever pairs are present cover exactly C(eligible, 2).
    """
    refusals: list[str] = []
    if not isinstance(per_pair, Sequence) or isinstance(per_pair, (str, bytes)):
        return ["per_pair must be a sequence of rows"]
    if not per_pair:
        return ["no per-pair comparison rows; an empty comparison decides nothing"]

    probe_set = set(eligible_probe_ids) if eligible_probe_ids is not None else None
    seen_ids: set[str] = set()
    seen_endpoints: set[frozenset] = set()
    jsds: list[float] = []
    sims: list[float] = []
    for i, row in enumerate(per_pair):
        if not isinstance(row, Mapping):
            refusals.append(f"per-pair row {i} is not a mapping")
            continue
        unknown = set(row) - _ROW_KEYS
        if unknown:
            refusals.append(f"per-pair row {i} has unknown key(s): {sorted(unknown)}")
        pe = _field_error(row.get("pair_id"), _ID) if "pair_id" in row else "is missing"
        if pe:
            refusals.append(f"per-pair row {i} pair_id {pe}")
        elif row["pair_id"] in seen_ids:
            refusals.append(f"per-pair row {i} duplicates pair_id {row['pair_id']!r}")
        else:
            seen_ids.add(row["pair_id"])

        a, b = row.get("probe_a"), row.get("probe_b")
        ae = _field_error(a, _ID) if "probe_a" in row else "is missing"
        be = _field_error(b, _ID) if "probe_b" in row else "is missing"
        if ae:
            refusals.append(f"per-pair row {i} probe_a {ae}")
        if be:
            refusals.append(f"per-pair row {i} probe_b {be}")
        if not ae and not be:
            if a == b:
                refusals.append(f"per-pair row {i} endpoints are identical ({a!r})")
            elif probe_set is not None and (a not in probe_set or b not in probe_set):
                refusals.append(
                    f"per-pair row {i} endpoints {a!r},{b!r} are not both ELIGIBLE probes")
            else:
                key = frozenset((a, b))
                if key in seen_endpoints:
                    refusals.append(f"per-pair row {i} duplicates endpoint pair {sorted(key)}")
                seen_endpoints.add(key)

        je = _num_in_range(row.get("jsd"), *_JSD_RANGE, "jsd") if "jsd" in row else "jsd is missing"
        if je:
            refusals.append(f"per-pair row {i} {je}")
        else:
            jsds.append(row["jsd"])
        se = (_num_in_range(row.get("embedding_similarity"), *_SIM_RANGE, "embedding_similarity")
              if "embedding_similarity" in row else "embedding_similarity is missing")
        if se:
            refusals.append(f"per-pair row {i} {se}")
        else:
            sims.append(row["embedding_similarity"])

    if probe_set is not None:
        expected = {frozenset(p) for p in combinations(sorted(probe_set), 2)}
        if seen_endpoints != expected and not any("endpoints" in r or "probe_" in r
                                                  for r in refusals):
            missing = expected - seen_endpoints
            extra = seen_endpoints - expected
            refusals.append(
                f"comparison endpoint set is not the complete ELIGIBLE pair set "
                f"(missing {len(missing)}, extra {len(extra)} of {len(expected)})")

    if not isinstance(aggregate, Mapping):
        return [*refusals, "aggregate must be a mapping"]
    unknown = set(aggregate) - _AGG_KEYS
    if unknown:
        refusals.append(f"aggregate has unknown key(s): {sorted(unknown)}")
    for key, rng in (("spearman_rho", _RHO_RANGE), ("mean_pairwise_jsd", _JSD_RANGE),
                     ("mean_pairwise_embedding", _SIM_RANGE)):
        if key not in aggregate:
            refusals.append(f"aggregate.{key} is missing")
        else:
            e = _num_in_range(aggregate[key], *rng, key)
            if e:
                refusals.append(f"aggregate.{e}")
    ne = _field_error(aggregate.get("n_pairs"), _POSINT) if "n_pairs" in aggregate else "is missing"
    if ne:
        refusals.append(f"aggregate.n_pairs {ne}")
    elif aggregate["n_pairs"] != len(per_pair):
        refusals.append(f"aggregate.n_pairs {aggregate['n_pairs']} != {len(per_pair)} per-pair rows")

    if len(jsds) == len(sims) == len(per_pair) and len(per_pair) >= 1:
        checks = [
            ("spearman_rho", diversity_agreement_rho(jsds, sims)),
            ("mean_pairwise_jsd", sum(jsds) / len(jsds)),
            ("mean_pairwise_embedding", sum(sims) / len(sims)),
        ]
        for key, computed in checks:
            declared = aggregate.get(key)
            if isinstance(declared, (int, float)) and not isinstance(declared, bool):
                if abs(float(declared) - computed) > _RECOMPUTE_TOL:
                    refusals.append(
                        f"aggregate.{key} {declared} does not match the value {computed:.12g} "
                        "recomputed from the rows; the summary must describe the rows")
    return refusals


@dataclass(frozen=True)
class R4SidecarRecord:
    """The sealed comparison record: deep-frozen so its digest cannot go stale (Codex #1137 F1)."""

    manifest_digest: str
    output_digest: str
    record: Mapping[str, Any]


def build_r4_sidecar(
    manifest: Mapping[str, Any],
    *,
    sealed_report: Mapping[str, Any],
    per_pair: Sequence[Mapping[str, Any]],
    aggregate: Mapping[str, Any],
) -> R4SidecarRecord:
    """Validate, DERIVE-bind to the verified sealed report over ELIGIBLE probes, and seal.

    No model, no comparison, no parent mutation. Eligibility (F1) is derived from the report's own
    receipts and the manifest's L to validate the comparison covers exactly C(N', 2) over eligible
    probes. rev5 (Isegrim probe): eligibility is NOT stored as an authority on the record — it is a
    pure function of (verified parent, L) and every gating boundary re-derives it from the bound
    parent. Storing it would invite a consumer to re-trust a declaration; the parent is the custody.
    """
    manifest = _inert_snapshot(manifest)
    per_pair = _inert_snapshot(per_pair)
    aggregate = _inert_snapshot(aggregate)

    refusals = validate_sidecar_manifest(manifest)
    if refusals:
        raise R4SidecarError("; ".join(refusals))
    par = manifest["parent"]

    verified = verify_sealed_report(sealed_report)
    if par["b0_report_digest"] != verified["published_digest"]:
        raise R4SidecarError(
            f"parent.b0_report_digest {par['b0_report_digest'][:12]}.. != the verified report's "
            f"published_digest {verified['published_digest'][:12]}.. — not that run")
    derived_gen = derive_generation_corpus_digest(verified)
    if par["generation_output_digest"] != derived_gen:
        raise R4SidecarError(
            f"parent.generation_output_digest {par['generation_output_digest'][:12]}.. != the "
            f"digest {derived_gen[:12]}.. derived from the report's OWN receipts — never a second "
            "generation")

    elig = partition_eligibility(verified, par["sequence_length"])
    comparison_refusals = validate_comparison(per_pair, aggregate,
                                              eligible_probe_ids=elig.eligible)
    if comparison_refusals:
        raise R4SidecarError("; ".join(comparison_refusals))

    plain_record: dict[str, Any] = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": dict(manifest["evaluator"]),
        "runner": dict(manifest["runner"]),
        "panel": manifest["panel"],
        "parent": dict(par),
        "per_pair": [dict(r) for r in per_pair],
        "aggregate": dict(aggregate),
    }
    assert_strict_json(plain_record)
    output_digest = canonical_digest(plain_record)
    return R4SidecarRecord(
        manifest_digest=canonical_digest(dict(manifest)),
        output_digest=output_digest,
        record=_deep_freeze(plain_record),
    )


# --------------------------------------------------------------------------- #
# F4 — capture once, re-validate semantics at every public boundary.           #
# --------------------------------------------------------------------------- #
def _verify_record(sidecar: Any) -> dict[str, Any]:
    """Exact-type the carrier, re-derive both digests, and RE-VALIDATE the semantics.

    Codex #1140 F4 + #1144 F3/F4: the deep-freeze stops in-place mutation, but a public boundary
    must not trust a hand-built or subclassed carrier. Exact-type ``R4SidecarRecord`` (a subclass
    could override ``output_digest`` to return different values on successive reads), read the frozen
    content ONCE, confirm both digests match, and re-run the manifest + comparison validation so a
    record whose evaluator revision is "main" cannot bind merely because its digest is self
    consistent.

    rev5 (Isegrim probe): this guard has NO parent report, so it CANNOT know the eligible set and
    must not check comparison completeness against any declared/stored eligibility — doing so is how
    rev4 leaked (a self-consistent fabrication passed its own declaration). It validates the
    comparison's shape/ranges/endpoint-identity/recompute only; completeness over the DERIVED
    eligible set is enforced at the parent-aware boundaries (bind/decision/publish).
    """
    if type(sidecar) is not R4SidecarRecord:
        raise R4SidecarError(f"not an exact R4SidecarRecord (got {type(sidecar).__name__})")
    output_digest = sidecar.output_digest          # read the digest attributes exactly once
    manifest_digest = sidecar.manifest_digest
    if type(output_digest) is not str or type(manifest_digest) is not str:
        raise R4SidecarError("record digests must be exact strs")
    thawed = _thaw(sidecar.record)
    if canonical_digest(thawed) != output_digest:
        raise R4SidecarError("record output_digest does not match its content (stale or tampered)")
    reconstructed_manifest = {
        "schema": thawed["schema"], "evaluator": thawed["evaluator"],
        "runner": thawed["runner"], "parent": thawed["parent"], "panel": thawed["panel"],
    }
    if canonical_digest(reconstructed_manifest) != manifest_digest:
        raise R4SidecarError("record manifest_digest does not match the reconstructed manifest")
    # Re-validate semantics, not just digest consistency. Completeness-over-eligible is NOT checked
    # here: without the parent report this boundary cannot derive the eligible set, and trusting a
    # declared one is exactly the rev4 leak. eligible_probe_ids=None => shape/ranges/endpoints only.
    m_refusals = validate_sidecar_manifest(reconstructed_manifest)
    if m_refusals:
        raise R4SidecarError("record manifest fails re-validation: " + "; ".join(m_refusals))
    c_refusals = validate_comparison(thawed["per_pair"], thawed["aggregate"],
                                     eligible_probe_ids=None)
    if c_refusals:
        raise R4SidecarError("record comparison fails re-validation: " + "; ".join(c_refusals))
    return thawed


def _rederive_eligibility(verified_report: Mapping[str, Any],
                          record: Mapping[str, Any]) -> Eligibility:
    """Re-derive eligibility from the VERIFIED parent and cross-check the record's comparison.

    rev5 (Isegrim probe, 2026-07-18): the SINGLE custody point for eligibility at every parent-aware
    boundary. The record carries no authoritative eligibility; it is a pure function of the bound
    parent's receipts and L. Confirm the record's parent digest matches the verified report, derive
    the eligible set from the report, and re-run the comparison validation against the DERIVED set
    (completeness over C(N', 2) eligible pairs). A record whose per_pair does not cover exactly the
    derived eligible set — the rev4 exploit's 6-declared-over-0-real fabrication — is REFUSED here,
    before any C1-precondition can be computed. Digest self-consistency is not eligibility custody.
    """
    if record["parent"]["b0_report_digest"] != verified_report["published_digest"]:
        raise R4SidecarError(
            "sidecar parent digest does not match the sealed report's recomputed published_digest")
    elig = partition_eligibility(verified_report, record["parent"]["sequence_length"])
    refusals = validate_comparison(record["per_pair"], record["aggregate"],
                                   eligible_probe_ids=elig.eligible)
    if refusals:
        raise R4SidecarError(
            "the comparison does not cover the eligibility DERIVED from the bound parent (a stored "
            "or declared eligibility is not custody): " + "; ".join(refusals))
    return elig


def bind_to_parent_report(sealed_report: Mapping[str, Any],
                          sidecar: R4SidecarRecord) -> dict[str, Any]:
    """The audit LINK between a sealed B0 report and a sidecar — parent read, never written.

    Reads ONLY the verified thawed snapshot (Codex #1140 F4), and re-derives eligibility from the
    verified parent (rev5): binding a sidecar whose comparison disagrees with the parent's true
    eligible set is refused, not linked.
    """
    verified_record = _verify_record(sidecar)
    verified_report = verify_sealed_report(sealed_report)
    _rederive_eligibility(verified_report, verified_record)
    link = {
        "schema": SIDECAR_SCHEMA + "-link",
        "b0_published_digest": verified_report["published_digest"],
        "sidecar_manifest_digest": sidecar.manifest_digest,
        "sidecar_output_digest": sidecar.output_digest,
        "evaluator_id": verified_record["evaluator"]["evaluator_id"],
        "evaluator_revision_sha": verified_record["evaluator"]["revision_sha"],
    }
    assert_strict_json(link)
    link["link_digest"] = canonical_digest({k: v for k, v in link.items() if k != "link_digest"})
    return link


# --------------------------------------------------------------------------- #
# The C1-precondition decision (fail-closed).                                  #
# --------------------------------------------------------------------------- #
def r4_decision(sealed_report: Mapping[str, Any], sidecar: R4SidecarRecord) -> dict[str, Any]:
    """Emit the exact, fail-closed R4 decision/precondition record for the future C1 boundary.

    Monk #1146: rho < RHO_GATE => JSD replacement required; below the N' >= 4 floor => INCOMPLETE.
    ONLY ``jsd_proceeds`` is a green precondition; every other state (INCOMPLETE, replacement, or any
    invalid/non-integrity-verified evidence upstream) denies C1 authorization. The rho used is the
    recomputed diversity-agreement rho, not merely the declared one.

    rev5 (Isegrim probe): this boundary now TAKES the sealed report and re-verifies it, then
    RE-DERIVES eligibility from that verified parent — it no longer reads a stored ``eligibility``
    block off the record (rev4's leak: the block was declared by the caller and re-trusted here).
    n_eligible is the DERIVED count; a fabricated comparison over non-eligible probes is refused by
    ``_rederive_eligibility`` before any state is computed.
    """
    record = _verify_record(sidecar)                 # revalidates before deciding
    verified_report = verify_sealed_report(sealed_report)
    elig = _rederive_eligibility(verified_report, record)
    n_eligible = len(elig.eligible)
    rows = record["per_pair"]
    rho = diversity_agreement_rho([r["jsd"] for r in rows],
                                  [r["embedding_similarity"] for r in rows])
    if n_eligible < _MIN_ELIGIBLE:
        state, c1 = DECISION_INCOMPLETE, False
        reason = (f"n_eligible {n_eligible} < floor {_MIN_ELIGIBLE}: too few non-refused prompts for "
                  "a meaningful Spearman; INCOMPLETE, not PASS")
    elif rho < RHO_GATE:
        state, c1 = DECISION_JSD_REPLACEMENT_REQUIRED, False
        reason = (f"rho {rho:.6g} < {RHO_GATE}: JSD's residual is load-bearing; JSD must be replaced "
                  "with the embedding measure before C1")
    else:
        state, c1 = DECISION_JSD_PROCEEDS, True
        reason = f"rho {rho:.6g} >= {RHO_GATE}: JSD and the embedding measure agree; JSD may proceed"
    decision = {
        "schema": SIDECAR_SCHEMA + "-decision",
        "state": state,
        "c1_authorization_permitted": c1,
        "reason": reason,
        "recomputed_rho": rho,
        "rho_gate": RHO_GATE,
        "n_eligible": n_eligible,
        "n_refused": len(elig.refusals),
        "sidecar_output_digest": sidecar.output_digest,
        "b0_report_digest": record["parent"]["b0_report_digest"],
    }
    assert_strict_json(decision)
    decision["decision_digest"] = canonical_digest(
        {k: v for k, v in decision.items() if k != "decision_digest"})
    return decision


# --------------------------------------------------------------------------- #
# F5 — atomic, no-replace publication with a TRUTHFUL terminal disposition.     #
# --------------------------------------------------------------------------- #
DISPOSITION_VERIFIED = "integrity_verified"
DISPOSITION_INTEGRITY_FAILED = "committed_integrity_failed"
DISPOSITION_INDETERMINATE = "committed_indeterminate"


@dataclass(frozen=True)
class R4PublishResult:
    path: str
    published_digest: str
    committed_bytes: int
    disposition: str                          # one of the DISPOSITION_* above


def publish_r4_sidecar(sealed_report: Mapping[str, Any], sidecar: R4SidecarRecord,
                       sidecar_path: Path) -> R4PublishResult:
    """Atomically publish the artifact (record + link + decision). No-replace, truthful disposition.

    Monk #1146 F5: after linking, READ BACK the final bytes and confirm they equal what was meant to
    commit; a mismatch => committed_integrity_failed. The temp is a hard link to the same inode, and
    it is WRITABLE, so a surviving temp is a mutation alias on the final artifact — if the post-link
    unlink fails, that is committed_integrity_failed, never success. A directory-durability fault is
    committed_indeterminate. Never report integrity_verified after any of these.

    rev5 (Isegrim probe): re-derives eligibility from the verified parent (has it in hand) and
    refuses a fabricated comparison BEFORE staging any bytes; the committed artifact records the
    DERIVED eligibility, never a caller's declaration.
    """
    sidecar_path = Path(sidecar_path)
    if sidecar_path.exists() or sidecar_path.is_symlink():
        raise R4SidecarError(f"sidecar path already exists (no-replace): {sidecar_path}")
    parent_dir = sidecar_path.parent
    if parent_dir.is_symlink() or not parent_dir.is_dir():
        raise R4SidecarError(f"sidecar parent dir must be an existing non-symlink: {parent_dir}")

    record = _verify_record(sidecar)
    verified_report = verify_sealed_report(sealed_report)
    elig = _rederive_eligibility(verified_report, record)   # rev5: refuse a fabrication before commit
    link = bind_to_parent_report(sealed_report, sidecar)
    decision = r4_decision(sealed_report, sidecar)
    artifact = {
        "schema": SIDECAR_SCHEMA + "-artifact",
        "record": record,
        # The DERIVED eligibility (from the verified parent, not a stored declaration) for audit.
        "eligibility": {
            "sequence_length": record["parent"]["sequence_length"],
            "n_eligible": len(elig.eligible),
            "eligible_probe_ids": list(elig.eligible),
            "refusals": [dict(r) for r in elig.refusals],
        },
        "link": link,
        "decision": decision,
        "sidecar_output_digest": sidecar.output_digest,
        "sidecar_manifest_digest": sidecar.manifest_digest,
    }
    assert_strict_json(artifact)
    artifact["published_digest"] = canonical_digest(
        {k: v for k, v in artifact.items() if k != "published_digest"})
    committed = _canonical_bytes(artifact)

    fd, tmp_name = tempfile.mkstemp(prefix=sidecar_path.name + ".", suffix=".tmp",
                                    dir=str(parent_dir))
    tmp = Path(tmp_name)
    disposition = DISPOSITION_VERIFIED
    try:
        os.write(fd, committed)
        os.fsync(fd)
    finally:
        os.close(fd)
    if tmp.read_bytes() != committed:
        tmp.unlink(missing_ok=True)
        raise R4SidecarError("staged sidecar bytes did not verify before commit")
    os.link(str(tmp), str(sidecar_path))          # no-replace: fails if the target appeared

    # From here the final artifact exists; downgrade the disposition truthfully on any fault, but
    # never raise over a committed artifact (Monk #1146: never ordinary success after a fault).
    if sidecar_path.read_bytes() != committed:    # final-byte readback
        disposition = DISPOSITION_INTEGRITY_FAILED
    try:
        tmp.unlink()                              # the writable hard-link alias MUST be removed
    except OSError:
        disposition = DISPOSITION_INTEGRITY_FAILED   # a surviving writable alias can mutate the file
    if tmp.exists():
        disposition = DISPOSITION_INTEGRITY_FAILED
    # Directory-entry durability. A real fsync FAULT (supported but failed) is indeterminate; a
    # platform that cannot open a directory fd at all (e.g. Windows) is NOT a fault — the file was
    # already fsync'd, which is the durability the platform offers — so it does not downgrade.
    if _fsync_dir(parent_dir) is False and disposition == DISPOSITION_VERIFIED:
        disposition = DISPOSITION_INDETERMINATE
    return R4PublishResult(path=str(sidecar_path), published_digest=artifact["published_digest"],
                           committed_bytes=len(committed), disposition=disposition)


def _fsync_dir(directory: Path) -> bool | None:
    """Best-effort directory durability. True = fsync'd durable; None = unsupported by this platform
    (could not open a directory fd, e.g. Windows) which is NOT a fault; False = supported but the
    fsync itself raised, which IS a durability fault."""
    try:
        dfd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return None
    try:
        os.fsync(dfd)
        return True
    except OSError:
        return False
    finally:
        os.close(dfd)


# --------------------------------------------------------------------------- #
# The production-callable seam (Monk #1146 non-test integration).              #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class R4RecordResult:
    decision: Mapping[str, Any]
    publish: R4PublishResult | None
    ok: bool                                  # True iff authority verified AND artifact committed clean


def _load_governed_report(report_path: Path, journal_path: Path) -> tuple[dict[str, Any], bytes]:
    """Load a GOVERNED B0 evidence reference: the report bytes cross-verified by the journal.

    Monk #1146 F2-depth: a governed parent is a verified report+JOURNAL reference, not a caller's
    in-memory dict. Read the report bytes, run the existing terminal-frame verifier over the journal
    binding those exact bytes/digest, and REQUIRE an ``integrity_verified`` terminal authority.
    """
    report_path, journal_path = Path(report_path), Path(journal_path)
    if not report_path.is_file():
        raise R4SidecarError(f"B0 report artifact not found: {report_path}")
    if not journal_path.is_file():
        raise R4SidecarError(f"B0 journal artifact not found: {journal_path}")
    report_bytes = report_path.read_bytes()
    try:
        report = json.loads(report_bytes)
    except json.JSONDecodeError as exc:
        raise R4SidecarError(f"B0 report is not valid JSON: {exc}") from None
    if not isinstance(report, dict):
        raise R4SidecarError("B0 report root is not a JSON object")
    published = report.get("published_digest")
    if type(published) is not str or not _SHA256.match(published):
        raise R4SidecarError("B0 report has no sha256 published_digest; not sealed")
    verdict = verify_terminal_frames(journal_path, report_published_digest=published,
                                     committed_report_bytes=report_bytes)
    if not verdict.get("ok"):
        raise R4SidecarError(
            f"B0 journal did not verify: {verdict.get('reason')!r}; not a governed parent")
    if verdict.get("disposition") != DISPOSITION_VERIFIED:
        raise R4SidecarError(
            f"B0 terminal authority is {verdict.get('disposition')!r}, not {DISPOSITION_VERIFIED!r}; "
            "no C1 authorization may rest on a non-integrity-verified parent")
    return report, report_bytes


def record_r4_comparison(
    *,
    report_path: Path,
    journal_path: Path,
    manifest: Mapping[str, Any],
    per_pair: Sequence[Mapping[str, Any]],
    aggregate: Mapping[str, Any],
    sidecar_path: Path,
) -> R4RecordResult:
    """Production-callable seam: governed evidence PATHS -> verified build/bind/publish -> decision.

    Monk #1146 non-test integration. The evaluator remains OUT-OF-PROCESS; this consumes its
    precomputed output. It NEVER runs B0, loads a model, or authorizes C1 — it emits a fail-closed
    C1-precondition. A non-integrity-verified / absent / invalid parent, or an INCOMPLETE /
    replacement-required comparison, all deny C1 authorization.
    """
    report, _report_bytes = _load_governed_report(report_path, journal_path)
    sidecar = build_r4_sidecar(manifest, sealed_report=report, per_pair=per_pair,
                               aggregate=aggregate)
    result = publish_r4_sidecar(report, sidecar, sidecar_path)
    decision = r4_decision(report, sidecar)
    # The seam only reports ok when authority verified, the artifact committed cleanly (a downgraded
    # disposition is NOT ok), AND the precondition permits C1. Fail-closed on everything else.
    ok = (result.disposition == DISPOSITION_VERIFIED
          and bool(decision["c1_authorization_permitted"]))
    return R4RecordResult(decision=decision, publish=result, ok=ok)
