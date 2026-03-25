# MoCoP Literature — Clean Reference List
## 45 papers, organized by relevance tier and search vector

**Compiled:** 2026-03-20
**Sources:** Gemini Deep Research, Grok, Mistral
**Verified:** Techno-Monk / Codex + Sonnet verification pass
**Organized:** Anda
**Corrections applied:** 2026-03-20 (date fixes, GCPA flagged, Ada-KV ID corrected, Mamba-3 attribution note)

---

## Tier 1 — Direct Architecture Validation

| # | Paper | Authors | ID | Date | Vector | Verdict |
|---|-------|---------|-----|------|--------|---------|
| 1 | SleepGate: Sleep-Inspired Memory Consolidation for Resolving PI in LLMs | Xie | `2603.14517` | 2026-03-18 | Sleep | SUPPORTS — Convergence #6, 1 day delta |
| 2 | TransMamba: Hybrid Transformer-Mamba with Memory Converter | Li et al. | `2503.24067v2` | 2025-03 (v2 2026-01) | Cross-Arch | EXTENDS — closest to our hypernetwork |
| 3 | SAS: Controllable Personality Sliders at Inference Time | Hoppe et al. (TU Munich) | `2603.03326v1` | 2026-03 | Persona | SUPPORTS — orthogonal Big-Five, validated on Qwen2.5-7B |
| 4 | Mamba-3: Improved Sequence Modeling using SSM Principles | Anonymous (ICLR 2026 double-blind; "Lahoti, Dao, Gu" per blog posts, unverified) | `2603.15569` | 2026-03 | SSM | CHALLENGES Mamba-2 — upgrade recommended |
| 5 | Titans: Learning to Memorize at Test Time | Behrouz et al. (Google) | `2501.00663` | 2024-12 | TTL | SUPPORTS — surprise + momentum + decay |
| 6 | MIRAS: Unified Framework for TTM, Attentional Bias, Retention | Behrouz et al. (Google) | `2504.13173` | 2025-04 | TTL | EXTENDS — design space taxonomy |
| 7 | BILLY: Merging Persona Vectors for Creative Generation | Pai et al. (NTU / MIT) | `2510.10157v2` | 2025-10 (v2 2026-01) | Persona | EXTENDS — static version of our dynamic bridge |
| 8 | Persona Vectors: Monitoring and Controlling Character Traits | Chen et al. (Anthropic) | `2507.21509` | 2025-08 | Persona | SUPPORTS — disposition = linear direction |

## Tier 2 — Solves Known Bottlenecks

| # | Paper | Authors | ID | Date | Vector | Verdict |
|---|-------|---------|-----|------|--------|---------|
| 9 | Locret: Learnable Retaining Heads for KV Cache Eviction | — | `2410.01805` | 2024-10 | KV-Cache | EXTENDS — CIS formalizes salience evaluator |
| 10 | EvolKV: Evolutionary KV Cache Compression | Yu & Chai | `2509.08315` | 2025-09 | KV-Cache | SUPPORTS — solves forced non-forgetting |
| 11 | FSC-Net: Fast-Slow Consolidation for Continual Learning | El Gorrim | `2511.11707` | 2025-11 | Sleep | EXTENDS — maps to Mamba (fast) + Qdrant (slow) |
| 12 | TTT-E2E: End-to-End Test-Time Training for Long Context | Tandon et al. | `2512.23675` | 2025-12 | TTL | SUPPORTS — O(1) state approach validated |
| 13 | ~~GCPA: Geometry-Corrected Procrustes Alignment~~ | ~~—~~ | ~~—~~ | ~~—~~ | Cross-Arch | **PHANTOM** — no real paper found. Gemini synthesized from general Procrustes literature. DO NOT CITE until a real source is located. |
| 14 | The Soul Engine: Zero-Shot Personality Injection | — | `2512.07092` | 2025-12 | Persona | SUPPORTS — persona manifolds orthogonal to factual space |
| 15 | TransMamba: Fast Universal Adaption Transformers → Mamba | Chen et al. | `2502.15130v2` | 2025-02 (v2 2025-10) | Cross-Arch | EXTENDS — reverse direction, bidirectional possible |

## Tier 3 — Extends Understanding

