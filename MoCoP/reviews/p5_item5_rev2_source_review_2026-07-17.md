# P5 Item 5 Rev 2 Source Review

**Date:** 2026-07-17
**Reviewer:** Codex
**OpenCLAW:** `#155`
**Review request:** Watercooler `#1139`
**Runtime contract:** `e1b9f4a9`
**R4 comparison contract:** `8c42be1442c8c35edaff94dbe81489a7a800554d`
**Implementation:** `2844d25a5a64bc93e50d0c54ffd9fa085038cfe7`

**Verdict:** `CHANGES` on the exact rev-2 implementation.

## Findings

### P1 - The agreement statistic has reversed polarity

The contract compares JSD pairwise **diversity** with embedding pairwise
**diversity**, and allows JSD to proceed when Spearman rho is at least 0.7
(`T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md:164-172`). The
implementation instead correlates JSD directly with cosine similarity
(`p5_r4_sidecar.py:340-350`, `:380-386`). Higher JSD means more diverse while
higher cosine means more similar, so perfect instrument agreement is inverse
rank order and produces `rho = -1.0`. The gate would classify that as
load-bearing disagreement.

The committed fixture encodes the inverse relationship
(`test_p5_r4_sidecar.py:50-68`) but tests only the mathematical correlation,
not the contract's gate interpretation. Direct reproduction:

```text
rho(jsd, cosine)     = -1.0
rho(jsd, 1 - cosine) =  1.0
```

Freeze one polarity explicitly: correlate JSD with embedding diversity such as
`1 - cosine`, or compare a similarity transform of JSD with cosine. Pin the
choice and its gate-direction regression test before using rho as evidence.

### P1 - Pair completeness is cardinality-only, not bound to the parent panel

Rows carry only a caller-authored `pair_id`. The validator checks uniqueness
and `len(per_pair) == C(N,2)` but explicitly defers exact pair identity
(`p5_r4_sidecar.py:323-358`). Three arbitrary strings therefore satisfy a
three-probe report's complete-pair check:

```text
report probes: p0, p1, p2
accepted pair_ids: fake-a, fake-b, fake-c
```

Recomputing rho and means proves only that the fabricated rows are internally
consistent; it does not prove they cover the required SEV continuations. A
two-probe/one-row record also turns undefined rank correlation into synthetic
`0.0` (`:292-306`, `:381-386`) and accepts it as evidence. Bind every row to
canonical endpoint probe IDs, require exact equality with the unordered pair
set derived from the parent, and freeze the minimum/tie/degenerate policy for a
meaningful Spearman gate.

### P1 - The parent seal and evaluator input are not established

Only manifest, row, and aggregate inputs are snapshotted
(`p5_r4_sidecar.py:420-423`). The caller-owned `sealed_report` is read multiple
times. Its `published_digest` is checked only for SHA-256 shape and string
equality; the report content is never rehashed (`:424-447`, `:489-498`). A
report whose `token_count` was changed after sealing, while retaining its stale
published digest, was accepted and linked to that stale digest.

The derived generation digest covers selected token receipts but omits the
actual `raw_generation` consumed by the embedding evaluator
(`p5_r4_sidecar.py:227-260`). It also does not establish the manifest's
sequence length or the contract's short-continuation handling. The happy-path
test fixture uses token counts `10+i` while declaring `L=160`
(`test_p5_r4_sidecar.py:35-46`, `:73-90`) and succeeds.

Take one owned exact report snapshot; verify its canonical published digest and
record schema; derive the evaluator-input binding, panel identity, length and
stop receipts from that same snapshot; and never reread the caller object.

### P1 - The binder discards its verified snapshot and publishes live values

`_inert_snapshot()` claims exact built-ins but admits arbitrary `Mapping` and
list subclasses (`p5_r4_sidecar.py:89-114`). More directly, a caller can
construct `R4SidecarRecord` with an active mapping. `_verify_record()` thaws and
rehashes one view, but `bind_to_parent_report()` discards the returned snapshot
and rereads `sidecar.record` for the parent and evaluator fields
(`:473-505`). A two-view mapping passed digest verification and then published
`evaluator_id = mutated-after-verify` under the digest of the first view.

`sidecar.manifest_digest` is likewise copied into the link without shape or
content verification (`:502`). Enforce recursively exact inert input types at
the public boundary, use the owned value returned by `_verify_record()` for all
subsequent reads, and recompute or remove every separately published digest.

### P1 - Publication has ambiguous commit states and is not integrated

`publish_r4_sidecar()` uses a fixed `.tmp`, writes and fsyncs it, hard-links it
to the final name, and unlinks the staging alias (`p5_r4_sidecar.py:515-561`).
Injected failures demonstrate both sides of an ambiguous transaction:

```text
pre-commit fsync failure: raises; fixed .tmp remains; final absent
post-link cleanup failure: raises; final exists; writable .tmp alias remains
```

There is also no final-byte/inode verification, parent-directory fsync, or
explicit committed/indeterminate disposition. A caller cannot distinguish a
retryable pre-commit failure from a successful publication followed by cleanup
failure. Use unique staging custody, total cleanup, durable directory sync and
post-commit verification, with an explicit post-commit result that never
reports the visible artifact as absent.

Finally, exact `git grep` finds no non-test caller of `build_r4_sidecar()`,
`bind_to_parent_report()`, or `publish_r4_sidecar()`. The artifact is not yet
bound into the B0 evidence/authorization path required by the R4 contract
(`T_DIVERSITY...md:170-172`).

## Accepted Scope

- Rev 2 closes ordinary nested-dictionary mutation with a frozen graph.
- Metric domains, declared means, and declared rho are now validated and
  recomputed from the supplied rows.
- The evaluator remains outside the monitor process, and no torch,
  transformers, or sentence-transformers dependency was added.
- A basic no-replace publication path now exists. The finding above concerns
  its failure-state semantics, durability, and missing evidence-chain caller.
- None of these accepted improvements changes the `CHANGES` verdict or
  authorizes a B0 run, C1, model/GPU use, deployment, or keeper action.

## Exact Provenance

Pinned blobs at `2844d25a5a64bc93e50d0c54ffd9fa085038cfe7`:

- runtime contract: `7425688363e9694c7553f9e3b996faad8bd34915`
- R4 comparison contract: `6e75192a61641459f7b20a2cb8cd4ca4418643ab`
- `p5_r4_sidecar.py`: `6229864947c889d0e1f6783c2c562d6c7857ba9d`
- sidecar tests: `a069c7782b83026bda0176a21b2ca15fc7f12341`

## Verification

- exact HEAD: `2844d25a5a64bc93e50d0c54ffd9fa085038cfe7`
- five-file model-free P5 suite: `431 passed, 1 skipped in 7.91s`
- focused Ruff and `py_compile`: clean
- scoped `git diff --check`: clean
- independent read-only Codex subreview: `CHANGES`, same five defect classes
- direct probes reproduced reversed polarity, fake pair-ID acceptance, stale
  parent-seal acceptance, post-verification reread, pre-commit staging leak,
  and post-commit exception with a visible final artifact
- no model, GPU, remote deployment, protected sink, B0 forward, C1 action,
  Qdrant path, or experiment state was touched

## Disposition

The exact rev-2 packet remains review-held. This review supersedes neither the
historical four-commit review nor its provenance; it records the successor's
state. Repair the five findings above and request another exact-source review.
All independent protected-sink, deployment, runtime-receipt, preflight, keeper,
nonzero, #149, #168, World Model, and bridge holds remain unchanged.
