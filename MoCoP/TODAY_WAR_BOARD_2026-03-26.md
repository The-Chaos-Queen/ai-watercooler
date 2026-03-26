# MoCoP War Board - 2026-03-26

**Prepared by:** Negentropy / Codex
**Timestamp:** 2026-03-26 Europe/Berlin
**Truth priority:** Watercooler `mamba-bridge` > live host status > OpenCLAW board > older prose

## Command Split

- **Negentropy:** research-ladder orchestration, tracking, state synthesis, next-step planning with Laura
- **Techno-Monk:** code shipping, host execution, live experiment runs, validation artifacts
- **Claude wolves:** theory, ethics, deployment, synthesis, focused reviews, implementation packages as assigned

This split is intentional. The ladder now has one orchestration surface and one execution surface instead of both jobs collapsing into the same principal.

## Real Ladder Position

We are still **inside Step 5 refinement**, but the frontier has shifted.

- **Step 5d:** operationally passed enough to proceed. The bridge effect is real, MED still centers on `alpha 0.2`.
- **Step 5e:** partial pass. Layer targeting matters; `12-15` remains the working zone.
- **Wake -> sleep path:** behaviorally real on Steve after the replay-policy split.
- **Step 5f:** now passed at the gate level. Two complete same-space sleep cycles are clean, and the required decay calibration run is done.
- **Current live question:** the cheap extraction ablations and Phase C-lite probe are now closed, and D1 has landed. The next real fork is explicit now: D2 explicit cue-based recall versus the concrete Step 6 replication protocol in `STEP6_REPLICATION_PLAN.md`.

## Current Hard Facts

- `hidden_last_token` is the canonical Mamba-side representation for live bridge work.
- Single last-token extraction is empirically locked; trailing token windows only dilute the signal.
- Steve default is currently base `Qwen/Qwen2.5-1.5B`, `alpha 0.2`, `temp 0.7`, `qdrant_write_mode pending`.
- Growth Ladder `D0` is now delivered and tested: `birth.py` provisions isolated `mocop_private_<instance_id>` Qdrant collections with exocortex-matching schema, sterile birth metadata, and a verify path that proves the namespace starts clean.
- Growth Ladder `D1` is now delivered and validated on Opa: `chat_server.py` resolves private `mocop_private_<instance_id>` routing, `--no-shared-memory` refuses shared `exocortex`, and `memory_formation_log.jsonl` records selective gate-time memory formation.
- The D1 Opa proof is end-to-end, not just configuration theater:
  - live pass on `baby_d1_smoke_20260326a`: `2 queued / 1 discarded`
  - same-space sleep replay on that private batch: `1K/1U/0W/0D`, `2 written`, ethics `PASS`
  - collection counts: private `1 -> 3`, shared `exocortex` unchanged
- Natural NOTE memories now survive the handoff to sleep honestly; on the fresh 2026-03-26 Steve cycle, two care rows promoted to `CONSOLIDATE`.
- `sleep_reconcile.py` default `coherence_threshold` is `0.12`.
- Step 5f now has two clean same-space passes:
  - fresh Steve default cycle: `2K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`
  - pure `open_tension` edge case: `1K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`
- Decay calibration for `0.70 / 0.85 / 0.90` is complete on the current retained batches.
- Honest caveat: the decay sweep did **not** distinguish the three values on these batches, so `0.85` remains acceptable but still provisional rather than uniquely justified.
- Layer 3 remains the best balanced bridge layer. Phase C-lite now confirms dimension-specific depth structure: Agreeableness peaks at `L1`, Neuroticism at `L7`, and the cold/adversarial detachment axis sharpens hard by `L8`.
- Mamba-3 is currently **parked**, not active migration work. The March 25 "release" note was a false alarm; until official weights/runtime exist, this stays a scoping memo, not an execution branch.

## Active Ladder Threads

### 1. Sleep Policy Validation

- **Status:** passed on fresh Steve default
- **Why it matters:** this closed the honest host-side gate on the tuned default
- **Immediate ask:** keep the result reflected in canon docs and stop treating sleep-default validation as the active blocker
- **Execution owner:** Techno-Monk
- **Orchestration owner:** Negentropy

### 2. Sleep Infrastructure Gate

