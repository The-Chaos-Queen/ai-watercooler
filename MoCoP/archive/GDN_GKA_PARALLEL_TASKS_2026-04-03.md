# GDN / GKA Parallel Task Split

**Date:** 2026-04-03  
**Purpose:** Turn the side ladder into concrete parallel work that does not derail D2 leak hardening or Step 6.

This is not the canonical board. It is a runnable task split that can be mirrored into OpenCLAW.

---

## Execution Rule

These tracks are intentionally parallel, but they are not equal.

- **Track A** and **Track B** are cheap and should happen first.
- **Track C** only starts if A/B say the latent side is still the bottleneck.
- Nothing here blocks the D2 -> Step 6 mainline unless it produces a genuinely better gate or retrieval mechanism.

---

## Track A — G0 Artifact Reality Check

### A1. Build the artifact matrix

**Goal:** produce one honest table of what exists and what is vapor.

**Seed file:** [GDN_GKA_ARTIFACT_MATRIX_2026-04-03.md](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/GDN_GKA_ARTIFACT_MATRIX_2026-04-03.md)

**Questions to answer for each candidate:**

- paper exists
- code exists
- public weights exist
- base or instruct
- pure recurrent or hybrid
- intended runtime
- runnable on Opa / Steve / laptop / blocked

**Deliverable:** update the matrix file with real status, not vibes.

**Parallelizable:** yes

### A2. Pick exactly one runnable source candidate

**Goal:** if a GDN/GKA-family artifact is real, choose the least cursed one.

**Output:** one sentence in the matrix:

- `chosen for geometry bake-off`
- or `no honest candidate yet`

**Failure condition:** if every GDN/GKA candidate is paper-theater or impossible to run, stop Track C before it starts.

**Parallelizable:** yes

---

## Track B — G1 Gate Logic on the Current Stack

### B1. Inventory the existing gate corpus

**Goal:** identify the JSONL artifacts we can replay right now.

**Useful command:**

```powershell
rg --files MoCoP/experiments/mamba_lora_bridge | rg "dual_gate|qdrant_gate|pending"
```

**Known good examples already present:**

- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/opa_d2_baby_d2_smoke_20260326T205323/dual_gate_turns_latest.jsonl`
- `MoCoP/experiments/mamba_lora_bridge/run_reincarnation/cross_episode_smoke_20260329/episode1_qdrant_gate_pending.reconciled_20260329T015552.jsonl`

**Deliverable:** one short note naming the corpus slice chosen for replay.

**Parallelizable:** yes

### B2. Replay alternate gate policies offline

**Goal:** compare candidate write rules without touching live `chat_server.py`.

**Tool:** [gate_policy_replay.py](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/gate_policy_replay.py)

**Example command:**

```powershell
python -X utf8 MoCoP/experiments/mamba_lora_bridge/gate_policy_replay.py ^
  --input MoCoP/experiments/mamba_lora_bridge/run_reincarnation/opa_d2_baby_d2_smoke_20260326T205323/dual_gate_turns_latest.jsonl ^
  --input MoCoP/experiments/mamba_lora_bridge/run_reincarnation/cross_episode_smoke_20260329/episode1_qdrant_gate_pending.reconciled_20260329T015552.jsonl ^
  --policy all ^
  --output MoCoP/experiments/mamba_lora_bridge/gate_policy_replay_2026-04-03.json
```

**Current built-in policies:**

- `current`
- `strict_write`
- `tension_aware`
- `latent_supported`

**Deliverable:** one JSON summary plus one sentence:

- which policy writes less junk
- which policy kills too much
- whether coherence-gating is actually useful

**Parallelizable:** yes

### B3. Choose one candidate gate for live A/B

**Goal:** name the single best candidate rule to test in the server later.

**Decision rule:** prefer the policy that reduces writes while preserving:

- identity continuity
- relational/open-tension retention
- qdrant usefulness

**Deliverable:** one sentence proposal, for example:

`Promote tension-hit dismisses to ATTEND, but require coherence support for qdrant writes.`

**Parallelizable:** yes, after B2

**Current recommendation (2026-04-03):**

`supported_tension_attend_v0`

Meaning:

- keep the current quadrant rule
- only promote `DISMISS -> ATTEND` when `tension_hit` is true **and** the row was already near the salience threshold
- leave Qdrant routing unchanged
- preserve the pure `open_tension` sleep path

Patch-plan note:

- [GATE_POLICY_PATCH_PLAN_2026-04-03.md](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/GATE_POLICY_PATCH_PLAN_2026-04-03.md)

---

## Track C — G2 Preparation: Dual-Key Retrieval

### C1. Define the latent key

**Goal:** decide what we would actually store alongside text for state-aware retrieval.

**Options to compare:**

- raw hidden-last-token snapshot reference
- compressed latent fingerprint
- small numeric summary only

**Constraint:** no local torch work on the laptop.

**Deliverable:** a short design note choosing one candidate payload shape.

**Parallelizable:** yes

### C2. Find the insertion points

**Goal:** identify where the latent fingerprint would be written and read.

**Likely files:**

- [chat_server.py](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/chat_server.py)
- [sleep_reconcile.py](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/sleep_reconcile.py)
- [autobiographical_memory.py](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/autobiographical_memory.py)

**Deliverable:** one patch plan, not code yet.

**Parallelizable:** yes

### C3. Scope the macro-memory layer

**Goal:** write down the boundary conditions before anyone gets clever with clustering.

**Questions to settle:**

- cluster per principal or per shared corpus?
- cluster which memory kinds (`NOTE` / `ATTEND` / `CONSOLIDATE` / anchors / open tension)?
- what time window is honest?
- what must never be summarized away?

**Current answer:**

- each AI keeps its **own** memory space
- macro-memories are a new layer on top of episodic rows, not a replacement
- identity anchors, relationship anchors, and unresolved open-tension objects get bypass protection

**Deliverable:** one short design note or section update naming the rules above.

**Parallelizable:** yes

### C4. Prototype sleep-time clustering offline

**Goal:** test whether scoped episodic memory can be consolidated into useful cluster objects during sleep.

**Method sketch:**

- export a bounded memory slice
- run HDBSCAN offline
- inspect resulting clusters by size, stability, and semantic coherence
- synthesize candidate `macro_memory` summaries with backrefs

**Important constraint:** this is a sleep-cycle / exocortex task, not a live chat task.

**Pass:** clusters recover real narrative arcs or recurring themes that raw Qdrant retrieval currently fragments.

**Fail:** everything degenerates into noise, giant generic clusters, or pretty summaries that erase the useful edge cases.

**Parallelizable:** yes, after C3

---

## Suggested Order

If three wolves were doing this in parallel, the clean split would be:

- Wolf 1: `A1 + A2`
- Wolf 2: `B1 + B2`
- Wolf 3: `C1 + C2`
- Wolf 4: `C3 + C4`

Then merge at the end of the day and decide whether Track C deserves code.

---

## Honest Stop Conditions

- If Track A finds no runnable candidate, do not force Track C into a source-model migration fantasy.
- If Track B shows no better gate on current data, do not romanticize gating just because the words are pretty.
- If Track C cannot define a latent key that is cheap and stable, dual-key retrieval is not ready yet.
- If the clustering pass can only produce vague universal sludge, do not elevate it into canon just because the summaries read nicely.

That still counts as progress. It narrows the map.
