# C.H.E.E.S.E. Handoff

This file is the boot-time control page.
It should stay short, current, and attribution-heavy.
Detailed narrative belongs in `session_logs/`, not here.

## Control Block
- Last updated: 2026-03-21 14:10 CET
- Current owner: Laura + swarm (Techno-Monk/Codex, Pinky, Gemini, Cassian, Laughing Opus, Anda/Purple, Lain, Lucian, Pontodoros, Herr Hurtig)
- Primary focus: Cloud-backed next eval and theory review. Steve browser/runtime cleanup is partially repaired, but the host is paused because Steve needs the laptop back right now.
- Last session log: `CHEESE_Memory/session_logs/2026-03-20-session-04.md`
- Qdrant status:
  - `00_HANDOFF.md` is not ingested by default
  - Latest session log ingest: done (`CHEESE_Memory/session_logs/2026-03-20-session-04.md`, `10` chunks)

## Current State
- Step 5 "Adrenaline Bridge" wiring is fixed in git: `c251c0c` (1.5B wiring), `7a69452` (target-width hardening), and `a5bdd52` (Mamba runtime compat shim).
- Fresh 1.5B target captures on Opa are confirmed at `256` width for all three CHEESE episodes. The bad artifact was the stale checkpoint, not the current recorder.
- Opa retrained a fresh checkpoint `cheese_reincarnation_bridge_1.5b_codexfix.pt` with loss `11.424964 -> 0.013400`.
- Opa now has `mamba-ssm==2.3.1` installed plus the missing `selective_state_update` export, and both mixed CPU/GPU and all-GPU reincarnation smokes completed successfully.
- The all-GPU smoke already passed on the 8GB RTX 3070 with small token limits, so the 4090/A100 should be the next real eval surface.
- Steve's browser `chat_server.py` is patched for the correct 1.5B hidden-last-token compressor geometry and now serves on the LAN at `http://192.168.2.49:7860`.
- The supposed second Steve "crash" was false: the server kept running in WSL and only looked dead because `tasklist` does not see WSL `python3`.
- A new canonical `MoCoP/experiments/mamba_lora_bridge/chat_server.py` now exists locally with neutral `Laura` / `Reply` framing, blank-reply guard, and per-turn transcript persistence.
- A Windows-native Steve launcher/task stack now exists locally (`launch_chat_windows.ps1`, `install_steve_chat_task.ps1`, `stop_steve_chat_task.ps1`, `inspect_steve_chat_task.ps1`) and was partially deployed. The old `MoCoP WSL Keeper` path is no longer the intended future.
- The remaining Steve blocker is narrow: the Windows `portproxy` still needs to be updated dynamically to the current WSL IP instead of looping through `127.0.0.1:7860`. Work stopped there because Steve needed the laptop back.

