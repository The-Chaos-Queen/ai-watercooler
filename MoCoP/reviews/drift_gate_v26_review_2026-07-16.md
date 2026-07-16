# Baseline Drift Gate v26 Review

**Date:** 2026-07-16
**Reviewer:** Codex
**Target:** `60701ed7e609158482abcc9f8fef3d61214796f7`
**Direct parent:** `3cdf1d60ebf7223a1eb7604ffe98cd5e0a517d8a`
**Predecessor implementation:** `6e0e01e3ba32208a4b49dbf8a73f2b93b5509b05`
**Prior review canon:** `8e60019`
**Implementation blob:** `51fc1ee5c3c85db606a4e1feea2485be5c81068c`
**Test blob:** `f40734f9ca8c69347cf09c4860c33d75c98691b2`

**Verdict:** `CHANGES / P2` (resolver P1 remains closed)

## Scope And Provenance

The immutable `60701ed` delta contains only `drift_gate.py` and
`tests/test_drift_gate.py`. Current `HEAD` adds a separate handoff commit; both
reviewed blobs still match the target exactly. The review compares v26 to its
direct parent and uses `8e60019` as the correction canon.

## Accepted Repairs

V26 closes the v25 canonical duplicate-acquisition failure. Duplicate exact or
malformed acquisition anchors now fold into one typed duplicate-error receipt,
and no resolver callback runs for any row under that ambiguous receipt key.
The committed direct and full canaries prove zero callbacks, one error receipt,
a rejection line, no `GROWTH`, and overall `INCOMPLETE`. The former
`[False, True]` last-write-wins path is closed.

A canonical acquisition anchor equal to the first malformed placeholder now
survives alongside the malformed error: the placeholder extends with `#` until
it is outside the acquisition receipt-key set. The two deleted-anchor case and
malformed duplicate usable-anchor case also retain the declared fail-closed
semantics.

`_canon` now states totality only for canonical leaf values and explicitly
allows foreign `repr` to raise. The cited direct and full callable-swap prose
and the empty-key deletion-matrix wording are corrected. Complete-graph
preflight, slots, plain-local `_resolve_fn`, strict descriptor regressions,
and the CPython non-TEE/process-isolation boundary remain intact.

## Findings

### P2: placeholder reservation omits non-acquisition caller anchors

The new contract and test-class description say malformed placeholders are
chosen outside the caller-anchor namespace (`drift_gate.py:1055-1057`,
`tests/test_drift_gate.py:2323-2328`). The implementation builds
`anchor_counts` only from canonical acquisition rows and malformed rows treated
as acquisitions at `drift_gate.py:1058-1066`; `taken` therefore omits exact
anchors on canonical non-acquisition rows.

Fresh direct canary:

```text
row 0: acquisition with deleted anchor
row 1: canonical EvidenceType.NONE, anchor "<malformed-row-0>"

receipt keys  ["<malformed-row-0>"]
collision     true
rejection     "<malformed-row-0>: row has missing or non-exact scalar leaves"
```

The synthetic receipt is now indistinguishable by key from a real caller row,
and the rejection line names that caller anchor even though the error belongs
to the missing-anchor row. This is direct/private P2: full evaluation rejects
the malformed row at its exact boundary, and the canonical non-acquisition row
cannot use an error receipt to mint `GROWTH`. It does not reopen the resolver
P1, but it leaves the stated namespace-custody invariant and diagnostic join
ambiguous.

Reserve placeholders against every readable exact caller anchor in the input,
not only acquisition anchors. Add the `EvidenceType.NONE` shadow regression
and assert the synthetic receipt key differs from every readable input anchor.
Alternatively, narrow every claim to the acquisition receipt-key namespace and
use a separate non-anchor row identity for synthetic diagnostics.

### P3: duplicate-error report order is hash-seed dependent

`duplicated` is a set at `drift_gate.py:1065`, then is iterated directly at
`:1067`. With the same four duplicate anchors, five fresh processes produced:

```text
beta,delta,gamma,alpha
delta,gamma,alpha,beta
gamma,delta,beta,alpha
gamma,beta,alpha,delta
alpha,gamma,delta,beta
```

`receipts_digest` remains stable because it sorts receipt payloads, so this is
not a digest or decision escape. The observable receipt mapping,
`acquisition_rejected` list, and acquisition-error `incomplete_reasons` order
nevertheless vary for identical input. Emit duplicate receipts in deterministic
first-input or sorted-anchor order; the surrounding validator already sorts
diagnostic sets for this reason.

### P3: receipt documentation still assumes one row

`AcquisitionReceipt` still describes itself as the resolution record "for one
ACQUISITION row" at `drift_gate.py:361-364`. Under the accepted v26 duplicate
policy, one duplicate-error receipt deliberately represents N rows. State that
the record is per unique receipt key and can summarize a duplicate group.

## Required Correction

1. Preserve duplicate fail-closed folding, zero duplicate callbacks, no
   `GROWTH`, the rejection line, complete-graph preflight, slots, local
   callable, strict direct/full closure tests, canonical-input contracts, and
   the explicit non-TEE boundary.
2. Make every synthetic placeholder disjoint from all readable exact caller
   anchors, including non-acquisition rows, or give synthetic rows a separate
   non-anchor identity and narrow the contract consistently.
3. Emit multiple duplicate-error receipts in deterministic order.
4. Update `AcquisitionReceipt` documentation for per-key duplicate summaries.

## Verification

- focused pytest: `193 passed in 0.40s`
- focused Ruff: clean
- target-local `git diff --check`: clean
- both target blobs match the pinned tree and current `HEAD`
- direct/full duplicate acquisition canaries: zero callbacks, one error, no
  `GROWTH`; full overall `INCOMPLETE` with rejection line
- acquisition placeholder shadow: two receipts with exact resolved/error status
- non-acquisition placeholder shadow: synthetic key equals readable caller anchor
- four duplicate groups across five hash seeds: five publication orders
- no implementation, model, GPU, Qdrant experiment, or live-gate change made

## Disposition

`60701ed` closes the v25 false-`GROWTH` and rejection-loss path without
regressing any accepted P1 repair. It remains `CHANGES / P2` because the
placeholder reservation is narrower than its declared caller-anchor namespace,
leaving direct synthetic receipt identity ambiguous. The report-order and
receipt-doc findings are P3. OpenCLAW #168 remains open and non-deployable.
Judge-chain discrimination, runner-origin custody, slow-leak detection,
disposition calibration, and operational launch holds remain independent and
unchanged.
