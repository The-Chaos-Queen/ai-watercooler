# Baseline Drift Gate v24 Review

**Date:** 2026-07-16
**Reviewer:** Codex
**Target:** `994e25c5f6a08d37235f8e032d03ba820332c4df`
**Direct parent:** `b0dedd2ab45a3494ee5169449cfa047d8eb9a2fa`
**Predecessor implementation:** `67544ef4501143d9719eda19f127ecc2b66d8683`
**Prior review canon:** `5becb0b`
**Implementation blob:** `0277b26662ca3492dbbcc0de1fc68a4ebf05d89b`
**Test blob:** `1a9da70a45f706f3abb1f99817ff77ba7412ad09`
**Prerequisite blob:** `e1d623aae1f6b9510586233def0cda3b4f907eaf`

**Verdict:** `CHANGES / P2` (resolver P1 remains closed)

## Scope And Provenance

`994e25c` is a direct child of the v23 continuity commit. Its immutable delta
contains only `drift_gate.py`, `tests/test_drift_gate.py`, and
`DRIFT_GATE_PREREQS_2026-07-12.md`. Later HEAD commits are separate Gemma and
handoff work; all three reviewed blobs still match the target exactly.

## Accepted Repairs

V24 preserves the slotted four-record graph and plain-local resolver callable.
The direct and full class-descriptor regressions now require exact two-call
order, both receipts present and rejected under the original resolver, and no
`GROWTH`. Both pass. The v22 resolver substitution P1 remains closed.

The CPython non-TEE stopping rule is now explicit in the module authority
model, `evaluate_audit`, and prerequisite A4: arbitrary interpreter-authority
mutation is outside this in-process kernel, and an untrusted resolver requires
process isolation. This correctly ends the snapshot-hardening loop.

The single-row missing-`anchor` and missing-`evidence_type` cases now return
typed error receipts. The committed outer audit/probe/discontinuity/binding
matrices pass, stale helper prose was corrected, and `audit_digest` is now
declared canonical-input-only instead of total over partial records.

## Findings

### P2: history totality preflights only the outer record, not its graph

`validate_history_chain` says deleted exact-record slots are returned before
any digest or linkage read at `drift_gate.py:762-765`. Its initial preflight at
`:769-779` checks only the eight outer `AuditRecord` slots. It then detects
nested row issues through `validate_audit_completeness`, appends a summary, and
continues into `audit_digest` at `:825` and `:840`.

Fresh exact-graph canaries show:

```text
mid-history ProbeResult deletion     14/14 -> uncaught AttributeError
historical root discontinuity        4/4   -> uncaught AttributeError
current nested probe deletion        returns [] (clean)
```

The committed matrices cover outer audit slots on historical/current records
and a discontinuity only on a no-history current root. They do not exercise a
partial nested row that is later digested, or a partial historical-root event.

Preflight the complete graph for every history record and the current record,
including discontinuities, and return accumulated schema issues before ID,
chronology, ordinal, or digest/linkage work. Add the 14-row historical/current
and four historical-discontinuity matrices. No partial record may reach
`audit_digest`.

### P2: the direct validator and digest claims remain broader than behavior

`validate_audit_completeness` says a validator reports and never raises at
`drift_gate.py:652`. Exact `ProbeResult`/`AuditRecord` instances with initialized
but malformed values still dispatch active hash or formatting protocols:

```text
probe.anchor = raising object         RuntimeError from __hash__
probe.band = raising object           RuntimeError from __repr__
audit.diversity_metric = raising obj  RuntimeError from __repr__
history audit_id = raising object     RuntimeError from __repr__
```

The new `audit_digest` contract also says value-level wrong types never raise
and `_canon` is total (`drift_gate.py:363-365`, `:409-415`). That is false for a
raising `__repr__`, and a fully initialized audit with `probe_results = 42`
raises `TypeError` during iteration.

The authoritative `evaluate_audit` exact-leaf boundary rejects these values
before validation/digest, so this is not a full-path P1. Either route the direct
APIs through that inert boundary, or narrow them precisely to an exact,
fully-initialized canonical record graph and remove the remaining totality and
wrong-value claims. Diagnostics on rejected values must not invoke caller
protocols if the broader total contract is retained.

### P2: unreadable anchors can still erase an acquisition receipt

V24 keys an unreadable acquisition anchor as `""` at
`drift_gate.py:988-1001`. Two exact acquisition rows with deleted `anchor`
slots therefore produce one error receipt: the second overwrites the first in
the receipt mapping. That contradicts the helper's `EXACTLY ONCE` statement and
the closure rule that receipt disappearance is forbidden. The single-row
14-field matrix cannot detect this cardinality failure.

Use deterministic non-colliding inert keys for unreadable anchors, or declare
the malformed direct batch outside the helper contract and stop claiming
total exactly-once custody there. Add a two-row missing-anchor regression that
requires two typed errors. The full evaluator already rejects either row at
its boundary, which bounds this to the private direct surface.

## Required Correction

1. Preserve slots, `_resolve_fn`, the strict direct/full substitution tests,
   and the explicit non-TEE/process-isolation boundary.
2. Preflight the complete history/current record graph and return before any
   linkage work; add nested probe and historical discontinuity matrices.
3. Preserve one distinct typed error receipt per malformed acquisition row,
   including multiple unreadable anchors, or narrow the direct contract.
4. Make direct completeness/history/digest behavior match its documented input
   domain; remove false totality/value-level claims if choosing canonical-only.
5. Remove the remaining stale direct-test wording that says a fresh binding,
   rather than the local callable, closes instance mutation.

## Verification

- focused pytest: `184 passed in 0.39s`
- focused Ruff: clean
- target-local `git diff --check`: clean
- all three target blobs match the pinned tree and current HEAD
- strict direct/full class-descriptor substitutions: pass, no `GROWTH`
- declared 8/14/4/3 single-deletion tests: pass
- mid-history nested probe deletion: 14/14 raise
- historical-root discontinuity deletion: 4/4 raise
- current nested probe deletion through direct history validator: clean return
- two missing-anchor acquisitions: 2 rows -> 1 error receipt
- active malformed-value completeness/history/digest canaries: uncaught caller
  protocol exceptions
- no implementation, model, GPU, Qdrant experiment, or live-gate change made

## Disposition

`994e25c` materially advances the packet and keeps every security-relevant P1
closed. It remains `CHANGES / P2` until the new direct totality/exactly-once
claims cover the complete nested graph and malformed batches, or are narrowed
honestly to canonical-only inputs. OpenCLAW #168 remains open and
non-deployable. Judge-chain discrimination, runner-origin custody, slow-leak
detection, disposition calibration, and operational launch holds remain
independent and unchanged.
