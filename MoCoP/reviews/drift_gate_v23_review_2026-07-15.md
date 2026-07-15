# Baseline Drift Gate v23 Review

**Date:** 2026-07-15
**Reviewer:** Codex
**Target:** `67544ef4501143d9719eda19f127ecc2b66d8683`
**Direct parent:** `0a2360e4535dcb34e1ce919a1e2f162df8c476de`
**Predecessor implementation:** `e7f0a49d74b99a3f7c8180611083e2193c04022c`
**Prior review canon:** `7a62337`
**Implementation blob:** `ee31dd414af9478bb56beb9740381533fa9369a3`
**Test blob:** `d8ea0e138a511a1ae8f44e9a14a055e5b26c630a`

**Verdict:** `CHANGES / P2` (`#1053` P1 closed)

## Scope And Provenance

The target is a direct child of the v22 continuity commit. Its reviewable delta
contains only `drift_gate.py` and `tests/test_drift_gate.py`. The unrelated
working-tree deletions under the World Model Phase 2 result bundles were not
read as part of the target, modified, restored, staged, or tested.

## Accepted Repair

The v22 false-growth path is closed. `_resolve_acquisitions` captures the
validated resolver callable in `_resolve_fn` before the first callback and
invokes that plain local for every canonical acquisition row. It no longer
rereads `snapped.resolve` through a mutable class descriptor.

A fresh full-evaluator two-row canary had the first resolver call replace
`EvidenceResolverBinding.resolve` with a property returning an always-true
replacement, then return `False`. The result was:

```text
calls                         original(acq1), original(acq2)
acq1 receipt                  rejected / resolver:original / v1
acq2 receipt                  rejected / resolver:original / v1
replacement calls             0
```

The direct regression and focused suite also pass. The slotted input graph and
all repairs accepted through v22 remain intact. There is no reproduced P1
false-growth path inside the bounded local-callable model.

## Findings

### P2: the required closure proof and non-TEE boundary are still absent

The v22 review required both direct and full two-row regressions with exact
original-callable identity, two rejected receipts, and no `GROWTH`. V23 adds
only the direct helper test at `test_drift_gate.py:1659-1691`, and that test is
weaker than the required invariant:

- its first row deliberately resolves rather than requiring two rejections;
- `all(src == "original" for ...)` does not require exactly two calls;
- `receipts.get("acq2", None) is None or ...` explicitly permits the second
  receipt to disappear; and
- it never runs `score_protected_set` or full `evaluate_audit`, so it does not
  pin absence of `GROWTH` on either published path.

The manual full canary passes today, but the repository does not preserve that
proof. Replace the permissive assertions with exact call-order, exact receipt
keys/statuses, and verdict assertions, then add the same canary through
`evaluate_audit`.

The second required stopping rule is also missing. Neither the kernel nor the
authority model in `DRIFT_GATE_PREREQS_2026-07-12.md:292-321` states that
arbitrary in-process module/class/function/bytecode mutation is outside the
kernel's threat model, or that an untrusted resolver must be process-isolated.
Without that boundary, this patch can be misread as interpreter-integrity
proof and the snapshot-hardening loop has no principled end.

The stale `_resolve_acquisitions` prose compounds the ambiguity:
`drift_gate.py:885-886` and `:910-912` still claim that a fresh frozen binding
holds the callable, although v23 intentionally removed that mechanism.

### P2: malformed direct-helper handling remains partial

`_probe_leaves_exact` now catches a missing probe slot, but its caller
immediately rereads `p.anchor` and `p.evidence_type` outside that catch at
`drift_gate.py:899-902`. Exact slotted probes with either field deleted still
escape `_resolve_acquisitions` as `AttributeError`; the new catch only makes
the other deleted fields return an error receipt.

The wider direct-helper totality issue from v22 is unchanged:

- `audit_digest` still claims "Total over malformed input: never raises" at
  `drift_gate.py:375-376`, but an uninitialized audit and every one of the
  eight single audit-slot deletions raise `AttributeError`;
- `validate_history_chain([], object.__new__(AuditRecord))` still raises; and
- direct `validate_audit_completeness` raises for 12 of 14 single deleted
  probe slots and silently returns normally for deleted `reframe_notes` and
  `smoke_result`.

The authoritative `evaluate_audit` boundary rejects the same malformed graph
before these helpers, so this is not the closed P1 false-growth issue. It is a
documented/API contract mismatch. Either make the direct functions total over
their advertised inputs or declare them canonical-only/private and narrow the
claims. Commit the complete deletion matrices so that decision remains
executable rather than reviewer-local.

## Required Correction

1. Preserve the plain-local `_resolve_fn`; do not restore a per-row descriptor
   read.
2. Strengthen the direct class-replacement test to require exactly two original
   calls, two present rejected receipts, and no growth; add the same full
   `evaluate_audit` regression.
3. State the CPython non-TEE boundary in the authority contract and kernel:
   arbitrary interpreter-authority mutation is out of scope; untrusted
   resolver execution requires process isolation.
4. Totalize the documented direct digest/completeness/history/resolver paths,
   or explicitly make them canonical-only/private and correct their claims.
5. Commit complete audit/probe/discontinuity/binding deletion matrices and
   remove the stale fresh-frozen-binding wording.

## Verification

- focused pytest: `173 passed in 0.48s`
- focused Ruff: clean
- commit-local `git diff --check`: clean
- both target blobs match the pinned commit tree
- direct class-descriptor regression: pass
- independent full class-descriptor canary: original called twice, two
  rejected receipts, replacement never called
- `_resolve_acquisitions` single-slot matrix: missing `anchor` and
  `evidence_type` raise; the other 12 cells return
- direct completeness single-probe-slot matrix: 12 raise, 2 return without a
  missing-field issue
- direct digest single-audit-slot matrix: 8 of 8 raise
- no implementation, model, GPU, Qdrant experiment, or live-gate change made

## Disposition

`67544ef` closes the v22 P1 and should be preserved. The exact packet remains
`CHANGES / P2` until its proof, threat boundary, and documented malformed-input
surface match the already-frozen closure contract. OpenCLAW #168 remains open
and non-deployable. Independent judge-chain discrimination, runner-origin
custody, slow-leak detection, disposition calibration, and operational launch
holds are unchanged.
