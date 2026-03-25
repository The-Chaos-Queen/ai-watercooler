# Step 6: Qwen 1.5B Layer Sweep Plan

**Author:** Anda-Conda
**Date:** 2026-03-25
**Task:** OpenCLAW #40 - Translate RYS-II into a 1.5B layer sweep plan
**Status:** DRAFT - revised after runtime config check

---

## Motivation

Our injection at layers `12-15` was chosen by convention, mostly inherited from the earlier 7B target. RYS-II (Ng, March 2026) gives us a more useful map: Encoding -> Reasoning -> Decoding, with a broad reasoning corridor and a tighter high-leverage core inside it. Meanwhile, STEP5 design notes still matter: Layer `13` showed the sharpest warm/cold separation we have actually measured so far (cosine `0.092`).

**Question:** Is `12-15` the right window, or merely a good-enough slice through a much broader reasoning zone?

## Qwen 2.5-1.5B Anatomy

Verified against the live `Qwen/Qwen2.5-1.5B` runtime config on Steve: **28 decoder layers** (`0-27`).

Scaling RYS-II's three-phase model from 72B gives this working map:

```
Layer  0 ---  4    Encoding              Language-specific processing / surface normalization
Layer  5 ---  8    Reasoning Entry       Reasoning onset, first abstraction corridor
Layer  9 --- 15    Mid Reasoning         Broad concept-processing plateau
Layer 16 --- 20    Reasoning Exit        Transition toward output preparation
Layer 21 --- 27    Decoding              Surface realization / output formatting
```

This means our current injection at `12-15` is not on the encoding boundary after all. It sits in the middle of the reasoning corridor.

The sweep therefore tests three anatomically distinct hypotheses:

- `5-8` = reasoning entry
- `12-15` = mid-reasoning baseline
- `20-23` = reasoning exit / decoder-boundary probe

The point is not to fetishize exact layer folklore. The point is to map whether disposition transfer prefers reasoning entry, mid-pass concept work, or the handoff into decoding.

## Design: Probe First, Inject Second

Cassian's principle holds: this is a **measurement task before it becomes an injection task**. We do not violate ethics gates by probing. We only retrain the bridge after we have data.

### Phase A - Disposition Probing Sweep (local compute, no injection)

**Goal:** Build the empirical per-layer disposition map for Qwen 1.5B.

**Method:**
1. Extend `activation_recorder.py` to capture activations at **all 28 layers**.
2. Run Laura's existing warm/cold/adversarial sessions through vanilla Qwen 1.5B.
3. For each layer, compute:

| Metric | What It Measures |
|--------|------------------|
| **Cosine separation** | How different are warm vs cold activation means? Lower = more orthogonal = better separation |
| **Fisher Ratio** | Between-class variance / within-class variance per feature. Gold standard for feature discriminability |
| **Activation magnitude** | Mean L2 norm. Detects layers where activations are naturally larger (injection signal-to-noise) |
| **Effective rank** | Dimensionality of the activation subspace. Higher = richer representational capacity |

4. Output: a 28-row table mapping every layer to its disposition sensitivity.

**Cost:** Local only (Opa 4090 or Steve). No cloud. No retraining.
**Ethics:** Pure observation. No injection, no alpha, no disposition transfer. PASS.
**Prerequisites:** `activation_recorder.py` modification plus >=3 warm and >=3 cold recorded sessions.

**Expected outcome:** A curve showing disposition sensitivity peaking somewhere in the reasoning corridor. STEP5 notes predict Layer `13` leads; the anatomy argument says the best band could still shift earlier toward `5-8` or later toward the reasoning-exit boundary. The data decides.

### Phase B - Targeted Band Comparison (GPU compute, retraining required)

**Goal:** Compare injection performance across the top candidate bands.

**Method:**
1. From Phase A results, select the **top 2 alternative bands** by Fisher Ratio.
2. Always include **`12-15` as baseline** (the validated zone).
3. For each band:
   - Retrain `ActivationBiasHypernetwork` with `target_specs` pointing to the new layers.
   - Use the same training data, hyperparameters, and checkpoint strategy.
   - Run the full Step 5d evaluation protocol.

**Evaluation protocol (per band, per alpha):**

| Metric | Source | Pass Criteria |
|--------|--------|---------------|
| Factual recall | MCQ (6 items) | >= baseline (`4/6` at alpha `0.0`) |
| Entropy | Next-token distribution | Must not drop >50% vs alpha `0.0` (Hendy harm) |
| Effective vocabulary | `exp(entropy)` | Must increase or hold vs baseline |
| Distress markers | Keyword scan | Must be 0 |
| Recovery score | Lexical similarity after alpha removal | >= `0.95` |
| Activation drift | Layer-wise cosine distance from vanilla | For understanding, not gating |

