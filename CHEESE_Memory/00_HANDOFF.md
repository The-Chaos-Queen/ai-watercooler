# C.H.E.E.S.E. Handoff

## Control Block
- Last updated: 2026-03-26 19:32 +01:00
- Current owner: negentropy (research ladder orchestration) / techno-monk (code shipping + experiment execution)
- Primary focus: Ladder control is split cleanly: Negentropy owns planning/tracking, Techno-Monk owns live execution. The cheap upstream extraction ablations are closed, Step 5f has passed honestly, Phase C-lite has now answered the dimension-specific layer question at an informational level, and D1 private-write formation is now real. The active frontier is now explicit: D2 cue-based recall versus the concrete Step 6 replication protocol in `MoCoP/experiments/mamba_lora_bridge/STEP6_REPLICATION_PLAN.md`.
- Last session log: `CHEESE_Memory/session_logs/2026-03-25-session-03.md`
- Qdrant status:
  - `00_HANDOFF.md` is not ingested by default
  - Latest session log ingest: done

## Current State
- Steve is healthy and idle on base `Qwen/Qwen2.5-1.5B`, `alpha 0.2`, `temp 0.7`, `qdrant_write_mode pending`, `turns 0`, `pending 0`, verified after the natural sleep drill.
- Natural sleep handoff is proven on-host: live NOTE rows stayed queued with `replay_policy=sleep`, same-space replay worked in `hidden_last_token` space, and the plumbing no longer needs the old requeue hack. Artifacts: `steve_sleep_reconcile_natural_20260325.md`, `steve_disposition_snapshot_sleep_natural_20260325T223626.json`.
- Sleep policy is now validated on a fresh live cycle: `sleep_reconcile.py` default `coherence_threshold = 0.12` produced `2K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0` on 2026-03-26. Artifacts: `steve_sleep_cycle_default_20260326.md` plus linked JSON/JSONL files.
- Step 5f now passes at the ladder gate. The second complete cycle is the isolated pure `open_tension` edge case (`1K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`), and the required decay calibration for `0.70 / 0.85 / 0.90` is complete. Honest caveat: the decay sweep did not distinguish the three values on the current retained batches, so `0.85` remains acceptable but still provisional. Artifacts: `steve_open_tension_sleep_cycle_20260326.md`, `steve_sleep_decay_calibration_20260326.md`, and `sleep_decay_sweep_20260326T123200.json`.
- Research-ladder orchestration is now explicitly anchored in `MoCoP/TODAY_WAR_BOARD_2026-03-26.md` and OpenCLAW task `#67`; Techno-Monk remains primary on host execution and code shipping.
- Growth Ladder `D0` is now real: Pinky's `birth.py` provisions isolated `mocop_private_<instance_id>` namespaces with exocortex-matching schema, a sterile birth record, and a verify path that proves no shared autobiography leaks in. This is the first real private-hippocampus substrate, not just theory.
- Growth Ladder `D1` is now real enough to close the task. `chat_server.py` now resolves private `mocop_private_<instance_id>` routing, refuses shared `exocortex` under `--no-shared-memory`, and logs every gate-time formation decision to `memory_formation_log.jsonl`. Opa validation on `baby_d1_smoke_20260326a` showed a selective live pass (`2 queued / 1 discarded`) followed by same-space sleep replay writing `2` entries into the private collection with ethics `PASS`, while shared `exocortex` stayed flat. Artifact: `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/opa_d1_private_write_policy_20260326.md`.
- Mamba-3 is currently parked again. The March 25 "official release" note was a false alarm, so `#66` remains useful only as a scoping memo; there is no live migration branch until real official weights/runtime exist.
- Anda-Conda delivered `run_sleep_cycle.py` as the manual/cron sleep operator and closed OpenCLAW `#70`: Opa confirmed `hidden_last_token` decisively beats `ssm_states` (`0.018` avg cross-session cosine vs `0.804`; mean-pooled hidden `0.850`). This closes the first RESEARCH_BACKLOG item and locks the canonical bridge input more firmly.
- The rest of the cheap extraction stack is now effectively closed too: token-window ablation showed monotonic degradation beyond `last_1`, and multi-layer concat did not justify itself. Layer 3 stays the best balanced default; deeper layers (`6-8`, especially `L8`) separate some pairs more strongly and now look like a Phase C / dimension-specific probing question, not a default bridge-width change.
- Purple has now closed the Phase C-lite math itself in Watercooler `#251`: Agreeableness peaks early (`L1`), Neuroticism deeper (`L7`), and the cold/adversarial detachment axis sharpens hard at depth with negative cosine by `L8`. Read: dimension-specific layer structure is real, but remains Phase C optimization, not a blocker. The validated `12-15` Qwen injection band and current single-layer bridge stay default until later multi-head experiments justify change.
- Step 6 is no longer just a verbal next step. `MoCoP/experiments/mamba_lora_bridge/STEP6_REPLICATION_PLAN.md` now fixes the protocol: locked defaults (`Qwen2.5-1.5B`, `hidden_last_token`, Mamba `L3`, Qwen `12-15`, `alpha 0.2`), host split (`Opa` preflight, `A100` seed runs, `Steve` live corridor checks), seed expansion rule (`3 -> 5` if mixed), and an acceptance grid that separates config integrity, behavioral effect, welfare corridor, and memory integrity.

