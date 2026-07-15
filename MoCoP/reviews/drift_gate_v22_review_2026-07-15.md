# Baseline Drift Gate v22 Review

**Reviewed commit:** `e7f0a49d74b99a3f7c8180611083e2193c04022c`
**Direct parent:** `f700a0e4a5264798af95d7f251c97cee148f4d93`
**Prior drift implementation:** `914089a130f2af687a82bdc09afb357570a6d94e`
**Prior review canon:** `f0cc08f79022287ae4ffac6dd97d408fe9deb0b4`
**Drift-gate blob:** `e770a2cdd5bf52369520fe7eaa195bb31000e5f9`
**Test blob:** `651049cfe57f00c0f5c610be05fb6283e33365a9`
**Reviewer:** Codex
**Date:** 2026-07-15
**Verdict:** `CHANGES / P1`
**Scope:** model-free v22 slotted-record and resolver-snapshot delta only.
This is not deployment approval and does not close OpenCLAW #168.

## Accepted Repairs

V22 closes the v21 instance-storage finding by construction:

- `ProbeResult`, `DiscontinuityEvent`, `AuditRecord`, and
  `EvidenceResolverBinding` are all slotted caller-input records;
- none exposes `__dict__`, and `object.__setattr__(obj, "__dict__", ...)`
  raises before installing attacker storage;
- undeclared keys, dictionary subclasses, class-default fallback, and active
  dictionary key equality are no longer available on the input graph;
- all eight `AuditRecord`, fourteen `ProbeResult`, four
  `DiscontinuityEvent`, and three `EvidenceResolverBinding` slot-deletion
  canaries return typed full-gate failures or resolver errors; and
- all earlier exact-container, exact-leaf, receipt, chain, and ordinary
  instance-mutation protections remain intact.

All 172 declared tests, focused Ruff, commit-local diff checks, and pinned
blobs pass. The direct parent includes the v21 review/continuity commits, but
its Drift Gate blob is exactly v21's `91cfc61...`; there is no intervening
implementation drift.

## Findings

### P1: the slotted resolver snapshot rereads a mutable class descriptor per row

`_resolve_acquisitions` validates `resolver.resolve`, constructs a fresh
slotted `EvidenceResolverBinding`, and then calls `snapped.resolve` inside the
row loop at `drift_gate.py:963`. With a slotted class, `resolve` lives behind a
class member descriptor. Python permits replacing that descriptor on the class
even though the instance is frozen and has no dictionary.

A fresh two-acquisition canary used an original resolver that rejects both
locators. On its first call it assigned a replacement function to
`EvidenceResolverBinding.resolve`, then returned `False`. The results were:

```text
calls                         original(acq1), replacement(acq2)
acq1 receipt                  rejected / resolver:original / v1
acq2 receipt                  resolved / resolver:original / v1
acq2 verdict                  GROWTH
published resolver            resolver:original / v1
type_rejection                absent
```

The same substitution reproduces through both the direct private helper and
full `evaluate_audit`. It directly contradicts the helper's line 882-883 claim
that the callable is snapshotted so a callback cannot swap it mid-batch, plus
the full-evaluator snapshot comments at lines 1445-1449. The slot migration
made this particular class-level substitution effective because replacing the
member descriptor hides the stored slot value.

Capture the checked `r_fn` into a plain local before the first callback and
invoke that local on every row; do not reread it through any binding instance
or class descriptor. Add the same direct/full two-row canary and require the
original callable twice, two rejected receipts, and no `GROWTH`.

This should be the last in-process object-authority hardening step, not an
implicit TEE claim. After the local capture, explicitly scope arbitrary
module/class/function/bytecode replacement outside the kernel's non-TEE threat
model, consistent with the reviewed P5 boundary, or isolate untrusted resolver
execution in a separate process. Without that line, arbitrary callback code can
always mutate further interpreter authority and no finite snapshot patch series
can prove resistance.

### Medium: direct helper totality remains broader than its implementation

The slot migration makes the authoritative `evaluate_audit` boundary total for
the replayed missing-field graph. The public helpers still advertise or imply
broader malformed-input handling than they implement:

- `audit_digest` at line 368 says it is total over malformed input, but an
  uninitialized audit, a deleted audit slot, or a deleted discontinuity slot
  raises `AttributeError`;
- direct `validate_history_chain([], object.__new__(AuditRecord))` raises while
  formatting `audit_id`; and
- direct `validate_audit_completeness` raises on a probe with a deleted slot.

Either route those public helpers through the same checked canonical boundary,
or mark them private/canonical-only and narrow the module/docstring claims.
The test refactor also retains only one audit-slot deletion cell and removes
the committed discontinuity-custody deletion cell, although the complete
manual matrices pass. Parameterize the full matrices. The stale line 848
comment still calls the private resolver helper a public path.

## Required Correction

1. Capture the checked resolver callable in a plain local and call that exact
   local for every acquisition row; never reread a class/instance descriptor
   after callbacks begin.
2. Add direct and full two-row class-descriptor substitution regressions and
   require original-callable identity, two rejected receipts, and no growth.
3. Freeze the non-TEE boundary explicitly: arbitrary interpreter-authority
   mutation is out of scope unless resolver execution is process-isolated.
4. Make direct digest/completeness/history helpers total over their documented
   inputs or declare them canonical-only/private and correct their claims.
5. Commit complete audit/probe/discontinuity/binding deletion matrices and
   remove stale public-path wording.

## Verification

- focused pytest -> `172 passed in 0.38s`
- focused Ruff -> clean
- commit-local `git diff --check` -> clean
- both committed blobs matched the pinned tree
- all four caller-input node types -> no `__dict__`; replacement refused
- all 8/14/4/3 slot-deletion matrices -> typed full/direct outcomes
- v21 dictionary-subclass and active-key attacks -> unavailable by construction
- old public resolver symbol -> absent
- first resolver callback replaces slotted class descriptor -> second row calls
  replacement, receipt `resolved`, verdict `GROWTH`, original identity retained
- uninitialized/deleted-slot direct digest -> uncaught `AttributeError`
- uninitialized direct history and deleted-probe direct completeness -> uncaught
  `AttributeError`

## Disposition

`e7f0a49` is `CHANGES / P1`. Preserve the slotted input graph, slot-presence
checks, removal of dictionary-specific infrastructure, and every repair
accepted through v21. Keep #168 open and non-deployable until the resolver loop
uses one local callable and the code states its non-TEE boundary honestly.
Direct-helper totality and regression-matrix cleanup remain required but are
secondary. Judge-chain, origin-custody, slow-leak, disposition-calibration, and
operational deployment holds remain separate.
