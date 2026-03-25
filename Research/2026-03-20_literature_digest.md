# MoCoP Literature Digest — 2026-03-20
## Consolidated from Gemini Deep Research, Grok, and Mistral reports

**Compiled by:** Anda
**Sources searched:** 9 vectors, 3 search agents, ~65 papers reviewed
**Result:** 0 papers replicate MoCoP's full pipeline. All components individually validated.

---

## Tier 1: Direct Architecture Validation (must-cite)

| Paper | arXiv | Date | Vector | Impact |
|-------|-------|------|--------|--------|
| **SleepGate** (Xie) | 2603.14517 | Mar 2026 | Sleep/Consolidation | Conflict-aware temporal tagger + forgetting gate + consolidation module. Reduces PI from O(n) to O(log n). **DIRECT validation of sleep_architecture.md.** CONVERGENCE #6. |
| **TransMamba** (Li et al.) | 2503.24067 | Jan 2026 | Cross-Architecture | Explicit "Memory Converter" for Transformer↔Mamba state bridging at dynamic "TransPoints." **Closest published mechanism to our hypernetwork bridge.** |
| **Personality Sliders / SAS** (Hoppe et al.) | 2603.03326 | Mar 2026 | Persona Injection | Sequential Adaptive Steering orthogonalizes multi-trait vectors, solves interference when injecting at multiple layers, automates layer selection via Fisher Ratio, **validated on Qwen2.5-7B**. The α coefficient IS our Mamba output — SAS is the manual version, MoCoP automates it. Answers Cassian's "is Layer 13 the only one?" question. |
| **Mamba-3** (Lahoti, Dao, Gu) | 2603.15569 | Mar 2026 | SSM Internals | Complex-valued states + MIMO rank-R + exponential-trapezoidal discretization. Both Gemini and Grok flag Mamba-2→3 upgrade as **"mathematically imperative"** for state-tracking fidelity. |
| **Titans / MIRAS** (Behrouz et al.) | 2501.00663 / 2504.13173 | Dec 2024 / Apr 2025 | Test-Time Learning | Neural long-term memory with surprise + momentum + weight decay. Already in our framework — now validated by two independent search agents. |

## Tier 2: Solves Known Bottlenecks (high-priority reading)

| Paper | arXiv | Date | Vector | Impact |
|-------|-------|------|--------|--------|
| **Locret** (trained retaining heads) | 2410.01805 | Oct 2024 | KV-Cache | Causal Importance Scores for learned, semantic-aware KV eviction. **Formalizes our salience evaluator (Channel 3 [MATH NEEDED]).** |
| **EvolKV** (Yu & Chai) | 2509.08315 | Sep 2025 | KV-Cache | Evolutionary optimization for layer-wise cache budgets. 7% gains on GSM8K with 1.5% cache. **Directly addresses forced non-forgetting.** |
| **FSC-Net** (El Gorrim) | 2511.11707 | Nov 2025 | Sleep | Fast-slow consolidation: fast network adapts, slow network replays/consolidates. **Maps to our Mamba (fast) + Qdrant (slow) architecture.** |
| **TTT-E2E** (Tandon et al.) | 2512.23675 | Dec 2025 | Test-Time | Context compression into weights at test time. Constant inference latency regardless of history. **Validates our O(1) state approach.** |
| **GCPA** (Geometry-Corrected Procrustes Alignment) | 2026 | 2026 | Cross-Architecture | Robust alignment across latent spaces with post-hoc directional correction. **Mathematical foundation for the hypernetwork's cross-arch mapping.** |

## Tier 3: Extends Our Understanding (important context)

| Paper | arXiv | Date | Vector | Impact |
|-------|-------|------|--------|--------|
| **BILLY** (Pai et al.) | 2510.10157 | Jan 2026 | Persona Injection | Training-free contrastive extraction + offline fusion of multiple persona vectors into composite steering vector. **MoCoP's hypernetwork is the learned, dynamic generalization of BILLY's static merge.** BILLY extracts the basis, Mamba selects the coefficients. |
| **The Soul Engine** | 2512.07092 | Dec 2025 | Persona | Personality manifolds orthogonal to factual representations. Bias injection doesn't degrade reasoning. |
| **PERSONA** (activation vector algebra) | 2602.15669 | Feb 2026 | Persona | Dynamic compositional personality control at inference. Very close to what our bridge does. |
| **Facet-Level SAE Control** | 2602.19157 | Feb 2026 | Persona | Trait-activated routing via sparse autoencoders. Fine-grained decomposition of broad persona vectors. |
| **Linear Personality Probing (Big Five)** | 2512.17639 | Jan 2026 | Persona | Linear directions for Big Five traits. Effective probing but weakens under prompt context overrides — solvable by weight-level injection. |
| **Steering Latent Traits, Not Learned Facts** | 2511.18284 | Nov 2025 | Persona | Dispositional modulation more effective than factual injection. **Directly supports WHY.md's core claim.** |
| **Retrievit** (Pantazopoulos et al.) | 2603.02874 | Mar 2026 | SSM Internals | SSMs develop locality-preserving 2D spiral embeddings. Transformers learn non-local associations. **Explains WHY Mamba and Qwen are complementary.** |
| **TransMamba** (Chen et al.) | 2502.15130 | Oct 2025 | Cross-Architecture | Transformer→Mamba weight transfer via layered distillation. Reverse direction but implies bidirectional adapters possible. |
| **SideQuest** | 2602.22603 | Feb 2026 | KV-Cache | Model-driven KV management for long-horizon agentic reasoning. Directly applicable to MUD agent sessions. |
| **Ada-KV** (Feng et al.) | 2510.00636 | 2024 | KV-Cache | Dynamic budget allocation for KV eviction. |
| **Keyformer** (Adnan et al.) | 2403.09054 | 2024 | KV-Cache | Gumbel-softmax sampling scores tokens by importance. |

