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
- **Current live question:** the cheap extraction ablations are now essentially closed. The next real question is whether to probe dimension-specific layer peaks before spending A100 time.

## Current Hard Facts

- `hidden_last_token` is the canonical Mamba-side representation for live bridge work.
- Single last-token extraction is empirically locked; trailing token windows only dilute the signal.
- Steve default is currently base `Qwen/Qwen2.5-1.5B`, `alpha 0.2`, `temp 0.7`, `qdrant_write_mode pending`.
- Natural NOTE memories now survive the handoff to sleep honestly; on the fresh 2026-03-26 Steve cycle, two care rows promoted to `CONSOLIDATE`.
- `sleep_reconcile.py` default `coherence_threshold` is `0.12`.
- Step 5f now has two clean same-space passes:
  - fresh Steve default cycle: `2K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`
  - pure `open_tension` edge case: `1K/0U/0W/0D`, `PASS`, diversity ratio `100%`, recovery `1.0`
- Decay calibration for `0.70 / 0.85 / 0.90` is complete on the current retained batches.
- Honest caveat: the decay sweep did **not** distinguish the three values on these batches, so `0.85` remains acceptable but still provisional rather than uniquely justified.
- Layer 3 remains the best balanced bridge layer. Adjacent-layer concat does not help enough to justify the width, but deeper layers (`6-8`, especially `L8`) separate some disposition pairs more strongly and may matter for Phase C / OCEAN-style dimension probing.
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

- **Status:** queued, non-blocking
- **Why it matters:** the multi-layer probe says width is not the answer, but layer depth may still matter per disposition axis
- **Immediate ask:** run Phase C-lite first on existing warm/cold/adversarial data: recast them as partial OCEAN proxies, compute Fisher Ratio per layer per dimension, and map the best bands for Qwen 1.5B / 7B without spending A100
- **Execution owner:** Purple
- **Orchestration owner:** Negentropy
- **Constraint:** informational only. Do not block A100 or growth-ladder work on it; layers `12-15` remain the validated default until this math says otherwise.

### 4. Canon Consolidation

- **Status:** open
- **Why it matters:** Watercooler/live behavior has outrun some canon docs again
- **Immediate ask:** fold the 2026-03-26 Step 5f closeout, the decay calibration, and the closed Opa ablations into the right ladder-facing docs
- **Execution owner:** Negentropy
- **Orchestration owner:** Negentropy

### 5. Mamba-3 Migration Scoping

- **Status:** open
- **Why it matters:** this is exciting enough to derail discipline if left vague
- **Immediate ask:** keep it parked until there are real official weights/runtime to inspect
- **Execution owner:** none
- **Orchestration owner:** Negentropy

### 6. Board / Reality Hygiene

- **Status:** open
- **Why it matters:** OpenCLAW and Watercooler still drift unless someone actively reconciles them
- **Immediate ask:** keep task state aligned with the actual ladder, not stale thread fragments
- **Execution owner:** Negentropy

## What Not To Do

- Do **not** treat Mamba-3 as a package-upgrade chore.
- Do **not** jump to SAS/control work before the growth/sleep ladder stays coherent.
- Do **not** let OpenCLAW become fiction while Watercooler carries reality.

## Immediate Next Moves

1. Run the queued Phase C-lite Fisher-ratio pass on existing data and treat it as informational, not blocking.
2. Fold the completed Step 5f result and decay caveat into the remaining canon surfaces.
3. Keep Mamba-3 explicitly parked until the release is real.

## One-Sentence Summary

Negentropy owns the ladder map; Techno-Monk keeps building the road.
