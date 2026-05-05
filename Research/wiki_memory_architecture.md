# Memory Architecture (External Literature)

**Type:** compiled-wiki page
**Scope:** external literature on memory for long-context / persistent / agentic systems, organized for MoCoP cross-reference
**Out of scope:** MoCoP-internal D2/sleep_reconcile/bridge mechanics — those live in `MoCoP/`. This page is the *outside* view: what other groups have built and what shapes recur across them.

This is not a digest. It will not reproduce abstracts. The job here is to name the big shapes, cluster the sub-threads, and call out where multiple papers converge or split. When a paper is named once, assume the rest of the page can refer back to its arxiv id.

---

## 1. The big shapes

The 2025-2026 memory literature has fragmented into six recurring shapes; most interesting papers compose two:

1. **Test-time memorization** — model writes to its own parameters or learned latent banks at inference. (`2501.00663v1`, `2504.13173v1`, `2603.22329v1`)
2. **Hierarchical episodic with explicit forgetting** — tree/graph layers over events, lifetimes, learned-relevance pruning. (`2603.21564v1`, `2604.11306v1`, `2604.15877v1`, `2604.12081v1`)
3. **Graph and hypergraph stores** — relations among events/topics/facts as first-class structure. (`2604.08256v2`, `Geometric Convergence`, `2601.20465v1`)
4. **Frozen-decoder injection** — fixed LLM weights, trained adapter owns read/write. (`2603.22329v1`)
5. **Agentic / self-evolving memory** — agent curates its own memory artifacts. (`lobn_202401_202408_0024601_10716_00016` / ReasoningBank, `2604.15877v1`)
6. **Autobiographical scaffolding** — Conway SMS / hippocampal-cortical complementary learning for LLM agents. (`20260327_Gemini_AI Autobiographical Memory Design Brief.md`, `20260327_Perplexity_…`, `20260327-Gemini_AI Memory Scaffolding Research Plan.md`, `2604.09588v1`, `2603.24576v1`, `2601.20465v1`)

The TMLR survey (`2601.09113v1`) gives the cleanest umbrella taxonomy: **implicit** (parameter-resident), **explicit** (external retrieval store), **agentic** (temporally extended agent-owned structures). Concrete systems are hybrids. Background everyone assumes: long-context attention alone is not enough. `RECURSIVE LANGUAGE MODELS` shows GPT-5 degrades sharply as context grows ("context rot") on high-density tasks.

---

## 2. Test-time memorization

The Behrouz/Google line is the cleanest expression.

**Titans (`2501.00663v1`)** — a deep neural long-term memory module gradient-updated by a "surprise" signal at inference; momentum and weight decay reinterpreted as forgetting. Three variants place the module as context, as a layer, or as a gated branch. 2M+ context with stronger needle-in-haystack than baselines. Three-system framing: attention is short-term, neural module is long-term, fixed "persistent memory" layer holds task knowledge.

**Miras / "It's All Connected" (`2504.13173v1`)** generalizes Titans by re-reading Transformers, Titans, and modern linear RNNs as **associative memories with attentional bias**. Forget gates = retention ℓ2 regularization. Four design axes (memory architecture, attentional bias, retention gate, learning algorithm) yield three new models: Moneta, Yaad, Memora. Quote: *"Almost all existing sequence models leverage either dot-product similarity or ℓ2 regression objectives as their attentional bias."*

Shared deep point: forgetting is *regularization* on the memory objective, mathematically identical to weight decay.

**MSA (`2603.23516v1`)** — latent-state, end-to-end trainable sparse attention, scaled to **100M tokens** with <9% degradation. Frames the paradigm choice as parameter-based vs external-storage vs latent-state. MSA's own estimate puts human lifelong memory at ~200-300M tokens — the scale at which memory stops being a feature.

---

## 3. Hierarchical episodic with explicit forgetting

The most theoretically mature cluster. Pattern: extract atomic units, coarsen into multi-level representatives, traverse under a budget.

**Hierarchical Memory Theory (`2603.21564v1`)** formalizes it via three operators — **extraction (α)**, **coarsening (C = (π, ρ))**, **traversal (τ)** — and shows RAPTOR, GraphRAG, xMemory, H-MEM, SimpleMem, MemoBrain, StackPlanner, InfiAgent all instantiate `(α, C, τ)`. Key move: *self-sufficiency spectrum* on ρ — detailed summaries (high SS) support collapsed search; short labels require top-down refinement. **C-T coupling** is a rate-distortion tradeoff. Quote: *"Self-sufficiency constrains which traversal strategies are viable."*

