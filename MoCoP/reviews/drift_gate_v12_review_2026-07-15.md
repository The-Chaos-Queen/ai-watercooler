# Baseline Drift Gate v12 Review

**Reviewed commit:** `f2edb870bd86d971cba48f2d5b07231b0e5be2ce`
**Direct parent:** `6506bad4f8ad83288cb14eae23c434a22957bb2e`
**Prior drift implementation:** `f1417be03c6aed489a59ec3355c3327581f64adc`
**Drift-gate blob:** `aa6e55efd62e518e9844d3ed5e663f330ef0fd33`
**Test blob:** `38ebfa63619db85bb0a402974160166cf8087ebd`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v12 active-boundary delta only. This is not deployment
approval and does not close OpenCLAW #168.

## Accepted Repairs

V12 closes the three literal v11 canaries:

- the `_coerce_*` functions are gone;
- `evaluate_audit` exact-checks its string and numeric record/row leaves before
  field-built reconstruction;
- the original active `audit_id.__str__` canary now returns `INCOMPLETE`, leaves
  the protected row unchanged, and invokes no hook;
- `resolve_acquisitions` exact-checks its outer list/tuple before iteration, so
  the original hostile list iterator remains untouched;
- a rejected `ProbeResult` subclass is no longer dereferenced through its
  instance `__getattribute__`; and
- all 152 declared tests, focused Ruff, and commit-local diff checks pass.

Preserve these changes. The public helper and the claimed no-callback diagnostic
boundary remain incomplete.

## Findings

### P1: exact public-helper rows still retain active scalar leaves

`resolve_acquisitions` at `drift_gate.py:811-870` exact-checks only its outer
container. Its comprehension at lines 827-828 field-copies exact rows without
checking their leaves, and line 834 then calls `.strip()` on the copied
`evidence_ref`. Resolver identity and version are likewise copied at lines
825-826 and `.strip()` is called on them at lines 852-853 without exact-type
validation.

A fresh exact-commit canary used an exact `list`, an exact `ProbeResult`, and
only a `str` subclass in `evidence_ref`. The stored string value was empty, but
its `.strip()` returned a valid locator:

```text
ordinary exact row     receipt=rejected
active scalar leaf     receipt=resolved  strip calls=1  resolver calls=1
```

The resolver received the active scalar by identity. A second canary put an
active `str` in an exact binding's `resolver_id`; its `.strip()` raised and
escaped the public helper. The outer-container fix therefore closes one entry
protocol but does not enforce the same row/leaf/binding boundary as the main
evaluator.

The helper also silently filters non-exact rows and returns `{}` for a
non-exact container. That is non-authorizing, but it is not the documented
"every acquisition exactly once" typed receipt contract and is
indistinguishable from a valid batch containing no acquisition rows.

### High: the exact-leaf scan omits all three enum fields

`_check_probe` at `drift_gate.py:1197-1215` checks strings and integers but does
not check `verdict_class`, `evidence_type`, or optional
`continuity_provenance`, despite the boundary comment claiming exact enum
leaves. Those objects survive into the canonical row. The downstream validator
then formats malformed values with `!r` at lines 530-542.

An exact `ProbeResult` carrying an active object in `verdict_class` passed the
new boundary; its `__repr__` ran during validation and escaped as
`RuntimeError`. This violates the total-schema promise that malformed external
data yields `INCOMPLETE`, never an exception.

### High: diagnostics and resolver result handling still format caller objects

The new comments at `drift_gate.py:1178-1183` call `type(obj).__name__` safe.
It is not inert when the caller's class uses a custom metaclass: `__name__`
lookup dispatches through that metaclass. An `audit_id` string subclass with an
active metaclass raised from `_leaf` at line 1189 instead of returning
`INCOMPLETE`. This corrects the reviewer's own v11 recommendation: a dynamic
type name is not a safe rejection fact unless lookup explicitly bypasses the
metaclass. The simpler repair is to omit dynamic type names entirely.

The same class of issue remains after the intentional resolver callback:

- line 861 formats both `type(exc).__name__` and `{exc}`, invoking metaclass and
  exception `__str__` hooks; and
- line 870 formats a non-boolean result with `!r`, invoking its `__repr__`.

Fresh governed canaries made each path escape as `RuntimeError`, although the
module contract says resolver exceptions and non-boolean returns become typed
error receipts.

## Required Correction

1. Use one exact, non-dispatching `ProbeResult` leaf checker in both
   `evaluate_audit` and `resolve_acquisitions`. Include exact
   `VerdictClass`, `EvidenceType`, and optional `ContinuityProvenance` fields.
2. In the public helper, exact-check `EvidenceResolverBinding` plus exact string
   identity/version before copying or calling `.strip()`. Do not silently drop
   invalid rows; either return a structured batch-boundary error or make the
   canonical-only worker private and expose a total checked wrapper.
3. Use constant rejection/error text, positional indices, and trusted schema
   names. Do not format caller values, exception values, callback results, or
   dynamically resolved caller type names.
4. Add regressions for the active evidence-ref leaf, active resolver identity,
   omitted active enum leaf, active metaclass type name, resolver exception
   `__str__`, and non-boolean result `__repr__`. Every hook counter must remain
   zero; no invalid acquisition may produce a resolved receipt.

## Verification

- focused pytest -> `152 passed in 0.54s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- prior active audit-id canary -> `INCOMPLETE`, hook count zero, row unchanged
- prior active helper-container canary -> empty receipts, iterator count zero
- prior rejected-row canary -> typed `INCOMPLETE`, no instance dereference
- active helper scalar canary -> changed `rejected` to `resolved`
- active resolver identity canary -> escaped as `RuntimeError`
- omitted enum-leaf canary -> active `__repr__` escaped as `RuntimeError`
- active metaclass diagnostic canary -> `__name__` hook escaped as `RuntimeError`
- resolver exception/result canaries -> `__str__`/`__repr__` escaped as
  `RuntimeError`

## Disposition

`f2edb87` is `CHANGES / P1`. Preserve its removal of conversion coercions,
exact evaluator scalar checks, safe outer-container gate, and removal of
instance dereferences. Keep #168 open and non-deployable until an immutable
successor applies the same exact boundary to every row/enum/resolver leaf and
uses constant, non-dispatching failure records. Policy/math/custody repairs
accepted before v12 remain accepted. Judge-chain, origin-custody, slow-leak,
disposition-calibration, and operational deployment holds remain separate.
