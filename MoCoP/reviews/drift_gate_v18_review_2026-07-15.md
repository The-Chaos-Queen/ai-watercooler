# Baseline Drift Gate v18 Review

**Reviewed commit:** `5e7d5d800b083a75922b6aad943822dd5eb112c1`
**Direct parent:** `30016a9bb7da096884745949d94eef068a3ea4e9`
**Prior drift implementation:** `9596737b87ae7e3bb7c03d88c20589370c8eb3ab`
**Prior review canon:** `cd6749a0e37e835fd2cdc5a9c3529e63a85fabba`
**Drift-gate blob:** `cc11680ad1075485b4f1f7097eeffd330ad8983e`
**Test blob:** `0fc4dea45f7a7e468b7d3428abf4e47058e9c14f`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v18 resolver-helper and boundary-totality delta only. This
is not deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V18 closes the callable substitution on both exercised resolver paths:

- `evaluate_audit` retains its fresh identity/version/callable snapshot;
- `_resolve_acquisitions` independently builds a fresh binding before the row
  loop, so a direct caller's first callback cannot replace the callable used for
  the second row;
- the direct two-row canary now calls the original resolver twice, rejects the
  second row, and does not produce a second resolved receipt;
- direct whitespace and wrong-typed identities now produce stable `error`
  receipts with `non-empty` or `exact str` reasons; and
- all 165 declared tests, focused Ruff, commit-local diff checks, and pinned
  blobs pass.

Preserve these repairs. Exact type still does not establish that required
dataclass fields exist, full evaluation still demotes malformed-bound to
unbound receipts, and the helper remains public through an exact alias.

## Findings

### P1: exact but uninitialized or field-deleted records escape as AttributeError

The boundary repeatedly treats `type(obj) is ExactDataclass` as proof that all
dataclass fields exist. Python does not provide that guarantee:
`object.__new__(ExactDataclass)` creates an exact uninitialized instance, and
`object.__delattr__` removes fields even from a frozen dataclass.

Resolver field reads at `drift_gate.py:889-900` and `1404-1417` occur outside a
typed missing-field guard. Fresh canaries produced uncaught `AttributeError` on
both direct and full paths for:

```text
object.__new__(EvidenceResolverBinding)  missing resolver_id
exact binding after delattr(resolve)     missing resolve
```

The same false exact-type assumption exists in the advertised total closed
schema gate. Fresh full-evaluator canaries also escaped on:

```text
object.__new__(AuditRecord)              missing audit_id
object.__new__(ProbeResult)              missing anchor
object.__new__(DiscontinuityEvent)       missing event_ref
```

These are exact classes with no subclass, metaclass, conversion, iteration, or
formatting hook. The gate promises `INCOMPLETE` for total-schema violations and
typed resolver errors, not exceptions. A malformed record can therefore abort
the decision publication path instead of producing a fail-closed artifact.

Use one descriptor-direct field reader that catches missing exact fields and
records a constant typed issue without invoking caller formatting. Apply it to
every required field of `AuditRecord`, `ProbeResult`, `DiscontinuityEvent`, and
`EvidenceResolverBinding`; return before canonicalization when any field is
missing. Exact type is necessary but not sufficient shape validation.

### High: full evaluation still writes malformed bound resolvers as unbound

V18 corrects direct helper receipts, but `evaluate_audit` still passes
`_resolver_snapshot=None` whenever its binding validation fails. With an actual
acquisition row, both full-evaluator cases remain:

```text
whitespace id   unbound / no evidence resolver bound
wrong-type id   unbound / no evidence resolver bound
```

The same outcome also contains the new malformed-binding incomplete reason, so
its receipt contradicts the evaluator. The v18 regressions exercise only the
direct helper; the existing full-evaluator malformed-binding tests contain no
acquisition row.

Carry a typed binding error into `_resolve_acquisitions`, or pass the rejected
binding through its now-safe validation path. Reserve `unbound` exclusively for
literal `resolver is None`; malformed bound state must create `error` receipts.

### High: alias preservation means the helper was not privatized

Line 947 exports `resolve_acquisitions = _resolve_acquisitions`. The exact same
callable therefore remains importable under the previous public name, and the
test module still imports and invokes that public alias. Repository search found
no production caller that requires compatibility; only the test suite and
historical reviews use the old name.

Consequently, the v15 invalid-batch finding remains live. Fresh calls through
the alias still return `{}` for a non-exact outer list, a row subclass, and an
exact row with malformed `evidence_type`. Renaming the definition while
retaining a public alias changes no boundary behavior.

Choose one real disposition:

- remove the alias, update tests to import `_resolve_acquisitions`, document the
  helper as canonical-only, and keep all external entry through the total
  evaluator gate; or
- retain a public function and return a typed batch result covering unkeyable
  container, row, and leaf errors.

### Medium: regressions omit the paths that still fail

The new direct tests correctly cover callable replacement and two binding-field
validation cases. They do not cover acquisition-bearing malformed bindings
through `evaluate_audit`, exact uninitialized or field-deleted dataclasses, true
removal of the public alias, or typed handling of invalid batch shapes.

## Required Correction

1. Make every exact-record field read total. Exact uninitialized and
   field-deleted bindings, audits, probes, and discontinuity events must produce
   constant typed errors/`INCOMPLETE`, never escape.
2. Preserve malformed-bound state through full-evaluator acquisition receipts;
   never translate it into `resolver is None` or `unbound`.
3. Actually privatize the helper by removing the public alias and updating
   tests/callers, or retain a public typed batch result that represents every
   invalid shape.
4. Add regressions for `object.__new__` and `object.__delattr__` across all four
   exact record types, acquisition-bearing full-evaluator malformed bindings,
   and the chosen private-or-typed public boundary.

## Verification

- focused pytest -> `165 passed in 0.38s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- full and direct callable swap -> original called twice; second row rejected
- direct whitespace/wrong-type binding -> typed error receipt
- full whitespace/wrong-type binding with acquisition -> receipt remains
  `unbound / no evidence resolver bound`
- exact uninitialized/deleted-field binding -> `AttributeError` on direct and
  full paths
- exact uninitialized audit/probe/discontinuity -> `AttributeError` from full
  boundary gate
- public alias is the private function by identity; invalid outer container,
  row class, and evidence-type leaf still return `{}`

## Disposition

`5e7d5d8` is `CHANGES / P1`. Preserve both callable snapshots, direct typed
binding errors, and all earlier repairs. Keep #168 open and non-deployable until
exact-but-missing record fields fail closed, full receipts distinguish malformed
bound from unbound, and the resolver helper is genuinely private or provides a
typed total public batch contract. Policy/math/custody repairs accepted before
v18 remain accepted. Judge-chain, origin-custody, slow-leak,
disposition-calibration, and operational deployment holds remain separate.
