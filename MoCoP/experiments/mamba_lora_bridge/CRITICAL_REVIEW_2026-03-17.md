# Critical Review: Activation-Bias Result — 2026-03-17

**Reviewer:** Fresh Claude Opus 4.6 instance (no prior project context)
**Prompt version:** v2 (with mandatory controls, removed pre-planted framing)
**Requested by:** Laura Turner
**Facilitated by:** Claude Opus 4.6 (session agent)

---

## Verdict

The activation-bias PPL improvement is almost certainly a learned constant offset masquerading as state-dependent transfer. The compressor is empirically collapsed (effective rank ~2 out of 2048), which means the hypernetwork receives near-identical input for every sample, which means it is generating near-identical bias vectors for every sample, which means you have trained a single fixed additive perturbation to Qwen's mid-block attention projections. That this slightly lowers held-out perplexity is unsurprising and tells you nothing about memory transfer, disposition transfer, or cross-architecture bridging. The 0/16 recall across all conditions is the result that actually matters, and it is devastating to the strong interpretation.

---

## Strongest Attacks

### 1. The compressor collapse makes "state-dependent" transfer physically impossible in this run

PC1 captures 76-91% of variance in the compressed context vectors. Effective rank is 1.6-2.5 out of 2048 dimensions. This is not a subtle concern — this is a showstopper. If the input to the hypernetwork is functionally constant across all 64 training samples and all 16 eval samples, then the hypernetwork's output (the generated bias vectors) must also be functionally constant across samples. You are not injecting different information for different facts. You are injecting approximately the same vector every time. The entire causal chain from "Mamba encodes facts" to "Qwen receives fact-specific modulation" is broken at the first link.

### 2. No constant-bias control exists — the most obvious confound is untested

If you take a single learned bias vector of norm ~5.9 and inject it into layers 12-15 q_proj+v_proj for every sample (ignoring Mamba entirely), you would very likely see a comparable PPL improvement. Any additive shift that nudges the residual stream even slightly toward higher-probability token predictions in this narrow synthetic distribution will lower perplexity. Until this control is run and shows a *different* PPL than the activation-bias path, the Mamba-dependent interpretation has zero unique support.

### 3. No random-bias control exists

If you inject random bias vectors of the same L2 norm (~5.9) into the same layers, what happens to PPL? If PPL also drops (even by 1-2 points), the entire result is within the noise envelope of "perturbing a frozen LLM's attention slightly changes its output distribution." Both controls are needed. Neither exists.

### 4. Zero recall is not a neutral result — it is actively disconfirming

The entire point of the architecture is to transfer factual knowledge from Mamba's processed context into Qwen's generation. If, after training, Qwen cannot produce a single correct factual answer that it could not produce before, then the bridge has transferred zero detectable factual content. A PPL drop of ~4 points without any recall lift is consistent with the model becoming slightly more confident in its *wrong* answers or in generic high-frequency tokens surrounding the answer positions.

### 5. The PPL improvement could be answer-length or format bias

If the bias injection causes Qwen to assign slightly more probability mass to common tokens that happen to appear in the answer spans, PPL drops without any factual transfer. This is especially dangerous with only 16 eval samples.

### 6. N=1 run with no variance estimate makes all numerical comparisons meaningless

Three epochs, one random seed, one data split. The PPL difference of 4.04 at epoch 3 has no error bar. With 16 eval samples, the standard error of the mean log-probability could easily be 2-3 points.

### 7. The LoRA comparison is a strawman

Dynamic LoRA diverged (PPL went from 29 to 44 by epoch 2). Comparing activation bias favorably against a mode that clearly exploded is not evidence that activation bias works; it is evidence that LoRA failed. "Better than broken" is not a meaningful bar.

### 8. Bias norm plateau at ~5.9 is suspicious

Combined with the compressor collapse, this strongly suggests the system learned: "always add this specific vector to these layers." If the bias were genuinely adapting to different inputs, you might expect sample-to-sample variance in the norm.

