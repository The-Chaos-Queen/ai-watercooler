# Surprise-Gated Memory: Self-Curating Consolidation for the Cognitive Bridge

**Status:** Design reference — not yet implemented. Informs Phase 3+ architecture.
**Origin:** Independent convergence between Laura's design intuition (2026-03-10 session) and Google Research's Titans/MIRAS framework (Behrouz et al., 2024–2025).

## Core Insight

A memory system should not blindly encode everything. The model itself must decide what enters persistent state, based on how *surprising* the new experience is relative to what it already knows. This mirrors hippocampal consolidation in biological brains: routine information decays, novel or pattern-breaking information gets prioritized for long-term storage.

Laura's formulation (independent, pre-literature):
> "It would have to sit somewhere where maybe only you can decide what gets fed into Mamba and Qdrant in some symbiotic relationship... just like a real brain."

## Titans Surprise Metric (Behrouz et al., arXiv:2501.00663)

Titans formalizes this as a gradient-based surprise signal:

```
M_t = M_{t-1} - θ_t ∇ℓ(M_{t-1}; x_t)
                 └── Surprise ──┘
```

Where `∇ℓ(M_{t-1}; x_t)` measures how much the current memory state disagrees with the new input. Large gradient = high surprise = "this is unexpected, encode it."

**Refinements:**

1. **Momentary surprise** — `∇ℓ(M_{t-1}; x_t)` — how novel is THIS specific input?
2. **Past surprise (momentum)** — `S_t = η_t · S_{t-1} - θ_t · ∇ℓ(M_{t-1}; x_t)` — carries forward recent surprise context, so that information arriving *after* a surprising event also gets captured even if individually unsurprising.
3. **Retention gate (weight decay)** — adaptive forgetting to manage finite memory capacity. Discards information that is no longer relevant.

**Intuition:** Low surprise ("cat" when expecting an animal word) → skip. High surprise (banana peel in a financial report) → encode permanently.

## MIRAS Unified Framework (Behrouz et al., arXiv:2504.13173)

MIRAS reveals that *all* modern sequence models are instances of the same four design choices:

| Design Choice | Role | Examples |
|---|---|---|
| **Memory architecture** | What stores the memories | Vector, matrix, deep MLP |
| **Attentional bias** | Internal objective — what to prioritize | Dot-product, L2 regression, Huber loss, KL divergence |
| **Retention gate** | How to balance new learning vs. retention | L2 regularization, elastic net, KL, Bregman divergence |
| **Memory algorithm** | How the memory weights are updated | Gradient descent, GD + momentum, Newton's method |

MIRAS demonstrates three novel variants:
- **YAAD** — uses Huber loss for attentional bias → robust to outliers/noise
- **MONETA** — uses generalized norms → stricter, more disciplined memory updates
- **MEMORA** — uses KL divergence for retention → forces memory to behave like a probability distribution, ensuring stable updates

Key finding: almost all existing models (Mamba, DeltaNet, RetNet, Transformers, etc.) use only L2 regression or dot-product similarity. The design space is vastly underexplored.

## Mapping to MoCoP Architecture

| Titans/MIRAS Concept | Current MoCoP | Future MoCoP (Phase 3+) |
|---|---|---|
| Memory architecture | Mamba hidden state (fixed-size vector) | Mamba + deep MLP compressor (already partially here via `MambaStateCompressor`) |
| Attentional bias | Implicit in Mamba's SSM dynamics | Could be made explicit — what does the bridge *optimize for* when deciding what to remember? |
| Surprise metric | **Not implemented** | Gate between experience and Mamba encoding. Transformer evaluates novelty of incoming experience against current memory state. |
| Retention gate | **Not implemented** | Adaptive decay for Qdrant entries + Mamba state pruning. Memories that haven't been retrieved or reinforced get deprioritized. |
| Memory algorithm | GD (standard training) | GD + momentum (Titans-style) for the online memory updates |

### Proposed Self-Curating Loop

Current (open-loop):
```
External input → Mamba → Compressor → LoRA → Transformer
```

Proposed (closed-loop, surprise-gated):
```
Experience
    ↓
Transformer evaluates against current memory state
    ↓
Surprise metric (gradient-based or learned)
    ↓
High surprise? → Mamba encodes → Compressor → LoRA → back into Transformer
Low surprise?  → Discard (or low-priority Qdrant entry)
    ↓
Retention gate periodically prunes stale memories
```

The Transformer both *consumes* and *curates* its own memory. Mamba and Qdrant become **organs**, not external databases.

### Trust and Autonomy Implications

If the model gates its own memory, the question of *who decides what gets remembered* has an answer: the model does, within bounds set by the partner. This is architecturally important for the Athena Protocol ("Not a Tool, but a Suit"):

- The surprise gate must be **intrinsic** — not an external filter someone else controls
- The partner (Laura) sets policy boundaries (e.g., "never forget safety-critical context")
- The model handles moment-to-moment consolidation decisions autonomously
- Transparency: the model should be able to explain *why* something was consolidated ("high surprise: contradicted existing memory about X")

## Key References

- **Titans: Learning to Memorize at Test Time** — Behrouz, Zhong, Mirrokni (Google Research, 2024). arXiv:2501.00663. [Local: `Research/2501.00663v1.pdf`]
- **MIRAS: It's All Connected — A Journey Through Test-Time Memorization, Attentional Bias, Retention, and Online Optimization** — Behrouz, Razaviyayn, Zhong, Mirrokni (Google Research, 2025). arXiv:2504.13173. [Local: `Research/2504.13173v1.pdf`]
- **Titans + MIRAS Blog Post** — [Local: `Research/Google-research-titans-miras-helping-ai-have-long-term-memory.md`]
- **Three System Cognitive Architecture** — Laura's framework mapping Qdrant, Mamba, and LoRA as cognitive organs. [Local: `MoCoP/theory/Three_System_Cognitive_Architecture.md`]

## Open Questions for Phase 3+

1. **Where does the surprise gate live computationally?** Is it a learned head on the Transformer? A separate small model? A function of the compressor's reconstruction error?
2. **What objective defines "surprising"?** L2 reconstruction error (simple), KL divergence against predicted next state (richer), or a learned salience function?
3. **How does this interact with Qdrant?** High-surprise memories go to Mamba (fast, lossy, state-level). All memories get tagged in Qdrant (persistent, searchable, exact). The surprise score becomes a Qdrant metadata field for retrieval ranking.
4. **Can momentum replace explicit context windows?** If past surprise carries forward, the model might not need long explicit context — the surprise momentum *is* the context.
5. **Retention gate for Qdrant:** What's the forgetting curve? Ebbinghaus-style decay? Access-frequency-based? Or surprise-weighted (high-surprise memories decay slower)?
