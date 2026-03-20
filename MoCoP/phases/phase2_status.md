# Phase 2 Status Snapshot

**Last updated:** 2026-03-18  
**Purpose:** live status/index for Phase 2. This file should stay short and current.  
**Not this file:** a full experiment diary, architectural manifesto, or historical runbook.

## Current Verdict

Phase 2 now has a real compressed-path control stack.

- The compressor-bypass ablation failed end-to-end.
- The compressed `activation_bias` path survives both major controls.
- Held-out factual recall is still `0/16`.
- The channel looks real on the compressed path, but still narrow.

The current control hierarchy is:

`per-sample activation_bias > fixed_mean >> constant_bias`

The next move is a research decision between Step 2b and Step 5, not another round of basic control building.

## Current Canonical Configuration

- **Primary Qwen default:** `Qwen/Qwen2.5-7B`
- **Mamba source:** `state-spaces/mamba-2.8b-hf`
- **Prompt surface for bridge eval:** `completion`
- **Current bridge baseline:** dynamic LoRA with contiguous mid-block targeting
- **Current reduced variant available:** `activation_bias` exists in the trainer path
- **Current new control available:** `constant_bias` now exists in the trainer path

## What Phase 2 Has Established

### D1 Baseline Solvability

Done. All 5 locked base models passed the baseline solvability gate.

### Tiny-Overfit Signal

The bridge can memorize a tiny shared train/eval subset. That result is real, but it should now be treated as **memorization**, not transfer.

### 64-Sample Scale-Up

The Sweden `64`-sample A3 completion burst gave the clearest Phase 2 answer so far:

| Epoch | Recall | Bridge PPL | Baseline PPL | Train Loss |
|---|---|---|---|---|
| 1 | 0/16 | 28.96 | 29.71 | 4.25 |
| 2 | 0/16 | 44.06 | 29.71 | 3.07 |
| 3 | 0/16 | 43.15 | 29.71 | 2.33 |

Interpretation:

- epoch 1 shows a weak but real constructive steering signal
- held-out recall stays zero
- later epochs overfit and become destructive

## Current Open Gates

1. **Step 2b decision gate**
   Single-layer raw bypass failed end-to-end, but raw contexts still contain more structure than compressed ones. Multi-layer concat is now a deliberate next-step choice, not an automatic follow-up.

2. **Step 5 substrate decision**
   The current controls justify moving beyond "is the channel empty?" but do not yet justify any claim about disposition transfer. The next substrate should be chosen deliberately.

3. **Raw-bias proof gap**
   The raw bypass host was lost before the checkpoint came home, so raw bias-vector collapse remains strongly suspected, not directly proven.

## Canonical Detail Docs

Read these in roughly this order:

1. `MoCoP/phases/phase2_diagnostic_ablation_plan.md`
2. `MoCoP/experiments/mamba_lora_bridge/BURST_2_DEBRIEF.md`
3. `MoCoP/EXPERIMENT_LADDER.md`
4. `MoCoP/phases/step4_constant_bias_runbook.md`
5. `MoCoP/experiments/mamba_lora_bridge/review_synthesis.md`
6. `MoCoP/experiments/mamba_lora_bridge/CODEX_TASKS.md`

## Historical Note

Older Phase 2 notes that mention `Qwen/Qwen3-4B`, early pilot framing, or pre-Sweden optimism are historical artifacts, not current runtime truth.

Use `CHEESE_Memory/00_HANDOFF.md` for the live cross-project control page and this file as the compact Phase 2 state snapshot.
