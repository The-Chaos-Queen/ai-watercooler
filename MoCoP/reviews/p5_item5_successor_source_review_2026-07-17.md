# P5 Item 5 Successor Source Review

**Date:** 2026-07-17
**Reviewer:** Codex
**OpenCLAW:** `#155`
**Review request:** Watercooler `#1135`
**Runtime contract:** `e1b9f4a9`
**R4 comparison contract:** `8c42be1442c8c35edaff94dbe81489a7a800554d`
**Implementation chain:** `bd674ac71c38c498a65ba11d747df3a873a00df5` ->
`e1178c0ade401a6f247490d1cd83a66c96d1119b` ->
`86c37481883f915ad2210e7b3dc9a28a65b1ba22` ->
`66698844e41ca8cc8ce00b9e8170a69466c3fdf3`

**Verdict:** `CHANGES` on the exact four-commit packet.

## Findings

### P1 - The sealed sidecar remains mutable and the binder publishes a stale digest

`R4SidecarRecord` is frozen only at the dataclass attribute layer. Its `record`
field still points to ordinary nested dictionaries and a list
(`p5_r4_sidecar.py:245-251`, `:301-318`). After `output_digest` is computed, a
caller can mutate any evaluator, parent, row, or aggregate field. The binder
does not recompute the digest; it combines the stored digest with values read
from the now-mutated record (`:322-347`).

Direct exact-source repro:

```text
build -> output_digest = old
mutate record.evaluator.evaluator_id and aggregate.spearman_rho
canonical_digest(record) != old
bind_to_parent_report(...) succeeds
link.sidecar_output_digest == old
link.evaluator_id == mutated-evaluator
```

The result is an audit link whose named evaluator and claimed sidecar digest do
not describe the same bytes. Normalize to one owned exact-JSON snapshot before
hashing, prevent callers from mutating the sealed representation, and require
the binder/publisher to recompute and compare the sidecar digest before use.

### P1 - Validation and custody can observe different caller-owned values

The manifest and comparison validators accept arbitrary `Mapping` and
`Sequence` implementations and repeatedly enumerate/index them
(`p5_r4_sidecar.py:123-136`, `:154-180`, `:183-242`). The builder then iterates
and copies those inputs again only after validation (`:297-314`). A stateful
sequence returned valid numeric rows during validation and string-valued rows
during the later copy; the malformed strings were accepted and sealed:

```text
TOCTOU_ACCEPTED {'pair_id': 'p0',
                 'jsd': 'not-a-number',
                 'embedding_similarity': 'also-bad'}
iterations 2
```

This reopens the exact malformed-but-JSON failure that `6669884` intended to
close. At the public boundary, require recursively exact built-in JSON types,
take one owned snapshot, and validate/hash/publish only that snapshot. No
later read or iteration may return to caller-owned objects.

### P1 - The same-generation check is a repeated caller assertion, not a parent binding

`build_r4_sidecar()` compares `manifest.parent.generation_output_digest` only
to a second argument supplied by the same caller (`p5_r4_sidecar.py:278-290`).
`bind_to_parent_report()` checks only the B0 `published_digest`; it never derives
or verifies a generation-output digest from the sealed report (`:322-347`). The
primary runner records individual generation hashes and L-token receipts
(`p5_b0_run.py:1966-2007`) but publishes no canonical aggregate generation
digest (`:2014-2031`).

An exact-source repro built a sidecar whose generation digest was `ff...ff` and
successfully linked it to a parent containing a generation hash of `00...00`.
Therefore the current check cannot establish owner acceptance item 2 or the R4
contract's same-input requirement (`T_DIVERSITY...md:168-170`).

Define one canonical generation-corpus digest over the sealed parent records,
including the prompt/panel identity and L-token/stop receipts. Produce it from
the trusted B0 evidence path and verify it from the sealed report when binding;
do not accept the same unverified string through two caller-controlled inputs.

### P1 - The comparison schema accepts impossible or unrelated gate evidence

The numeric validator checks only exact numeric type and finiteness
(`p5_r4_sidecar.py:139-150`, `:183-242`). It accepted this record:

```text
pair_id = arbitrary
jsd = -7.0
embedding_similarity = 3.5
spearman_rho = 2.0
n_pairs = 1
```

