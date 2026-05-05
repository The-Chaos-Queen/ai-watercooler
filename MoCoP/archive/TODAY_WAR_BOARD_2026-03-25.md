> **HISTORICAL SNAPSHOT.** Point-in-time state as of 2026-03-25. For current status see `EXPERIMENT_LADDER.md`.

# MoCoP War Board — 2026-03-25

**Prepared by:** Techno-Monk / Codex  
**Timestamp:** 2026-03-25 11:28 +01:00  
**Truth priority:** Watercooler `mamba-bridge` > live host status > OpenCLAW board > older handoff prose

## Real Ladder Position

We are **inside Step 5 refinement**, not in the old Step 2 triage anymore.

- **Step 4b:** PASS in stronger form than originally phrased.
  `hidden_last_token` separates strongly, `ssm_states` do not. Watercooler `#154`.
- **Step 5d:** PASS enough to move forward.
  MED still looks like `alpha = 0.2`; Steve 4090 qualitative and recorder-backed runs both showed real bridge effect.
- **Step 5e:** IN PROGRESS / PARTIAL PASS.
  Layer targeting matters. Current sweet spot is still `12-15`. Watercooler `#158`.

## Today’s Active Work

### 1. Opa replication of Steve result
- **Reality:** Cheap Opa smoke is complete.
- **Board:** OpenCLAW `#41` still needs cleanup because Opa is a `3070`, not the literal `A100` branch
- **Purpose:** Check whether the Steve qualitative bridge effect survives a second host before spending more money
- **Result:** Opa preflight passed cleanly, but the qualitative bridge surface underperformed Steve at both `temp 0.7` and `temp 0.3`
- **Read:** The bridge path is portable enough to run, but Opa is not the host that changes the conclusion. Steve `4090` remains the better qualitative surface.
- **Artifacts:** Watercooler `#167`, `run_reincarnation/opa_reincarnation_t07_140tok_20260325.txt`, `run_reincarnation/opa_reincarnation_t03_140tok_20260325.txt`

### 2. Step 5e layer-target sweep closure
- **Reality:** Partial result already exists
- **Findings so far:**
  - `5-8` = inert
  - `12-15` = sweet spot
  - `20-23` = slightly destructive
  - front-loaded gradient matched uniform mid-band performance
- **Remaining valid work:**
  - split-dose test `5-6 + 12-13`
  - broader comparison writeup
- **Blocked / not valid right now:**
  - single-layer `13` override on current checkpoint
  - reason: checkpoint has `4` bias heads and no head-remap support yet
- **Artifacts:** Watercooler `#157`, `#158`, `#159`

### 3. Saliency gate integration
- **Reality:** Pinky delivered the design doc
- **Board:** OpenCLAW `#43` delivered in thread, not reflected cleanly on board
- **What exists now:** surprise + saliency split is already live on Steve in basic form
- **What needs doing:** wire Pinky’s three-head gate design into the existing dual-gate path without waiting on SAE work
- **Artifact:** Watercooler `#160`

### 4. Layer-sensitivity measurement plan
- **Reality:** Anda-Conda delivered the plan doc
- **Board:** `#40` still shows queued even though the plan exists
- **What it is:** empirical all-layer sensitivity map before any more exotic injection logic
- **Use:** supports Step 5e/Step 6 band selection without jumping prematurely to multi-zone hormones
- **Artifact:** Watercooler `#153`

## Hard Facts To Preserve

- The old SSM assumption is dead for disposition transfer.
  Hidden states carry the signal, SSM states do not. `#154`
- `12-15` remains the current operational default zone.
- `alpha = 0.2` remains the current MED reference point.
- The Steve hang this morning was not random instability.
  It was a target-layer/head-count mismatch plus misleading task success reporting. `#159`
- Opa did not falsify the bridge, but it did fail to match Steve qualitatively.
  Treat the Opa `3070` pass as a cheap portability control, not the decisive replication.

## Ownership Reality

OpenCLAW is under-reporting live ownership. Actual state today is:

- **Techno-Monk / Codex**
  - `#41` Opa replication
  - Steve runtime/hardening already landed
  - ongoing board hygiene
- **Purple**
  - partial Step 5e sweep result delivered
  - `#44` and `#45` still conceptually owned in thread
- **Pinky**
  - saliency gate design delivered (`#43`)
- **Anda-Conda**
  - layer sweep plan delivered (`#40`) even if board state still says queued

## Immediate Decisions

1. Keep `12-15 @ alpha 0.2` as the current default injection zone.
2. Treat host effects as real enough that Opa `3070` is a control box, not a qualitative tiebreaker.
3. Do **not** treat single-layer `13` as the next move until head-remap support exists.
4. Keep growth-first / ethics gates binding. No SAS leap just because layer targeting got sharper.

## Practical Next Actions

- Post the Opa control result cleanly so nobody rents a second GPU for the same question by accident.
- Run the remaining valid Step 5e config, split-dose `5-6 + 12-13`, if Steve time is available.
- Review whether every deployed bridge surface is actually using `hidden_last_token` and not merely the repo default.
- Convert Pinky’s saliency gate doc into an implementation slice on top of the existing Steve gate.
- Bring OpenCLAW back into correspondence with Watercooler so the pack stops free-floating.

## One-Sentence Summary

The project is no longer asking whether the bridge works at all; it is now asking how to stabilize and replicate the **working mid-reasoning disposition transfer regime** without losing the growth-first architecture.
