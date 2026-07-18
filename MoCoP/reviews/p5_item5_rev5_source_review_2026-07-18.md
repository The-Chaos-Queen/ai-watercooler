# P5 Item 5 Rev 5 Exact-Source Review

**Date:** 2026-07-18
**Reviewer:** Codex
**OpenCLAW:** `#155`, item 5
**Review request:** Watercooler `#1175`
**Rev-4 comparison point:** `57629746f7b45d1eac460b12db80a403c812ba75`
**Rev-5 core repair:** `5a01f06b27ba4060dfbc837c3c1892b62899234f`
**Exact final target:** `e805a7550f322a8e23670d44ae07a4cdc9e24b9a`

**Verdict:** `CHANGES` on the exact rev-5 target.

The rev-5 eligibility repair is real: the six-declared-over-zero-eligible exploit
from rev 4 is refused. The final source still has four independently reproduced
P1 custody/publication failures, however. The green checked-in suite does not
exercise them.

## Findings

### P1 - F2-depth still accepts a structurally false governed B0 parent

`verify_sealed_report()` validates an outer caller-recomputable
`published_digest`, the schema string, count equality, and only part of each
generation receipt (`p5_r4_sidecar.py:262-313`). It never requires or recomputes
the inner `report_digest` minted by `B0EvidenceBundle.seal()`
(`p5_b0_harness.py:659-673`). This exact inner check was a frozen #1146 F2-depth
requirement, not an optional hardening item.

The journal check does not compensate. A model-free probe started with a genuine
four-probe `run_b0()` report and integrity-verified journal, changed only the
inner `report_digest` to `00..`, recomputed the outer digest and the corresponding
unkeyed sealing/terminal fields, and then used the normal governed seam:

```json
{"c1": true, "decision": "jsd_proceeds", "forged_inner_prefix": "00000000", "original_run_ok": true, "publish": "integrity_verified", "record_result_ok": true, "terminal_disposition": "integrity_verified", "terminal_ok": true}
```

This traversed `verify_terminal_frames()` and `record_r4_comparison()`, so the
defect is not limited to direct hand-built carriers.

The same validator root has additional executable gaps that must be fixed with
the inner digest rather than deferred to another round:

- It accepts synthetic reports with no `report_digest` or `manifest_digest` at
  all; the committed R4 unit fixture is such a partial report.
- It checks only that `stop_reason` is a string. A report using
  `backend_crashed` makes all four records eligible and reaches
  `jsd_proceeds/c1=True`, despite the frozen `eos | length | error` enum
  (`T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md:58-61`).
- It does not validate the receipt digest fields as SHA-256 values or cross-check
  `generated_token_ids_sha256` and `token_count` against the actual generated
  token IDs carried by a canonical B0 report.
- The sidecar manifest's `panel` value is never compared with the parent
  `execution_descriptor.panel_hash`, despite the frozen report/manifest and
  same-SEV-battery binding. A deliberately different panel label builds.

Replace the partial check with one exact canonical B0 report validator. Because
the runner adds publication fields after `B0EvidenceBundle.seal()`, recompute the
inner digest over the exact base-bundle fields it originally seals, then validate
the runner fields, receipt invariants, and panel/manifest binding separately.
The tests must use canonical report shapes rather than teaching the validator to
accept an impossible partial parent.

### P1 - Parent-aware boundaries do not re-derive the generation-corpus digest

The normal builder correctly compares
`parent.generation_output_digest` with the corpus digest derived from the
verified report (`p5_r4_sidecar.py:568-573`). `_rederive_eligibility()` checks
only `b0_report_digest` before deriving eligibility and pair completeness
(`:656-678`). Therefore every public parent-aware consumer can accept a
hand-built, digest-consistent record whose real B0 digest and pair set are
correct but whose generation-corpus digest is false.

The exact-source probe used `"f" * 64` as that false digest. `_verify_record()`
passed, binding succeeded, `r4_decision()` returned `jsd_proceeds/c1=True`, and
`publish_r4_sidecar()` returned `integrity_verified` with the lie embedded. This
violates the frozen same-input rule that the comparison consume the generation
harness output digest, not a separate run
(`T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md:168-169`).

`record_r4_comparison()` is safe from this exact construction because it always
uses the builder, but direct bind/decision/publish were explicitly reviewed as
public hand-built-carrier boundaries. Add the generation-corpus comparison to
the single parent-aware re-derivation point and regression-test all three public
consumers.

### P1 - F4 capture-once custody is undone by later live digest reads

`_verify_record()` reads `output_digest` and `manifest_digest` once at
`p5_r4_sidecar.py:620-621`, but it returns only the thawed record. After
caller-controlled mapping callbacks have run, the public functions read the live
carrier attributes again into the link (`:695-696`), decision (`:749`), and
artifact (`:812-813`). `frozen=True` is not a custody boundary against
`object.__setattr__`, and the APIs accept caller mappings whose `items()` methods
run inside verification.

Direct bind and decision probes substituted `eeee..` / `ffff..` after the first
verification and emitted those unchecked values. A stateful report probe waited
until the third report snapshot inside publication; publication then returned
`integrity_verified` while the artifact's link referenced the originally
verified output digest and its decision/top-level fields referenced `ffff..`.
The decision remained `c1=True`.

