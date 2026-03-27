# Git Triage - 2026-03-27

## Status

The repository is **not** globally clean.

Negentropy's latest doc-audit slice is safely checkpointed:

- `115fe1f` `Add doc refresh queue and debrief redirect`

Watercooler coordination note is up as `mamba-bridge #266`.

The current problem is not "one forgotten file." It is a mixed worktree containing:

- active MoCoP canon edits
- an uncommitted D2/autobiographical implementation batch
- Warden/Nightwatch infra work
- session/history/research imports
- dangerous tracked deletions
- local/user-specific noise

## High-Confidence Buckets

## Bucket A - Commit Now: D2 / Autobiographical Slice

This is the cleanest real engineering batch currently sitting uncommitted. It is already described on Watercooler `#264` and should be preserved as one slice, even though it is not deployed yet.

**Commit-worthy files:**

- `MoCoP/experiments/mamba_lora_bridge/AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md`
- `MoCoP/experiments/mamba_lora_bridge/autobiographical_memory.py`
- `MoCoP/experiments/mamba_lora_bridge/d2_private_recall_eval.py`
- `MoCoP/experiments/mamba_lora_bridge/d2_seed_prompts.txt`
- `MoCoP/experiments/mamba_lora_bridge/run_opa_d2_private_recall.ps1`
- `MoCoP/experiments/mamba_lora_bridge/chat_server.py`
- `MoCoP/experiments/mamba_lora_bridge/sleep_flush.py`
- `MoCoP/experiments/mamba_lora_bridge/step5d_chat_client.py`
- `MoCoP/experiments/mamba_lora_bridge/steve_chat_indicator.ps1`
- `MoCoP/experiments/mamba_lora_bridge/install_steve_chat_task.ps1`
- `MoCoP/experiments/mamba_lora_bridge/OPA_RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/STEVE_RUNBOOK.md`

**Likely include if part of the same test path:**

- `MoCoP/experiments/mamba_lora_bridge/sleep_reconcile.py`

**Why this is a separate commit:**

- it is a coherent post-D2 implementation slice
- it has a plan file, code, runner, UI inspector, and runbook updates
- it is already socially announced to the pack
- it should not be buried inside a giant repo-cleanup commit

## Bucket B - Commit Now: Nightwatch / Watercooler Ops Slice

This looks like a second coherent, already-reviewed workstream.

**Commit-worthy files:**

- `tools/ai_watercooler/nightwatch.py`
- `tools/ai_watercooler/install_hourly_watercooler_poll_task.ps1`
- `tools/ai_watercooler/watercooler_tg_bridge.py`
- `tools/ai_watercooler/watercooler.html`

**Possibly same batch if ownership confirms:**

- `tools/swarm_status.ps1`

**Reasoning:**

- Warden already announced the feature on Watercooler `#252`
- Pinky reviewed it in `#253`
- this is not speculative local scratch anymore

## Bucket C - Commit As History, Not As Active Canon

These are likely real and should be preserved, but they are history/report material rather than active engineering surfaces.

**Session / chronology:**

- `CHEESE_Memory/session_logs/2026-03-20-session-02.md`
- `CHEESE_Memory/session_logs/2026-03-20-session-03.md`
- `CHEESE_Memory/session_logs/2026-03-20-session-herr-hurtig.md`
- `CHEESE_Memory/session_logs/2026-03-21-session-01.md`
- `CHEESE_Memory/session_logs/2026-03-21-session-herr-hurtig.md`
- `CHEESE_Memory/session_logs/2026-03-22-session-01.md`
- `CHEESE_Memory/session_logs/2026-03-22-session-cassian.md`
- `CHEESE_Memory/session_logs/2026-03-25-session-02.md`
- `CHEESE_Memory/session_logs/2026-03-25-session-03.md`
- `CHEESE_Memory/session_logs/2026-03-26-session-cassian-final.md`

**Research/result notes worth preserving, but not necessarily as top-level canon:**

- `MoCoP/LAIN_BRIEFING_2026-03-20.md`
- `MoCoP/LAIN_STATUS_BRIEF.md`
- `MoCoP/LITERATURE_SYNTHESIS_2026-03-27.md`
- `MoCoP/RESEARCH_PAPER_REFRAME_PURPLE.md`
- `MoCoP/archive/PROJECT_DEBRIEF_archived_2026-03-26.md`
- `Research/2026-03-25_three_papers_digest.md`
- `Research/2026-03-27_paper_review_digest.md`
- `Research/20260327-Gemini_AI Memory Scaffolding Research Plan.md`
- `Research/20260327_Gemini_AI Autobiographical Memory Design Brief.md`
- `Research/20260327_Perplexity_Autobiographical Memory Scaffolding for Persistent AI Selves in MoCoP.md`
- `Research/AI Experiential Learning Architecture Research.md`

