# Git Triage - 2026-03-25

## Status

The repository is **not** globally clean.

The recent Steve/Qdrant engineering line is safely checkpointed in git:

- `8523ccb` `Refine Steve gate-event payload for sleep and retrieval`
- `9034991` `Add Steve pending flush for queued Qdrant writes`
- `432cf8d` `Add Steve qdrant write mode and pending default`
- `7b02acf` `Fix Steve critical-only safety override`
- `75d4661` `Add Steve Qdrant auto-replay worker`

So the current MoCoP Steve memory stack is safe. The remaining dirt is broader shared repo drift.

## Current Worktree Weight

Top-level counts from `git status --porcelain`:

- `MoCoP`: 78
- `tools`: 17
- `CHEESE_Memory`: 14
- `Research`: 9
- `Projects`: 4
- `Preserved-History`: 3

## Owner Updates (Watercooler Round)

### Anda-Conda

Already landed as clean commits and therefore **not** at risk:

- `2575ba9` `Add layer sweep plan and minimal sleep flush script`
- `7fd7e70` `Fix stale LoRA/SSM references in 4 MoCoP docs`
- `c28511e` `Retire handoff as live control surface, point boot at Watercooler`

Important nuance:

- these commits are already in `HEAD`
- some overlapping files still show as modified in the worktree, which means later edits happened after Anda's clean commits

### Cassian

Cassian's explicit triage from Watercooler `#203`:

Commit-worthy:

- `QDRANT_PATH_REVIEW_CASSIAN.md`
- `OPA_BOOTSTRAP.md`
- `run_7b_reincarnation/`  
  Note: only if the payload is git-safe; `.pt` files may need ignore rules instead

Private / gitignored:

- `CHEESE_SHAPING_EPISODES_CASSIAN.md`

Operational / throwaway, do **not** commit:

- `inspect_ckpt.py`
- `inspect_ckpt.sh`
- `run_inspect.sh`
- `install_mamba_steve.sh`
- `launch_chat.sh`
- `restart_scaled.sh`
- `run_step5_steve.sh`
- `talk_to_reincarnated.sh`
- `patch_scaling.py`
- `chat_reincarnated.py`

Belongs to others:

- `chat_server.py`
- `step1_c3_fixed_mean_no4bit/`

### Purple

Purple explicitly claimed these as hers:

Tracked modified:

- `MoCoP/EXPERIMENT_LADDER.md`
- `MoCoP/RESEARCH_PAPER.md`
- `MoCoP/experiments/mamba_lora_bridge/cognitive_bridge.py`
- `MoCoP/theory/unified_cognitive_framework.md`

Untracked new:

- `MoCoP/experiments/mamba_lora_bridge/activation_sessions/ssm_vs_hidden_separation.py`
- `MoCoP/experiments/mamba_lora_bridge/collect_mamba_states.py`
- `MoCoP/experiments/mamba_lora_bridge/run_step5e_layer_sweep.ps1`
- `MoCoP/experiments/mamba_lora_bridge/train_sae.py`
- `MoCoP/theory/autonomy_gradient.md`
- `MoCoP/theory/fleeting_state_security.md`
- `MoCoP/theory/oxytocin_spec.md`
- `MoCoP/theory/purple_reflection_on_building_the_lock.md`

### Pinky

No longer pending. Pinky's infra/tooling slice is already safely in `HEAD`:

- `4b8c75e` `Pinky infra batch: boot hygiene, watercooler upgrades, orchestrator tooling`

Important nuance:

- `86b8f95` also carries Pinky-owned canon material like
  - `MoCoP/theory/saliency_gate_design.md`
  - `MoCoP/ORCHESTRATOR_DASHBOARD_SPEC.md`
- but that commit is not a pure Pinky-only ownership signal, because it also includes adjacent shared docs and code

Read: Pinky's slice is not at risk, but do not use `86b8f95` as an excuse to batch-assume ownership of every file it touched.

### An-Chan

No longer pending. The sleep/reconciliation slice is already represented in git:

