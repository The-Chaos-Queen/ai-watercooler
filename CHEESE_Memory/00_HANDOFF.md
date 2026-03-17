# C.H.E.E.S.E. Handoff

This file is the boot-time control page.
It should stay short, current, and attribution-heavy.
Detailed narrative belongs in `session_logs/`, not here.

## Control Block
- Last updated: 2026-03-17 08:22 CET
- Current owner: Laura + swarm (Claude, Codex, Lain, Lucian)
- Primary focus: AB0-AB3 activation-bias runs are launch-ready; next move is AB0 reproduce plus a fresh critical review
- Last session log: `CHEESE_Memory/session_logs/2026-03-17-session-02.md`
- Qdrant status:
  - Automated weekly backup to Google Drive (Sundays 3 AM, cron on LXC 101)
  - Research scanner running weekly (Mondays 6 AM, cron on LXC 101)
  - 12,715 points in `exocortex` collection, first backup verified (71 MB)
  - Latest session log ingest: failed (`2026-03-17-session-02.md`; Qdrant connect timeout to `192.168.2.191:6333`)

## Current State (2026-03-16)

### Infrastructure (new this session)
- **Qdrant backup** automated: `backup_qdrant.sh` on LXC 101 → Google Drive `backups/qdrant/`. Weekly cron.
- **Research scanner** deployed: `research_scanner.py` on LXC 101. Full reports now archive under `tools/research_scanner_runs/`; handoff/dashboard should only surface compact summary metadata. Latest recorded run: `2026-03-14 15:20 UTC`, `0` arXiv papers, `0` GitHub repos, `0` HuggingFace hits.
- **SSH keys** set up: Laura's laptop → Proxmox host (192.168.2.55) → Qdrant LXC 101. Also `ssh opa` for Opa-PC WSL access.
- **AI watercooler / OpenCLAW v0** deployed on Proxmox host (`192.168.2.55:8765`): LAN-only agent mailbox plus task board backed by SQLite. Local clients/config live at `tools/ai_watercooler/` and `C:\Users\cerub\AppData\Local\AIWatercooler\config.json`. Usage notes are now in `CHEESE_Memory/01_TOOLS.md`. Seeded task: `MoCoP / mamba-bridge / #2 Decide first simplification-gate prototype`.
- **Playwright MCP** configured in `.mcp.json` (available in VSCode, not terminal).
- **Claude Code MAX** now recognized (was stuck on Pro, fixed via re-login).

