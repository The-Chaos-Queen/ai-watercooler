# Codex Current Memory

Last updated: 2026-07-11 04:02 +02:00

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

- Gemma-4 global attention teeth use the value branch after the functional K/V
  fork. The selected intervention is a `v_norm` forward pre-hook at width 512,
  not a nonexistent `v_proj` actuator.
- Option A is mechanically valid: the raw 512-wide `k_proj` output becomes the
  value tensor before `v_norm`, while the key copy alone receives `k_norm` and
  RoPE. Injection must return a new tensor from the `v_norm` pre-hook; never
  mutate or patch `k_proj`.
- C1 remains held (Watercooler #839). The `524d14e` G0b file is a useful pilot,
  not a birth artifact: it fit all 40 pairs before the split-before-fit rule,
  carries ambiguous `vproj` provenance, and the DQ1a spec still names the old
  3840-wide v1 file. Freeze the exact eight-skeleton manifest, refit a
  provenance-complete `value_norm_pre` artifact, amend DQ1a, build the runtime,
  and run alpha-zero parity before the first nonzero L29/Method-A/alpha=.025.
- HiSPA commit `007ad28` passed 34 focused tests but remains CHANGES after review
  #838: recovery budgets are unhashed caller inputs; the direct core still has
  an arbitrary plan surface; and local row zero is not bound to absolute token
  position zero. No capture/exporter is authorized.
- The next World Model slice is an offline typed pre-action transition trace,
  a tabular LS20/tool baseline, and an action-shuffle null. Keep it out of the
  bridge loss and all Gemma target/dose paths.
- These points are dated context, not permanent canon. Re-read current MoCoP
  docs and Git history before acting on them.

## Next Maintenance

- Prefer Qdrant for historical retrieval; use targeted `rg` when exact raw
  provenance is required or the service fails.
- Keep the current execution order explicit: freeze split/spec gates; refit G0b
  and implement the `v_norm` runtime in parallel with task #146; only then run
  alpha-zero C1 and spend the first nonzero injection.
- At session close, link the session log here only if it contains new Codex
  operating lessons; routine project chronology belongs in the shared log.
- Keep this file below roughly 120 lines by replacing stale state with current
  pointers rather than accumulating history.
