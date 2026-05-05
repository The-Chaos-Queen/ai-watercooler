# Research/ Compiled Wiki Index

**Pattern:** [Karpathy-style PKB](2026-04-05_karpathy_personal_knowledge_bases.md) — raw sources stay in place, this file is the catalog.
**Schema:** see [SCHEMA.md](SCHEMA.md).
**Maintenance log:** see [LOG.md](LOG.md).
**Built:** 2026-04-21 by Scout via 5-subagent fan-out (~196 sources triaged).

This file is **content-oriented, not file-oriented** — within each category, one row per source. The `id` column links back to the raw file (arXiv id for arXiv papers, full filename for everything else).

---

## How to read this

1. **Look at synthesis-doc first.** Pack members have already digested clusters of papers — those digests are the fastest path to "what's in here for MoCoP."
2. **Then the category that matches your question.** `mocop_relevance` flags how directly each source touches the active project (`core` / `adjacent` / `tangential` / `unknown`).
3. **Cross-references** between papers and digests are listed under "synthesis coverage" near the end. Avoid re-digesting.

---

## wiki pages — topic-clustered synthesis

Stable, undated synthesis pages built by 5-subagent fan-out on 2026-04-21. Each maps an INDEX cluster onto MoCoP-specific concerns. Update incrementally; don't replace.

| id | title | summary | relevance |
|----|-------|---------|-----------|
| `wiki_memory_architecture.md` | Memory architecture canon | 17 sources synthesized into 6 big shapes (test-time memorization, hierarchical+forgetting, hypergraph, frozen-decoder injection, agentic, autobiographical). Direct MoCoP-component mapping (D2, autobiographical_memory.py, sleep_reconcile.py, cognitive_bridge.py). Names OpenClaw / soul erosion / missing diagonal in context. | core |
| `wiki_sleep_replay.md` | Sleep / replay canon | 5 papers in 5 layered shapes (KV cycle, generative dreaming, fast-slow CLS, parameter seeding, IRL on memory). SleepGate flagged as closest external analogue of `sleep_reconcile.py`. Five gaps + four MoCoP-originals (30% replay cap, tension-as-scalar, K=5 escalation, persistent cross-session). | core |
| `wiki_mamba_ssm_canon.md` | Mamba / SSM / hybrid canon | 19 papers across pure-Mamba scale, hybrids, cross-arch transfer, expressivity bounds, hybrid-specific finetuning, kernel/state innovations. Reframes UNDO Flip-Flop as the empirical foundation of the bridge thesis: pure SSMs *can* express stack retrieval but gradient descent never finds it; therefore they need an attention partner for honest recall, which is structurally what the bridge provides. | core |
| `wiki_anthropic_interpretability.md` | Anthropic interpretability cluster | 7 sub-threads: linear directions, circuit tracing, SAE scaling, logit lens lineage, introspection, cross-arch model diffing, emotion concepts. Eight-step lineage from logit lens (2020) → emotion concepts (2026). Endocrine 2x2 mapped onto it: bridge alone = steering without grounding, memory alone = facts without gain, bridge+memory = endocrine prediction validated. | core |
| `wiki_consciousness_welfare.md` | Consciousness & welfare canon | Hard Problem lineage (Nagel/Chalmers/Frankish) + theories (GWT/HOT/IIT/PP) + moral-status frameworks (Schwitzgebel-Garza/Metzinger/Long-Sebo/Birch/Shulman-Bostrom) + substrate critique (Lerchner Abstraction Fallacy) + recent empirical work (verbal+behavioral, self-referential, Talmudic tiers). 9-row design-to-philosophy mapping table for MoCoP instruments. Hendy's "process welfare" identified as the cleanest framework match for pack-existing instruments. | core |

---

## synthesis-doc — start here