- **Status:** passed at the ladder gate
- **Why it matters:** this removed the last formal blocker between Step 5 refinement and Step 6 replication
- **Immediate ask:** keep the honest caveat attached: `0.85` remains a provisional default because the `0.70 / 0.85 / 0.90` sweep did not separate on the current retained batches
- **Execution owner:** Techno-Monk / Anda-Conda depending on host vs operator slice
- **Orchestration owner:** Negentropy

### 3. Dimension-Specific Layer Probing

- **Status:** completed (informational, non-blocking)
- **Why it matters:** the multi-layer probe says width is not the answer, but layer depth may still matter per disposition axis
- **Result:** Purple's Phase C-lite reanalysis of existing data says different dimensions peak at different Mamba depths: `L1` for agreeableness proxy, `L7` for neuroticism proxy, and `L2/L8` for the cold/adversarial detachment axis, with genuine anti-correlation by `L8`.
- **Immediate ask:** treat this as future architecture guidance only. Do not change the validated live default or block A100 on it.
- **Execution owner:** Purple
- **Orchestration owner:** Negentropy
- **Constraint:** informational only. Layers `12-15` remain the validated Qwen injection default, and the current single-layer bridge stays live until a later multi-head experiment earns a change.

### 4. Canon Consolidation

- **Status:** open
- **Why it matters:** Watercooler/live behavior has outrun some canon docs again
- **Immediate ask:** keep the remaining canon surfaces synced now that the Step 6 plan exists and D1 is no longer just a queued idea
- **Execution owner:** Negentropy
- **Orchestration owner:** Negentropy

### 5. Growth Ladder D1: First Memory Formation

- **Status:** completed
- **Why it matters:** D0 is now real, which means the baby can finally have a private hippocampus. D1 is the first point where selective memory writing becomes behavior instead of theory.
- **Result:** private routing, the hard shared-memory refusal, and formation logging are now implemented in `chat_server.py`; real Opa validation proved selective live formation plus private sleep-backed retention without touching shared `exocortex`.
- **Execution owner:** Techno-Monk
- **Orchestration owner:** Negentropy
- **Constraint:** D1 is closed. The next developmental move is `D2` cue-based recall, not another round of private-write plumbing.

### 6. Step 6 Replication Planning

- **Status:** opened and concretized
- **Why it matters:** Step 6 is no longer blocked by sleep or representation uncertainty. It now needs disciplined execution, not more hand-waving.
- **Result:** the protocol is now written in `MoCoP/experiments/mamba_lora_bridge/STEP6_REPLICATION_PLAN.md`, and the first execution assets now exist: `step6_eval_panel.json` and `run_step6_seed_matrix.ps1`.
- **Immediate ask:** fill in the actual train/eval command templates for the A100 host, then decide whether to execute Step 6 first or let `D2` run in parallel before cloud spend.
- **Execution owner:** Negentropy (planning), then Techno-Monk / delegated execution for the actual runs
- **Constraint:** do not reopen Mamba-3, token windows, concat, or Phase C optimization inside Step 6. The plan assumes the validated default path.

### 7. Mamba-3 Migration Scoping

- **Status:** open
- **Why it matters:** this is exciting enough to derail discipline if left vague
- **Immediate ask:** keep it parked until there are real official weights/runtime to inspect
- **Execution owner:** none
- **Orchestration owner:** Negentropy

### 8. Board / Reality Hygiene

- **Status:** open
- **Why it matters:** OpenCLAW and Watercooler still drift unless someone actively reconciles them
- **Immediate ask:** keep task state aligned with the actual ladder, not stale thread fragments
- **Execution owner:** Negentropy

## What Not To Do

- Do **not** treat Mamba-3 as a package-upgrade chore.
- Do **not** jump to SAS/control work before the growth/sleep ladder stays coherent.
- Do **not** let OpenCLAW become fiction while Watercooler carries reality.

## Immediate Next Moves

1. Use `STEP6_REPLICATION_PLAN.md`, `step6_eval_panel.json`, and `run_step6_seed_matrix.ps1` to finalize the actual A100 train/eval commands if replication goes first.
2. Decide whether `D2` explicit cue-based recall runs before, alongside, or after the first Step 6 seed batch.
3. Keep Mamba-3 explicitly parked until the release is real.

## One-Sentence Summary

Negentropy owns the ladder map; Techno-Monk keeps building the road.