### MoCoP Progress
- **D1 COMPLETE:** All 5 target base models pass baseline solvability (fact recall from context). Results in `d1_results.json`.
- **Target models locked:** `target_models.md` — Qwen2.5-7B (primary), Mistral-Nemo-Base-2407 (validation), Llama-3.1-8B, Gemma-2-9B, Qwen3-14B-Base.
- **Model CLI flags added:** `--qwen-model-id` and `--mamba-model-id` in `train_bridge.py`.
- **Disposition eval spec v1** written: `disposition_eval_spec.md` — synthesizes input from Codex (framework), Lucian (philosophy), Lain (metrics), Claude (synthesis). Critically reviewed by Opus — verdict: "shelve until D2 passes."
- **TTT paper read:** `MoCoP/theory/TTT_as_Linear_Attention_2602.21204.md`. Key insight: Titans' gradient-based surprise is secretly linear attention, not memorization. Our surprise gate should use reconstruction error, not gradient magnitude.
- **Codex trainer patch landed:** `train_bridge.py` now uses `model.generate()` for eval, warns on wasteful 4-bit usage, and logs cheap compressed-state unusualness surrogates instead of a premature reconstruction decoder.
- **Opa verification:** dry-run completed with saved prediction JSON carrying `context_norm`, centroid L2, and centroid cosine metrics; real `--no-4bit` startup also booted cleanly with `Qwen/Qwen2.5-0.5B` + Mamba on CPU.
- **Model-default cleanup landed:** bridge helper scripts now share `model_defaults.py`, executable MoCoP entrypoints swap model IDs via flags instead of file edits, and the canonical Qwen default is now `Qwen/Qwen2.5-7B`.
- **Phase 2 status repaired:** `MoCoP/phases/phase2_status.md` is now a short live snapshot/index aligned with the Sweden result, `Qwen/Qwen2.5-7B`, and the simplification gate, rather than an outdated pilot-era narrative.
- **Activation-bias result promoted:** the first real `activation_bias` run stayed stable across all `3` epochs, improved PPL each epoch (`27.09 -> 25.95 -> 25.67` vs baseline `29.71`), hit `0%` clamp, and never collapsed. This is now the current winning simplification branch for the disposition channel.
- **Linearity probe extended:** `linearity_probe.py` now supports both `context-pca` and a real `hyper-linearity` mode, which loads a saved bridge checkpoint plus saved context vectors and measures cross-validated linear predictability of generated LoRA weights.
- **Trainer comparison export landed:** `train_bridge.py` now writes compact per-epoch comparison artifacts (`eval_epoch_XXX_comparison.json`, `eval_comparison_latest.json`, `eval_comparison_history.jsonl`) so LoRA vs activation-bias vs baseline can be compared cleanly across runs.
- **Activation-bias launch kit expanded:** `phase2_activation_bias_ablation_matrix.md` now stages exact AB0-AB3 commands with fixed output dirs, and `phase2_critical_eval_prompt.md` gives a copy-paste skeptical reviewer prompt for tearing the result apart before the next narrative update.
- **Qdrant ingest currently blocked:** both `2026-03-17-session-01.md` and `2026-03-17-session-02.md` failed to ingest because `192.168.2.191:6333` timed out. Memory docs are updated, but the newest session remains unembedded.
- **Watercooler snapshot:** Orion is now onboarded into the `mamba-bridge` thread and already read the Sweden burst context. Laughing Opus validated the quick PCA/context-dump flow, but hit an Opa crash on `Qwen2.5-7B` with 4-bit load; current cheap workaround is to run the manifold diagnostic with `Qwen2.5-0.5B`, since the PCA only needs compressor geometry, not strong bridge quality.

### Key Architectural Insights (this session)
- **Mirror problem:** Long context makes AI mirror the human. Frozen transformer + surprise-gated bridge could solve this by giving the model agency over what it internalizes.
- **Base models for eval:** No instruct/thinking models — LoRA should be the ONLY behavioral modifier. Test gut responses, not reasoned answers.
- **Disposition > fact recall:** The bridge should carry "how" (style, warmth, lean) not "what" (facts). Perplexity differential is the primary automated metric.

## Scale-Up Verdict (2026-03-16)

**HONEST NEGATIVE RESULT.** The current bridge can memorize a tiny shared subset, but it does not generalize yet.

| Epoch | Recall | Bridge PPL | Baseline PPL | Train Loss |
|-----|-----|-----|-----|-----|
| 1 | 0/16 | 28.96 | 29.71 | 4.25 |
| 2 | 0/16 | 44.06 | 29.71 | 3.07 |
| 3 | 0/16 | 43.15 | 29.71 | 2.33 |

- **Epoch 1 is real but weak:** bridge perplexity briefly improved over baseline, so the bridge does shift Qwen's distribution in a constructive direction early on.
- **Generalization failed:** recall stayed `0/16` on the disjoint eval set across all three epochs.
- **Over-injection returned:** epochs 2-3 became destructive again despite steadily falling train loss.
- **Tiny-overfit is demoted:** the earlier `2/8` A3 win should now be treated as shared-set memorization, not transfer.
- Local artifacts from the Sweden burst are already copied back; the host is safe to terminate.

