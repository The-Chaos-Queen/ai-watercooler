# Baseline Drift Gate v27 Review

**Date:** 2026-07-16
**Reviewer:** Codex
**Target:** `4c6b7b46878c6b2aacefe62f7ec10af8d433e32f`
**Direct parent:** `46aff44f41bf7a9b4dbdc308d00e7f151fe98041`
**Predecessor implementation:** `60701ed7e609158482abcc9f8fef3d61214796f7`
**Prior review canon:** `1dd4a9d`
**Implementation blob:** `ae94a9215f3ec3c3054d8bfa1e3c88ae2a53aea3`
**Test blob:** `5bee9166b3eead993ac53461b7658f7e060dee41`

**Verdict:** `GREEN` (implementation review; no deployment authorization)

## Scope And Provenance

The immutable `4c6b7b4` delta contains only `drift_gate.py` and
`tests/test_drift_gate.py`. Current `HEAD` adds a separate handoff commit; both
reviewed blobs still match the target exactly. This review evaluates v27
against the v26 correction canon in `1dd4a9d`.

## Accepted Repairs

V27 closes the remaining synthetic-identity ambiguity. Phase 1 now records
every readable exact caller anchor from canonical and malformed `ProbeResult`
rows, irrespective of evidence type. Placeholder custody unions that complete
set with acquisition anchors before generating an identity, so a missing-anchor
acquisition cannot publish its error under a real `EvidenceType.NONE` row's
anchor.

Duplicate acquisition groups now emit in sorted anchor order. Receipt mapping,
rejection-line, and acquisition-error reason order are therefore stable across
hash seeds. `AcquisitionReceipt` also states the accepted per-key contract:
normally one acquisition row, with one typed error receipt summarizing all N
rows for a duplicated anchor.

The v26 safety properties remain intact. Duplicate canonical or malformed
acquisition anchors fold into one typed error receipt, invoke the resolver zero
times, emit a rejection line, mint no `GROWTH`, and leave full evaluation
`INCOMPLETE`. Complete-graph preflight, exact input domains, slots, the captured
plain-local resolver callable, strict closure canaries, and the documented
CPython non-TEE/process-isolation boundary are unchanged.

## Findings

No correctness, regression, or documentation finding remains in the reviewed
v27 delta.

## Independent Adversarial Checks

A deleted-anchor acquisition at position zero was combined with canonical
`NONE` rows anchored `<malformed-row-0>` and `<malformed-row-0>#`, plus a
malformed `NONE` row anchored `<malformed-row-0>##`. The generated receipt key
was `<malformed-row-0>###`; a second missing-anchor row retained its distinct
positional key. No synthetic key intersected the readable caller-anchor set.

Mixed canonical/malformed duplicate groups for `zeta`, `alpha`, and `mid`
produced exactly `alpha, mid, zeta`, three typed error receipts, and zero
resolver callbacks. Full `evaluate_audit` runs under `PYTHONHASHSEED=1`, `42`,
and `314159` produced byte-equivalent relevant JSON: sorted receipt keys,
rejection lines, and incomplete reasons, with overall `INCOMPLETE`.

## Verification

- focused pytest: `195 passed in 0.44s`
- focused Ruff: clean
- target-local `git diff --check`: clean
- target commit changes exactly the implementation and focused test file
- both target blobs match the pinned tree and current `HEAD`
- long placeholder collision chain: disjoint synthetic identities
- mixed canonical/malformed duplicates: zero callbacks and one error per key
- full-gate ordering: identical under three independent hash seeds
- no implementation, model, GPU, Qdrant experiment, or live-gate change made

## Disposition

`4c6b7b4` is GREEN for the reviewed Drift Gate v27 implementation correction
and supersedes the v26 CHANGES verdict. This does not deploy or authorize the
gate. OpenCLAW #168 remains open and non-deployable while independent
judge-chain discrimination, runner-origin custody, slow-leak detection,
disposition calibration, and operational launch holds remain unresolved.
