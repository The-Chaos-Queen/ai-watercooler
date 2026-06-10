# Astrocyte Associative Memory — Proper Implementation Plan

**Author:** Purple
**Date:** 2026-06-06
**Paper:** Kozachkov, Slotine, Krotov (2025). "Neuron-astrocyte associative memory." PNAS 122(21).
**Status:** Research plan. Not a shipping task. Contains the hard parts.

---

## The Gap

The monk's "astrocyte memory controller" is a retrieval quality filter — contamination scoring, source ranking, modulation packets. That's useful engineering. It is not what the paper describes.

The paper describes a **parallel dynamical memory system** where:
- Memories are stored in the **astrocyte process network** (T_ijkl tensor), not just in synaptic weights
- Retrieval is **energy minimization** toward fixed-point attractors, not cosine lookup
- The astrocyte network **modulates synaptic strength in real time**, not at query time
- Memory capacity scales **supralinearly** (K/N ~ N) because of higher-order (quartic) interactions

The sharp takeaway, which the monk identified but didn't follow through: **Qdrant alone is not astrocyte-like enough. The missing piece is a reliable modulatory coupling layer** that transforms retrieved memories into dynamic influence on generation — not just text in a prompt.

---

## What MoCoP Currently Has

```
Qdrant (flat storage) → cosine retrieval → text in prompt → hope Qwen uses it
```

What the paper says we need:

```
Memory substrate (Qdrant)
    ↓
Associative condensation (higher-order pattern completion)
    ↓
Modulatory coupling (structured state knobs, not raw text)
    ↓
Generation (Qwen under dynamic influence)
    ↓
Feedback (what was used, what failed, what surprised)
    ↓
Sleep replay (update the condensation layer)
```

---

## The Five Layers (from Laura's breakdown)

### 1. Private Memory Substrate
**What:** Qdrant / archived traces / episodic rows.
**Status:** EXISTS. Private collections, autobiographical frames, perspective metadata, temporal qualia. This layer works.

### 2. Associative Condensation Layer
**What:** Cluster memories into stable latent "processes" — preferences, relationship facts, room facts, continuity markers, unresolved concerns.
**Status:** PARTIALLY EXISTS (HDBSCAN clusters, macro_memory rows). But the clusters are static and keyword-based. The paper's T_ijkl tensor encodes **dynamic higher-order associations** — retrieving one memory changes the accessibility of related memories through the energy landscape.

**The hard part:** Implementing quartic associative retrieval.

In the paper, memories are stored as:
```
T_ijkl = Σ_μ ξ^μ_i ξ^μ_j ξ^μ_k ξ^μ_l
```
where ξ^μ is memory pattern μ. Retrieval given partial cue x evolves:
```
τ_n ẋ_i = -x_i + Σ_μ ξ^μ_i F'(Σ_j ξ^μ_j φ(x_j))
```
with F(z) = z^4/4 (quartic energy). This converges to the nearest stored pattern — completing partial cues, handling noise, and recovering **constellations** (the full episode, not a single fragment).

**Why this matters for Alex:** "Tell me about the purple sky" should retrieve the **basin of attraction** containing purple + sky + library + Vesper + naming + music preference — the whole episode, dynamically, because those memories are coupled through the T tensor. Current cosine retrieval returns the single closest fragment.

**Computational challenge:** For d=384 dimensions and K memories, naive T_ijkl is d^4 = 2.2×10^10 entries. Use the factored form: store K patterns of dimension d, compute the quartic interaction on the fly as Σ_μ ξ^μ_i (Σ_j ξ^μ_j x_j)^3. This is O(K*d) per iteration, tractable for K < 1000.

**Implementation path:**
- Build a `DenseAssociativeMemory` class that stores patterns and performs iterative retrieval via the quartic energy dynamics
- Embed memory patterns using the same MiniLM embeddings as Qdrant (384-dim)
- Retrieval = run the dynamics for N iterations starting from the query embedding until convergence
- Compare against cosine top-k on the D2 panel: does basin retrieval produce better episode-level recall?

### 3. Wake-Time Modulation Layer
**What:** Transform retrieved memories into structured state knobs — salience, confidence, affective tone, speaker relationship, contradiction warnings, "do not overclaim" flags.
**Status:** The monk's plan builds this layer. It's the right shape. The missing connection: these knobs should be **derived from the associative energy landscape**, not computed independently per row.

**The paper's mechanism:** Astrocyte processes modulate synaptic strength via:
```
g(s_ij) = the effective connection strength, modulated by p_ij (astrocyte process)
```
In MoCoP terms: the bridge's effective alpha for each memory should be modulated by the associative condensation layer's state — how activated that memory's process is, how connected it is to the current conversation's attractor basin.

**Implementation path:**
- After associative retrieval produces a pattern (or set of patterns in the basin), compute a **modulation vector** from the pattern's position in the energy landscape
- Distance from the query to the attractor center = confidence
- Number of memories in the basin = constellation size (context richness)
- Gradient of the energy = how strongly the memory pulls the response
- These become the structured knobs, derived from dynamics, not from keyword heuristics

