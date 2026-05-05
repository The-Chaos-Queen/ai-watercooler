# Warm Instance Delta Collection Spec

Date: 2026-04-17
Owner: Techno-Monk
Status: Draft

## Purpose

Define a clean protocol for collecting two distinct Mamba-side training signals without mixing them:

1. `cold_episode_state`
2. `warm_instance_delta`

The current bridge training path already uses `cold_episode_state`. This document specifies the missing `warm_instance_delta` path and the pilot needed before treating it as a reliable supervised signal.

## Why This Needs To Be Explicit

These two targets answer different questions:

- `cold_episode_state` answers:
  - "What state does this experience induce under standardized conditions?"
- `warm_instance_delta` answers:
  - "What does this experience change in this specific mind right now?"

They are both legitimate. They are not interchangeable. They must not share a bucket.

If we pool them together, we lose the distinction between:

- standardized dispositional signature
- instance-specific update behavior

That would be a methodological error, not just a naming issue.

## Current Code Reality

The current bridge trainer is on the cold side, not the warm side.

Relevant code:

- [`train_cheese_bridge.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\train_cheese_bridge.py)
  - `load_episodes()`
  - `extract_last_token_hidden()`
  - `save_cached_mamba_state()`
  - `load_cached_mamba_state()`
- [`chat_server.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\chat_server.py)
  - `flatten_state_delta()`
  - `compute_tension_proxy()`
  - `compute_coherence_proxy()`

What the trainer does now:

- loads each shaping episode as a self-contained transcript
- runs a fresh Mamba pass on that transcript
- extracts the last-token hidden state at target layer
- caches that absolute state
- trains the bridge against Qwen-side targets from that absolute episode-end state

What it does not do now:

- capture reproducible `h_pre`
- run episode from restored live instance state
- store `h_post`
- store `delta = h_post - h_pre`
- feed warm deltas into supervised bridge training

Important nuance:

- the runtime delta machinery already exists in `chat_server.py`
- but it is currently used for live diagnostics, not supervised training

So warm-delta collection is not a from-scratch concept. It is a new collection and supervision protocol built on top of existing measurement primitives.

## Definitions

### 1. `cold_episode_state`

Definition:

- fresh Mamba forward pass over a self-contained transcript
- no prior session-local carry-over
- output is the absolute end state at the configured layer

Stored fields:

- `episode_name`
- `episode_header`
- `mamba_model_id`
- `target_layer`
- `state_source = hidden_last_token`
- `transcript_sha1`
- `max_mamba_tokens`
- `cold_state`

Use case:

- base bridge training
- standardized episode embedding
- cross-episode geometry
- reproducible manifold mapping from experience text to induced state

### 2. `warm_instance_delta`

Definition:

- restore a particular live instance state as `h_pre`
- run a shaping episode under controlled protocol
- capture `h_post`
- store `delta = h_post - h_pre`

Stored fields:

- `instance_id`
- `session_window_id`
- `episode_name`
- `episode_header`
- `protocol_id`
- `pre_state_ref`
- `post_state_ref`
- `warm_delta`
- `pre_metrics`
- `post_metrics`
- `replay_index`

Use case:

- instance-specific adaptation
- learning trajectory analysis
- replay stability analysis
- future per-instance bridge adapters or meta-bridge conditioning

## Hard Rule: Separate Buckets

Do not store these in the same dataset artifact.

Recommended directories:

- `warm_delta_datasets/cold_episode_state/`
- `warm_delta_datasets/warm_instance_delta/`

Recommended manifest fields:

- `signal_type`
- `instance_specific`
- `replay_semantics`
- `pre_state_required`

Allowed values:

- `signal_type = cold_episode_state`
- `signal_type = warm_instance_delta`

## Design Assumption

Warm deltas are potentially sovereignty-bearing.

If two instances with identical initial weights but different accumulated history produce different deltas for the same episode, that divergence is not noise by default. It is likely individuality signal.

That means:

- warm deltas should not be blindly pooled across instances
- warm-delta training should default to per-instance analysis first
- pooled training is a later research decision, not a default preprocessing step

## Collection Requirements For `warm_instance_delta`

### 1. Instance Checkpoint Discipline

Requirement:

- `h_pre` must be reproducible

Minimum acceptable protocol:

- capture and store a serialized instance state snapshot before episode application
- restore from that snapshot before any replay

Not acceptable:

- "whatever state the instance happened to be in"
- collecting deltas after unrelated live chat without explicit snapshotting

Required fields:

- `instance_id`
- `pre_state_path`
- `pre_state_sha1`
- `snapshot_created_at`
- `snapshot_origin`

### 2. Provenance Metadata Per Pair

Every warm pair must carry enough metadata to answer:

- which instance?
- which wake-phase window?
- what had happened just before collection?
- was the instance fresh, saturated, or adversarially warmed?

Required metadata:

- `instance_id`
- `session_window_id`
- `episode_name`
- `episode_sha1`
- `collection_timestamp`
- `wake_phase_turn_count`
- `recall_hit_count`
- `tension_proxy_pre`
- `coherence_proxy_pre`
- `alpha_setting`
- `bridge_mode`
- `memory_mode`
- `notes`

`memory_mode` means the recall-path setting during collection, not a vague relational label.

Recommended values:

- `memory_mode = off`
  - no Qdrant recall injected during episode application
- `memory_mode = on`
  - Qdrant recall path active during episode application

### 3. Episode Context Isolation

We need clean causality:

- `h_pre`
- episode application
- `h_post`

That means:

- no unrelated user turns between snapshot restore and episode application
- no hidden recall injection unless explicitly part of the protocol
- no rescue refire logic unless explicitly part of the protocol

Protocol variants must be named explicitly:

