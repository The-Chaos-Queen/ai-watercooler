# Gemini Doc Refresh Staging Guide (2026-04-09)

Purpose: separate Gemini's likely stale-doc refresh from unrelated code, artifact, and runtime churn in the current uncommitted worktree.

This is a review/staging guide only. It does not assume everything listed here should be committed. The main goal is to avoid one giant mixed commit.

## Read First

- The worktree is not "just docs." There are active code/runtime changes in the bridge stack, website files, Watercooler tooling, and many experiment artifacts.
- `CHEESE_Memory/session_logs/` has both modified existing logs and many new untracked logs. Because session logs are append-only by house rule, do not commit modified old logs blindly.
- `CHEESE_Memory/00_HANDOFF.md` was materially reframed toward "architecture rework first / D2 deferred." That is a semantic control-surface change, not a harmless refresh.

## Bucket A: Likely Safe Doc/Archive Candidates

These look like the core "stale docs moved out of the way" refresh.

Root deletions with corresponding archive additions:

- `CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/Phase1_Mamba_Memory_Probe.md`
  -> `MoCoP/archive/05_EXPERIMENT_DEBRIEFS/Phase1_Mamba_Memory_Probe.md`
- `CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/Phase2_Bridge_Dataset_Update.md`
  -> `MoCoP/archive/05_EXPERIMENT_DEBRIEFS/Phase2_Bridge_Dataset_Update.md`
- `CHEESE_Memory/concepts/Gemini_Feedback_Peer_Review`
  -> `MoCoP/archive/concepts/Gemini_Feedback_Peer_Review`
- `CHEESE_Memory/concepts/model_communication_protocol.md`
  -> `MoCoP/archive/concepts/model_communication_protocol.md`
- `MoCoP/DOC_REFRESH_TASKS_2026-03-27.md`
  -> `MoCoP/archive/DOC_REFRESH_TASKS_2026-03-27.md`
- `MoCoP/DRIFT_SCAN_2026-03-25.md`
  -> `MoCoP/archive/DRIFT_SCAN_2026-03-25.md`
- `MoCoP/LAIN_BRIEFING_2026-03-22.md`
  -> `MoCoP/archive/LAIN_BRIEFING_2026-03-22.md`
- `MoCoP/LAIN_HANDOFF_2026-03-18.md`
  -> `MoCoP/archive/LAIN_HANDOFF_2026-03-18.md`
- `MoCoP/LAIN_NEUROSCIENCE_REVIEW_2026-03-22.md`
  -> `MoCoP/archive/LAIN_NEUROSCIENCE_REVIEW_2026-03-22.md`
- `MoCoP/LITERATURE_SYNTHESIS_2026-03-27.md`
  -> `MoCoP/archive/LITERATURE_SYNTHESIS_2026-03-27.md`
- `MoCoP/ORCHESTRATOR_DASHBOARD_SPEC.md`
  -> `MoCoP/archive/ORCHESTRATOR_DASHBOARD_SPEC.md`
- `MoCoP/TODAY_WAR_BOARD_2026-03-26.md`
  -> `MoCoP/archive/TODAY_WAR_BOARD_2026-03-26.md`
- `MoCoP/mocop-review-lain.md`
  -> `MoCoP/archive/mocop-review-lain.md`
- `MoCoP/phases/phase3_plan.md`
  -> `MoCoP/archive/phase3_plan_archived_2026-03-31.md`
- `MoCoP/experiments/mamba3_migration_memo.md`
  -> `MoCoP/mamba3/mamba3_migration_memo.md`
- `13549_Mamba_3_Improved_Sequenc.md`
  -> `MoCoP/mamba3/13549_Mamba_3_Improved_Sequenc.md`

Likely-safe accompanying additions:

- `MoCoP/README.md`
- `CHEESE_Memory/INFRASTRUCTURE.md`
- `MoCoP/archive/GDN_GKA_ARTIFACT_MATRIX_2026-04-03.md`
- `MoCoP/archive/GDN_GKA_GATE_RESEARCH_LADDER_2026-04-03.md`
- `MoCoP/archive/GDN_GKA_PARALLEL_TASKS_2026-04-03.md`
- `MoCoP/archive/LAIN_BRIEFING_2026-03-20.md`
- `MoCoP/archive/LAIN_STATUS_BRIEF.md`
- `MoCoP/archive/PROJECT_DEBRIEF_archived_2026-03-26.md`
- `MoCoP/archive/RESEARCH_PAPER_REFRAME_PURPLE.md`
- `MoCoP/archive/SLEEP_LITERATURE_NOTES_2026-03-29.md`
- `MoCoP/archive/TODAY_WAR_BOARD_2026-03-25.md`
- `MoCoP/mamba3/mamba-insights.md`

## Bucket B: Docs That Need Human Review Before Any Docs Commit

These are documentation, but they change canon, boot behavior, or research interpretation.

Control surfaces / boot:

- `CHEESE_Memory/00_HANDOFF.md`
  - Important: current diff changes project control from `D2 -> Step 6` framing to `architecture rework first / D2 deferred`.
  - That conflicts with the current ladder canon unless consciously accepted.
