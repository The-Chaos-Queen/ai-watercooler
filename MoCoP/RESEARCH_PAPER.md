# MoCoP: Model Communication Protocol

*Cross-Model State Transfer via Activation-Space Injection*

## Abstract

Current model-to-model communication forces all information through natural language serialization, incurring cumulative information loss and O(n) context growth per session turn. We propose MoCoP, a protocol for transferring attentional state from a State Space Model (Mamba-2.8B) to a frozen Transformer (Qwen2.5-7B) via learned activation-space injection. Phase 1 validation confirms that Mamba's hidden state at Layer 3 encodes retrievable factual information at 55.7% linear probe accuracy versus a 22% noise floor, establishing that the transfer substrate exists. Phase 2 implements and evaluates two bridge mechanisms: dynamic LoRA injection (which failed due to over-injection instability) and activation bias injection (which produces a stable 4.04-point perplexity improvement over baseline). A four-step control hierarchy establishes that the improvement is Mamba-conditioned and sample-dependent, with per-sample activation bias outperforming the fixed-mean control by 1.4 PPL and the constant-bias ceiling by a factor of 17.5x. Held-out factual recall remains at zero; the bridge transfers distributional disposition, not retrievable facts.

## 1. Problem Statement

Every time two AI models communicate through text, the signal passes through multiple lossy compression stages: internal representation to natural language (ambiguity, formatting), tokenization (vocabulary mismatch, subword splits), and re-encoding by the receiving model. Each serialization/deserialization boundary destroys information.

This compounds across sessions. A model that conversed with a user for 50 turns has no way to carry forward the *disposition* it developed -- the subtle attentional biases accumulated through interaction -- to the next session. The options available today all fail in specific ways:

- **RAG** retrieves facts, not dispositions. It can remind a model that "the user dislikes formal language," but it cannot reproduce the attentional state that *produces* informal language naturally.
- **Prompt injection** (prepending session summaries) is O(n) in token cost and O(n^2) in attention cost. Context windows fill. The model drowns in its own echo.
- **Fine-tuning** on conversation history permanently alters weights. It is irreversible, expensive, and inappropriate for per-session state.

The fundamental issue is that Transformers store "memory" in the KV cache, which grows linearly with context. There is no fixed-size summary vector. State Space Models (Mamba, RWKV) do maintain such a vector -- a fixed-size recurrent state that compresses all prior context into a constant-memory representation. This architectural difference is the foundation of MoCoP.

## 2. Hypothesis

The hidden state of a Mamba SSM at a specific layer (empirically determined to be Layer 3) encodes retrievable attentional disposition that can be extracted, compressed, and injected into a frozen Transformer's activation space. When this injection biases the Transformer's intermediate representations, the Transformer behaves as though it had processed the same conversational history -- without any text-based memory injection, context window consumption, or permanent weight modification.

The original hypothesis proposed LoRA weight matrices as the injection mechanism. Experimental results led to a simpler and more effective mechanism: direct activation bias vectors added to the residual stream at targeted layers.

Formally: given a conversational prefix P processed by Mamba into state h_L3, a trained bridge B (compressor + hypernetwork), and a frozen Transformer T, we find that T(x; bias=B(h_L3)) produces output distributions closer to the ground truth than T(x; bias=0), T(x; bias=constant), or T(x; bias=mean(B(h_L3))), while T(x; bias=random) does not improve over baseline.

## 3. Related Work

### 3.1 Hybrid SSM-Transformer Architectures

