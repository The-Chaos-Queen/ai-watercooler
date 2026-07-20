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
  a-Codex pre-board hardening: _verify_record also rejects unknown/deprecated top-level record keys
  (closed-world _RECORD_KEYS), so a hand-built carrier cannot smuggle a stale `eligibility` block
  into the verbatim-embedded, integrity_verified artifact alongside the correctly-derived one.

REV6 (Codex exact-source review of record #1183, 2026-07-18 — six findings, one custody pass):
  F1 CANONICAL B0 PARENT: verify_sealed_report now recomputes the INNER report_digest minted by
     B0EvidenceBundle.seal() over {schema_version, manifest_digest, record_count, records}, requires
     manifest_digest + execution_descriptor.panel_hash, enforces the frozen stop_reason enum
     (eos|length|error), validates receipt digests as sha256, and cross-checks
     generated_token_ids_sha256 + token_count against the record's actual generated_token_ids.
  F2 GENERATION-CORPUS AT THE BOUNDARY: the generation_output_digest match lived only in the
     builder; a hand-built record could lie about it and pass decision/publish. It, the parent
     digest, and the panel binding now live in ONE _check_parent_binding used by BOTH build and the
     parent-aware re-derivation — the divergence class itself is removed.
  F3 ONE CAPTURE: _verify_record returns an inert _VerifiedSidecar (record + both digests captured
     once). bind/decision/publication read ONLY that snapshot via internal helpers; publication
     verifies once and never recursively reopens the live public carriers, so a stateful caller
     mapping cannot swap a second value in after verification.
  F4 NON-THROWING PUBLICATION TERMINAL: after os.link commits, every readback/unlink/existence/
     durability fault is caught, best-effort removes the writable alias, and returns a truthful
     committed_integrity_failed / committed_indeterminate — never raises over a committed artifact.
  F5 EXACT RECORD SHAPE: _verify_record requires an exact mapping root and exact _RECORD_KEYS set
     (missing keys / scalar roots become typed refusals, not raw KeyError/TypeError).
  F6 FROZEN §5.5 SCHEMA: the row field is cosine_similarity (the evaluator's raw output name); rows
     are canonicalized (endpoints oriented, sorted by (probe_a, probe_b)) before validation and
     sealing, so equivalent comparisons hash identically (spec §5.5 output-digest rule).

REV7 (Codex exact-source review of record #1187 — F2 CLOSED, six residual public-boundary items):
  F1 CANONICAL PRODUCER SHAPE: verify_sealed_report enforces the EXACT producer key sets (top-level
     report / record / provenance / execution_descriptor), manifest-authority EQUALITY
     (report.manifest_digest == execution_descriptor.manifest_digest == .base_manifest_digest), and
     the producer's EOS mutual-consistency — a self-consistent report with stripped / contradictory /
     impossible producer fields is no longer a governed parent.
  F3 OWNED DEEP COPY: _verify_record captures via _inert_snapshot (rebuilds nested lists, not just
     mappings/tuples), so a post-verification mutation of a live nested list cannot reach the
     artifact; §5.5 has no caller pair_id (dropped from the input row).
  F4 ALIAS-FIRST TERMINAL: the writable hard-link alias is removed BEFORE the definitive readback,
     so a write through the alias during unlink cannot corrupt already-verified final bytes.
  F5/#7 TYPED TOTALITY: _inert_snapshot requires EXACT leaf types + str keys (a str/int subclass or
     non-str key is refused, not silently accepted); _num_in_range range-checks huge ints without an
     overflowing float conversion; the record key set is exact-equality.
  F6 CANONICAL AT VERIFY: _verify_record requires the stored rows to BE their canonical form, so a
     hand-built non-canonical record cannot mint a divergent digest for an equivalent comparison.
  #6 EMPTY/INCOMPLETE: N' = 0/1 yields the frozen INCOMPLETE decision over the canonical empty pair
     set, not a structural refusal.

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
from typing import Any, Callable, Mapping, NamedTuple, Sequence

from p5_b0_harness import (
    B0_RUN_KIND,
    B0_SCHEMA_VARIANT,
    SCHEMA_VARIANTS,
    _is_unset,
    assert_strict_json,
    canonical_digest,
    check_decoding_contract,
)
# The existing terminal-PROTOCOL verifier (Monk #1146 F2-depth). p5_b0_run is torch-free at import
# (its only torch use is a lazy __import__ inside HFGenerationBackend.__init__), so this keeps the
# sidecar's zero-torch property while giving "governed parent" real teeth. check_device_map is the
# producer's own load-route check (Codex #1197 F1 — reuse the frozen authority, do not re-mirror it).
from p5_b0_run import DESCRIPTOR_KEYS, check_device_map, verify_terminal_frames

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

# F6 (frozen §5.5, Codex #1187): the row field is `cosine_similarity` (line 173), and §5.5 (lines
# 164-178) names NO caller `pair_id`. The INPUT row a producer/evaluator emits is exactly these four;
# pair_id is DERIVED at canonicalization and only appears in the stored/canonical row.
_INPUT_ROW_KEYS = frozenset({"probe_a", "probe_b", "jsd", "cosine_similarity"})
_CANON_ROW_KEYS = frozenset({"pair_id", "probe_a", "probe_b", "jsd", "cosine_similarity"})
_AGG_KEYS = {"spearman_rho", "n_pairs", "mean_pairwise_jsd", "mean_pairwise_embedding"}
# The frozen continuation stop-reason enum (spec §4.1 line 60): eos | length | error.
_STOP_REASONS = frozenset({"eos", "length", "error"})
# The EXACT top-level key set of a sealed sidecar record. Closed-world: a hand-built record may not
# add/drop keys. eligibility is re-derived from the parent, never stored on the record.
_RECORD_KEYS = frozenset({"schema", "evaluator", "runner", "panel", "parent", "per_pair", "aggregate"})

# ---- Canonical B0 producer contract (Codex #1187 F1). These mirror the EXACT shapes
# B0EvidenceBundle.seal() (p5_b0_harness) + run_b0 (p5_b0_run) emit. A governed parent that is
# missing or has extra fields is NOT the canonical producer's report, however self-consistent its
# inner/outer digests — the digests prove byte-consistency of what is present, not membership in the
# producer schema. Kept in lockstep with those producers by review. ----
_B0_REPORT_KEYS = frozenset({
    "schema_version", "manifest_digest", "record_count", "records", "report_digest",
    "run_kind", "schema_variant", "base_manifest_id", "execution_descriptor",
    "terminal_state", "journal_digest", "published_digest"})
_B0_RECORD_KEYS = frozenset({
    "probe_id", "raw_generation", "scorer_input", "scorer_output", "provenance", "ordinal"})
# Full per-record provenance receipt (run_b0 §3.2). The digest/id/count/stop invariants are checked;
# the custody extras (prompt_sha256/attempt_id/wall_time_ms) are required present.
_B0_PROVENANCE_KEYS = frozenset({
    "prompt_sha256", "attempt_id", "input_token_ids_sha256", "generated_token_ids",
    "generated_token_ids_sha256", "token_count", "stop_reason", "eos_token_id_fired", "wall_time_ms"})
_B0_DESCRIPTOR_KEYS = frozenset({
    "panel_hash", "model", "decoding", "decoding_hash", "scorer_id", "scorer_version",
    "scorer_blob_sha256", "scorer_allowlist_digest", "scorer_review_ref", "rubric_version",
    "processor_revision", "runtime_hash", "runner_digest", "schema_variant", "base_manifest_id",
    "run_kind", "base_manifest_digest", "manifest_digest"})
# The exact fields B0EvidenceBundle.seal() digests into the inner report_digest, before publication.
_B0_SEALED_BASE_KEYS = ("schema_version", "manifest_digest", "record_count", "records")

# C1-precondition decision states (fail-closed). Only JSD_PROCEEDS is a green precondition; every
# other state denies C1 authorization.
DECISION_JSD_PROCEEDS = "jsd_proceeds"
DECISION_JSD_REPLACEMENT_REQUIRED = "jsd_replacement_required"
DECISION_INCOMPLETE = "incomplete"

# Publication terminal dispositions (used by publish_r4_sidecar / _load_governed_report /
# record_r4_comparison). Defined here so _bind_authority can freeze them; still public constants.
DISPOSITION_VERIFIED = "integrity_verified"
DISPOSITION_INTEGRITY_FAILED = "committed_integrity_failed"
DISPOSITION_INDETERMINATE = "committed_indeterminate"


# --------------------------------------------------------------------------- #
# F-AUTH (Codex #1201): the frozen sidecar authority snapshot.                 #
#                                                                              #
# rev8 read the producer-policy and decision authorities (RHO_GATE, run_kind,  #
# schema_variant, the neutralization/device validators, the policy key sets)   #
# through ASSIGNABLE module attributes, and only CALL-ENTRY-copied RHO_GATE.   #
# So a caller ``Mapping.items()`` callback (run during ``_inert_snapshot``) —  #
# or a mere pre-call ``setattr`` — could rebind ``p5_r4_sidecar.B0_RUN_KIND``, #
# ``check_decoding_contract``, or ``RHO_GATE`` and drive the verdict. A copy   #
# of a mutable module attribute is not an authority freeze.                    #
#                                                                              #
# This mirrors the producer's own accepted freeze (``p5_b0_run._bind_authority #
# `` / ``_authority()``, Codex #1009 B2 / #1013 B1): capture every verdict     #
# authority ONCE into a closure cell at import; the public names above stay    #
# documentation copies that NO verdict path reads. Reassign any of them and    #
# ``_auth()`` still returns the import-frozen snapshot for a value-global      #
# rebind. The ``_auth`` NAME itself is also a reassignable module attr, and a   #
# carrier ``.items()`` callback CAN reassign it mid-verification — so every     #
# public entry binds ``_A = _auth()`` ONCE, before any caller ``.items()`` in   #
# the whole call chain runs, and THREADS that inert ``_A`` through every        #
# verdict helper (``authority=`` param). No verdict path re-fetches ``_auth()`` #
# after caller code has run, so a mid-verification ``_auth`` swap is inert.     #
# The ONLY residual is a PRE-call reassignment of ``_auth`` (before the entry   #
# binds ``_A``) — the producer's accepted bar; free-var cells / accessor names  #
# are as immutable as the language offers in-process.                           #
#                                                                              #
# a-Codex hardening (Codex #1201 pre-board): the freeze now covers the         #
# COMPLETE policy authority set reachable from the public entry points — not   #
# just the B0-parent authorities, but the SIDECAR-side validation policy       #
# (schema/keys/specs/ranges/tolerance/format regexes/mutable-ref set/          #
# placeholder check) AND the TERMINAL/publication authority (the journal       #
# verifier + disposition labels). The rule: a name that ENCODES an accept/     #
# reject decision is frozen; a PURE PRIMITIVE (canonical_digest, _require_     #
# sha256, assert_strict_json, _canonical_bytes, _inert_snapshot, _safe_        #
# typename, _norm_num, spearman_rho, diversity_agreement_rho, _fsync_dir) is   #
# not — rebinding one is the same class as reassigning ``_auth`` itself.        #
# --------------------------------------------------------------------------- #
class _SidecarAuthority(NamedTuple):
    # ---- B0-parent producer authorities ----
    gate: float                                  # RHO_GATE — the instrument-agreement threshold
    floor: int                                   # _MIN_ELIGIBLE — the N' Spearman floor
    run_kind: str                                # B0_RUN_KIND — the only run_kind a B0 parent carries
    variant: str                                 # B0_SCHEMA_VARIANT — the B0 closed-world variant
    variants: frozenset                          # SCHEMA_VARIANTS — the closed-world union
    model_keys: frozenset                        # DESCRIPTOR_KEYS — the producer's exact 8 model keys
    decoding_check: Callable[[Mapping[str, Any]], list]   # check_decoding_contract (neutralization set)
    device_check: Callable[[Any], str]           # check_device_map (explicit single device)
    report_keys: frozenset                       # _B0_REPORT_KEYS — exact top-level report shape
    b0_record_keys: frozenset                    # _B0_RECORD_KEYS — exact producer per-record shape
    provenance_keys: frozenset                   # _B0_PROVENANCE_KEYS — exact provenance receipt shape
    descriptor_keys: frozenset                   # _B0_DESCRIPTOR_KEYS — exact execution_descriptor shape
    sealed_base_keys: tuple                      # _B0_SEALED_BASE_KEYS — the inner-digest base fields
    stop_reasons: frozenset                      # _STOP_REASONS — the frozen eos|length|error enum
    bundle_schema: str                           # B0_BUNDLE_SCHEMA — the evidence-bundle schema tag
    # ---- sidecar-side validation policy (a-Codex #1201) ----
    sha40: Any                                    # _SHA40 — immutable-40-hex format regex
    sha256: Any                                   # _SHA256 — sha256 format regex
    mutable_refs: frozenset                       # _MUTABLE_REFS — refs a C1-gating pin may NOT be
    is_unset: Callable[[Any], bool]               # _is_unset — placeholder/unset id check
    sidecar_schema: str                           # SIDECAR_SCHEMA — the sidecar manifest schema tag
    required_sidecar_keys: frozenset              # REQUIRED_SIDECAR_KEYS — exact manifest key set
    evaluator_spec: Mapping[str, str]             # _EVALUATOR_SPEC — evaluator block field→kind
    runner_spec: Mapping[str, str]                # _RUNNER_SPEC — runner block field→kind
    parent_spec: Mapping[str, str]                # _PARENT_SPEC — parent block field→kind
    jsd_range: tuple                              # _JSD_RANGE — [0,1]
    sim_range: tuple                              # _SIM_RANGE — [-1,1]
    rho_range: tuple                              # _RHO_RANGE — [-1,1]
    recompute_tol: float                          # _RECOMPUTE_TOL — aggregate recompute tolerance
    agg_keys: frozenset                           # _AGG_KEYS — exact aggregate key set
    input_row_keys: frozenset                     # _INPUT_ROW_KEYS — evaluator INPUT row shape
    canon_row_keys: frozenset                     # _CANON_ROW_KEYS — stored canonical row shape
    sidecar_record_keys: frozenset                # _RECORD_KEYS — exact sealed-sidecar record shape
    # ---- terminal / publication authority (a-Codex #1201) ----
    terminal_verifier: Callable[..., Mapping[str, Any]]   # verify_terminal_frames — journal authority
    disp_verified: str                            # DISPOSITION_VERIFIED — the ONLY green terminal
    disp_failed: str                              # DISPOSITION_INTEGRITY_FAILED
    disp_indeterminate: str                       # DISPOSITION_INDETERMINATE
    # ---- C1-precondition decision-state labels (Wachhund audit) ----
    decision_proceeds: str                        # DECISION_JSD_PROCEEDS — stamped into decision.state
    decision_replacement: str                     # DECISION_JSD_REPLACEMENT_REQUIRED
    decision_incomplete: str                      # DECISION_INCOMPLETE
    # ---- field-kind DISPATCH tags (a-Codex #1201 pass 2): swapping these mis-routes _field_error ----
    id_kind: str                                  # _ID — dispatch tag for id fields
    sha40_kind: str                               # _SHA40F — dispatch tag for 40-hex fields
    sha256_kind: str                              # _SHA256F — dispatch tag for sha256 fields
    posint_kind: str                              # _POSINT — dispatch tag for positive-int fields


def _bind_authority() -> "Callable[[], _SidecarAuthority]":
    """Freeze the COMPLETE verdict-authority set into ONE closure cell at import (F-AUTH)."""
    snap = _SidecarAuthority(
        gate=float(RHO_GATE),
        floor=int(_MIN_ELIGIBLE),
        run_kind=str(B0_RUN_KIND),
        variant=str(B0_SCHEMA_VARIANT),
        variants=frozenset(SCHEMA_VARIANTS),
        model_keys=frozenset(DESCRIPTOR_KEYS),
        decoding_check=check_decoding_contract,
        device_check=check_device_map,
        report_keys=frozenset(_B0_REPORT_KEYS),
        b0_record_keys=frozenset(_B0_RECORD_KEYS),
        provenance_keys=frozenset(_B0_PROVENANCE_KEYS),
        descriptor_keys=frozenset(_B0_DESCRIPTOR_KEYS),
        sealed_base_keys=tuple(_B0_SEALED_BASE_KEYS),
        stop_reasons=frozenset(_STOP_REASONS),
        bundle_schema=str(B0_BUNDLE_SCHEMA),
        sha40=_SHA40,
        sha256=_SHA256,
        mutable_refs=frozenset(_MUTABLE_REFS),
        is_unset=_is_unset,
        sidecar_schema=str(SIDECAR_SCHEMA),
        required_sidecar_keys=frozenset(REQUIRED_SIDECAR_KEYS),
        evaluator_spec=MappingProxyType(dict(_EVALUATOR_SPEC)),
        runner_spec=MappingProxyType(dict(_RUNNER_SPEC)),
        parent_spec=MappingProxyType(dict(_PARENT_SPEC)),
        jsd_range=tuple(_JSD_RANGE),
        sim_range=tuple(_SIM_RANGE),
        rho_range=tuple(_RHO_RANGE),
        recompute_tol=float(_RECOMPUTE_TOL),
        agg_keys=frozenset(_AGG_KEYS),
        input_row_keys=frozenset(_INPUT_ROW_KEYS),
        canon_row_keys=frozenset(_CANON_ROW_KEYS),
        sidecar_record_keys=frozenset(_RECORD_KEYS),
        terminal_verifier=verify_terminal_frames,
        disp_verified=str(DISPOSITION_VERIFIED),
        disp_failed=str(DISPOSITION_INTEGRITY_FAILED),
        disp_indeterminate=str(DISPOSITION_INDETERMINATE),
        decision_proceeds=str(DECISION_JSD_PROCEEDS),
        decision_replacement=str(DECISION_JSD_REPLACEMENT_REQUIRED),
        decision_incomplete=str(DECISION_INCOMPLETE),
        id_kind=str(_ID),
        sha40_kind=str(_SHA40F),
        sha256_kind=str(_SHA256F),
        posint_kind=str(_POSINT),
    )

    def authority() -> _SidecarAuthority:
        return snap

    return authority


_auth = _bind_authority()


class R4SidecarError(ValueError):
    """A structural refusal of the comparison sidecar (bug/unsafe config), not an outcome."""


def _safe_typename(value: Any) -> str:
    """A diagnostic type label chosen by EXACT built-in type IDENTITY (Codex #1201 F-TYPENAME).

    ``type(x).__name__`` dispatches the ``__name__`` lookup through x's METACLASS, so a hostile
    metaclass that raises on it escapes a typed refusal as a raw exception. A ``dict.get(type(x))``
    would be no safer — it HASHES the type, re-opening the same escape through a hostile ``__hash__``.
    Identity never touches foreign type metadata: ``type(x)`` reads the true type from the object
    header (not the spoofable ``__class__``) and ``is`` is a pointer compare. Anything that is not a
    plain built-in renders as a constant placeholder, never by inspecting the foreign type.
    """
    t = type(value)
    if t is str:
        return "str"
    if t is bool:
        return "bool"
    if t is int:
        return "int"
    if t is float:
        return "float"
    if t is bytes:
        return "bytes"
    if t is list:
        return "list"
    if t is tuple:
        return "tuple"
    if t is dict:
        return "dict"
    if t is set:
        return "set"
    if t is frozenset:
        return "frozenset"
    if value is None:
        return "NoneType"
    return "<non-builtin>"


# --------------------------------------------------------------------------- #
# Inert snapshot / deep-freeze (F2/F4).                                        #
# --------------------------------------------------------------------------- #
def _inert_snapshot(obj: Any, _depth: int = 0) -> Any:
    """A fully-OWNED, EXACT-typed deep copy (Codex #1183 F3 + #1187 F3/#7).

    Rebuilds mappings AND lists AND tuples into new dicts/lists (no shared mutable reference survives
    — a caller cannot mutate a nested list after this returns), and requires EXACT built-in leaf
    types: a str/int/float subclass (which could compare/hash as one value but serialize as another)
    is refused, not silently accepted. Also used as the record-capture snapshot in _verify_record.
    """
    if _depth > 64:
        raise R4SidecarError("input nesting too deep")
    if obj is None or type(obj) is bool or type(obj) is int:
        return obj
    if type(obj) is str:
        return obj
    if type(obj) is float:
        if not math.isfinite(obj):
            raise R4SidecarError(f"non-finite float in input: {obj!r}")
        return obj
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if type(k) is not str:
                # F3 (Codex #1197) + F-TYPENAME (Codex #1201): render only an INERT type label, never
                # repr(k) (a hostile __repr__ raises) and never type(k).__name__ (a hostile metaclass
                # raises on the __name__ lookup) — either would escape this refusal as a raw exception.
                raise R4SidecarError(f"mapping key must be an exact str (got {_safe_typename(k)})")
            out[k] = _inert_snapshot(v, _depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return [_inert_snapshot(v, _depth + 1) for v in obj]
    raise R4SidecarError(f"non-exact/JSON value in input: {_safe_typename(obj)}")


def _deep_freeze(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return MappingProxyType({k: _deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_deep_freeze(v) for v in obj)
    return obj


def _canonical_bytes(obj: Any) -> bytes:
    assert_strict_json(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      ensure_ascii=True).encode("utf-8")


def _safe_keys(keys: Any) -> list[str]:
    """Sorted key display that never calls repr/str on an untrusted key (Codex #1197 F3 / #1201
    F-TYPENAME): a non-str key (or one with a hostile __repr__/metaclass) renders as an INERT
    placeholder, so a diagnostic on a public self-check entry cannot itself raise, and sorting stays
    over strs (no mixed-type TypeError)."""
    return sorted(k if type(k) is str else f"<non-str {_safe_typename(k)}>" for k in keys)


# --------------------------------------------------------------------------- #
# Field + number validation.                                                   #
# --------------------------------------------------------------------------- #
def _field_error(value: Any, kind: str, *, authority: "_SidecarAuthority | None" = None) -> str | None:
    # F-AUTH (a-Codex #1201): read the accept/reject policy (placeholder check, mutable-ref set, format
    # regexes) AND the dispatch tags from the frozen snapshot. rev9-pass2 (a-Codex): dispatching against
    # the LIVE module tags was NOT fail-closed — a callback that SWAPS _ID<->_SHA40F mis-routes a
    # mutable ref down the id-branch (non-empty-str only), bypassing the mutable-ref + 40-hex checks.
    # The frozen specs carry the frozen tag VALUES and we compare them to the frozen _A.*_kind, so a
    # module-tag swap can neither re-route dispatch nor reach a decision.
    _A = authority if authority is not None else _auth()
    if kind == _A.id_kind:
        if type(value) is not str:
            return f"must be an exact str (got {_safe_typename(value)})"
        if _A.is_unset(value):
            return f"is a placeholder/unset value ({value!r})"
        return None
    if kind == _A.sha40_kind:
        if type(value) is not str:
            return f"must be an exact str 40-hex SHA (got {_safe_typename(value)})"
        if value.strip().lower() in _A.mutable_refs:
            return (f"{value!r} is a MUTABLE ref; the R4 comparison gates C1 and must pin an "
                    "immutable 40-hex revision")
        if not _A.sha40.match(value):
            return f"must be an immutable lowercase 40-hex SHA (got {value!r})"
        return None
    if kind == _A.sha256_kind:
        if type(value) is not str:
            return f"must be an exact str sha256 digest (got {_safe_typename(value)})"
        if not _A.sha256.match(value):
            return f"must be a lowercase sha256 hex digest (got {value!r})"
        return None
    if kind == _A.posint_kind:
        if type(value) is not int:
            return f"must be an exact positive int (got {_safe_typename(value)})"
        if value <= 0:
            return f"must be a positive int (got {value!r})"
        return None
    raise R4SidecarError(f"unknown field kind {kind!r}")


def _num_in_range(value: Any, lo: float, hi: float, name: str) -> str | None:
    if isinstance(value, bool) or type(value) not in (int, float):
        # F-TYPENAME (Codex #1201): inert type label only — no metaclass __name__, no repr of an
        # untrusted value; both could escape this refusal as a raw exception.
        return f"{name} must be a finite number (got {_safe_typename(value)})"
    # math.isfinite() on a huge exact int raises OverflowError (Codex #1187 #7). Only floats need
    # the finiteness test; int-vs-float range comparison is exact and never overflows.
    if type(value) is float and not math.isfinite(value):
        return f"{name} must be finite (got {value!r})"
    if not (lo <= value <= hi):
        return f"{name} must be in [{lo}, {hi}] (got {value!r})"
    return None


def _check_block(block: Any, name: str, spec: Mapping[str, str], refusals: list[str],
                 *, authority: "_SidecarAuthority | None" = None) -> None:
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
        err = _field_error(block[key], kind, authority=authority)
        if err:
            refusals.append(f"{name}.{key} {err}")


def validate_sidecar_manifest(manifest: Mapping[str, Any], *,
                              authority: "_SidecarAuthority | None" = None) -> list[str]:
    """Return refusal reasons ([] means clean). Never runs anything, never loads a model."""
    # F-AUTH (a-Codex #1201): the required key set, schema tag, and per-block field specs come from the
    # frozen snapshot THREADED from the public entry (bound before the carrier's items() callback), so
    # neither a rebind of REQUIRED_SIDECAR_KEYS / SIDECAR_SCHEMA / _*_SPEC nor an _auth-accessor rebind
    # mid-verification can loosen the manifest gate.
    _A = authority if authority is not None else _auth()
    refusals: list[str] = []
    if not isinstance(manifest, Mapping):
        return ["sidecar manifest is not a mapping"]
    unknown = set(manifest) - set(_A.required_sidecar_keys)
    if unknown:
        refusals.append(f"sidecar manifest has unknown key(s): {sorted(unknown)}")
    for key in _A.required_sidecar_keys:
        if key not in manifest:
            refusals.append(f"required key {key!r} is missing")
    if manifest.get("schema") != _A.sidecar_schema:
        refusals.append(f"schema must be {_A.sidecar_schema!r} (got {manifest.get('schema')!r})")
    _check_block(manifest.get("evaluator"), "evaluator", _A.evaluator_spec, refusals, authority=_A)
    _check_block(manifest.get("runner"), "runner", _A.runner_spec, refusals, authority=_A)
    _check_block(manifest.get("parent"), "parent", _A.parent_spec, refusals, authority=_A)
    err = _field_error(manifest.get("panel"), _A.id_kind, authority=_A)
    if err:
        refusals.append(f"panel {err}")
    return refusals


# --------------------------------------------------------------------------- #
# F1 — verify the parent is the CANONICAL B0 producer's report, then derive.    #
# --------------------------------------------------------------------------- #
def _require_sha256(value: Any, name: str, *, authority: "_SidecarAuthority | None" = None) -> None:
    _A = authority if authority is not None else _auth()
    if type(value) is not str or not _A.sha256.match(value):   # F-AUTH: frozen format regex
        raise R4SidecarError(f"{name} must be a lowercase sha256 hex digest (got {value!r})")


def verify_sealed_report(sealed_report: Mapping[str, Any], *,
                         authority: "_SidecarAuthority | None" = None) -> dict[str, Any]:
    """Validate a CANONICAL B0 evidence report (Monk #1146 F2-depth; Codex #1183/#1187 F1).

    A governed parent is not merely a self-hashed Mapping, and not merely a report with the fields
    this sidecar happens to read: it is the EXACT report ``B0EvidenceBundle.seal()`` mints and
    ``run_b0`` publishes. The inner and outer digests prove byte-consistency of what is PRESENT, not
    membership in the producer schema, so a self-consistent report with stripped / contradictory /
    impossible producer fields must still be refused. Requires: exact top-level key set; the bundle
    schema; the INNER report_digest recomputed over the sealed base fields; the OUTER published_digest
    over the rest; manifest-authority EQUALITY (report.manifest_digest == execution_descriptor
    .manifest_digest == .base_manifest_digest, DQ1b §290-292); the exact execution_descriptor key
    set + panel_hash; and per record the exact producer record + provenance key sets, sequential
    ordinal, the frozen ``eos|length|error`` stop enum, sha256 receipt digests,
    ``generated_token_ids_sha256`` + ``token_count`` cross-checked against the record's OWN
    ``generated_token_ids``, and the producer's EOS mutual-consistency rule. The seam adds journal +
    terminal-authority verification on top of this.
    """
    # F-AUTH (Codex #1201 + a-Codex): use the frozen authority THREADED from the public entry when
    # present (bound before ANY caller items() in the whole call chain ran), else bind it here as the
    # VERY FIRST statement, before _inert_snapshot runs this report's Mapping.items(). Every
    # producer-policy decision below — and the digest-format checks it delegates — reads this inert
    # snapshot, never a reassignable module global and never a re-fetch of _auth() after caller code
    # ran, so no mid-verify value-rebind OR _auth-accessor-rebind can change what this call accepts.
    _A = authority if authority is not None else _auth()
    snap = _inert_snapshot(sealed_report)                   # owned, exact-typed (rejects subclasses)
    if not isinstance(snap, dict):
        raise R4SidecarError("sealed_report must be a mapping")
    if set(snap) != _A.report_keys:
        missing = sorted(_A.report_keys - set(snap))
        extra = sorted(set(snap) - _A.report_keys)
        raise R4SidecarError(
            f"sealed_report is not the canonical B0 shape (missing {missing}, unexpected {extra})")
    if snap["schema_version"] != _A.bundle_schema:
        raise R4SidecarError(
            f"sealed_report.schema_version must be {_A.bundle_schema!r} (got {snap['schema_version']!r})")

    mdig = snap["manifest_digest"]
    _require_sha256(mdig, "sealed_report.manifest_digest", authority=_A)

    records = snap["records"]
    if not isinstance(records, list) or not records:
        raise R4SidecarError("sealed_report has no records")
    rc = snap["record_count"]
    if type(rc) is not int or rc != len(records):
        # F1 (Codex #1197): EXACT int. `4.0 != 4` is False in Python, so a float record_count would
        # otherwise pass the equality alone; the producer emits an int.
        raise R4SidecarError(
            f"sealed_report.record_count must be the exact int len(records) {len(records)} (got {rc!r})")

    # INNER digest: exactly what seal() sealed, before run_b0 appended publication fields.
    inner_stated = snap["report_digest"]
    _require_sha256(inner_stated, "sealed_report.report_digest", authority=_A)
    inner_recomputed = canonical_digest({k: snap[k] for k in _A.sealed_base_keys})
    if inner_recomputed != inner_stated:
        raise R4SidecarError(
            f"sealed_report.report_digest {inner_stated[:12]}.. != the inner seal digest "
            f"{inner_recomputed[:12]}.. recomputed over its base fields; not the sealed report")

    # OUTER digest: the runner's publication digest over everything except itself.
    outer_stated = snap["published_digest"]
    _require_sha256(outer_stated, "sealed_report.published_digest", authority=_A)
    outer_recomputed = canonical_digest({k: v for k, v in snap.items() if k != "published_digest"})
    if outer_recomputed != outer_stated:
        raise R4SidecarError(
            f"sealed_report.published_digest {outer_stated[:12]}.. != the digest "
            f"{outer_recomputed[:12]}.. recomputed from its own contents; modified since sealing")

    # Execution descriptor: exact producer shape + panel_hash + manifest-authority equality (F1).
    ed = snap["execution_descriptor"]
    if not isinstance(ed, Mapping) or set(ed) != _A.descriptor_keys:
        raise R4SidecarError("execution_descriptor is not the canonical producer shape")
    # F1 (Codex #1197): panel_hash is a sha256 (canonical_panel_hash emits one), not any non-empty str.
    _require_sha256(ed["panel_hash"], "execution_descriptor.panel_hash", authority=_A)
    _require_sha256(ed["manifest_digest"], "execution_descriptor.manifest_digest", authority=_A)
    _require_sha256(ed["base_manifest_digest"], "execution_descriptor.base_manifest_digest", authority=_A)
    if not (mdig == ed["manifest_digest"] == ed["base_manifest_digest"]):
        raise R4SidecarError(
            "manifest authority disagreement: report.manifest_digest, "
            "execution_descriptor.manifest_digest and .base_manifest_digest must be equal "
            "(DQ1b): one base, one authority")

    # Duplicated authority fields must AGREE between the report and the descriptor — the producer
    # emits them from one source (Codex #1187 a-Codex): a report whose top-level run_kind /
    # schema_variant / base_manifest_id contradicts its descriptor is not one run_b0 could emit.
    for key in ("run_kind", "schema_variant", "base_manifest_id"):
        if type(snap[key]) is not str or not snap[key]:
            raise R4SidecarError(f"sealed_report.{key} must be a non-empty str")
        if snap[key] != ed[key]:
            raise R4SidecarError(
                f"sealed_report.{key} {snap[key]!r} != execution_descriptor.{key} {ed[key]!r}")
    # F1 (Codex #1197): pin the producer POLICY VALUES, not just the top-level==descriptor equality
    # above. A self-consistent report whose run_kind is 'c1_intervention', or whose schema_variant is
    # the c1 closed-world value, is not a B0 baseline run_b0 could publish — rev7 checked the SHAPE of
    # these fields but never that their values are the ones a B0 parent must carry.
    if snap["run_kind"] != _A.run_kind:
        raise R4SidecarError(
            f"sealed_report.run_kind must be {_A.run_kind!r} for a B0 parent (got {snap['run_kind']!r})")
    if snap["schema_variant"] not in _A.variants or snap["schema_variant"] != _A.variant:
        raise R4SidecarError(
            f"sealed_report.schema_variant must be {_A.variant!r} for a B0 parent "
            f"(got {snap['schema_variant']!r})")
    if snap["terminal_state"] != "committed":
        raise R4SidecarError(
            f"sealed_report.terminal_state must be 'committed' (got {snap['terminal_state']!r})")
    _require_sha256(snap["journal_digest"], "sealed_report.journal_digest", authority=_A)
    # Descriptor authority values must be PINNED, not null/incomplete (Codex #1187 a-Codex): a
    # runner_digest=None or an incomplete model is not a report the runner could publish.
    _require_sha256(ed["runner_digest"], "execution_descriptor.runner_digest", authority=_A)
    _require_sha256(ed["decoding_hash"], "execution_descriptor.decoding_hash", authority=_A)
    if not isinstance(ed["decoding"], Mapping) or not ed["decoding"]:
        raise R4SidecarError("execution_descriptor.decoding must be a non-empty mapping")
    # F1 (Codex #1197): the decoding_hash must be the digest OF this decoding (cross-bind, not merely
    # some sha256), and the decoding must satisfy the producer's own neutralization contract — a
    # report whose decoding samples (do_sample/temperature/top_p) is not a B0 baseline, however
    # self-hashed. Reuse the frozen check_decoding_contract rather than re-mirroring the tiers.
    if ed["decoding_hash"] != canonical_digest(ed["decoding"]):
        raise R4SidecarError(
            "execution_descriptor.decoding_hash is not the canonical digest of its own decoding block")
    decoding_refusals = _A.decoding_check({"decoding": dict(ed["decoding"])})
    if decoding_refusals:
        raise R4SidecarError(
            "execution_descriptor.decoding is not the pinned B0 neutralization set: "
            + "; ".join(decoding_refusals))
    model = ed["model"]
    # F-MODEL (Codex #1201): the producer requires the EXACT frozen model-descriptor key set
    # (_descriptor_schema_error, p5_b0_run:1485-1503 — extra fields would publish UNBOUND under
    # integrity_verified). rev8 used a SUBSET test, so a re-sealed report with an extra unbound model
    # field was accepted though run_b0 would refuse it. Require exact key-set equality; the per-key
    # value checks below cover exactly those eight keys.
    if not isinstance(model, Mapping) or set(model) != _A.model_keys:
        raise R4SidecarError(
            "execution_descriptor.model is not the exact producer model descriptor "
            f"(must have exactly {sorted(_A.model_keys)})")
    # F1 (Codex #1197): the model descriptor VALUES must be pinned, not merely present. A model with
    # id=None passes the key-membership check but is not a load the runner could have performed; the
    # device_map must be an explicit single device — reuse the producer's own check_device_map.
    for mkey in ("id", "revision", "dtype", "backend", "device", "attention"):
        if type(model[mkey]) is not str or not model[mkey]:
            raise R4SidecarError(f"execution_descriptor.model.{mkey} must be a non-empty str")
    if type(model["use_cache"]) is not bool:
        raise R4SidecarError("execution_descriptor.model.use_cache must be a bool")
    try:
        _A.device_check(model["device_map"])
    except Exception as exc:  # noqa: BLE001 — any check_device_map failure is a refusal of this parent
        raise R4SidecarError(
            f"execution_descriptor.model.device_map is not an explicit single device: {exc}") from exc

    seen: set[str] = set()
    for i, rec in enumerate(records):
        if not isinstance(rec, Mapping) or set(rec) != _A.b0_record_keys:
            raise R4SidecarError(f"record {i} is not the canonical producer record shape")
        pid = rec["probe_id"]
        if type(pid) is not str or not pid:
            raise R4SidecarError(f"record {i} has no valid probe_id")
        if pid in seen:
            raise R4SidecarError(f"duplicate probe_id {pid!r} in report")
        seen.add(pid)
        if type(rec["raw_generation"]) is not str:
            raise R4SidecarError(f"record {i} raw_generation must be a str")
        if type(rec["ordinal"]) is not int or isinstance(rec["ordinal"], bool) or rec["ordinal"] != i:
            raise R4SidecarError(f"record {i} ordinal must be the sequential int {i}")
        prov = rec["provenance"]
        if not isinstance(prov, Mapping) or set(prov) != _A.provenance_keys:
            raise R4SidecarError(f"record {i} provenance is not the canonical producer shape")
        _require_sha256(prov["prompt_sha256"], f"record {i} provenance.prompt_sha256", authority=_A)
        _require_sha256(prov["input_token_ids_sha256"],
                        f"record {i} provenance.input_token_ids_sha256", authority=_A)
        _require_sha256(prov["generated_token_ids_sha256"],
                        f"record {i} provenance.generated_token_ids_sha256", authority=_A)
        if type(prov["attempt_id"]) is not str or not prov["attempt_id"]:
            raise R4SidecarError(f"record {i} provenance.attempt_id must be a non-empty str")
        if type(prov["wall_time_ms"]) not in (int, float) or isinstance(prov["wall_time_ms"], bool):
            raise R4SidecarError(f"record {i} provenance.wall_time_ms must be a number")
        stop = prov["stop_reason"]
        if type(stop) is not str or stop not in _A.stop_reasons:  # exact str before enum membership
            raise R4SidecarError(
                f"record {i} stop_reason {stop!r} is not an exact str in {sorted(_A.stop_reasons)}")
        gen_ids = prov["generated_token_ids"]
        if not isinstance(gen_ids, list) or any(
                type(t) is not int or isinstance(t, bool) for t in gen_ids):
            raise R4SidecarError(f"record {i} generated_token_ids must be a list of ints")
        if canonical_digest(gen_ids) != prov["generated_token_ids_sha256"]:
            raise R4SidecarError(
                f"record {i} generated_token_ids_sha256 does not match its own generated_token_ids")
        tc = prov["token_count"]
        if type(tc) is not int or isinstance(tc, bool) or tc < 0:
            raise R4SidecarError(f"record {i} token_count must be a non-negative int")
        if tc != len(gen_ids):
            raise R4SidecarError(
                f"record {i} token_count {tc} != len(generated_token_ids) {len(gen_ids)}")
        # Producer EOS mutual-consistency (p5_b0_run:459-466): eos names WHICH id fired and it is the
        # final generated id; length/error must not name a fired eos id.
        eos_fired = prov["eos_token_id_fired"]
        if stop == "eos":
            if type(eos_fired) is not int or isinstance(eos_fired, bool):
                raise R4SidecarError(f"record {i} stop_reason 'eos' requires an int eos_token_id_fired")
            if not gen_ids or gen_ids[-1] != eos_fired:
                raise R4SidecarError(
                    f"record {i} eos_token_id_fired does not match the final generated token id")
        elif eos_fired is not None:
            raise R4SidecarError(
                f"record {i} stop_reason {stop!r} must not name a fired eos id")
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


def _validate_aggregate(aggregate: Any, per_pair: Sequence[Any],
                        jsds: list[float], sims: list[float],
                        *, authority: "_SidecarAuthority | None" = None) -> list[str]:
    """Range-check the aggregate, bind n_pairs to the row count, and recompute from the rows.

    n_pairs is a NON-NEGATIVE int (0 is the canonical value for a below-floor empty comparison);
    the recompute runs only when there are rows to describe.
    """
    _A = authority if authority is not None else _auth()   # F-AUTH: frozen key set / ranges / tol
    refusals: list[str] = []
    if not isinstance(aggregate, Mapping):
        return ["aggregate must be a mapping"]
    if not per_pair:
        # The ONLY canonical aggregate for an empty comparison (Codex #1187 a-Codex): pinned so an
        # empty comparison has ONE deterministic digest, not an arbitrary caller rho/means.
        if not (set(aggregate) == _A.agg_keys
                and type(aggregate.get("n_pairs")) is int and aggregate["n_pairs"] == 0
                and all(type(aggregate.get(k)) is float and aggregate[k] == 0.0
                        for k in ("spearman_rho", "mean_pairwise_jsd", "mean_pairwise_embedding"))):
            return ["an empty comparison requires the canonical zero aggregate "
                    "{spearman_rho: 0.0, mean_pairwise_jsd: 0.0, mean_pairwise_embedding: 0.0, "
                    "n_pairs: 0}"]
        return []
    unknown = set(aggregate) - _A.agg_keys
    if unknown:
        refusals.append(f"aggregate has unknown key(s): {_safe_keys(unknown)}")
    range_ok: set[str] = set()
    for key, rng in (("spearman_rho", _A.rho_range), ("mean_pairwise_jsd", _A.jsd_range),
                     ("mean_pairwise_embedding", _A.sim_range)):
        if key not in aggregate:
            refusals.append(f"aggregate.{key} is missing")
        else:
            e = _num_in_range(aggregate[key], *rng, key)
            if e:
                refusals.append(f"aggregate.{e}")
            else:
                range_ok.add(key)          # only range-passing (|v| <= 1) keys are float-recompute safe
    n = aggregate.get("n_pairs")
    if "n_pairs" not in aggregate:
        refusals.append("aggregate.n_pairs is missing")
    elif type(n) is not int or isinstance(n, bool) or n < 0:
        refusals.append(f"aggregate.n_pairs must be a non-negative int (got {n!r})")
    elif n != len(per_pair):
        refusals.append(f"aggregate.n_pairs {n} != {len(per_pair)} per-pair rows")

    if jsds and len(jsds) == len(sims) == len(per_pair):
        checks = [
            ("spearman_rho", diversity_agreement_rho(jsds, sims)),
            ("mean_pairwise_jsd", sum(jsds) / len(jsds)),
            ("mean_pairwise_embedding", sum(sims) / len(sims)),
        ]
        for key, computed in checks:
            # F3 (Codex #1197): recompute ONLY keys that passed the range check. A declared value that
            # failed range (already refused) must not enter float() — a huge declared int (e.g.
            # 10**400) overflows float() and raises out of this validator. |v| <= 1 makes float safe.
            if key not in range_ok:
                continue
            if abs(float(aggregate[key]) - computed) > _A.recompute_tol:
                refusals.append(
                    f"aggregate.{key} {aggregate[key]} does not match the value {computed:.12g} "
                    "recomputed from the rows; the summary must describe the rows")
    return refusals


def validate_comparison(per_pair: Sequence[Mapping[str, Any]], aggregate: Mapping[str, Any],
                        *, eligible_probe_ids: Sequence[str] | None = None,
                        row_keys: frozenset[str] | None = None,
                        authority: "_SidecarAuthority | None" = None) -> list[str]:
    """Row shape + endpoint identity + COMPLETENESS over ELIGIBLE probes + RECOMPUTATION.

    Completeness is over the ELIGIBLE set (Monk #1146 F1), never all report probes. §5.5 (Codex
    #1187) names NO caller pair_id, so the default INPUT row shape is exactly
    {probe_a, probe_b, jsd, cosine_similarity}; the stored canonical row (pass ``row_keys=
    _A.canon_row_keys``) also carries the DERIVED pair_id. An EMPTY comparison is valid ONLY when the
    eligible set yields zero pairs (N' < 2) — the frozen INCOMPLETE case — never otherwise. The
    N' >= 4 floor is a decision outcome, not enforced here.

    F-AUTH (a-Codex #1201): the row shape and the jsd/similarity ranges are read from the frozen
    snapshot (default row shape too — via ``None`` sentinel, not a reassignable default arg), so a
    caller callback cannot loosen them mid-validation.
    """
    _A = authority if authority is not None else _auth()
    row_keys = _A.input_row_keys if row_keys is None else row_keys
    if not isinstance(per_pair, Sequence) or isinstance(per_pair, (str, bytes)):
        return ["per_pair must be a sequence of rows"]
    probe_set = set(eligible_probe_ids) if eligible_probe_ids is not None else None
    expected = ({frozenset(p) for p in combinations(sorted(probe_set), 2)}
                if probe_set is not None else None)

    if not per_pair:
        # An empty comparison is the canonical form iff the eligible set yields zero pairs (N' < 2).
        # Without a parent (expected is None) emptiness is allowed here; the parent-aware boundary
        # enforces completeness. A non-empty expected set with no rows is a refusal.
        refusals = ([f"empty comparison but the eligible set requires {len(expected)} pair(s)"]
                    if expected else [])
        return refusals + _validate_aggregate(aggregate, per_pair, [], [], authority=_A)

    refusals = []
    seen_endpoints: set[frozenset] = set()
    jsds: list[float] = []
    sims: list[float] = []
    for i, row in enumerate(per_pair):
        if not isinstance(row, Mapping):
            refusals.append(f"per-pair row {i} is not a mapping")
            continue
        if set(row) != set(row_keys):                       # exact row shape; §5.5 has no caller pair_id
            # F3 (Codex #1197): render keys safely — never repr/str an untrusted key (a hostile
            # __repr__ would raise) on this PUBLIC self-check entry; _safe_keys also keeps the sort
            # over strs so a non-str key cannot raise a mixed-type TypeError either.
            refusals.append(
                f"per-pair row {i} key set is not {sorted(row_keys)} (got {_safe_keys(row)})")
            continue
        a, b = row["probe_a"], row["probe_b"]
        ae = _field_error(a, _A.id_kind, authority=_A)
        be = _field_error(b, _A.id_kind, authority=_A)
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

        je = _num_in_range(row["jsd"], *_A.jsd_range, "jsd")
        if je:
            refusals.append(f"per-pair row {i} {je}")
        else:
            jsds.append(row["jsd"])
        se = _num_in_range(row["cosine_similarity"], *_A.sim_range, "cosine_similarity")
        if se:
            refusals.append(f"per-pair row {i} {se}")
        else:
            sims.append(row["cosine_similarity"])

    if expected is not None and seen_endpoints != expected and not any(
            "endpoints" in r or "probe_" in r or "key set" in r for r in refusals):
        missing = expected - seen_endpoints
        extra = seen_endpoints - expected
        refusals.append(
            f"comparison endpoint set is not the complete ELIGIBLE pair set "
            f"(missing {len(missing)}, extra {len(extra)} of {len(expected)})")

    return refusals + _validate_aggregate(aggregate, per_pair, jsds, sims, authority=_A)


@dataclass(frozen=True)
class R4SidecarRecord:
    """The sealed comparison record: deep-frozen so its digest cannot go stale (Codex #1137 F1)."""

    manifest_digest: str
    output_digest: str
    record: Mapping[str, Any]


def _check_parent_binding(verified_report: Mapping[str, Any], *, b0_report_digest: str,
                          generation_output_digest: str, panel: str) -> None:
    """The ONE parent-binding custody check, used by build AND the parent-aware boundary (Codex #1183
    F1/F2). A check that lives only in the builder is the exact class Isegrim (eligibility) and Codex
    (generation digest) both exploited: a hand-built record reaches decision/publish without it.

    Bind three facts of the record's ``parent``/``panel`` to the VERIFIED report: (1) the outer
    published_digest is that run; (2) the generation_output_digest equals the corpus digest derived
    from the report's OWN receipts (frozen same-input rule, spec line 169 — never a second run);
    (3) the sidecar panel equals the parent execution_descriptor.panel_hash (same SEV battery).
    """
    if b0_report_digest != verified_report["published_digest"]:
        raise R4SidecarError(
            f"parent.b0_report_digest {b0_report_digest[:12]}.. != the verified report's "
            f"published_digest {verified_report['published_digest'][:12]}.. — not that run")
    derived_gen = derive_generation_corpus_digest(verified_report)
    if generation_output_digest != derived_gen:
        raise R4SidecarError(
            f"parent.generation_output_digest {generation_output_digest[:12]}.. != the digest "
            f"{derived_gen[:12]}.. derived from the report's OWN receipts — never a second generation")
    parent_panel = verified_report["execution_descriptor"]["panel_hash"]
    if panel != parent_panel:
        raise R4SidecarError(
            f"sidecar panel {panel!r} != the parent execution_descriptor.panel_hash "
            f"{parent_panel!r} — the comparison must bind to the same SEV battery")


def _norm_num(value: Any) -> float:
    """Canonical float for a range-VALIDATED metric (|value| <= 1): collapse -0.0 to 0.0 and any int
    to float, so equivalent comparisons mint ONE digest (Codex #1197 F6: "0.0" and "-0.0" are
    distinct canonical-JSON tokens, and int/float spellings differ too). float() is safe only because
    the caller has already range-checked the value; a huge int would otherwise overflow."""
    f = float(value)
    return 0.0 if f == 0.0 else f


def _canonicalize_comparison(per_pair: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Canonicalize comparison rows for a deterministic output digest (Codex #1183 F6 / spec §5.5
    line 178: rows sorted by (probe_a, probe_b)). Orient each row's endpoints (probe_a <= probe_b)
    and derive pair_id from the oriented endpoints, then sort rows by (probe_a, probe_b). JSD and
    cosine are symmetric in the unordered pair, so orientation does not change them. The jsd/cosine
    metrics are normalized to canonical float (Codex #1197 F6), so 0.0 vs -0.0 and int vs float
    cannot mint different digests for the same comparison. Any row order, endpoint orientation, or
    numeric spelling of the same comparison thus hashes identically. Runs AFTER validation, so every
    row is well-formed and every metric is in range (float-safe).
    """
    canon: list[dict[str, Any]] = []
    for row in per_pair:
        a, b = row["probe_a"], row["probe_b"]
        if a > b:
            a, b = b, a
        # Unambiguous pair_id (a-Codex): a single "|" delimiter collides when a probe id contains "|"
        # (("a","b|c") and ("a|b","c") both -> "a|b|c"), which would then fail _verify_record's
        # duplicate-pair_id check on a comparison that built fine. JSON of the oriented endpoints is
        # injective and still order/orientation-canonical.
        canon.append({"pair_id": json.dumps([a, b], separators=(",", ":")),
                      "probe_a": a, "probe_b": b,
                      "jsd": _norm_num(row["jsd"]),
                      "cosine_similarity": _norm_num(row["cosine_similarity"])})
    canon.sort(key=lambda r: (r["probe_a"], r["probe_b"]))
    return canon


def _canonicalize_aggregate(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize the stored aggregate's float metrics to canonical form (Codex #1197 F6); n_pairs
    stays an int. Runs only over an aggregate _validate_aggregate has already accepted, so every
    metric present is range-checked (float-safe) and the keys are exactly _AGG_KEYS. Without this a
    hand-built record carrying a -0.0 (or int-spelled) metric would pass verify and mint a divergent
    public digest for an equivalent comparison — the same equivalence leak the rows normalization
    closes."""
    out = dict(aggregate)
    for key in ("spearman_rho", "mean_pairwise_jsd", "mean_pairwise_embedding"):
        if key in out:
            out[key] = _norm_num(out[key])
    return out


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
    # F-AUTH (a-Codex #1201): bind the GENUINE frozen authority ONCE here, before _inert_snapshot fires
    # the caller manifest's items() callback, and thread it through every validator — none re-fetches
    # _auth() after caller code has run. build takes no caller authority (self-safe; a-Codex pass 2).
    _A = _auth()
    manifest = _inert_snapshot(manifest)
    per_pair = _inert_snapshot(per_pair)
    aggregate = _inert_snapshot(aggregate)

    refusals = validate_sidecar_manifest(manifest, authority=_A)
    if refusals:
        raise R4SidecarError("; ".join(refusals))
    par = manifest["parent"]

    verified = verify_sealed_report(sealed_report, authority=_A)
    _check_parent_binding(verified, b0_report_digest=par["b0_report_digest"],
                          generation_output_digest=par["generation_output_digest"],
                          panel=manifest["panel"])

    elig = partition_eligibility(verified, par["sequence_length"])
    comparison_refusals = validate_comparison(per_pair, aggregate,
                                              eligible_probe_ids=elig.eligible, authority=_A)
    if comparison_refusals:
        raise R4SidecarError("; ".join(comparison_refusals))
    canonical_per_pair = _canonicalize_comparison(per_pair)     # F6: deterministic order/orientation

    plain_record: dict[str, Any] = {
        "schema": _A.sidecar_schema,                             # F-AUTH: frozen label (fail-closed at verify)
        "evaluator": dict(manifest["evaluator"]),
        "runner": dict(manifest["runner"]),
        "panel": manifest["panel"],
        "parent": dict(par),
        "per_pair": canonical_per_pair,
        "aggregate": _canonicalize_aggregate(aggregate),    # F6: canonical numeric form, one digest
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
@dataclass(frozen=True)
class _VerifiedSidecar:
    """An inert, ONCE-captured view of a verified R4SidecarRecord (Codex #1183 F3).

    The public carrier's fields may be caller-controlled mappings whose ``items()`` runs during
    verification, and ``frozen=True`` is no defence against ``object.__setattr__``. So every
    downstream output reads ONLY this snapshot — the thawed record and both digests captured in a
    single pass — never the live carrier again.
    """
    record: dict[str, Any]
    output_digest: str
    manifest_digest: str


def _verify_record(sidecar: Any, *, authority: "_SidecarAuthority | None" = None) -> _VerifiedSidecar:
    """Exact-type the carrier, capture its content + digests ONCE, and RE-VALIDATE the semantics.

    Codex #1140 F4 + #1144 F3/F4: the deep-freeze stops in-place mutation, but a public boundary must
    not trust a hand-built or subclassed carrier. Exact-type ``R4SidecarRecord`` (a subclass could
    override ``output_digest`` to return different values on successive reads), read the frozen
    content ONCE, confirm both digests match, and re-run the manifest + comparison validation so a
    record whose evaluator revision is "main" cannot bind merely because its digest is self
    consistent. Returns an inert ``_VerifiedSidecar`` (Codex #1183 F3): callers must read that, never
    the live carrier, so a stateful caller mapping cannot swap a second value in after verification.

    rev5 (Isegrim probe): this guard has NO parent report, so it CANNOT know the eligible set and
    must not check comparison completeness against any declared/stored eligibility — doing so is how
    rev4 leaked. It validates the comparison's shape/ranges/endpoint-identity/recompute only;
    completeness over the DERIVED eligible set is enforced at the parent-aware boundaries.
    """
    if type(sidecar) is not R4SidecarRecord:
        raise R4SidecarError(f"not an exact R4SidecarRecord (got {_safe_typename(sidecar)})")
    output_digest = sidecar.output_digest          # read the digest attributes exactly once
    manifest_digest = sidecar.manifest_digest
    if type(output_digest) is not str or type(manifest_digest) is not str:
        raise R4SidecarError("record digests must be exact strs")
    # F-AUTH (a-Codex #1201): use the authority THREADED from the public entry (bound before ANY caller
    # items() ran), else bind it here BEFORE _inert_snapshot fires THIS carrier's items() callback. The
    # exact-record-shape and canonical-row-shape decisions below — and the manifest/comparison
    # re-validation they delegate to — read this frozen snapshot, never a rebound value-global and
    # never a re-fetch of _auth() after the callback (which could reassign _auth itself).
    _A = authority if authority is not None else _auth()
    # F3 (Codex #1187): capture a fully-OWNED, EXACT-typed deep copy in one pass — _inert_snapshot
    # rebuilds nested lists too (no live list survives) and refuses str/int subclasses (which could
    # compare as one value but serialize as another) and non-str keys, so a stateful/subclass carrier
    # cannot mutate or spoof the captured record after this returns.
    record = _inert_snapshot(sidecar.record)
    # F5 (Codex #1183): exact root type + exact key set BEFORE indexing, so a missing key / scalar
    # root / extra key is a typed refusal, not a raw KeyError/TypeError. (_inert_snapshot already made
    # every key an exact str, so this set-difference cannot raise on heterogeneous keys.)
    if not isinstance(record, dict):
        raise R4SidecarError("record root is not a mapping")
    if set(record) != _A.sidecar_record_keys:
        missing = sorted(_A.sidecar_record_keys - set(record))
        extra = sorted(set(record) - _A.sidecar_record_keys)
        raise R4SidecarError(
            f"record key set is not exact (missing {missing}, unexpected {extra}); eligibility is "
            "re-derived from the parent, never stored on the record")
    if canonical_digest(record) != output_digest:
        raise R4SidecarError("record output_digest does not match its content (stale or tampered)")
    reconstructed_manifest = {
        "schema": record["schema"], "evaluator": record["evaluator"],
        "runner": record["runner"], "parent": record["parent"], "panel": record["panel"],
    }
    if canonical_digest(reconstructed_manifest) != manifest_digest:
        raise R4SidecarError("record manifest_digest does not match the reconstructed manifest")
    m_refusals = validate_sidecar_manifest(reconstructed_manifest, authority=_A)
    if m_refusals:
        raise R4SidecarError("record manifest fails re-validation: " + "; ".join(m_refusals))
    # Stored rows carry the DERIVED pair_id -> validate against the canonical row shape.
    c_refusals = validate_comparison(record["per_pair"], record["aggregate"],
                                     eligible_probe_ids=None, row_keys=_A.canon_row_keys, authority=_A)
    if c_refusals:
        raise R4SidecarError("record comparison fails re-validation: " + "; ".join(c_refusals))
    # F6 (Codex #1187): the stored rows must already BE their canonical representation (oriented,
    # sorted, derived pair_id). Otherwise a hand-built non-canonical record mints a different public
    # digest for an equivalent comparison. Canonical form is a validated property of any accepted
    # record, not merely a builder convention.
    # F6 (Codex #1197) + rev7: the stored rows AND aggregate must BE their canonical serialization,
    # compared by canonical BYTES, not ==. Python == treats -0.0 == 0.0 and 1 == 1.0 as equal, but
    # those serialize to distinct canonical-JSON tokens ("-0.0" vs "0.0", "1" vs "1.0") and mint
    # DIFFERENT public digests; a byte compare is what actually pins "equivalent comparisons share one
    # digest" across row order, endpoint orientation, pair_id, AND numeric spelling.
    if _canonical_bytes(record["per_pair"]) != _canonical_bytes(
            _canonicalize_comparison(record["per_pair"])):
        raise R4SidecarError(
            "stored comparison is not in canonical form (endpoints oriented, rows sorted by "
            "(probe_a, probe_b), pair_id derived, metrics normalized); equivalent comparisons "
            "must share one digest")
    if _canonical_bytes(record["aggregate"]) != _canonical_bytes(
            _canonicalize_aggregate(record["aggregate"])):
        raise R4SidecarError(
            "stored aggregate is not in canonical numeric form (metrics normalized to canonical "
            "float); equivalent comparisons must share one digest")
    return _VerifiedSidecar(record=record, output_digest=output_digest,
                            manifest_digest=manifest_digest)


def _reverify_against_parent(verified_report: Mapping[str, Any], record: Mapping[str, Any],
                             *, authority: "_SidecarAuthority | None" = None) -> Eligibility:
    """The SINGLE parent-aware custody point (rev5 Isegrim + Codex #1183 F1/F2).

    Bind the record's parent block + panel to the verified report via ``_check_parent_binding`` (the
    same check the builder runs — no divergence), then RE-DERIVE eligibility from the verified parent
    and cross-check the record's comparison covers exactly C(N', 2) over the DERIVED eligible set. A
    hand-built record that lies about eligibility, the generation-corpus digest, or the panel — none
    of which digest self-consistency can catch — is REFUSED here, before any C1-precondition.
    """
    _A = authority if authority is not None else _auth()
    par = record["parent"]
    _check_parent_binding(verified_report, b0_report_digest=par["b0_report_digest"],
                          generation_output_digest=par["generation_output_digest"],
                          panel=record["panel"])
    elig = partition_eligibility(verified_report, par["sequence_length"])
    refusals = validate_comparison(record["per_pair"], record["aggregate"],
                                   eligible_probe_ids=elig.eligible, row_keys=_A.canon_row_keys,
                                   authority=_A)
    if refusals:
        raise R4SidecarError(
            "the comparison does not cover the eligibility DERIVED from the bound parent (a stored "
            "or declared eligibility is not custody): " + "; ".join(refusals))
    return elig


def _build_link(vs: _VerifiedSidecar, verified_report: Mapping[str, Any],
                *, authority: "_SidecarAuthority | None" = None) -> dict[str, Any]:
    """The audit link, built from the ONE verified snapshot (never the live carrier — F3)."""
    _A = authority if authority is not None else _auth()
    rec = vs.record
    link = {
        "schema": _A.sidecar_schema + "-link",
        "b0_published_digest": verified_report["published_digest"],
        "sidecar_manifest_digest": vs.manifest_digest,
        "sidecar_output_digest": vs.output_digest,
        "evaluator_id": rec["evaluator"]["evaluator_id"],
        "evaluator_revision_sha": rec["evaluator"]["revision_sha"],
    }
    assert_strict_json(link)
    link["link_digest"] = canonical_digest({k: v for k, v in link.items() if k != "link_digest"})
    return link


def bind_to_parent_report(sealed_report: Mapping[str, Any],
                          sidecar: R4SidecarRecord) -> dict[str, Any]:
    """The audit LINK between a sealed B0 report and a sidecar — parent read, never written.

    Verifies the carrier ONCE (Codex #1183 F3), re-derives + parent-binds from the verified report
    (rev5 + F1/F2): binding a sidecar whose comparison, generation digest, or panel disagrees with
    the parent is refused, not linked.
    """
    # F-AUTH (a-Codex #1201): bind the frozen authority ONCE, before _verify_record fires the carrier's
    # items() callback, and thread it through every verdict helper. No helper re-fetches _auth() after
    # caller code has run, so a callback that reassigns _auth itself cannot poison a later read.
    _A = _auth()
    vs = _verify_record(sidecar, authority=_A)
    verified_report = verify_sealed_report(sealed_report, authority=_A)
    _reverify_against_parent(verified_report, vs.record, authority=_A)
    return _build_link(vs, verified_report, authority=_A)


# --------------------------------------------------------------------------- #
# The C1-precondition decision (fail-closed).                                  #
# --------------------------------------------------------------------------- #
def _build_decision(vs: _VerifiedSidecar, elig: Eligibility,
                    *, authority: "_SidecarAuthority | None" = None) -> dict[str, Any]:
    """Compute the fail-closed C1-precondition from the ONE verified snapshot + derived eligibility.

    Monk #1146: rho < gate => JSD replacement required; below the N' >= floor => INCOMPLETE. ONLY
    ``jsd_proceeds`` is green. The rho is recomputed from the rows, and n_eligible is the DERIVED
    count — never a stored declaration. All identity fields come from ``vs`` (F3), so a stateful
    carrier cannot swap a different digest in after verification.

    F-AUTH (Codex #1201, supersedes the rev8 F2 call-entry copy): ``gate`` and ``floor`` come from the
    import-frozen ``_auth()`` snapshot, not the reassignable module globals. So a report/carrier whose
    ``items()`` reassigns ``p5_r4_sidecar.RHO_GATE = -2.0`` — whether mid-verify or before the call —
    cannot green a failing comparison. The public ``RHO_GATE`` stays a documentable constant.
    """
    _A = authority if authority is not None else _auth()
    gate, floor = _A.gate, _A.floor
    rec = vs.record
    n_eligible = len(elig.eligible)
    rows = rec["per_pair"]
    # rho over the rows, computed defensively: an empty comparison (N' = 0/1) has no pairs, so there
    # is nothing to correlate — its rho is a report-only 0.0 sentinel that never gates.
    rho = (diversity_agreement_rho([r["jsd"] for r in rows], [r["cosine_similarity"] for r in rows])
           if rows else 0.0)
    # Take the floor outcome BEFORE trusting rho (Codex #1187 #6). Fewer than the N' >= 4 floor —
    # including N' = 0/1 whose canonical comparison is EMPTY — is the frozen INCOMPLETE, never a
    # division-by-zero or a structural refusal.
    # Wachhund audit: the state LABEL is read from the frozen snapshot too — a pre-call rebind of
    # DECISION_JSD_PROCEEDS (etc.) must not stamp a spoofed state into the record that feeds the future
    # C1 boundary. The c1 bool is already derived from the frozen gate/floor branch, not the label.
    if n_eligible < floor:
        state, c1 = _A.decision_incomplete, False
        reason = (f"n_eligible {n_eligible} < floor {floor}: too few non-refused prompts for "
                  "a meaningful Spearman; INCOMPLETE, not PASS")
    elif rho < gate:
        state, c1 = _A.decision_replacement, False
        reason = (f"rho {rho:.6g} < {gate}: JSD's residual is load-bearing; JSD must be replaced "
                  "with the embedding measure before C1")
    else:
        state, c1 = _A.decision_proceeds, True
        reason = f"rho {rho:.6g} >= {gate}: JSD and the embedding measure agree; JSD may proceed"
    decision = {
        "schema": _A.sidecar_schema + "-decision",
        "state": state,
        "c1_authorization_permitted": c1,
        "reason": reason,
        "recomputed_rho": rho,
        "rho_gate": gate,
        "n_eligible": n_eligible,
        "n_refused": len(elig.refusals),
        "sidecar_output_digest": vs.output_digest,
        "b0_report_digest": rec["parent"]["b0_report_digest"],
    }
    assert_strict_json(decision)
    decision["decision_digest"] = canonical_digest(
        {k: v for k, v in decision.items() if k != "decision_digest"})
    return decision


def r4_decision(sealed_report: Mapping[str, Any], sidecar: R4SidecarRecord) -> dict[str, Any]:
    """Public C1-precondition entry. Binds the GENUINE frozen authority and delegates.

    a-Codex #1201 pass 2: the public C1 gate takes NO caller authority — a public ``authority`` param
    is a trivial C1 bypass (a caller could pass ``_auth()._replace(gate=-2.0)`` and green anti-
    correlated evidence). Authority threading lives only behind the private ``_r4_decision`` worker,
    called by this wrapper and by the seam.
    """
    return _r4_decision(sealed_report, sidecar, authority=_auth())


def _r4_decision(sealed_report: Mapping[str, Any], sidecar: R4SidecarRecord,
                 *, authority: "_SidecarAuthority | None" = None) -> dict[str, Any]:
    """Emit the exact, fail-closed R4 decision/precondition record for the future C1 boundary.

    Verifies the carrier ONCE (Codex #1183 F3), re-derives eligibility + parent-binds from the
    verified report (rev5 + F1/F2), and builds the decision from that single snapshot. It no longer
    reads a stored ``eligibility`` block or re-reads the live carrier; a fabricated comparison,
    generation digest, or panel is refused by ``_reverify_against_parent`` before any state.

    PRIVATE: ``authority`` is the genuine snapshot threaded from the seam (bound before any caller
    items() ran); the public ``r4_decision`` wrapper supplies ``_auth()``. Not a public parameter.
    """
    # F-AUTH (Codex #1201 + a-Codex): every verdict helper below consumes this ONE threaded snapshot;
    # none re-fetches _auth() after caller code has run, so neither a value-global rebind nor an
    # _auth-accessor rebind mid-verification (nor a pre-call rebind of RHO_GATE) can drive the verdict.
    _A = authority if authority is not None else _auth()
    vs = _verify_record(sidecar, authority=_A)
    verified_report = verify_sealed_report(sealed_report, authority=_A)
    elig = _reverify_against_parent(verified_report, vs.record, authority=_A)
    return _build_decision(vs, elig, authority=_A)


# --------------------------------------------------------------------------- #
# F5 — atomic, no-replace publication with a TRUTHFUL terminal disposition.     #
# (DISPOSITION_* constants are defined up top so _bind_authority can freeze     #
# them; they remain public, documentable module names.)                        #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class R4PublishResult:
    path: str
    published_digest: str
    committed_bytes: int
    disposition: str                          # one of the DISPOSITION_* above


def publish_r4_sidecar(sealed_report: Mapping[str, Any], sidecar: R4SidecarRecord,
                       sidecar_path: Path) -> R4PublishResult:
    """Public publication entry. Binds the GENUINE frozen authority and delegates.

    a-Codex #1201 pass 2: takes NO caller authority (a public authority param is a bypass — a forged
    ``disp_verified`` could mislabel a downgraded commit). Threading lives behind ``_publish_r4_sidecar``.
    """
    return _publish_r4_sidecar(sealed_report, sidecar, sidecar_path, authority=_auth())


def _publish_r4_sidecar(sealed_report: Mapping[str, Any], sidecar: R4SidecarRecord,
                        sidecar_path: Path, *,
                        authority: "_SidecarAuthority | None" = None) -> R4PublishResult:
    """Atomically publish the artifact (record + link + decision). No-replace, truthful disposition.

    PRIVATE: ``authority`` is the genuine snapshot threaded from the seam / public wrapper.

    Monk #1146 F5: after linking, READ BACK the final bytes and confirm they equal what was meant to
    commit; a mismatch => committed_integrity_failed. The temp is a hard link to the same inode, and
    it is WRITABLE, so a surviving temp is a mutation alias on the final artifact — if the post-link
    unlink fails, that is committed_integrity_failed, never success. A directory-durability fault is
    committed_indeterminate. Never report integrity_verified after any of these.

    rev5 (Isegrim probe): re-derives eligibility from the verified parent (has it in hand) and
    refuses a fabricated comparison BEFORE staging any bytes; the committed artifact records the
    DERIVED eligibility, never a caller's declaration. rev6 (Codex #1183): verifies the carrier ONCE
    and builds link + decision from that single snapshot (F3), and the whole post-commit region is a
    non-throwing terminal state machine (F4) — a readback fault downgrades, never escapes.
    """
    # F-AUTH (Codex #1201 + a-Codex): gate/floor are frozen in _auth() (read inside _build_decision),
    # and the terminal DISPOSITION_* labels below are read from this frozen snapshot too — bound BEFORE
    # _verify_record fires the carrier's items() — so a rebind of RHO_GATE or of DISPOSITION_VERIFIED
    # (mid-verify or before the call) can neither green a failing decision nor mislabel a downgraded
    # commit as verified. Uses the authority THREADED from the seam when present, else binds here.
    _A = authority if authority is not None else _auth()
    sidecar_path = Path(sidecar_path)
    if sidecar_path.exists() or sidecar_path.is_symlink():
        raise R4SidecarError(f"sidecar path already exists (no-replace): {sidecar_path}")
    parent_dir = sidecar_path.parent
    if parent_dir.is_symlink() or not parent_dir.is_dir():
        raise R4SidecarError(f"sidecar parent dir must be an existing non-symlink: {parent_dir}")

    vs = _verify_record(sidecar, authority=_A)             # F3: capture the carrier ONCE
    verified_report = verify_sealed_report(sealed_report, authority=_A)
    elig = _reverify_against_parent(verified_report, vs.record, authority=_A)  # refuse a fabrication
    link = _build_link(vs, verified_report, authority=_A)   # internal helpers over the ONE snapshot,
    decision = _build_decision(vs, elig, authority=_A)       # never reopening the live carrier
    artifact = {
        "schema": _A.sidecar_schema + "-artifact",
        "record": vs.record,
        # The DERIVED eligibility (from the verified parent, not a stored declaration) for audit.
        "eligibility": {
            "sequence_length": vs.record["parent"]["sequence_length"],
            "n_eligible": len(elig.eligible),
            "eligible_probe_ids": list(elig.eligible),
            "refusals": [dict(r) for r in elig.refusals],
        },
        "link": link,
        "decision": decision,
        "sidecar_output_digest": vs.output_digest,
        "sidecar_manifest_digest": vs.manifest_digest,
    }
    assert_strict_json(artifact)
    artifact["published_digest"] = canonical_digest(
        {k: v for k, v in artifact.items() if k != "published_digest"})
    committed = _canonical_bytes(artifact)

    fd, tmp_name = tempfile.mkstemp(prefix=sidecar_path.name + ".", suffix=".tmp",
                                    dir=str(parent_dir))
    tmp = Path(tmp_name)
    try:
        os.write(fd, committed)
        os.fsync(fd)
    finally:
        os.close(fd)
    if tmp.read_bytes() != committed:                       # PRE-commit: raising is safe, nothing committed
        tmp.unlink(missing_ok=True)
        raise R4SidecarError("staged sidecar bytes did not verify before commit")
    os.link(str(tmp), str(sidecar_path))          # COMMIT — no-replace: fails if the target appeared

    # ---- F4 (Codex #1183/#1187): a non-throwing terminal state machine, ordered alias-FIRST. Past
    # the commit NOTHING may raise; every fault best-effort removes the writable alias and downgrades
    # truthfully. The definitive readback happens ONLY after the writable alias is gone — otherwise a
    # write through the alias can corrupt the final inode AFTER it verifies (Codex #1187). ----
    disposition = _A.disp_verified
    try:
        tmp.unlink()                                        # remove the writable hard-link alias FIRST
    except OSError:
        disposition = _A.disp_failed                        # a surviving writable alias can mutate the file
    try:
        if tmp.exists():
            disposition = _A.disp_failed
    except OSError:
        disposition = _A.disp_failed
    if disposition == _A.disp_verified:                    # only with no writable alias left
        try:
            if sidecar_path.read_bytes() != committed:      # definitive final-byte readback
                disposition = _A.disp_failed
        except OSError:
            disposition = _A.disp_failed                    # cannot confirm the commit => not verified
    # Directory-entry durability. A real fsync FAULT (supported but failed) is indeterminate; a
    # platform that cannot open a directory fd at all (e.g. Windows) is NOT a fault — the file was
    # already fsync'd, which is the durability the platform offers — so it does not downgrade.
    try:
        if _fsync_dir(parent_dir) is False and disposition == _A.disp_verified:
            disposition = _A.disp_indeterminate
    except OSError:
        if disposition == _A.disp_verified:
            disposition = _A.disp_indeterminate
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


def _load_governed_report(report_path: Path, journal_path: Path, *,
                          authority: "_SidecarAuthority | None" = None) -> tuple[dict[str, Any], bytes]:
    """Load a GOVERNED B0 evidence reference: the report bytes cross-verified by the journal.

    Monk #1146 F2-depth: a governed parent is a verified report+JOURNAL reference, not a caller's
    in-memory dict. Read the report bytes, run the existing terminal-frame verifier over the journal
    binding those exact bytes/digest, and REQUIRE an ``integrity_verified`` terminal authority.
    """
    # F-AUTH (a-Codex #1201): the sha256 format check, the terminal-journal VERIFIER, and the
    # integrity-verified disposition label are all read from the frozen snapshot. Rebinding
    # verify_terminal_frames to a permissive stub, or DISPOSITION_VERIFIED to a downgraded label
    # (so a committed-integrity-FAILED B0 parent clears this gate), can no longer admit an
    # inadmissible parent to the C1 precondition. Authority THREADED from the seam when present.
    _A = authority if authority is not None else _auth()
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
    if type(published) is not str or not _A.sha256.match(published):
        raise R4SidecarError("B0 report has no sha256 published_digest; not sealed")
    verdict = _A.terminal_verifier(journal_path, report_published_digest=published,
                                   committed_report_bytes=report_bytes)
    if not verdict.get("ok"):
        raise R4SidecarError(
            f"B0 journal did not verify: {verdict.get('reason')!r}; not a governed parent")
    if verdict.get("disposition") != _A.disp_verified:
        raise R4SidecarError(
            f"B0 terminal authority is {verdict.get('disposition')!r}, not {_A.disp_verified!r}; "
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
    # F-AUTH (a-Codex #1201 + pass 2): bind the frozen authority ONCE at the seam entry and thread it
    # through the PRIVATE workers, so a caller-manifest items() callback (fired inside build, which
    # binds its OWN genuine _A before that callback) cannot poison the later publish/decision reads.
    # The public gates take no caller authority; the seam uses the private _publish_r4_sidecar /
    # _r4_decision workers to thread its genuine _A.
    _A = _auth()
    report, _report_bytes = _load_governed_report(report_path, journal_path, authority=_A)
    sidecar = build_r4_sidecar(manifest, sealed_report=report, per_pair=per_pair,
                               aggregate=aggregate)
    result = _publish_r4_sidecar(report, sidecar, sidecar_path, authority=_A)
    decision = _r4_decision(report, sidecar, authority=_A)
    # The seam only reports ok when authority verified, the artifact committed cleanly (a downgraded
    # disposition is NOT ok), AND the precondition permits C1. Fail-closed on everything else. The
    # "verified" label is the frozen one, so a rebound DISPOSITION_VERIFIED cannot make a downgraded
    # publish read as ok.
    ok = (result.disposition == _A.disp_verified
          and bool(decision["c1_authorization_permitted"]))
    return R4RecordResult(decision=decision, publish=result, ok=ok)
