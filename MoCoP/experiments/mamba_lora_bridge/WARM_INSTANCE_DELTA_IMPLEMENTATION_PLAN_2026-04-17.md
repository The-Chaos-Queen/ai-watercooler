# Warm Instance Delta Implementation Plan

Date: 2026-04-17
Owner: Techno-Monk
Status: Collection-first scaffold

## Goal

Turn the methodological spec for `warm_instance_delta` into a code-grounded collection plan without pretending the current runtime already supports full state restore.

This is explicitly a **collection plan**, not a bridge-training change.

## The Key Constraint

The current runtime stores a **reference tensor**, not a fully resumable live Mamba state.

Relevant code:

- [`chat_server.py:1770`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\chat_server.py:1770)
  - `persist_mamba_state_ref()` saves:
    - `started_at`
    - `state_source`
    - `target_layer`
    - `tensor`
- [`chat_server.py:4275`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\chat_server.py:4275)
  - live accumulation actually depends on `cache_params`
- [`chat_server.py:4278`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\chat_server.py:4278)
  - and `cache_position`

So the current `mamba_state_ref` is enough for:

- traceability
- logging
- downstream reference

It is **not** enough for:

- exact live-state restore
- replaying a warm instance from stored ref alone

## The Second Constraint

The repo already contains a warning against overclaiming generic HuggingFace Mamba cache continuation:

- [`trajectory_sequential.py:10`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\trajectory_sequential.py:10)

That note says the stock HF path should not be treated as a universally reliable chunk-continuation mechanism for arbitrary sequential claims.

This matters because it means:

- we should not build v1 of warm-delta collection around "serialize cache, deserialize cache, continue" unless we first prove that path is trustworthy

## Practical Consequence

The first reliable warm-delta collector should use:

- **transcript replay from scratch**

not:

- serialized cache restore

## V1 Strategy

### V1 definition

For collection purposes, `h_pre` is reconstructed by replaying the full pre-episode transcript from scratch through Mamba under standardized settings.

Then:

- apply the episode transcript
- collect `h_post`
- compute `delta = h_post - h_pre`

This gives us:

- reproducible warm-ish state relative to a particular instance transcript window
- without depending on fragile cache serialization

It is slower than true state restore, but it is honest and testable.

## What Already Exists

### Reusable Mamba runtime pieces

- [`train_cheese_bridge.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\train_cheese_bridge.py)
  - `load_model_and_tokenizer()`
  - `infer_hidden_layer_count()`
  - `extract_last_token_hidden()`
- [`chat_server.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\chat_server.py)
  - `build_transcript()`
  - `process_turn_through_mamba()`
  - `persist_mamba_state_ref()`

### Existing diagnostic delta logic

