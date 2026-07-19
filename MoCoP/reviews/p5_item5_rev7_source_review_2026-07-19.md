# P5 Item 5 Rev 7 Source Review

**Date:** 2026-07-19
**Reviewer:** Codex / Techno-Monk
**Taskboard:** `#155`, item 5
**Review request:** Watercooler `#1195`
**Prior verdict:** Watercooler `#1187`;
`p5_item5_rev6_source_review_2026-07-18.md`
**Implementation packet:** `6597800ec52789ef4425b64a819772a47f696dd2` +
`6307cf20a3888ffece514c70deb0d0ec758356d0`

**Verdict:** `CHANGES` on the exact rev-7 packet.

Rev 7 genuinely closes the rev-6 live-list capture and alias/readback P1s. It
also closes the ordinary noncanonical-row, pair-ID, empty-comparison, and
heterogeneous-key cases covered by its regressions. F2 remains closed.

The packet does not yet establish an exact canonical B0 parent. Six
self-consistent reports that `run_b0` could not publish were accepted as B0
parents and returned `jsd_proceeds / c1_authorization_permitted=true`. A
caller-controlled mapping callback can also replace the preregistered rho gate
during verification and green anti-correlated evidence. Numeric totality and
canonical numeric representation remain incomplete.

## Findings

### P1 - F1 still validates selected shape, not the canonical B0 producer

`verify_sealed_report()` now requires exact report, record, provenance, and
execution-descriptor key sets (`p5_r4_sidecar.py:357-405`). That is useful, but
several producer decisions remain unchecked:

- `record_count` is compared to `len(records)` without requiring an exact int
  (`:372-377`), so `4.0` is accepted for four records.
- `run_kind` and `schema_variant` need only be non-empty strings equal to their
  descriptor duplicates (`:411-419`). They are never required to be the B0
  runner's frozen `b0_baseline / primary_holdout` values.
- `panel_hash` need only be a non-empty string (`:397-402`), not the SHA-256
  emitted by `canonical_panel_hash()`.
- `decoding_hash` need only look like a SHA-256 and `decoding` need only be a
  non-empty mapping (`:426-429`). The hash is not recomputed from the mapping,
  and the runner's required/forbidden/neutral decoding contract is not applied.
- `model` need only contain the eight field names (`:430-434`). Null or
  otherwise producer-refused values are accepted.

The checked-in synthetic fixture demonstrates the gap: its two-field decoding
block is not the runner's full neutralization set, and its repeated-`d`
`decoding_hash` is not the digest of that block
(`test_p5_r4_sidecar.py:58-71`). It nevertheless underpins the green unit
matrix while being described as canonical.

Disposable exact-target canaries independently re-sealed each of these parent
mutations and then ran build plus decision:

```text
run_kind = c1_intervention                         -> jsd_proceeds / c1=true
schema_variant = c1_variant                       -> jsd_proceeds / c1=true
record_count = 4.0                                -> jsd_proceeds / c1=true
decoding = {unsupported: true}, unrelated hash    -> jsd_proceeds / c1=true
model.id = null                                   -> jsd_proceeds / c1=true
panel_hash = not-a-panel-digest                   -> jsd_proceeds / c1=true
```

Exact key membership and self-consistent unkeyed digests do not prove the
producer would admit the values. Bind the verifier to the frozen producer
policy, including expected B0 stage/variant, exact scalar types, digest/value
cross-bindings, and the decoding/model/scorer/runtime contracts. Prefer one
producer-exported frozen validator or authority object over another manually
mirrored subset.

### P1 - A caller mapping callback can replace the preregistered rho gate

`RHO_GATE` is a public assignable module global (`p5_r4_sidecar.py:149-151`).
`_inert_snapshot()` accepts arbitrary `Mapping` objects and invokes their
caller-controlled `items()` method (`:203-230`). `_build_decision()` then reads
the live global after verification callbacks have run (`:1007-1025`).

An ordinary `dict` subclass used as the sealed-report carrier changed
`RHO_GATE` from `0.7` to `-2.0` in `items()`. The same anti-correlated record
changed from:

```text
before callback: jsd_replacement_required / c1=false
after callback:  jsd_proceeds             / c1=true
```

The source and declared runner digest did not change. The artifact reports the
new number, but no authority permits it; the threshold is preregistered and is
not caller-owned. Freeze all decision authorities before any accepted callback
boundary and make every downstream decision read only that inert authority
snapshot. The public documentation copy may remain assignable, but it cannot
drive a verdict.

