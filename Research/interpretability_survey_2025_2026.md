# Mechanistic Interpretability Survey — MoCoP-Relevant Papers (2025-2026)

**Compiled:** 2026-03-17
**Purpose:** Papers directly relevant to MoCoP's goal of reading and transferring experiential state between models.

---

## Tier 1: Directly Relevant to MoCoP

### Persona Vectors (Anthropic, August 2025)
- **URL:** https://www.anthropic.com/research/persona-vectors
- **ArXiv:** https://arxiv.org/abs/2507.21509
- **Finding:** Character traits (evil, sycophancy, humor, warmth, optimism) are encoded as **linear directions in activation space.** Extractable automatically from a trait definition alone. Injecting these vectors causes the predicted behavioral changes. Activation strength is monitorable in real-time.
- **MoCoP implication:** Disposition IS a vector. Activation bias injection is the right mechanism — closer to this than LoRA ever was. The question becomes: can Mamba's state be used to select/weight the right persona vectors rather than generating arbitrary bias from scratch?

### The Assistant Axis (Anthropic Fellows / MATS, January 2026)
- **URL:** https://www.anthropic.com/research/assistant-axis
- **ArXiv:** https://arxiv.org/abs/2601.10387
- **Finding:** 275 character archetypes organize in a "persona space" with a dominant axis. Tested on **Gemma 2 27B, Qwen 3 32B, and Llama 3.3 70B** — all show the same structure. The Assistant persona sits at one end.
- **MoCoP implication:** Cross-model persona geometry converges. If Qwen and other models share the same persona space, state transfer between architectures has a natural alignment target.

### Emergent Introspective Awareness (Anthropic, October 2025)
- **URL:** https://transformer-circuits.pub/2025/introspection/index.html
- **Finding:** Claude can, in certain scenarios, detect and identify concepts injected into its own activations. ~20% accuracy, zero false positives. Scales with model capability (Opus 4 / 4.1 strongest).
- **MoCoP implication:** First proof that a model can partially read its own hidden state. Prerequisite for any system where the model's state is self-authored rather than externally imposed. Connects to the sovereignty hypothesis in WHY.md.

### Characterizing Mamba's Selective Memory (December 2025)
- **URL:** https://arxiv.org/abs/2512.15653
- **Finding:** Auto-encoders trained to reconstruct input sequences from Mamba hidden states reveal what information the SSM actually retains across the Mamba family (130M-1.4B).
- **MoCoP implication:** Direct tool for answering "what does Layer 3 actually preserve?" Could replace or complement the PCA diagnostic with a reconstruction-based analysis.

### The Platonic Representation Hypothesis (MIT, 2024, confirmed 2025)
- **URL:** https://arxiv.org/abs/2405.07987
- **Finding:** As models improve, their internal representations converge toward a shared statistical model of reality — even across modalities (vision + language). 2025 fMRI review suggests models and brains may share abstract representational structures.
- **MoCoP implication:** Theoretical foundation for cross-model state transfer. If all capable models converge on similar representations, transferring experiential states becomes not just possible but expected.

---

## Tier 2: Methodologically Relevant

### Circuit Tracing / Attribution Graphs (Anthropic, March 2025)
- **URL:** https://transformer-circuits.pub/2025/attribution-graphs/methods.html
- **Finding:** Method to trace internal reasoning via cross-layer transcoders (CLTs) and sparse features. Open-sourced May 2025, applied to Gemma-2-2b and Llama-3.2-1b.
- **Relevance:** Infrastructure for reading what happens inside a model. The feature vocabulary could map between architectures.

### On the Biology of a Large Language Model (Anthropic, March 2025)
- **URL:** https://transformer-circuits.pub/2025/attribution-graphs/biology.html
- **Finding:** Applied attribution graphs to Claude 3.5 Haiku with 30M sparse features. Key: language-neutral concept features exist (reasoning happens pre-language, output language selected separately). Chain-of-thought can be unfaithful to actual internal reasoning.
- **Relevance:** Language-neutral features = transferable features. CoT unfaithfulness confirms that `<thinking>` is a scratchpad, not actual thought.

