# Baseline Drift Gate v21 Review

**Reviewed commit:** `914089a130f2af687a82bdc09afb357570a6d94e`
**Direct parent:** `ff10884d96142bb2f3f03ec465b3651aea73415e`
**Prior drift implementation:** `46d58c6438e7577e719fda171603f2dc44c6c278`
**Prior review canon:** `f4f4b723fe0c6b10eff4c0d8696f422afe995f07`
**Drift-gate blob:** `91cfc61d9a8e20d0ea047ec4eaa2544542809499`
**Test blob:** `f2d78504d3ba51333ab795490c357c2a114c1573`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v21 instance-storage and full caller-record-graph delta
only. This is not deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V21 closes the literal v20 dictionary-subclass paths:

- `AuditRecord.__dict__` is fetched through `object.__getattribute__`;
- a non-exact dictionary is rejected before its iteration or indexing hooks;
- fresh raising-iterator and raising-index canaries return typed `INCOMPLETE`
  with zero hook calls;
- there is no caller callback between the exact storage check and canonical
  copy, so the second descriptor-direct read remains the checked exact object
  under the single-threaded boundary contract; and
- all ordinary audit/probe/discontinuity/binding deletion guards, callable
  snapshots, typed receipts, resolver privatization, and earlier graph-copy
  repairs remain intact.

All 173 declared tests, focused Ruff, commit-local diff checks, and pinned
blobs pass. The direct parent includes the v20 review/continuity commits, but
its Drift Gate blob is exactly v20's `fd8bc54...`; there is no intervening
implementation drift.

## Findings

### P1: exact dictionaries still carry active undeclared keys across the record graph

An exact built-in `dict` is an inert container implementation, but its keys are
still caller-owned objects. Python permits arbitrary keys to be inserted
directly into a non-slotted instance dictionary. V21 checks only the container
type, then materializes every key with `set(storage)` at `drift_gate.py:287`.
A non-string key with the same hash as a declared field can therefore execute
its `__eq__` while the set is built.

Fresh exact-commit canaries used exact records and exact built-in dictionaries,
with one undeclared collision key inserted before the normal string fields:

```text
AuditRecord key equality raises             uncaught RuntimeError
direct validate_audit_completeness          uncaught RuntimeError
stored current diversity                    0.5 -> 0.8 during key equality
range trajectory                            HARD -> PASS
type_rejection                              absent
chain_ok                                    true
```

The issue is not limited to the new presence predicate. The other caller-owned
non-slotted dataclasses still use ordinary attribute lookup, which can also
compare a colliding key in their exact instance dictionary:

- an active `DiscontinuityEvent` key rewrote the published predecessor digest
  from `aa...aa` to `bb...bb` and count from `7` to `1`, with no rejection and
  `chain_ok=true`;
- an active `EvidenceResolverBinding` key replaced the original rejecting
  callable with an accepting callable during the `resolver_id` lookup. The
  acquisition was published as `resolved`/`GROWTH` under the unchanged
  `resolver:original` identity and `v1` version;
- raising variants escape both full evaluation and the direct private resolver
  helper as `RuntimeError`; and
- `audit_digest`, whose docstring promises totality over malformed input, also
  raises during ordinary field lookup on this exact-record shape.

The same predicate accepts an extra exact-string instance field with direct
completeness `[]`, no type rejection, and `chain_ok=true`, so the advertised
closed schema is not actually closed over instance keys.

This is the remaining version of the full-record-graph authority defect: exact
container identity does not make unchecked contained keys inert. The cleanest
repair is to make all caller-owned boundary dataclasses slotted
(`AuditRecord`, `DiscontinuityEvent`, and `EvidenceResolverBinding`) and retain
typed missing-slot guards. If non-slotted compatibility must remain, use one
shared storage reader for every node: exact built-in dictionary, exact declared
key set, and exact-string keys proven by `dict.__iter__` plus identity checks
before any set, hash, equality, membership, or ordinary attribute lookup. Read
declared values only through built-in dictionary primitives and snapshot them
once.

### Medium: the regression packet covers only the outer container class

The new test at `test_drift_gate.py:1908` correctly rejects a `dict` subclass,
but it does not cover active keys inside an exact dictionary, nested
discontinuity storage, binding callable substitution, direct helper/digest
totality, or exact key-set closure. The earlier default-field test still names
four fields while deleting only `diversity_metric`; no committed matrix cell
deletes `predecessor_digest`. Stale comments at `drift_gate.py:849` and in tests
also continue to describe the private resolver helper as a public path.

## Required Correction

1. Close the storage shape for every caller-owned non-slotted boundary node,
   preferably with `slots=True`, or with one descriptor-direct exact-storage
   validator shared by audits, discontinuities, and resolver bindings.
2. Before any key hashing/equality or ordinary field lookup, iterate the exact
   dictionary with built-in primitives, require every key to be exact `str`,
   and require exactly the declared field set with no extras.
3. Snapshot only values read from that checked storage; use the same canonical
   snapshot for validation, resolver identity/callable, custody, digest, and
   publication. Route direct helpers through the same boundary or document
   them as canonical-only and remove false totality claims.
4. Add raising and mutating collision-key canaries for all three node types.
   Assert zero new key hooks, typed refusal, no `HARD -> PASS`, no custody
   rewrite, and no `GROWTH` under a substituted callable.
5. Commit the complete four-default-field deletion matrix and remove stale
   public-path wording.

## Verification

- focused pytest -> `173 passed in 0.43s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- v20 `dict`-subclass iterator/index attacks -> typed `INCOMPLETE`, zero hooks
- all eight ordinary `AuditRecord` deletions -> typed full/direct rejection
- all fourteen probe, four discontinuity, and three binding deletions -> typed
- old public resolver symbol -> absent
- exact built-in audit dictionary with raising collision key -> uncaught
  `RuntimeError` in full and direct completeness paths
- exact built-in audit dictionary with mutating collision key -> trajectory
  `HARD -> PASS`, no rejection, chain clean
- exact built-in discontinuity dictionary with mutating collision key ->
  predecessor digest/count rewritten, no rejection, chain clean
- exact built-in binding dictionary with mutating collision key -> rejecting
  callable replaced; receipt `resolved`, verdict `GROWTH`, original identity
- direct `audit_digest` on exact active-key record -> uncaught `RuntimeError`
- extra exact-string audit instance key -> completeness `[]`, no rejection,
  chain clean

## Disposition

`914089a` is `CHANGES / P1`. Preserve its exact outer-dictionary gate,
descriptor-direct retrieval, ordinary missing-field repair, and every repair
accepted through v20. Keep #168 open and non-deployable until the declared
storage graph includes exact keys for audits, discontinuities, and resolver
bindings before any caller protocol can run. Judge-chain, origin-custody,
slow-leak, disposition-calibration, and operational deployment holds remain
separate.