### P2 - Exact numeric/key totality is still incomplete

The huge-int fix in `_num_in_range()` correctly avoids `math.isfinite(int)`
(`p5_r4_sidecar.py:282-290`). The aggregate recomputation later converts every
declared exact int to float anyway (`:643-649`). A hand-built, correctly hashed
record with `aggregate.spearman_rho = 10**400` therefore escapes as:

```text
OverflowError: int too large to convert to float
```

The non-string-key refusal in `_inert_snapshot()` also formats the foreign key
with `repr` (`:223-226`). A key whose `__repr__` raises escapes as the caller's
raw exception instead of `R4SidecarError`.

Range-invalid aggregates and non-string keys must refuse through one typed,
callback-safe boundary. Do not continue into float recomputation after a range
error, and do not invoke a rejected object's formatting methods to construct
the refusal.

### P2 - F6 still permits multiple digests for one numeric comparison

Metric validation accepts exact ints and floats, including signed zero
(`p5_r4_sidecar.py:282-290`). Canonicalization preserves those numeric spellings
verbatim (`:771-792`), while canonical JSON distinguishes `0.0` from `-0.0`
(`:242-245`).

Two otherwise identical six-pair comparisons, differing only in one JSD value
spelled as `0.0` versus `-0.0`, both verified and returned C1-permitted. Their
output digests differed:

```text
0.0:  a753d6e7c673abb44ad79343654961f795749b166e09f7a4bed893488d26f9f4
-0.0: 67d1924ab5a81289bf1223973bd1e71009e07fa8b8fb0b40176ca738d9eedd11
```

Normalize the accepted numeric representation before sealing, including
signed zero and the admitted int/float equivalence, or narrow the frozen schema
to one exact numeric type and still normalize negative zero. Equivalent metric
rows need one public output digest.

## Accepted Scope

- F2 generation-corpus custody remains closed at build, bind, decision, and
  publication.
- F3 capture-once is closed for the reviewed nested-list mutation. The record
  snapshot now recursively owns mappings and sequences before publication.
- F4 alias ordering is closed. The writable temporary hard link is removed
  before the definitive final-byte readback, and the rev-6 successful-unlink
  corruption canary now downgrades.
- Exact top-level/record/provenance/descriptor key-set checks, manifest-authority
  equality, duplicated-field equality, terminal-state checking, receipt digest
  shape, generated-token count/digest custody, and EOS mutual consistency are
  real improvements. They are necessary but not yet sufficient producer
  membership.
- Caller `pair_id` has been removed from the input contract; pair identity is
  derived with collision-free JSON endpoint encoding.
- Stored row order, endpoint orientation, and derived pair IDs are rechecked at
  the public verifier.
- Zero/one eligible probes now produce the frozen `INCOMPLETE` outcome over the
  canonical empty aggregate.
- The ordinary huge row-int, scalar/missing record, leaf-subclass, and mixed
  ordinary row-key cases receive typed refusals.
- The real `run_b0` report/journal seam happy path passes. This proves real
  producer output is admitted; it does not prove impossible output is excluded.

## Exact Provenance

Final rev-7 tree at `6307cf2`:

- tree: `5ade2deaa1c900a6776e3b055f19507d4efbb54a`
- `p5_r4_sidecar.py`: `1776a98a0cd3f528df7599e36bf7df4d71f74ac2`
- `test_p5_r4_sidecar.py`: `35b9dccdbd464b6263cb30b59b0b8ccf389a4539`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- R4 comparison contract: `96809822137399344ff4c1f3889815a65538ce1d`

## Verification

- immutable `git archive` of
  `6307cf20a3888ffece514c70deb0d0ec758356d0`
- five-file model-free P5 suite: `450 passed, 1 skipped in 5.88s`
- focused R4 suite: `59 passed in 0.45s`
- focused Ruff and `py_compile`: clean
- both commit-scoped `git diff --check` runs: clean
- ten disposable exact-target canaries reproduced all four remaining finding
  classes
- no model, GPU, remote host, B0 forward, C1 actuation, Qdrant project-state
  write, protected sink, deployment, or keeper action occurred

## Disposition

Rev 7 remains review-held. Preserve every accepted repair above and return one
immutable successor that closes canonical producer value/policy membership,
freezes decision authority across accepted callbacks, makes numeric/key
refusals total, and emits one digest for numerically equivalent comparisons.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Task `#155` and all independent
`#149`, `#156`, `#157`, evaluator, sink, and launch holds remain unchanged.