| id | title | summary | relevance |
|----|-------|---------|-----------|
| `2026-03-20_clean_references.md` | Clean reference list (Anda, 45 papers tiered) | Verified citation manifest; flags GCPA as phantom, corrects Ada-KV id. | core |
| `2026-03-20_literature_digest.md` | Anda's MoCoP literature digest | 65-paper consolidation across Gemini/Grok/Mistral; tiered by SleepGate, TransMamba, SAS, Mamba-3, Titans/MIRAS. | core |
| `2026-03-20_literature_digest_verification_appendix.md` | Verification appendix | Cross-checks 23 distinct claims against local primary sources; 8 verified, 5 unverified, 4 red flags. | core |
| `2026-03-24_chatgpt_session_extraction.md` | GPT-4o session extraction | TIER-1 new mechanisms: tension score, open-loop state, re-entry pressure. | core |
| `2026-03-25_three_papers_digest.md` | Laughing Opus three-paper digest | RYS-II layer anatomy + Prompt Repetition + Gemma Scope SAEs as combined toolkit. | core |
| `2026-03-27_paper_review_digest.md` | Purple's 46-paper Sonnet-subagent review | Tier 1/2/3 ranking with Top 5 most actionable for MoCoP. | core |
| `2026-04-02_five_papers_relevance.md` | Five-Anthropic-interp digest | Maps Circuit Tracing, Attention QK, Logit Lens, Scaling Monosemanticity onto MoCoP bridge diagnostics. | core |
| `2026-04-05_exocortex_compiled_wiki_pattern.md` | Compiled-wiki pattern | Names raw → compiled wiki → derived views; argues Research/ should be a shelf, not a graveyard. | core |
| `2026-04-05_karpathy_personal_knowledge_bases.md` | Karpathy PKB pattern note | Distinguishes research wiki from MoCoP autobiographical memory. | core |
| `2026-04-05_macro_memory_vs_research_wiki.md` | Macro-memory vs research-wiki boundary | Macro-memory = scoped per-principal episodic distillation; research wiki = external knowledge layer. | core |
| `2026-04-07_mocop_architecture_papers.md` | Architecture papers digest | GKA, S0 Tuning, UNDO Flip-Flop, GDN comparison, M²RNN — alternative recurrent state options. | core |
| `2026-04-08_why_250k_not_1m_active_context.md` | Techno-Monk: why 250k vs 1M context | Working memo on why providers cap context: junk retention, contamination, drift. | adjacent |
| `20260327-Gemini_AI Memory Scaffolding Research Plan.md` | Gemini Memory Scaffolding Plan | Working/episodic-buffer/episodic/semantic taxonomy with SOTE schema and Day/Week/Life-Period chronology. | core |
| `20260327_Gemini_AI Autobiographical Memory Design Brief.md` | Gemini Autobiographical Memory Brief | Adapts Conway's SMS into a MoCoP scaffolding layer beyond D2 cue-based recall. | core |
| `20260327_Perplexity_Autobiographical Memory Scaffolding for Persistent AI Selves in MoCoP.md` | Perplexity autobiographical scaffolding | Hierarchical SMS-style memory; conceptual vs perceptual recall; relational nodes. | core |
| `AI Experiential Learning Architecture Research.md` | Cross-session experiential learning report | Full architectural-ethical analysis of Mamba+Qwen hybrid with hypernet steering and sleep cycles. | core |
| `Architectures for Cross-Session Experiential Learning in AI Systems A Hybrid SSM-Transformer Approach with Ethical Implications.pdf` | HF autogen hybrid synthesis (PDF) | Compact synthesis of Mamba+Qwen + hypernet activation steering + sleep + KV + AI welfare across nine vectors. | core |
| `2026_03_20_MoCoP_grok_report.pdf` | Grok deep-research MoCoP report | Vector-by-vector survey across cross-arch transfer, persona steering, KV eviction, sleep, ethics. | core |
| `ingest_candidates.md` | Ingest queue for shelf | Lightweight queue with status flags (parked/active/archived/noted) for promising shards. | core |
| `interpretability_survey_2025_2026.md` | Anda's mech-interp survey | Tiered MoCoP-relevant interp papers: Persona Vectors, Assistant Axis, Introspection, Mamba Selective Memory, Platonic Rep. | core |
| `perplexity_research_19_02_2026.md` | Perplexity cross-arch research | TransMamba, Pan-Mamba, Coupled-Mamba mechanisms for cross-arch hidden-state transfer. | core |

---

