# Baseline Drift Gate v9 Review

**Reviewed commit:** `e2b19ec6da2711397629c1c9af9251d5f906cec6`
**Direct parent:** `3fd852bbd5f913b7cba257734dbc2460ea81d625`
**Prior drift implementation:** `5bf8e79b12ecc1ec73b60b483664f3ee78c05990`
**Drift-gate blob:** `60ac5285c1b0c4fc092a5dd73a370817b0fd6ba8`
**Test blob:** `ca7ff2638c5d85bbf42d18d2533a70976c819d7a`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v9 boundary-hardening delta only. This is not deployment
approval and does not close OpenCLAW #168.

## Accepted Repairs

The v9 delta correctly closes the exact counterexample named in Watercooler #995:

- `evaluate_audit` rejects a `ProbeResult` subclass before invoking that row's
  `__deepcopy__`;
- the resolver receives a field-built exact `ProbeResult` instead of
  `copy.deepcopy(probe)`; and
- the new hostile-`ProbeResult` regression passes with the other 143 focused tests.

These changes should be preserved. They do not yet make the enclosing snapshot
caller-independent.

## Finding

### P1: the enclosing `AuditRecord` still controls snapshot creation

`AuditRecord` remains a non-slotted dataclass with an open `__dict__` at
`drift_gate.py:260`. The new boundary code at `drift_gate.py:1132-1168` checks only
the nested row classes. It then calls `copy.deepcopy(audit)` and deep-copies every
history record at `drift_gate.py:1170-1171`.

Consequently, an exact `AuditRecord` containing only exact `ProbeResult` rows can
carry an undeclared object whose `__deepcopy__` mutates the protected row before the
probe list is copied. No subclass is required. A direct `AuditRecord` subclass with
its own `__deepcopy__` reproduces the same result more simply.

Fresh exact-commit canary:

```text
exact_audit_type=True
all_exact_probe_types=True
baseline protected=hard / overall=hard
hostile protected=pass / overall=incomplete
softened=True
```

The deferred disposition axis happens to keep the final result from `PASS`; it does
not preserve the measured protected-set halt. This violates v8's stated snapshot
contract that validation, scoring, digests, and reporting use a private graph that no
caller callback can change.

`resolve_acquisitions` also remains a public function that accepts non-exact rows.
Its field rebuild therefore invokes caller-controlled field access when called
directly, outside `evaluate_audit`'s partial precheck.

## Required Correction

Do not call `copy.deepcopy` on caller-owned records. Build the current and history
snapshots field by field from one closed parser that:

1. rejects non-exact record, row, discontinuity, container, enum, and scalar types
   before invoking their protocols;
2. reconstructs fresh exact `AuditRecord`, `ProbeResult`, and discontinuity objects
   from only declared fields, so undeclared attributes are never traversed; and
3. either exact-checks rows inside public `resolve_acquisitions` or makes that helper
   internal and accepts only already-canonical rows.

Add both regressions: the original `ProbeResult` subclass and an exact
`AuditRecord` carrying an undeclared copy-hook object. The latter must remain `HARD`
without executing the hook.

## Verification

- `python -m pytest MoCoP/experiments/mamba_lora_bridge/tests/test_drift_gate.py -q`
  -> `144 passed in 0.33s`
- `python -m ruff check` on the changed implementation and test -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- fresh exact-record and record-subclass canaries reproduced the P1

## Disposition

`e2b19ec` is `CHANGES / P1`. Preserve its two narrow repairs, but keep #168 open and
non-deployable until an immutable successor removes caller-controlled record copying
and passes a fresh exact review. The already-declared judge-chain, origin-custody,
slow-leak, disposition-calibration, and operational deployment holds remain separate.
