# Baseline Drift Gate v20 Review

**Reviewed commit:** `46d58c6438e7577e719fda171603f2dc44c6c278`
**Direct parent:** `974c0b06dd90474ccdc1e69fe9cc2ae8263bedbb`
**Prior drift implementation:** `187c6230ff39236cec549f389430c2708b098197`
**Prior review canon:** `578c4d88d4bc16e07d839c967b220e86a55d306a`
**Drift-gate blob:** `fd8bc54f2d678e395fe378092d41e0aff51e5b85`
**Test blob:** `942a237ec127481f3e6f973bf0a92d303e0b8f7d`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v20 `AuditRecord` instance-storage delta only. This is
not deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V20 closes class-default fallback for ordinary exact-dict records:

- all eight declared `AuditRecord` keys are checked before field access;
- deleting any of the four default-backed fields (`diversity_metric`,
  `ordinal`, `predecessor_digest`, or `discontinuity`) now produces a typed
  `INCOMPLETE` result and a matching direct-completeness issue;
- `_canonical_audit` reads checked instance keys instead of normal attribute
  lookup, so an actually deleted field cannot fall through to its class
  default; and
- the earlier audit/probe/discontinuity/binding missing-field guards, malformed
  binding receipts, resolver privatization, callable snapshots, and graph-copy
  protections remain intact under the built-in container shapes.

All 172 declared tests, focused Ruff, commit-local diff checks, and pinned
blobs pass. The direct parent includes the v19 review/continuity commits, but
its drift-gate blob is exactly v19's `ba58bad...`; there is no intervening
implementation drift.

## Findings

### P1: active `__dict__` subclasses can crash or rewrite the private snapshot

`AuditRecord` is still a non-slotted class whose instance dictionary can be
replaced with a `dict` subclass. The new predicate at `drift_gate.py:277-288`
does not require exact built-in storage. `set(rec.__dict__)` at line 284
dispatches the subclass iteration protocol. Later, `_canonical_audit` stores
`record.__dict__` and uses ordinary `d[...]` lookups at lines 830-842, which
dispatch the subclass `__getitem__` protocol.

Fresh exact-commit canaries demonstrate both failure modes:

```text
RaisingIterDict.__iter__                 uncaught RuntimeError
stored current diversity 0.5            honest trajectory HARD
__getitem__('diversity_metric') -> 0.8   hostile trajectory PASS
hostile trajectory type_rejection       absent
hostile trajectory chain_ok              true
```

The same value-substitution shape erased a valid root discontinuity during
canonicalization. Before replacement, the outcome published predecessor digest
`aa...aa`, predecessor count `7`, event `task:#168@event-696`, and recorder
`runner:test-harness`. Returning `None` only from the dictionary subclass's
`__getitem__('discontinuity')` removed all four custody fields while the outcome
still reported `chain_ok=true` and no type rejection.

This is an exact `AuditRecord`; no record subclass, probe subclass, conversion,
resolver callback, thread, or concurrent mutation is involved. The boundary
therefore remains non-total and its supposedly private snapshot remains
caller-controlled. It is the exact built-in-dictionary requirement already
named in the v19 correction, not a new threat-model expansion.

Fetch instance storage with `object.__getattribute__`, require
`type(storage) is dict` before any iteration or indexing, and check the known
field keys with built-in `dict` primitives. Canonicalization must consume that
same checked inert mapping or values and must not redispatch an unchecked
mapping protocol.

### Medium: regressions claim a four-field matrix but exercise only three shapes

`test_deleted_default_field_not_masked_by_class_fallback` at
`test_drift_gate.py:1878` names all four default-backed fields but deletes only
`diversity_metric`. The other new tests cover `discontinuity` and direct
`ordinal` completeness; no committed regression deletes
`predecessor_digest`, and none replaces `__dict__` with an active subclass.
The stale private-helper comments at `drift_gate.py:846` and several test
docstrings also still call `_resolve_acquisitions` a public path.

## Required Correction

1. Reject a non-exact `AuditRecord.__dict__` with a constant typed issue before
   invoking its iteration, membership, indexing, formatting, or copy hooks.
2. Check the required field keys with built-in primitives and canonicalize only
   from the exact checked storage or an inert value snapshot derived from it.
3. Add canaries for a raising dictionary iterator, a decision-softening
   `__getitem__`, and discontinuity erasure; require typed `INCOMPLETE`, no hook
   execution, no `chain_ok=true`, and no softened axis.
4. Parameterize the normal deletion regression over all four default-backed
   fields, including `predecessor_digest`, and remove the stale public-path
   wording.

## Verification

- focused pytest -> `172 passed in 0.74s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- all eight ordinary `AuditRecord` field deletions -> typed `INCOMPLETE` in
  full evaluation and matching direct-completeness issue
- all fourteen `ProbeResult` field deletions -> typed `INCOMPLETE`
- all four `DiscontinuityEvent` field deletions -> typed `INCOMPLETE`
- all three `EvidenceResolverBinding` field deletions -> typed error receipts
- old public resolver symbol -> absent
- exact record with raising `dict`-subclass iterator -> uncaught `RuntimeError`
- exact record with substituting `__getitem__` -> trajectory `HARD -> PASS`, no
  type rejection, chain clean
- exact root with substituting `discontinuity -> None` -> all predecessor/event
  custody details erased, no type rejection, chain clean

## Disposition

`46d58c6` is `CHANGES / P1`. Preserve its ordinary instance-key validation,
class-default-fallback repair, canonical instance-value intent, and every
repair accepted through v19. Keep #168 open and non-deployable until instance
storage itself is exact and inert before the gate touches it. Judge-chain,
origin-custody, slow-leak, disposition-calibration, and operational deployment
holds remain separate.
