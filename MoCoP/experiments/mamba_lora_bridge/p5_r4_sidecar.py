"""P5 R4 comparison sidecar — evaluator provenance, derived binding, journal (#155 item 5).

The mandatory R4 check (Cairn #1099, Elf's T_DIVERSITY spec §5.5) compares the JSD-based diversity
measure against an embedding-based one on the B0 null corpus, and its outcome GATES C1: if the two
disagree (Spearman rho below the preregistered instrument-agreement threshold), JSD's residual is
load-bearing and the function must be replaced before C1. That decision needs custody as strong as
the thing it decides about.

WHY A SIDECAR, NOT A P5 COMPONENT (Monk #1128, resolving Gidim #1114 B3): the embedding evaluator
(`all-MiniLM-L6-v2`) is a second transformer, deliberately OUT-OF-PROCESS. It is NOT in
``COMPONENT_ROUTES``/``FORBIDDEN_ROUTE_MODULES`` — those govern the MONITOR PROCESS. This module
validates, binds, and journals a comparison; it never performs it, never imports the model stack,
and never rewrites the sealed primary B0 report.

CODEX #1137 (CHANGES) drove the rev-2 redesign. The five P1 findings share ONE root cause and ONE
cure: the sidecar TRUSTED THE CALLER for facts it could DERIVE. Rev 2 derives them.
  F1 mutable seal → the record is DEEP-FROZEN; in-place mutation raises, and the digest is
     re-verified at publish, so a stale digest cannot ride along.
  F2 validate/copy TOCTOU → inputs are normalized to ONE inert JSON snapshot FIRST; validation,
     hashing, and publication all read only that snapshot, never the live (possibly two-view) input.
  F3 self-attested generation binding → the b0-report digest and the generation-corpus digest are
     DERIVED from the sealed report's own per-record receipts, not taken as caller arguments.
  F4 unchecked comparison evidence → values are range-checked, the pair set must be COMPLETE
     (C(N,2) over the report's probes), and the declared rho/means are RECOMPUTED from the rows.
  F5 no publication path → an O_EXCL/no-replace atomic writer emits a terminal-disposition artifact
     bound to the parent, without touching the parent.

Torch-free and model-free-testable: tests inject a fake evaluator. Authorizes NO run, sets NO
threshold, lifts NO hold.
"""
from __future__ import annotations

import math
import os
import re
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

SIDECAR_SCHEMA = "p5-r4-comparison-sidecar-v1"

REQUIRED_SIDECAR_KEYS = frozenset({"schema", "evaluator", "runner", "parent", "panel"})

# FIELD-SPECIFIC types/formats (Monk #1133). Type AND format are ONE obligation per field: the
# rev-1 bug typed fields as "str or int" and format-checked only `if isinstance(value, str)`, so a
# wrong-typed value dodged its own check. A format check guarded by a type it does not enforce is
# decoration.
_ID = "id"            # nonempty exact str, non-placeholder
_SHA40F = "sha40"     # immutable lowercase 40-hex revision
_SHA256F = "sha256"   # 64-hex digest
_POSINT = "posint"    # exact positive int (bool excluded)

_EVALUATOR_SPEC = {"evaluator_id": _ID, "revision_sha": _SHA40F}
_RUNNER_SPEC = {"runner_id": _ID, "runner_digest": _SHA256F}
_PARENT_SPEC = {"b0_report_digest": _SHA256F, "generation_output_digest": _SHA256F,
                "sequence_length": _POSINT}

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MUTABLE_REFS = {"main", "master", "head", "latest", "dev", "stable"}

# Value ranges the comparison evidence MUST lie in (Codex #1137 F4). JSD in bits is [0, 1];
# cosine similarity is [-1, 1]; Spearman rho is [-1, 1]. Anything outside is not a measurement.
_JSD_RANGE = (0.0, 1.0)
_SIM_RANGE = (-1.0, 1.0)
_RHO_RANGE = (-1.0, 1.0)

