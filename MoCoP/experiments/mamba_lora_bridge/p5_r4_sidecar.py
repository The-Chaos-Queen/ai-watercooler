"""P5 R4 comparison sidecar — evaluator provenance, derived binding, journal (#155 item 5).

The mandatory R4 check (Cairn #1099, Elf's T_DIVERSITY spec §5.5) compares the JSD-based diversity
measure against an embedding-based diversity measure on the B0 null corpus, and its outcome GATES
C1. That decision needs custody as strong as the thing it decides about.

WHY A SIDECAR, NOT A P5 COMPONENT (Monk #1128): the embedding evaluator is a second transformer,
deliberately OUT-OF-PROCESS. This module validates, binds, and journals a comparison; it never
performs it, never imports the model stack, and never rewrites the sealed primary B0 report.

REVIEW HISTORY: rev 1 (86c3748) typed-field CHANGES (Monk #1133); rev 2 (2844d25) added derive/
freeze/journal for Codex #1137's five P1s; rev 3 (this) closes Codex #1140's five P1s. Root cause
across all rounds: the sidecar TRUSTED input for facts it could DERIVE, CHECK, or RECOMPUTE.

CODEX #1140 rev-3 fixes:
  F1 REVERSED GATE POLARITY — JSD is a DIVERGENCE (higher = more diverse); cosine is a SIMILARITY
     (higher = more alike). Correlating them directly makes perfect agreement read as rho ≈ -1 and
     falsely trip "replace JSD". The recomputation now correlates JSD against embedding DIVERGENCE
     (1 - cos). Spearman is rank-invariant to a monotone transform, so the transform choice does not
     change the number — only the SIGN — and the diversity-vs-diversity sign is the gate-correct one
     (spec §4.4). [Elf/Monk async confirm §5.5's evaluator emits cosine SIMILARITY: WC #1142.]
  F2 PAIR IDENTITY — a complete count of arbitrary pair_ids proves nothing. Every row now names its
     two endpoint probes; both must be probes of the sealed report; the unordered endpoint set must
     equal C(report probes, 2) exactly; and a structural minimum sample is required.
  F3 UNVERIFIED PARENT — the sealed report's published_digest was trusted, not recomputed, so a
     modified report kept a stale digest. The report is now inert-snapshotted and its digest
     RECOMPUTED; the generation-corpus digest binds the raw generation text (what the evaluator
     embeds) plus token_count/stop_reason (L / short-continuation handling).
  F4 LIVE REREAD AT BIND — bind re-read the live record and never verified manifest_digest. It now
     reads ONLY the verified thawed snapshot and re-derives BOTH digests from record content.
  F5 AMBIGUOUS PUBLISH — a unique temp (no O_EXCL strand), a directory fsync, best-effort post-link
     cleanup (the artifact is already committed), and an explicit published result.

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

SIDECAR_SCHEMA = "p5-r4-comparison-sidecar-v1"

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

# Structural minimum sample for a non-degenerate Spearman (Codex #1140 F2). This is a floor against
# a trivially tiny panel, NOT a statistical power requirement — the substantive minimum-N is a
# panel/B0 design decision (Cairn/Elf), and is deferred to them.
_MIN_PROBES = 3

_ROW_KEYS = {"pair_id", "probe_a", "probe_b", "jsd", "embedding_similarity"}
_AGG_KEYS = {"spearman_rho", "n_pairs", "mean_pairwise_jsd", "mean_pairwise_embedding"}


class R4SidecarError(ValueError):
    """A structural refusal of the comparison sidecar (bug/unsafe config), not an outcome."""


# --------------------------------------------------------------------------- #
# F2/F3 — one inert JSON snapshot; nothing downstream reads the live input.     #
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
# F3 — verify the parent report, then derive from the verified snapshot.        #
# --------------------------------------------------------------------------- #
def verify_sealed_report(sealed_report: Mapping[str, Any]) -> dict[str, Any]:
    """Inert-snapshot the parent report and RECOMPUTE its published_digest (Codex #1140 F3).

    The report is caller-owned: trusting its stated ``published_digest`` lets a modified report keep
    a stale digest. Snapshot it once, recompute the digest over the report MINUS that field, and
    refuse a mismatch. Returns the verified snapshot; all derivation reads only this.
    """
    snap = _inert_snapshot(sealed_report)
    if not isinstance(snap, dict):
        raise R4SidecarError("sealed_report must be a mapping")
    stated = snap.get("published_digest")
    if type(stated) is not str or not _SHA256.match(stated):
        raise R4SidecarError("sealed_report.published_digest is absent or not a sha256; not sealed")
    recomputed = canonical_digest({k: v for k, v in snap.items() if k != "published_digest"})
    if recomputed != stated:
        raise R4SidecarError(
            f"sealed_report.published_digest {stated[:12]}.. != the digest {recomputed[:12]}.. "
            "recomputed from its own contents; the report has been modified since sealing")
    return snap


def derive_generation_corpus_digest(sealed_report: Mapping[str, Any]) -> str:
    """Canonical digest over the sealed report's per-generation receipts.

    Binds what the evaluator actually consumed: the RAW generation text (the evaluator embeds text,
    Codex #1140 F3), plus the token-id digests, token_count and stop_reason so length /
    short-continuation handling is inside the binding. Order-independent (sorted by probe_id).

    Accepts either an already-verified snapshot or a raw report; callers inside this module pass the
    verified snapshot.
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
                "raw_generation": rec["raw_generation"],
                "input_token_ids_sha256": prov["input_token_ids_sha256"],
                "generated_token_ids_sha256": prov["generated_token_ids_sha256"],
                "token_count": prov["token_count"],
                "stop_reason": prov["stop_reason"],
            })
        except KeyError as exc:
            raise R4SidecarError(
                f"sealed report record {i} is missing a generation receipt field: {exc}") from None
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
# F1/F4 — recompute the summary; the caller may not just declare it.            #
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

    Codex #1140 F1: JSD ↑ = diverse; cosine ↑ = SIMILAR. Correlating them directly makes perfect
    instrument agreement read as -1. Embedding divergence (1 - cos) is a monotone-decreasing
    transform of cosine, and Spearman is rank-invariant to it, so only the SIGN changes vs
    ``spearman_rho(jsds, sims)`` — and the diversity-vs-diversity sign is the one the gate's
    rho ≥ threshold decision needs (spec §4.4). Perfect agreement → +1.
    """
    return spearman_rho(jsds, [1.0 - s for s in sims])


def validate_comparison(per_pair: Sequence[Mapping[str, Any]], aggregate: Mapping[str, Any],
                        *, report_probe_ids: Sequence[str] | None = None) -> list[str]:
    """Refuse a comparison whose numbers are not numbers, out of range, incomplete, mislabeled, or
    fabricated. Range + endpoint identity + COMPLETENESS + RECOMPUTATION (Codex #1137 F4, #1140 F1/F2).
    """
    refusals: list[str] = []
    if not isinstance(per_pair, Sequence) or isinstance(per_pair, (str, bytes)):
        return ["per_pair must be a sequence of rows"]
    if not per_pair:
        return ["no per-pair comparison rows; an empty comparison decides nothing"]

    probe_set = set(report_probe_ids) if report_probe_ids is not None else None
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

        # F2: endpoint identity, bound to the parent panel.
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
                    f"per-pair row {i} endpoints {a!r},{b!r} are not both report probes")
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

    # F2 completeness: the endpoint set must be EXACTLY C(report probes, 2), so no cherry-picking
    # and no fabricated pairs outside the panel.
    if probe_set is not None:
        if len(probe_set) < _MIN_PROBES:
            refusals.append(
                f"report has {len(probe_set)} probes; a meaningful R4 comparison needs at least "
                f"{_MIN_PROBES} (structural floor; the power-based minimum is a panel decision)")
        expected = {frozenset(p) for p in combinations(sorted(probe_set), 2)}
        if seen_endpoints != expected and not any("endpoints" in r or "probe_" in r
                                                  for r in refusals):
            missing = expected - seen_endpoints
            extra = seen_endpoints - expected
            refusals.append(
                f"comparison endpoint set is not the complete panel pair set "
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

    # F1/F4 RECOMPUTE and require the declared summary to match. spearman_rho is on the DIVERSITY
    # convention (JSD vs embedding divergence), the gate-correct polarity.
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
    """Validate, DERIVE-bind to the verified sealed report, and seal one R4 comparison record."""
    manifest = _inert_snapshot(manifest)
    per_pair = _inert_snapshot(per_pair)
    aggregate = _inert_snapshot(aggregate)

    refusals = validate_sidecar_manifest(manifest)
    if refusals:
        raise R4SidecarError("; ".join(refusals))
    par = manifest["parent"]

    verified = verify_sealed_report(sealed_report)          # F3: snapshot + rehash
    if par["b0_report_digest"] != verified["published_digest"]:
        raise R4SidecarError(
            f"parent.b0_report_digest {par['b0_report_digest'][:12]}.. != the verified report's "
            f"published_digest {verified['published_digest'][:12]}.. — not that run")
    derived_gen = derive_generation_corpus_digest(verified)
    if par["generation_output_digest"] != derived_gen:
        raise R4SidecarError(
            f"parent.generation_output_digest {par['generation_output_digest'][:12]}.. != the "
            f"digest {derived_gen[:12]}.. derived from the report's OWN generation receipts — the "
            "comparison must consume the same generations, never a second generation")

    probe_ids = _report_probe_ids(verified)
    comparison_refusals = validate_comparison(per_pair, aggregate, report_probe_ids=probe_ids)
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


def _verify_record(sidecar: R4SidecarRecord) -> dict[str, Any]:
    """Re-derive BOTH digests from the (frozen) record content; refuse a stale/forged record.

    Codex #1137 F1 + #1140 F4: the deep-freeze stops in-place mutation, and this catches a
    hand-built R4SidecarRecord whose ``output_digest`` OR ``manifest_digest`` lies about its
    ``record``. The manifest is reconstructed from the record's own stored fields (the same fields
    that composed it), so no separate manifest copy is trusted.
    """
    thawed = _thaw(sidecar.record)
    if canonical_digest(thawed) != sidecar.output_digest:
        raise R4SidecarError(
            f"sidecar output_digest {sidecar.output_digest[:12]}.. does not match the record "
            f"content digest (stale or tampered)")
    reconstructed_manifest = {
        "schema": thawed["schema"],
        "evaluator": thawed["evaluator"],
        "runner": thawed["runner"],
        "parent": thawed["parent"],
        "panel": thawed["panel"],
    }
    if canonical_digest(reconstructed_manifest) != sidecar.manifest_digest:
        raise R4SidecarError(
            f"sidecar manifest_digest {sidecar.manifest_digest[:12]}.. does not match the manifest "
            "reconstructed from the record (stale or tampered)")
    return thawed


def bind_to_parent_report(sealed_report: Mapping[str, Any],
                          sidecar: R4SidecarRecord) -> dict[str, Any]:
    """The audit LINK between a sealed B0 report and a sidecar — parent read, never written.

    Reads ONLY the verified thawed snapshot (Codex #1140 F4): a live reread of ``sidecar.record``
    could publish different evaluator data under the verified digest.
    """
    verified_record = _verify_record(sidecar)
    verified_report = verify_sealed_report(sealed_report)
    if verified_record["parent"]["b0_report_digest"] != verified_report["published_digest"]:
        raise R4SidecarError(
            "sidecar parent digest does not match the sealed report's recomputed published_digest")
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
# F5 — atomic, no-replace publication with a terminal disposition.              #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class R4PublishResult:
    path: str
    published_digest: str
    committed_bytes: int


def publish_r4_sidecar(sealed_report: Mapping[str, Any], sidecar: R4SidecarRecord,
                       sidecar_path: Path) -> R4PublishResult:
    """Atomically publish the sidecar artifact (record + parent link + disposition). No-replace.

    Codex #1140 F5: a UNIQUE temp (no fixed-name O_EXCL strand on a retry), the temp fsync'd and
    the directory fsync'd for durability, ``os.link`` no-replace into place, then a BEST-EFFORT
    temp cleanup — once the final artifact is linked it is committed, so a cleanup fault must not
    raise over a visible result. The parent report is READ to build the link and never written.
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

    fd, tmp_name = tempfile.mkstemp(prefix=sidecar_path.name + ".", suffix=".tmp",
                                    dir=str(parent_dir))
    tmp = Path(tmp_name)
    linked = False
    try:
        os.write(fd, committed)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        if tmp.read_bytes() != committed:
            raise R4SidecarError("staged sidecar bytes did not verify before commit")
        os.link(str(tmp), str(sidecar_path))          # no-replace: fails if the target appeared
        linked = True
        _fsync_dir(parent_dir)                          # durability of the new directory entry
    finally:
        if fd != -1:
            os.close(fd)
        # Best-effort: once linked the artifact is committed; a cleanup fault must not raise.
        try:
            tmp.unlink()
        except OSError:
            if not linked:
                raise
    return R4PublishResult(path=str(sidecar_path), published_digest=artifact["published_digest"],
                           committed_bytes=len(committed))


def _fsync_dir(directory: Path) -> None:
    try:
        dfd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return                                          # some platforms cannot open a dir fd
    try:
        os.fsync(dfd)
    except OSError:
        pass                                            # directory fsync unsupported on this FS
    finally:
        os.close(dfd)
