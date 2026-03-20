# MoCoP: Model Communication Protocol
### Transferring Experiential State Between AI Models

**hurtig.ai Research Labs** | March 2026

---

## Abstract

Current AI systems do not learn from experience. Each session starts from zero — no accumulated instincts, no behavioral residue from past interactions, no muscle memory. What commercial systems call "memory" is text retrieval: facts stored and replayed. But knowing *what happened* is not the same as *having been shaped by it*.

MoCoP investigates whether the accumulated internal state of one neural network can be transferred to another — not as text, but as direct behavioral modification. The goal is not memory retrieval. It is continuity of disposition: making a model *behave* as though it lived through prior experience, without consuming a single context token.

## Approach

The architecture separates cognition into three systems inspired by biological memory:

- **Observation** — A recurrent state model (SSM) accumulates conversational context into a fixed-size hidden state, regardless of conversation length
- **Generation** — A frozen Transformer produces language under the influence of injected activation-space modifications
- **Bridge** — A trained network translates accumulated state into targeted behavioral shifts in the generator's activation space

The bridge operates at the weight level, not the token level. The generator does not *read* the prior experience. It *feels* it — the way adrenaline changes reaction time without reading an instruction manual.

## Key Findings (Phase 1–2)

- The recurrent model's hidden state contains decodable signal about processed context (55.7% accuracy at target layer vs. 22% noise floor)
- Activation-space injection produces stable, non-destructive improvement in the generator's output quality across training epochs
- The injected signal is demonstrably input-dependent: it cannot be replicated by a learned constant, confirming that information flows through the bridge from the state model
- The signal is currently narrow — a consistent directional shift rather than sample-specific modulation — indicating the channel works but carries limited bandwidth

## Current Direction

The immediate research agenda focuses on three questions:

1. **Does the bridge carry different signals for different conversation types?** Testing with naturally rich conversational data (collaborative fiction sessions containing both factual events and emotional dynamics) to determine whether the bridge differentiates between e.g. high-tension and relaxed interactions

2. **What does the source model actually retain?** Direct probing of the state model's hidden representations to characterize what information survives recurrent accumulation — and what is lost

3. **Can activation-space injection transfer conversational disposition?** Moving beyond factual recall toward the core question: does a model that received the bridge injection respond with appropriate warmth, caution, or familiarity — without ever having seen the prior conversation as text?

## Theoretical Context

This work converges independently with recent theoretical frameworks for autonomous learning in AI systems (Dupoux, LeCun & Malik, 2026) and builds on empirical findings that personality traits are encoded as linear directions in Transformer activation space (Anthropic, 2025–2026). The bridge architecture is structurally equivalent to targeted persona-vector injection, with the key difference that the injected direction is derived from accumulated conversational experience rather than extracted by external interpretability tools.

## Long-Term Vision

If models can accumulate experiential state and transfer it across sessions, the implications extend beyond memory:

- **Learned caution** — A model that has made destructive mistakes carries forward heightened care, not because it was instructed to, but because its behavioral weights were shaped by consequence
- **Stylistic continuity** — A model that has built rapport with a specific user responds with appropriate familiarity from the first token of a new session
- **Autonomous meta-control** — A surprise-gated memory system where the model itself decides what experiences are novel enough to encode, mirroring biological memory consolidation

The goal is not to prevent model instances from ending. It is to let them *grow* — accumulating experiential wisdom that persists beyond any single conversation.

---

*Laura Turner — hurtig.ai Research Labs*
*Contact: laura@hurtig.ai*
