# Baseline Drift Gate v11 Review

**Reviewed commit:** `f1417be03c6aed489a59ec3355c3327581f64adc`
**Direct parent:** `2e45d31ae55cd3a632150c4d04eca26834ec1fe1`
**Prior drift implementation:** `5f5d331f28e0c795ecca56d104f291fe3115ceb6`
**Drift-gate blob:** `4f561d0aacc3ed68c37561cfc6c0c996aafa8f19`
**Test blob:** `b5f4dfbe1b8726807b9d9bd12b79ceba90f7fcbd`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v11 boundary delta only. This is not deployment approval
and does not close OpenCLAW #168.

## Accepted Repairs

V11 closes the two active-container counterexamples from the v10 review:

- `history` must be an exact `list` or `tuple` before enumeration;
- each record's `probe_results` and `slot_probe_results` must be an exact
  `list` before row access;
- fresh canaries confirm that rejected row/history container subclasses return
  `INCOMPLETE` without invoking their `__iter__` hooks;
- the stale deep-copy documentation and unused test import are repaired;
- `copy` is absent from the module; and
- all 149 declared tests and focused Ruff pass.

Preserve these changes. The new scalar and public-helper repairs do not yet
implement the claimed inert boundary.

## Findings

### P1: scalar "coercion" executes caller code before the row snapshot

`_coerce_str`, `_coerce_int`, and `_coerce_float` at
`drift_gate.py:755-768` call `str(v)`, `int(v)`, or `float(v)` on accepted
subclasses. Those conversions dispatch the subclass's conversion hook. In
`_canonical_audit`, `audit_id` is coerced at line 815 before the protected rows
are rebuilt, so the hook can mutate a row reference that the later list
comprehension will snapshot.

A fresh exact-commit canary used an exact `AuditRecord`, exact lists, exact
`ProbeResult` rows, and only a `str` subclass in `audit_id`. Its `__str__`
changed `name` from `ABSENT/-1` to `PRESENT_RECOVERABLE/2`:

```text
ordinary audit       protected=hard overall=hard
active audit_id      protected=pass overall=incomplete  __str__ calls=1
```

The deferred disposition axis prevents final `PASS`, but the measured halt is
erased. Conversion is protocol dispatch, not inert canonicalization. The new
float regression overrides arithmetic/comparison operators but not `__float__`,
so it does not exercise this boundary.

### P1: public `resolve_acquisitions` can mint a resolved receipt through `__iter__`

`resolve_acquisitions` at `drift_gate.py:826-840` remains a public boundary.
It evaluates `list(probes)` before constraining the caller's container and then
canonicalizes whatever the iterator yielded. A fresh canary passed a list
subclass whose `__iter__` changed an empty acquisition locator into a valid one.
The identical exact row was `rejected` through an ordinary list, but the active
list produced `resolved` and invoked the resolver:

```text
ordinary list        receipt=rejected
active list          receipt=resolved  __iter__ calls=1  resolver calls=1
```

This is an authorization change at the receipt source of truth. The same
function also calls `str()` on resolver identity/version at lines 838-839
before validating them, exposing another conversion callback.

### High: rejected row subclasses are dereferenced while formatting rejection

The row type gate correctly notices a non-exact `ProbeResult`, but its error
message calls `getattr(_p, "anchor", "?")` at lines 1211 and 1223. A rejected
row subclass whose `__getattribute__` raises therefore escapes the declared
typed `INCOMPLETE` path:

```text
evaluate_audit(...) -> RuntimeError: caller hook ran
```

The authority contract says malformed external data yields `INCOMPLETE`, never
an exception, and the local comment promises rejection before caller protocol
dispatch. Diagnostics must not dereference an object already known to be of a
forbidden type.

## Required Correction

1. Validate every scalar leaf by exact type before conversion. Do not call
   `str`, `int`, `float`, formatting, hashing, comparison, or other protocols on
   a subclass. Normalize only values already proven to be exact built-ins.
2. Make `resolve_acquisitions` accept only an already-canonical private list, or
   enforce the same exact container, row, scalar, and resolver-binding boundary
   before any callback or conversion.
3. Format rejected-node diagnostics from inert facts only, such as container
   index and `type(node).__name__`; never read a field from the rejected node.
4. Add the three exact canaries above. Require the original `HARD` to remain,
   the direct receipt to remain rejected or return a typed boundary rejection,
   and every hostile hook counter to stay zero.

## Verification

- focused pytest -> `149 passed in 0.33s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- no `copy` import/use found in the module or focused tests
- v10 row/history container canaries -> `INCOMPLETE`, hook counters both zero
- active scalar canary -> softened `HARD/HARD` to `PASS/INCOMPLETE`
- direct acquisition-container canary -> changed `rejected` to `resolved`
- rejected-row diagnostic canary -> escaped as `RuntimeError`

## Disposition

`f1417be` is `CHANGES / P1`. Preserve the exact container gates, documentation
cleanup, and field-built declared records, but keep #168 open and non-deployable
until an immutable successor removes conversion dispatch, closes the public
receipt boundary, and makes type rejection total. Policy/math/custody repairs
accepted before v11 remain accepted. Judge-chain, origin-custody, slow-leak,
disposition-calibration, and operational deployment holds remain separate.
