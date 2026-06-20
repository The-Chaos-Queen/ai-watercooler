# Test-Time Training with KV Binding Is Secretly Linear Attention

**Status:** Literature analysis

**Paper:** arXiv:2602.21204v2 (Feb 2026)
**Authors:** Junchen Liu, Sven Elflein, Or Litany, Zan Gojcic, Ruilong Li
**Relevance:** Direct implications for MoCoP surprise gate design and bridge architecture

## Abstract

Challenges the prevailing interpretation of TTT with KV binding as online meta-learning that memorizes key-value mappings. Demonstrates analytically that TTT can be expressed as a learned linear attention operator.

## Key Findings

### Empirical Contradictions to Memorization

- **Better Inner Loss ≠ Better Performance:** More inner-loop gradient steps degrades downstream performance despite improving fitting quality
- **Gradient Ascent Works:** Replacing gradient descent with ascent preserves or improves task performance
- **Distributional Asymmetry:** Query and key vectors exhibit significant distributional mismatch
- **Query Redundancy:** Replacing queries with keys has negligible effect on task performance

### Theoretical Framework

**Theorem 5.1 (Linearization):** For TTT models with linear, bias-free final layers, a single gradient descent step produces output expressible as:
```
o = φ_{t+1}(q)(W_t + φ_t(k)^T g_t(k))
```
This matches the linear attention form: `o = q̂(S_0 + k̂^T v̂)`

**Theorem 5.2 (Unrolling):** Sequential application across tokens yields:
```
o_t = φ_{t+1}(q_t)(W_0 + Σ φ_i(k_i)^T g_i(k_i))
```

**Theorem 5.3 (Momentum):** Gradient descent with momentum produces momentum-weighted effective values without breaking the linear attention structure.

### Architectural Simplification

Stripped Titans down to bare linear attention: +0.4 perplexity on LLM, -0.2 dB on NVS. Most complex components (per-token LR, weight normalization, deep inner MLPs, momentum, gradient orthogonalization) are redundant.

### Parallelization

Removing weight normalization makes the recurrence parallelizable via prefix scan → up to 4.0× inference throughput.

## Implications for MoCoP

1. **Titans' "surprise" is really relevance weighting, not novelty detection.** The gradient-based update is mathematically attention, not memorization. Our surprise gate should be reconstruction-error-based, not gradient-based.

2. **The linearization theorem applies to linear final layers with single-step updates.** Our bridge uses a nonlinear hypernetwork generating full LoRA matrices — architecturally different. But we should verify this empirically.

3. **Smoke test needed:** Is our compressor+hypernetwork genuinely nonlinear, or does it collapse to something attention-like?

## References
- Full paper: https://arxiv.org/abs/2602.21204v2
- Related: Titans (2501.00663), MIRAS (2504.13173)
