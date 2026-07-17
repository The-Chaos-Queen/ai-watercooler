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

# The evaluator block must pin an identity AND an immutable revision.
_EVALUATOR_KEYS = ("evaluator_id", "revision_sha")
# The runner block names what executed the comparison (out-of-process), so a reader knows the
# sidecar's own provenance and not merely the model's.
_RUNNER_KEYS = ("runner_id", "runner_digest")
# The parent block ties this sidecar to exactly one sealed B0 report and its generation receipts.
_PARENT_KEYS = ("b0_report_digest", "generation_output_digest", "sequence_length")

# A revision must be an immutable 40-hex commit/blob SHA. A branch, tag, or "main" is mutable: the
# artifact it names can change under a frozen manifest, which is the whole failure this pins against
# (same lesson as the checkpoint generation_config drift, WC #1103 — vendor-controlled data that
# moves while the manifest looks unchanged).
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MUTABLE_REFS = {"main", "master", "head", "latest", "dev", "stable"}


class R4SidecarError(ValueError):
    """A structural refusal of the comparison sidecar (bug/unsafe config), not an outcome."""


def _check_block(block: Any, name: str, keys: Sequence[str], refusals: list[str]) -> None:
    if not isinstance(block, Mapping):
        refusals.append(f"{name} block missing or not a mapping")
        return
    unknown = set(block) - set(keys)
    if unknown:
        refusals.append(f"{name} has unknown key(s): {sorted(unknown)}")
    for key in keys:
        if key not in block:
            refusals.append(f"{name}.{key} is missing")
        elif type(block[key]) is not str and not isinstance(block[key], int):
            refusals.append(f"{name}.{key} must be an exact str/int, got {type(block[key]).__name__}")
        elif isinstance(block[key], str) and _is_unset(block[key]):
            refusals.append(f"{name}.{key} is a placeholder/unset value ({block[key]!r})")


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

    _check_block(manifest.get("evaluator"), "evaluator", _EVALUATOR_KEYS, refusals)
    _check_block(manifest.get("runner"), "runner", _RUNNER_KEYS, refusals)
    _check_block(manifest.get("parent"), "parent", _PARENT_KEYS, refusals)

    # ACCEPT 1 + 5: the evaluator revision must be IMMUTABLE. A mutable ref (a branch, "main", a
    # tag) lets the evaluated artifact change while the manifest reads identical — the comparison
    # would then decide C1's fate against an artifact nobody reviewed.
    ev = manifest.get("evaluator")
    if isinstance(ev, Mapping):
        rev = ev.get("revision_sha")
        if isinstance(rev, str) and not _is_unset(rev):
            if rev.strip().lower() in _MUTABLE_REFS:
                refusals.append(
                    f"evaluator.revision_sha {rev!r} is a MUTABLE ref; the R4 comparison gates C1 "
                    "and must pin an immutable 40-hex revision"
                )
            elif not _SHA40.match(rev.strip()):
                refusals.append(
                    f"evaluator.revision_sha must be an immutable 40-hex SHA (got {rev!r})")

    par = manifest.get("parent")
    if isinstance(par, Mapping):
        for key in ("b0_report_digest", "generation_output_digest"):
            val = par.get(key)
            if isinstance(val, str) and not _is_unset(val) and not _SHA256.match(val.strip()):
                refusals.append(f"parent.{key} must be a sha256 hex digest (got {val!r})")
        n = par.get("sequence_length")
        if isinstance(n, bool) or (isinstance(n, int) and n <= 0):
            refusals.append(f"parent.sequence_length must be a positive int (got {n!r})")
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

    if not per_pair:
        raise R4SidecarError("no per-pair comparison rows; an empty comparison decides nothing")

    rows = [dict(r) for r in per_pair]
    for i, row in enumerate(rows):
        for key in ("pair_id", "jsd", "embedding_similarity"):
            if key not in row:
                raise R4SidecarError(f"per-pair row {i} is missing {key!r}")

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
