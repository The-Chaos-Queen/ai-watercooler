# Alex Friction World Model v0

## Purpose

This is the smallest useful step toward giving Alex a procedural world-model layer.

The goal is **not** to solve sentience, replace Qdrant, or train a hidden-state adapter yet. The goal is to create a small auditable loop that runs before Qwen generation and says:

> Given the current message, known memories, and learned rules, what friction/tension should shape Alex's next move?

## Why this exists

Qdrant-style recall can store that something happened:

- Laura said pistachio croissants are her favorite.
- OpenRGB probing wedged ML-WS.
- Alex collapsed attribution in a previous conversation.

But recall alone does not make those facts procedural. Alex needs a layer that can turn repeated failures/corrections into active constraints:

- Do not answer a Laura memory as if Opussy said it.
- Do not treat unattributed memory as a personal fact.
- Treat hardware control-plane probes on ML-WS as high-risk.
- Treat user correction as prediction error, not mere conversational flavor.

## Minimal v0

v0 is deliberately boring:

1. Build a `CognitiveState` before generation.
2. Classify the user turn into simple trigger tags.
3. Load active `FrictionRule` records from JSONL.
4. Select rules whose trigger tags match the turn.
5. Render a compact friction context for Qwen or future adapters.
6. Score obvious response violations after a draft in tests/offline mode.

No live behavior changes are required until this standalone module is tested.

## Mathematical shape

Let:

```text
z_t = latent cognitive/world state at turn t
a_t = candidate action/response/tool call
o_t = observation: user message, correction, tool result, failure
E(a_t, z_t) = friction/energy for doing a_t in state z_t
```

The future version chooses or steers actions by:

```text
a_t = argmin_a E(a, z_t)
```

or softly:

```text
π(a | z_t) = softmax(-E(a, z_t))
```

For v0, `E` is not neural. It is a deterministic rule/heuristic score so we can debug it.

## Relation to Mamba and Qwen

- Qwen remains the language surface.
- Mamba remains the gut/endocrine/salience bridge.
- Friction layer adds procedural constraints: what should feel wrong.
- Episodic memory remains evidence, not policy.

Eventually, friction features may steer hidden states:

```text
h_l <- h_l + alpha_mamba * mamba_bias_l + beta_friction * friction_adapter_l(features)
```

But v0 should only create the explicit state/rule substrate.

## Pinductor / POMDP reference

Relevant paper:

- **Learning POMDP World Models from Observations with Language-Model Priors**
- https://arxiv.org/abs/2605.13740

The important idea: use an LLM prior to propose candidate partially-observable world models from observation-action traces, but refine/score them by belief-based likelihood rather than linguistic plausibility alone.

For Alex:

- observations: user messages, corrections, tool results, test failures
- hidden state: speaker identity, task state, uncertainty, unresolved tension
- actions: answer, ask, retrieve, run tool, store memory, abstain
- score: did this candidate world/rule model predict the observed correction/failure?

## Non-goals

- No autonomous self-modification.
- No hidden-state adapter training yet.
- No replacement of Qdrant yet.
- No infinite regenerate loops.
- No claim that this is already a real world model.

## v0 success criteria

- Standalone tests pass.
- Turn classifier activates useful tags for personal recall, preferences, attribution, correction, and hardware/tool risk.
- Rule selection is deterministic and auditable.
- Croissant/provenance examples score attribution collapse as high friction.
- OpenRGB/ML-WS examples activate hardware caution.
- Default live Alex behavior remains unchanged until explicit integration flag is added.