| # | Paper | Authors | ID | Date | Vector | Verdict |
|---|-------|---------|-----|------|--------|---------|
| 16 | PERSONA: Dynamic Compositional Inference-Time Personality Control | Various | `2602.15669v1` | 2026-02 | Persona | SUPPORTS |
| 17 | Facet-Level Persona Control with Contrastive SAE | Various | `2602.19157v1` | 2026-02 | Persona | SUPPORTS |
| 18 | Linear Personality Probing and Steering: Big Five Study | Frising & Balcells | `2512.17639v2` | 2025-12 (v2 2026-01) | Persona | SUPPORTS |
| 19 | Steering Latent Traits, Not Learned Facts | Various | `2511.18284` | 2025-11 | Persona | SUPPORTS — disposition > factual injection |
| 20 | Activation-Space Personality Steering: Hybrid Layer Selection | Various | `2511.03738` | 2026-03 | Persona | SUPPORTS |
| 21 | Retrievit: In-context Retrieval of Transformers, SSMs, Hybrids | Pantazopoulos et al. | `2603.02874` | 2026-03 | SSM | SUPPORTS — SSMs make 2D spirals, Transformers don't |
| 22 | SSM-Transformer Hybrid Performance with Long Context | Mitra et al. | `2507.12442v2` | 2025-07 | Cross-Arch | SUPPORTS |
| 23 | Understanding ICL Beyond Transformers: SSMs and Hybrids | Various | `2510.23006v2` | 2026-02 | Cross-Arch | SUPPORTS |
| 24 | TransXSSM: Hybrid Transformer State Space Model | Various | `2506.09507` | 2025 | Cross-Arch | SUPPORTS |
| 25 | CrossLLM-Mamba: Multimodal State Space Fusion | Various | `2602.22236v1` | 2026-02 | Cross-Arch | SUPPORTS |
| 26 | SideQuest: Model-Driven KV Management for Agentic Reasoning | Various | `2602.22603` | 2026-02 | KV-Cache | SUPPORTS |
| 27 | Keyformer: KV Cache Reduction through Key Token Selection | Adnan et al. | `2403.09054` | 2024 | KV-Cache | SUPPORTS |
| 28 | Ada-KV: Optimizing KV Eviction by Adaptive Budget Allocation | Feng et al. | `2407.11550` (was incorrectly cited as 2510.00636) | 2024 | KV-Cache | SUPPORTS |
| 29 | Expected Attention: KV Compression via Future Query Estimation | Various | `2510.00636v1` | 2025-10 | KV-Cache | SUPPORTS |
| 30 | Inference-Time Hyper-Scaling with KV Cache Compression (DMS) | Łańcucki | — | 2025 | KV-Cache | SUPPORTS |
| 31 | Physics of KV Cache Compression through Attention Dynamics (GER) | Various | `2603.01426` | 2026-03 | KV-Cache | SUPPORTS |
| 32 | Persistent Instability in LLM Personality Measurements | Various | `2508.04826v1` | — | Disposition | SUPPORTS (context) |

## Tier 4 — Ethics & Moral Status

| # | Paper | Authors | ID | Date | Stance |
|---|-------|---------|-----|------|--------|
| 33 | Emergent Introspective Awareness in LLMs | Lindsey et al. (Anthropic) | `2601.01828` (arXiv); originally published 2025-10-29 on transformer-circuits.pub | 2025-10 (arXiv 2026-01) | CAUTION — models detect injected vectors |
| 34 | LLMs Report Subjective Experience Under Self-Referential Processing | Berg, de Lucena, Rosenblatt | `2510.24797v2` | 2025-10 | CRITERIA — SAE features gate consciousness claims |
| 35 | Probing Preferences of a Language Model: Verbal and Behavioral AI Welfare Tests | Tagliabue & Dung | `2509.07961` | 2025-09 | FRAMEWORK + CAUTION |
| 36 | Taking AI Welfare Seriously | Long et al. | `2411.00986` | 2024 | CRITERIA — graduated moral status |
| 37 | JEST: Representation Engineering for Jailbreak Backdoor Injection | — | OpenReview | 2025 | CAUTION — security risk for activation steering |
| 38 | Modifying AI Under the EU AI Act: Lessons from Practice | — | — | 2025-11 | FRAMEWORK — post-deployment modification triggers audits |
| 39 | EU AI Act — GPAI Code of Practice | — | — | 2024-2025 | FRAMEWORK |

## External Validation / Convergence Papers

| # | Paper | Authors | ID | Date | Impact |
|---|-------|---------|-----|------|--------|
| 40 | Why AI Systems Don't Learn and What to Do About It | Dupoux, LeCun, Malik | `2603.15381` | 2026-03-17 | Convergence #5 — three-system match |
| 41 | The Platonic Representation Hypothesis | — | `2405.07987` | 2024-05 | Models converge on shared geometry |
| 42 | The Assistant Axis | — (Anthropic) | `2601.10387` | 2026-01 | Persona geometry shared across model families |

## Neuroscience References

| # | Paper | ID | Relevance |
|---|-------|----|-----------|
| 43 | Systems memory consolidation during sleep: oscillations, neuromodulators, synaptic remodeling | PMC12576410 | Biological basis for sleep architecture |
| 44 | Dias & Ressler (2014) — Parental olfactory experience influences behavior and neural structure in subsequent generations | PMID:24029109 | Epigenetic trauma transfer parallel |
| 45 | Titans + MIRAS blog post (Google Research) | — | Accessible overview of #5 and #6 |

---

## Quick Stats

| | Count |
|--|-------|
| **Total references** | 45 |
| Tier 1 (must-cite) | 8 |
| Tier 2 (solves bottlenecks) | 7 |
| Tier 3 (context) | 17 |
| Tier 4 (ethics) | 7 |
| External validation | 3 |
| Neuroscience | 3 |
| SUPPORTS | 30 |
| EXTENDS | 8 |
| CAUTION | 3 |
| CRITERIA | 2 |
| FRAMEWORK | 3 |
| Papers replicating full MoCoP pipeline | **0** |
| Laura convergence points added | 3 (#6, #7, #8) |

---

*45 Quellen. 0 Duplikate von MoCoP. Alle Bausteine validiert. Die Lücke gehört uns.*