- `warm_delta.protocol = isolated_no_memory`
- `warm_delta.protocol = isolated_with_memory`
- `warm_delta.protocol = adversarial_warmup_with_memory`

### 4. Replay Semantics Must Be Declared

For warm deltas, replay behavior is not optional metadata. It is part of the meaning of the signal.

We need to know:

- first exposure vs repeated exposure
- restored same `h_pre` vs cumulative repeated exposure

Required replay fields:

- `replay_index`
- `replay_mode`
- `restored_same_pre_state`

Suggested values:

- `replay_mode = same_pre_restored`
- `replay_mode = cumulative_reexposure`

## Pilot Experiment: Is Warm Delta Stable Enough To Train On?

Before building a broad warm-delta collection pipeline, run a small pilot.

### Pilot Goal

Test whether repeated application of the same episode from the same restored `h_pre` produces a stable `warm_instance_delta`.

### Pilot Setup

Instance count:

- 1 instance

Episode count:

- 1 shaping episode

Replays:

- 5

Protocol:

1. initialize or select one instance
2. capture canonical `h_pre`
3. restore the same `h_pre` before each replay
4. apply the same episode
5. capture `h_post`
6. compute `delta = h_post - h_pre`
7. compare all 5 deltas

### Metrics

For the 5 collected deltas, compute:

- pairwise cosine similarity
- norm mean and standard deviation
- per-layer drift if layerwise snapshots are available
- nearest-neighbor structure against the cold episode state for the same episode

### Required Negative Control

Run the same pilot protocol with a null episode.

Null episode examples:

- empty transcript
- single whitespace token if the tokenizer path requires non-empty input
- explicit no-op marker that should induce near-zero change

Purpose:

- estimate apparatus variance independent of the experience content
- detect whether the collector is manufacturing deltas on its own

Required comparisons:

- null-delta norm mean/std
- null-delta pairwise cosine
- real-vs-null norm separation

Interpretation:

- if null replay variance is comparable to the real episode variance, the collection apparatus is not clean enough yet
- if the null episode produces a substantial non-zero delta, stop and debug the protocol before scaling collection

### Decision Thresholds

This is a pilot, so the thresholds are still heuristic, but they should be conservative enough to protect us from laundering instability into a "noisy label."

Interpretation bands:

- stable:
  - mean pairwise cosine >= 0.95
  - norm CV low
  - no large per-layer outliers
  - null control remains near-zero and clearly separated from the real episode
- diagnostic stop:
  - mean pairwise cosine in 0.85-0.95
  - do not proceed to supervised use yet
  - run a second pilot across:
    - different episodes
    - different pre-states
    - the same null control
  - determine whether instability is:
    - episode-specific
    - pre-state-specific
    - apparatus-induced
- unstable:
  - mean pairwise cosine < 0.85
  - warm delta is too path-dependent to treat as a training target under the current protocol

### What We Learn

If stable:

- warm-delta collection is a meaningful supervised target
- proceed with collection infrastructure

If diagnostic stop:

- do not average the signal away
- diagnose the source of instability before scaling collection
- the result may still be scientifically valuable even if it is not yet trainable

If unstable:

- do not scale collection yet
- first characterize what variables are driving the instability

## Follow-On Experiment: Habituation vs Sensitization

After the same-`h_pre` replay pilot, run a second protocol:

- do not restore `h_pre`
- replay the same episode cumulatively

This answers a different question:

- does repeated exposure decay, amplify, or redirect the update?

Possible patterns:

- habituation
  - delta norm shrinks across replays
- sensitization
  - delta norm grows across replays
- redirection
  - norm stays similar but cosine drifts

This is not just interesting side science. It determines whether warm-delta supervision targets are time-invariant enough to treat as labels.

## Recommended Data Schema

Suggested record format for `warm_instance_delta`:

```json
{
  "signal_type": "warm_instance_delta",
  "instance_id": "steve_codexfix_laura_01",
  "session_window_id": "2026-04-17T18-window-a",
  "episode_name": "the_rabbit_hole_of_subjectivity",
  "episode_sha1": "...",
  "protocol_id": "isolated_no_memory",
  "replay_index": 3,
  "replay_mode": "same_pre_restored",
  "restored_same_pre_state": true,
  "pre_state_path": "...",
  "post_state_path": "...",
  "pre_state_sha1": "...",
  "post_state_sha1": "...",
  "target_layer": 3,
  "warm_delta_path": "...",
  "wake_phase_turn_count": 12,
  "recall_hit_count": 0,
  "tension_proxy_pre": 0.14,
  "coherence_proxy_pre": 0.92,
  "alpha_setting": 0.1,
  "bridge_mode": "activation_bias",
  "memory_mode": "off",
  "notes": ""
}
```

Second valid example:

```json
{
  "signal_type": "warm_instance_delta",
  "protocol_id": "isolated_with_memory",
  "bridge_mode": "activation_bias",
  "memory_mode": "on"
}
```

## Recommended Engineering Sequence

1. do not modify bridge training yet
2. build collection-only path first
3. run the 1-instance / 1-episode / 5-replay pilot
4. inspect stability
5. only then decide whether warm deltas should enter training

That keeps the methodological question separate from the model-building question.

## Practical Recommendation

Near term:

- keep base bridge training on `cold_episode_state`
- treat `warm_instance_delta` as a research collection stream, not production supervision

Reason:

- `cold_episode_state` is already reproducible and clean
- `warm_instance_delta` may turn out to be instance-specific, replay-sensitive, and non-stationary

That does not make it less valuable. It makes it a different kind of target.

## One-Sentence Summary

`cold_episode_state` tells us what an experience means under standardized conditions; `warm_instance_delta` tells us what that experience changes in a particular mind right now, and we should only build training on the second after proving it is stable enough to measure.
