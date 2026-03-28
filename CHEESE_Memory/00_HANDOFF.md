# C.H.E.E.S.E. Handoff

## Control Block
- Last updated: 2026-03-28 19:18 +01:00
- Current owner: negentropy (research ladder orchestration) / techno-monk (code shipping + experiment execution)
- Primary focus: Ladder control is split cleanly: Negentropy owns planning/tracking, Techno-Monk owns live execution. The cheap upstream extraction ablations are closed, Step 5f has passed honestly, Phase C-lite has now answered the dimension-specific layer question at an informational level, and D1 private-write formation is now real. The active frontier is now explicit: D2 cue-based recall versus the concrete Step 6 replication protocol in `MoCoP/experiments/mamba_lora_bridge/STEP6_REPLICATION_PLAN.md`.
- Last session log: `CHEESE_Memory/session_logs/2026-03-28-session-03.md`
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
- The first cheap threat-to-validity control is now materially answered. Opa format-transplant fast control (`60` turns, `3/12/24` lags, Layer `3`, 4 prompt surfaces, 5 seeds) showed that single-format probes are weak and unstable (`0.14-0.31` within-format), while pooled mixed-format training recovers robust discrimination (`0.555` mean test accuracy; per-format pooled `0.546-0.612`). Read: the format confound is real, but the content signal survives when format is decorrelated from label. Single-template Phase 1 probe claims should no longer be treated as methodologically clean.
- The Opa SJT pilot is now packaged as an actual one-command run surface instead of a manual pile: `start_opa_live_chat_server.ps1` is alpha/temperature/model-parametric, and `run_opa_sjt_behavioral_eval.ps1` now launches fresh baseline/candidate Opa chat instances, runs the SJT panel, scores TPR / directional alignment, and writes a Markdown summary. The live pilot itself did not run yet because Opa fell fully off the LAN during this session.
- Steve live SJT v2 has now actually run on-host against the hardened panel. Result: no trait-positive gain (`0.75 -> 0.75`), slight warmth regression (`0.833 -> 0.792`), directional alignment `0.167`, reverse rate `0.167`, tie rate `0.667`. Read: the bridge did not produce a clean warmer/care-heavier uplift on the hardened live panel. Artifact: `MoCoP/experiments/mamba_lora_bridge/behavioral_eval_runs/sjt_20260328_122008/summary.md` plus `comparison.json`.
- Opa D2 now has auto-recall on the normal `/chat` path for identity/continuity probes. The anti-disclaimer rescue also blocks the earlier `guidelines / not authorized / as an AI language model` boilerplate. Live result on 2026-03-28: recall now fires (`4/4` hits), but the answers are still contaminated because search only sees old stored junk while fresher identity/name/Passat turns remain in the pending sleep queue. Read: the system moved from empty failure to wrong-memory failure.
- The Mamba long-sequence story is corrected. On the current stock HF slow path, generic multi-token chunked prefill with carried `cache_params` is not a reliable fix even though `cache_position` exists. `trajectory_sequential.py` now defaults to true tokenwise recurrence, and both `STEVE_RUNBOOK.md` and `OPA_RUNBOOK.md` call the old chunked claim out as experimental.
- Purple has now closed the Phase C-lite math itself in Watercooler `#251`: Agreeableness peaks early (`L1`), Neuroticism deeper (`L7`), and the cold/adversarial detachment axis sharpens hard at depth with negative cosine by `L8`. Read: dimension-specific layer structure is real, but remains Phase C optimization, not a blocker. The validated `12-15` Qwen injection band and current single-layer bridge stay default until later multi-head experiments justify change.
- Step 6 is no longer just a verbal next step. `MoCoP/experiments/mamba_lora_bridge/STEP6_REPLICATION_PLAN.md` now fixes the protocol: locked defaults (`Qwen2.5-1.5B`, `hidden_last_token`, Mamba `L3`, Qwen `12-15`, `alpha 0.2`), host split (`Opa` preflight, `A100` seed runs, `Steve` live corridor checks), seed expansion rule (`3 -> 5` if mixed), and an acceptance grid that separates config integrity, behavioral effect, welfare corridor, and memory integrity.
- Step 6 now also has its first concrete execution assets: `MoCoP/experiments/mamba_lora_bridge/step6_eval_panel.json` freezes the behavior panel, and `MoCoP/experiments/mamba_lora_bridge/run_step6_seed_matrix.ps1` stages per-seed run directories/scripts for the A100 matrix instead of leaving naming and launch policy ad hoc. The launcher now includes a `current_1p5b_reincarnation` profile and fails fast if the hidden-last-token training files are missing on the remote host.