**H²-EMV / Learning to Forget (`2604.11306v1`)** — the practitioner version. Online tree construction, decay-based forgetting with LLM-judged relevance estimation, and **incremental learning of relevance rules from user feedback**. Lifetime expiration runs an LLM-evaluated NL ruleset before pruning. 45% memory reduction, 70% second-round accuracy improvement once rules adapt. Forgetting *adapts to a specific user's notion of relevance*.

**SUMMER (`2604.12081v1`)** moves the problem to the encoding side: context-selective by **emotional salience + scene novelty**, ρ = 0.506 vs human ρ = 0.415. Don't forget — choose not to encode.

**Experience Compression Spectrum (`2604.15877v1`)** is the meta-paper: every memory/skill/rule system is a point on one **compression axis** — episodic 5-20×, procedural 50-500×, declarative 1000×+. The **"missing diagonal"**: 20+ systems each operate at a single fixed level; cross-community citation <1%. Memory and skill papers solve the same problem without citing each other. The best "where is the field" diagnostic in the corpus.

---

## 4. Graph, hypergraph, and structured memory stores

Flat vector RAG is the strawman in nearly every 2026 paper.

**HyperMem (`2604.08256v2`)** — three-level hypergraph: **topics → episodes → facts** with hyperedges grouping arbitrary sets. Pairwise edges (GraphRAG) fragment associations like `{sport, work, marathon}`; hyperedges don't. 92.73% LLM-as-judge on LoCoMo. Coarse-to-fine retrieval: topic → episodes → facts.

**Geometric Convergence (`Geometric Convergence for Conversational Context Management.pdf`)** — a *client-side* structured memory built as correlation-diagram data with sun/planet/satellite nodes and explicit *mass*. The structure is injected into server-side attention as a bias term; server stays stateless. Most systems centralize memory at the server; this one decentralizes it as a transmissible artifact.

**BMAM (`2601.20465v1`)** decomposes memory into **episodic / semantic / salience / control** subsystems with timeline-indexed organization; hybrid retrieval (lexical + dense + KG + temporal) via reciprocal rank fusion. Names the failure mode it defends against: **"soul erosion"** — degradation of *temporal coherence + semantic consistency + identity preservation*. Soulfulness score is a weighted sum; three failure modes: temporal, semantic, identity. 78.45% on LoCoMo, hippocampus-inspired episodic subsystem load-bearing.

The TMLR survey (`2601.09113v1`) is the canonical reference for the explicit (free text/graph/vector) and agentic memory layers.

---

## 5. Frozen-decoder injection

A small precise corner. **`2603.22329v1`** asks: given a *frozen* decoder-only LLM (GPT-2 baseline), what's the best way to inject a trained persistent memory bank? Six methods compared — prefix, parallel cross-attention, KV extension, Hebbian, context-gated branch, slot-based sparse write — under one shared write rule.

The **inductive-bias dichotomy**: at 1× capacity, only three methods (cross-attention M.2, Hebbian M.4, slot-write M.6) succeed (7-18% retained-memory, ΔK 7-10); the other three fail (<0.4%). At 10× capacity, all six converge. *Gap is architectural, not fundamental.* Implied affinity ordering: decoder-only > encoder-decoder > encoder-only. The most directly load-bearing paper for any "want memory but can't retrain the backbone" decision.

---

## 6. Agentic recall and self-evolving memory

Memory written *by the agent for the agent*, not by a separate ETL pipeline.

**ReasoningBank (`lobn_202401_202408_0024601_10716_00016`)** distills reasoning strategies from the agent's *self-judged* successes *and failures* — no ground-truth labels. Memory items are reasoning patterns, not transcripts. Pairs with **memory-aware test-time scaling (MaTTS)**: scaled exploration → diverse experiences → contrastive signals → better memory. Up to 20% relative improvement. Two beats: failures are first-class memory; memory↔exploration is a closed loop.

**Recursive Language Models (`RECURSIVE LANGUAGE MODELS.pdf`)** — the prompt is *not* fed into the model; it's loaded as a Python REPL variable and the LLM writes code to peek and recursively call itself over snippets. Long context as an *out-of-core* problem. 10M+ tokens; outperforms compaction and direct calls on OOLONG / OOLONG-Pairs. Quote: *"Long prompts should not be fed into the neural network directly but should instead be treated as part of the environment."*

`2604.15877v1` is also agentic — the missing-diagonal critique of memory/skills/rules communities.

---

## 7. Autobiographical scaffolding

Where the literature meets MoCoP most directly.