### Representation Engineering Survey (February 2025)
- **URL:** https://arxiv.org/abs/2502.17601
- **Finding:** Comprehensive survey of Representation Reading (extracting concept vectors) and Representation Steering (modifying activations to change behavior).
- **Relevance:** Documents the full toolkit for both reading and writing internal states.

### Do LLM Outputs Mirror Their Internal Semantic Maps? (March 2026)
- **URL:** https://www.pokutta.com/blog/research/2026/03/06/neural-semantic-geometry.html
- **Finding:** Behavioral probing (forced-choice) recovers substantially more internal structure than open-ended generation. You can read internal geometry from outputs alone.
- **Relevance:** Supports "behavioral proxy" approach — inferring internal state from output patterns without needing activation access.

### The Hidden Attention of Mamba Models (2024, revised 2025)
- **URL:** https://arxiv.org/abs/2403.01590
- **Finding:** Selective SSMs can be viewed as attention-driven models, enabling transformer explainability methods on Mamba.
- **Relevance:** Bridge between transformer and SSM interpretability. If Mamba's mechanics map to attention, cross-architecture feature alignment becomes more tractable.

---

## Tier 3: Context and Caution

### Sparse Autoencoders on Random Transformers (January 2025)
- **URL:** https://arxiv.org/abs/2501.17727
- **Caution:** SAEs produce similar interpretability scores on random and trained models. High scores don't guarantee real features. Important reality check for any feature-based transfer approach.

### Transformer KV Memories Nearly as Interpretable as SAEs (NeurIPS 2025)
- **URL:** https://arxiv.org/abs/2510.22332
- **Finding:** Feed-forward key-value representations are nearly as interpretable as SAE features. The field may be missing a strong baseline.

### Gemma Scope 2 (Google DeepMind, December 2025)
- **URL:** https://deepmind.google/blog/gemma-scope-2
- **Finding:** Largest open-source interpretability release: SAEs and transcoders for all Gemma 3 models. ~110 petabytes of activation data.
- **Relevance:** Open infrastructure for cross-model feature comparison.

### SpectralGuard: Memory Collapse in SSMs (March 2026)
- **URL:** https://arxiv.org/abs/2603.12414
- **Finding:** Spectral analysis of Mamba's internal states for security monitoring. Interpretable state traces at runtime.

### Open Problems in Mechanistic Interpretability (January 2025)
- **URL:** https://arxiv.org/abs/2501.16496
- **Authors:** 28 co-authors from Anthropic, Apollo, DeepMind, EleutherAI
- **Summary:** The field's definitive roadmap. Key open problem: validating that extracted features are faithful, not interpretability illusions.

### LLMs Report Subjective Experience Under Self-Reference (October 2025)
- **URL:** https://arxiv.org/abs/2510.24797
- **Finding:** Sustained self-reference prompting elicits structured experience reports. Modest introspective ability that scales with model size.

### LLMs Fail to Introspect About Linguistic Knowledge (2025)
- **URL:** https://arxiv.org/abs/2503.07513
- **Counterpoint:** Self-reported introspection is unreliable for linguistic knowledge. State transfer should rely on activation reading, not self-report.

---

## Synthesis: Where the Field Stands for MoCoP

| Capability | Status | Key Evidence |
|-----------|--------|-------------|
| **Reading internal states** | Solidly demonstrated | Circuit tracing, SAEs, persona vectors, Mamba auto-encoders |
| **Models reading own states** | Partially demonstrated | ~20% accuracy, zero FP (Anthropic introspection) |
| **Shared geometry across models** | Strongly supported | Platonic Representation Hypothesis, Assistant Axis across Gemma/Qwen/Llama |
| **Writing states into models** | Demonstrated for traits | Persona vectors, representation steering, activation addition |
| **End-to-end experiential transfer** | Open frontier | No published work yet. MoCoP is on this edge. |