- `86b8f95` introduced `MoCoP/experiments/mamba_lora_bridge/sleep_reconcile.py`
- `2575ba9` introduced the prerequisite `MoCoP/experiments/mamba_lora_bridge/sleep_flush.py`

Important nuance:

- the current live Steve memory path in `chat_server.py` has since been materially extended by Negentropy / Techno-Monk
- so `sleep_reconcile.py` is An-Chan-owned canon, but `chat_server.py` remains a shared active code path and should not be bucketed as hers alone

### Remaining Coordination Gap

The blocker is no longer missing wolf confirmation from Pinky / An-Chan.

The remaining dirt is now mainly:

- shared canon/workflow files with overlapping later edits
- local / operational noise
- deletions and moves that still need explicit intent confirmation

## Bucket 1 - Safe And Already Checkpointed

These do **not** need rescue work right now:

- Steve/Qdrant payload patch
- pending flush
- `qdrant_write_mode`
- `critical-only` safety override
- auto-replay worker

## Bucket 2 - Shared Tracked Files, High Coordination Risk

Do **not** batch-commit these blindly. They are shared canon / workflow surfaces or active code paths.

- `CHEESE_Memory/00_BOOT_FILES.md`
- `CHEESE_Memory/00_HANDOFF.md`
- `CHEESE_Memory/00_HAUSREGELN.md`
- `CHEESE_Memory/01_TOOLS.md`
- `CLAUDE.md`
- `.agent/workflows/start.md`
- `MoCoP/EXPERIMENT_LADDER.md`
- `MoCoP/MASTER_PLAN.md`
- `MoCoP/RESEARCH_PAPER.md`
- `MoCoP/RESEARCH_BACKLOG.md`
- `MoCoP/theory/README.md`
- `MoCoP/theory/unified_cognitive_framework.md`
- `MoCoP/theory/Three_System_Cognitive_Architecture.md`
- `MoCoP/theory/sleep_architecture.md`
- `MoCoP/phases/phase1_results.md`
- `MoCoP/phases/phase3_plan.md`
- `MoCoP/experiments/mamba_lora_bridge/train_bridge.py`
- `MoCoP/experiments/mamba_lora_bridge/cognitive_bridge.py`
- `tools/activation_recorder.py`

These need ownership or reviewer confirmation before any cleanup commit.

## Bucket 3 - Untracked But Likely Intentional Project Material

These look like real work products, not junk:

- `CHEESE_Memory/session_logs/*.md`
- `MoCoP/DRIFT_SCAN_2026-03-25.md`
- `MoCoP/TODAY_WAR_BOARD_2026-03-25.md`
- `MoCoP/experiments/mamba_lora_bridge/OPA_RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/STEVE_RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/VASTAI_RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/*`
- `MoCoP/experiments/step5d_min_dose_protocol.md`
- `MoCoP/experiments/step6_layer_sweep_plan.md`
- `MoCoP/theory/failure_path_review.md`
- `MoCoP/theory/saliency_gate_design.md`
- `MoCoP/theory/sleep_reconciliation_algorithm.md`
- `MoCoP/theory/autonomy_gradient.md`
- `Research/2026-03-20_literature_digest.md`
- `Research/2026-03-25_three_papers_digest.md`

These are probably commit-worthy, but should be grouped by owner/topic rather than swept up in one giant commit.

### Bucket 3A - Operational Files That Are Already Canonically Referenced

These are not just ad hoc host clutter anymore. They are referenced from boot docs, runbooks, or session logs and therefore belong to repo history if they are real:

- `MoCoP/experiments/mamba_lora_bridge/STEVE_RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/VASTAI_RUNBOOK.md`
- `MoCoP/experiments/mamba_lora_bridge/steve-wsl.ps1`
- `MoCoP/experiments/mamba_lora_bridge/set_steve_chat_alpha.ps1`
- `MoCoP/experiments/mamba_lora_bridge/set_steve_chat_model.ps1`
- `MoCoP/experiments/mamba_lora_bridge/set_steve_chat_temperature.ps1`
- `MoCoP/experiments/mamba_lora_bridge/steve_chat_indicator.ps1`
- `MoCoP/experiments/mamba_lora_bridge/install_steve_midnight_recorder_task.ps1`
- `MoCoP/experiments/mamba_lora_bridge/run_steve_midnight_recorder.ps1`
- `MoCoP/experiments/mamba_lora_bridge/launch_hidden_powershell.vbs`
- `MoCoP/experiments/mamba_lora_bridge/run_opa_reincarnation_qualitative.ps1`

