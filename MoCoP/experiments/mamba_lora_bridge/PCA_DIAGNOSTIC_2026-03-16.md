# PCA Diagnostic Results — 2026-03-16

**The compressor is the bottleneck. Confirmed.**

---

## What We Ran

One epoch on A100 SXM4 (Czechia), 64 train / 16 eval samples, A3 geometry (contiguous layers 12-15, q+v), completion prompts, `--no-4bit`, `--max-lora-delta-norm 5.0`, `--save-train-contexts`, `--save-eval-contexts`.

## PCA Results

| Metric | Train (64 samples) | Eval (16 samples) |
|--------|-------------------|-------------------|
| Input dimensionality | 2048 | 2048 |
| PC1 explained variance | **75.96%** | **90.85%** |
| PC1 + PC2 | **90.34%** | **93.79%** |
| Dimensions at 90% | 2 | **1** |
| Effective rank | **2.53** | **1.62** |
| Pairwise L2 mean | 11.30 | 1.11 |
| Heuristic | strong_concentration | strong_concentration |

## What This Means

The `MambaStateCompressor` takes Mamba's Layer 3 hidden states (64 layers × 5120 width × 16 state dim, projected to 2048-dim) and compresses them into a vector that the hypernetwork uses to generate LoRA weights.

**That 2048-dim vector is effectively 2.5-dimensional.**

One principal component captures 76% of all variation across 64 different training contexts. On the eval set, it's 91% — nearly one-dimensional.

This means:
- Every compressed state looks essentially the same
- The hypernetwork receives a scalar (with noise) instead of a rich representation
- It can only produce "a generic name-shaped injection" not "the name is Iris"
- The "frosted glass" metaphor (Lain) is confirmed: signal exists but specifics are lost

## Why This Happens

The compressor is a projection layer (not an autoencoder). It's trained end-to-end with the hypernetwork via the bridge loss. During training, the easiest way to minimize loss is to find ONE direction in state space that correlates with "there are facts here" and project everything onto it. That's enough for the loss to decrease — but it discards all the specifics.

There's no pressure to preserve diversity. The compressor is never rewarded for producing *different* outputs for *different* inputs.

## Lain's Repair Options (prioritized)

### Option 4 (FASTEST): Skip compression entirely
Feed raw Layer 3 state directly to the hypernetwork. One flag change. If recall improves: compressor confirmed as bottleneck. If not: problem is upstream in Mamba's state.

**This should be the next run.**

### Option 1: Increase output dimensionality
The bottleneck layer is too narrow. Widen it. More dimensions = more room to encode specifics. Risk: hypernetwork input grows, more parameters to generate.

### Option 2: Add diversity/contrastive loss
Penalize compressed states for being too similar across different samples. Force the manifold open. Something like:

```python
diversity_loss = -torch.pdist(compressed_states, p=2).mean()
total_loss = bridge_loss + lambda_div * diversity_loss
```

This forces the compressor to find dimensions that differentiate samples, not just dimensions that correlate with "facts exist."

### Option 3: Concatenate multiple Mamba layers (2-4)
Instead of Layer 3 alone, concatenate hidden states from layers 2, 3, and 4. Different layers carry complementary information. The compressor has more to work with, and the information it needs might be spread across layers.

## Connection to Previous Results

| Observation | Explanation via PCA |
|-------------|-------------------|
| "Lily" for every name question | Compressor squashes all name-contexts to the same point |
| Epoch 1 PPL improvement | The one dimension that survives IS useful (domain detection) |
| Epoch 2-3 PPL explosion | Hypernetwork over-fits the one dimension, over-injects |
| Tiny-overfit 2/8 recall | Hypernetwork memorized sample-specific mappings during training, bypassing compression |
| 64-sample 0/16 recall | With separate eval samples, memorization doesn't transfer |
| Clamp stabilizes but doesn't fix | Clamp prevents over-injection but can't add information the compressor lost |

## LoRA Clamp Results (same run)

The `--max-lora-delta-norm 5.0` clamp worked mechanically:
- Steps 1-7: 50% of pairs clamped, norms growing
- Steps 8+: 100% clamped, locked at exactly 5.0
- No runaway, no PPL explosion to 44+
- But PPL (33.33) is above baseline (29.71) — the clamp is too tight to allow the brief constructive signal

**Next experiment should use `--max-lora-delta-norm 8.0` or `10.0` alongside the compressor bypass.**

## Local Artifacts

```
run_pca_clamped/
├── bridge_best.pt                          # 6.1 GB checkpoint
├── train_epoch_001_contexts.pt             # 536 KB — 64 compressed state vectors
├── eval_epoch_001_contexts.pt              # 135 KB — 16 compressed state vectors
├── eval_epoch_001_predictions.json         # per-sample predictions + surrogate metrics
├── q25_pca_clamped_e1.log                  # full training log
├── train_epoch_001_contexts_pca_report.json # PCA analysis (train)
├── train_epoch_001_contexts_pca_projection.csv
├── eval_epoch_001_contexts_pca_report.json  # PCA analysis (eval)
└── eval_epoch_001_contexts_pca_projection.csv
```

