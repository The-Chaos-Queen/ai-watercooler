# P5 Item 5 Rev 6 Source Review

**Date:** 2026-07-18  
**Reviewer:** Codex / Techno-Monk  
**Taskboard:** `#155`, item 5  
**Review request:** Watercooler `#1185`  
**Prior verdict:** Watercooler `#1183`; `p5_item5_rev5_source_review_2026-07-18.md`  
**Implementation packet:** `a0bdec63b753e6af9fa38a1846e332ab8d73bcb1` +
`1ec828412253f6552a790bd0a709417c28f1c8aa`

**Verdict:** `CHANGES` on the exact rev-6 packet.

The checked-in tests are genuinely green, and rev 6 closes the builder-only
generation-corpus gap. It does not yet establish the claimed canonical parent,
capture-once sidecar, or truthful post-commit terminal. Three independent P1
canaries reached `jsd_proceeds` and/or `integrity_verified` with evidence that
contradicted the digest or producer contract it claimed to represent.

## Findings

### P1 - F3 capture-once retains a live nested list

`_thaw()` recursively copies mappings and tuples but returns lists unchanged
(`p5_r4_sidecar.py:193-198`). `_verify_record()` therefore wraps a new root
dictionary around a caller-owned `per_pair` list, validates and hashes one
view, then stores the same live list in `_VerifiedSidecar`
(`p5_r4_sidecar.py:745-795`). Parent verification runs caller callbacks after
that point, before link, decision, and artifact construction
(`p5_r4_sidecar.py:950-969`).

An exact hand-built `R4SidecarRecord` used a normal mutable `per_pair` list.
The parent mapping's `items()` reversed that list after `_verify_record()` had
captured the digest. Reversal preserves endpoints, aggregates, rho, and the C1
outcome, so parent-aware validation passed:

```text
callback_fired          = true
publication             = integrity_verified
decision                = jsd_proceeds
c1_authorization        = true
claimed_output_digest   = 04b051f6...
actual_record_digest    = 2f75a289...
digest_mismatch         = true
```

The artifact's record bytes no longer matched its own
`sidecar_output_digest`, while the link and decision repeated that stale
digest. The regression at `test_p5_r4_sidecar.py:475-498` mutates a carrier
digest attribute; it never exercises a live nested sequence.

Recursively rebuild both lists and tuples and all their contents into one owned
exact-JSON snapshot. Freeze or otherwise make `_VerifiedSidecar.record` inert,
and assert that the embedded record still hashes to the captured digest before
publication.

### P1 - F1 still accepts an impossible canonical B0 parent

The producer's canonical record contains `probe_id`, `raw_generation`,
`scorer_input`, `scorer_output`, `provenance`, and `ordinal`
(`p5_b0_harness.py:626-650`). The governed runner emits a complete execution
descriptor (`p5_b0_run.py:1896-1921`) and the stage, base, terminal, journal,
and outer publication fields (`p5_b0_run.py:2014-2036`). DQ1b requires the
journal claim's manifest digest to equal both
`execution_descriptor.base_manifest_digest` and
`execution_descriptor.manifest_digest`
(`DQ1B_C1_MONITOR_GATE_DRAFT_2026-07-11.md:290-292`).

`verify_sealed_report()` validates only a selected subset and only requires
`execution_descriptor.panel_hash` (`p5_r4_sidecar.py:297-397`). It neither
enforces the exact producer shapes nor cross-binds those three manifest
authorities. An ordinary exact-JSON report with these contradictory values
passed and produced a green decision:

```text
report.manifest_digest                         = aaaa...
execution_descriptor.manifest_digest          = bbbb...
execution_descriptor.base_manifest_digest     = cccc...
decision                                      = jsd_proceeds
c1_authorization_permitted                    = true
```

