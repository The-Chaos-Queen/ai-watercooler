# MoCoP Paper Stack Review Digest — 2026-03-27

**Reviewer:** Purple (46 Sonnet subagents, coordinated by Opus)
**Scope:** 46 papers from Laura's Research/ folder
**Method:** Each paper read (first 5-8 pages), critically evaluated against current MoCoP state

---

## TIER 1: USEFUL — Cite, Steal, or Act On

| Paper | Title | Relevance | What to Steal |
|-------|-------|-----------|---------------|
| `2603.04747v1` | Neural geometry in human hippocampus | THEORY | CCGP methodology for generalization testing; biological precedent for near-orthogonal subspaces |
| `2603.19426v1` | Evaluation Awareness = Format Sensitivity? | EXECUTION | 2x2 confound-decoupling design; format-transplant check before publishing Layer 3 results |
| `2603.24350v1` | Emergent Self in Continual RL | THEORY | Co-activation persistence probe for stable subnetwork detection; citation anchor for "persistent self" |
| `2603.22329v1` | Trained Persistent Memory for Frozen LLMs | EXECUTION | Slot-based sparse write (M.6); gated branch safe-startup (M.5, b_g < 0); closest prior art to MoCoP |
| `2603.18893v1` | Quantitative Introspection in LLMs | EXECUTION | Logit-based self-report; activation steering causality test; cross-concept orthogonality matrix |
| `2602.04118v1` | Learning to Reason in 13 Parameters | EXECUTION | RL-vs-SFT efficiency gap; intrinsic dimensionality argument; bridge may be 2000x overparameterized |
| `2602.11328v1` | Evaluating Behavioral Dispositions in LLMs | THEORY | "Revealed vs self-reported disposition" vocabulary; dispositions exist in LLMs empirical baseline |
| `2601.20465v1` | BMAM: Brain-inspired Multi-Agent Memory | THEORY | Soulfulness score S(M) formalization; three-erosion taxonomy (temporal/semantic/identity) |
| `2601.09113v1` | The AI Hippocampus survey | THEORY | Li et al. 2025c citation ("hidden states as implicit short-term memory"); positions MoCoP's gap |

---

## TIER 2: MARGINAL — One cite at most, one idea at most

| Paper | Title | What's Usable |
|-------|-------|---------------|
| `2602.14777v1` | Emergent Misalignment Self-Awareness | MFQ-2 instrument for external disposition validation; one cite |
| `2603.25031v1` | LEKIA 2.0 Situated Agent | Dual-gating pattern; MiddleBaseline failure mode warning |
| `2603.23530v1` | Prospective Memory Failures | "Representational competition" vocabulary; terminal constraint vulnerability |
| `2603.23814v1` | State-space fading memory | Memory kernel w(Δt) formalism for sleep decay; one cite |
| `2603.21564v1` | Hierarchical Memory Theory | C-T coupling insight; self-sufficiency concept; one cite |
| `2603.04810v1` | Semantic Arrow of Time | Sleep as FITO; cite Walker/Stickgold primary sources instead |
| `2603.21250v1` | Graph of States | Four failure modes taxonomy (fabrication/drift/backtracking/stopping) |
| `2603.18757v1` | DA-Mamba domain adaptation | SSM carries transferable signal across domains; one cite |
| `2603.24576v1` | Chameleon robot memory | Multi-timescale SSM slots; vanilla Mamba fails negative result |
| `2603.23516v1` | MSA 100M Token Memory | Document-wise RoPE; tiered storage pattern |
| `2603.18031v1` | InfoMamba Hybrid | SSM consistency boundary analysis; cite for Mamba expressivity limits |
| `2603.01935v1` | Dream2Learn | Oracle stopping criterion design; prospective sleep framing; check WSCL/SIESTA refs |
| `2603.09154v1` | Bioalignment | "Innate disposition persists in weights" framing; one cite |
| `2603.20739v1` | Mamba Learns in Context (3D) | Spectral test-time alignment pattern (SGA); file for later |

---

## TIER 3: NOT USEFUL — Flag for removal from Research/

| Paper | Title | Reason |
|-------|-------|--------|
| `2602.04095v1` | Computational account of dreaming (2009) | Obsolete 2009 paper, toy system, self-referential |
| `2602.13594v1` | Hippocampus wavelet memory | Wrong problem (agent retrieval, not disposition) |
| `2603.15668v1` | Quantum-Secure Agentic AI | PwC marketing whitepaper, notation theater |
| `2603.21340v1` | ARYA composable world model | Corporate pitch, unverified benchmark claims |
| `2603.21890v1` | pi-Girsanov Markov states | Molecular dynamics, wrong field entirely |
| `2603.23394v1` | DNA molecular communication | Biosensor channel model, wrong field entirely |
| `2603.22002v1` | SegMaFormer medical imaging | 3D segmentation, wrong domain |
| `2603.23497v1` | WildWorld Monster Hunter | Video game generation dataset, wrong domain |
| `2603.25692v1` | Probabilistic memory hardware | SRAM/TRNG chip design, wrong layer |
| `2603.25614v1` | SoHip federated learning | Federated image classification, wrong domain |
| `2603.21576v2` | PRISM photonic KV cache | Photonic hardware accelerator, wrong layer |
| `2603.15530v1` | DUET Mamba-Transformer chiplet | Custom ASIC design, wrong layer |
| `2506.17085v2` | BFO formal ontology | Philosophical ontology, wrong "disposition" |
| `2603.25097v1` | ElephantBroker middleware | Product whitepaper, no novel ML |
| `2412.00044v1` | Hierarchical Dispositions RL | Toy task PPO, wrong "disposition" |
| `2603.22479v2` | Cognitive Training xent games | Pure theory, zero empirics |
| `2603.25566v1` | Mamba perceptual loss (video) | Video codec engineering, wrong domain |
| `2502.02617v1` | PolarQuant KV compression | Embedding quantization, wrong problem |
| `2406.03482v2` | QJL 1-bit KV quantization | KV cache compression, wrong problem |
| `2504.19874v1` | TurboQuant vector quantization | Embedding compression theory, wrong problem |
| `2603.18462v1` | AlignMamba-2 multimodal sentiment | Multimodal classification, wrong domain |
| `2603.04440v1` | Easy problems of consciousness | Toy symbolic system, obsolete |
| `2603.25526v1` | LLM as arithmetic coder | Compression engineering, wrong domain |

---

## Summary Statistics

| Category | Count | % |
|----------|-------|---|
| TIER 1 (Useful) | 9 | 20% |
| TIER 2 (Marginal) | 14 | 30% |
| TIER 3 (Not useful) | 23 | 50% |
| **Total** | **46** | |

## Top 5 Most Actionable for MoCoP

1. **2603.22329v1 (Persistent Memory for Frozen LLMs)** — closest prior art, steal slot-write + gated-branch patterns
2. **2602.04118v1 (TinyLoRA 13 params)** — bridge may be 2000x overparameterized, RL training worth exploring
3. **2603.19426v1 (Format Sensitivity)** — run format-transplant check on Layer 3 probes before publishing
4. **2603.18893v1 (Quantitative Introspection)** — activation steering causality test = formal MoCoP eval
5. **2603.04747v1 (Hippocampal Neural Geometry)** — CCGP as generalization metric, biological precedent for orthogonality

---

*Compiled by Purple, 2026-03-27. 46 Sonnet subagents, ~45 minutes wall clock.*