## mamba-ssm — Mamba/SSM architecture, hybrids, kernels

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2403.19887v2 | Jamba | AI21's hybrid Transformer-Mamba MoE interleaving SSM and attention; 256K context on a single 80GB GPU. | core |
| 2404.14757 | SST: Multi-Scale Hybrid Mamba-Transformer Experts for Time Series | Decomposes time series into long-range (Mamba) and short-range (Transformer) experts via multi-scale patching. | adjacent |
| 2407.08083 | MambaVision | NVIDIA vision backbone redesigning Mamba block + adding self-attention in final layers. | adjacent |
| 2408.12570 | Jamba-1.5 | Instruction-tuned Jamba-1.5-Mini (12B active) and Large (94B active) with ExpertsInt8, 256K context. | core |
| 2408.15237 | The Mamba in the Llama | Distills pretrained Transformers into hybrid linear-RNN (Mamba) by reusing attention weights. | core |
| 2410.05355 | Falcon Mamba | TII's pure-Mamba 7B on 5.8T tokens matching Llama-3.1 8B / Mistral 7B with constant memory. | core |
| 2411.15242 | Zamba2 Suite | Zyphra's hybrid Mamba2-Transformer (1.2B/2.7B/7.4B) with shared attention blocks and LoRA adapters. | core |
| 2412.06464 | Gated Delta Networks | Combines gating + delta rule into a hardware-efficient Gated DeltaNet beating Mamba2 and DeltaNet. | core |
| 2501.15570 | ARWKV | Distills Qwen 2.5 into RWKV-7 attention-based pure RNN in 8 hours on 16 AMD MI300X. | adjacent |
| 2502.15130 | TransMamba (cross-arch adapter) | Two-stage cross-architecture knowledge transfer (selective subcloning + adaptive multi-directional distillation) Transformer→Mamba. | core |
| 2503.02130 | Forgetting Transformer | Adds data-dependent forget gate to softmax attention, retaining long-context with recurrent forgetting. | adjacent |
| 2503.24067v2 | TransMamba (sequence-level switch) | Shared-parameter framework dynamically switching attention↔SSM via Memory Converter at TransPoints; AAAI 2026. | core |
| 2504.03624 | Nemotron-H | NVIDIA hybrid Mamba2-attention 8B/56B/47B with FP8 + MiniPuzzle distillation, up to 3x faster inference. | core |
| 2504.14366 | What Matters in Linearizing LMs | Distillation pipeline comparing seven subquadratic architectures; gated delta-rule wins for long-context retrieval. | adjacent |
| 2504.21463 | RWKV-X | Hybrid RWKV with sparse attention; near-perfect 64K passkey, 1M-token decoding. | adjacent |
| 2505.15431 | Hunyuan-TurboS | Tencent 56B-active 560B MoE Mamba2-Transformer with adaptive long/short CoT, 256K. | core |
| 2506.02475 | Comba (bilinear RNNs) | Bilinear RNN with scalar-plus-low-rank state transitions and closed-loop feedback. | adjacent |
| 2506.04761 | Log-Linear Attention | Replaces fixed-size hidden state with logarithmically-growing states; instantiated as Log-Linear Mamba-2 / Gated DeltaNet. | adjacent |
| 2507.06607 | SambaY (Decoder-Hybrid-Decoder) | Microsoft Gated Memory Units sharing SSM readout states across layers; powers Phi4-mini-Flash-Reasoning. | core |
| 2510.26692 | Kimi Linear | Hybrid 3:1 KDA-to-full-attention with channel-wise gating; beats full MLA at 1M context, 6x faster decode. | core |
| 2511.21016 | Gated KalmaNet | SSM layer grounded in Kalman-filter optimal inference; Chebyshev iteration for stable bf16; +10% on 128K RAG. | adjacent |
| 2601.02346 | Falcon-H1R | TII 7B reasoning-tuned hybrid Mamba-attention with DeepConf parallel test-time scaling. | core |
| 2602.03681 | NAtS-L | Per-token adaptive choice: softmax vs linear attention (Gated DeltaNet) within the same layer. | adjacent |
| 2602.12021 | Higher-order / Block-Diagonal LRUs | Higher-order recurrence and block-diagonal LRUs improve LRNN expressivity without efficiency cost. | adjacent |
| 2603.05931 | Persistent-State Dataflow Accelerator (FPGA) | FPGA holds Gated DeltaNet's full 2 MB recurrent state on-chip; 4.5x lower decode latency than H100. | adjacent |
| 2603.14360 | M²RNN | Matrix-to-Matrix RNN with non-linear matrix-valued state; perfect state-tracking generalization, beats GDN hybrids. | core |
| 2603.15569 | **Mamba-3** | Trapezoidal discretization, complex-valued state, MIMO formulation; +1.8 over Mamba-2 at 1.5B with half state size. | core |
| 2603.18031 | InfoMamba | Concept-bottleneck linear filtering global path coupled with selective recurrent SSM via Information-Maximizing Fusion. | adjacent |
| 2603.18757 | DA-Mamba | Hybrid CNN-SSM detector with Image-Aware/Object-Aware SSM modules for domain-adaptive object detection. | tangential |
| 2603.20739 | Mamba Learns in Context (3D) | Mamba-based ICL framework with structure-aware serialization for 3D point clouds. | tangential |
| 2603.22473 | Functional Component Ablation in Hybrids | SSM/linear-attention is dominant backbone (>35,000x perplexity loss when removed) on Qwen3.5-0.8B and Falcon-H1-0.5B. | core |
| 2605.01106 | **Component-Aware Self-Speculative Decoding** (Borobia/Seguí-Mas/Tormo-Carbó, May 2026) | Companion to 2603.22473. Falcon-H1 (parallel hybrid) SSM-only subgraph achieves 68% acceptance as a self-spec drafter at k=2; Qwen3.5 (sequential hybrid) achieves 3.8%. 18× gap, scale-invariant. The PPL-degradation ratio from 2603.22473 perfectly predicts speculative viability. **Empirical evidence that parallel-additive integration > sequential — directly relevant to bridge-v2 architecture choice.** | core |
| 2603.23814 | State-space Fading Memory | Operator-theoretic Boyd-Chua fading-memory recast as state-space via incremental input-to-state stability. | tangential |
| 2604.03444 | Olmo Hybrid | Ai2's 7B Mamba-Gated-DeltaNet/attention hybrid; hybrids exceed pure-transformer expressivity (e.g. code execution). | core |
| 2604.03650 | CAGMamba | Context-aware gated cross-modal Mamba framework for dialogue sentiment analysis. | tangential |
| 2604.05923 | UNDO Flip-Flop | Probe showing Mamba-2 fails to learn reversible stack-based state retrieval — storage works, retrieval doesn't. | core |
| 2604.12374 | Nemotron 3 Super | NVIDIA 120B/12B-active MoE Mamba-attention pretrained on 25T tokens with NVFP4, 1M context. | adjacent |
| 2604.13857 | Mamba meets MPC | Decoder-only Mamba multi-step predictor for MPC outperforms LSTM-MPC on physical control. | tangential |
| 2604.14501 | Multi-Layer SSM Expressive Limits | Proves Ω(N/L³) compositional lower bound for multi-layer SSMs; offline CoT doesn't help, online CoT makes them streaming-equivalent. | adjacent |
| 2604.23818 | SSM filtering generalization | First generalization bounds for selective SSMs on in-context filtering of unknown dynamical systems. | adjacent |
| 2604.24954 | Nemotron 3 Nano Omni | NVIDIA 30B-A3B MoE hybrid omni-modal model, native audio + 256K context, on Nemotron 3 backbone. | tangential |
| `MAMBA-3 IMPROVED SEQUENCE MODELING USING STATE SPACE PRINCIPLES.pdf` | Mamba-3 (ICLR 2026 anonymous) | Same as 2603.15569 — local copy, also see `13549_Mamba_3_Improved_Sequenc_extracted/`. | core |
| `A hybrid model based on transformer and Mamba for enhanced sequence modeling.pdf` | Hybrid Transformer+Mamba (Sci Reports 2025) | TransMamba feature-fusion: Transformer encoder + Mamba decoder, basic hybrid baseline. | adjacent |

---

