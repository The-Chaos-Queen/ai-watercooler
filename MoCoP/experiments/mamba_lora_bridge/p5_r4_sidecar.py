"""P5 R4 comparison sidecar — evaluator provenance + journal (#155 item 5, Monk WC #1128).

The mandatory R4 check (Cairn #1099, Elf's T_DIVERSITY spec §5.5) compares the JSD-based diversity
measure against an embedding-based one on the B0 null corpus, and its outcome GATES C1: if the two
disagree (Spearman rho below the preregistered instrument-agreement threshold), JSD's residual is
load-bearing and the function must be replaced before C1. That decision therefore needs custody as
strong as the thing it decides about.

WHY THIS IS A SIDECAR AND NOT A P5 COMPONENT (Monk #1128 scope lock, resolving Gidim #1114 B3):
the embedding evaluator (`all-MiniLM-L6-v2`) is a second transformer. It does NOT belong in
``COMPONENT_ROUTES``/``FORBIDDEN_ROUTE_MODULES`` — those inventories govern the P5 MONITOR PROCESS,
and the evaluator is deliberately out-of-process. It must never run inside the monitor, never import
here, and never rewrite the sealed primary B0 report. This module validates and journals the
comparison; it does not perform it.

WHAT THIS MODULE GUARANTEES (Monk #1128 ACCEPT, five items):
  1. the declared evaluator ID + IMMUTABLE revision SHA are pinned, with sidecar format/runner
     identity;
  2. the comparison binds the SAME frozen SEV panel and the SAME #155 generation-output digest and
     L-token receipts — never a second generation;
  3. per-pair and aggregate comparison output is emitted with a SHA-256;
  4. the parent B0 evidence digest and the sidecar output digest are bound WITHOUT mutating the
     O_EXCL/no-replace primary report;
  5. absent/mutable evaluator provenance, or an input/output digest mismatch, is REFUSED.

Torch-free and model-free-testable, like the rest of the P5 stack: tests inject a fake evaluator.
This module authorizes NO run, sets NO threshold, and lifts NO hold.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from p5_b0_harness import (
    _is_unset,
    assert_strict_json,
    canonical_digest,
)

# The sidecar's own format identity, so a consumer can tell WHICH contract produced a record.
SIDECAR_SCHEMA = "p5-r4-comparison-sidecar-v1"

# Closed-world required keys of the companion comparison manifest.
REQUIRED_SIDECAR_KEYS = frozenset({
    "schema",
    "evaluator",
    "runner",
    "parent",
    "panel",
})

# FIELD-SPECIFIC types/formats (Monk #1133). The first cut typed these blocks generically — "str or
# int" — and then format-checked only `if isinstance(value, str)`. That is not a check: a wrong-typed
# value DODGES its own validation. `revision_sha=123` skipped the SHA40 match entirely and published;
# `sequence_length="one-sixty"` skipped the positive-int test the same way. A format check guarded by
# a type it does not enforce is decoration. Each field now declares exactly what it must be.
_ID = "id"            # nonempty exact str, non-placeholder
_SHA40F = "sha40"     # immutable lowercase 40-hex revision
_SHA256F = "sha256"   # 64-hex digest
_POSINT = "posint"    # exact positive int (bool excluded)

# The evaluator block must pin an identity AND an immutable revision.
_EVALUATOR_SPEC = {"evaluator_id": _ID, "revision_sha": _SHA40F}
# The runner block names what executed the comparison (out-of-process), so a reader knows the
# sidecar's own provenance and not merely the model's.
_RUNNER_SPEC = {"runner_id": _ID, "runner_digest": _SHA256F}
# The parent block ties this sidecar to exactly one sealed B0 report and its generation receipts.
_PARENT_SPEC = {"b0_report_digest": _SHA256F, "generation_output_digest": _SHA256F,
                "sequence_length": _POSINT}

# A revision must be an immutable 40-hex commit/blob SHA. A branch, tag, or "main" is mutable: the
# artifact it names can change under a frozen manifest, which is the whole failure this pins against
# (same lesson as the checkpoint generation_config drift, WC #1103 — vendor-controlled data that
# moves while the manifest looks unchanged).
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MUTABLE_REFS = {"main", "master", "head", "latest", "dev", "stable"}


class R4SidecarError(ValueError):
    """A structural refusal of the comparison sidecar (bug/unsafe config), not an outcome."""


def _field_error(value: Any, kind: str) -> str | None:
    """Enforce ONE field's exact type AND format together. Returns an error string or None.

    Type and format are checked as a single obligation on purpose: separating them is what let
    Monk's repro through (#1133).
    """
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
        # bool is an int subclass; exact-type excludes True/False masquerading as a length.
        if type(value) is not int:
            return f"must be an exact positive int (got {type(value).__name__})"
        if value <= 0:
            return f"must be a positive int (got {value!r})"
        return None
    raise R4SidecarError(f"unknown field kind {kind!r}")     # programming error, not input


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


def _number_error(value: Any, name: str) -> str | None:
    """A comparison value must be a FINITE real number — not merely JSON-serializable.

    ``jsd="not-a-number"`` is valid JSON and hashes happily, which is exactly the point Monk made:
    a SHA over malformed-but-JSON values is not custody. The rho in particular has to survive the
    preregistered ``rho < 0.7`` decision; a str rho raises TypeError there, and a NaN silently
    compares False against every threshold.
    """
    if isinstance(value, bool) or type(value) not in (int, float):
        return f"{name} must be a finite number (got {type(value).__name__}: {value!r})"
    if not math.isfinite(value):
        return f"{name} must be finite (got {value!r})"
    return None


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
        refusals.append(
            f"schema must be {SIDECAR_SCHEMA!r} (got {manifest.get('schema')!r})")

    # ACCEPT 1 + 5 live inside these specs now: each field's type AND format are one obligation,
    # so nothing can dodge validation by arriving as the wrong type.
    _check_block(manifest.get("evaluator"), "evaluator", _EVALUATOR_SPEC, refusals)
    _check_block(manifest.get("runner"), "runner", _RUNNER_SPEC, refusals)
    _check_block(manifest.get("parent"), "parent", _PARENT_SPEC, refusals)

    err = _field_error(manifest.get("panel"), _ID)
    if err:
        refusals.append(f"panel {err}")
    return refusals


def validate_comparison(per_pair: Sequence[Mapping[str, Any]],
                        aggregate: Mapping[str, Any]) -> list[str]:
    """Refuse a comparison whose numbers are not numbers (Monk #1133 blocker 2).

    Presence checks are not enough: ``jsd="not-a-number"`` is valid JSON, passes strict-JSON, and
    seals into a digest. The artifact would then claim custody over values that cannot be compared
    — and the rho it carries is the input to the preregistered ``rho < 0.7`` C1 decision.
    """
    refusals: list[str] = []
    if not isinstance(per_pair, Sequence) or isinstance(per_pair, (str, bytes)):
        return ["per_pair must be a sequence of rows"]
    if not per_pair:
        return ["no per-pair comparison rows; an empty comparison decides nothing"]

    seen: set[str] = set()
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
        for key in ("jsd", "embedding_similarity"):
            if key not in row:
                refusals.append(f"per-pair row {i} is missing {key!r}")
                continue
            err = _number_error(row[key], key)
            if err:
                refusals.append(f"per-pair row {i} {err}")

    if not isinstance(aggregate, Mapping):
        return [*refusals, "aggregate must be a mapping"]
    unknown = set(aggregate) - {"spearman_rho", "n_pairs"}
    if unknown:
        refusals.append(f"aggregate has unknown key(s): {sorted(unknown)}")
    if "spearman_rho" not in aggregate:
        refusals.append("aggregate.spearman_rho is missing")
    else:
        err = _number_error(aggregate["spearman_rho"], "spearman_rho")
        if err:
            refusals.append(f"aggregate.{err}")
    if "n_pairs" not in aggregate:
        refusals.append("aggregate.n_pairs is missing")
    else:
        err = _field_error(aggregate["n_pairs"], _POSINT)
        if err:
            refusals.append(f"aggregate.n_pairs {err}")
        elif aggregate["n_pairs"] != len(per_pair):
            # A count that disagrees with the rows it counts is a receipt disagreeing with its own
            # evidence — the same class as the generation receipt that lies about its ids.
            refusals.append(
                f"aggregate.n_pairs {aggregate['n_pairs']} != {len(per_pair)} per-pair rows")
    return refusals


@dataclass(frozen=True)
class R4SidecarRecord:
    """The sealed comparison record: what was compared, against what, and by whom."""

    manifest_digest: str
    output_digest: str
    record: Mapping[str, Any]


def build_r4_sidecar(
    manifest: Mapping[str, Any],
    *,
    panel_hash: str,
    b0_report_digest: str,
    generation_output_digest: str,
    per_pair: Sequence[Mapping[str, Any]],
    aggregate: Mapping[str, Any],
) -> R4SidecarRecord:
    """Validate and seal one R4 comparison record. Performs NO comparison and loads NO model.

    The caller (an out-of-process evidence sidecar) does the embedding work and hands the results
    here. This function is the custody boundary: it refuses unless the record demonstrably describes
    the SAME panel and the SAME generation outputs the primary B0 run produced.

    ACCEPT 2 is the load-bearing check. A second generation would silently compare a different
    sample: the JSD side and the embedding side must be two measurements OF ONE CORPUS, or the
    Spearman correlation between them is measuring generation noise rather than instrument
    agreement — and that number decides whether JSD is admissible at all.
    """
    refusals = validate_sidecar_manifest(manifest)
    if refusals:
        raise R4SidecarError("; ".join(refusals))

    par = manifest["parent"]
    # ACCEPT 5: input-digest mismatch is a refusal, not a warning. Same corpus or no verdict.
    if par["b0_report_digest"] != b0_report_digest:
        raise R4SidecarError(
            f"parent.b0_report_digest {par['b0_report_digest'][:12]}.. != the supplied sealed B0 "
            f"report digest {str(b0_report_digest)[:12]}.. — this sidecar does not describe that run"
        )
    if par["generation_output_digest"] != generation_output_digest:
        raise R4SidecarError(
            f"parent.generation_output_digest {par['generation_output_digest'][:12]}.. != the "
            f"supplied generation-output digest {str(generation_output_digest)[:12]}.. — the "
            "comparison must consume the SAME generations, never a second generation"
        )
    if type(panel_hash) is not str or _is_unset(panel_hash):
        raise R4SidecarError("panel_hash must be a pinned non-placeholder str")
    if manifest["panel"] != panel_hash:
        raise R4SidecarError(
            f"manifest.panel {manifest['panel']!r} != the frozen SEV panel hash {panel_hash!r}")

    comparison_refusals = validate_comparison(per_pair, aggregate)
    if comparison_refusals:
        raise R4SidecarError("; ".join(comparison_refusals))

    rows = [dict(r) for r in per_pair]
    record: dict[str, Any] = {
        "schema": SIDECAR_SCHEMA,
        "evaluator": dict(manifest["evaluator"]),
        "runner": dict(manifest["runner"]),
        "panel": panel_hash,
        "parent": dict(par),
        "per_pair": rows,
        "aggregate": dict(aggregate),
    }
    # Strict JSON before custody, same rule as the primary bundle (#960 MED-5): a non-finite rho or
    # a coerced object must fail here, not publish.
    assert_strict_json(record)
    output_digest = canonical_digest(record)
    return R4SidecarRecord(
        manifest_digest=canonical_digest(dict(manifest)),
        output_digest=output_digest,
        record=record,
    )


def bind_to_parent_report(sealed_report: Mapping[str, Any],
                          sidecar: R4SidecarRecord) -> dict[str, Any]:
    """Return the AUDIT LINK between a sealed B0 report and a sidecar — without touching either.

    ACCEPT 4, and the reason this returns a new object rather than mutating: the primary report is
    published under O_EXCL with no-replace, and its `published_digest` covers its own contents. If
    the sidecar were written INTO it, either the digest breaks or it must be recomputed — which
    means the sealed artifact is no longer the thing that was sealed. The link therefore lives in
    the REFERRER and carries both digests, exactly the referent<-referrer direction the DQ1b owner
    ruled for base manifests (WC #1078). The parent is read, never written.
    """
    if sealed_report.get("published_digest") is None:
        raise R4SidecarError("parent report has no published_digest; it is not sealed")
    if sidecar.record["parent"]["b0_report_digest"] != sealed_report["published_digest"]:
        raise R4SidecarError(
            "sidecar parent digest does not match the sealed report's published_digest")
    link = {
        "schema": SIDECAR_SCHEMA + "-link",
        "b0_published_digest": sealed_report["published_digest"],
        "sidecar_manifest_digest": sidecar.manifest_digest,
        "sidecar_output_digest": sidecar.output_digest,
        "evaluator_id": sidecar.record["evaluator"]["evaluator_id"],
        "evaluator_revision_sha": sidecar.record["evaluator"]["revision_sha"],
    }
    assert_strict_json(link)
    link["link_digest"] = canonical_digest({k: v for k, v in link.items() if k != "link_digest"})
    return link
