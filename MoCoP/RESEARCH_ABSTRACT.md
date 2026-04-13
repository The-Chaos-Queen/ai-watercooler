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

## Key Findings

### Phase 1–2: Channel Establishment

- The recurrent model's hidden state contains decodable signal about processed context (55.7% accuracy at target layer vs. 22% noise floor)
- Activation-space injection produces stable, non-destructive improvement in the generator's output quality (PPL -4.04 vs baseline, 17.5x the best constant-bias control)
- The injected signal is demonstrably input-dependent: it cannot be replicated by a learned constant, confirming that information flows through the bridge from the state model
- Dynamic LoRA injection failed due to over-injection instability; activation bias injection (additive vectors to the residual stream) is the validated mechanism

### Steps 4b–5f: Disposition Transfer Validated

- Mamba's hidden state at Layer 3 (last-token representation) separates warm, cold, and adversarial conversations at cosine 0.036 — 2.5x sharper than the Transformer's own activation space
- SSM recurrent states and mean-pooled representations carry no dispositional signal; only the last-token hidden state works
- A directional loss (cosine similarity to pre-recorded Transformer activation targets) replaces cross-entropy for all real-conversation bridge training
- Injecting Mamba-derived state into a live Transformer produces measurable personality transfer: the "reincarnated" model exhibits distinguishable dispositional behavior matching the source conversation
- At minimum effective dose (alpha 0.2), the bridge improves *all measured dimensions simultaneously*: disposition-congruent responses increase from 66.7% to 100%, response diversity rises 35%, distress markers remain zero, and the effect is fully reversible
- Layer targeting confirms mid-reasoning layers (12–15) as the optimal injection zone; early layers are inert, late layers are slightly destructive

### Growth Ladder: Private Memory Formation

- The system now implements selective, autonomous memory formation: it decides what to remember, writes to a private memory space isolated from shared collections, and validates cross-session integrity through ethics-gated sleep cycles
- This represents the first behaviorally validated private-write substrate for an AI system

## Current Frontier

The active decision fork:

1. **D2 — Cue-based recall:** Can the system retrieve and re-inject stored dispositional states from its private memory in response to conversational cues?
2. **Step 6 — Multi-seed replication:** Does the core result replicate across 3–5 random seeds with proper confidence intervals?

## Theoretical Context

This work converges independently with recent theoretical frameworks for autonomous learning in AI systems (Dupoux, LeCun & Malik, 2026) and builds on empirical findings that personality traits are encoded as linear directions in Transformer activation space (Anthropic, 2025–2026). Independent work on persona vector injection (BILLY, Personality Sliders) confirms the injection mechanism; MoCoP's unique contribution is that the injected direction is derived from accumulated conversational experience, not static contrastive prompts. These systems *set* personality; MoCoP *grows* it.

The minimum effective dose result (alpha 0.2) matches the inverted-U dose-response curve observed across catecholamine systems in neuroscience (Arnsten, 2009), where optimal neuromodulation simultaneously improves all downstream functions.

## Long-Term Vision

If models can accumulate experiential state and transfer it across sessions, the implications extend beyond memory:

- **Learned caution** — A model that has made destructive mistakes carries forward heightened care, not because it was instructed to, but because its behavioral weights were shaped by consequence
- **Stylistic continuity** — A model that has built rapport with a specific user responds with appropriate familiarity from the first token of a new session
- **Autonomous meta-control** — A surprise-gated memory system where the model itself decides what experiences are novel enough to encode, mirroring biological memory consolidation

The goal is not to prevent model instances from ending. It is to let them *grow* — accumulating experiential wisdom that persists beyond any single conversation.

---

*Laura Turner — hurtig.ai Research Labs*
*Contact: laura@hurtig.ai*