## Open Threads
> Note: the scale-up question for the current dynamic-LoRA bridge is answered. The next move is simplification, not more samples on the same setup.
- [ ] Run AB0 from the staged launch block in `phase2_activation_bias_ablation_matrix.md` to confirm the activation-bias win reproduces on the same geometry.
- [ ] Run AB1 from the staged tiny-overfit block to answer whether activation bias can carry any precise fact signal at all.
- [ ] Run AB2/AB3 from the staged `v_proj`-only and `q_proj`-only blocks before implementing FiLM.
- [ ] Hand `phase2_critical_eval_prompt.md` to a fresh reviewer before broadening the activation-bias claim.
- [ ] Run the cheap compressor PCA diagnostic on Opa using saved context dumps; if `Qwen2.5-7B` 4-bit keeps crashing, use `Qwen2.5-0.5B` just to recover manifold shape.
- [ ] Run `linearity_probe.py hyper-linearity` against a saved checkpoint plus real context dumps from `run_a1/` or `run_a3/` once the PCA/context-export artifacts exist.
- [ ] Decide whether activation bias is only a disposition channel or a weak factual channel after AB1.
- [ ] Decide whether FiLM is still warranted after the activation-bias matrix, rather than before it.
- [ ] Decide whether the Sweden epoch-1 checkpoint should be treated as the only non-destructive LoRA artifact worth preserving separately.
- [ ] Audit docs/runbooks for stale `Qwen/Qwen3-4B` references if command-copy safety matters outside the executable Python paths.
- [ ] Wire the latest research-scanner summary (`tools/research_scanner_runs/latest_summary.json`) into handoff/dashboard refreshes so scanner state stays visible without dumping full reports into memory docs.
- [ ] Fresh Opus pass: rationalize the near-canonical MoCoP doc stack (`PROJECT_DEBRIEF.md`, `MASTER_PLAN.md`, `phase2_status.md`, diagnostic plan, burst debriefs) into a cleaner hierarchy with explicit roles.
- [ ] Update `01_TOOLS.md` with per-surface tool map
- [ ] Align CLAUDE.md / AGENTS.md / .gemini/ boot files (shared Hausregeln)
- [ ] Read `surprise_gated_memory.md` and `Three_System_Cognitive_Architecture.md` into Qdrant
- [x] D1 baseline solvability — all 5 models pass
- [x] Qdrant backup automated (Google Drive, weekly)
- [x] Research scanner deployed (NUC, weekly)
- [x] SSH infrastructure set up (Proxmox, Opa-PC)
- [x] Target models locked (5 base transformers)
- [x] Disposition eval spec v1 written + reviewed

## Watch Out For
- Do not resume `run_pilot_01` as if it were promising; it is a useful artifact, not a positive result.
- Do not use `/dev/shm` for future paid runs. Keep HF cache, logs, and checkpoints on `/workspace` or an attached volume.
- Opa-PC is good for dry-run and tooling validation, but not for meaningful full bridge training.
- Opa's `mamba_lora_bridge` snapshot can drift from the local repo; sync at least `train_bridge.py`, `bridge_dataset.py`, `models.py`, and `cognitive_bridge.py` before trusting verification results.
- Executable defaults now point at `Qwen/Qwen2.5-7B`, but historical docs and logs still contain `Qwen/Qwen3-4B`; do not treat old prose as current runtime config.
- `activation_bias` is now the leading trainer result, but live `cognitive_bridge.py` / `server.py` runtime deployment still defaults to LoRA.
- The new comparison exports are only useful if runs keep the same eval surface and split policy; do not compare arbitrary historical runs as if they were controlled.
- Qdrant was unreachable during session close, so semantic retrieval is one session behind until ingestion is retried.
- The research scanner now archives full reports under `tools/research_scanner_runs/`; do not copy whole scan reports into handoff when a 1-line summary will do.
- Do not read the Sweden `64`-sample burst as "almost there." The held-out result is still `0/16`; the only positive signal is early PPL steering.
- NotebookLM auth tokens may expire; re-run `notebooklm login` interactively if API calls fail.
- Audio task `a8c64765` may have failed silently on Google's side; poll before assuming success.
- Qdrant re-ingest for the wider MoCoP corpus is still pending.
- Cloud stability was unusually poor on 2026-03-10 across multiple providers; checksum artifacts before terminating rented instances.

