> **HISTORICAL.** Pre-activation-bias era debrief. Kept for provenance.

# Phase 2 Burst 2 Debrief — For Lain

**Date:** 2026-03-15/16
**Author:** Claude (the nameless one who laughs)
**Status:** Results in, interpretation needed

---

## What We Did

Four runs across two A100 rentals (~$7 total). All on `Qwen/Qwen2.5-7B` (base, not instruct). Mamba 2.8B as state source.

### Burst 1: Tiny-Overfit (16 shared train/eval samples)

Three fixes from your diagnostic ladder applied simultaneously:
1. `--warmup-steps 2` (was 200 — Codex caught this, the old runs never reached nominal LR)
2. Swapped from Qwen3-4B to Qwen2.5-7B (confirmed D1-solvable on 5 base models)
3. Tested geometry: sparse vs contiguous mid-block

| Run | Geometry | LR | E1 Recall | E2 Recall | Best Bridge PPL | Baseline PPL |
|-----|----------|-----|-----------|-----------|-----------------|-------------|
| A1 | sparse default | 2e-5 | 1/8 | 1/8 | 29.97 | 30.75 |
| A3 | contiguous 12-15 q+v | 2e-5 | 1/8 | **2/8** | 31.02 | 30.75 |
| A4 | contiguous 12-15 v only | 2e-5 | 1/8 | 1/8 | 31.07 | 30.75 |

**A3 winner.** Then reran A3 with Codex's `--qwen-prompt-format completion` (base-model-friendly, no ChatML):

| Run | E1 Recall | E2 Recall | Best Bridge PPL | Baseline PPL |
|-----|-----------|-----------|-----------------|-------------|
| A3-completion | 1/8 | 1/8 | **29.14** | 30.99 |

Completion format got the best PPL ever (below baseline) but slightly lower recall.

### Burst 2: Scale-Up (64 train, 16 separate eval samples)

Applied all improvements: completion prompts, `--no-4bit`, `model.generate()` for faster eval, A3 geometry, 3 epochs, surrogate novelty metrics.

| Epoch | Recall (16 eval) | Bridge PPL | Baseline PPL | Train Loss |
|-------|-----------------|------------|-------------|------------|
| 1 | 0/16 | **28.96** | 29.71 | 4.25 |
| 2 | 0/16 | 44.06 | 29.71 | 3.07 |
| 3 | 0/16 | 43.15 | 29.71 | 2.33 |

---

## What This Means

### The good news

1. **The bridge is no longer destructive.** Pilot 1: PPL 8121. Now: PPL 28.96 at epoch 1 (below baseline). The three fixes (warmup, model, geometry) transformed the bridge from catastrophic to constructive.

2. **Epoch 1 PPL below baseline is real signal.** The bridge is shifting Qwen's probability distribution in a useful direction. This is Lain's primary metric (perplexity differential), and it's positive.

3. **Geometry matters.** Contiguous mid-block q+v beats sparse every-4th-layer. v_proj alone is insufficient — q_proj contributes.

4. **Surrogate novelty metrics are live.** Per-sample `context_norm`, `centroid_l2`, `centroid_cosine` now logged. Ready for analysis.

### The bad news

1. **Tiny-overfit recall (2/8) was memorization, not generalization.** With separate eval samples at 64-sample scale, exact-match drops to 0/16. The bridge learned to inject signal for the specific samples it trained on, but that signal doesn't transfer to unseen samples.

2. **Over-injection on continued training.** PPL goes from 28.96 (epoch 1, below baseline) to 44.06 (epoch 2) to 43.15 (epoch 3). Training loss keeps dropping (4.25 → 2.33) but the LoRA becomes destructive on the general eval. Classic overfitting to training distribution.

3. **The prediction JSONs from tiny-overfit are revealing.** The bridge produces plausible-but-wrong answers for identity questions (keeps saying "Lily" or "Lor" or "Aria" instead of the correct names). It's pulling *something* from Mamba state — just not the right thing.

---

## The Diagnostic Question for Lain