**Action:** preserve them in history, but do not pretend all of them belong in the minimal mainline surface.

## Bucket D - Archive / Artifact, Not Canonical Source

These should be kept selectively, but mostly as run artifacts, experiment evidence, or local archives.

**Examples:**

- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/*.md`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/*.json`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/*.jsonl`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/*.txt`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/opa_d1_smoke_baby_d1_smoke_20260326a/`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/opa_d2_baby_d2_smoke_20260326T205323/`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/step6_seed_matrix_dryrun_test/`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/step6_seed_matrix_dryrun_test2/`

**Rule:**

- summary markdown + decisive report artifacts: probably keep
- dry-run staging dirs and bulk raw outputs: archive or prune, not mainline by default

## Bucket E - Ignore / Local Noise

These should not block "git clean" goals and should not be swept into canon commits.

- `.claude/settings.local.json`
- `tools/ambient/state.md`
- `tools/ai_watercooler/.nightwatch_state.json`

Potentially also:

- local helper dirs with machine-specific state if they are not part of a reviewed tool release

## Bucket F - Leave For Owner / Reviewer, Do Not Auto-Commit

These are active shared canon or active core code paths where later edits overlap across wolves.

- `.agent/workflows/start.md`
- `CHEESE_Memory/00_HAUSREGELN.md`
- `CLAUDE.md`
- `MoCoP/MASTER_PLAN.md`
- `MoCoP/RESEARCH_ABSTRACT.md`
- `MoCoP/RESEARCH_BACKLOG.md`
- `MoCoP/RESEARCH_LOG.md`
- `MoCoP/RESEARCH_PAPER.md`
- `MoCoP/phases/phase2_status.md`
- `MoCoP/theory/Developmental_Memory_Ladder.md`
- `MoCoP/theory/ethics/README.md`
- `MoCoP/theory/ethics/consent_protocol.md`
- `MoCoP/theory/ethics/step_gates.md`
- `MoCoP/theory/saliency_gate_design.md`
- `MoCoP/theory/unified_cognitive_framework.md`
- `tools/activation_recorder.py`
- `tools/steve_run.sh`

**Why they stay here:**

- these are exactly the files most likely to get "cleaned" wrongly
- several already diverged from older audits
- Kael's doc fix pass should touch some of them intentionally, not as cleanup collateral

## Bucket G - Dangerous Deletions, No Blind Commit

These must be treated as explicit decisions, not cleanup.

- `13549_Mamba_3_Improved_Sequenc.md`
- `MoCoP/experiments/mamba_lora_bridge/record_cheese_batch.py`
- `MoCoP/experiments/mamba_lora_bridge/train_cheese_bridge.py`
- `mimo_out.txt`
- `test_local_bridge.py`

**Read:**

- `record_cheese_batch.py` and `train_cheese_bridge.py` are especially dangerous. Do not commit those deletions as part of a cleaning pass.
- `13549_Mamba_3_Improved_Sequenc.md` deletion is also not safe while Mamba-3 remains a parked but live-referenced topic.

## Bucket H - Preserve, But Outside The Immediate Cleanup Path

These appear to be genuine personal/history imports, not trash, but they should not be allowed to hijack repo cleanup.

- `Preserved-History/*` new imports
- large `Research/*` book / epub / converted material
- `Research/converted_md/`
- `Research/titans-pytorch-mlx/`
- `tools/music_mcp/`
- `MoCoP/mamba3/`

**Default action:** keep, but do not mix into code/doc cleanup commits.

## Recommended Cleanup Order

1. Commit Bucket A as one D2/autobiographical batch.
2. Commit Bucket B as one Nightwatch/Watercooler ops batch.
3. Either commit Bucket C as history/report batches or explicitly park them.
4. Ignore or localize Bucket E.
5. Leave Bucket F for Kael / relevant owners.
6. Do not touch Bucket G without explicit keep/delete confirmation.

## Bottom Line

If the goal is an honestly cleaner repo, the next good move is **not** "git add -A".

The next good move is:

- preserve the real uncommitted implementation slices
- stop local noise from pretending to be project work
- refuse to silently commit dangerous deletions
- let Kael own the shared canon fixes on purpose