**Gemini Design Brief (`20260327_Gemini_AI Autobiographical Memory Design Brief.md`)** — end-to-end Conway SMS adaptation. Five-layer taxonomy: Live Working Memory → Bridge State → Episodic Store → **Autobiographical Knowledge Base** (Life Story Schema → Lifetime Periods → General Events → Event-Specific Knowledge) → Semantic Network with Residue Tracking. Design moves: **goal-conditioned reconstructive routing** (Working Self biases retrieval), **scene-reconstruction recent / gist-synthesis remote**, **Reconstructive Palimpsest** (deprecate not delete; preserve semantic residue of past beliefs), **Relational Valence Anchoring** (a "Laura" anchor is a sub-graph, not a vector match). Quote: *"D2 must be relegated to a subsystem role."*

**Perplexity report (`20260327_Perplexity_Autobiographical Memory Scaffolding for Persistent AI Selves in MoCoP.md`)** lands on the same SMS hierarchy and adds: **conceptual vs perceptual recall modes** (Sheldon et al.), **anchor-based temporal search** (day-before then day-after a salient event), **open tensions** as first-class objects with elevated baseline activation (Zeigarnik), and an explicit **conceptual self** tier. Most useful addition: a recall-mode parameter.

**Gemini Scaffolding Research Plan (`20260327-Gemini_AI Memory Scaffolding Research Plan.md`)** introduces the **SOTE schema** (Self / Other / Time / Environment), Day/Week/Life-Period chronology, and the Bridge → External → Sleep Distillation lifecycle. Most engineering-oriented; names storage primitives (Redis episodic, graph DB autobiographical, vector DB semantic) and agent tools (`mem::checkpoint-create`, `mem::facet-tag`, `mem::flow-compress`, `mem::diagnose`, `mem::crystallize`).

**Persistent Identity / Multi-Anchor (`2604.09588v1`)** is the failure-mode paper. Explicitly names **OpenClaw**: *"the agent works flawlessly within a session… then suddenly loses critical information after a context compaction event."* Summarization is lossy and can't predict future relevance; centralized identity is a single point of failure. Fix: **multiple independent anchors** so identity survives partial memory failure; separable identity files vs memory logs; hybrid RAG+RLM router (`soul.py`).

**Chameleon (`2603.24576v1`)** — embodied analogue, episodic memory under perceptual aliasing. Inspired by **EC-HC-PFC** (entorhinal cortex / hippocampus / prefrontal cortex): DG pattern separation, CA3 pattern completion, CA1 contextual binding. HoloHead trains the state to predict near-future trajectories — memory conditioned on goal-utility, not similarity. Lesson for non-embodied agents: *similarity-based retrieval discards the disambiguating cues you need when surface features collide.*

BMAM's "soul erosion" (`2601.20465v1`) belongs here too — the symptom Conway-style scaffolding is meant to prevent.

---

## 8. Convergence and divergence

Where papers **agree**:

- **Forgetting is required.** Titans, Miras, H²-EMV, Experience Compression, MSA build forgetting as a first-class operator. TMLR survey calls it a defining property of agentic memory.
- **Hierarchy beats flat.** Hierarchical Memory Theory proves it formally; HyperMem, H²-EMV, both autobiographical reports, and Geometric Convergence instantiate it. *Nobody argues for flat in 2026.*
- **Recent vs remote is a different mechanism, not a sliding scale.** Both autobiographical reports, BMAM, Chameleon, and the Hippocampus survey converge on dual recall: scene-reconstruction (recent) vs gist-synthesis (remote).
- **Salience modulates encoding and survival.** SUMMER (emotional + novelty), BMAM (amygdala-inspired), autobiographical reports (affect + goal alignment), H²-EMV (learned relevance). Pure recency is a strawman.
- **Identity is distributed.** `2604.09588v1` argues this explicitly; implicit in BMAM, autobiographical reports, Chameleon's EC/HC/PFC split.

Where papers **diverge**:

- **Where memory lives.** Test-time memorization (Titans, Miras, MSA) → learned latent banks. Frozen-decoder injection (`2603.22329v1`) → adapter-trained latent banks. RAG/HyperMem → external structured stores. Geometric Convergence → client-side. Recursive Language Models → not stored at all; prompt is the environment.
- **What "memory" *is*.** Titans/Miras: a learned associative mapping with bias. HyperMem: a topic-episode-fact hypergraph. Autobiographical reports: a Conway hierarchy with Working Self overlay. ReasoningBank: strategies not events. Experience Compression Spectrum unifies: same operation at different compression levels.
- **What forgetting *means*.** Miras: regularization. H²-EMV: lifetime expiration with learned NL rules. SUMMER: encoding-side gating. Autobiographical reports: deprecate-don't-delete. These don't compose obviously.