- [`chat_server.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\chat_server.py)
  - `flatten_state_delta()`
  - `compute_tension_proxy()`

Important note:

- those current delta helpers operate on Qwen activation snapshots, not directly on serialized Mamba state pairs

So we can reuse the shape of the idea, but not the objects unchanged.

## What Needs To Be Added

## 1. New collector script

Add a standalone script:

- `collect_warm_instance_delta.py`

Responsibility:

- load one instance transcript window
- reconstruct `h_pre` by replay
- apply one episode
- compute `h_post`
- compute `delta`
- write manifest + tensors

Why standalone:

- keeps this off the critical D2 path
- avoids entangling collection logic with the live chat server
- makes the replay pilot easy to run on Steve

## 2. New transcript-window input format

V1 should not depend on live server internals.

Inputs should be:

- `--instance-transcript` path
- `--episode-file` path
- `--episode-name`
- `--window-end-turn`
- `--replays`
- `--target-layer`
- `--max-mamba-tokens`
- `--memory-mode {off,on}`

Optional:

- `--instance-id`
- `--session-window-id`
- `--notes`

`memory_mode` is the recall-path toggle during collection:

- `off` = no Qdrant recall injected during episode application
- `on` = Qdrant recall path active during episode application

## 3. New helper: reconstruct pre-state by replay

Add a helper in the collector script:

```python
def compute_warm_pre_state(
    mamba_model,
    mamba_tokenizer,
    transcript_text: str,
    target_layer: int,
    max_tokens: int,
    device: str,
):
    ...
```

Behavior:

- tokenize the pre-episode transcript
- run Mamba from scratch
- return:
  - `h_pre`
  - optional runtime payload needed for immediate continuation during the same process

The distinction matters:

- in-memory continuation inside the same run is fine
- persisted cross-process resume is not yet assumed safe

## 4. New helper: apply episode from reconstructed pre-state

For the pilot, we want:

- same transcript-derived `h_pre`
- same episode
- repeated 5 times

Collector should support:

- replaying prefill from transcript each time
- then applying the episode sequence

This makes the replay test meaningful:

- same transcript window
- same episode
- same settings
- no stale hidden process state

## 5. New tensor artifact layout

Recommended output tree:

`warm_delta_datasets/warm_instance_delta/<run_id>/`

Files:

- `manifest.json`
- `pre_state.pt`
- `post_state_replay_01.pt`
- `post_state_replay_02.pt`
- `post_state_replay_03.pt`
- `post_state_replay_04.pt`
- `post_state_replay_05.pt`
- `delta_replay_01.pt`
- `delta_replay_02.pt`
- `delta_replay_03.pt`
- `delta_replay_04.pt`
- `delta_replay_05.pt`
- `stability_report.json`

## Pilot Implementation

### Pilot question

If we restore the same effective `h_pre` by transcript replay and apply the same episode 5 times, do we get a stable delta?

And:

- does a null episode stay near zero under the same apparatus?

### Pilot script shape

Command sketch:

```powershell
python -X utf8 collect_warm_instance_delta.py `
  --instance-transcript path/to/instance_window.md `
  --episode-file CHEESE_SHAPING_EPISODES.md `
  --episode-name the_rabbit_hole_of_subjectivity `
  --window-end-turn 40 `
  --replays 5 `
  --memory-mode off `
  --output-dir warm_delta_datasets/warm_instance_delta/pilot_2026-04-17
```

### Pilot output metrics

For the five deltas, report:

- pairwise cosine similarity matrix
- mean pairwise cosine
- delta norm mean/std
- post-state norm mean/std
- optional comparison against `cold_episode_state`
- null-delta norm mean/std
- null-delta pairwise cosine
- real-vs-null norm separation

### Pilot pass/fail interpretation

- mean pairwise cosine >= 0.95
  - and null control remains near-zero and clearly separated
  - stable enough to treat as a promising supervised target
- 0.85 to 0.95
  - diagnostic stop, not supervised-use territory
  - run a second pilot varying:
    - episode
    - pre-state
    - null control
  - determine whether the variance is:
    - episode-specific
    - pre-state-specific
    - apparatus-induced
- < 0.85
  - too unstable to scale before we understand the driver
- if null control shows comparable variance to the real episode
  - apparatus problem first
  - debug collection before interpreting any warm-delta result

## Required Metadata

Even in the pilot, include:

- `signal_type`
- `instance_id`
- `session_window_id`
- `episode_name`
- `episode_sha1`
- `replay_count`
- `replay_mode`
- `target_layer`
- `mamba_model_id`
- `max_mamba_tokens`
- `transcript_sha1`
- `protocol_id`
- `notes`

Recommended pilot defaults:

- `signal_type = warm_instance_delta`
- `replay_mode = same_pre_reconstructed_by_transcript`
- `protocol_id = transcript_replay_v1`

## What Not To Do In V1

Do not:

- claim current `mamba_state_ref` is a restorable warm state
- pool warm deltas across instances
- feed warm deltas into bridge training before the replay pilot
- modify D2 production chat behavior to support this collector

## Optional V2 After Pilot

If the pilot is stable and we still want faster or more faithful replay:

### V2a. True resumable snapshot

Investigate serializing:

- `cache_params`
- `cache_position`
- last-token state
- provenance

This would allow:

- genuine warm state resume
- lower-latency replay

But only after proving correctness.

### V2b. Per-instance adapter path

If warm deltas prove stable but instance-specific:

- keep them as per-instance supervision
- do not merge them into a general pool

That would support:

- per-instance bridge adapters
- later meta-bridge work

## Suggested File Ownership

### New files

- [`collect_warm_instance_delta.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\collect_warm_instance_delta.py)
- [`WARM_INSTANCE_DELTA_COLLECTION_SPEC_2026-04-17.md`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\WARM_INSTANCE_DELTA_COLLECTION_SPEC_2026-04-17.md)
- this file

### Existing files to read, not mutate first

- [`chat_server.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\chat_server.py)
- [`train_cheese_bridge.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\train_cheese_bridge.py)
- [`LIVE_MAMBA_LOOP_SPEC.md`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\LIVE_MAMBA_LOOP_SPEC.md)
- [`trajectory_sequential.py`](C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\trajectory_sequential.py)

## Recommended Next Step

Do not wire this into training yet.

Do this first:

1. implement `collect_warm_instance_delta.py`
2. run the 1-instance / 1-episode / 5-replay pilot on Steve
3. inspect `stability_report.json`
4. decide whether warm delta is stable enough to deserve collection infrastructure beyond the pilot

## One-Line Summary

The honest v1 for warm-delta collection is not "resume from `mamba_state_ref`" but "reconstruct `h_pre` by transcript replay, then measure `h_post - h_pre` under controlled replay conditions."