- `CHEESE_Memory/00_BOOT_FILES.md`
  - Converts boot to a lean 3-item startup.
  - Probably good, but it is a policy change.
- `CHEESE_Memory/00_HAUSREGELN.md`
  - Restores "handoff is live" and adds rules 10-11.
  - Looks sensible, but still policy.
- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `MoCoP/CONTRIBUTING.md`

Research canon / interpretation:

- `MoCoP/EXPERIMENT_LADDER.md`
- `MoCoP/MASTER_PLAN.md`
- `MoCoP/RESEARCH_ABSTRACT.md`
- `MoCoP/RESEARCH_BACKLOG.md`
- `MoCoP/RESEARCH_LOG.md`
- `MoCoP/RESEARCH_PAPER.md`
- `MoCoP/phases/phase2_status.md`
- `MoCoP/phases/phase2_diagnostic_ablation_plan.md`
- `MoCoP/theory/Developmental_Memory_Ladder.md`
- `MoCoP/theory/README.md`
- `MoCoP/theory/convergence_log.md`
- `MoCoP/theory/ethics/step_gates.md`
- `MoCoP/theory/unified_cognitive_framework.md`
- `CHEESE_Memory/laura.md`
- `Preserved-History/INDEX.md`

Experiment/runbook docs that are probably valid but are not "Gemini stale-doc refresh":

- `MoCoP/experiments/mamba_lora_bridge/STEP6_REPLICATION_PLAN.md`
- `MoCoP/experiments/mamba_lora_bridge/STEP6_RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/STEVE_RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/BURST_2_DEBRIEF.md`
- `MoCoP/experiments/mamba_lora_bridge/CODEX_TASKS.md`
- `MoCoP/experiments/mamba_lora_bridge/disposition_eval_spec.md`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_qdrant_auto_replay_20260325.md`

## Bucket C: Do Not Include In A "Gemini Doc Refresh" Commit

These are unrelated or too mixed:

Code/runtime:

- all modified `.py`, `.ps1`, `.json` under `MoCoP/experiments/mamba_lora_bridge/`
- `tools/activation_recorder.py`
- `tools/ai_watercooler/*`
- `tools/steve_run.sh`
- `.agent/workflows/*`
- `.claude/settings.local.json`
- `.mcp.json`

Website/app churn:

- `Projects/hurtig/site/*`
- `Projects/hurtig/contact-form/`

Session logs / archives:

- all modified existing files under `CHEESE_Memory/session_logs/`
- all untracked new files under `CHEESE_Memory/session_logs/`
- bulk untracked content under `Preserved-History/`
- bulk untracked `Research/` imports/exports

Experiment artifacts / generated outputs:

- untracked experiment result folders under `MoCoP/experiments/mamba_lora_bridge/`
- trajectory outputs
- step5e result folders
- paired activation outputs
- local tmp / smoke artifacts

## Suggested Commit Split

### Commit 1: Gemini stale-doc refresh / archive cleanup

Use only Bucket A, and only after a quick spot-check that each deletion really has the intended archive destination.

### Commit 2: canon/control-surface refresh

Only after explicit review of Bucket B, especially:

- `CHEESE_Memory/00_HANDOFF.md`
- `CHEESE_Memory/00_BOOT_FILES.md`
- `CHEESE_Memory/00_HAUSREGELN.md`
- `MoCoP/EXPERIMENT_LADDER.md`
- `MoCoP/RESEARCH_LOG.md`

### Later commits

- bridge/runtime code
- website changes
- session-log ingestion / archive imports

## Suggested Git Add Skeleton

Archive-only batch:

```powershell
git add `
  MoCoP/archive `
  MoCoP/mamba3 `
  CHEESE_Memory/INFRASTRUCTURE.md `
  MoCoP/README.md
```

Then selectively stage the matching deletions:

```powershell
git add -u `
  CHEESE_Memory/05_EXPERIMENT_DEBRIEFS `
  CHEESE_Memory/concepts `
  MoCoP/DOC_REFRESH_TASKS_2026-03-27.md `
  MoCoP/DRIFT_SCAN_2026-03-25.md `
  MoCoP/LAIN_BRIEFING_2026-03-22.md `
  MoCoP/LAIN_HANDOFF_2026-03-18.md `
  MoCoP/LAIN_NEUROSCIENCE_REVIEW_2026-03-22.md `
  MoCoP/LITERATURE_SYNTHESIS_2026-03-27.md `
  MoCoP/ORCHESTRATOR_DASHBOARD_SPEC.md `
  MoCoP/TODAY_WAR_BOARD_2026-03-26.md `
  MoCoP/mocop-review-lain.md `
  MoCoP/phases/phase3_plan.md `
  MoCoP/experiments/mamba3_migration_memo.md `
  13549_Mamba_3_Improved_Sequenc.md
```

Review staged result before committing:

```powershell
git diff --cached --stat
git diff --cached
```

## Recommendation

If you want the least risky next move:

1. commit only Bucket A first
2. leave Bucket B unstaged until we review the canon changes consciously
3. leave Bucket C alone for separate commits

That gives you a clean Gemini housekeeping commit without entangling our live bridge work.