# The recomputed rho / means must match the declared values to within this absolute tolerance — the
# evaluator computes in float, so exact equality would be brittle, but the declared summary must be
# the ACTUAL summary of the rows, not a number a caller wrote in.
_RECOMPUTE_TOL = 1e-9


class R4SidecarError(ValueError):
    """A structural refusal of the comparison sidecar (bug/unsafe config), not an outcome."""


# --------------------------------------------------------------------------- #
# F2 — one inert JSON snapshot; nothing downstream reads the live input again.  #
# --------------------------------------------------------------------------- #
def _inert_snapshot(obj: Any, _depth: int = 0) -> Any:
    """Recursively rebuild ``obj`` from EXACT built-in JSON types, or raise.

    Mirrors the runner's #1009 BLOCKER-3 discipline: a caller-owned Mapping/Sequence may return
    different contents on each read (a two-view object passes validation with numbers, then hands
    the copy strings). Reading the input EXACTLY ONCE into inert built-ins closes that window — the
    snapshot is what gets validated, hashed, and published, and it cannot change underfoot.
    """
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
        for k, v in obj.items():           # ONE pass over this mapping
            if type(k) is not str:
                raise R4SidecarError(f"non-str mapping key {k!r}")
            out[k] = _inert_snapshot(v, _depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return [_inert_snapshot(v, _depth + 1) for v in obj]   # ONE pass over this sequence
    raise R4SidecarError(f"non-JSON value in input: {type(obj).__name__}")


# --------------------------------------------------------------------------- #
# F1 — deep-freeze the sealed record so its digest cannot go stale.             #
# --------------------------------------------------------------------------- #
def _deep_freeze(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return MappingProxyType({k: _deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_deep_freeze(v) for v in obj)
    return obj


def _thaw(obj: Any) -> Any:
    """Convert a deep-frozen view back to plain built-ins so it can be digested/serialized."""
    if isinstance(obj, Mapping):
        return {k: _thaw(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return [_thaw(v) for v in obj]
    return obj


# --------------------------------------------------------------------------- #
# Field + number validation.                                                    #
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
        if type(value) is not int:           # bool is an int subclass; exact-type excludes it
            return f"must be an exact positive int (got {type(value).__name__})"
        if value <= 0:
            return f"must be a positive int (got {value!r})"
        return None
    raise R4SidecarError(f"unknown field kind {kind!r}")


def _num_in_range(value: Any, lo: float, hi: float, name: str) -> str | None:
    """A comparison value must be a FINITE real number IN RANGE — not merely JSON-serializable.

    ``jsd="not-a-number"`` is valid JSON and hashes happily; ``jsd=-7`` is a finite number that is
    not a JSD. Both are "a SHA over malformed values is not custody" (Monk #1133 / Codex #1137 F4).
    """
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
# F3 — derive the parent bindings from the sealed report's own receipts.        #
# --------------------------------------------------------------------------- #
def derive_generation_corpus_digest(sealed_report: Mapping[str, Any]) -> str:
    """Canonical digest over the sealed B0 report's per-generation receipts.

    Authoritative and derivable WITHOUT touching the primary report (Monk #1128 scope lock): each
    record already carries input/generated token-id digests, stop_reason and token_count. The
    corpus digest is a deterministic function of those, so the sidecar can require the manifest's
    declared ``generation_output_digest`` to EQUAL what the report actually produced — the
    same-generation binding becomes a derivation, not a caller's self-attestation (Codex #1137 F3).
    """
    records = sealed_report.get("records")
    if not isinstance(records, Sequence) or not records:
        raise R4SidecarError("sealed report has no records to derive a generation corpus from")
    rows = []
    for i, rec in enumerate(records):
        if not isinstance(rec, Mapping):
            raise R4SidecarError(f"sealed report record {i} is not a mapping")
        prov = rec.get("provenance")
        if not isinstance(prov, Mapping):
            raise R4SidecarError(f"sealed report record {i} has no provenance")
        try:
            rows.append({
                "probe_id": rec["probe_id"],
                "input_token_ids_sha256": prov["input_token_ids_sha256"],
                "generated_token_ids_sha256": prov["generated_token_ids_sha256"],
                "token_count": prov["token_count"],
                "stop_reason": prov["stop_reason"],
            })
        except KeyError as exc:
            raise R4SidecarError(
                f"sealed report record {i} is missing a generation receipt field: {exc}") from None
    # Sort by probe_id so the corpus digest is order-independent (the report's record order is not a
    # contract the comparison should depend on).
    rows.sort(key=lambda r: r["probe_id"])
    return canonical_digest(rows)


def _report_probe_ids(sealed_report: Mapping[str, Any]) -> list[str]:
    records = sealed_report.get("records") or []
    ids = [rec.get("probe_id") for rec in records if isinstance(rec, Mapping)]
    if any(type(p) is not str or not p for p in ids):
        raise R4SidecarError("sealed report has a record without a valid probe_id")
    if len(set(ids)) != len(ids):
        raise R4SidecarError("sealed report has duplicate probe_ids")
    return ids


# --------------------------------------------------------------------------- #
# F4 — recompute the summary from the rows; the caller may not just declare it.  #
# --------------------------------------------------------------------------- #
def _ranks(values: Sequence[float]) -> list[float]:
    """Fractional (average) ranks, so ties do not bias the correlation."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0          # 1-based average rank across the tie block
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_rho(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman rank correlation, recomputed from the rows (Codex #1137 F4).

    Returns 0.0 for a degenerate (zero-variance) axis rather than raising: a constant column has no
    rank correlation, and the caller's declared rho is then required to be 0.0 too.
    """
    n = len(xs)
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0.0 or syy == 0.0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def validate_comparison(per_pair: Sequence[Mapping[str, Any]], aggregate: Mapping[str, Any],
                        *, expected_pair_count: int | None = None) -> list[str]:
    """Refuse a comparison whose numbers are not numbers, out of range, incomplete, or fabricated.

    Presence + type + range + COMPLETENESS + RECOMPUTATION. The recomputation is the teeth: a
    caller cannot declare an in-range passing rho unrelated to its rows (Codex #1137 F4), because
    the declared rho and means must match the ones this function computes from the rows.
    """
    refusals: list[str] = []
    if not isinstance(per_pair, Sequence) or isinstance(per_pair, (str, bytes)):
        return ["per_pair must be a sequence of rows"]
    if not per_pair:
        return ["no per-pair comparison rows; an empty comparison decides nothing"]

    seen: set[str] = set()
    jsds: list[float] = []
    sims: list[float] = []
    for i, row in enumerate(per_pair):
        if not isinstance(row, Mapping):
            refusals.append(f"per-pair row {i} is not a mapping")
            continue
        unknown = set(row) - {"pair_id", "jsd", "embedding_similarity"}
        if unknown:
            refusals.append(f"per-pair row {i} has unknown key(s): {sorted(unknown)}")
        err = _field_error(row.get("pair_id"), _ID) if "pair_id" in row else "is missing"
        if err:
            refusals.append(f"per-pair row {i} pair_id {err}")
        elif row["pair_id"] in seen:
            refusals.append(f"per-pair row {i} duplicates pair_id {row['pair_id']!r}")
        else:
            seen.add(row["pair_id"])
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

    # F4 completeness: the comparison must cover the COMPLETE pair set, so a caller cannot cherry
    # pick agreeable pairs. Cardinality is derivable and non-overreaching; exact pair-IDENTITY
    # binding belongs to Elf's evaluator convention (§5.5) and is deferred to when that is pinned.
    if expected_pair_count is not None and len(per_pair) != expected_pair_count:
        refusals.append(
            f"comparison has {len(per_pair)} pairs but the panel's complete set is "
            f"{expected_pair_count} (C(N,2)); a partial comparison can cherry-pick agreement")

    if not isinstance(aggregate, Mapping):
        return [*refusals, "aggregate must be a mapping"]
    unknown = set(aggregate) - {"spearman_rho", "n_pairs", "mean_pairwise_jsd",
                                "mean_pairwise_embedding"}
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

    # RECOMPUTE and require the declared summary to match. This is what stops a fabricated rho.
    if len(jsds) == len(sims) == len(per_pair) and len(per_pair) >= 1:
        checks = [
            ("spearman_rho", spearman_rho(jsds, sims)),
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
    record: Mapping[str, Any]          # a deep-frozen (MappingProxyType/tuple) view


def build_r4_sidecar(
    manifest: Mapping[str, Any],
    *,
    sealed_report: Mapping[str, Any],
    per_pair: Sequence[Mapping[str, Any]],
    aggregate: Mapping[str, Any],
) -> R4SidecarRecord:
    """Validate, DERIVE-bind to the sealed report, and seal one R4 comparison record.

    No model, no comparison, no parent mutation. Every fact that CAN be derived from the sealed
    report IS (Codex #1137): the parent digests and the complete pair count come from the report,
    not from the caller. The caller still provides the comparison numbers (that is the evaluator's
    output), but the summary is recomputed from them and the record is frozen.
    """
    # F2: one inert snapshot up front; everything below reads only these, never the live inputs.
    manifest = _inert_snapshot(manifest)
    per_pair = _inert_snapshot(per_pair)
    aggregate = _inert_snapshot(aggregate)
    if not isinstance(sealed_report, Mapping):
        raise R4SidecarError("sealed_report must be a mapping")

    refusals = validate_sidecar_manifest(manifest)
    if refusals:
        raise R4SidecarError("; ".join(refusals))
    par = manifest["parent"]

    # F3: derive the parent bindings from the report, then require the manifest to match them.
    published = sealed_report.get("published_digest")
    if type(published) is not str or not _SHA256.match(published):
        raise R4SidecarError("sealed_report.published_digest is absent or not a sha256; not sealed")
    if par["b0_report_digest"] != published:
        raise R4SidecarError(
            f"parent.b0_report_digest {par['b0_report_digest'][:12]}.. != the sealed report's "
            f"published_digest {published[:12]}.. — this sidecar does not describe that run")
    derived_gen = derive_generation_corpus_digest(sealed_report)
    if par["generation_output_digest"] != derived_gen:
        raise R4SidecarError(
            f"parent.generation_output_digest {par['generation_output_digest'][:12]}.. != the "
            f"digest {derived_gen[:12]}.. derived from the report's OWN generation receipts — the "
            "comparison must consume the same generations, never a second generation")

    probe_ids = _report_probe_ids(sealed_report)
    expected_pairs = len(list(combinations(sorted(probe_ids), 2)))

    comparison_refusals = validate_comparison(per_pair, aggregate,
                                              expected_pair_count=expected_pairs)
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
    assert_strict_json(plain_record)                 # non-finite / non-JSON fails before custody
    output_digest = canonical_digest(plain_record)
    return R4SidecarRecord(
        manifest_digest=canonical_digest(dict(manifest)),
        output_digest=output_digest,
        record=_deep_freeze(plain_record),           # F1: mutation of the returned record raises
    )


def _verify_record(sidecar: R4SidecarRecord) -> dict[str, Any]:
    """Re-derive the digest from the (frozen) record and confirm it still matches output_digest.

    Belt-and-braces for F1: the deep-freeze makes in-place mutation raise, and this catches a
    hand-constructed ``R4SidecarRecord`` whose ``output_digest`` lies about its ``record``. Round-12
    discipline — verify the container's contents, do not trust the stated digest.
    """
    thawed = _thaw(sidecar.record)
    recomputed = canonical_digest(thawed)
    if recomputed != sidecar.output_digest:
        raise R4SidecarError(
            f"sidecar output_digest {sidecar.output_digest[:12]}.. does not match the record "
            f"content digest {recomputed[:12]}.. (stale or tampered)")
    return thawed


def bind_to_parent_report(sealed_report: Mapping[str, Any],
                          sidecar: R4SidecarRecord) -> dict[str, Any]:
    """The audit LINK between a sealed B0 report and a sidecar — parent read, never written (F4/ACCEPT 4)."""
    _verify_record(sidecar)                          # F1: no stale/tampered digest may link
    published = sealed_report.get("published_digest")
    if type(published) is not str or not _SHA256.match(published):
        raise R4SidecarError("parent report has no sha256 published_digest; it is not sealed")
    if sidecar.record["parent"]["b0_report_digest"] != published:
        raise R4SidecarError(
            "sidecar parent digest does not match the sealed report's published_digest")
    link = {
        "schema": SIDECAR_SCHEMA + "-link",
        "b0_published_digest": published,
        "sidecar_manifest_digest": sidecar.manifest_digest,
        "sidecar_output_digest": sidecar.output_digest,
        "evaluator_id": sidecar.record["evaluator"]["evaluator_id"],
        "evaluator_revision_sha": sidecar.record["evaluator"]["revision_sha"],
    }
    assert_strict_json(link)
    link["link_digest"] = canonical_digest({k: v for k, v in link.items() if k != "link_digest"})
    return link


# --------------------------------------------------------------------------- #
# F5 — atomic, no-replace publication with a terminal disposition.              #
# --------------------------------------------------------------------------- #
def publish_r4_sidecar(sealed_report: Mapping[str, Any], sidecar: R4SidecarRecord,
                       sidecar_path: Path) -> tuple[bytes, str]:
    """Atomically publish the sidecar artifact (record + parent link + disposition). No-replace.

    Mirrors the primary bundle's O_EXCL/no-replace discipline (a same-dir O_EXCL temp, fsync, then
    ``os.link`` to the final path, verify, unlink temp) so a crashed or racing publish cannot leave
    a partial or clobbered artifact. The parent report is READ to build the link and is never
    written. Returns the committed bytes and the artifact's published digest.
    """
    sidecar_path = Path(sidecar_path)
    if sidecar_path.exists() or sidecar_path.is_symlink():
        raise R4SidecarError(f"sidecar path already exists (no-replace): {sidecar_path}")
    parent_dir = sidecar_path.parent
    if parent_dir.is_symlink() or not parent_dir.is_dir():
        raise R4SidecarError(f"sidecar parent dir must be an existing non-symlink: {parent_dir}")

    record = _verify_record(sidecar)
    link = bind_to_parent_report(sealed_report, sidecar)
    artifact = {
        "schema": SIDECAR_SCHEMA + "-artifact",
        "disposition": "r4_comparison_recorded",
        "record": record,
        "link": link,
        "sidecar_output_digest": sidecar.output_digest,
        "sidecar_manifest_digest": sidecar.manifest_digest,
    }
    assert_strict_json(artifact)
    artifact["published_digest"] = canonical_digest(
        {k: v for k, v in artifact.items() if k != "published_digest"})
    committed = _canonical_bytes(artifact)

    tmp = Path(str(sidecar_path) + ".tmp")
    fd = os.open(str(tmp), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, committed)
        os.fsync(fd)
    finally:
        os.close(fd)
    # Verify the TEMP bytes are exactly what we meant to commit, THEN link into place no-replace.
    if tmp.read_bytes() != committed:
        tmp.unlink(missing_ok=True)
        raise R4SidecarError("staged sidecar bytes did not verify before commit")
    try:
        os.link(str(tmp), str(sidecar_path))         # no-replace: fails if the target appeared
    finally:
        tmp.unlink(missing_ok=True)
    return committed, artifact["published_digest"]


def _canonical_bytes(obj: Any) -> bytes:
    import json
    assert_strict_json(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      ensure_ascii=True).encode("utf-8")