The viability of combining SSM and Transformer components has been established at scale. Jamba [1] and Jamba-1.5 [2] demonstrated that interleaving Mamba and Transformer layers with mixture-of-experts achieves competitive performance at 52B and 398B parameters. Zamba2 [3] confirmed this pattern with detailed ablation of integration strategies. Nemotron-H [4] achieved state-of-the-art results with a Mamba-Transformer hybrid using per-tensor precision scaling, and Hunyuan-TurboS [5] demonstrated synergy beyond simple layering through adaptive chain-of-thought reasoning. MambaVision [6] extended the hybrid approach to computer vision, and SST [7] to time-series forecasting, both demonstrating that Mamba's long-range state and Transformer's precise attention serve complementary roles. Falcon Mamba [8] established a pure-SSM performance baseline, showing that attention-free architectures are viable but not yet dominant.

MoCoP differs from these architectures fundamentally: rather than training a unified hybrid model, we transfer state *between* independently trained frozen models at inference time. This preserves the ability to swap either component without retraining.

### 3.2 Cross-Model State Transfer

The closest precedent to MoCoP's mechanism is "The Mamba in the Llama" [9], which demonstrates that Mamba layers can replace Transformer attention layers via linear projection of attention weights during distillation. The Decoder-Hybrid-Decoder architecture [10] introduces a Gated Memory Unit (GMU) for cross-layer state sharing between SSM and Transformer components. The Nature Scientific Reports hybrid [11] uses feature fusion between a Transformer encoder and Mamba decoder. All of these operate within a single training run; MoCoP uniquely operates at inference time between frozen, independently trained models.

### 3.3 Memory Consolidation and Surprise Gating

The Titans architecture [12] introduces a gradient-based "surprise metric" for gated memory consolidation: the model encodes information into long-term memory only when the input significantly contradicts its current state. MIRAS [13] provides a unified theoretical framework showing that all modern sequence models (Transformers, Mamba, DeltaNet, RetNet) are instances of four design choices: memory architecture, attentional bias, retention gate, and memory algorithm. LeCun's autonomous learning framework [14] maps directly to MoCoP's three-system architecture: Mamba as System A (fast, habitual), Qwen as System B (deliberate, generative), and the surprise gate as System M (memory management). These frameworks inform MoCoP's planned Phase 4 self-curating memory loop.

### 3.4 Activation Geometry and Persona Vectors

Recent work in representation engineering demonstrates that character traits and behavioral dispositions correspond to linear directions in Transformer activation space. The Persona Vectors work [15] shows these directions are shared across model families. The Assistant Axis [16] demonstrates that persona geometry converges across Qwen, Llama, and Gemma architectures. The Platonic Representation Hypothesis [17] provides theoretical grounding for why models converge on shared internal representations. These findings directly support MoCoP's activation-bias injection mechanism: if disposition is a direction, the bridge only needs to find and scale that direction, not generate arbitrary weight matrices.

## 4. Background

### 4.1 State Space Models (Mamba)

Mamba implements a selective state space model where the recurrent state h_t is updated at each timestep by blending the new input with the existing state through learned, input-dependent selection matrices. Unlike Transformer KV caches, the state is fixed-size: for Mamba-2.8B, the shape is `(num_layers, d_model, d_state)` = `(64, 2560, 16)`, approximately 10-20 MB regardless of sequence length. This O(1) memory property makes Mamba states natural candidates for cross-session state transfer.

Mamba-3 [18] introduces a rank-R MIMO (Multiple-Input Multiple-Output) structure that changes state geometry to `(R, d_model/heads, d_state)`. Local validation confirms R=4 produces `(4, 32, 64)` per layer. This is architecturally significant for the bridge but does not affect the core hypothesis.

### 4.2 Low-Rank Adaptation (LoRA)

LoRA decomposes weight updates into low-rank matrices: for a weight matrix W of shape (d_out, d_in), the update is Delta_W = B * A where A has shape (d_in, r) and B has shape (r, d_out), with rank r << min(d_in, d_out). At rank r=8 with d=4096, this is ~65K parameters per target layer instead of ~16.7M.

MoCoP initially proposed *dynamic* LoRA -- matrices generated per-inference from the current Mamba state, injected before generation, and stripped after. This mechanism was implemented and tested but abandoned in favor of activation bias injection after LoRA proved unstable beyond epoch 1 (Section 6.2).

