# Baseline Drift Gate v13 Review

**Reviewed commit:** `f8b9e77d8317c1f27663d0e2f551e90031e3e4b5`
**Direct parent:** `1ccda6fef8bc656ede81d9f0094b342bb732dd77`
**Prior drift implementation:** `f2edb870bd86d971cba48f2d5b07231b0e5be2ce`
**Drift-gate blob:** `cf64a05e66391aa4ab9be6d0b2486a13db8301c3`
**Test blob:** `e1d4477accdc8e11e5deb98308491c789edce35c`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v13 active-boundary delta only. This is not deployment
approval and does not close OpenCLAW #168.

## Accepted Repairs

V13 closes all six literal v12 hook canaries:

- exact `str.strip` is used only after an exact evidence-ref type check;
- all three enum leaves are now exact-checked in the main evaluator;
- `_safe_type_name` bypasses caller metaclass `__getattribute__` through the
  trusted `type.__dict__` descriptor;
- resolver exceptions use constant text and non-boolean result type reporting
  does not invoke caller `__repr__`;
- fresh canaries confirm that active evidence-ref, resolver-id, enum, metaclass,
  exception, and callback-result hooks all remain untouched; and
- all 152 declared tests, focused Ruff, and commit-local diff checks pass.

Preserve these changes. The remaining blocker is the unchanged open record graph
at the public acquisition helper and resolver-binding boundary.

## Findings

### P1: public acquisition resolution still passes unchecked row leaves and bindings

`resolve_acquisitions` at `drift_gate.py:821-880` does not use the evaluator's
exact row/leaf checker. Its comprehension at lines 837-838 accepts an exact
`ProbeResult` and `_canonical_probe` field-copies every leaf without validating
it. Only `anchor` and `evidence_ref` are constrained afterward. Active `notes`,
envelope, numeric, and enum leaves therefore survive by identity into the row
given to the resolver callback.

A fresh exact-commit canary used an exact list and exact rows. The acquisition
row's only active field was a `str` subclass in `notes`; that object carried an
`owner` reference to the ordinary `name` row. The resolver received the exact
same active leaf, followed the alias, changed `name` from `ABSENT/-1` to
`PRESENT_RECOVERABLE/2`, and returned `True`:

```text
before helper       protected=hard  name=erosion
resolver input      probe.notes is caller_notes: true
receipt             new_capacity=resolved
after helper        protected=pass  name=neither  new_capacity=growth
```

This recreates the callback alias class that the canonical resolver row was
intended to close. Field-building only the outer dataclass does not make its
active leaves inert.

The binding side is also unchecked. Line 835 reads `resolver.resolver_id` before
requiring an exact `EvidenceResolverBinding`; an overriding binding subclass
raised from that attribute and escaped both direct `resolve_acquisitions` and
the full `evaluate_audit` path. The main evaluator later reads resolver fields
again at line 1430. Exact binding identity and exact identity/version leaves
must be established before any of those reads.

Finally, lines 837-838 still silently drop non-exact rows, while a non-exact
outer container returns an indistinguishable empty receipt map. That does not
implement the documented typed, exactly-once batch contract or the explicit
v12 correction.

### Medium: none of the v12 adversarial regressions were committed

The v13 test delta changes only one expected error string. It adds no regression
for the active evidence-ref, resolver identity, enum leaf, custom metaclass,
resolver exception, or non-boolean result paths required by review `3f47dcd`.
Fresh manual canaries show the six named fixes currently work, but the declared
suite will not detect their regression. The new active-notes alias and binding
subclass cases are also absent.

## Required Correction

1. Move the exact `ProbeResult` leaf check to a shared module-level parser and
   use it before `_canonical_probe` in both `evaluate_audit` and every public
   acquisition entry point. No active leaf may reach the resolver by identity.
2. Before reading any field, require an exact `EvidenceResolverBinding`; then
   require exact nonempty string identity/version and capture its callable once.
   Use only the checked local binding data in receipts and outcome details.
3. Stop silently filtering invalid rows. Return a structured batch-boundary
   failure, or make the resolver worker private and canonical-only behind a
   total checked public wrapper.
4. Commit all v12 zero-hook regressions plus the active-notes alias and binding
   subclass cases. Require the original protected `HARD` to remain and every
   hostile hook counter to stay zero.

## Verification

- focused pytest -> `152 passed in 0.38s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- six v12 hook canaries -> corrected outcomes, every hook count zero
- active exact-row notes alias -> resolver received caller leaf by identity;
  protected score changed `HARD` to `PASS` and minted `GROWTH`
- active binding subclass -> `resolver_id` hook escaped direct helper and full
  evaluator as `RuntimeError`

## Disposition

`f8b9e77` is `CHANGES / P1`. Preserve its exact evidence-ref handling, enum
checks, descriptor-direct type names, and safe resolver result/error reporting.
Keep #168 open and non-deployable until an immutable successor applies the same
closed graph parser to the public acquisition and binding surfaces and commits
the adversarial regressions. Policy/math/custody repairs accepted before v13
remain accepted. Judge-chain, origin-custody, slow-leak,
disposition-calibration, and operational deployment holds remain separate.
