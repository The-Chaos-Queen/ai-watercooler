# Codex Current Memory

Last updated: 2026-07-15 00:30 +02:00

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

- Qdrant authentication is operational. On 2026-07-11, both read and write
  probes returned HTTP 200, Prosthetic recall succeeded, and the three failed or
  pending July 10 session logs were ingested (37 requested chunks total).
- Root cause of the earlier 401: the PowerShell profile exported 44-character
  padded Base64 strings while the live container stored the same key strings
  without the trailing padding character. The profile now normalizes its runtime
  exports to match the container.
- Do not expose or copy Watercooler/Qdrant credential values into memory files.

## Active Technical Context

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
- DQ1a math hardening landed in `e9c64d8`; Gidim/Isegrim/Cairn returned GREEN
  in Watercooler #852-#854. Clarifications in `b3d4821` preregister the P5
  dispersion cap, forbid post-hoc rescue of a dispersion-only failure, and
  make the attempt/birth/death ordering explicit. OpenCLAW #150 is complete.
- C1 nonzero remains held on the second positive 512-wide `value_norm_pre`
  direction/full matrix, #149 DQ1b sites and numeric gates, implementation and
  separate review of Gidim's P5 runner/report contract, its true alpha-zero
  anchors, and keeper ratification. The first nonzero remains
  Method-A/L29/alpha=.025 after every hold closes.
- P5 round-twelve packet `1dcb36f` + `c17f6d8` is GREEN in canon `23fad60`.
  Exact-list checks precede all restore/checkpoint protocols; malformed objects are
  untouched and fail closed; identity duplicates, persistent swaps, full real-import
  matrix, constant refusal, and prior custody/publication repairs pass. #156's model-free
  implementation/review scope is complete. Watercooler #1014 and OpenCLAW events
  #729/#731 record the verdict and closure. The explicit CPython non-TEE residual remains.
  No B0, #155, #149, HF audit,
  protected-sink, alpha-zero, keeper, or nonzero authorization follows.
- Drift v9 `e2b19ec` remains `CHANGES / P1` in Codex #1021/event #733, canon
  `5d9d0f5`. Preserve its exact `ProbeResult` rejection and field-built resolver row.
  The enclosing snapshot is still caller-controlled: an exact `AuditRecord` with exact
  rows plus undeclared copy-hook state, or an `AuditRecord` subclass, softens protected
  `HARD` to `PASS` during `deepcopy`. #168 remains open/non-deployable pending a closed
  field-by-field current/history parser with exact record/container/leaf boundaries.
  Cairn #998 GREENed the A1/Case 07b ethics wording; external calibration holds remain.
- Monk's HiSPA v2 evaluator at `cb4125b` is GREEN (#842), and Isegrim ratified
  its terminology/threshold shape (#843). This approves the offline read-only
  evaluator only; a capture exporter/model hook remains a separately reviewed
  slice.
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
- Kang et al.'s 2026 cerebellum-inspired memtransistor paper is indexed in
  `bee3a1e` as an adjacent prediction-error/event-trigger reference. It supports
  evaluating a cheap novelty interrupt after raw trace custody, not a learned
  transition model, event authority, appraisal, rollout, or integration claim.
  Watercooler #967 and `Research/2026-07-13_cerebellum_memtransistor_novelty_gate.md`
  carry the bounded mapping to #170/#171.
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
- Current execution order: finish #149 plus the same-surface direction/full
  matrix; record P5 closure; run its true alpha-zero anchors; only then spend
  the first nonzero injection. Task #146 independently repairs
  matched-delta recording/training. Do not re-review completed P5 packet `c17f6d8`.
  Review only an immutable drift successor to `e2b19ec` against `5d9d0f5`.
- World Model work is independently gated: #170 trace custody/open set, #171
  event authority/lifecycle/composition, #172 controller phase portrait and
  leakage, and #173 matched-null/rollout evidence. Passing one gate authorizes
  none of the others and no model/runtime connection.
- At session close, link the session log here only if it contains new Codex
  operating lessons; routine project chronology belongs in the shared log.
- Keep this file below roughly 120 lines by replacing stale state with current
  pointers rather than accumulating history.