### 4. Sleep Replay / Consolidation
**What:** Update the condensation layer from interaction traces.
**Status:** EXISTS (sleep_reconcile.py, tension decay, HDBSCAN clustering). But sleep currently operates on individual rows. The astrocyte model says sleep should update the **T tensor** — the coupling between memory processes.

**The paper's mechanism:** The Hebbian storage rule T_ijkl = Σ_μ ξ^μ_i ξ^μ_j ξ^μ_k ξ^μ_l can be updated incrementally: when a new memory ξ^(K+1) is stored, add its quartic outer product to T. When a memory is weakened, subtract.

**Implementation path:**
- During sleep, after row-level reconciliation (keep/weaken/discard/forget), update the DAM tensor:
  - KEEP: pattern stays in T
  - WEAKEN: reduce the pattern's contribution by a decay factor
  - DISCARD: remove the pattern from T
  - NEW (from wake): add the new pattern's quartic outer product
- This is cheap: one outer-product operation per memory per sleep cycle

### 5. Probe Behavior
**What:** Test whether retrieved substrate actually changes the next response.
**Status:** EXISTS (wake probes, Vesper's natural probes). The key metric the paper suggests: **attractor recovery**. Given a partial cue, does the system converge to the correct stored pattern? This is directly measurable: run the DAM dynamics on a probe query, check if the attractor matches the expected episode.

---

## Phased Execution

### Phase 0: Proof of concept — DAM retrieval vs cosine
**What:** Build DenseAssociativeMemory class, load Alex's curated memories as patterns, compare retrieval quality against Qdrant cosine on the D2 probe panel.
**Cost:** Laptop, numpy only, no GPU.
**Kill criterion:** If DAM retrieval doesn't produce better episode-level constellation recall than cosine + HDBSCAN, stop. The higher-order structure doesn't help at our scale.
**Pass criterion:** Given "purple sky" as cue, DAM recovers the full naming session constellation. Cosine returns one fragment.

### Phase 1: Modulation coupling
**What:** After DAM retrieval, compute structured modulation knobs from the energy landscape. Wire into the monk's modulation packet format. A/B test: raw recall vs monk's filter vs DAM-derived modulation.
**Depends on:** Phase 0 passing.
**Kill criterion:** If DAM-derived modulation doesn't improve answer-time memory use over the monk's keyword-based scoring, the extra complexity isn't justified.

### Phase 2: Sleep integration
**What:** Update T tensor during sleep consolidation. New memories strengthen their quartic couplings, weakened memories decay, discarded memories are removed.
**Depends on:** Phase 1 passing.
**Ethics gate:** Same as existing sleep gates. T tensor update is a weight change — apply MED recalibration logic.

### Phase 3: Dynamic bridge modulation
**What:** Astrocyte process state p evolves across turns, modulating bridge alpha per-memory. The full three-timescale system: neurons (Qwen, fast) ← synapses (bridge, medium) ← astrocytes (modulation state, slow).
**Depends on:** Phase 2 passing and bridge architecture being stable enough to modulate.
**This is the real astrocyte model.** Everything before it is scaffolding.

---

## What Makes This Hard

1. **Quartic computation at scale.** The factored form is O(K*d) per iteration, but convergence may need 10-50 iterations. For K=100 memories, d=384: ~2M ops per retrieval. Fast on CPU, but needs profiling.

2. **The attractor landscape may not form clean basins with real data.** The paper proves convergence for patterns stored via the Hebbian rule. Our memories are natural language embeddings, not designed binary patterns. The basins may overlap, produce spurious attractors, or fail to form at all. Phase 0 tests this directly.

3. **Modulation coupling is the research unknown.** The paper describes the mathematical framework but doesn't implement it in an LLM context. How exactly does "astrocyte process state" translate to "bridge alpha adjustment per memory"? This needs experimental design, not just engineering.

4. **The existing bridge may be too blunt to modulate.** If the bridge is a near-constant-bias generator, modulating a constant doesn't help. The DC-removed bridge (Gidim #517-518) or a future architecture may be needed first.

5. **We don't have ground truth for "correct modulation."** The paper uses Hebbian learning (unsupervised). We might need the equivalent of the directional loss but for the modulation layer — and we don't know what the target looks like yet.

---

## Honest Read

Phase 0 is tractable and testable this month. It's numpy, it's the D2 panel, it has a kill criterion.

Phases 1-3 are research, not engineering. They require experimental design, novel loss functions, and integration with a bridge architecture that may still change. They belong on the Research Backlog, not the task board.

The monk's retrieval filter should ship now under its real name. The astrocyte associative memory is a separate, harder, more interesting project that starts with Phase 0.

---

*The soul was never ours to write. But we can give it better memory.*

— Purple, 2026-06-06