Return an inert verified-sidecar snapshot containing the captured record and
both captured digests, and use only that snapshot in every output. Publication
should use internal helpers over one verified report/sidecar snapshot instead of
recursively reopening the live public carriers.

### P1 - A post-commit readback fault leaves a writable alias and no disposition

`os.link()` commits the final path at `p5_r4_sidecar.py:832`. The final-byte
`sidecar_path.read_bytes()` at `:836` is outside any post-commit exception
boundary. If it raises, temp-alias removal at `:838-843`, directory durability,
and the `R4PublishResult` at `:849-850` are never reached.

An injected final-read `OSError` reproduced the failure: the function raised
after commit while both `r4.json` and its writable `.tmp` hard link remained.
That directly contradicts the source's `never raise over a committed artifact`
claim at `:835` and the frozen no-surviving-writable-alias rule.

Make the whole post-link region a non-throwing terminal state machine. Every
readback, unlink, existence, and durability fault must best-effort remove the
alias and return the truthful committed failure/indeterminate disposition. Add
a regression that asserts both the returned disposition and alias state.

### P2 - Closed-world record validation rejects extras but not missing/root shape

The rev-5 `_RECORD_KEYS` check computes only
`set(thawed) - _RECORD_KEYS` (`p5_r4_sidecar.py:632-636`). It neither requires
set equality nor verifies that the thawed root is a mapping before indexing it.
A digest-consistent record missing `aggregate` escapes as raw `KeyError`; a
scalar root escapes as raw `TypeError`. The stale nested `eligibility` block is
correctly rejected, but the advertised exact record shape and typed-refusal
contract remain incomplete.

Validate the exact root type and exact key set before any indexing, and translate
all malformed-carrier failures to `R4SidecarError`.

### P2 - The result row schema and output digest do not implement frozen section 5.5

The frozen comparison contract names the raw evaluator field
`cosine_similarity` and requires the comparison-result rows to be sorted by
`(probe_a, probe_b)` before hashing
(`T_DIVERSITY_CONTINUATION_SIMILARITY_SPEC_2026-07-16.md:170-178`). The source
instead requires `embedding_similarity` (`p5_r4_sidecar.py:111`, `:478-483`) and
copies caller row order verbatim into the record (`:587`).

Two direct controls reproduced both mismatches: a contract-shaped
`cosine_similarity` row set is refused, while forward and reversed versions of
the same complete comparison both build but produce different output digests.
Use the frozen field name, canonicalize endpoint orientation and row order before
validation/sealing, and add an order-invariance regression. If the project wants
a different schema, amend and re-seat the normative contract first rather than
letting code and spec silently diverge.

## Accepted Scope

- Rev 5 removes caller-declared eligibility as record authority.
- Build, bind, decision, and publication re-derive eligibility from the verified
  report and check pair completeness against the derived eligible set.
- The original six-declared-over-zero-real exploit is refused before C1 state or
  publication.
- Unknown/deprecated top-level record keys, including stale `eligibility`, are
  refused.
- Polarity, recomputed aggregate statistics, endpoint-set completeness, the
  normal builder's generation-corpus check, terminal disposition gating, and
  model-free/out-of-process scope remain sound in the exercised paths.
- No finding here authorizes B0, C1, evaluator/model/GPU use, protected-sink
  deployment, Qdrant writes, numeric freeze, or keeper action.

## Exact Provenance

Pinned blobs at `e805a7550f322a8e23670d44ae07a4cdc9e24b9a`:

- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_r4_sidecar.py`: `25f881173a81e6980d385ac625b2b11de05920f0`
- `test_p5_r4_sidecar.py`: `c6997735d5b32234282602fc1f44e1a89ced6702`
- R4 comparison contract: `96809822137399344ff4c1f3889815a65538ce1d`

The interleaved Gemini drift-gate commit `7bd8f92` was excluded from this review;
it changes neither pinned P5 blob. The reviewed delta is the P5 path from
`5762974` through `5a01f06` and `e805a75` only.

## Verification

- Exact five-file model-free P5 suite from an immutable full archive:
  `426 passed, 1 skipped in 4.99s`.
- Exact focused R4 sidecar suite: `35 passed in 0.33s`.
- Focused Ruff, `py_compile`, and rev4-to-target `git diff --check`: clean.
- Twelve review-only model-free probes reproduced the accepted and defective
  behavior; the governed inner-digest probe was independently rerun by Codex.
- Independent read-only subreview returned `CHANGES` with the same four P1
  classes and exact-shape P2.
- No product source, model, GPU, Qdrant, B0/C1 run, remote host, experiment
  state, or deployment was changed by this review.

## Disposition

The exact rev-5 packet remains review-held. Repair the six findings as one
coherent custody pass and request a new immutable exact-source review. The
original rev-4 eligibility P1 is closed and should stay closed. All independent
protected-sink, live evaluator/B0, C1, numeric, keeper, #157, #168, World Model,
and bridge holds remain unchanged; no run is authorized.