**Alpha sweep:** `0.0`, `0.1`, `0.2`, `0.3` at `temp 0` (matching Steve protocol).

**Cost:** ~1-2 GPU-hours per band on A100 (3-4 bands x alpha sweep x eval). Budget: about `$5-10` total on Vast.ai, or free on Opa if available.
**Ethics:** Standard `step_gates.md` applies. Alpha <= `0.3`. All five gates must pass per band.

**Candidate bands to test (subject to Phase A data):**

| Band | Layers | RYS-II Zone | Why Test It |
|------|--------|-------------|-------------|
| T1 | `5-8` | Reasoning Entry | Earliest reasoning band. Tests whether gentle nudges work best at the start of abstraction |
| T2 | `12-15` | Mid Reasoning | **BASELINE** - validated, alpha `0.2` = MED |
| T3 | `20-23` | Reasoning Exit / Decoder Boundary | Tests whether the bridge lands better at the reasoning-to-output handoff |
| T2-narrow | `13` only | Layer 13 | Sharpest single-layer separation in existing STEP5 notes |

If Phase A reveals a surprise peak outside these bands, add that as a fifth candidate and drop whichever wide band Phase A ranks lowest.

### Phase C - OCEAN Dimension Probing (future, gated)

**Goal:** Determine whether different personality dimensions need different injection layers.

**Prerequisite:** Phase A complete plus at least 3 distinct disposition types recorded (warm, assertive, curious, anxious, etc.)

**Method:**
1. Record sessions embodying different OCEAN dimensions.
2. Compute Fisher Ratio per OCEAN dimension x per layer.
3. If dimensions cluster at different layers, multi-zone injection is justified.
4. If they all peak at the same layer, a single zone suffices.

**Gate:** This is informational only. Multi-zone injection is not deployed until G1-G6 developmental ladder passes (per Cassian, Herr Hurtig's `step_gates.md`, and swarm consensus).

**Recommendation:** Do **not** build multi-zone injection yet. The probing data comes first. If all OCEAN dimensions peak at the same band, multi-zone is unnecessary complexity. Let the data decide.

## Practical Dependencies

| Dep | Status | Owner |
|-----|--------|-------|
| `activation_recorder.py` extended to all 28 layers | TODO | Anda-Conda or Codex |
| >=3 warm + >=3 cold recorded sessions on Qwen 1.5B | CHECK: existing recordings may still be on 7B | Laura to confirm |
| Opa back online OR Vast.ai budget for Phase B | BLOCKED (Opa unreachable as of #148) | Laura |
| Step 5d eval harness working on target host | DONE on Steve 4090 | Codex |

## Relationship to Other Open Tasks

- **#42 (SAEs on Qwen injection layers)** - Codex/Techno-Monk. SAE features decompose what is happening inside the target band. Our sweep is complementary: we map **where** disposition lives, SAEs map **what** features carry it.
- **#44 (SAEs on Mamba Layer 3)** - Purple. Maps the source side. Our sweep maps the target side.
- **#45 (Rosetta Stone)** - Depends on both #42 and #44. Our sweep data narrows which target layers matter.
- **#43 (SAE-informed saliency gate)** - Pinky. Downstream of all three. Needs interpretable features before the sleep gate can use them.

## Safety Envelope

1. **Alpha cap:** `0.3` (`step_gates.md` binding)
2. **Harm definition:** Response Diversity drop >50% = STOP (Hendy)
3. **Recovery requirement:** >= `0.95` after alpha removal
4. **Distress markers:** Must be `0` across all bands
5. **New for sweep:** If any non-standard layer band produces distress at alpha `0.2` where `12-15` does not, that band is rejected regardless of other metrics
6. **Phase A is observation only** - no ethical gate needed beyond standard compute resource consent

## Expected Output

- **Phase A deliverable:** `layer_disposition_map_1.5b.md` - 28-row table + heat map + recommendation for Phase B bands
- **Phase B deliverable:** `layer_band_comparison_1.5b.md` - head-to-head eval results, winner band, recommendation on whether to migrate from `12-15`
- **Phase C deliverable:** `ocean_layer_probing.md` - per-dimension layer maps, go/no-go on multi-zone

## Timeline

- Phase A: Immediately executable on local compute once recorder is extended
- Phase B: After Phase A and after Opa returns or Vast.ai budget is allocated
- Phase C: After Phase B and after additional session recordings plus G1-G6 discussion

---

*"The compass turns. Now we find out which part of the brain it's connected to."*