### 9. Cosine similarity between per-sample bias vectors was never measured

This is the single cheapest diagnostic that could instantly kill or support the interpretation. If cos(bias_i, bias_j) ≈ 1.0 for all sample pairs, the "state-dependent" claim is dead on arrival.

---

## What Is Actually Supported

The narrowest defensible claim: **Injecting a trained additive bias of norm ~5.9 into Qwen2.5-7B layers 12-15 (q_proj + v_proj) reduces held-out perplexity by ~4 points on a 16-sample synthetic MUD-domain eval set, relative to no injection, without improving factual recall, in a single run with no variance estimate.**

That is all. There is no evidence that:
- The bias is sample-dependent
- The bias encodes information from Mamba's state
- The improvement reflects any form of "memory" or "disposition" transfer
- The improvement would replicate across seeds, data, or domains
- The improvement exceeds what a constant learned bias (without Mamba) would achieve

---

## What Is Overclaimed

Any framing that includes the words "transfer," "bridging," "Mamba-derived," "state-dependent," or "cross-architecture" in connection with this result is overclaimed. The compressor collapse severs the causal link between Mamba's per-sample state and the injected bias.

Calling this a "PPL improvement" without immediately qualifying it as "indistinguishable from a constant offset" is misleading.

Describing recall = 0/16 as "same as baseline" without flagging it as disconfirming is framing bias. The system was designed to transfer facts. It transferred zero facts. That is a negative result for the core hypothesis.

---

## Minimum Next Controls

### C0. Cosine similarity matrix of per-sample bias vectors (~1 hour, no training)
Compute cos(bias_i, bias_j) for all pairs from the current checkpoint.
- **Kill:** mean cosine > 0.95 → hypernetwork generates constant bias, "state-dependent" is dead.
- **Save:** mean cosine < 0.7 with visible clustering by fact type → compressor retains more structure than PCA suggested.

### C1. Constant-bias control (1 training run)
Train a single learnable bias vector (no Mamba, no compressor, no hypernetwork) of the same dimensionality, injected into the same layers.
- **Kill:** comparable PPL reduction → Mamba pathway is irrelevant.
- **Save:** PPL significantly worse → something from the Mamba pathway contributes.

### C2. Random-bias control (no training needed)
Inject random Gaussian bias vectors with L2 norm = 5.9 into the same layers. Run eval.
- **Kill:** PPL drops by 1-2+ points → magnitude alone is partially responsible.
- **Save:** PPL increases substantially → trained direction matters (though still not proven sample-dependent).

### C3. Fixed-mean-bias control (no training needed)
Take the mean bias vector across all training samples from the current checkpoint. Inject this single fixed vector for all eval samples.
- **Kill:** eval PPL indistinguishable from per-sample path (~25.67) → per-sample variation does nothing.
- **Save:** eval PPL measurably worse → at least some sample-dependent component exists.

### C4. Multi-seed replication (3-5 runs)
Rerun activation-bias training with 3-5 different random seeds. Compute mean and SD of PPL delta at epoch 3.
- **Kill:** 95% CI includes zero → noise.
- **Save:** delta consistently negative across seeds → reproducible effect.

### C5. Fix or ablate the compressor (medium-term)
Either add diversity/contrastive loss or replace compressor output with random orthogonal vectors to test whether the hypernetwork can use distinguishable inputs.

---

## Decision

**"Likely artifact."**

The compressor collapse alone is sufficient to downgrade this. The most parsimonious explanation: the system learned a single constant additive bias that slightly improves Qwen's predictions on this narrow synthetic domain, unrelated to per-sample Mamba state.

**Upgrade conditions (ALL required, not any one):**
1. Cosine similarity analysis shows meaningful per-sample variation (mean cosine < 0.8)
2. Constant-bias control achieves measurably worse PPL than the per-sample path
3. Result replicates across at least 3 seeds