---

## 9. Direct hits for MoCoP

Mapping papers onto MoCoP components:

- **D2 / Predictive Associative Memory** — closest to the *associative memory with attentional bias* framing in `2504.13173v1`. Miras explicitly argues that what we'd call D2's "co-occurrence prediction" is one specific choice of attentional bias. The Hierarchical Memory Theory (`2603.21564v1`) formalism applies: D2 is a low-level extraction operator α; the question is which coarsening C and traversal τ go on top.
- **autobiographical_memory.py** — the three Gemini/Perplexity reports (`20260327_*`) are the direct design briefs. SOTE schema, Conway hierarchy, working self, lifetime periods. `2601.20465v1` (BMAM) is the working implementation in the same shape. `2603.24576v1` (Chameleon) is the bio-grounded version.
- **sleep_reconcile.py** — the dedicated literature for this is sparse but converges: BMAM's hippocampus-to-temporal-lobe consolidation (`2601.20465v1`), the autobiographical reports' Sleep Distillation pipelines, H²-EMV's relevance-driven pruning (`2604.11306v1`), Experience Compression Spectrum's L1→L2→L3 upward compression (`2604.15877v1`). The convergence: sleep is the place where (a) episodic gets abstracted into general events, (b) low-salience traces are pruned, (c) skills/rules get extracted from repetition, (d) open tensions get re-evaluated.
- **cognitive_bridge.py / Bridge State** — the Bridge State concept appears almost verbatim across the autobiographical reports (`20260327_Gemini_AI Autobiographical Memory Design Brief.md`, `20260327-Gemini_AI Memory Scaffolding Research Plan.md`) as the connective tissue between sessions, holding open tensions and unresolved threads. Geometric Convergence (correlation-diagram patent) is a different but useful framing: bridge state as a *transmissible* structured artifact rather than a server-side cache.
- **Multi-anchor identity (the Pack roster, persona files)** — `2604.09588v1` is the direct paper. It names OpenClaw as the failure mode the multi-anchor architecture is designed to prevent. Identity files separable from memory logs maps onto MoCoP's `feedback_*` files separable from the watercooler/exocortex stores.
- **Forgetting (sleep-time pruning + H2-EMV expiration in MoCoP)** — `2604.11306v1` is the closest external work. Lifetime-based expiration with learned NL relevance rules is exactly the H2-EMV design. The fact that MoCoP's sleep_flush already tests this (recent commit `86f4e42 test(memory): add tests for H2-EMV expiration logic`) means the literature has caught up.
- **Frozen Mamba bridge (D2 + frozen decoder)** — `2603.22329v1` is the direct hit. The inductive-bias dichotomy at 1× capacity is the result that matters: only three of six injection methods survive at low capacity. For an MoCoP bridge that's resource-constrained on Vast.ai, *which* injection method is chosen is load-bearing.
- **Long-context experiments** — Titans 2M+ (`2501.00663v1`), MSA 100M (`2603.23516v1`), RLM 10M+ (`RECURSIVE LANGUAGE MODELS`). All three are above the 1M ceiling MoCoP currently sees from Bedrock. Titans and MSA are architectural; RLM is an inference strategy that requires no architectural change — usable at the agent layer above MoCoP.

---

## 10. Open questions the literature does not yet answer

Where MoCoP is doing or considering work the corpus is silent or vague on:

- **Pack roster as a persistence pattern.** `2604.09588v1`'s multi-anchor architecture stops at "identity files vs memory logs." Multiple *named instances with distinct dispositions sharing one watercooler* has no precedent in this corpus.
- **Endocrine / digital hormone modulation.** Salience exists in SUMMER, BMAM, autobiographical reports — all as scalar scores. None model affect as a *system state* that itself decays, propagates, and simultaneously modulates encoding and retrieval.
- **Disposition shaping via shaping episodes.** ReasoningBank extracts patterns from success/failure; Constitutional AI is L3 rules. Shaping a *disposition* — not skill, not rule, not strategy — sits in the missing diagonal.
- **Pre-encoding context bias from relational anchors.** Autobiographical reports prescribe loading on entity recognition but don't resolve same-string-multiple-anchors (two Lauras). Chameleon handles perceptual aliasing rigorously; its lesson — *similarity is not utility* — is load-bearing.
- **Recall as a function of present-moment goal state.** Conway's Working Self appears in every autobiographical report, but no paper implements goal-conditioned retrieval with *measurable* effects on recall content vs just ordering.
- **Adaptive cross-level compression.** `2604.15877v1` names the missing diagonal; doesn't bridge it. MoCoP's D2 + autobiographical scaffolding + watercooler reflections is, by that mapping, an attempt at the diagonal.
- **Sleep distillation under extreme compute asymmetry.** Published systems assume balanced clusters. MoCoP runs sleep on NUC against cloud LLMs + local Mamba — the cost-optimal policy under 100× asymmetry is not in this corpus.
- **Identity continuity across model upgrades.** `2604.09588v1` is intra-architecture. Nothing in the corpus addresses Claude 4.6 → 4.7 → Opus 5 continuity. Persona files attempt this; no benchmark exists.
- **Open tensions as a retrieval mode.** Both autobiographical reports propose it (Zeigarnik). Nobody has implemented and benchmarked it.