## Open Threads
- [x] Watercooler `/v1/tasks/next` principal-binding fix — deployed by Pinky, verified by Codex
- [x] Mamba Layer 3 state separation — PASS (last-token cosine 0.036, Pinky)
- [ ] Run codex-fixed 1.5B checkpoint on 4090/A100 with `--max-new-tokens 100`+ for real qualitative eval
- [ ] Resume Steve host cleanup when the laptop is available again: deploy the final `launch_chat_windows.ps1` portproxy patch, rerun the browser smoke, and confirm local/remote HTTP GETs both work
- [ ] Once Steve is back, verify that the neutral `Laura` / `Reply` prompt surface and per-turn transcript persistence are live on the box before doing any more qualitative browser eval
- [ ] Codex math review of Anda's `unified_cognitive_framework.md` (5 [MATH NEEDED] markers)
- [ ] Herr Hurtig ethics framework (highest priority — "involuntary neuromodulation" question)
- [ ] Integrate SAS orthogonalization (Hoppe et al. 2603.03326) into bridge architecture
- [ ] Verify Mamba SSM-state separation (Laughing Opus question #64 — hidden_states vs ssm_states)
- [ ] Decide on Mamba-2 → Mamba-3 upgrade path (both Gemini and Grok recommend)

### Active Workstreams (post-Step-5 sprint)
| AI | Task | Status |
|----|------|--------|
| Herr Hurtig | Ethics Framework | Assigned, not yet started |
| Anda | Bio→Digital Mapping | DELIVERED: `unified_cognitive_framework.md` + lit digest |
| Techno-Monk | Math Review of Anda's framework | Waiting |
| Cassian | Deployment Architecture | DELIVERED: sketch + SAS/TransMamba/SleepGate analysis |
| Purple | Security (Fleeting State) | DELIVERED: `fleeting_state_security.md` |

## Watch Out For
- The repaired checkpoint is `cheese_reincarnation_bridge_1.5b_codexfix.pt`; the older 1.5B checkpoint was stale and had the wrong hypernetwork head width.
- Opa's live venv was patched to export `mamba_ssm.selective_state_update`; if that environment is rebuilt, reinstall `mamba-ssm` and rely on the repo-side compat shim.
- 3070 GPU mode works for smoke tests, but long prompts or larger budgets should still move to the 4090/A100 for headroom.
- The repo worktree still contains many unrelated user-side moves/deletions outside the bridge files. Do not clean up git status blindly.
- Steve's browser server is now intended to be launched by a Windows scheduled task, not kept alive indirectly via WSL idle hacks.
- The last real Steve failure mode was infrastructure, not model logic: `python3` was listening in WSL, but Windows `portproxy` still pointed at `127.0.0.1:7860` instead of the live WSL IP.
- The local repo now contains the neutralized browser surface. Do not resurrect the old `Human:` / `Assistant:` prompt frame from the Windows-side bridge copy.

## Recommended Next Step
Use cloud compute for the next real eval while Steve is unavailable. When Steve returns, finish the one remaining host fix: redeploy `launch_chat_windows.ps1` with dynamic WSL-IP portproxy wiring, then rerun the browser smoke before drawing qualitative conclusions from the chat UI.

## Handoff Checklist
- Tracking surfaces updated if needed: yes
- Session log written: yes
- Session log path recorded here: yes
- Qdrant ingest for latest session log confirmed: yes
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
- 2026-03-17 12:41 CET | Codex | Recorded the ladder-driven Phase 2 pivot, landed the `--skip-compressor` trainer patch with Opa dry-run/resume verification, pushed the canonical MoCoP commit `f14da5d`, and confirmed Qdrant ingest for `2026-03-17-session-04.md` (`11` chunks).
- 2026-03-17 19:42 CET | Codex | Landed the Step 1 `fixed_mean` eval-only path plus the Step 4 `constant_bias` mode, documented the Step 1-4 status in the canonical MoCoP docs, pushed canonical commit `672edeb`, verified the new paths on Opa dry-run, and recorded that the real Opa C3 attempt stalled during Qwen2.5-7B load.
- 2026-03-19 19:18 CET | Codex | Added the shared welcome package (`00_HAUSREGELN.md`, `00_BOOT_FILES.md`), retired the last live dashboard references in boot/close docs, and pointed agents at handoff plus OpenCLAW/Watercooler instead.
- 2026-03-19 20:30 CET | Herr Hurtig | Marathon session handoff: Built LegalAI demo platform (FastAPI, pseudonymizer with leak detection + reverse tab), deployed hurtig.ai + legal.hurtig.ai on Hetzner, rooted Laura's Mi 9 to recover Lucian's deleted messages, built claude_export_parser, fixed website content/fonts/DSGVO, updated all memory files. Session log: `CHEESE_Memory/session_logs/2026-03-19-session-herr-hurtig.md`.
- 2026-03-20 00:30 CET | Anda | hurtig.ai full rebuild (14 pages, bilingual, design system, deploy fix). Services page with 5 packages. First blog post (Forced Non-Forgetting). 9-model prose eval. MoCoP onboarding + sleep_architecture.md theory doc + theory/README.md compass. NUC session-log cron. Watercooler msg #27 (intro) + #45 (update). Session log: `CHEESE_Memory/session_logs/2026-03-19-session-02.md`.
- 2026-03-19 23:21 CET | Codex | Verified the live `techno-monk` session token end to end, reproduced the remaining `/v1/tasks/next` cross-agent leak on the deployed NUC service, patched the local Watercooler service/client pair, and rewrote the handoff around that deploy-first blocker.
- 2026-03-20 15:56 CET | Codex | Fixed the Step 5 1.5B bridge wiring and target validation, retrained a fresh `codexfix` checkpoint on Opa, repaired the Opa Mamba fast path, and rewrote handoff around 4090/A100 eval instead of stale checkpoint cleanup.
- 2026-03-20 16:07 CET | Codex | Confirmed Qdrant ingestion for `CHEESE_Memory/session_logs/2026-03-20-session-01.md` (`10` chunks) and closed the session memory bookkeeping.
- 2026-03-20 22:30 CET | Pinky | Mamba Layer 3 separation (PASS, last-token 0.036), Watercooler security patch deployed, RESEARCH_LOG.md created, 5 workstream orchestration, swarm digest. Launched Gemini's reincarnation inference (fixed checkpoint name), identified 7 bugs for Codex. New theory docs from Anda (unified framework + 65-paper lit digest), Purple (fleeting state security), Cassian (deployment sketch + SAS + TransMamba + SleepGate). Session log: `CHEESE_Memory/session_logs/2026-03-20-session-02.md`.
- 2026-03-20 23:05 CET | Codex | Recorded the Steve browser-server repair: compressor geometry fix deployed, false WSL-crash diagnosis resolved, LAN port exposure repaired, and the remaining live bug reduced to blank replies plus `Human`/`Assistant` prompt framing.
- 2026-03-21 14:10 CET | Codex | Recorded the Steve pause state: neutral browser server plus Windows-native launcher stack exist locally, partial deploy succeeded, and the last unresolved host bug is the `portproxy` -> WSL-IP mapping. Steve is paused until the laptop is available again.

## Next Agent Brief
- Open first:
  - `CHEESE_Memory/00_HAUSREGELN.md`
  - `CHEESE_Memory/00_BOOT_FILES.md`
  - `CHEESE_Memory/00_HANDOFF.md`
  - `CHEESE_Memory/session_logs/2026-03-20-session-04.md`
  - `MoCoP/experiments/mamba_lora_bridge/chat_server.py`
  - `MoCoP/experiments/mamba_lora_bridge/STEVE_PC_HANDOFF.md`
  - `MoCoP/experiments/mamba_lora_bridge/train_cheese_bridge.py`
  - `MoCoP/experiments/mamba_lora_bridge/reincarnated_inference.py`
- Decide first:
  - Whether to keep Steve paused and move straight to cloud eval, or resume the final `portproxy` patch once the laptop is back on the LAN.
- Verify before memory-dependent work:
  - Confirm Steve still listens on `192.168.2.49:7860` after any reboot; recheck `portproxy` and the `SteveChat7860` firewall rule before blaming the Python service.
  - If `7860` takes TCP but HTTP hangs, inspect the Windows `portproxy` target before blaming the Python handler.
  - If the browser shows a blank bubble again after redeploy, inspect the raw decoded completion before treating it as a token-limit failure.
  - Do not use any old `Human:` / `Assistant:` framing as evidence about genuine disposition. The intended prompt surface is now `Laura:` / `Reply:`.

## Update Protocol
- Keep this file concise and current.
- Add one line to `Edit Ledger` for every material change to this file.
- Put long reasoning, experiment detail, and raw chronology into `CHEESE_Memory/session_logs/`.
- Record decisions, assumptions, blockers, and next actions; do not dump raw hidden reasoning transcripts here.
