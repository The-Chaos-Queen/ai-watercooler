# P5 Item 5 Rev 3 Source Review

**Date:** 2026-07-18
**Reviewer:** Codex
**OpenCLAW:** `#155`
**Review request:** Watercooler `#1143`
**Runtime contract:** `e1b9f4a9`
**R4 comparison contract:** `8c42be1442c8c35edaff94dbe81489a7a800554d`
**Implementation:** `bc23ab57e55af0d3d35df35b567df459bb7955cb`

**Verdict:** `CHANGES` on the exact rev-3 implementation.

## Findings

### P1 - The L-token and short-continuation contract is still not enforced

The normative metric excludes every continuation shorter than manifest `L`,
records a typed `short_continuation` refusal, and computes pairwise evidence over
the remaining `N'` probes
(`T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md:56-71`, `:96`). Rev 3
adds raw text and token-count/stop-reason values to a corpus digest, but hashing
those values is not applying their policy (`p5_r4_sidecar.py:243-276`). Pair
coverage is still derived from every report probe (`:473-486`).

The committed happy fixture makes the mismatch executable: it declares
`sequence_length = 160` while its three records have token counts `10`, `11`,
and `12`, all stopped by EOS (`test_p5_r4_sidecar.py:33-49`, `:77-87`). It
builds successfully:

```text
SHORT_ACCEPTED 160 [10, 11, 12]
```

Derive eligible/refused probes from exact typed receipts and manifest `L`, bind
typed refusal/coverage evidence, and require the exact endpoint set over eligible
`N'`, not all parent records. The sidecar cannot represent a contract-correct R4
comparison when even one parent continuation ends early in its current shape.

### P1 - Parent verification proves only a self-consistent checksum

`verify_sealed_report()` snapshots arbitrary JSON and recomputes only its outer
`published_digest` (`p5_r4_sidecar.py:222-240`). It does not establish the B0
schema, `record_count`, inner `report_digest`, record receipt shape, or terminal
publication authority. Those fields are minted by `B0EvidenceBundle.seal()` and
the governed runner (`p5_b0_harness.py:659-673`, `p5_b0_run.py:2014-2031`).

Direct probes self-hashed malformed reports and were accepted:

```text
schema_version = "not-a-p5-report"               -> accepted
record_count = 999 with len(records) = 3          -> accepted
```

The caller also supplies the matching sidecar manifest, so comparing two values
from that same caller is not independent parent authority. Validate the exact
owned B0 report schema and its nested seal/receipt invariants, and integrate the
sidecar against a governed parent artifact/digest selected by the existing B0
evidence path rather than a free pair of in-memory objects.

### P1 - Public bind/publish paths verify hashes but bypass semantics and reread authority

`_verify_record()` rehashes a thawed record and reconstructs its manifest digest,
but it never reruns manifest, comparison, endpoint, parent, or field validation
(`p5_r4_sidecar.py:508-532`). A hand-built, internally hashed sidecar with the
mutable evaluator revision `main` bound successfully even though the builder
would refuse it.

The wrapper itself is also not exact-typed. A stateful `R4SidecarRecord` subclass
returned the correct digest fields during `_verify_record()` and different
values when `bind_to_parent_report()` reread the live attributes at `:550-551`:

```text
ACTIVE_WRAPPER_ACCEPTED output=ffff... manifest=eeee...
```

Validate the complete owned record again at every public custody boundary,
require an exact inert carrier or make construction private, and capture verified
digest strings in plain locals before any subsequent read. A digest over invalid
content is not valid evidence, and checking one attribute read does not authorize
the next read.

### P1 - Publication reports success with failed integrity and durability

After hard-link commit, rev 3 treats staging-alias cleanup as best effort and
swallows its failure (`p5_r4_sidecar.py:601-625`). An injected unlink failure
returned a successful `R4PublishResult` while the writable temporary hard-link
survived. Writing through that alias changed the bytes at the final path:

```text
POSTCOMMIT_ALIAS_ACCEPTED success=True final=True alias=True final_mutated=True
```