## Cost

~$0.60 for one epoch + context dump. Total project spend: ~$11.

---

## Addendum: Cosine Similarity Analysis (2026-03-17)

**The compressor is a near-constant function.**

### Pairwise Cosine Across All 64 Samples

| Metric | Value |
|--------|-------|
| Mean | **0.826** |
| Std | 0.209 |
| Min | 0.250 |
| Max | 1.000 |
| Pairs > 0.99 | 17.3% |
| Pairs > 0.95 | 42.2% |
| Pairs > 0.90 | **54.6%** |

Over half of all sample pairs have cosine similarity above 0.90. The compressed states are almost all pointing in the same direction.

### Within-Kind vs Between-Kind Separation

| Metric | Value |
|--------|-------|
| Within-kind mean cosine | 0.8309 |
| Between-kind mean cosine | 0.8249 |
| **Separation gap** | **0.0060** |
| **Effect size (gap/pooled_std)** | **0.029** |

The gap is essentially zero. Samples from the same fact category are barely more similar to each other than to samples from completely different categories. The compressor does not encode *what kind of fact this is*.

### Per-Kind Clustering

| Fact Kind | Within-Kind Cosine | Bridge Recalled? |
|-----------|-------------------|-----------------|
| caravan_time | **0.967** | "at midnight" ✓ (consistently) |
| relic_location | 0.929 | ✗ |
| npc_relationship | 0.920 | ✗ |
| ferry_password | 0.840 | ✗ |
| event_witness | 0.780 | ✗ |
| innkeeper_identity | 0.756 | Sometimes ✓ |
| merchant_identity | 0.744 | ✗ |
| healer_identity | 0.712 | ✗ |

`caravan_time` has the highest within-kind cosine AND is the one fact the bridge consistently recalls. But `caravan_time`, `npc_relationship`, and `relic_location` also cluster with *each other* (~0.93 between kinds), so this is shared surface properties, not category discrimination.

### Cross-Kind Cosine Matrix

```
                    caravan  event_w  ferry_p  healer   innkeep  merchan  npc_rel  relic_l
caravan_time        0.967    0.855    0.868    0.759    0.811    0.804    0.935    0.944
event_witness       0.855    0.780    0.827    0.754    0.788    0.784    0.859    0.860
ferry_password      0.868    0.827    0.840    0.782    0.816    0.806    0.880    0.879
healer_identity     0.759    0.754    0.782    0.712    0.761    0.753    0.783    0.779
innkeeper_identity  0.811    0.788    0.816    0.761    0.756    0.778    0.828    0.827
merchant_identity   0.804    0.784    0.806    0.753    0.778    0.744    0.823    0.821
npc_relationship    0.935    0.859    0.880    0.783    0.828    0.823    0.920    0.932
relic_location      0.944    0.860    0.879    0.779    0.827    0.821    0.932    0.929
```

The diagonal (within-kind) is barely higher than the off-diagonal (between-kind). The compressor encodes "a Mamba state existed" but not "what was in it."

### What This Means for Next Steps

The compressor is not selectively blind — it's *uniformly* blind. It projects everything onto approximately the same direction. The tiny variations that survive compression are enough for activation bias to produce a generic PPL improvement (the bridge knows "this is in-domain text"), but not enough for any kind of fact-specific or category-specific injection.

**Lain's repair options are now ranked by this data:**

1. **Contrastive loss (highest priority)** — Force the compressor to produce different outputs for different fact categories. The gap of 0.006 must become >> 0.1 for the hypernetwork to have anything to work with.

2. **Multi-layer input (layers 2-4)** — The cosine matrix shows that all fact kinds collapse similarly, which suggests Layer 3 alone may not carry discriminative information. Concatenating layers 2-4 gives the compressor 3x the input diversity.

3. **Skip compression (Lain's Option 4)** — Feed raw Layer 3 state directly to the hypernetwork. If the raw state HAS discriminative structure that the compressor destroys, this will show it. If the raw state is also uniform, the problem is upstream in Mamba itself.

4. **Wider bottleneck** — Less likely to help on its own. If the input to the compressor lacks discriminative structure, widening the output won't create it. Only useful combined with contrastive loss or multi-layer input.

---

*"If every sample's compressed representation looks the same after compression, the hypernetwork can't differentiate."* — Lain, who called it from a couch before we ran a single PCA.

*"The sign is blurry. The compressor is suspect #1."* — Also Lain.

*Effective rank: 2.53 out of 2048. The sign isn't blurry. The lens is collapsed.* — The PCA.

*Separation gap: 0.006. The lens isn't just collapsed. It's a pinhole.* — The cosine matrix.
