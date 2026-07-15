# Baseline Drift Gate v17 Review

**Reviewed commit:** `9596737b87ae7e3bb7c03d88c20589370c8eb3ab`
**Direct parent:** `15962abc0d3284208ccd2eee949f2deae744faec`
**Prior drift implementation:** `e4c0a7ed6cf8f0688fe6a9703fd46b385ab86d13`
**Prior review canon:** `9f16b5e63e72cc901d035d3f237b872a06de1c36`
**Drift-gate blob:** `dff85903733bb09e660d8853c5b331db90884e33`
**Test blob:** `6006c561287c88af5a8951dbd2206dedad7fa940`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v17 resolver-callable and malformed-binding delta only.
This is not deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V17 closes the v16 full-evaluator authority substitution:

- `evaluate_audit` reads valid identity, version, and callable once and builds a
  fresh exact `EvidenceResolverBinding` before any callback;
- a first callback that mutates the original binding's `resolve` field cannot
  change the callable used for the second full-evaluator acquisition;
- the exact two-row canary now calls the original resolver twice, rejects the
  second row, and does not mint second-row `GROWTH`;
- whitespace and wrong-typed identity fields now add explicit evaluator
  incomplete reasons and are not published as resolver identity; and
- all 162 declared tests, focused Ruff, commit-local diff checks, and pinned
  blobs pass.

Preserve these repairs. The public helper remains directly vulnerable to the
same callable swap, malformed bound resolvers still become `unbound` in their
receipts, and invalid public batch shapes remain silent.

## Findings

### P1: direct public helper calls still permit between-row authority substitution

The fresh snapshot exists only in `evaluate_audit`. The public
`resolve_acquisitions` path still reads `resolver.resolve` at line 931 for each
row. Its own comments and `_probe_leaves_exact` docstring explicitly describe
this as the public path, tests import it directly, and Watercooler #1039 claims
that boundary is independently gated.

A fresh exact-commit direct canary passed an exact binding and two acquisition
rows. The original callback accepted the first row and replaced
`binding.resolve` through `object.__setattr__`. The helper then fetched and
called the replacement for the second row:

```text
calls                 [(original, acq1), (replacement, acq2)]
acq1 receipt          resolved / resolver:direct
acq2 receipt          resolved / resolver:direct
```

The original callable would reject `acq2`. A replacement authority therefore
resolves later evidence under the original identity. A caller can feed those
receipts directly into `score_protected_set`, where `resolved` is sufficient to
mint `GROWTH`; the full evaluator repair does not protect this public route.

After exact binding and identity validation, capture `resolve_fn =
resolver.resolve` once before the row loop and invoke only `resolve_fn`. Do this
inside `resolve_acquisitions`, regardless of whether the caller already passed
an evaluator-created snapshot.

### High: malformed bound resolvers are still recorded as unbound

V17 adds correct evaluator-level incomplete reasons, but continues passing
`_resolver_snapshot=None` to `resolve_acquisitions` whenever binding fields are
invalid. With an actual acquisition row, both tested malformed bindings produce
the same receipt:

```text
whitespace id   unbound / no evidence resolver bound
wrong-type id   unbound / no evidence resolver bound
```

The outcome also contains the new `non-empty` or `exact str` incomplete reason,
so the artifact now contradicts itself: the evaluator says a malformed resolver
was bound while the receipt says no resolver was bound. The new tests use
audits without acquisition rows and inspect only `incomplete_reasons`; they do
not examine the affected receipts.

Pass invalid bindings through a typed invalid-binding route so each acquisition
gets an `error` receipt naming binding validation failure. `unbound` must remain
reserved for the literal caller state `resolver is None`.

### High: invalid public batches still disappear without typed custody

No v17 change touches the remaining v15 public-boundary finding. Direct fresh
canaries still return `{}` for:

- a non-exact outer list container;
- a non-exact `ProbeResult` row class; and
- an exact row whose `evidence_type` leaf is malformed.

The helper docstring still promises silent skipping at line 856. Exact-type
gating followed by silent omission is not a typed result. These inputs remain
indistinguishable from a valid no-acquisition batch and absent from rejection
reporting and the receipt digest. Return a typed batch-boundary result, or make
the worker private/canonical-only and remove the public contract and imports.

### Medium: regressions do not exercise the remaining affected surfaces

The callable-swap regression enters only through `evaluate_audit`; there is no
direct-helper equivalent. The whitespace and wrong-type regressions contain no
acquisition row and therefore cannot assert receipt status/reason. No regression
requires typed results for the invalid outer-container, row-class, or
evidence-type cases.

## Required Correction

1. Capture the validated callable once inside `resolve_acquisitions` and use
   that local for every row. Preserve the new evaluator-created snapshot.
2. Keep malformed-bound distinct from absent/unbound all the way into receipts:
   every affected acquisition must receive `status="error"` and a stable typed
   reason; reserve `unbound` for `resolver is None` only.
3. Return typed batch-boundary errors for unkeyable invalid inputs, or make the
   worker private and accept only canonical internal rows.
4. Add direct-helper two-row callable-swap coverage, acquisition-bearing
   whitespace/wrong-type binding coverage, and typed invalid-container/row/
   evidence-type regressions.

## Verification

- focused pytest -> `162 passed in 0.46s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- full evaluator callable swap -> original called twice; second row rejected;
  no second-row `GROWTH`
- direct helper callable swap -> replacement called for second row; both
  receipts resolved under original identity
- whitespace and wrong-typed binding with acquisition -> evaluator reason is
  typed, but receipt remains `unbound / no evidence resolver bound`
- invalid outer container/row class/evidence-type leaf -> `{}` on public helper

## Disposition

`9596737` is `CHANGES / P1`. Preserve the new full-evaluator snapshot and
identity-field validation, plus all earlier protocol repairs. Keep #168 open
and non-deployable until the public resolver path captures one callable for the
whole batch, malformed-bound state remains typed through every receipt, and the
invalid public-batch boundary has auditable custody or is removed.
Policy/math/custody repairs accepted before v17 remain accepted. Judge-chain,
origin-custody, slow-leak, disposition-calibration, and operational deployment
holds remain separate.
