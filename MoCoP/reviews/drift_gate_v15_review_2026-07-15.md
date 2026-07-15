# Baseline Drift Gate v15 Review

**Reviewed commit:** `9061dccb251f40a13cbd3cc8a783a696ca4ad20b`
**Direct parent:** `b2d8f882b62cc1ccc92e4edd294cd6d3fc3c82bd`
**Prior drift implementation:** `da9a1e18b8b9522a38d3b3a5ec8abe95a897348e`
**Drift-gate blob:** `90ae8f91df7684f4fd725d568ee9c72ffcf4b1a3`
**Test blob:** `3e32da82e30a36e6b57eb9a606360b6d31ceed34`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v15 resolver isolation/custody delta only. This is not
deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V15 closes the pre-canonical resolver getter attack from v14:

- probes are leaf-checked and canonicalized before any resolver access;
- `type(resolver) is EvidenceResolverBinding` is required before the helper
  reads a binding field;
- the active binding getter can no longer run or change the caller row; the
  locator remains empty and the helper emits an error receipt;
- recognizable exact acquisition rows with non-exact leaves now receive typed
  error receipts instead of silently disappearing;
- the prior active-notes alias remains closed and protected scoring stays
  `HARD`;
- three focused regressions were added; and
- all 157 declared tests, focused Ruff, and commit-local diff checks pass.

Preserve these changes. The helper snapshot is not carried through full outcome
publication, and several invalid public-batch shapes remain silent.

## Findings

### P1: full evaluation rereads caller binding after the resolver callback

`resolve_acquisitions` captures `rid` and `rver` at
`drift_gate.py:881-901`, so its receipts retain the checked identity. But
`evaluate_audit` discards that custody boundary and reads the original caller
binding again at lines 1489-1490 while building `details["evidence_resolver"]`.
The helper also rereads `resolver.resolve` at line 931 instead of capturing the
checked callable once.

An exact frozen dataclass prevents ordinary assignment, not
`object.__setattr__`. A fresh exact-commit canary used an exact
`EvidenceResolverBinding`; its resolver callback held the binding in its
closure and changed `resolver_id` and `version` before returning `True`:

```text
receipt status/identity    resolved, resolver:original, v1
published resolver         resolver:mutated, v999
binding after callback     resolver:mutated, v999
```

The same decision artifact therefore attributes one successful receipt to two
different resolver identities. This violates the bound typed receipt and
single-source custody contract.

A second canary supplied a non-exact binding subclass whose identifier getter
raises. The helper correctly returned error receipts without touching it, but
the final outcome-details reread invoked the getter and escaped full
`evaluate_audit` as `RuntimeError`. The new test named
`test_raising_binding_subclass_produces_error_receipt` exercises only the direct
helper, not the full evaluator path named in its docstring.

Snapshot exact identity, version, and callable once after the exact binding
gate. Pass that internal snapshot through resolution and publish only its inert
fields. No code after the intentional callback may return to the caller-owned
binding object.

### High: some invalid public batches still disappear without custody evidence

V15 emits an error receipt for an exact `ProbeResult` whose leaves are invalid
and whose `evidence_type` is still an exact `ACQUISITION`. It still returns `{}`
for a non-exact outer container at line 858, silently skips non-exact row
objects at lines 864-866, and cannot record an exact row whose evidence-type
leaf itself is malformed. The helper docstring at line 856 still states that
non-exact rows are silently skipped.

These cases remain indistinguishable from a valid batch containing no
acquisition rows and remain absent from rejection reporting and the receipt
digest. A dict keyed only by a validated anchor cannot express every malformed
batch. Use a typed batch result with boundary errors, or make the worker private
and canonical-only behind the evaluator's already-total gate.

### Medium: full-path and batch-shape regressions remain missing

The new tests cover helper-local binding rejection and one recognizable invalid
leaf row. They do not cover full evaluator publication, binding self-mutation,
non-exact outer containers, non-exact row classes, or malformed evidence-type
leaves. The earlier six zero-hook canaries also remain manual rather than
committed.

## Required Correction

1. After exact binding validation, capture exact identity/version and the
   callable once into an internal immutable snapshot.
2. Use only that snapshot in every callback invocation, receipt, digest, error,
   and final `GateOutcome.details` field. Never reread the caller binding after
   the first intentional resolver call begins.
3. Return a typed batch-boundary result for container/row/leaf failures that
   cannot safely produce an anchor-keyed receipt, or make the worker private and
   canonical-only.
4. Add full-evaluator regressions for a raising binding subclass and exact
   binding self-mutation. Require no exception and exact equality between
   receipt and published resolver identity/version. Add typed invalid-container,
   row-class, and evidence-type cases.

## Verification

- focused pytest -> `157 passed in 0.36s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- v14 binding-getter mutation -> getter zero, row unchanged, typed error receipt
- active exact-row notes alias -> callback zero, protected `HARD`
- exact binding self-mutation -> resolved receipt retained original identity,
  outcome published mutated identity/version
- raising binding subclass -> helper typed error, full evaluator escaped as
  `RuntimeError` during publication reread

## Disposition

`9061dcc` is `CHANGES / P1`. Preserve its phased row-before-binding order,
exact binding gate, typed recognizable-row failures, and all prior protocol
repairs. Keep #168 open and non-deployable until an immutable successor carries
one resolver snapshot through callback execution and outcome publication and
gives every invalid public batch auditable typed custody. Policy/math/custody
repairs accepted before v15 remain accepted. Judge-chain, origin-custody,
slow-leak, disposition-calibration, and operational deployment holds remain
separate.
