# Baseline Drift Gate v25 Review

**Date:** 2026-07-16
**Reviewer:** Codex
**Target:** `6e0e01e3ba32208a4b49dbf8a73f2b93b5509b05`
**Direct parent:** `4f5b954238e6c72acc29893c937da5abbebdcd9e`
**Predecessor implementation:** `994e25c5f6a08d37235f8e032d03ba820332c4df`
**Prior review canon:** `a910caf`
**Implementation blob:** `59fca075403660be00d1b5ae4ff7ed7931b9eccf`
**Test blob:** `0925f0b067aaf0f6a907600c2fb205aa6072adf3`

**Verdict:** `CHANGES / P2` (resolver P1 remains closed)

## Scope And Provenance

The immutable `6e0e01e` delta contains only `drift_gate.py` and
`tests/test_drift_gate.py`. Current `HEAD` adds a separate handoff commit; both
reviewed blobs still match the target exactly. The review compares the v25
implementation delta to its direct parent and uses `a910caf` as the correction
canon.

## Accepted Repairs

`validate_history_chain` now preflights initialized slots across the complete
exact record graph: current and historical outer records, both probe lists,
and discontinuity events. It returns structural issues before ID, chronology,
linkage, or digest work. The new mid-history 14-slot probe matrix, current
nested probe matrix, and historical-root four-slot discontinuity matrix pass.
The three v24 nested-history canaries are closed.

The direct completeness, history, and digest contracts now state their actual
canonical-value domain. Foreign initialized values and wrong containers are
explicitly outside that direct surface and may raise; authoritative full
evaluation still rejects them at its exact-type boundary before snapshot or
digest. The public-facing domain correction is sound, subject to the remaining
private `_canon` wording below.

Slots, the plain-local `_resolve_fn`, strict direct/full class-descriptor
closure regressions, and the explicit CPython non-TEE/process-isolation
boundary remain intact. No resolver-substitution or overall-PASS escape was
reproduced.

## Findings

### P2: receipts remain anchor-addressed rather than row-addressed

V25 replaces the shared empty key with `f"<malformed-row-{i}>"` at
`drift_gate.py:1038`. The generated value is an exact inert string, but it
shares the same dictionary namespace as caller-supplied exact-string anchors.
Anchor validation requires only a nonempty string, so the generated key is a
valid caller anchor. A later malformed or canonical row can overwrite the
first row's error receipt.

Fresh direct canaries reproduce both forms:

```text
deleted anchor + malformed anchor "<malformed-row-0>"
    2 rows -> 1 error receipt

deleted anchor + canonical anchor "<malformed-row-0>"; resolver returns True
    2 rows -> 1 resolved receipt
```

The second case erases the malformed error entirely. Two malformed rows with
the same usable anchor also remain `2 rows -> 1 error receipt`, because
malformed rows with a nonempty anchor still use that anchor directly. The new
test at `tests/test_drift_gate.py:2258` proves only that two deleted anchors at
different positions generate different strings; it does not prove those
strings are disjoint from caller anchors or that every malformed row retains
one receipt.

The same anchor-addressed design also loses canonical duplicate rows on the
authoritative full path. With two exact acquisition rows named
`duplicate-acq`, the first resolver result false and the second true, the
canary produced:

```text
callbacks       [first locator, second locator]
overall         incomplete (duplicate protected anchor)
published       one receipt: resolved for the second locator
verdict         duplicate-acq = growth
rejection lines []
```

The exact-type boundary admits both rows, completeness reports the duplicate,
and evaluation nevertheless resolves and scores them. The second write erases
the first rejection. This contradicts the module and helper claims that every
acquisition row resolves exactly once into custody evidence. Overall remains
`INCOMPLETE`, so no P1 or overall-PASS escape is reproduced, but the published
receipt, per-anchor verdict, and rejection evidence are incomplete on the full
path.

Use a genuinely row-unique receipt identity, preserving the diagnostic anchor
separately, or stop before resolver callbacks and scoring whenever duplicate
schema makes row identity ambiguous. Add regressions for canonical duplicate
anchors on the full path, generated-key collision with malformed and canonical
rows, and malformed duplicate usable anchors. Assert exact callback order,
input/receipt cardinality, statuses, rejection lines, and no erased error.

### P2: `_canon` still claims totality over every field value

The narrowed `audit_digest` and validator docs now permit foreign initialized
values to raise, and the new test explicitly pins that behavior. However,
`_canon` still calls itself "Total canonicalization" for "any field value" at
`drift_gate.py:393-395`. `_canon(Bomb())` dispatches `Bomb.__repr__` at `:404`
and raises. Narrow the helper doc to the same exact canonical leaf domain; the
current helper claim and the newly pinned direct behavior contradict each
other.

### P3: direct-test descriptions remain stale

`tests/test_drift_gate.py:1752-1756` still says the direct helper snapshots the
callable into a fresh binding. The accepted direct repair captures one checked
callable in plain local `_resolve_fn`; it does not create a fresh binding.
Update this description as required by the v24 canon. The separate full-path
wording at `:1876-1880` is accurate because `evaluate_audit` does construct a
private binding snapshot. The deletion-matrix description at `:2201-2210`
also says an unreadable anchor uses the empty key and then says it uses a
positional placeholder; remove the superseded empty-key sentence.

## Required Correction

1. Preserve the complete-graph early preflight, narrowed canonical-input
   contracts, slots, plain-local callable, strict direct/full closure tests,
   and non-TEE/process-isolation boundary.
2. Make receipt identity row-unique on direct and full paths, or refuse
   resolver/scoring work after duplicate-schema failure.
3. Add collision regressions that require exact callback and receipt
   cardinality, preserve rejection evidence, and forbid an error or rejection
   from being overwritten as resolved.
4. Narrow `_canon`'s remaining false totality claim.
5. Correct the stale test descriptions at lines 1756 and 2201-2210.

## Verification

- focused pytest: `189 passed in 0.41s`
- focused Ruff: clean
- target-local `git diff --check`: clean
- both target blobs match the pinned tree and current `HEAD`
- new nested-history deletion matrices: pass
- direct canonical-input contract canary: pass as documented
- two deleted anchors at distinct positions: two error receipts
- generated placeholder plus malformed colliding anchor: 2 rows -> 1 error
- generated placeholder plus canonical colliding anchor: 2 rows -> 1 resolved
- duplicate usable malformed anchors: 2 rows -> 1 error
- full canonical duplicate anchors: two callbacks -> one resolved receipt,
  `GROWTH`, no rejection line, overall `INCOMPLETE`
- `_canon` foreign value: raising `__repr__` escapes despite "any value" doc
- no implementation, model, GPU, Qdrant experiment, or live-gate change made

## Disposition

`6e0e01e` closes the nested-history finding and most contract-scope wording
without regressing any accepted P1 repair. It remains `CHANGES / P2` because
receipt custody is still anchor-addressed and lossy on direct and full paths,
and `_canon` retains the last false any-value totality claim. OpenCLAW #168
remains open and non-deployable.
Judge-chain discrimination, runner-origin custody, slow-leak detection,
disposition calibration, and operational launch holds remain independent and
unchanged.