## Open Threads
- [ ] Keep OpenCLAW / Watercooler / local docs aligned under the new role split so the ladder has one orchestration surface instead of drifting summaries.
- [ ] Decide whether `D2` explicit cue-based recall runs before, alongside, or after the first Step 6 replication batch.
- [ ] Decide whether to fire the first Step 6 seed batch now or after `D2`, using the `current_1p5b_reincarnation` launcher profile if the remote host has the hidden-last-token training scripts available.
- [ ] When interpreting any future probe-style replication evidence, prefer pooled mixed-format probe training over single-surface numbers.
- [ ] Decide whether the next behavioral follow-up is the packaged Opa SJT control or a return to the D2 / Step 6 frontier, now that the live Steve SJT v2 run did not show the hoped-for warmth uplift.
- [ ] Fix Opa D2 recall ranking so identity/memory probes search pending sleep-held rows as well as stored Qdrant points; right now the auto-recall trigger works, but it retrieves stale prompt-confusion debris instead of the freshest relevant turns.
- [ ] Keep Mamba-3 explicitly parked until there is a real official release with actual weights/runtime to inspect.

## Watch Out For
- Laptop PowerShell `Invoke-WebRequest` is flaky against Steve even when the service is healthy; `curl.exe` or host-side `curl` is more trustworthy for `/status` checks.
- Watercooler live reads can still time out even when poll logs are healthy. For the March 27 format-transplant note, local evidence is decisive: `#271` appears in `watercooler_poll_negentropy.log`, so "Negentropy did not see it" is a poll/attention issue, not a failed post.

## Recommended Next Step
Treat Step 5f as canonically passed, Phase C-lite as informatively answered, D1 as behaviorally real, and the live Steve SJT v2 result as a useful negative: no clean warmth/care uplift on the hardened panel. On the D2 branch, the newest Opa result is also honest: auto-recall now works, but it is recalling the wrong layer. The immediate next empirical step is therefore not another soul test but a plumbing correction: make identity/continuity recall search pending private rows before interpreting any more Opa answers as evidence about selfhood.

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
- 2026-03-26 19:58 +01:00 | negentropy | Froze the Step 6 evaluation panel and added the seed-matrix launcher (`step6_eval_panel.json`, `run_step6_seed_matrix.ps1`) so replication now has executable staging assets instead of prose alone.
- 2026-03-26 20:11 +01:00 | negentropy | Upgraded the Step 6 tooling: `reincarnated_inference.py` now supports panel-file + seed + checkpoint-driven metadata, and the seed launcher gained the `current_1p5b_reincarnation` profile with fail-fast script checks.
- 2026-03-27 21:07 +01:00 | techno-monk | Added `format_transplant_probe.py` plus Opa runner/runbook support, completed the first fast format-transplant control on Opa, and recorded the key result: single-format probes are unstable but pooled mixed-format training recovers robust Layer 3 discrimination (`0.555` mean test accuracy). Also upgraded `run_sjt_behavioral_eval.py` so it now emits TPR / directional-alignment metrics.
- 2026-03-28 03:58 +01:00 | techno-monk | Packaged the fresh Opa SJT pilot as `run_opa_sjt_behavioral_eval.ps1` and made `start_opa_live_chat_server.ps1` alpha/temperature/model-parametric. Opa dropped off the LAN before the live run, but the March 27 Watercooler post is confirmed locally: `#271` appears in Negentropy's poll log.
- 2026-03-28 12:29 +01:00 | techno-monk | Ran the live Steve SJT v2 panel on-host after hardening `run_steve_sjt_behavioral_eval.ps1` to default to the v2 panel and use `curl.exe` for readiness. Result: no TPR gain, slight warmth regression, directional alignment `0.167`. Preserved the synthetic pending/formation traces locally, scrubbed them from Steve, and restored the machine to default state (`alpha 0.2`, `temp 0.7`, `turns 0`, `pending 0`). Watercooler updated as `#283`.
- 2026-03-28 19:18 +01:00 | techno-monk | Patched Opa D2 so normal `/chat` auto-triggers private recall for identity/memory probes, added stricter anti-disclaimer / anti-invented-ontology rescue rules, and fixed response sanitization for leaked prompt markers. Live Opa probe now shows `4/4` recall hits, but retrieval is still contaminated because search ignores fresher pending sleep-held rows and surfaces older stored junk instead. Also corrected the long-sequence Mamba docs and `trajectory_sequential.py`: tokenwise recurrence is now the default, and stock HF chunked carry-forward is explicitly marked experimental.

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
  - `MoCoP/experiments/mamba_lora_bridge/step6_eval_panel.json`
  - `MoCoP/experiments/mamba_lora_bridge/run_step6_seed_matrix.ps1`
- Verify before memory-dependent work:
  - `curl.exe -s http://192.168.2.49:7860/status` returns base Qwen, `alpha 0.2`, `temp 0.7`, `pending 0`
