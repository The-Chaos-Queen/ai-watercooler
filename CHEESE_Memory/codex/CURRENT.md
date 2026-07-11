# Codex Current Memory

Last updated: 2026-07-11 11:53 +02:00

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
- C1 nonzero remains held only on committed DQ1b monitor sites/numeric gates;
  full C1 also needs a second positive 512-wide `value_norm_pre` MVB direction.
  The first nonzero remains Method-A/L29/alpha=.025 with monitors and timestamp.
- Monk's HiSPA v2 evaluator at `cb4125b` is GREEN (#842), and Isegrim ratified
  its terminology/threshold shape (#843). This approves the offline read-only
  evaluator only; a capture exporter/model hook remains a separately reviewed
  slice.
- World Model Phase 1 landed in `e6358a4`: typed pre-action trace v2,
  null/tabular/oracle/shuffle baselines, strict held-out leakage checks, and
  corrected null semantics in the disposition runner. OpenCLAW #148 is the
  next real-trace LS20/tool collection lane. Keep it outside bridge loss and
  Gemma dose paths.
- Integrated package verification: 314 passed, 45 deselected, 5 subtests.
- These points are dated context, not permanent canon. Re-read current MoCoP
  docs and Git history before acting on them.

## Next Maintenance

- Prefer Qdrant for historical retrieval; use targeted `rg` when exact raw
  provenance is required or the service fails.
- Current execution order: DQ1b monitor/gate freeze plus a same-surface MVB
  direction; build/review the C1 geometry/behavior recorder; run its true
  alpha-zero anchor; only then spend the first nonzero injection. Task #146
  independently repairs matched-delta recording/training. Task #148 collects
  and scores real World Model traces offline.
- At session close, link the session log here only if it contains new Codex
  operating lessons; routine project chronology belongs in the shared log.
- Keep this file below roughly 120 lines by replacing stale state with current
  pointers rather than accumulating history.