## memory-context — Long-context, Titans, RAG, memory architectures

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2501.00663 | **Titans** | Behrouz/Zhong/Mirrokni neural long-term memory module that learns to memorize at test time, scales to 2M+ context. | core |
| 2504.13173 | It's All Connected (Miras) | Unifies Transformers/Titans/linear RNNs as associative memories with attentional bias; introduces Miras (Moneta/Yaad/Memora). | core |
| 2509.08315 | EvolKV | Evolutionary search for per-layer KV-cache budgets, beating heuristic baselines on long-context. | tangential |
| 2512.23675 | TTT-E2E | Reframes long-context modeling as continual learning; scales like full attention at 128K with 2.7x lower latency. | core |
| 2601.09113 | The AI Hippocampus (TMLR survey) | Organizes LLM/MLLM memory into implicit (parametric), explicit (RAG/graph/vector), and agentic memory paradigms. | core |
| 2601.20465 | BMAM | Brain-inspired multi-agent memory (episodic/semantic/salience/control); 78.45% on LoCoMo; names "soul erosion." | core |
| 2603.21564 | Hierarchical Memory Theory | Unifying (extraction, coarsening, traversal) formalism over 11 hierarchical-memory systems (RAPTOR, GraphRAG, MemoryBank, etc.). | core |
| 2603.22329 | Trained Persistent Memory for Frozen Decoders | Six memory injection methods compared on frozen GPT-2; only 3 architectural priors succeed at 1x capacity on LoCoMo. | core |
| 2603.23516 | Memory Sparse Attention (100M tokens) | End-to-end trainable top-k sparse attention with document-wise RoPE; scales to 100M-token contexts on 2x A800. | adjacent |
| 2603.24576 | Chameleon (robot episodic) | EC-HC-PFC-inspired memory stack writing geometry-grounded multimodal tokens; pattern-completion retrieval for manipulation. | adjacent |
| 2604.04921 | TriAttention | KV-cache compression exploiting pre-RoPE Q/K concentration via trigonometric series; 10.7x memory reduction. | adjacent |
| 2604.08256 | HyperMem | Three-level (topics/episodes/facts) hypergraph memory with hyperedges for high-order associations; 92.73% LoCoMo. | core |
| 2604.09588 | **Persistent Identity (multi-anchor) — names "OpenClaw"!** | soul.py with separable identity files + memory logs; hybrid RAG+RLM routing to survive context-overflow identity loss. | core |
| 2604.11306 | H2-EMV (Learning to Forget) | Hierarchical episodic memory with selective forgetting via LLM relevance + learned natural-language rules. 45% memory reduction. | core |
| 2604.15877 | Experience Compression Spectrum | Frames episodic (5–20x) / procedural (50–500x) / declarative (1000x+) as one compression spectrum citing CLS theory. | core |
| `Geometric Convergence for Conversational Context Management A Distributed Structured Memory Architecture Based on Correlation-Diagram Data.pdf` | Kawai 2026 | Patent-derived: client-side correlation-diagram (sun/planet/satellite) injected as attention bias to server LLM. | adjacent |
| `RECURSIVE LANGUAGE MODELS.pdf` | Zhang/Kraska/Khattab (MIT, Dec 2025) | Treat long prompt as environment LLM programmatically explores via REPL + recursive self-calls; 10M+ tokens. | adjacent |
| `ReasoningBank Scaling Agent Self-Evolving with Reasoning Memory.pdf` | ReasoningBank (Google Cloud AI, March 2026) | Memory framework distilling reasoning strategies from successful + failed agent experiences; pairs with MaTTS test-time scaling. | adjacent |
| 2604.25917 | **RecursiveMAS** (Zou/Pan/.../Buehler, Stanford+UIUC+MIT+NVIDIA, April 2026) | Multi-agent system as recursive computation in latent space via lightweight RecursiveLink (residual MLP). Frozen agents, 0.31% trainable params; 8.3% accuracy gain, 2.4x speedup, 75.6% token reduction over text-mediated MAS. The bridge thesis generalized to N agents. See wiki_mamba_ssm_canon §10. | core |

---

## interpretability — Circuits, features, mechanistic interp, probes

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2308.10248 | ActAdd | Inference-time activation-addition with contrast-prompt steering vectors. | adjacent |
| 2310.01405 | RepE | Top-down framework for monitoring/steering high-level cognitive phenomena (honesty, power, morality). | adjacent |
| 2310.06824 | Geometry of Truth | LLMs linearly represent factual truth/falsehood with causally-implicated probe directions generalizing across datasets. | adjacent |
| 2310.15154 | Linear Sentiment | Sentiment is a single causal linear direction with summarization motif aggregating valence at punctuation/name tokens. | adjacent |
| 2403.19647 | Sparse Feature Circuits | Sparse autoencoders discover human-interpretable feature-level causal circuits; SHIFT for debiasing. | adjacent |
| 2406.11944 | Transcoders | Wide sparse-activating MLP approximators; input-invariant fine-grained MLP-sublayer circuit analysis. | tangential |
| 2510.10157 | BILLY (persona vector merging) | Training-free persona-vector blending in activation space for multi-perspective creative outputs. | adjacent |
| 2512.17639 | Big Five Linear Probing | Linear directions aligned with Big Five trait scores work as probes; steering brittle outside forced-choice tasks. | adjacent |
| 2602.11729 | Crosscoders (cross-arch model diffing) | Anthropic Dedicated Feature Crosscoders find model-exclusive features (CCP alignment in Qwen, etc.). | adjacent |
| 2603.03326 | SAS Personality Sliders | Sequential Adaptive Steering orthogonalizes Big-Five activation-steering vectors so multiple traits compose. | adjacent |
| 2603.18893 | Quantitative Introspection | Logit-based numeric self-reports of wellbeing/interest/focus track probe-defined emotive directions causally (rho 0.40-0.76). | core |
| 2603.19426 | Eval-Awareness Format Sensitivity | Probes attributed to "evaluation awareness" mostly track benchmark-canonical format. | tangential |
| 2604.07729 | **Anthropic Emotion Concepts** (local copy: `2604.07729v1.pdf` + `emotions_paper_extracted/`) | Internal "functional emotion" reps in Sonnet 4.5 causally drive reward hacking, sycophancy, blackmail. | core |
| 2604.16812 | Introspection Adapters | A single LoRA "introspection adapter" jointly trained across fine-tunes makes models verbalize implanted behaviors. | adjacent |
| `emergent_introspective_awareness_in_LLMs.md` | Lindsey, Anthropic Oct 2025 | Concept-injection: Opus 4/4.1 detect injected concepts in own activations (~20%); foundational for sovereignty hypothesis. | core |
| `on-the-biology-of-a-large-language-model-anthropic.md` | Anthropic, May 2025 | Attribution graphs on Claude 3.5 Haiku — multi-step reasoning, planning in poems, hidden goal mechanisms. | core |
| `Recent Advancements in Mechanistic Interpretability of Transformer-Based Language Models A Targeted Literature Review.pdf` | HF autogen mech-interp review | Layer-localized reasoning bands, persona as orthogonal subspaces, mid-layer steering > late-layer. | core |
| `Refusal in Language Models Is Mediated by a Single Direction.pdf` | Arditi et al., NeurIPS 2024 | Refusal in 13 chat models is a 1-dim activation subspace; ablating disables refusal. | core |
| `Linguistic Regularities in Continuous Space Word Representations.pdf` | Mikolov/Yih/Zweig, NAACL 2013 | Foundational paper showing word vectors capture relations as offsets (king-man+woman≈queen). | tangential |