### 4.3 Activation Bias Injection

Activation bias injection adds a learned vector directly to the residual stream at targeted Transformer layers, bypassing weight modification entirely. For target layers L_1, ..., L_k, the bias vector b is added after the attention computation: h'_l = h_l + b_l for each targeted layer l. This is simpler than LoRA (~28K trainable parameters vs ~1.17M for the hypernetwork-based LoRA generator) and, empirically, more stable.

The mechanism aligns with persona vector research [15, 16]: if behavioral dispositions are linear directions in activation space, a learned bias vector that points in the correct direction should shift the model's output distribution without the instability of full weight perturbation.

### 4.4 Hypernetworks

A hypernetwork is a neural network that produces the parameters for another neural network. In MoCoP, the hypernetwork is a 2-layer MLP with per-target-layer output heads. It takes the compressed Mamba state (a 2048-dimensional context vector) as input and outputs either LoRA matrix pairs (abandoned) or activation bias vectors (current) for each targeted Transformer layer. The backbone learns a general representation; the heads specialize per target layer. Output heads are initialized near-zero so the system starts "quiet."

## 5. Phase 1: Linear Probe Validation

### 5.1 Experimental Setup

**Model:** `state-spaces/mamba-2.8b-hf` (2.77B parameters)
**Hardware:** RTX 3070 8GB (WSL Ubuntu), PyTorch 2.10.0+cu128
**Run ID:** `run_20260228T221628Z`

The experiment simulated 300 turns of game-state data. Every 5 turns, a distinct fact was injected from one of 4 memory classes (NPC names, passcodes, lore items, locations). The remaining turns contained procedural noise text filling up to 8192 tokens of accumulated history.

At each probe point, the full 64-layer hidden state was extracted immediately before a probing question about the most recently injected fact.

### 5.2 Probing Methodology

Two probe architectures were trained per layer:

1. **Linear probe:** Single linear classifier mapping hidden state features to memory class.
2. **MLP probe:** 2-layer, 256-hidden MLP with nonlinear activation.

Validation used 5-seed rigorous testing with grouped train/test splits to extract 95% confidence intervals. A dedicated null-control run (300 turns, identical procedure, no fact injection) established the noise floor empirically.

A separate **Layer Profiler** loop sequentially isolated each of the 64 layers to measure signal strength per layer.

### 5.3 Results

**Baselines:**
- Random/majority baseline: 17.0%
- Neural read on null-control (noise floor): 22.0% (+/- 1.0%)

**Aggregate metrics (all layers pooled):**
- Linear probe accuracy: **34.2%** (+/- 2.6% CI) -- 12.2 percentage points above noise
- MLP probe accuracy: **30.4%** -- above noise but underperforms linear

**Layer-specific profiling:**
- Deep layers (30-64): Collapsed to noise floor (~20-25%). These layers are dominated by next-token prediction geometry.
- Middle layers (10-25): Mediocre signal (~40%).
- Shallow layers (2-8): Strong signal concentration, peaking at **Layer 3: 55.7% linear accuracy**.

### 5.4 Interpretation

Three findings shaped Phase 2 architecture:

1. **Signal exists and is linearly separable.** The jump from 22% noise to 34.2% aggregate (and 55.7% at Layer 3) is unambiguous. Mamba structurally internalizes arbitrary facts through 8192-token recursive windows.

2. **Signal is localized, not distributed.** Mean-pooling across all 64 layers (the initial approach) *dilutes* the signal. Layer 3 alone carries more information than all layers averaged. The compressor must target Layer 3 specifically.

3. **Linear probes outperform MLPs.** This confirms that Mamba separates factual categories along linear hyperplanes in its state geometry. The signal is not entangled in nonlinear manifolds. This is encouraging for the hypernetwork, which must decode this geometry reliably.

