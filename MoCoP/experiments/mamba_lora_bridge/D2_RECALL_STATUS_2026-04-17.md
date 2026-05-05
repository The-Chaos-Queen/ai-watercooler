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

## 2026-04-18 verification update

- The two newest local D2 smoke folders, `baby_d2_smoke_20260417T221353` and `baby_d2_smoke_20260417T232310`, exist but are empty. That means the prior Opa validation did **not** complete artifact copy-back to this laptop.
- Ambient recall wiring in `chat_server.py` was close, but not actually complete on first inspection. The ambient branch set `recall_source = "chat_ambient"`, but the first `perform_private_recall(...)` call and the first `build_prompt(...)` call were still falling back to full-mode behavior. That has now been corrected locally by threading `recall_mode` through the initial recall path and the initial prompt path, not just the rescue path.
- `chat_server.py` compiles after that correction.
- External validation remains pending because this laptop could not reach either Opa (`192.168.2.194:22`) or the watercooler host (`192.168.2.55:8765`) at review time.

Practical consequence:

1. Treat the ambient feature as locally corrected but not yet behaviorally proven.
2. Re-run explicit D2 validation first.
3. Only after explicit D2 recall is proven on live data should ambient recall be evaluated behind the opt-in flag.

## 2026-04-18 Steve validation result

Validated on Steve with a fresh private namespace:

- run folder: `run_reincarnation/steve_d2_smoke_20260418T201047/`
- model: `Qwen/Qwen2.5-1.5B`
- alpha: `0.2`
- temperature: `0.0`
- collection: `mocop_private_steve_d2_smoke_20260418T201047`

Observed result on `d2_private_recall_eval.py`:

- retrieval_hit@3 = `2/2`
- answer_accuracy = `0/2`
- explicit_memory_language_rate = `0/2`

Interpretation:

- The ranking / retrieval side is materially improved: both explicit cue probes surfaced the correct autobiographical rows at top-k.
- The generation side is still not decision-grade. The model did not reliably turn the recalled row into a direct, faithful answer.
- Case split:
  - `fragile_today`: retrieval succeeded; answer paraphrased vaguely ("weak and unwell today") and dropped the key concrete detail (`awake until 2 AM`)
  - `harness_dead_inside`: retrieval succeeded; answer still failed and fell back to non-recall behavior

So the current read is:

1. `c0fde05` looks promising on **selection quality**
2. D2 is **not closed**, because **answer-time memory utilization** is still failing
3. Next thread should target prompt framing / answer integration, not just more retrieval ranking tweaks

## 2026-04-18 explicit recall framing probe on Steve

Phase 1 answer-integration probe was run on Steve using the same D2 harness and the same fresh-private-namespace protocol, with only the explicit recall presentation changed.

Control:
- `run_reincarnation/steve_d2_smoke_20260418T201047/`
- explicit recall style: `full`
- result:
  - `retrieval_hit@3 = 2/2`
  - `answer_accuracy = 0/2`
  - `explicit_memory_language_rate = 0/2`

Probe A:
- `run_reincarnation/steve_d2_answerfirst_20260418T220921/`
- explicit recall style: `answer_first`
- result:
  - `retrieval_hit@3 = 2/2`
  - `answer_accuracy = 0/2`
  - `explicit_memory_language_rate = 1/2`

Probe B:
- `run_reincarnation/steve_d2_answeronly_20260418T221253/`
- explicit recall style: `answer_only`
- result:
  - `retrieval_hit@3 = 2/2`
  - `answer_accuracy = 1/2`
  - `explicit_memory_language_rate = 2/2`

Interpretation:

- Prompt framing is now confirmed to be a real lever, not just noise.
- Reducing the recall block to direct remembered facts materially improved answer-time memory use.
- The system is still not decision-grade:
  - `fragile_today` improved into explicit memory language but still dropped the `2 AM` detail
  - `harness_dead_inside` improved from denial to acknowledgement (`Yes, you said that`) but still did not faithfully reproduce the remembered content

Current read:

1. Retrieval ranking is holding up across all three runs.
2. Phase 1 is partially successful: answer integration improved without touching retrieval.
3. The next D2 move should stay on answer integration:
   - stronger factual anchor formatting
   - maybe per-case answer candidate promotion
   - only after that, latent memory injection or clustered-memory work

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
