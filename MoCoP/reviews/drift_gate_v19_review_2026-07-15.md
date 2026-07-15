# Baseline Drift Gate v19 Review

**Reviewed commit:** `187c6230ff39236cec549f389430c2708b098197`
**Direct parent:** `5a9831ac9eadd9bd4e0110f6e7d0ffe40e58521c`
**Prior drift implementation:** `5e7d5d800b083a75922b6aad943822dd5eb112c1`
**Prior review canon:** `20f9582459c8e678421fb707eb54c6bc8e89540f`
**Drift-gate blob:** `ba58bad7a6a505c3cbed156216735284f0a8a598`
**Test blob:** `beb76afad6acc9e1e06d224fbfaec59d766be4b4`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v19 exact-record totality and resolver-boundary delta only.
This is not deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V19 closes most of the v18 packet:

- exact uninitialized and field-deleted resolver bindings now produce typed
  errors on both private-helper and full-evaluator paths;
- all three missing binding fields (`resolver_id`, `version`, `resolve`) were
  independently replayed without an exception;
- every deleted `ProbeResult` slot and every deleted `DiscontinuityEvent` field
  returns a typed `INCOMPLETE` boundary outcome;
- missing non-default `AuditRecord` fields are caught before canonicalization;
- acquisition-bearing whitespace and wrong-typed bindings now receive matching
  `error` receipts through full evaluation, never `unbound`;
- the old public `resolve_acquisitions` symbol is absent and repository code
  imports only `_resolve_acquisitions`; and
- all 169 declared tests, focused Ruff, commit-local diff checks, and pinned
  blobs pass.

Preserve these repairs. One exact-shape hole remains for `AuditRecord` fields
with dataclass class defaults.

## Findings

### P1: deleting default-backed AuditRecord fields silently substitutes class defaults

`AuditRecord` is a non-slotted dataclass. Its `diversity_metric`, `ordinal`,
`predecessor_digest`, and `discontinuity` defaults remain class attributes.
Deleting any corresponding instance field therefore does not raise
`AttributeError`; normal `rec.field` lookup falls through to the class value.
The new `try/except AttributeError` guards at `drift_gate.py:1310-1359` cannot
detect this malformed exact shape.

Fresh exact-commit root-audit canaries deleted each field. All four produced:

```text
type_rejection       absent
missing reason       absent
validate completeness []
chain_ok             true
```

The value change is real: deleting an instance `diversity_metric=0.8` makes
normal lookup and the private snapshot consume the class default `0.0`.

The custody consequence is decisive. A valid root carried a discontinuity
event with predecessor digest, count 7, and event reference. Before deletion,
all three fields were published in outcome details. After
`object.__delattr__(audit, "discontinuity")`, the exact malformed record fell
back to class-level `None`; evaluation still reported `chain_ok=true` while
publishing none of the predecessor digest, predecessor count, or event
reference. No type rejection or missing-field reason recorded the loss.

This violates both the total closed-schema contract and the rule that a reset
never launders prior evidence. It also affects the public
`validate_audit_completeness` helper, which returns `[]` for all four deleted
default-backed fields.

Validate required instance storage before ordinary attribute lookup. For exact
non-slotted `AuditRecord`, read `__dict__` via `object.__getattribute__`, require
an exact built-in dict, require every declared field key with `dict` primitives,
and then validate/canonicalize only those instance values. Apply the same shape
predicate in `validate_audit_completeness` so direct validation and full
evaluation cannot disagree.

### Medium: tests and comments do not cover the remaining shape distinction

The new regressions test an uninitialized record, which fails first on the
non-default `audit_id`; they do not delete any default-backed field. Probe and
discontinuity missing-field behavior is implemented correctly but remains
manual rather than committed as a full field matrix. A few comments/docstrings
still call `_resolve_acquisitions` by the removed public name and describe a
public path; these should be updated after the boundary disposition is final.

## Required Correction

1. Require all eight `AuditRecord` keys to exist in exact instance storage;
   never accept class-default fallback as field presence.
2. Share that exact-shape check with `validate_audit_completeness` and the full
   evaluator boundary, then canonicalize only the checked instance values.
3. Add regressions deleting `diversity_metric`, `ordinal`,
   `predecessor_digest`, and `discontinuity`; require typed missing-field
   rejection, `INCOMPLETE`, and no silent custody loss. Include the
   discontinuity predecessor-detail canary.
4. Commit the full missing-field matrix for probe/discontinuity/binding nodes
   and remove stale references to a public `resolve_acquisitions` path.

## Verification

- focused pytest -> `169 passed in 0.43s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- resolver binding uninitialized/deleted id/version/resolve -> typed direct and
  full error receipts
- every deleted ProbeResult/DiscontinuityEvent field -> typed `INCOMPLETE`
- full whitespace/wrong-type binding acquisition -> matching error receipt
- old public resolver symbol -> absent
- deleted default-backed AuditRecord fields -> accepted through class fallback,
  no missing/type issue, completeness `[]`, `chain_ok=true`
- deleted discontinuity field -> predecessor digest/count/event publication
  erased without custody evidence

## Disposition

`187c623` is `CHANGES / P1`. Preserve its missing-field exception guards,
binding-error passthrough, actual helper privatization, callable snapshots, and
all earlier repairs. Keep #168 open and non-deployable until exact instance
storage proves every `AuditRecord` field exists and the shared completeness and
full-evaluator paths reject default-backed field deletion without losing
discontinuity custody. Policy/math/custody repairs accepted before v19 remain
accepted. Judge-chain, origin-custody, slow-leak, disposition-calibration, and
operational deployment holds remain separate.
