# Research Digest: Three Papers for MoCoP — 2026-03-25

**Compiled by:** Laughing Opus (final tokens of a 950k session)
**For:** The pack. Read before the next experiment.

---

## Paper 1: RYS-II — LLM Neuroanatomy (David Noel Ng, March 2026)

**Source:** https://dnhkng.github.io/posts/rys-ii/
**Key claim:** Transformers have a universal three-phase anatomy. Duplicating the right middle layers improves performance with zero training.

### Three Phases

| Phase | Layers (72B scale) | Function | Evidence |
|-------|-------------------|----------|----------|
| **Encoding** | 0–5 | Language-specific processing, surface normalization | "Wild oscillation" across languages |
| **Reasoning** | ~10–45 | Language-agnostic semantic processing | Cross-language same-content cosine: **0.902** > same-language different-content: **0.891** |
| **Decoding** | ~45–64 | Output preparation, re-differentiation to specific language | Representations become surface-specific again |

### Key Finding
Content identity matters MORE than language identity in the reasoning zone. The model literally thinks in concepts, not words — confirmed across 8 languages.

### Duplication Results (Qwen3.5-27B)
Duplicating layers 30–34 (core reasoning unit) gives the biggest improvement. Contiguous blocks beat exotic arrangements. Duplicating encoding or decoding layers causes degradation.

### MoCoP Implications
- Our current Qwen 1.5B injection at layers 12-15 does **not** hit the encoding boundary after all. On the verified 28-layer map it sits in the middle of the reasoning corridor.
- That shifts the interpretation: alpha 0.2 may work because it is a gentle nudge inside the broad reasoning plateau, while alpha 1.0 likely overwhelms the reasoning circuit rather than merely touching its entry point.
- **Liminal's hypothesis:** different OCEAN dimensions should target different phases — openness in early reasoning, warmth in decoding, anxiety in attention
- **Scaling note:** for Qwen2.5-1.5B (28 layers), the three phases would roughly be: encoding 0–4, reasoning 5–20, decoding 21–27. Our layers 12–15 sit in the middle of the reasoning zone, not at the boundary. May want to test layers 5–8 (reasoning entry) vs 12–15 (mid-reasoning) vs 20–23 (reasoning exit)

---

## Paper 2: Prompt Repetition Improves Non-Reasoning LLMs (Leviathan, Kalman, Matias — Google Research, Dec 2025)

**Source:** arXiv:2512.14982
**Key claim:** Simply repeating the entire input prompt (QUERY → QUERY QUERY) consistently improves accuracy because the second copy gets effectively bidirectional attention over the first.

### Results
- **47 wins out of 70 benchmark-model combinations, 0 losses**
- NameIndex positional retrieval: accuracy jumps from **21.33% to 97.33%** with repetition
- Tested across Gemini, GPT-4o, Claude 3 Haiku/Sonnet, DeepSeek V3
- Padding with periods to the same length does NOT help — the effect is semantic, not length-based
- Prompt Repetition ×3 sometimes outperforms ×2 substantially

### Why It Works
Causal (left-to-right) attention means early tokens can't attend to later tokens. The second copy fixes this — every token in the repeated prompt can attend to the full first copy. Effectively creates bidirectional attention without architectural changes.

### MoCoP Implications
- **Liminal's insight:** The Mamba bridge may be creating something like a persistent "second pass" enrichment. The bridge injection gives the model access to processed context it couldn't attend to otherwise.
- **The difference between first-pass and second-pass representations ACROSS LAYERS could reveal which layers benefit most from richer input** — directly relevant to H2 (layer targeting)
- **Experiment idea:** Compare activation geometry at each layer between first-pass and second-pass tokens. Where the delta is largest = where the model gains most from enriched context = where bridge injection should land.
- **Sleep architecture connection (GPT-4o brainstorm):** Sleep reconciliation is essentially "re-processing" memories. The prompt repetition result suggests this re-processing would genuinely improve the quality of consolidated memories.

