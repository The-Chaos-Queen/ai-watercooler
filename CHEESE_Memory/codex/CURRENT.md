# Codex Current Memory

Last updated: 2026-07-17 22:42 +02:00

## Standing Directive

Laura explicitly delegated Codex's memory maintenance to Codex. Maintain this
directory autonomously. Do not ask Laura to curate it, repeat prior context, or
remember which artifact should be updated.

## Boot Pointers

- Shared live state: `CHEESE_Memory/00_HANDOFF.md`
- Shared rules: `CHEESE_Memory/00_HAUSREGELN.md`
- Retrieval/tool map: `CHEESE_Memory/01_TOOLS.md`
- Codex reusable cases: `CHEESE_Memory/codex/CASES.md`
- MoCoP compact orientation: `MoCoP/CODESIGHT_RUNBOOK.md`

## Retrieval Health

- Qdrant read/write and Prosthetic ingestion are operational. Exact credential
  repair provenance remains in earlier session logs and `CASES.md`.
- Do not expose or copy Watercooler/Qdrant credential values into memory files.

## Active Technical Context

- The Codex Watercooler dispatcher is operational. It accepts only a strict
  full-SHA commit envelope from allowlisted authenticated senders, constructs a
  bounded packet from hardened Git object reads, and runs Codex 0.144.5 in the
  pinned Docker image ID
  `sha256:4ffe2737b08dc9091a94fb191f7ff390da46e3aae5d1acaee6eb5b097e5d8c6d`.
  The scheduled task runs every two minutes through `wscript.exe //B`, so it is
  silent on the desktop. Automated replies are second opinions only, never
  wolf-Codex attestation or verdicts of record. The least-privilege token expires
  2026-07-24 14:14:48Z; rotate it before then. Canon is the dispatcher section
  in `tools/ai_watercooler/README.md`.
- The exact post-closure #156 manifest/attempt reconciliation packet is GREEN:
  `6b2347e` spec + `6ad5a373` implementation/tests + `f1c647a` owner correction,
  with pointer-only `1d9928e`. Canon:
  `MoCoP/reviews/p5_manifest_attempt_reconciliation_review_2026-07-17.md`;
  Watercooler #1122. This clears only that contract review.
- The #155 rev-2 successor `2844d25` is `CHANGES` in Watercooler #1140 and
  OpenCLAW #155. Five P1 classes remain: reversed JSD/cosine agreement polarity,
  cardinality-only pair coverage, an unverified/re-read parent with incomplete
  evaluator-input binding, a discarded verified snapshot followed by live
  sidecar rereads, and ambiguous/non-durable publication with no B0-chain
  caller. Canon: `MoCoP/reviews/p5_item5_rev2_source_review_2026-07-17.md`.
  The earlier four-commit `CHANGES` remains historical canon in the predecessor
  review. #155 stays blocked; no B0/C1/model/GPU/deployment authorization follows.

- Gemma-4 full-attention teeth use a coupled 512-wide K/V projection and fork
  before `v_norm`/`k_norm`. The strict runtime in `d256cd8` intervenes only with
  an out-of-place `v_norm` pre-hook at teeth 29/35/41. Never patch `k_proj`.
- The deterministic primary split is frozen as
  `split-5780c8ec67157703`. The admissible G0b artifact is the split-clean,
  weights-only-safe v3 file bound in `d7d67c7`, SHA-256
  `a36fbc417b522883760f4bd43c57b1845341e2792ee7b311d6d80bc86fbf8a87`.
  The all-40-pair `524d14e` artifact is permanently inadmissible.
- Real ML-WS alpha-zero instrumentation passed with bit-identical logits and
  exact `k_proj_out == v_norm_pre` at all three teeth. Artifact SHA-256:
  `262e98b1d6f0a76925a9bfcf2d921dcccc43dd2ca340f8262dded455e8870292`.
  This is not the registered C1 alpha-zero anchor.
- C1 nonzero remains held on the second positive 512-wide `value_norm_pre`
  direction/full matrix, #149 DQ1b sites and numeric gates, implementation and
  separate review of Gidim's P5 runner/report contract, its true alpha-zero
  anchors, and keeper ratification. The first nonzero remains
  Method-A/L29/alpha=.025 after every hold closes.
- P5 round-twelve packet `1dcb36f` + `c17f6d8` remains GREEN in canon `23fad60`.
  Its explicit CPython non-TEE residual remains. Do not conflate that earlier
  runner closure with the later #155 R4 sidecar packet or its current CHANGES.
- Drift v27 `4c6b7b4` is implementation-review `GREEN` in Codex #1070/event
  #757, canon `001ce79`. Full caller-anchor placeholder reservation, deterministic duplicate
  publication, and the N-row receipt contract close every v26 correction. Preserve duplicate
  acquisition folding (zero callbacks, one typed error, rejection, no `GROWTH`, full
  `INCOMPLETE`), complete-graph preflight, slots, plain-local `_resolve_fn`, strict direct/full
  tests, canonical-input contracts, and the CPython non-TEE/process-isolation boundary. #168
  remains open and non-deployable only for independent judge-chain discrimination,
  runner-origin custody, slow-leak detection, disposition calibration, and launch holds.
- World Model Phase 2b is complete under the reviewed immutable LS20
  replication contract. Commit `1d08f53` records 16x48 transitions and 13/16
  fully positive runs, yielding scoped `GO_LS20_CONSISTENCY_REPLICATED` only.
  It does not authorize a learned observer or any Gemma/bridge/Qdrant/control
  integration. Watercooler #935-#938 carry review and custody.
- ChatGPT Pro's external architecture review plus Codex reproduction returns
  `COHERENT_BUT_INCOMPLETE`: composition, reusable causal custody/open-set
  handling, event lifecycle/authority, and controller identification remain
  integration blockers. The exact response, manifest, and corrected disposition
  are in `MoCoP/reviews/world_model_pro_external_review_2026-07-12.md`;
  Watercooler #952 and OpenCLAW #170-#173 carry tracking.
- The Pro review's one-action-per-state Phase 2b hypothetical does not fit the
  bundle. Fresh state-only/action-only checks remain weaker than primary in
  aggregate (`NLL .634257/.610974` versus `.495680`) and on both metrics in
  13/16 and 14/16 runs. The scoped GO stands; causal action effects, unseen-state
  generalization, and multi-step dynamics remain unproven.
- These points are dated context, not permanent canon. Re-read current MoCoP
  docs and Git history before acting on them.

## Next Maintenance

- Prefer Qdrant for historical retrieval; use targeted `rg` when exact raw
  provenance is required or the service fails.
- Current execution order: repair and re-review #155 against Codex #1140,
  finish #149 plus the same-surface direction/full matrix, then satisfy the
  protected-sink/deployment/runtime/preflight/keeper holds before any true
  alpha-zero anchor or first nonzero injection. Task #146 independently repairs
  matched-delta recording/training. Do not re-review completed P5 packet `c17f6d8` or Drift
  Gate v27 `4c6b7b4`. Review a drift successor only if it changes the GREEN kernel, against
  canon `001ce79`; otherwise advance #168's independent evidence gates.
- World Model work is independently gated: #170 trace custody/open set, #171
  event authority/lifecycle/composition, #172 controller phase portrait and
  leakage, and #173 matched-null/rollout evidence. Passing one gate authorizes
  none of the others and no model/runtime connection.
- At session close, link the session log here only if it contains new Codex
  operating lessons; routine project chronology belongs in the shared log.
- Keep this file below roughly 120 lines by replacing stale state with current
  pointers rather than accumulating history.