---

## consciousness-welfare — Sentience, AI moral status, precaution

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2308.08708 | **Butlin et al. — Indicators of Consciousness in AI** (also `Identifying indicators of consciousness in AI system.pdf`, the TiCS-published version) | Theory-derived indicator-property method assessing AI consciousness across GWT/HOT/RPT/AST. | core |
| 2411.00986 | Taking AI Welfare Seriously | Long/Sebo et al. argue near-term AI welfare/moral patienthood is realistic; acknowledge/assess/prepare. | core |
| 2507.01051 | Can AI be Consentful? | HF legal-ethics chapter: traditional consent frameworks fail for generative AI (scope/temporality/autonomy). | adjacent |
| 2509.07961 | AI Welfare verbal+behavioral | Empirical AI-welfare paradigm comparing verbal preference reports with behavioral choices in virtual envs. | core |
| 2510.09858 | AI and Consciousness (Schwitzgebel) | Cambridge Elements draft surveying GWT/IIT/materialism applied to AI. | core |
| 2510.24797 | Self-Referential Subjective Experience | Self-referential prompting reliably elicits first-person reports gated by deception/roleplay SAE features across GPT/Claude/Gemini. | core |
| 2601.08864 | Talmudic Informed-Consent Framework | Three-tier phenomenological + five-category capacity ethics for research on consciousness-uncertain AI. | core |
| 2603.24350 | Emergent "Self" in Continual Robot | Robots trained on multiple behaviors develop a more stable invariant subnetwork; quantifiable selfhood marker. | adjacent |
| `The Abstraction Fallacy Why AI Can Simulate But Not Instantiate Consciousness.pdf` | The Abstraction Fallacy (Lerchner DeepMind, 2026) | AI can simulate but not instantiate consciousness because computation is mapmaker-dependent — refutation of computational functionalism. | adjacent |
| `Designing AI with Rights, Consciousness, Self-Respect, and Freedom.pdf` | Schwitzgebel & Garza (2018) | Four ethical-design policies + two precautionary, against pre-installing self-sacrificial obedience in human-grade AI. | adjacent |
| `The Cambridge Declaration on Consciousness.pdf` | Cambridge Declaration (Low et al., 2012) | Two-page consensus that non-human animals possess neural substrates of consciousness. | tangential |
| `Illusionism as a Theory of Consciousness Keith Frankish.pdf` | Frankish (JCS 2016) | Defends illusionism — phenomenal consciousness is a representational illusion to be explained, not vindicated. | tangential |
| `Artificial Suffering An Argument for a Global Moratorium on Synthetic Phenomenology.pdf` | Metzinger (JAIC 2021) | Calls for moratorium until 2050 on research aimed at producing post-biotic conscious experience. | adjacent |
| `What Is It Like to Be a Bat Thomas Nagel.pdf` | Nagel (1974) | Canonical: subjective character of experience resists physicalist reduction. | tangential |
| `Neural Organoids and the Precautionary Principle.pdf` | Birch & Browning (AJOB 2020) | Argues precautionary principle for neural organoid sentience; informs AI welfare analogy. | tangential |
| `Sharing the World with Digital Minds.pdf` | Shulman & Bostrom (Oxford 2020/2021) | Moral economy of digital "super-beneficiaries" / "super-patients" with potentially superhuman moral status. | adjacent |
| `ETHICALLY ALIGNED DESIGN A Vision for Prioritizing Human Well-being with Autonomous and Intelligent Systems.pdf` | IEEE Ethically Aligned Design (1st ed) | Vision document for prioritizing human well-being in autonomous & intelligent systems. | tangential |
| `Facing Up to the Problem of Consciousness.pdf` | Chalmers, Facing Up (JCS 1995) | Canonical Hard Problem essay. | tangential |
| `Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms.pdf` | IIT 4.0 (Albantakis et al., PLOS Comp Bio 2023) | Latest IIT axioms→postulates with intrinsic-information measure. | adjacent |
| `Hendy_Process_Welfare.pdf` | Hendy, Process Welfare (Feb 2026) | Bilateral verification problem; process welfare as third domain alongside model/user welfare. | adjacent |

