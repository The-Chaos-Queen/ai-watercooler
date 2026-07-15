# Baseline Drift Gate v16 Review

**Reviewed commit:** `e4c0a7ed6cf8f0688fe6a9703fd46b385ab86d13`
**Direct parent:** `b1f54710559f5226f0a13bca089942337092c225`
**Prior drift implementation:** `9061dccb251f40a13cbd3cc8a783a696ca4ad20b`
**Prior review canon:** `f5e3c29274fa22ac194f4f11289ca73c7b6c49c1`
**Drift-gate blob:** `076fa8b5f371ba73dd0e455d3ea51d7d6af0feda`
**Test blob:** `db7fefceb748dd591fc500523e68c4f92e60dff6`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v16 resolver-snapshot/custody delta only. This is not
deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V16 closes two concrete v15 paths:

- final `GateOutcome.details` no longer rereads caller-owned resolver identity
  fields after a resolver callback;
- an exact binding whose callback mutates both `resolver_id` and `version`
  retains the original values in its receipt and published resolver details;
- full `evaluate_audit` exact-checks the binding object before field access;
  a hostile non-exact object has zero getter reads and produces an explicit
  incomplete reason instead of escaping; and
- all 159 declared tests, focused Ruff, commit-local diff checks, and pinned
  blobs pass.

Preserve these repairs. `_resolver_snapshot` is nevertheless the original
binding object, not an immutable snapshot, so callback authority is still
replaceable between acquisition rows. Resolver validity and public-batch
custody also remain inconsistent.

## Findings

### P1: the first resolver callback can replace the authority used for later rows

At `drift_gate.py:1397-1406`, `_resolver_snapshot` is assigned the original
caller binding by identity. `resolve_acquisitions` captures identity strings but
still reads `resolver.resolve` afresh at line 931 for every acquisition row.
The requested callable snapshot therefore does not exist.

A fresh exact-commit full-evaluator canary supplied two acquisition rows. The
original callable accepted the first row and used `object.__setattr__` to
replace `binding.resolve` with a permissive callable. The second row was then
handled only by the replacement:

```text
original callable calls      [(ruling:first/allowed, acq_first)]
replacement callable calls   [(ruling:second/must-reject, acq_second)]
acq_first receipt/verdict    resolved / GROWTH
acq_second receipt/verdict   resolved / GROWTH
published authority          resolver:original / v1
```

The second row would have been rejected by the original callable. A different
authority can therefore mint `GROWTH` while receipts and outcome details name
the original resolver. Frozen dataclass syntax does not prevent
`object.__setattr__`, as the v15 finding and v16 regression already recognize.

Capture `resolver.resolve` once before the first callback and invoke only that
local callable for every row. Full evaluation should pass a newly constructed
private binding/snapshot, not the caller object. The public helper must also
capture its callable once because callers can invoke it directly with an exact
binding whose callback closes over that binding.

### High: evaluator and helper disagree about resolver validity

The evaluator checks only exact string types at lines 1402-1406. The helper
also requires non-whitespace identity and version. This split produces
contradictory artifacts:

- resolver id `"   "` is published in `details["evidence_resolver"]`, while
  the same row receives an error receipt with empty resolver identity and
  reason `resolver binding lacks identity/version`; and
- an exact binding with a wrong-typed identifier is converted to `None`, so
  the receipt says `unbound / no evidence resolver bound` and no
  resolver-specific incomplete reason is recorded. The caller did bind a
  malformed resolver; it did not omit one.

Validate exact, nonempty identity/version once and preserve invalid bindings as
typed resolver errors. Do not silently translate validation failure into the
semantic state `no resolver bound`, and publish resolver details only from the
same fully valid snapshot used for every receipt.

### High: the public invalid-batch boundary remains silent

Watercooler #1037 says invalid containers, rows, scalars, and enums all receive
typed rejection through the evaluator boundary. That is true only after entry
through `evaluate_audit`; it does not close the v15 finding against the public
`resolve_acquisitions` function. The helper still:

- returns `{}` for a non-exact outer container at line 858;
- silently skips a non-exact row class at lines 864-866; and
- emits no receipt for an exact row with a malformed `evidence_type` leaf.

Fresh direct canaries returned `{}` for all three cases. The docstring at line
856 still promises silent skipping. These inputs remain indistinguishable from
a valid batch with no acquisitions and remain absent from rejection reporting
and the receipt digest. Return a typed batch-boundary result, or make this
worker private/canonical-only behind the evaluator's total gate.

### Medium: regressions cover identity, not authority or boundary completeness

The new mutation test checks only `resolver_id` and a single callback; it does
not assert version, callable stability, or multi-row authority. The non-exact
binding test uses passive class fields rather than proving hostile getters stay
untouched. There are no regressions for whitespace/wrong-typed binding fields
or the three public invalid-batch shapes.

## Required Correction

1. After exact binding validation, capture exact nonempty identity, exact
   nonempty version, and `resolve` once. Build a new internal immutable snapshot
   or pass those locals; never retain the caller binding as the snapshot.
2. Make `resolve_acquisitions` invoke one captured callable for every row. A
   callback mutation of the source binding must not affect any later row.
3. Keep malformed bound resolvers typed as malformed-bound errors and explicit
   incomplete reasons. Never demote them to `resolver is None`; publish identity
   only when it exactly matches every receipt.
4. Return typed batch-boundary errors for otherwise unkeyable invalid inputs,
   or make the worker private and accept only canonical internal rows.
5. Add full-evaluator regressions for two-row callable replacement, identity
   plus version mutation, whitespace and wrong-typed fields, hostile getter
   zero access, and typed invalid-container/row/evidence-type handling.

## Verification

- focused pytest -> `159 passed in 0.40s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- exact binding identity/version mutation -> receipt and details retained
  original values
- hostile non-exact binding -> getter zero, explicit incomplete reason
- two-row exact binding callable replacement -> replacement resolved the second
  row and minted `GROWTH` under the original resolver identity
- whitespace identity -> error receipt with empty identity but whitespace
  resolver published
- wrong-typed identity -> silently reported as unbound, no resolver reason
- invalid outer container/row class/evidence-type leaf -> `{}` on public helper

## Disposition

`e4c0a7e` is `CHANGES / P1`. Preserve its final-publication identity locals,
pre-read exact binding gate, and all earlier protocol repairs. Keep #168 open
and non-deployable until one inert identity/version/callable snapshot governs
every acquisition row and final publication, malformed bound resolvers remain
typed as such, and the public invalid-batch boundary has auditable custody or is
removed. Policy/math/custody repairs accepted before v16 remain accepted.
Judge-chain, origin-custody, slow-leak, disposition-calibration, and operational
deployment holds remain separate.