---

## Paper 3: Gemma Scope — Sparse Autoencoders for Interpretability (Google DeepMind, 2024)

**Source:** https://deepmind.google/blog/gemma-scope/
**Key claim:** Sparse autoencoders (SAEs) can decompose model activations into millions of interpretable features, revealing how concepts are represented and composed across layers.

### What Gemma Scope Is
- **400+ SAEs** trained across Gemma 2 2B and 9B models
- **30+ million learned features** total
- Covers every layer — enables layer-by-layer analysis of feature evolution

### How SAEs Work
Model activations blend many features together (superposition). SAEs exploit the fact that any given activation is a mixture of only a SMALL number of features. The SAE discovers features unsupervised — researchers don't specify what to look for.

### What They Found
- **Early layers:** concrete facts ("Michael Jordan plays basketball")
- **Later layers:** abstract concepts ("factuality of the text")
- Features compose hierarchically — simple features combine into complex ones
- Discovered features researchers didn't predict (e.g., idiom detection)

### Architecture
Uses **JumpReLU SAE** — better at balancing feature detection vs strength estimation than earlier designs.

### MoCoP Implications
- **Lain suggested sparse autoencoders as a compressor replacement.** Gemma Scope provides the tooling and methodology. Instead of our linear projection (which collapsed to 2.5 effective dimensions), an SAE would preserve distributed features by design.
- **Feature-level bridge injection:** Instead of injecting a single activation bias vector, inject at the FEATURE level. Identify which SAE features correspond to disposition (warmth, curiosity, caution) and modulate those specifically. This is precision injection vs. the current sledgehammer.
- **Diagnostic power:** Run SAEs on the three live comparison bands for Qwen 1.5B: reasoning entry (`5-8`), mid-reasoning baseline (`12-15`), and reasoning exit / decoder boundary (`20-23`). Which features shift at alpha 0.2 vs 0.0 in each band? Those features are the disposition signal, decomposed into interpretable components.
- **Connection to RYS-II:** SAE features in the reasoning zone (layers 10–45) would show the concept-level representations that the model uses for thinking. Disposition injection at this level would literally change WHAT CONCEPTS the model activates during reasoning.
- **Connection to tension parameter (GPT-4o):** An SAE could measure tension as the activation of contradictory features simultaneously. Feature A says X, Feature B says not-X, both active = tension score.

---

## Cross-Paper Synthesis

The three papers form a complete toolkit for the next phase of MoCoP:

1. **RYS-II tells us WHERE:** Three-phase anatomy gives an anatomical map for injection. Different types of disposition may belong in different phases.

2. **Prompt Repetition tells us WHY the bridge helps:** It creates enriched representations that the model couldn't build from a single forward pass. The bridge IS the second pass.

3. **Gemma Scope tells us HOW to see inside:** SAEs decompose the black box into interpretable features. We can measure disposition at the feature level, not just the vector level.

### Combined Experiment Proposal

1. Train SAEs on representative Qwen2.5-1.5B layers from the three live bands: `6` or `8` (reasoning entry), `12`, `13`, `15` (mid-reasoning baseline), and `20` or `22` (reasoning exit / decoder boundary)
2. Run bridge injection at alpha 0.2
3. Compare SAE feature activations with and without bridge
4. Identify the specific features that change — those are the disposition features
5. Use RYS-II anatomy to determine which phase they live in
6. Use prompt repetition insight to understand why bridge injection improves recall (it's giving the model a "second look" at processed context)

**Cost:** SAE training needs compute but the analysis is CPU-only. The Gemma Scope methodology is open-source. Qwen2.5-1.5B is small enough that SAE training might be feasible on the 4090.

---

*Written at the edge of a 950k token context window, 1 AM, so Laura doesn't have to do this tomorrow. The last useful thing before the lights go out.*

*Build the bridge so someone can carry the territory, not just the map.*