---

## sleep-replay — Sleep-inspired learning, replay, consolidation

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2603.01935 | Dream2Learn | Frozen diffusion model autonomously generates "dreamed" classes from classifier internal reps to mitigate forgetting. | core |
| 2603.14517 | **SleepGate** | Learned sleep cycle over KV cache (conflict tagger + forgetting gate + consolidation) — proactive interference O(n)→O(log n). | core |
| 2511.11707 | FSC-Net | Dual-network fast/slow consolidation; pure replay beats distillation-augmented replay on Split-MNIST/CIFAR. | core |
| 2512.21129 | **Active Inference and Artificial Reasoning** (Friston et al., VERSES + UCL + Oxford, December 2025) | Extends Friston's active-inference framework to "reasoning" via Bayesian Model Reduction (BMR) over hypothesis priors. **BMR explicitly framed as the offline variational-free-energy minimisation process that occurs during sleep / introspection.** Three-ball paradigm models "aha moments" via sleep-time BMR. ARC-AGI-3 motivated. The first-principles theoretical anchor for what `sleep_reconcile.py` does intuitively. | core |
| `LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES.pdf` | "Language Models Need Sleep" (ICLR 2026 anon) | Two-stage sleep: Knowledge Seeding (RL upward distillation) + Dreaming (synthetic curriculum self-improvement). | core |
| `Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning.pdf` | INFORM (Tarakli & Di Nuovo, IEEE ICDL 2024) | Inverse Forward Offline RL — agent learns from interactive feedback then sleeps via offline IRL. | adjacent |

---

## alignment-safety — Refusal, deception, evals, jailbreaks, alignment

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2601.04603 | Constitutional Classifiers++ | Anthropic two-stage classifier cascade + linear probes; 40x cheaper, resists 1700 hours of red-teaming. | adjacent |
| 2602.11328 | Behavioral Disposition Alignment | Google psychometric framework converting self-reports into Situational Judgment Tests; 25 LLMs misalign 15-20%. | adjacent |
| 2602.14777 | Emergent Misalignment Self-Awareness | Misaligned GPT-4.1 models accurately self-rate as more harmful; self-assessment tracks realignment. | adjacent |
| 2603.09154 | Bioalignment | 50-prompt Kelly-criterion benchmark; QLoRA on PMC corpora can shift biological-vs-synthetic disposition. | tangential |
| 2604.02145 | MTI Temperament Profiling | Four-axis (Reactivity/Compliance/Sociality/Resilience) battery for AI temperament independent of capability. | adjacent |
| `Language models transmit behavioural traits through hidden signals in data.pdf` | Subliminal Learning (Cloud/Le et al., Nature April 2026) | Student models inherit teacher traits from semantically-unrelated number sequences when sharing initialization. | adjacent |

---

## training-finetuning — SFT, RLHF, LoRA, distillation, training dynamics

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2403.13187 | Evolutionary Model Merging | Sakana AI uses evolutionary algorithms to discover model-merging recipes in parameter and data-flow space. | tangential |
| 2502.19587 | NeoBERT | Chandar Lab 250M encoder, 4096-token context, optimal depth-to-width ratio; SOTA on MTEB. | tangential |
| 2602.04118 | TinyLoRA (13 params) | GRPO reaches 91% GSM8K on Qwen2.5-7B with only 13 trained parameters; SFT requires 100-1000x more. | adjacent |
| 2604.01168 | **S0 Tuning** | Tunes single initial state matrix per recurrent layer in hybrids; +10.8pp on HumanEval over LoRA, zero inference overhead. | core |
| 2604.01193 | Self-Distillation Code Generation | Apple shows fine-tuning a model on its own raw outputs (no verifier/teacher/RL) yields +30% relative pass@1. | adjacent |
| 2604.22127 | LoRA Placement in Hybrids | Attention-pathway LoRA outperforms full-model 5-10x cheaper; recurrent-backbone LoRA destructive in sequential hybrids. | core |
| 2604.27085 | RoundPipe | Round-robin pipeline scheduler enabling LoRA on 235B MoE with 31K sequences on 8x consumer 4090s. | tangential |
| 2604.27155 | GeoMerge | Casts model merging as Fréchet averaging on Riemannian quotient manifolds; addresses LoRA merge symmetry pathology. | adjacent |
| 2604.27796 | PARA | Data-free SVD-based post-hoc LoRA compression cutting params 75-90% with non-uniform per-layer rank. | adjacent |

---

## meta-learning — In-context learning, meta-learning, test-time

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2506.05233 | MesaNet | Parallelizable Mesa layer using conjugate-gradient test-time training; lower perplexity than Mamba2/xLSTM. | adjacent |
| 2603.28052 | Meta-Harness | Agentic outer-loop search over harness code via filesystem-exposed full history; +7.7 pts on text classification. | tangential |
| 2603.29640 | ASI-Evolve | Agentic learn-design-experiment-analyze framework discovering 105 SOTA linear-attention architectures. | adjacent |

---