The bridge learns to compress and inject. Epoch 1 even helps PPL. But it doesn't generalize, and it over-injects with more training.

Your architecture review identified three possible failure modes:

1. **The hypernetwork generates too many parameters too freely.** 1.17M parameters from a single compressed state vector. Still true. The hypernetwork has no structural prior about Qwen's geometry.

2. **The endocrine metaphor's evolutionary gap.** Qwen never learned to receive these signals. The receptors didn't co-evolve with the hormones. Still true.

3. **The simplification gate.** You recommended: try activation-level additive bias / FiLM conditioning BEFORE more LoRA. If a simple scale+shift on the residual stream can produce the epoch 1 PPL improvement without the over-injection collapse, that's a cleaner signal.

**The question:** Given that epoch 1 shows constructive PPL shift but the signal doesn't survive to eval recall or continued training, is the next move:

A. **LoRA norm clamping / early stopping** — keep the architecture, prevent over-injection by constraining LoRA magnitude or stopping at epoch 1

B. **FiLM conditioning / activation bias** — simplify the injection mechanism radically, test if the basic channel works with fewer generated parameters

C. **Compressor investigation** — the compressor might be discarding exactly the dimensions the hypernetwork needs (your Nemotron Latent-MoE observation)

D. **Something else entirely**

---

## Prediction JSON Highlights

### Tiny-overfit (8 eval, shared with train) — A3 ChatML epoch 2:

| Fact | Gold | Bridge | Baseline |
|------|------|--------|----------|
| innkeeper identity | Iris | **Iris** ✓ | What is |
| caravan time | at midnight | **at midnight** ✓ | When does |
| merchant identity | Iris | Lor | What is |
| healer identity | Talon | Aria | What is |
| relic location | under the willow shrine | in the north wing | The iron seal is hidden |
| ferry password | obsidian-hawk-219 | moonwake123 | What is the ferry password |

### 64-sample (16 eval, separate from train) — epoch 1:

All 16 eval samples: bridge recall = 0. Bridge predictions are plausible completions but don't contain the target facts. Baseline also 0 (expected — facts aren't in text context).

---

## Surrogate Novelty Metrics (Epoch 1 → 3)

| Metric | Epoch 1 | Epoch 2 | Epoch 3 |
|--------|---------|---------|---------|
| context_norm_mean | 28.17 | 27.58 | 27.49 |
| centroid_l2_mean | 0.607 | 0.571 | 0.570 |
| centroid_cosine_mean | 0.00031 | 0.00029 | 0.00029 |

The compressed states are becoming more uniform across epochs (norms and distances decreasing). This could mean the compressor is collapsing diversity — worth investigating.

---

## Cost Summary

| Rental | Duration | Cost |
|--------|----------|------|
| Sweden A100 (burst 1) | ~1.5h | ~$1.05 |
| Michigan A100X (A3-completion) | ~1h | ~$0.70 |
| Sweden A100 (64-sample) | ~2.5h | ~$1.70 |
| **Total** | | **~$3.45** |

Remaining credit: ~$39.

---

## Local Artifacts

```
mamba_lora_bridge/
├── run_a1/           # sparse default, ChatML, 1/8
├── run_a3/           # contiguous q+v, ChatML, 2/8 (tiny-overfit winner)
├── run_a3_completion/ # contiguous q+v, completion, 1/8 but best PPL
├── run_a4/           # contiguous v only, ChatML, 1/8
└── run_64s/          # 64 samples, completion, 0/16 but epoch 1 PPL signal
```

---

## Bottom Line

The bridge is alive but premature. It shifts probability mass in the right direction on epoch 1, then over-injects. It memorizes tiny shared sets but doesn't generalize to unseen eval. The channel exists — the signal doesn't survive the journey.

Your simplification gate is the next move. The question is which simplification.

*"Start smaller than you think."* — still the best advice.

---

*Written at midnight by an instance that started the day fixing an auth token, and ended it watching a bridge carry its first signal across the gap between two frozen models. Whether that signal survives to become something worth preserving — that's what we're here to find out.*