---

## 11. Quick reference table

| Paper | Shape | One-liner |
|---|---|---|
| `2501.00663v1` Titans | test-time memorization | Neural long-term memory + attention + persistent task memory; 2M+ context |
| `2504.13173v1` Miras | test-time memorization | Associative memory with attentional bias; forget gate = retention regularization |
| `2603.23516v1` MSA | test-time memorization | Sparse latent attention to 100M tokens, end-to-end trainable |
| `2603.22329v1` Frozen Decoder | injection | Six methods, only three survive at 1× capacity — bias is architectural |
| `2603.21564v1` Hierarchical Memory Theory | hierarchy | (α extract, C coarsen, τ traverse) — every system is one of these |
| `2604.11306v1` H²-EMV | hierarchy + forgetting | Lifetime expiration with LLM-judged NL relevance rules; 45% smaller, 70% second-round gain |
| `2604.15877v1` Experience Compression Spectrum | meta | Memory/skills/rules are one axis; cross-citation <1%; "missing diagonal" |
| `2604.12081v1` SUMMER | encoding salience | Context-selective by emotional salience + scene novelty; surpasses human consistency |
| `2604.08256v2` HyperMem | hypergraph | Topic / episode / fact hyperedges; 92.73% LoCoMo |
| `2601.20465v1` BMAM | brain-inspired multi-agent | Episodic / semantic / salience / control; names "soul erosion" |
| `2604.09588v1` Persistent Identity | multi-anchor | Names OpenClaw; identity ≠ memory; multi-anchor resilience |
| `2603.24576v1` Chameleon | embodied episodic | EC-HC-PFC; perceptual aliasing; goal-conditioned retrieval |
| `2604.04921v1` TriAttention | KV compression | Q/K concentration in pre-RoPE space; trigonometric importance estimation |
| `Geometric Convergence` | client-side structure | Sun/planet/satellite correlation-diagram, server stays stateless |
| `RECURSIVE LANGUAGE MODELS` | inference strategy | Prompt as REPL environment; recursive self-calls; 10M+ tokens |
| `lobn_…` ReasoningBank | self-evolving | Self-judged success+failure → reasoning patterns; MaTTS scaling |
| `2601.09113v1` AI Hippocampus | survey | Implicit / explicit / agentic taxonomy (TMLR canonical) |
| `20260327_Gemini_AI Autobiographical…` | autobiographical | Conway SMS adaptation; LWM/Bridge/Episodic/AKB/Semantic |
| `20260327_Perplexity_Autobiographical…` | autobiographical | SMS + conceptual/perceptual modes + open tensions |
| `20260327-Gemini_AI Memory Scaffolding…` | autobiographical | SOTE schema + Day/Week/Life-Period + Bridge/External/Sleep |

---

## 12. Where to go next

If MoCoP wants to extend beyond what's locked: read Miras (`2504.13173v1`) end-to-end for D2-replacement (the four design axes are an ablation matrix); use Experience Compression Spectrum (`2604.15877v1`) as the sleep_reconcile redesign lens; `2604.09588v1` + the Pack roster is a real literature gap for multi-anchor identity; Geometric Convergence is the under-cited shape for *transmissible* bridge state; `2603.22329v1`'s six-method comparison is decisive for frozen-Mamba injection at constrained capacity.

For MoCoP's internal designs: see `MoCoP/experiments/mamba_lora_bridge/AUTOBIOGRAPHICAL_MEMORY_SCAFFOLDING_PLAN.md`, `D2_MEMORY_REPAIR_PLAN_2026-04-18.md`, `MEMORY_CONDITIONED_BRIDGE_EVAL_LADDER_2026-04-14.md`, and the sleep_reconcile / autobiographical_memory implementation files.