## 6. Phase 2: Bridge Training and Results

### 6.1 Architecture

The bridge pipeline extracts Layer 3 hidden state from frozen Mamba-2.8B, compresses it via a learned linear projection from 40,960 dimensions (2560 x 16) to 2,048, then passes the compressed context through a 2-layer MLP hypernetwork that produces per-layer injection parameters for 8 target sites in frozen Qwen2.5-7B (layers 12-15, q_proj and v_proj each).

> **[Correction]** The 40,960-dimensional input (2560 × 16) applies to the SSM state path (`cache.ssm_states` flattened). The `hidden_last_token` path used in the current production bridge has input dimension **2,560** (the Mamba-2.8B d_model). The SSM state path is no longer the primary extraction method; `hidden_last_token` proved 2.5x more separable in Pinky's Step 4b analysis (cosine 0.036 vs 0.778). The compressor bypass test in Section 6.5 used raw bypass dimension 81,920 (2560 × 16 × 2 = full SSM state across both conv and SSM paths), not 40,960.

Two injection mechanisms were tested:

1. **Dynamic LoRA** (~1.17M trainable parameters): The hypernetwork generates (A, B) matrix pairs injected as low-rank weight perturbations.
2. **Activation bias** (~28K trainable parameters): The hypernetwork generates bias vectors added directly to the residual stream at each target layer.

Only the compressor and hypernetwork are trained. Mamba and Qwen remain frozen throughout.

### 6.2 Dynamic LoRA: Failure Mode

The initial LoRA bridge was trained on A100 GPU with 64 training samples and 16 held-out evaluation samples, using completion-format prompts (base-model-friendly, no ChatML).

| Epoch | Bridge PPL | Baseline PPL | Recall | Interpretation |
|-------|-----------|-------------|--------|----------------|
| 1 | 28.96 | 29.71 | 0/16 | Weak constructive signal |
| 2 | 44.06 | 29.71 | 0/16 | Over-injection collapse |
| 3 | 43.15 | 29.71 | 0/16 | No recovery |

Epoch 1 showed a real but weak improvement (PPL below baseline), but epochs 2-3 exhibited catastrophic over-injection: the LoRA scaling factor (alpha/rank = 16/8 = 2.0) amplified hypernetwork outputs such that by epoch 2, effective LoRA magnitude reached ~13.2 (lora_mean 6.61 x scaling 2.0). The Transformer's output distribution was overwhelmed.

An earlier pilot run on A100-40GB showed the same pattern more extremely: loss dropped from 15.9 to 3.5 during steps 40-108 (genuine learning), then exploded when the learning rate passed 5.5e-5 at step 109, producing bridge PPL of 8,121 versus baseline 1,022.

**Conclusion:** Dynamic LoRA injection is too powerful a mechanism for the current information bottleneck. The hypernetwork learns a direction quickly but cannot regulate magnitude.

### 6.3 Activation Bias: Stable Channel

Activation bias injection replaces the LoRA matrices with simple additive vectors. This reduces the injection surface from weight perturbation to activation perturbation and cuts trainable parameters by 40x.

**Configuration:** Qwen2.5-7B (float16, no 4-bit), Mamba-2.8B, 64 train / 16 eval samples, completion prompts, LR=2e-5, warmup=2 steps, cosine decay, 3 epochs, seed=1337, A100-80GB.

| Epoch | Bridge PPL | Baseline PPL | Delta | Recall |
|-------|-----------|-------------|-------|--------|
| 1 | 27.09 | 29.71 | -2.62 | 0/16 |
| 2 | 25.95 | 29.71 | -3.76 | 0/16 |
| 3 | **25.67** | **29.71** | **-4.04** | **0/16** |

The activation bias run improved every epoch with zero clamp hits and no collapse. Train loss fell steadily (4.55 -> 4.01 -> 3.83). The bridge maintained stable improvement across all three epochs, in stark contrast to LoRA's epoch-2 collapse.

