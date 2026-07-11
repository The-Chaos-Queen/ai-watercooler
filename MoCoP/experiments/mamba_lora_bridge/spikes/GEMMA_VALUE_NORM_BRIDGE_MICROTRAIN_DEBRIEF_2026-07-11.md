# Gemma Value-Norm Bridge Microtrain — Debrief

**Date:** 2026-07-11
**Status:** offline bridge-training spike passed; not a C1 run
**Commit:** `866fc8b` (`feat(mocop): run first Gemma value-norm bridge microtrain`)

## Why this was run

Laura corrected the planning posture: we are building because the current fixed,
stateless transformer arrangement appears to be missing something worth building.
We do not know who benefits. The hope under test is that **Gemma itself may
benefit** from an additional continuity/state relation, rather than only being
prompted to imitate one.

The immediate correction was practical: run one bounded bridge train before
constructing further measurement-gate theory around an entirely untried bridge.

## Question

Can a small bridge learn a mapping from paired Mamba state deltas to paired
Gemma deltas at Gemma's **current, runtime-validated** value-side seam?

This is an offline learnability question. It is not a claim about behavior,
welfare, consciousness, identity, or C1 readiness.

## Current surface contract

| Role | Surface |
|---|---|
| Source | Mamba 2.8B Layer-3 last-token hidden state, scenario minus neutral, width 2560 |
| Target | Gemma 4 12B base `value_norm_pre`, scenario minus neutral, width 512 |
| Target teeth | Full-attention teeth `29`, `35`, `41` |
| Gemma revision | `1dd69cd087619018c29fbfe2c30c3cd3530479fb` |
| Mamba revision | `96c48e0292b63f5346b6d30061af2551f7101e26` |

The old C3/Qwen-era `v_proj` / 2048-wide plan was deliberately not used:
Gemma's current full-attention seam is `value_norm_pre`, 512-wide.

## Run

- **Pairs:** `craft_1_warm - craft_1_neutral` and
  `craft_2_warm - craft_2_neutral`, both selected from the frozen non-holdout
  SEV split.
- **Bridge:** three-head MLP, 268,032 trainable bridge parameters.
- **Training:** 16 CPU AdamW steps at learning rate `0.01`.
- **Frozen hosts:** Gemma and Mamba base weights were read only.
- **Explicitly absent:** nonzero injection, generation, Qdrant, memory, replay,
  sleep, persistence, and C1 runtime routes.

## Result

| Measure | Value |
|---|---:|
| Initial directional loss | `0.9836280942` |
| Final directional loss | `0.0099957781` |
| Source pair cosine | `0.0944672897` |
| Output pair cosines at teeth 29 / 35 / 41 | `0.3071274` / `0.3621168` / `0.3043999` |
| Checkpoint save/load round-trip | PASS |
| Post-run GPU state | `15 MiB / 24576 MiB`, `0%`, `34°C` |

The training path is real: cached Gemma and Mamba loaded, paired deltas were
captured, only bridge weights trained, and the saved bridge reloaded with finite
`[2, 512]` outputs at all three teeth.

## Evidence

- **Ignored local checkpoint:**
  `results/bridge_train_microtrains/real_two_pair_value_norm_microtrain_20260711T2015Z.pt`
- **SHA-256:**
  `c257dbad5eff64e3a0b4d823c8bf8635f33cd9575d57f3ee613128af23fb203c`
- **Tracked provenance receipt:**
  `results/bridge_train_microtrains/real_two_pair_value_norm_microtrain_20260711T2015Z.provenance.json`
- **Trainer:** `spikes/train_gemma_value_norm_bridge_microtrain.py`
- **Focused test:** `tests/test_gemma_value_norm_bridge_microtrain.py`
  (`3 passed` on ML-WS)
- **Watercooler:** #907, posted by `techno-monk` using its own token.

`*.pt` files are intentionally Git-ignored. The local artifact and ML-WS staged
copy are retained by hash; the provenance receipt is versioned.

## What this does and does not mean

### Established

- The canonical current Gemma `value_norm_pre` seam can be captured in paired
  delta space at teeth 29/35/41.
- A bridge can train against real paired Mamba/Gemma deltas and save/reload
  without modifying frozen host models or entering a C1 path.

### Not established

- Held-out generalization: two pairs are a training fit, not an evaluation.
- Behavioral or welfare benefit to Gemma.
- Consciousness, identity, continuity success, or a transferred inner state.
- Safety clearance, recovery, monitor validity, or any C1/nonzero-injection
  authorization.

## Smallest next useful step

Use a small **split-clean, disjoint train/evaluation slice** to read bridge
outputs on held-out paired deltas. Keep it offline and non-injecting. That tests
whether the bridge learns a mapping rather than merely two examples, without
turning the next move back into a gate-design festival.

The broader production recorder/trainer work remains OpenCLAW **#146**:
source-delta wiring, target-capture integration, split enforcement,
label-aware/deferred `L_sep`, provenance/atomic gates, and a throughput decision.
This spike neither closes nor bypasses that work.