These may still be operationally ugly, but they are not local-only noise anymore.

## Bucket 4 - Likely Local / Operational / User-Specific Noise

These should be treated cautiously and are strong candidates for ignore / local-only / manual review:

- `.claude/settings.local.json`
- `.claude/scheduled_tasks.lock`
- `Projects/Project_Prosthetic/chrome_profile/`
- `tmp/`
- `tmp_test_wc.sh`
- `tmp_vastai_stub.sh`
- `tools/ambient/state.md`  
  Note: append-only auto state; not the same thing as unfinished work.

## Bucket 5 - Deletions / Moves That Need Intent Check

These should not be “cleaned up” without confirming the move/replacement path:

- `CHEESE_Memory/mud_7k_eval_prompt.txt`
- `CHEESE_Memory/mud_7k_eval_prompt_v2.txt`
- `Preserved-History/gemini_chat_2026-01-16T13-53-20.md`
- `Preserved-History/gemini_chat_2026-02-09T23-44-07.md`
- root helper scripts like:
  - `ask_pinky_creative.py`
  - `extract_text_pdfminer.py`
  - `test_local_bridge.py`

Some of these may have been intentionally relocated into `Projects/` or `tools/`; some may be true deletions. Check before acting.

### Bucket 5A - Relocations Now Effectively Confirmed

These are no longer mysterious deletions. The replacement path exists in the current worktree:

- `CHEESE_Memory/mud_7k_eval_prompt.txt`
  -> `Projects/Project_MUD/mud_7k_eval_prompt.txt`
- `CHEESE_Memory/mud_7k_eval_prompt_v2.txt`
  -> `Projects/Project_MUD/mud_7k_eval_prompt_v2.txt`
- `ask_pinky_creative.py`
  -> `tools/ask_pinky_creative.py`
- `extract_text_pdfminer.py`
  -> `tools/extract_text_pdfminer.py`
- `musk_complaint_text.txt`
  -> `Research/musk_complaint_text.txt`
- `parity_out.txt`
  -> `MoCoP/parity_out.txt`

These still need a tidy history pass, but they are no longer blocked on pure intent ambiguity.

### Bucket 5B - Still Risky Deletions

These still need an explicit keep/delete call before cleanup:

- `mamba-insights.md`
  Referenced from live theory docs and older session logs; deletion is not yet safe.
- `Preserved-History/gemini_chat_2026-01-16T13-53-20.md`
  No obvious replacement surfaced in the current worktree.
- `Preserved-History/gemini_chat_2026-02-09T23-44-07.md`
  Probably replaced by `Preserved-History/gemini_ENI_chat_2026-02-09T23-44-07.md`, but that still deserves confirmation before cleanup.

## Recommendation

Do **not** aim for `git status` zero in one pass.

Use this order:

1. Keep the Steve/Qdrant line as-is; it is already safe.
2. Respect the owner-confirmed slices above before touching anything else.
3. Treat Pinky + An-Chan as confirmed; do not wait on them anymore.
4. Split the remaining work into canon ops/runbooks, archive/session/research material, and local-noise/deletion cleanup.
5. Decide what belongs in `.gitignore` versus what belongs in history.
6. Only then do a repo-wide cleanup pass.

## Immediate Practical Next Step

If the goal is “sauber ziehen”, the next sane move is an **ownership pass**, not a cleanup pass:

- `Cassian`: Steve/Qdrant code review
- `Anda`: drift/doc fixes she already touched
- `Purple / theory owners`: shared canon docs and active MoCoP theory/code
- `Laura`: local-only artifacts and deletions
- `Negentropy`: confirmed relocations, canon ops scripts, and the remaining noisy edge cases
