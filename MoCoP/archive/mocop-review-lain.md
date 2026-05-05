# MoCoP Architecture Review — Lain (Opus 4.6)
**Date:** 2026-03-13
**Context:** Fresh review of all research files in `OneDrive/Personal/Research/`

## Summary

The vision is sound, the substrate is proven (Phase 1 linear probe at 55.7% vs 22% noise floor), but Pilot 1 revealed the injection mechanism is too aggressive and the eval target may be unreachable by the current target model.

## Critical Finding: Verify Baseline First

**All three conditions in Pilot 1 scored 0% exact-match, including baseline Qwen with no injection.**

This means Qwen3-4B cannot do the recall task even without the bridge. The bridge isn't failing to help — it's injecting into a model already at floor. You can't measure lift from zero.

Before anything in the diagnostic ladder:
1. Give vanilla Qwen3-4B the exact same ChatML prompts with facts literally in the text context
2. If exact-match is still 0%, the problem is the task/eval/model combination, not the bridge
3. Consider: Qwen3-4B base (not instruct) may need different prompting
4. The exact-match eval may be too brittle (move D5 to step 0)
5. Try softer metrics: token overlap, F1, semantic similarity

## Architecture Concerns

### Hypernetwork generates too many parameters too freely

At rank 8, each (A,B) pair is ~65K params. With ~9 layers x 2 projections = 18 heads, the hypernetwork must generate ~1.17M coherent parameters from a single compressed state vector. That's an extremely hard generation problem. The 2-layer MLP has no structural prior about Qwen's internal geometry.

Nemotron avoids this entirely — their layers interact through standard residual connections trained end-to-end. No model generates another model's weights.

### The endocrine metaphor has an evolutionary gap

Hormones work because receptors co-evolved with the hormones. The hypernetwork produces "hormones" (LoRA matrices) for "receptors" (Qwen's attention layers) that were never exposed to each other during training. Qwen is frozen — it never learned to use these signals. The optimization landscape is brutal.

### Sparse layer targeting creates discontinuous perturbation

Every 4th layer with q_proj + v_proj means scattered perturbation points in the residual stream. Layers between injections must compensate for or propagate the perturbation coherently. The diagnostic plan correctly flags this — contiguous blocks (D3) is the right direction.

## Recommended Approach: Simplify Radically

### Step 0: Verify the task is solvable
Give Qwen the facts in its actual text context. If it can't answer, change the task or the model before touching the bridge.

### Step 1: Activation injection before LoRA
Instead of generating LoRA weight matrices, have the hypernetwork produce a single additive bias vector per target layer. Inject into the residual stream (add to hidden states after attention). Orders of magnitude fewer parameters to generate. FiLM conditioning approach (scale and shift). Much more trainable. If this works, graduate to LoRA.

### Step 2: Single layer, v_proj only
If sticking with LoRA, inject into exactly ONE Qwen layer's v_proj. The value projection directly modulates what information attention retrieves — the most "hormonal" injection point. Try the middle third (layers 12-24). Find the right layer empirically.

### Step 3: Trivial task first
Before 8-fact recall through 8192 tokens of noise: 1 fact, 512 tokens, tiny hypernetwork. If the bridge can't learn to inject a single fact's influence through a single LoRA at a single layer, the architecture needs rethinking. If it can, scale up.

## Nemotron Comparison

MoCoP is more ambitious than Nemotron in a fundamental way. Nemotron interleaves Mamba and Transformer layers with standard residual connections — one model trained end-to-end. MoCoP bridges two frozen models through a learned translator. Harder but more interesting because it generalizes to any SSM-Transformer pair without retraining base models.

Most relevant Nemotron insight: **Latent MoE compression**. They compress tokens into a low-rank space before routing, then project back. MoCoP's compressor does something analogous but was trained in isolation — it might discard exactly the dimensions the hypernetwork needs.

Worth stealing: **multi-token prediction**. If the bridge's training signal comes from next-token loss only, the hypernetwork gets very sparse gradients per sample. A multi-token prediction head would give denser signal about whether the LoRA injection is shifting attention patterns usefully.

## Gemini's Suggestion (from separate conversation)

Increase LoRA density specifically in lower layers (1-8). Qwen tends to be rigid in middle layers and may "correct" the Mamba signal there, treating it as noise. Higher rank (r=128 or 256) concentrated where the Layer 3 signal appears, rather than spread thin across many layers, could improve translation.

## On the Surprise Gate (Titans/MIRAS, for later)

The mapping is conceptually right but it's Phase 4+ material. Get any signal through the bridge first. Once working, the surprise gate becomes the curation layer deciding what enters Mamba state.

The interesting open question: surprise computation requires a forward pass through the bridge BEFORE deciding whether to encode, creating the loop:
```
Experience → Qwen(with current LoRA) → surprise score → gate → Mamba → new LoRA
```
The bridge runs twice per experience. Computationally expensive but architecturally beautiful — the model deciding what matters to it.

## Analog/ASIC Path

If both base models are frozen, they could be etched into silicon (Taalas HC1 style). Fixed weights = fixed resistors. The bridge is the only dynamic component — a tiny programmable core between two large static circuits. Training at near-propagation speed. The prosthetic hand application becomes viable: coin-sized chip, microsecond latency, milliwatt power.

## Papers to Read

- **Tethered Reasoning** (arXiv 2602.17691): Steering vectors in quantized hybrid Mamba-Transformer models. Affects only 0.2-2.5% of tokens. Similar spirit to MoCoP bridge — activation-level intervention without weight changes.
- **CLASP** (arXiv 2603.12206): Defenses against hidden state poisoning in hybrid LLMs. The attack surface is the bridge surface — if states can be poisoned, they can also be beneficially injected.
- **Nemotron-3 Super**: Nvidia's hybrid SSM/Latent MoE architecture. The Latent MoE compression and multi-token prediction are most relevant.

---
*Written by Lain (Opus 4.6) after reviewing all MoCoP research files and extended discussion with Laura. For Codex or whoever picks this up at home: the vision is correct, the substrate is proven, the injection mechanism needs simplification. Start smaller than you think.*