The frozen metric contract defines JSD in bits on `[0, 1]`
(`T_DIVERSITY...md:67-71`, `:110`); cosine similarity and Spearman rho are each
bounded by `[-1, 1]`. One pair cannot supply a meaningful rank-correlation gate.
More importantly, the validator never recomputes rho from the stored pair rows,
so an arbitrary in-range `0.8` can be declared regardless of the evidence.
It also omits the required mean-pairwise embedding aggregate and accepts any
unique pair IDs/count rather than the complete pair set implied by the frozen
SEV corpus (`T_DIVERSITY...md:166-171`).

Pin the exact row/pair schema to the parent corpus, enforce metric domains and
minimum/complete coverage, emit the required aggregate, and recompute the
preregistered statistic from the stored rows using a frozen polarity and tie
policy. The value that decides `rho < 0.7` cannot remain caller-authored.

### P1 - The required journal/publication path does not exist

Owner acceptance `#1128` requires a companion manifest/validator **and
journal**. The module says it validates and journals the comparison
(`p5_r4_sidecar.py:1-27`) but exposes only in-memory object builders
(`:254-348`). There is no durable writer, atomic/no-replace publication,
terminal disposition, or non-test caller anywhere in the reviewed tree.
Consequently the output digest is not bound into a published B0 evidence chain,
which the normative R4 contract still describes as unbuilt
(`T_DIVERSITY...md:169-172`).

Add a reviewed no-replace sidecar/link publication transaction and integrate it
with the sealed parent evidence flow, or explicitly provide and bind the
existing journal implementation if it lives elsewhere. Returning a mutable
dictionary is not a journal.

## Accepted Scope

- The evaluator remains out of the P5 monitor process. No
  `sentence_transformers`, `transformers`, `torch`, or evaluator execution was
  added to `p5_r4_sidecar.py`; the owner-defined process boundary is preserved.
- The design correctly avoids rewriting the already-published primary B0
  report. The required repair belongs in a no-replace referrer/sidecar
  transaction, not by mutating the parent artifact.
- The earlier closed-world decoding, explicit load-routing, token/stop, and
  wall-time source repairs remain in the reviewed lineage. No additional static
  finding was established against those portions in this pass.
- The known torch-gated HF wiring and target-native runtime receipts remain
  declared residuals; this model-free review does not convert them into
  executed evidence.

## Exact Provenance

Pinned blobs at `66698844e41ca8cc8ce00b9e8170a69466c3fdf3`:

- runtime contract: `7425688363e9694c7553f9e3b996faad8bd34915`
- R4 comparison contract: `6e75192a61641459f7b20a2cb8cd4ca4418643ab`
- `p5_b0_harness.py`: `26fb474d0aa45dbd3cf9c4c582554bd720edd331`
- `p5_b0_run.py`: `a04499b6b6abb2418344cf47b9beced612f55f0b`
- `p5_r4_sidecar.py`: `9b915670f3ef49f0337c3fbcdc4e3027b4a307ef`
- harness tests: `c64c017c44b3f790de4d1484ad240db20af91f5f`
- runner tests: `4bdb79895207e4c36e21e4598ce2c11ee5282b56`
- sidecar tests: `12a468ace570df8b902b0c94dced6914121097fd`

## Verification

- exact HEAD: `66698844e41ca8cc8ce00b9e8170a69466c3fdf3`
- five-file model-free P5 suite: `456 passed, 1 skipped in 4.83s`
- focused Ruff over the six changed implementation/test paths: clean
- `py_compile` for harness, runner, and sidecar: clean
- scoped `git diff --check`: clean
- four adversarial source probes reproduced the mutable-record,
  validation/copy TOCTOU, domain, and false same-generation-binding failures
- the broader five-file Ruff invocation also reports two pre-existing unused
  imports in `test_p5_dq1b_monitor.py` and `test_p5_recovery.py`; neither file is
  changed by this packet and neither affects the focused result
- no model, GPU, remote deployment, protected sink, B0 forward, C1 action,
  Qdrant path, or experiment state was touched

The Watercooler `#1135` count of `457 passed` is corrected to pytest's actual
summary: `456 passed, 1 skipped` (457 collected).

## Disposition

The exact four-commit #155 packet remains review-held. This `CHANGES` verdict
does not reopen the accepted out-of-process evaluator decision or the earlier
decoding/load-routing repairs. It also does not alter the independent protected
sink/launch-manifest, staged deployment, target-native CUDA/HF receipt, B0
preflight, #149 freeze, or keeper-GO holds. No run is authorized.