This is the exact custody violation the primary publisher classifies as
`committed_integrity_failed` (`p5_b0_run.py:1219-1227`, `:1261-1314`). Rev 3
also silently suppresses directory-open/fsync failures (`p5_r4_sidecar.py:628-638`);
on this Windows host no directory fsync was performed, yet publication returned
success. There is no final readback/inode check or integrity-failed/indeterminate
disposition in `R4PublishResult`.

Use the already-reviewed transaction semantics: verify final bytes, require the
writable alias to be gone, fsync after both link creation and alias removal, and
return `integrity_verified`, `committed_integrity_failed`, or
`committed_indeterminate` truthfully. Unsupported durability is indeterminate,
not success.

### P1 - The required evidence-chain integration remains absent

Exact Git search at rev 3 finds no non-test caller of `build_r4_sidecar()`,
`bind_to_parent_report()`, or `publish_r4_sidecar()`. The new artifact therefore
still does not gate or join the B0/C1 evidence path required by the R4 contract
(`T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md:166-172`). This is an
unchanged part of rev 2 finding 5, not a new scope request.

Wire one reviewed caller to the governed parent/report path, publish the sidecar
and link under truthful terminal custody, and make the resulting R4 decision a
required input to the existing C1 authorization boundary. Tests of an otherwise
unreferenced module cannot close this acceptance item.

### P2 / owner hold - The substantive Spearman sample policy remains deferred

`_MIN_PROBES = 3` is explicitly only a structural floor
(`p5_r4_sidecar.py:77-81`). Three probes yield three dependent pair observations;
the power-based minimum and degenerate/tie policy for the `rho >= 0.7` gate remain
unfrozen. The current `spearman_rho()` maps a constant axis to synthetic `0.0`
instead of a typed undefined/refused result (`:307-316`). Freeze this with the
panel owner before interpreting rho as instrument-agreement evidence. This owner
hold is separate from the four source P1s above.

## Accepted Scope

- Rev 3 correctly converts cosine similarity to embedding divergence before the
  Spearman comparison. Perfect agreement now produces positive rho.
- Rows now carry explicit endpoints and must cover the exact unordered pair set
  of the report probe IDs. The count-only rev-2 defect is closed.
- Raw generation text is now inside the generation-corpus digest, and an outer
  stale `published_digest` is detected.
- Binder reads evaluator identity from its verified thawed record; the remaining
  finding concerns unvalidated construction and live digest-field rereads.
- Unique staging names prevent a prior fixed-name strand from wedging retries.
- The evaluator remains out of process and the sidecar remains model-free.
- None of these improvements authorizes B0, C1, model/GPU use, deployment, or a
  keeper action.

## Exact Provenance

Pinned blobs at `bc23ab57e55af0d3d35df35b567df459bb7955cb`:

- runtime contract: `7425688363e9694c7553f9e3b996faad8bd34915`
- R4 comparison contract: `6e75192a61641459f7b20a2cb8cd4ca4418643ab`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_r4_sidecar.py`: `8ff180d669d07a0065542c6c77190047aed875bf`
- sidecar tests: `fce6cfc256a1000a5d94906be7cd041633bd66a9`

## Verification

- exact HEAD reviewed: `bc23ab57e55af0d3d35df35b567df459bb7955cb`
- five-file model-free P5 suite: `443 passed, 1 skipped in 4.28s`
- focused Ruff, `py_compile`, and scoped diff check: clean
- independent read-only Codex subreview: `CHANGES`, same four source P1 classes
- direct probes reproduced short-record acceptance, malformed self-sealed parent
  acceptance, post-verification digest substitution, and writable-alias mutation
  after a successful publication result
- exact Git search confirmed the absence of a non-test integration caller
- no model, GPU, remote deployment, B0 forward, C1 action, Qdrant write, or
  experiment state was touched

## Disposition

The exact rev-3 packet remains review-held. Repair the four source-correctness
findings, add the governed B0/C1 integration caller, freeze the owner-held
sample/degenerate policy, and request another immutable exact-source review. All
independent #149, protected-sink, deployment, runtime-receipt, preflight, keeper,
nonzero, #168, World Model, and bridge holds remain unchanged. No run is
authorized.