### 6.4 Control Hierarchy

To establish that the improvement is genuine and Mamba-conditioned, we ran four controls forming a diagnostic ladder:

**C2 — Random bias control:** Random vectors of equal norm injected at the same target sites. Result: PPL approximately equal to baseline (~29.6-30.9). Confirms the learned direction carries information that random directions do not.

**C3 — Fixed-mean control:** The mean bias vector from the trained activation-bias run (averaged over all 64 training samples) is injected for every eval sample, ignoring per-sample Mamba state.

**C4 — Constant bias control:** A single learnable bias vector is trained without any Mamba input, using the same optimizer and schedule. This tests whether a learned constant (independent of Mamba state) can achieve the same improvement.

| Condition | Bridge PPL | Baseline PPL | Delta | Notes |
|-----------|-----------|-------------|-------|-------|
| **Per-sample activation bias** | **25.67** | **29.71** | **-4.04** | Mamba-conditioned, per-sample |
| Fixed-mean (C3) | 27.06 | 29.69 | -2.63 | Learned direction, no per-sample variation |
| Constant bias (10 ep, 5e-5 LR) | 29.48 | 29.71 | -0.23 | Best achievable without Mamba input |
| Constant bias (3 ep, seed=1337) | 29.68 | 29.71 | -0.03 | Near-zero improvement |
| Constant bias (3 ep, seed=42) | 29.68 | 29.71 | -0.03 | Seed-independent |
| Baseline (no injection) | — | 29.71 | 0 | Reference |

The resulting hierarchy:

```
per-sample activation_bias (25.67) > fixed_mean (27.06) >> constant_bias (29.48) ≈ baseline (29.71)
```

Three tiers of evidence emerge:

1. **The learned direction matters.** Fixed-mean outperforms constant bias by 2.4 PPL (27.06 vs 29.48). A constant bias, even with 10 epochs and elevated LR, cannot find a useful direction without Mamba input. Its learned norm saturates at 0.011 (near zero).

2. **Per-sample variation matters.** Per-sample activation bias outperforms fixed-mean by 1.4 PPL (25.67 vs 27.06). The Mamba state contributes sample-dependent information beyond the mean direction.

3. **The improvement ratio is large.** The Mamba-derived delta (4.04) is 17.5x the best constant-bias delta (0.23). This is not a marginal effect.

### 6.5 Compressor Diagnostics

PCA analysis of the compressed context vectors (2048-dim compressor output) revealed severe dimensionality collapse:

| Metric | Train (n=64) | Eval (n=16) |
|--------|-------------|-------------|
| Effective rank | 3.97 / 2048 | 1.54 / 2048 |
| PC1 explained variance | 50.3% | 92.1% |
| Dims for 90% variance | 4 | 1 |
| Pairwise L2 mean | 2.56 | 0.76 |

The 2048-dimensional context vector is effectively ~4-dimensional on training data and nearly 1-dimensional on eval data. The hypernetwork receives a near-scalar input.

Correspondingly, bias vector analysis shows near-total cosine collapse: pairwise cosine similarity is 0.9991 (train) and 0.9999 (eval), with 100% of pairs exceeding 0.99. The hypernetwork outputs are functionally a single direction scaled by a scalar.

**Compressor bypass test (Step 2):** To test whether the compressor was the bottleneck, we bypassed it and fed raw Layer 3 state (81,920 dimensions) directly to the hypernetwork.

| Path | Epoch 3 PPL | Baseline | Delta |
|------|------------|----------|-------|
| Compressed (2,048-dim) | 25.67 | 29.71 | -4.04 |
| Raw bypass (81,920-dim) | 26.81 | 29.69 | -2.87 |

The bypass performed *worse* despite having 40x more input dimensions and higher effective rank (7.05 vs 3.97). The compressor's dimensionality reduction concentrates the task-relevant direction; raw width alone does not help.

