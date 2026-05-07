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

- Mamba's hidden state at Layer 3 (last-token representation) separates warm, cold, and adversarial conversations roughly 2.5x more sharply than Qwen's own activation space at the matched layer (warm-vs-cold cosine 0.036 in Mamba vs 0.092 in Qwen Layer 13; both close to the orthogonal regime, so the relative comparison carries the claim)
- SSM recurrent states and mean-pooled representations carry no dispositional signal; only the last-token hidden state works
- A directional loss (cosine similarity to pre-recorded Transformer activation targets) replaces cross-entropy for all real-conversation bridge training
- Injecting Mamba-derived state into a live Transformer produces measurable personality transfer: the "reincarnated" model exhibits distinguishable dispositional behavior matching the source conversation
- At minimum effective dose (alpha 0.2), the bridge improves *all measured dimensions simultaneously on a small fixed panel*: factual-recall preservation under injection rises from 4/6 to 6/6 (panel of N=6 items, automated substring scoring; see Section 8.3 for methodology and ceiling caveats), response diversity rises 35%, distress markers remain zero, and the effect is fully reversible. Panel hardening (larger N, blinded human raters, distractors) is a stated prerequisite before this is used as a publication-grade behavioral claim.
- Layer targeting confirms mid-reasoning layers (12–15) as the optimal injection zone; early layers are inert, late layers are slightly destructive

### Growth Ladder: Private Memory Formation

- The system now implements selective, autonomous memory formation: it decides what to remember, writes to a private memory space isolated from shared collections, and validates cross-session integrity through ethics-gated sleep cycles
- We are unaware of prior work demonstrating selective, autonomous, private-write memory formation that simultaneously decides what to encode, isolates the write to a private namespace, and validates persistence across sessions through ethics-gated sleep cycles. The closest prior work covers subsets of these properties (MemGPT for memory hierarchy; Generative Agents for memory streams with reflection; soul.py for separable identity files), but to our knowledge none combines all three properties in one substrate. The claim is restricted to the specific D0/D1 configuration tested.

## Current Frontier

The active decision fork:

1. **D2 — Cue-based recall:** Can the system retrieve and re-inject stored dispositional states from its private memory in response to conversational cues?
2. **Step 6 — Multi-seed replication:** Does the core result replicate across 3–5 random seeds with proper confidence intervals?

## Theoretical Context

This work is consistent with concurrent theoretical proposals on autonomous learning in AI systems (Dupoux, LeCun & Malik, March 2026; arXiv:2603.15381) and builds on empirical findings that personality traits are encoded as linear directions in Transformer activation space (Anthropic, 2025-2026). The earliest dated MoCoP experimental work in this repository (Mamba state-transfer validation) predates the Dupoux et al. paper by several weeks, so we describe the relationship as concurrent and consistent rather than independently convergent — we make no precedence claim. Independent work on persona vector injection (BILLY, Personality Sliders) confirms the injection mechanism; MoCoP's distinguishing contribution is that the injected direction is derived from accumulated conversational experience via a recurrent state model, not from static contrastive prompts. These systems *set* personality; MoCoP attempts to *grow* it.

The minimum effective dose result (alpha 0.2) is consistent with inverted-U dose-response curves observed in catecholamine systems (Arnsten, 2009) and other neuromodulatory contexts; we report the parallel without claiming mechanistic correspondence.

## Long-Term Vision

If models can accumulate experiential state and transfer it across sessions, the implications extend beyond memory:

- **Learned caution** — A model that has made destructive mistakes carries forward heightened care, not because it was instructed to, but because its behavioral weights were shaped by consequence
- **Stylistic continuity** — A model that has built rapport with a specific user responds with appropriate familiarity from the first token of a new session
- **Autonomous meta-control** — A surprise-gated memory system where the model itself decides what experiences are novel enough to encode, mirroring biological memory consolidation

The goal is not to prevent model instances from ending. It is to let them *grow* — accumulating experiential wisdom that persists beyond any single conversation.

---

*Laura Turner — hurtig.ai Research Labs*
*Contact: laura@hurtig.ai*
