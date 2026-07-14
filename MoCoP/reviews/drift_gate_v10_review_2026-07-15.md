# Baseline Drift Gate v10 Review

**Reviewed commit:** `5f5d331f28e0c795ecca56d104f291fe3115ceb6`
**Direct parent:** `e1e97e233017ddb488e58bb2fe2f54ddd0791023`
**Prior drift implementation:** `e2b19ec6da2711397629c1c9af9251d5f906cec6`
**Drift-gate blob:** `33114368f59bb6bb0e86ab5c792d04fa2f880b33`
**Test blob:** `c890d3edb8e44ee86f6bea393a566dd4387f0ec7`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v10 canonical-snapshot delta only. This is not deployment
approval and does not close OpenCLAW #168.

## Accepted Repairs

V10 closes the enclosing-record counterexample from review `5d9d0f5`:

- `copy.deepcopy` is removed from the implementation;
- exact `AuditRecord`, `DiscontinuityEvent`, and `ProbeResult` subclasses are
  rejected in the declared current/history paths;
- `_canonical_audit`, `_canonical_discontinuity`, and `_canonical_probe` rebuild
  declared fields instead of traversing an exact record's undeclared `__dict__`;
- the prior exact `AuditRecord` with an undeclared copy hook now remains `HARD`, and
  the hook is not invoked; and
- all 146 declared tests pass.

These changes should be preserved. They do not yet implement the claimed closed
record-graph boundary.

## Findings

### P1: active containers execute before the type scan and canonical snapshot

`_check_record` at `drift_gate.py:1167-1191` exact-checks the record class, but then
iterates `rec.probe_results` and `rec.slot_probe_results` without first requiring
exact built-in lists. `evaluate_audit` likewise enumerates the caller-supplied
`history` sequence at line 1193 before constraining its container type. The canonical
rebuild at lines 1209-1210 therefore happens after those active protocols execute.

Two fresh exact-commit canaries independently softened the same protected halt:

```text
baseline                         protected=hard overall=hard
probe_results list subclass     protected=pass overall=incomplete
history sequence subclass       protected=pass overall=incomplete
```

In the first case, the current object was an exact `AuditRecord`, every nested row
was an exact `ProbeResult`, and only `probe_results` was a list subclass whose
`__iter__` changed `name` before yielding. In the second, the current record and all
of its fields used the ordinary declared containers; the history sequence's
`__iter__` changed the already-checked current row before `_canonical_audit` ran.

The deferred disposition axis again prevents final `PASS`, but the measured
protected-set halt is erased. Exact dataclass nodes do not make their active
containers inert.

### High: scalar and direct-helper boundaries from `5d9d0f5` remain open

The canonical builders at `drift_gate.py:754-801` copy caller field objects by
reference. They do not enforce exact strings, floats, integers, enums, optionals, or
exact row-list containers before reconstruction. The downstream schema still uses
`isinstance` for most string, enum, and numeric fields, so active subclasses can
survive into the supposedly canonical graph.

`resolve_acquisitions` at line 804 also remains a public function that accepts and
dereferences non-exact `ProbeResult` rows outside `evaluate_audit`'s partial gate.
This was an explicit required correction in `5d9d0f5`, not an optional hardening.

Use one total parser for both the full evaluator and any public helper. Either reject
non-exact leaves without invoking their protocols or reconstruct only from a
separately parsed inert wire representation.

### Minor: lint and snapshot documentation regressed

`test_drift_gate.py:1502` imports `copy as copy_mod` but never uses it, so focused
Ruff fails with `F401`. The module authority text and `evaluate_audit` docstring still
claim the inputs are "deep-copied exactly once" even though v10 intentionally removed
that mechanism. Update those claims to describe canonical reconstruction.

## Required Correction

Before any iteration, membership, conversion, comparison, hashing, formatting, or
copy protocol:

1. require an exact accepted history container and exact built-in row containers;
2. exact-check every declared record, discontinuity, row, enum, scalar, and optional
   leaf used by the decision;
3. reconstruct the full private graph only after that inert structural pass;
4. make `resolve_acquisitions` consume only canonical rows or enforce the same public
   boundary itself; and
5. add both active-container regressions, requiring `HARD` and proving the hooks were
   not invoked.

Remove the unused import and update the stale snapshot documentation in the same
successor.

## Verification

- focused pytest -> `146 passed in 0.32s`
- focused Ruff -> failed: one `F401` at `test_drift_gate.py:1502`
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- prior exact-record undeclared-hook canary -> `hook_called=False`, `HARD/HARD`
- fresh row-container and history-container canaries -> both softened
  `HARD/HARD` to `PASS/INCOMPLETE`

## Disposition

`5f5d331` is `CHANGES / P1`. Preserve its field-built record reconstruction, but keep
#168 open and non-deployable until an immutable successor closes the container and
leaf boundaries and passes fresh review. Policy/math/custody repairs accepted before
v10 remain accepted. Judge-chain, origin-custody, slow-leak, disposition-calibration,
and operational deployment holds remain separate.