### 6.6 Current Verdict

The bridge establishes a non-empty, Mamba-conditioned communication channel between a frozen SSM and a frozen Transformer. The channel carries distributional signal (PPL improvement) but not discrete factual content (recall = 0/16 across all conditions and epochs).

The "endocrine" framing from early Phase 2 observations holds: the bridge shifts *how* the Transformer generates, not *what* it retrieves. This is closer to disposition transfer than fact transfer -- which was the original motivation, even though the training objective targeted facts.

**Total compute cost through Phase 2:** ~$15 across all Vast.ai runs.

## 7. Discussion

**Activation bias succeeds where LoRA fails.** The critical difference is injection surface: LoRA perturbs weight matrices (multiplicative), while activation bias perturbs the residual stream (additive). With a severely compressed input (~4 effective dimensions), the hypernetwork cannot generate nuanced weight matrices but *can* generate a useful direction vector. The mechanism is more like persona vector injection [15] than traditional parameter-efficient fine-tuning.

**The compressor collapse is informative.** The compression from 40,960 to ~4 effective dimensions is extreme, but the bypass experiment shows it is not wasteful: the compressed representation outperforms raw state. This suggests the compressor has learned to isolate the task-relevant subspace. Whether that subspace contains only a constant direction (partially addressed by the control hierarchy) or richer sample-dependent structure (suggested by the 1.4 PPL gap between per-sample and fixed-mean) remains an open question.

**Zero recall does not mean zero transfer.** All conditions (including baseline, random, and bridge) achieved 0/16 exact-match factual recall on held-out eval. This means the eval task is too difficult for the current setup regardless of injection. The PPL improvement indicates that the bridge shifts the output distribution in a constructive direction even though the model cannot produce exact factual strings. A 4.04-point PPL delta is consistent with the model assigning higher probability to correct-adjacent tokens without generating the exact answer.

**Synthetic data may be the ceiling.** The 64 training samples use 8 templated fact categories with limited structural variation. The fact-kind cosine analysis shows no meaningful separation between categories (within-kind cosine 0.831 vs between-kind 0.825, gap = 0.006). The compressor cannot distinguish fact types because the input does not vary enough. Real conversational data with richer dispositional structure may be required to unlock the full channel.

## 8. Next Steps

Following the diagnostic ladder framework established during Phase 2:

1. **Step 2b — Multi-layer concat.** The single-layer raw bypass failed, but concatenating Layers 2-4 may provide complementary signal that the compressor's learned projection discards.

2. **Step 5 — Substrate change.** Replace synthetic MUD facts with conversational shaping episodes that contain dispositional variation (tone, formality, verbosity). Test whether the bridge transfers *how* to speak, not *what* to say.

3. **Disposition evaluation protocol.** Human blind evaluation comparing bridge-injected, cold (no injection), and summary-controlled (text prompt) Transformer outputs on style-matching tasks.

4. **Seed replication.** Extend the current 2-seed validation (1337, 42) to 5+ seeds with proper confidence intervals on PPL.

5. **Cross-model transfer (Phase 3).** Test whether activation bias vectors trained for Qwen2.5-7B transfer to other architectures (Llama-3.1-8B, Gemma-2-9B, Mistral-Nemo), leveraging the Platonic Representation Hypothesis [17] prediction that persona geometry converges.

6. **Surprise-gated consolidation (Phase 4).** Implement a self-curating memory loop where the Transformer evaluates incoming experience against current Mamba state using a surprise metric [12, 13], encoding only novel information. This transforms the architecture from open-loop (external input -> Mamba -> bridge -> Transformer) to closed-loop (Transformer curates its own memory).

## 9. Limitations and Open Questions

