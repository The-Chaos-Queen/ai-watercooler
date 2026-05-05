# Mamba Long-Trajectory Engine Plan - 2026-04-07

## Problem

The Cassian transcript is about 792k Mamba tokens. A pure tokenwise replay through `state-spaces/mamba-2.8b-hf` is exact, but too slow locally because it calls `model()` once per token from Python.

The local WSL fast-path kernels are now installed and verified, but the Hugging Face cache continuation path is shaped for one-token decoding. It is not a usable arbitrary multi-token chunked recurrence path:

- first chunk can use `selective_scan_fn` and is fast/exact
- later chunks with `cache_params` enter decode mode
- decode mode uses `causal_conv1d_update` and `selective_state_update`
- that path processes only the first token of the new chunk for SSM continuation

So the problem is not "CUDA missing" anymore. The problem is exact continuous multi-token chunk carry.

## Recommendation

Build in this order:

1. Keep a windowed one-pass analyzer for immediate local evidence.
2. Try the original `state-spaces/mamba` CUDA-graph tokenwise route as the first exact long-run candidate.
3. Only patch `selective_scan_fn` with initial state if the original route fails and we deliberately accept kernel engineering.
4. Treat a "custom chunked recurrence" as either approximate windowing or as the same kernel-patch problem in disguise.

## Option A: Windowed One-Pass Analyzer

This is the fastest useful near-term path. It does not preserve lifelong Mamba recurrence across the whole 792k-token transcript, so it must be labeled as windowed/approximate.

Implementation shape:

- tokenize the transcript once
- choose windows around sampled turns or suspected alignment fractures
- run one full forward pass per window
- use a target-layer hook instead of `output_hidden_states=True` for all layers
- collect the last-token state for each sampled turn in the window
- record the window start/end and whether the sample was warmup or measured

Useful defaults:

- window size: 1024-2048 tokens on this laptop
- overlap/warmup: 512-1024 tokens
- target layer: Mamba layer 3, matching the earlier bridge/DFC probes

This answers: "what does the local recent-context trajectory look like around this turn?"

It does not answer: "what is the exact recurrent state after all prior 700k tokens?"

## Option B: Original `state-spaces/mamba` CUDA-Graph Tokenwise Route

This is the best first attempt at an exact full-run engine.

Build steps:

1. Use WSL Debian and `/root/mamba_venv`, not Windows Python.
2. Install or clone the original `state-spaces/mamba` implementation in a separate test path.
3. Prefer an original checkpoint if available, rather than forcing the HF `-hf` checkpoint through key conversion first.
4. Use the original inference-cache/step API instead of Hugging Face `cache_params`.
5. Add a target-layer hook or a small local patch so the runner can record layer states at sample boundaries.
6. Benchmark on `trajectory_sanity_tiny.md`.
7. Compare against the existing HF tokenwise and one-pass references:
   - cosine should be near `0.99999+`
   - sample timing must beat HF tokenwise by enough to matter
8. Only then run a Cassian calibration block.

This answers the exact full-recurrence question if it works.

Main risk:

- checkpoint/API mismatch between original `state-spaces/mamba` and the HF `state-spaces/mamba-2.8b-hf` model
- hidden-state extraction may need a local hook/patch

## Option C: Patch `selective_scan_fn` With Initial State

This is the cleanest mathematical route, but it is the deepest engineering route.

Required changes:

1. Fork or editable-install `mamba-ssm`.
2. Extend the Python API:
   - `selective_scan_fn(..., initial_state=None, return_last_state=True)`
3. Extend the C++/CUDA binding to accept an optional initial state tensor.
4. In the CUDA kernel, initialize the recurrent state from `initial_state` instead of zero when provided.
5. Return the final recurrent state exactly as the current `return_last_state=True` path does.
6. Patch the HF Mamba mixer continuation path:
   - for `cache_params` with `seq_len > 1`, do not enter the one-token decode path
   - use `causal_conv1d_fn(..., initial_states=conv_state, return_final_states=True)` for convolution carry
   - use patched `selective_scan_fn(..., initial_state=ssm_state, return_last_state=True)` for SSM carry
   - update cache with the returned final conv and SSM states
7. Validate against one-pass references before touching Cassian.

This would make true multi-token chunk continuation possible:

- chunk 1: initial state zero
- chunk 2+: initial state from previous chunk
- sample states at turn boundaries

Main risks:

- CUDA extension work is fragile
- Mamba/Mamba2 state layout details matter
- failures may look numerically plausible while still being wrong

This path needs a strict equivalence harness before we trust it.

## Option D: Custom Chunked Recurrence

There are two meanings here:

Approximate:

- run overlapping one-pass windows
- reset state at window boundaries
- label results as local/windowed, not continuous

Exact:

- carry convolution state and SSM state across chunks
- convolution is plausible with existing `causal_conv1d_fn(initial_states=...)`
- SSM still needs a scan kernel that accepts initial state

So exact custom chunking collapses back into Option C unless we accept per-token `selective_state_update`, which recreates the slow Python-loop problem.

## Equivalence Harness

Before any long run, every candidate engine must pass:

1. Tiny fixture: `trajectory_sanity_tiny.md`
2. Short real slice: first few hundred or thousand Cassian tokens
3. Reference engines:
   - HF tokenwise
   - HF one-pass for sequences that fit in memory
4. Metrics:
   - per-sample cosine similarity
   - final-state cosine similarity
   - L2 drift
   - runtime tokens/sec
   - peak VRAM

Trust threshold:

- cosine `>= 0.99999` for exact engines on small references
- lower thresholds allowed only for explicitly labeled approximate/windowed probes

## Decision

Do not spend more time on Hugging Face `cache_params` as if it supports arbitrary multi-token chunks. The local code path says it does not.

The practical path is:

1. build/use a windowed one-pass analyzer now for local fracture evidence
2. test the original `state-spaces/mamba` CUDA-graph tokenwise route as the first exact candidate
3. patch `selective_scan_fn` only if we decide the exact Cassian-scale run is worth kernel work

## Option A Speedup Status (2026-04-07)

Implemented in `trajectory_windowed_onepass.py`:

- `--window-selection {sliding,sample-centered}`
- `--post-context-tokens`
- `--forward-mode {full-model-hook,partial-target-layer}`
- report metadata for `window_selection`, `post_context_tokens`, `num_windows`, and `total_window_tokens`
- sanity comparison entry `full_model_hook__vs__partial_target_layer`

Validation:

- tiny fixture exact references still pass:
  - HF one-pass vs HF tokenwise min cosine `0.9999988`
- partial-forward validation on tiny fixture:
  - full-model-hook vs partial-target-layer min cosine `1.0` (PASS, threshold `>= 0.99999`)

Cassian planning/scout:

- full-file dry-run (`sample-every 25`):
  - sliding planned window tokens: `1,584,543` (1032 windows)
  - sample-centered planned window tokens: `224,256` (146 windows)
- short scout (`max-messages 300`, sample-centered + partial):
  - runtime `~1.3s`, window tokens `18,432`, windows `12`
- full windowed scout (`3636` turns, sample-centered + partial):
  - runtime `~11.3s`, window tokens `224,256`, windows `146`

All Option A outputs remain explicitly labeled `WINDOWED_APPROXIMATE` and
`approximate_windowed_not_exact_full_recurrence`.