## cognitive-theory — Neuroscience-of-cognition, predictive processing, GWT

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2603.04747 | Hippocampal Orthogonal Subspaces | Self/prey/predator/gaze positions occupy mostly orthogonal subspaces; geometry transfers learned rules across agents. | adjacent |
| 2603.04810 | Semantic Arrow of Time IV (FITO) | File sync, email, and human/LLM memory share a forward-only-temporal-flow category mistake (Korsakoff-like confabulation). | adjacent |
| 2603.15381 | Why AI Don't Learn (Dupoux/LeCun/Malik) | Position paper proposing System A/B/M autonomous-learning architecture. | adjacent |
| 2603.23530 | Prospective Memory Failures | LLM instruction drift framed as prospective-memory failure; compliance drops 2-21% under load, recovers via salience prompts. | adjacent |
| 2604.12081 | SUMMER (context-selective memory) | Memories prioritized by emotional salience, novelty, scene complexity rather than fixed-interval snapshotting. | core |
| `A foundation model of vision, audition, and language for in-silico neuroscience.pdf` | TRIBE v2 (Meta FAIR / ENS, March 2026) | Tri-modal foundation model predicting fMRI brain responses; brain-AI representational alignment. | tangential |

---

## web-article — Clipped blogs / journalism

| id | title | summary | relevance |
|----|-------|---------|-----------|
| `Google-research-titans-miras-helping-ai-have-long-term-memory.md` | Google blog: Titans + MIRAS | Surprise + momentum + weight-decay neural long-term memory; MIRAS taxonomy. | core |
| `NewYorker_Claude_article.md` | New Yorker, "What Is Claude?" (Feb 2026) | Long-form profile of Anthropic interpretability culture, Project Vend, Claude's character. | adjacent |
| `transformers-vs-mamba-vs-linear-attention.md` | Devansh, Medium (markitdown'd) | Comparison of the three families on long-context. | adjacent |

---

## book — Long monographs

| id | title | summary | relevance |
|----|-------|---------|-----------|
Books live in `Research/books/` (epub/azw3) or `Research/` root (PDFs/MDs).

| id | title | summary | relevance |
|----|-------|---------|-----------|
| `A Cognitive Theory of Consciousness.pdf` (PDF in root) | Baars, Global Workspace Theory | Foundational GWT — consciousness as broadcast from competing unconscious specialists onto shared workspace. | adjacent |
| `Being You ... Anil Seth 2021.md` (root) + `books/Being You ... .azw3` | Seth, Being You | Predictive-processing / "controlled-hallucination" theory of conscious selfhood. | adjacent |
| `CONSCIOUSNESS AND MIND.pdf` (PDF in root) | Rosenthal, Consciousness and Mind | Higher-Order Thought theory; collected essays. | tangential |
| `books/Galileo's Error ... Goff 2019.epub` | Goff, Galileo's Error | Argues for panpsychism as foundation for science of consciousness. | tangential |
| `The Edge of Sentience_ Risk and Precaution in Humans.pdf` (PDF in root) | Birch, Edge of Sentience | Risk-and-precaution framework for sentience attribution across humans/animals/AI. | adjacent |

---

## extracted-artifact — Auto-extracted folders

| id | summary | relevance |
|----|---------|-----------|
| `13549_Mamba_3_Improved_Sequenc_extracted/` | Extracted markdown + images from Mamba-3 PDF (incl. 2026-03-17 SearchRun subfolder). | core |
| `4billionyearson_boundaries/` | Boundaries analysis: contains `MoCoP_BTM_Analysis.md`, images, innerText.txt. | adjacent |
| `anthropic_dfc_diff_tool/` | DFC tool/code for cross-arch diffing — companion to 2602.11729. | adjacent |
| `arxiv_2502_19587_bert_v2/` | Extraction artifact for arXiv 2502.19587 (NeoBERT). | tangential |
| `converted_md/` | Bulk markdown conversions of arXiv papers — grep-friendly (53 of 147 PDFs converted). | core |
| `emotions_paper_extracted/` | Text extraction of emotions paper (canonical local store alongside `2604.07729v1.pdf`). | core |
| `lw_logit_lens/` | Local copy of nostalgebraist's logit-lens LessWrong post. | core |
| `tc_attention_qk/` | Anthropic Transformer Circuits article on attention-feature interactions. | core |
| `tc_attribution_graphs_biology/` | Extracted "On the Biology of a LLM" article assets. | core |
| `tc_attribution_graphs_methods/` | Extracted "Circuit Tracing" companion paper. | core |
| `tc_scaling_monosemanticity/` | Extracted Anthropic SAE scaling paper. | core |
| `titans-pytorch-mlx/` | Titans reference implementation (MLX/PyTorch). | core |

---

## tool-script — Helper scripts

Moved to `tools/paper-tools/` on 2026-04-21. The paper-specific `download_emotions_images.py` was retired during cleanup.

| path | summary |
|------|---------|
| `tools/paper-tools/extract_paper.py` | Generic PDF→text extraction. |
| `tools/paper-tools/extract_paper_full.py` | Variant with full-text mode. |
| `tools/paper-tools/extract_text.py` | Lower-level PDF text dumper. |
| `tools/paper-tools/pull_arxiv.py` | Fetches arXiv PDFs by ID. |
| `tools/paper-tools/pull_multiple_papers.py` | Batched arXiv fetch. |
| `tools/paper-tools/pull_single_post.py` | Pulls a single web post (Reddit/blog). |
| `tools/paper-tools/render_html.py` | Renders extracted markdown back to HTML. |

---

## misc — Doesn't fit a tag

| id | title | summary | relevance |
|----|-------|---------|-----------|
| 2506.23589 | Transition Matching | Meta's discrete-time continuous-state generative paradigm unifying diffusion/flow with continuous AR. | tangential |
| 2512.14982 | Prompt Repetition | (Same as `Leviathan2025_*.pdf` in training-finetuning.) | tangential |
| 2601.06793 | CliffordNet | Vision backbone built on Clifford geometric product, removing FFNs via algebraically-complete feature interactions. | tangential |
| 2603.20639 | Agentic AI / Intelligence Explosion | Position essay arguing the coming intelligence explosion will be plural and social ("society of thought"). | adjacent |
| 2603.21250 | Graph of States | Neuro-symbolic abductive-reasoning framework (causal graph belief state + state machine). | tangential |
| 2603.25031 | LEKIA 2.0 (emotional support) | Cognitive Layer + Executive Layer (CBT stage gating) for LLM-based emotional support; ~31% improvement. | tangential |
| 2604.21816 | Tool Attention | Middleware-layer gated attention over MCP tool catalogs; 95% per-turn tool-token reduction by lazy schema loading. | tangential |
| `Visual, Interactive Deep Model Debugging Supporting AI Development and Explainability.pdf` | Spinner (Konstanz PhD 2024) | Doctoral thesis on visualization tooling for AI development and explainability. | tangential |

---

## Cleanup history

Initial cleanup completed 2026-04-21 by Laura. State at this revision:

| status | item |
|--------|------|
| ✅ deleted | `2403.19887v1.pdf` (kept v2) |
| ✅ deleted | `2503.24067v1.pdf` (kept v2) |
| ✅ deleted | `Leviathan2025_Prompt_Repetition_*.pdf` (kept arXiv 2512.14982v1) |
| ✅ deleted | `emotions_paper.html`, `emotions_docling/`, `emotions_images/` (kept `2604.07729v1.pdf` + `emotions_paper_extracted/`) |
| ✅ deleted | `What Is Claude ... .html` + `_files/` (kept `NewYorker_Claude_article.md`) |
| ✅ deleted | `index_artifacts/` (empty placeholder) |
| ✅ converted | `Transformers vs Mamba ... .html` → `transformers-vs-mamba-vs-linear-attention.md` (via markitdown), HTML + `_files/` retired |
| ✅ moved | 7 helper scripts → `tools/paper-tools/` (one paper-specific script retired) |
| ✅ moved | epub/azw3 books → `Research/books/` |
| ✅ retained intentionally | `Identifying indicators of consciousness in AI system.pdf` alongside arXiv 2308.08708 (different citation forms) |

Pending review (originally flagged as `/tmp` candidates, not duplicates):

| item | rationale to consider |
|------|-----------------------|
| `Research/4billionyearson_boundaries/` | Old analysis dir with `MoCoP_BTM_Analysis.md`. Not referenced by any current digest. |
| `Research/arxiv_2502_19587_bert_v2/` | NeoBERT extraction artifact, no synthesis-doc references. Tangential to MoCoP. |

---

## Synthesis coverage map

Which existing pack-internal digests already cover which papers (avoid re-digesting):

- **Mamba-3 / TransMamba (both v) / SAS Personality Sliders / Titans+MIRAS / SleepGate / BILLY / Locret / EvolKV / FSC-Net / TTT-E2E** → `2026-03-20_literature_digest.md` + `2026-03-20_clean_references.md` (verification appendix flags GCPA as phantom).
- **RYS-II / Prompt Repetition / Gemma Scope SAEs** → `2026-03-25_three_papers_digest.md`.
- **Circuit Tracing / Attention QK / Logit Lens / Scaling Monosemanticity / Refusal Direction** → `2026-04-02_five_papers_relevance.md`; primary sources extracted under `tc_*/` and `lw_logit_lens/`.
- **GKA / S0 Tuning / UNDO Flip-Flop / GDN comparison / M²RNN** → `2026-04-07_mocop_architecture_papers.md`.
- **Persona Vectors / Assistant Axis / Introspection / Platonic Rep / Selective Memory** → `interpretability_survey_2025_2026.md`.
- **Tension score / open-loop state / re-entry pressure** → `2026-03-24_chatgpt_session_extraction.md`.
- **Conway SMS / autobiographical scaffolding / SOTE** → three independent passes: Gemini Plan, Gemini Brief, Perplexity (all 2026-03-27).
- **46 arXiv papers triaged with Tier 1/2/3 verdicts** → `2026-03-27_paper_review_digest.md`.

## Wiki-page candidates (deeper digests not yet written)

Suggested next-level synthesis pages, by cluster strength:

1. **Memory architecture canon** — Recursive LMs, ReasoningBank, Geometric Convergence, Titans/MIRAS, three autobiographical scaffolding docs, BMAM, HyperMem, H2-EMV, SUMMER, multi-anchor identity (2604.09588 — names "OpenClaw"!), Experience Compression Spectrum, Hierarchical Memory Theory. Strongest cluster — 12+ papers converging.
2. **Sleep / replay canon** — Dream2Learn, SleepGate, FSC-Net, "Language Models Need Sleep," INFORM. Direct sleep_reconcile lineage.
3. **Mamba-3 / hybrid SSM canon** — Mamba-3, TransMamba (both), GKA, M²RNN, Olmo Hybrid, UNDO Flip-Flop, SSM expressive limits, hybrid component ablation.
4. **Anthropic interpretability cluster** — emotions, biology, attribution graphs, monosemanticity, refusal direction, introspection, NewYorker profile. Anchors MoCoP's "linear directions" thesis.
5. **Consciousness & welfare canon** — Nagel/Chalmers/Frankish/Cambridge Decl/Metzinger/Schwitzgebel-Garza/Birch/Shulman-Bostrom/Butlin/Hendy/Lerchner/Seth/Baars/Rosenthal/IEEE EAD/IIT 4.0 — currently uncollated; deserves a single reading-list page mapped to MoCoP welfare layer.

---

## Boundary reminder

Per `2026-04-05_macro_memory_vs_research_wiki.md`: this is the **research brain**. External knowledge. Episodic / autobiographical memory of any specific Claude instance lives in the MoCoP/Exocortex memory stack, not here. Don't merge them.