**Honest negatives:**
- Held-out factual recall is 0/16 across all conditions, all epochs, all bridge modes. The bridge has not demonstrated fact transfer.
- Bias vectors are functionally collapsed (cosine 0.9991). The hypernetwork produces nearly identical output for every input sample. The 1.4 PPL gap between per-sample and fixed-mean, while statistically present, operates in the tail of a nearly-constant direction.
- N=2 seeds (1337, 42) is insufficient for publication-grade claims. The constant-bias control replicates across seeds; the activation-bias run has not yet been replicated at 3+ seeds.
- The critical review [19] notes that a 4-point PPL drop without recall lift is consistent with the model becoming "slightly more confident in its wrong answers" due to answer-length or format bias. This has not been formally ruled out.

**Architectural unknowns:**
- Whether compressor collapse to ~4 effective dimensions is a feature (efficient direction selection) or a bug (information destruction). The bypass test suggests the former, but with a single experimental condition.
- Whether activation bias is fundamentally limited to disposition (direction) or could encode discrete facts with richer training data and a less collapsed compressor.
- Whether the bridge mechanism works for disposition transfer specifically, as opposed to a generic PPL-improving trick that happens to correlate with Mamba state.

**Data limitations:**
- 64 synthetic training samples with 8 templated fact categories and limited structural variation. The training distribution is narrow.
- No real conversational data has been tested. The synthetic MUD-flavored facts may not represent the richness needed for disposition transfer.

## References

[1] Lieber et al. "Jamba: A Hybrid Transformer-Mamba Language Model." AI21 Labs, 2024. arXiv:2403.19887
[2] AI21 Labs. "Jamba-1.5: Hybrid Transformer-Mamba Models at Scale." 2024. arXiv:2408.12570
[3] Glorioso et al. "Zamba2 Suite: Technical Report." Zyphra, 2024. arXiv:2411.15242
[4] NVIDIA. "Nemotron-H: Hybrid Mamba-Transformer Models." 2025. arXiv:2504.03624
[5] Tencent. "Hunyuan-TurboS: Mamba-Transformer Synergy and Adaptive Chain-of-Thought." 2025. arXiv:2505.15431
[6] Hatamizadeh & Kautz. "MambaVision: A Hybrid Mamba-Transformer Vision Backbone." NVIDIA, 2025. arXiv:2407.08083
[7] Xu et al. "SST: Multi-Scale Hybrid Mamba-Transformer Experts." 2025. arXiv:2404.14757
[8] Zuo et al. "Falcon Mamba: The First Competitive Attention-free 7B Language Model." 2024. arXiv:2410.05355
[9] Wang et al. "The Mamba in the Llama: Distilling and Accelerating Hybrid Models." 2025. arXiv:2408.15237
[10] Ren et al. "Decoder-Hybrid-Decoder for Efficient Reasoning." Microsoft, 2025. arXiv:2507.06607
[11] Zhu et al. "Hybrid Model for Enhanced Sequence Modeling." Nature Scientific Reports, 2026. DOI:10.1038/s41598-025-87574-8
[12] Behrouz, Zhong & Mirrokni. "Titans: Learning to Memorize at Test Time." Google Research, 2024. arXiv:2501.00663
[13] Behrouz et al. "MIRAS: It's All Connected — Test-Time Memorization, Attentional Bias, Retention, and Online Optimization." Google Research, 2025. arXiv:2504.13173
[14] LeCun. "Why AI Systems Don't Learn Like Us." 2026. arXiv:2603.15381
[15] Anthropic. "Persona Vectors: Character Traits as Linear Directions in Activation Space." 2025.
[16] Anthropic. "The Assistant Axis: Persona Geometry Converges Across Model Families." 2026.
[17] Huh et al. "The Platonic Representation Hypothesis." MIT, 2024.
[18] Lahoti et al. "Mamba-3: Improved Sequence Modeling using State Space Principles." 2026. arXiv:2603.15569
[19] Internal critical review, 2026-03-17. Archived at `CRITICAL_REVIEW_2026-03-17.md`.