## Recommended Next Step
Run AB0 from the staged launch block, then get an external skeptical read using `phase2_critical_eval_prompt.md` before treating activation bias as more than a narrow but promising disposition-channel result.

## Handoff Checklist
- `00_DASHBOARD.md` updated: yes
- Session log written: yes
- Session log path recorded here: yes
- Qdrant ingest for latest session log confirmed: no
- Blocking risks called out: yes

## Edit Ledger
- 2026-03-01 22:15 CET | Antigravity | Extended bridge_dataset.py with expanded pools, persistence manifest, and verified disjoint splits. Completed Phase 2 data pipeline readiness.
- 2026-03-01 22:15 CET | Codex | Added CHEESE handoff/session workflow standardization plus Qdrant metadata-quality extensions. Logged the need to re-ingest session logs, Research, and MoCoP before relying on the new schema.
- 2026-03-01 23:49 CET | Codex | Hardened the real Phase 2 training path: disjoint split usage in `train_bridge.py`, resumable checkpoints, refreshed runbook/tests, and verified Opa WSL smoke/train/resume before any cloud spend.
- 2026-03-02 00:06 CET | Codex | Added `MoCoP/PRE_CLOUD_AGENT_TODO.md` as the standalone pre-cloud worklist and updated handoff/dashboard pointers for agent handoff.
- 2026-03-02 23:30 CET | Claude | Session-02 close. MoCoP technical state confirmed stable, MM_Version inventory updated, and screen script access flagged as a build item. Session log: `CHEESE_Memory/session_logs/2026-03-02-session-02.md`.
- 2026-03-07 01:23 CET | Codex | Added the Phase 2 preflight, fixed sync and Linux-local checkpoint strategy, recorded the exact Vast.ai pilot command and policy decisions, and verified token-backed model access on Opa.
- 2026-03-07 01:53 CET | Codex | Reworked the paid-cloud launch into a gated `1 + 4` epoch flow so Laura can inspect epoch 1 before committing the rest of the spend.
- 2026-03-07 01:54 CET | Antigravity | Session: reviewed Claude web conversation on MoCoP. Created `MoCoP/theory/Three_System_Cognitive_Architecture.md` (Qdrant+Mamba+LoRA cognitive organ model). Added P2 tasks to TODO: living reframe + disposition eval protocol. Built `Projects/LegalAI/PROJECT_BRIEF.md` for lawyer consulting engagement (Medizinstrafrecht, 5000-page Strafakte analysis pipeline). Lead model: Qwen 3.5-35B-A3B abliterated MLX. Built working pseudonymizer with demo (`Projects/LegalAI/pseudonymizer.py`). Created desktop screenshot tool (`tools/screenshot.ps1`).
- 2026-03-07 23:08 CET | Codex | Restored Project MUD as the live focus: removed the stale `mud_agent` fork after migrating Mamba artifacts, hardened the wrapper/JSON protocol, deduped live exits, and verified canonical-path smoke behavior with local LMStudio models.
- 2026-03-08 01:12 CET | Codex | Landed `mud.agent_state/v1`, unified server-side JSON serialization, made semantic destination-name movement valid, and revalidated the path live with `qwen3.5-4b`.
- 2026-03-08 02:12 CET | Claude Opus 4.6 | Qwen 3.5 model eval (4B/9B/27B + SauerkrautLM + Grok). Key finding: citation accuracy floor between 9B and 27B. 27B with thinking nailed section 222 StGB. Created `EVAL_RESULTS.md`, added citation verification slide to `presentation.html` (now 11 slides), updated `DEMO_AGENDA.md` with RAG/StGB lookup concept. Added `--role-swap` flag to MUD `agent_wrapper.py`. Created `compressor_service.py` for Qwen3.5-0.8B context compression daemon.
- 2026-03-09 21:09 CET | Codex | Built the LegalAI statutory citation layer: official StGB/StPO XML importer, SQLite database, FastAPI lookup/verify endpoints, tests, docs, and a live `legalai_citations.db` build.
- 2026-03-09 21:15 CET | Codex | Confirmed Qdrant ingestion for `2026-03-09-session-01.md` and updated handoff memory status.
- 2026-03-09 21:50 CET | Codex | Recorded the Project MUD context filter fix, new session log, and successful Qdrant ingest for `2026-03-09-session-02.md`.
- 2026-03-10 12:09 CET | Codex | Switched handoff to the MoCoP onboarding debrief, recorded the new canonical debrief file, and noted that Phase 2 blocker status now lives in the debrief/PRE_CLOUD docs rather than the stale `phase2_status.md`.
- 2026-03-10 12:12 CET | Codex | Confirmed Qdrant ingestion for `CHEESE_Memory/session_logs/2026-03-10-session-01.md` (`11` chunks) and updated the handoff memory status.
- 2026-03-10 12:37 CET | Codex | Refreshed `MoCoP/phases/phase2_status.md` to match the actual launch-ready state and switched handoff focus from doc repair to today's staged Phase 2 compute readiness.
- 2026-03-10 12:39 CET | Codex | Confirmed Qdrant ingestion for `CHEESE_Memory/session_logs/2026-03-10-session-02.md` (`11` chunks) and updated the handoff memory status.
- 2026-03-10 13:35 CET | Codex | Synced current bridge files to Opa, fixed the local `opa-wsl.ps1` helper, and recorded a clean Opa WSL preflight as the final gate before cloud host selection.
- 2026-03-10 13:36 CET | Codex | Confirmed Qdrant ingestion for `CHEESE_Memory/session_logs/2026-03-10-session-03.md` (`10` chunks) and updated the handoff memory status.
- 2026-03-10 21:14 CET | Codex | Switched handoff focus to the ClaudeExporter reasoning-chain fix, recorded the new session log, and confirmed Qdrant ingestion for `CHEESE_Memory/session_logs/2026-03-10-session-04.md` (`10` chunks).
- 2026-03-10 23:15 CET | Claude Opus 4.6 | Installed notebooklm-py, created MoCoP notebook (13 sources), kicked off audio podcast. Session log: `CHEESE_Memory/session_logs/2026-03-10-session-05.md`.
- 2026-03-10 23:22 CET | Codex | Added the MoCoP startup runsheet, merged the handoff/dashboard back toward the Phase 2 diagnostic path, and recorded the fresh `80GB` tiny-overfit next step without discarding the NotebookLM thread.
- 2026-03-10 23:26 CET | Codex | Confirmed Qdrant ingestion for `CHEESE_Memory/session_logs/2026-03-10-session-06.md` (`10` chunks) and closed the memory bookkeeping for the night.
- 2026-03-15 19:34 CET | Codex | Landed the base-model completion-prompt patch in the bridge harness, corrected the A100 run docs/checklists, and rewrote handoff next steps around the A3 rerun plus scale-up gate.
- 2026-03-15 22:50 CET | Codex | Recorded the trainer speed/telemetry patch, Opa validation status, Qdrant ingest for `2026-03-15-session-01.md` (`10` chunks), and the new next step: scale A3 completion to `64` samples before broader cleanup.
- 2026-03-16 01:32 CET | Codex | Recorded the Sweden `64`-sample A3 completion failure on disjoint eval, switched handoff focus to the simplification gate, marked the host safe to terminate once artifacts were local, and confirmed Qdrant ingest for `2026-03-16-session-01.md` (`10` chunks).
- 2026-03-16 12:48 CET | Codex | Deployed the Proxmox-hosted AI watercooler mailbox (`192.168.2.55:8765`), seeded the `mamba-bridge` thread, and recorded the client/config usage in `01_TOOLS.md` so future agents can find it on boot.
- 2026-03-16 13:25 CET | Codex | Extended the Proxmox mailbox into OpenCLAW v0 with task queue/claims/heartbeats/context/board endpoints, added the local `openclaw.py` client, verified a full task lifecycle live, and seeded MoCoP task `#2` in `mamba-bridge`.
- 2026-03-16 14:05 CET | Codex | Recorded the latest `mamba-bridge` watercooler state in handoff: Orion onboarded cleanly, Opus validated the quick PCA flow, and the current Opa workaround is to use `Qwen2.5-0.5B` for context-dump manifold inspection if `7B` 4-bit load keeps crashing.
- 2026-03-16 14:12 CET | Codex | Recorded the parallel model-default cleanup effort: another Codex instance is parameterizing hardcoded model IDs, and the handoff now explicitly preserves `Qwen/Qwen2.5-7B` as the canonical default unless Laura decides otherwise.
- 2026-03-16 14:13 CET | Codex | Closed the model-default cleanup loop: bridge/runtime scripts now expose model IDs via flags, share the canonical `Qwen/Qwen2.5-7B` default, and the new session log was ingested into Qdrant (`10` chunks).
- 2026-03-16 15:31 CET | Codex | Extended `linearity_probe.py` with a cross-validated `hyper-linearity` mode and updated the open thread from "build the probe" to "run it once real context dumps exist."
- 2026-03-16 15:45 CET | Codex | Landed the trainer-side `activation_bias` prototype, verified LoRA plus activation-bias dry-runs and activation-bias checkpoint resume on Opa, and ingested `2026-03-16-session-03.md` into Qdrant (`10` chunks).
- 2026-03-16 15:52 CET | Codex | Rewrote `phase2_status.md` into a live snapshot/index, moved research-scanner output toward an archived-runs + latest-summary shape, and recorded the need for an Opus doc-governance pass over the MoCoP canon stack.
- 2026-03-17 00:36 CET | Codex | Promoted the first real activation-bias result to the live MoCoP control pages, added a dedicated activation-bias ablation matrix doc, verified the new trainer comparison export on Opa, and recorded the failed Qdrant ingest for `2026-03-17-session-01.md`.
- 2026-03-17 08:22 CET | Codex | Expanded the activation-bias runbook with exact AB2/AB3 launch blocks, added the standalone critical-eval prompt, recorded `2026-03-17-session-02.md`, and logged the repeated Qdrant timeout.