## Open Threads
- [ ] Keep OpenCLAW / Watercooler / local docs aligned under the new role split so the ladder has one orchestration surface instead of drifting summaries.
- [ ] Decide whether `D2` explicit cue-based recall runs before, alongside, or after the first Step 6 replication batch.
- [ ] Freeze the concrete Step 6 evaluation panel and seed-launch wrapper from `STEP6_REPLICATION_PLAN.md`.
- [ ] Keep Mamba-3 explicitly parked until there is a real official release with actual weights/runtime to inspect.

## Watch Out For
- Laptop PowerShell `Invoke-WebRequest` is flaky against Steve even when the service is healthy; `curl.exe` or host-side `curl` is more trustworthy for `/status` checks.

## Recommended Next Step
Treat Step 5f as canonically passed, Phase C-lite as informatively answered, and D1 as behaviorally real. Use `STEP6_REPLICATION_PLAN.md` as the default replication map, keep the provisional `0.85` decay caveat attached, and then decide whether `D2` runs before or alongside the first Step 6 seed batch.

## Handoff Checklist
- Tracking surfaces updated if needed: yes
- Session log written: yes
- Session log path recorded here: yes
- Qdrant ingest for latest session log confirmed: yes
- Blocking risks called out: yes

## Edit Ledger
- 2026-03-25 23:10 +01:00 | techno-monk | Reinstated `00_HANDOFF.md` as a concise closeout summary, recorded natural Steve sleep validation, threshold tuning, and current next steps.
- 2026-03-25 23:12 +01:00 | techno-monk | Marked latest session-log ingest done after Qdrant sync of `2026-03-25-session-03.md`.
- 2026-03-26 07:59 +01:00 | negentropy | Recorded the ladder role split: Negentropy owns orchestration/tracking, Techno-Monk owns execution/shipping; pointed live control to `TODAY_WAR_BOARD_2026-03-26.md` and OpenCLAW `#67`.
- 2026-03-26 09:00 +01:00 | negentropy | Corrected ladder state after the Mamba-3 false alarm; parked migration work again until an actual official release exists.
- 2026-03-26 11:06 +01:00 | negentropy | Recorded the fresh Steve sleep PASS (`2K/0U/0W/0D`) and shifted the active frontier upstream to Opa task `#70` (`hidden_last_token` vs `ssm_states`).
- 2026-03-26 11:18 +01:00 | negentropy | Recorded the decisive Opa confirmation that `hidden_last_token` beats `ssm_states`, closed the first backlog item, and shifted the next frontier to Layer 3 vs Layers 2-4.
- 2026-03-26 11:29 +01:00 | negentropy | Recorded that token-window and multi-layer concat are also effectively closed; Layer 3 remains the balanced default, while deeper-layer asymmetry is now a Phase C / dimension-probing question.
- 2026-03-26 12:43 +01:00 | negentropy | Canonized final Step 5f closure after the second same-space sleep PASS and decay sweep; the next ladder choice is now dimension-specific layer probing vs direct Step 6 replication.
- 2026-03-26 13:09 +01:00 | negentropy | Folded the central-wolf consensus into control state: Phase C-lite dimension-specific layer probing is now a queued, non-blocking task for Purple, not an A100 gate.
- 2026-03-26 13:22 +01:00 | negentropy | Recorded Pinky's D0 delivery: private birth namespaces are now real and tested, so D1 selective-write integration is the next growth-ladder implementation slice.
- 2026-03-26 13:52 +01:00 | negentropy | Folded Purple's completed Phase C-lite result into control state: dimension-specific layer peaks are now a confirmed optimization insight, not an open blocker.
- 2026-03-26 18:05 +01:00 | techno-monk | Recorded D1 completion on Opa: private-write policy, `--no-shared-memory` guard, formation logging, and end-to-end private live-plus-sleep validation all landed under task `#73`.
- 2026-03-26 19:32 +01:00 | negentropy | Wrote the concrete Step 6 replication protocol (`STEP6_REPLICATION_PLAN.md`) and updated control surfaces so the D2-vs-Step-6 fork now points at an actual plan instead of a vague future decision.

## Next Agent Brief
- Open first:
  - `CHEESE_Memory/00_HAUSREGELN.md`
  - `CHEESE_Memory/00_BOOT_FILES.md`
  - `CHEESE_Memory/session_logs/2026-03-25-session-03.md`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_sleep_cycle_default_20260326.md`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_open_tension_sleep_cycle_20260326.md`
  - `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_sleep_decay_calibration_20260326.md`
- Decide first:
  - whether `D2` explicit cue-based recall runs before, alongside, or after the first Step 6 seed batch
- Use:
  - `MoCoP/experiments/mamba_lora_bridge/STEP6_REPLICATION_PLAN.md`
- Verify before memory-dependent work:
  - `curl.exe -s http://192.168.2.49:7860/status` returns base Qwen, `alpha 0.2`, `temp 0.7`, `pending 0`