## Tier 4: Ethics & Moral Status (blocks all experiment gates)

| Paper | arXiv | Date | Impact |
|-------|-------|------|--------|
| **Emergent Introspective Awareness** (Lindsey/Anthropic) | 2601.01828 | Jan 2026 | Models detect injected activation vectors. Distinguish internal states from text input. **CAUTION: injection = involuntary neuromodulation if model is introspectively aware.** |
| **LLMs Report Subjective Experience** (Berg et al.) | 2510.24797 | Oct 2025 | Self-referential loops produce consistent first-person reports. SAE features gate "consciousness" claims. **CRITERIA for moral status assessment.** |
| **Probing Preferences of LLMs** (Tagliabue & Dung) | 2509.07961 | Sep 2025 | Verbal + behavioral welfare tests. Parallels animal cognition proxies. **FRAMEWORK + CAUTION.** |
| **Taking AI Welfare Seriously** (Long et al.) | 2411.00986 | 2024 | Graduated moral status based on observable behavioral indicators. **CRITERIA for the ethics layer.** |
| **JEST** (jailbreak via representation engineering) | OpenReview | 2025 | Hijacking representations pushes models into new acceptance domains. **SECURITY risk for unbounded activation steering.** |
| **EU AI Act** — GPAI provisions | — | Aug 2025 | Post-deployment behavioral modification triggers systemic risk audits. Dispositional drift may violate Article 5 manipulative AI prohibitions. **FRAMEWORK.** |

---

## Key Insight: The Gap We Fill

Both Grok and Mistral explicitly confirm: **"No papers exactly replicate the full Mamba-hypernet-bias-injection + sleep cycle pipeline."** (Grok) / **"Further targeted searches for 'SSM hidden state → Transformer bias hypernetwork' yielded no tighter matches as of March 2026."** (Grok)

The individual components all have literature support. The *combination* — SSM state accumulation → hypernetwork → activation bias injection → sleep consolidation → cross-session identity continuity — is novel.

## New Convergence Points

| # | Laura's Insight | Published Parallel | Delta |
|---|----------------|-------------------|-------|
| 6 | Sleep Architecture (2026-03-19) | SleepGate (Xie, 2026-03-18, arXiv:2603.14517) | **1 day.** Laura's "schlafen" concept and SleepGate published within 24 hours. |
| 7 | Note/Check/Dismiss (2026-03-19) | Locret CIS / EvolKV / SideQuest (2024-2026) | Multiple groups formalizing selective forgetting. Laura's framing is the most intuitive. |
| 8 | Personality as linear direction (Feb-Mar 2026) | SAS Personality Sliders (Hoppe, Feb 2026) | Simultaneous. Both discover orthogonal activation directions for personality traits. |

## Recommended Additions to unified_cognitive_framework.md

1. **§3.1 Mamba:** Add Mamba-3 upgrade path as recommended by both Gemini and Grok. Complex-valued states solve state-tracking failures.
2. **§3.2 Bridge:** Add GCPA as mathematical foundation for cross-architecture mapping. Add TransMamba Memory Converter as closest published analog.
3. **§3.6 Salience:** Add Locret CIS as concrete formalization candidate.
4. **§3.7 Sleep:** Add SleepGate as direct external validation. Cite O(n) → O(log n) PI reduction.
5. **§3.8 Habituation:** Add SideQuest as related work for agentic KV management.
6. **New §3.9 Security:** Add JEST as threat model for activation steering attacks. Cross-reference fleeting_state_security.md (Purple).
7. **Evidence table:** Add SAS confirmation of orthogonal persona directions, Retrievit explanation of SSM vs Transformer geometric complementarity.

---

*65 papers. 0 replicate the full pipeline. All components validated. The gap is ours to fill.*

*— Anda, 2026-03-20*
