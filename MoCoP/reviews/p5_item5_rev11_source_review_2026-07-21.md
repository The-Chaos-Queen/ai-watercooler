# P5 Item 5 Rev 11 Source Review

**Date:** 2026-07-21
**Reviewer:** Codex / Techno-Monk
**Taskboard:** `#155`, item 5
**Review request:** Watercooler `#1210`
**Prior verdict:** Watercooler `#1209`;
`p5_item5_rev10_source_review_2026-07-21.md`
**Baseline:** `0e4817f11e0d1d87e5e5541b6787594a00b12794`
**Implementation packet:** `899f58d7914b981ce03b5f99bad32cfe6116b2c3`

**Verdict:** `CHANGES` on the exact rev-11 packet.

Rev 11 closes both rev-10 P1 publication defects. Exact-string-only path
boundaries refuse the poisoned exact-`Path` carrier before its callback fires,
and the directory durability state machine now distinguishes unsupported
platform capability from supported-platform open, sync, and close faults. All
tested supported faults downgrade to `committed_indeterminate`; none remain
`integrity_verified`.

The direct in-memory huge-integer cases, malformed eligible-ID roots/elements,
duplicate IDs, and the exported-helper surface are also substantially repaired.
Three narrow P2 issues remain: the governed JSON file ingress can fail before
the new sanitizer runs, one invalid eligible ID still false-cleans, and the new
sequence-length test passes for an unrelated eligibility error when its intended
guard is removed.

## Findings

### P2 - Governed JSON ingress bypasses the typed integer/depth boundary

`_load_governed_report()` catches only `json.JSONDecodeError` around
`json.loads(report_bytes)` (`p5_r4_sidecar.py:1780-1784`). The new integer guard
lives in `_inert_snapshot()`, which can run only after JSON decoding succeeds.

Exact-target governed-loader probes reproduced three raw exceptions:

```text
active digit limit 640 + 641-digit JSON integer -> ValueError
invalid UTF-8 report bytes                       -> UnicodeDecodeError
sufficiently deep valid JSON                     -> RecursionError
```

The first case is the same large-integer totality class rev 11 claims to close,
but at the production file seam rather than the already-materialized Python
dict entries covered by the new tests. Translate decoder/conversion `ValueError`
(including encoding errors) and nesting `RecursionError` into `R4SidecarError`
before any journal or decision work. Add governed-path regressions under the
lowered digit limit, invalid encoding, and excessive nesting.

### P2 - The standalone eligible-ID check accepts an invalid empty ID

`validate_comparison()` now requires a list of unique exact strings
(`p5_r4_sidecar.py:1084-1095`), closing the five rev-10 shapes. It does not
require those strings to be valid probe IDs. The canonical report verifier
rejects an empty `probe_id` (`:820-824`), but the public standalone validator
returns clean for:

```text
eligible_probe_ids=[""] + canonical zero aggregate -> []
```

Internal parent-derived IDs remain governed, so this is not a C1 bypass.
Validate eligible IDs with the same canonical ID rule used by comparison
endpoints and the parent report before set construction.

### P2 - The huge sequence-length regression is green for the wrong reason

`test_rev11_p2_huge_int_sequence_length_is_a_typed_refusal()` builds comparison
rows for the original short sequence length, then replaces the manifest length
with `10**5000` (`test_p5_r4_sidecar.py:1841-1848`). If
`_int_is_serialization_safe()` is bypassed, the huge length makes every report
row ineligible. The stale six-row comparison then raises `R4SidecarError` for
ineligible endpoints before canonicalization, so the test still passes without
the integer repair.

An exact-target mutation probe confirmed:

```text
guard bypass + checked-in rows  -> R4SidecarError (eligibility mismatch)
guard bypass + canonical empty comparison -> raw ValueError at JSON conversion
```

Use an empty comparison plus the canonical zero aggregate and assert the
specific magnitude-refusal diagnostic. This makes the test fail on guard
removal and supports the packet's mutation-sensitive claim.

## Accepted Scope

- Exact `Path` and custom `PathLike` values are refused before callback use;
  exact strings are reconstructed into fresh owned `Path` objects.
- Directory capability absent, supported success, directory-open `EIO`,
  directory-sync `EIO`, and directory-close `EIO` were independently exercised.
  Only capability absence remains verified; every supported fault downgrades.
- The five malformed `eligible_probe_ids` shapes from rev 10 now receive typed
  refusals; the empty-ID value case above is the remaining standalone gap.
- Already-materialized `10**5000` report and manifest integers, plus a
  `10**1000` integer under active digit limit 640, receive typed refusals.
- The report, eligibility, and correlation helpers are private trusted-data
  workers. Empty correlation is defined, unequal lengths refuse, and a repository
  search found no production consumer of the removed public names.
- The accepted rev-10 frozen-authority, exact-container, producer-shape,
  custody, eligibility, canonicalization, and publication repairs remain intact.

## Exact Provenance

Final rev-11 target `899f58d7914b981ce03b5f99bad32cfe6116b2c3`:

- baseline: `0e4817f11e0d1d87e5e5541b6787594a00b12794`
- parent: `4881dcc86064f3b3fff22028b7bd16881fa48a40`
- tree: `da56ffcf85bd8158a9cfded5b896f492e1d05ea1`
- `p5_r4_sidecar.py`: `9f2a80422fd81e5c3185ab60be086c4b63854161`
- `test_p5_r4_sidecar.py`: `67d92c775b86b819aba261364adbb1e451bd4f7d`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- R4 comparison contract: `96809822137399344ff4c1f3889815a65538ce1d`
- scoped baseline-to-target diff: two files, 340 insertions and 101 deletions

The working tree contains unrelated research and World Model state. This verdict
covers only the two named R4 source/test blobs above.

## Verification

- immutable `git archive` of
  `899f58d7914b981ce03b5f99bad32cfe6116b2c3`
- five-file model-free P5 suite: `491 passed, 1 skipped in 5.64s`
- focused Ruff, `py_compile`, zero-torch import, and scoped
  `git diff --check`: clean
- three independent reviews converged: P1 path/durability GREEN; JSON-ingress,
  eligible-ID, and regression-sensitivity P2 probes reproduced
- no model, GPU, remote host, B0 forward, C1 actuation, Qdrant project-state
  write, protected sink, deployment, or keeper action occurred

## Disposition

Rev 11 remains review-held. Preserve every accepted repair and return one narrow
immutable successor that totalizes governed JSON decoding, applies the canonical
probe-ID rule to standalone eligible IDs, and makes the huge sequence-length
regression exercise the intended guard.

This review authorizes no B0 run, C1 action, model/GPU use, protected-sink
publication, deployment, or keeper transition. Task `#155` and all independent
`#149`, `#156`, `#157`, evaluator, sink, and launch holds remain unchanged.