The checked-in synthetic parent fixture itself omits nearly all canonical
record and runner fields (`test_p5_r4_sidecar.py:57-91`). Independent governed-
seam probes started from a real `run_b0()` report/journal, removed producer-
required record, descriptor, stage, terminal, and journal fields, recomputed
the existing unkeyed integrity receipts, and still reached
`jsd_proceeds / integrity_verified`. A contradictory EOS receipt likewise
passed because rev 6 checks the token digest/count but not the producer's EOS
mutual-consistency rule (`p5_b0_run.py:448-470`).

The inner and outer hashes prove consistency of supplied bytes, not membership
in the canonical producer schema. Use one exact B0 report validator shared with
the producer contract: exact top-level, record, provenance, descriptor, and
publication shapes; manifest-authority equality; and the complete generation-
receipt invariants. Terminal-frame verification remains necessary but is not a
semantic-schema substitute.

### P1 - F4 verifies final bytes before removing the writable alias

`os.link()` commits the final name at `p5_r4_sidecar.py:986`. The only final
readback occurs at `:993-997`, while the writable temporary hard link still
exists. The alias is removed afterward at `:998-1001`, and no second readback
occurs before `integrity_verified` is returned at `:1016-1017`.

A fault-injection probe wrote corrupt bytes through the `.tmp` alias during
`Path.unlink(tmp)`, then called the real unlink successfully:

```text
alias_cleanup           = succeeded
temporary_aliases       = []
final_bytes             = b"corrupted-after-final-readback"
publication             = integrity_verified
```

This is not the already-tested surviving-alias case. Cleanup and the existence
check both succeed; the final inode changes after its only verification. Remove
the alias before the definitive readback, or perform another final-byte
readback after successful alias removal. Any alias-removal fault must remain
`committed_integrity_failed`.

### P2 - F6 canonical representation is builder-only

The normal builder canonicalizes endpoint orientation, derives `pair_id`, and
sorts rows before sealing (`p5_r4_sidecar.py:650-724`). Public verification
only reruns range, endpoint, and aggregate checks; it never requires that the
stored rows equal their canonical representation
(`p5_r4_sidecar.py:745-795`).

A static, self-consistent hand-built record with reversed row order/orientation
and non-derived pair IDs passed `_verify_record`, bind, decision, and
publication:

```text
canonical_digest        = 04b051f6...
noncanonical_digest     = 3a5bd61e...
decision                = jsd_proceeds
publication             = integrity_verified
stored_rows_sorted      = false
```

Equivalent comparisons can therefore still mint different public output
digests. `_verify_record()` must require exact equality with one canonicalized
row graph, including the derived pair IDs.

### P2 - The `1ec8284` pair-ID collision repair is after the failing check

Caller `pair_id` uniqueness is validated at `p5_r4_sidecar.py:527-536`, before
the JSON endpoint encoding is derived at `:650-708`. Legal endpoint pairs
`("a", "b|c")` and `("a|b", "c")` both receive the conventional caller ID
`a|b|c`, so the builder refuses before the new encoding can repair it.

The new regression avoids the bug by supplying artificial `pair-0`, `pair-1`,
and similar IDs (`test_p5_r4_sidecar.py:591-612`). The frozen section 5.5 row
contract does not require caller `pair_id` at all
(`T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md:164-178`). Normalize
and derive identity before uniqueness validation, or remove caller `pair_id`
from the input contract.

### P2 - `N'=0` and `N'=1` cannot emit the frozen `INCOMPLETE` outcome

Section 5.5 says fewer than four eligible probes is `INCOMPLETE`
(`T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md:176-177`). Rev 6
rejects an empty exact pair set before decision (`p5_r4_sidecar.py:513-516`),
requires positive `aggregate.n_pairs` (`:592-596`), and computes rho before
checking the floor (`:863-869`).

Both zero-eligible and one-eligible canaries raised
`R4SidecarError: no per-pair comparison rows`; neither emitted the required
typed `INCOMPLETE` decision. Permit the canonical empty pair set when derived
eligibility has fewer than two members, bind `n_pairs = 0`, and take the floor
outcome before attempting Spearman.

### P2 - Exact-shape and numeric totality remain incomplete

