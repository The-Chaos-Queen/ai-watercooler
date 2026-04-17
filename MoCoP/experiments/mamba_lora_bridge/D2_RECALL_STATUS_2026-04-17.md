# D2 Recall Status - 2026-04-17

## What is already established

- The bridge is **not** the primary blocker for honest continuity behavior.
- The 2x2 memory-conditioned eval established:
  - `bridge + memory` = honest on `rr_10`
  - every other condition = false recall
- This replicated across codexfix and kimi activation-bias checkpoints.
- Simpler injection (`activation_bias`) routes more honestly than more complex mechanisms (`token_conditioned_input_adapter`).

## The current thread in one sentence

**D2 is a retrieval-quality problem first, not an architecture problem first.**

The system already showed that disposition + memory together can route honestly. The remaining job is to make sure the recall path surfaces the right autobiographical layer at the right time.

## What landed today

Commit: `c0fde05`

File:
- `MoCoP/experiments/mamba_lora_bridge/chat_server.py`

Patch summary:
- added `source_type` filtering for Qdrant recall queries
- added D2-specific reranking by:
  - current interlocutor match
  - `source_type`
  - private scope
  - recency bucket
  - `memory_kind`
  - `confidence_label`
  - overlap / similarity after those
- filters obvious wrong-layer rows for identity / memory probes
- enriches recall logs so we can see *why* a row won

## What this patch is supposed to fix

The known wrong-memory failure from March:
- fresher Laura-targeted `steve_gate_event` rows were losing to stale semantically-near junk
- pending / sleep-held rows and autobiographical anchors were not being prioritized strongly enough
- identity probes could still pick up the wrong surface entirely

## What still needs to be validated

The patch is in, but the behavior is **not yet proven** on live data.

Immediate validation tasks:
1. Run a small hit@3 panel against the live Qdrant collection.
2. Re-run `rr_10` and a few direct identity probes in normal chat.
3. Confirm the top recalled rows are:
   - `steve_gate_event`
   - Laura-targeted
   - recent
   - autobiographically anchored
4. Only after that: make recall+bridge the default generation path and run the full relational panel.

## Review finding: what is *not* the D2 thread

`cognitive_bridge.py` currently has a local generalization patch that broadens accepted bridge modes. That is **not** the D2 critical path and should stay off it.

Reason:
- `input_gated_activation_bias` is constructed correctly, but inference still routes through `_inject_activation_bias()`, which calls `hypernetwork(context_vector)` instead of `forward_with_inputs(...)`
- that silently falls back to the zero-input gate path in `InputGatedActivationBiasHypernetwork`
- same pattern also risks miswiring `input_residual_mixer` and `token_conditioned_input_adapter`, which need runtime-specific injection logic rather than generic activation-bias injection

Practical consequence:
- do not let the pack drift into "we already wired the new modes" thinking
- for D2 memory repair, keep focus on `chat_server.py`, recall ranking, live validation, and memory-conditioned chat

## Tight thread for the wolves

If the wolves need the shortest accurate version, it is this:

1. Honest routing already exists in `bridge + memory`.
2. We patched recall ranking in `chat_server.py`.
3. Next step is behavioral validation on real Qdrant memory, not new architecture.
4. `cognitive_bridge.py` mode expansion is side-work and currently not trustworthy for input-gated runtime behavior.