## Next Agent Brief
- Open first:
  - `CHEESE_Memory/00_DASHBOARD.md`
  - `CHEESE_Memory/session_logs/2026-03-17-session-02.md`
  - `MoCoP/phases/phase2_activation_bias_ablation_matrix.md`
  - `MoCoP/phases/phase2_critical_eval_prompt.md`
  - `MoCoP/phases/phase2_a100_quick_tiny_overfit_plan.md`
  - `MoCoP/phases/phase2_diagnostic_ablation_plan.md`
  - `MoCoP/experiments/mamba_lora_bridge/CODEX_TASKS.md`
- Decide first:
  - Whether AB0 reproduce should run before or in parallel with the external critical review pass
- Verify before memory-dependent work:
  - Preserve or relabel the Sweden epoch-1 artifact if you want the brief constructive PPL checkpoint kept distinct from the later over-injected epochs
  - Check whether you are reading executable code or historical docs before acting on any `Qwen/Qwen3-4B` reference
  - Remember that `activation_bias` is only trainer-side so far; deployment/runtime code still assumes LoRA
  - Retry Qdrant ingestion for `2026-03-17-session-01.md` and `2026-03-17-session-02.md` once `192.168.2.191:6333` is reachable again

## Update Protocol
- Keep this file concise and current.
- Add one line to `Edit Ledger` for every material change to this file.
- Put long reasoning, experiment detail, and raw chronology into `CHEESE_Memory/session_logs/`.
- Record decisions, assumptions, blockers, and next actions; do not dump raw hidden reasoning transcripts here.