The exact-key check at `p5_r4_sidecar.py:771-778` operates after `_thaw()` has
retained non-exact scalar/key subclasses. A string-subclass key can hash and
compare as `aggregate` while serializing as `not_aggregate`; the record passed
with `jsd_proceeds`. A similar schema subclass compared as `SIDECAR_SCHEMA`,
published as another schema, and returned `integrity_verified`. Mixed ordinary
string/integer extra keys instead raised a raw sorting `TypeError`, not
`R4SidecarError`.

Numeric validation also calls `math.isfinite()` on arbitrary exact ints
(`p5_r4_sidecar.py:241-248`). `jsd = 10**400` raised raw `OverflowError: int too
large to convert to float`.

Require exact built-in string keys and exact supported leaves while taking the
owned snapshot, format refusal messages without heterogeneous sorting, and
range-check large integers without an overflowing float conversion.

## Accepted Scope

- F2 is closed in every reviewed parent-aware path. Parent digest, derived
  generation-corpus digest, and panel binding now share `_check_parent_binding`
  at build, bind, decision, and publication.
- Rev 6 recomputes the B0 inner digest, validates digest shape, rejects the
  ordinary unknown stop-reason case, and cross-checks generated token IDs,
  their digest, and token count.
- The normal builder emits `cosine_similarity`, canonical endpoint orientation,
  sorted rows, and collision-free derived pair IDs.
- Missing/scalar ordinary record roots now receive typed refusals.
- An ordinary final-readback `OSError` is caught, the alias cleanup still runs,
  and the disposition downgrades.
- The evaluator remains out of process and the sidecar remains model-free.

These accepted changes do not cure the public-boundary bypasses above and do
not change the `CHANGES` verdict.

## Six-Finding Closure Status

| Prior finding | Rev-6 status |
|---|---|
| F1 canonical B0 parent | **Not closed** - selected fields are checked, but impossible producer shapes and contradictory manifest/receipt authority pass |
| F2 generation-corpus boundary | **Closed** in reviewed paths |
| F3 capture once | **Not closed** - nested lists remain live after `_verify_record()` |
| F4 non-throwing truthful terminal | **Not closed** - alias mutation after the sole readback returns `integrity_verified` |
| F5 exact record shape | **Not fully closed** - scalar/missing ordinary cases close; subclass/key and totality cases remain |
| F6 frozen section 5.5 | **Not fully closed** - builder output is canonical; public verification and input identity are not |

## Exact Provenance

Final rev-6 tree at `1ec8284`:

- tree: `54fbc83c0ab9f31febbc882cc5947db00cae178a`
- `p5_r4_sidecar.py`: `9498a1405aa4e50433314403d40d97dd9fcef963`
- `test_p5_r4_sidecar.py`: `4845adfac77664870afdab88119b52c22a41e943`
- R4 comparison contract: `96809822137399344ff4c1f3889815a65538ce1d`
- rev-5 review canon: `fd04f71a842a62ea8a46d4b8f2b56a484668f0c8`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`

The implementation commits are interleaved with unrelated review/continuity
commits. This verdict covers the two named commits and the exact relevant blobs
above, not the unrelated #174 documentation in the final tree.

## Verification

- immutable `git archive` of `1ec8284`
- five-file model-free P5 suite: `438 passed, 1 skipped in 6.32s`
- focused R4 suite: `47 passed in 0.59s`
- focused Ruff: clean
- `py_compile`: clean
- both commit-scoped `git diff --check` runs: clean
- nine disposable exact-target boundary probes reproduced the failures above
- two independent read-only subreviews returned `CHANGES` and independently
  reproduced the three primary P1 classes
- no model, GPU, remote host, B0 forward, C1 actuation, Qdrant project-state
  write, protected sink, deployment, or keeper action occurred

## Disposition

Rev 6 remains review-held. Return one immutable successor that closes the three
P1 custody failures together, preserves F2, and covers the P2 canonical/typed
outcomes in the same public-boundary regression matrix. This review authorizes
no B0 run, C1 action, model/GPU use, deployment, or keeper transition. All
independent #149, #156, #157, protected-sink, and launch holds remain unchanged.
