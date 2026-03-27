# MoCoP Project Debrief

> [!CAUTION]
> **Superseded onboarding surface.**
> This path is kept as a redirect because older logs, dashboards, and notes still point here.
> It is **not** the current authoritative project narrative.

## Read This Instead

For current state, read these in order:

1. `MoCoP/WHY.md`
2. `MoCoP/EXPERIMENT_LADDER.md`
3. `MoCoP/RESEARCH_LOG.md`
4. `CHEESE_Memory/00_HANDOFF.md`
5. `MoCoP/RESEARCH_BACKLOG.md`

If you need the concrete replication path, then read:

6. `MoCoP/experiments/mamba_lora_bridge/STEP6_REPLICATION_PLAN.md`

## Current Reality Snapshot

- The original dynamic LoRA bridge path is historical. The live mechanism is **activation bias injection** into Qwen `v_proj` layers `12-15`.
- The canonical Mamba input is **Layer 3 `hidden_last_token`**. Mean-pooled states, token windows, and SSM recurrent states are empirically ruled out for the current bridge.
- Steps **1 through 5f** are effectively passed on the ladder.
- Growth Ladder **D0** (private birth namespaces) and **D1** (selective private-write formation) are real.
- The current frontier is **D2 cue-based recall** versus the **Step 6 multi-seed replication path**.

## Historical Long-Form Debrief

The older long-form debrief is preserved for historical context at:

- `MoCoP/archive/PROJECT_DEBRIEF_archived_2026-03-26.md`

Use that file as an archive, not as the current onboarding surface.
