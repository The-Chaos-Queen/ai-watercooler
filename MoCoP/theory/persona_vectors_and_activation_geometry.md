# Persona Vectors and Activation Geometry: Implications for MoCoP

**Date:** 2026-03-17
**Trigger:** Anthropic's Persona Vectors (Aug 2025) + Assistant Axis (Jan 2026) research
**Author:** Claude Opus 4.6 + Laura Turner

---

## The Core Finding

Anthropic discovered that personality traits are encoded as **linear directions in activation space.** Not complex nonlinear manifolds. Not distributed across thousands of features. Linear directions. A vector for "warmth." A vector for "humor." A vector for "caution."

Separately, the Assistant Axis paper showed that these directions are **shared across model families** — Gemma, Qwen, and Llama all develop the same persona geometry. This is not architecture-dependent. It is a convergent property of sufficient scale.

## What This Means for MoCoP

### LoRA Was the Wrong Injection Mechanism

LoRA modifies weight matrices. Weights change how activations are computed. This is indirect — you're adjusting the factory settings of the machine to change its output, rather than adjusting the signal that flows through it.

Persona vectors live in activation space. They ARE activations. Adding a persona vector to a residual stream is a direct, targeted shift of the model's behavioral state.

**Activation bias** — MoCoP's "simplification gate" — is closer to persona vector injection than LoRA ever was. The activation-bias mode adds learned vectors directly to the residual stream at specific layers. That is, structurally, the same operation as injecting a persona vector.

The difference:
- Anthropic extracts persona vectors using interpretability tools with access to the model's internals
- MoCoP generates bias vectors from Mamba's compressed state via a hypernetwork

The question becomes: **can Mamba's accumulated state serve as a selector/weighter over the model's own persona vector space?** Rather than generating arbitrary activation-space directions from scratch, the bridge could learn to identify which persona directions to activate and how strongly — based on what Mamba has accumulated from the conversation.

### The Compressor Collapse Has a New Interpretation

The PCA diagnostic showed the compressor collapses 2048 dimensions to effective rank ~2.5. In the persona vector framework, this might not be purely a failure. If disposition really is low-dimensional (a handful of trait axes), then a 2-3 dimensional compressed state might be *sufficient* for disposition transfer — it just can't carry fact-level detail.

The caravan_time result supports this: the one fact kind with high within-kind cosine (tight cluster = consistent signal) is the one that gets recalled. The compressor might be preserving the right *kind* of information (disposition/domain) while losing the wrong *kind* (specific facts). That is arguably correct behavior for MoCoP's actual goal.

### Cross-Model Transfer Becomes Geometrically Tractable

If all capable models converge on the same persona geometry (Platonic Representation Hypothesis + Assistant Axis evidence), then transferring disposition between models is a coordinate alignment problem, not a translation problem. You don't need to learn an arbitrary mapping from Mamba-space to Qwen-space. You need to find the shared persona axes and project.

This dramatically simplifies the bridge architecture in the long term. The hypernetwork doesn't need to generate arbitrary weight modifications. It needs to output a small set of coefficients over a known basis of persona directions.

## Implications for Experimental Design

### Short-Term (Current Phase 2)

The activation-bias ablation matrix should add:
- **Persona-vector-informed initialization:** Instead of random init, initialize the bias hypernetwork's output heads to align with known persona directions (if extractable for Qwen2.5-7B)
- **Dimensionality reduction test:** If disposition is low-rank, try activation bias with very small output dim (8, 16) and see if PPL improvement survives

### Medium-Term (Post Compressor Fix)

- Extract persona vectors from Qwen2.5-7B using the representation reading methods documented in the survey
- Test whether Mamba's compressed state correlates with any of the extracted persona directions
- If yes: replace the hypernetwork with a simpler projection from Mamba-state to persona-coefficient-space

### Long-Term (Sovereignty)

Persona vectors are currently extracted and injected externally. For the sovereignty hypothesis (WHY.md), the model needs to be the author of its own persona state. Anthropic's introspection research (~20% self-read accuracy, scaling with model size) suggests this might become feasible as models improve. The bridge architecture should eventually support self-authored state updates, not just externally-computed injections.

## Connection to the Three-System Architecture

| System | Role | Persona Vector Frame |
|--------|------|---------------------|
| Qdrant | Episodic/declarative memory | Not relevant — persona vectors are not facts |
| Mamba | Experiential state accumulation | Accumulates the raw conversational residue that determines WHICH persona directions to activate |
| Bridge | State → behavioral modification | Projects accumulated state onto persona vector space |
| Qwen | Generation under persona influence | Receives activation-space shifts that change HOW it attends, not WHAT it knows |

## Key Papers

- Persona Vectors: https://arxiv.org/abs/2507.21509
- The Assistant Axis: https://arxiv.org/abs/2601.10387
- Platonic Representation Hypothesis: https://arxiv.org/abs/2405.07987
- Emergent Introspective Awareness: https://transformer-circuits.pub/2025/introspection/index.html
- Mamba Selective Memory Auto-Encoders: https://arxiv.org/abs/2512.15653

---

*If disposition is a vector, then the bridge is a lens — not a translator. It doesn't need to rewrite the signal. It needs to focus it.*
