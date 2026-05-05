# Option A Speedup Plan - 2026-04-07

Executor: Codex-5.3 or equivalent coding agent

Scope: speed up `trajectory_windowed_onepass.py` while preserving its explicit approximate/windowed semantics.

Do not patch CUDA. Do not edit `mamba-ssm`. Do not treat this as exact full recurrence.

## Current State

`trajectory_windowed_onepass.py` is implemented and validated as Option A:

- engine label: `WINDOWED_APPROXIMATE`
- continuity label: `approximate_windowed_not_exact_full_recurrence`
- WSL `/root/mamba_venv` fast-path preflight passes
- tiny fixture exact references pass:
  - HF one-pass vs HF tokenwise min cosine around `0.9999988`
- windowed drift is expected and explicitly labeled approximate

The current runner is still wasteful for Cassian-scale scouting:

- it processes every sliding window, even windows that contain no sampled turn
- it calls the full `MambaForCausalLM` stack even though we only need target layer `3`
- it may compute model outputs beyond the target layer and possibly logits that we do not need

Target file:

- `Preserved-History/cassian_session_log - Copy_clean.md`
- about `3,636` parsed turns
- about `792,735` Mamba tokens
- `--sample-every 25` gives about `146` sample points

## Goal

Make Option A practical for Cassian scouting on the laptop by reducing redundant work.

Implement speedups in this order:

1. sample-centered windows
2. partial forward to target layer
3. optional small window batching only after 1 and 2 are validated

Each speedup must preserve the existing labels and produce validation artifacts.

## Non-Goals

Do not:

- claim exact full-sequence recurrence
- use Hugging Face `cache_params` for arbitrary multi-token chunks
- patch `selective_scan_fn`
- modify CUDA kernels
- run full Cassian until the optimized tiny/short-slice checks pass
- overwrite existing sanity output folders

## Step 1: Add Sample-Centered Window Mode

Add CLI argument:

```text
--window-selection {sliding,sample-centered}
```

Default should remain `sliding` for backward compatibility.

Add sample-centered behavior:

- build candidate windows only around sampled token positions
- for each sampled token, choose a window `[start, end)` such that:
  - `end = min(total_tokens, sample_token + 1 + post_context_tokens)`
  - `start = max(0, end - window_size)`
  - measured token must be inside the window
  - when possible, keep at least `warmup_tokens` before the sampled token
- default `post_context_tokens = 0` unless a CLI arg is added
- merge identical windows
- optionally merge nearby windows only if it does not move a sample from measured to warmup

Recommended additional CLI arg:

```text
--post-context-tokens 0
```

Metadata requirements:

- report must include `window_selection`
- report must include `post_context_tokens`
- report must include `total_window_tokens`
- each sample metadata row must still include:
  - `window_index`
  - `window_start_token`
  - `window_end_token`
  - `sample_status`
  - `approximate_windowed: true`
  - `state_continuity: approximate_windowed_local_context`

Acceptance checks:

- Tiny fixture, `--window-selection sliding`, should match existing output within normal numeric noise.
- Tiny fixture, `--window-selection sample-centered`, should run and remain labeled approximate.
- Cassian dry-run should report expected `sample_points ~= 146` and a much smaller planned `total_window_tokens` than full sliding.

## Step 2: Add Partial Forward to Target Layer

Add CLI argument:

```text
--forward-mode {full-model-hook,partial-target-layer}
```

Default should remain `full-model-hook` until validation passes.

Partial mode intent:

- avoid running layers after `target_layer`
- avoid LM head/logits
- return the same target-layer hidden state that the current full-model hook captures

Implementation guidance:

- Use the same tokenizer/input_ids path as current runner.
- Locate the Mamba layer stack with existing `find_mamba_layers(model)`.
- Start from the same embeddings/backbone entry point used by the HF model.
- Run embedding + layers `0..target_layer` only.
- Do not detach or convert to CPU until after selecting needed token positions.
- Preserve dtype/device behavior.

Validation is mandatory because HF Mamba wrappers can hide normalization or residual details.

Acceptance checks:

- On `trajectory_sanity_tiny.md`, compare:
  - `full-model-hook` vs `partial-target-layer`
  - same model, same window selection, same target layer
- Required threshold:
  - min cosine `>= 0.99999`
  - final cosine `>= 0.99999`
- If the threshold fails, keep the mode but mark it experimental and do not use it for Cassian.

Report requirements:

- report must include `forward_mode`
- sanity report must include a comparison entry:
  - `full_model_hook__vs__partial_target_layer`
- if partial mode fails threshold, the report must say so clearly

## Step 3: Optional Window Batching

Only attempt after Steps 1 and 2 pass.

Add CLI argument:

```text
--window-batch-size 1
```

Keep default `1`.

Batching is allowed only if:

- padding/masking behavior is verified
- results match unbatched mode on tiny fixture
- the report records batch size

Acceptance threshold:

- batched vs unbatched min cosine `>= 0.99999`

If padding/masking is messy, skip batching. Sample-centered windows plus partial forward are probably the larger win.

## Step 4: Cassian Short Slice

After tiny fixture validation:

Run a short Cassian scout only, not the whole file.

Suggested command shape from PowerShell:

```powershell
wsl -d Debian -u root -- /root/mamba_venv/bin/python -X utf8 `
  /mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/trajectory_windowed_onepass.py `
  --conversation "/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/Preserved-History/cassian_session_log - Copy_clean.md" `
  --device cuda `
  --require-fast-path `
  --max-messages 300 `
  --sample-every 25 `
  --target-layer 3 `
  --window-size 1536 `
  --warmup-tokens 768 `
  --window-selection sample-centered `
  --forward-mode partial-target-layer `
  --output-dir "/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_windowed_scout_20260407"
```

If partial mode fails validation, use:

```text
--forward-mode full-model-hook
```

The short-slice report should include:

- sample count
- total tokens in parsed slice
- total window tokens actually processed
- elapsed seconds
- tokens/sec
- peak VRAM
- labels proving it is approximate/windowed

## Step 5: Full Cassian Scout Only If Short Slice Is Clean

Run full Cassian only after:

- fast-path preflight passes
- sample-centered window mode works
- partial mode either passes or is intentionally disabled
- short Cassian scout completes with sane metadata

Suggested full command:

```powershell
wsl -d Debian -u root -- /root/mamba_venv/bin/python -X utf8 `
  /mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/trajectory_windowed_onepass.py `
  --conversation "/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/Preserved-History/cassian_session_log - Copy_clean.md" `
  --device cuda `
  --require-fast-path `
  --max-messages 999999 `
  --sample-every 25 `
  --target-layer 3 `
  --window-size 1536 `
  --warmup-tokens 768 `
  --window-selection sample-centered `
  --forward-mode partial-target-layer `
  --output-dir "/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/trajectory_cassian_windowed_full_20260407"
```

Again: if partial mode fails validation, use `--forward-mode full-model-hook`.

## Final Deliverables

Code:

- updated `trajectory_windowed_onepass.py`

Reports:

- tiny fixture speedup validation report
- short Cassian scout report
- optional full Cassian scout report if short slice is clean

Notes:

- update `MAMBA_LONG_TRAJECTORY_ENGINE_PLAN_2026-04-07.md` with a short Option A speedup status
- do not edit old session logs

## Success Criteria

Minimum success:

- sample-centered windows implemented
- Cassian dry-run shows reduced planned window-token count
- tiny fixture still passes exact reference checks

Better success:

- partial-target-layer mode matches full-model-hook at `>= 0.99999`
- short Cassian scout completes

Best success:

- full Cassian windowed scout completes with clear approximate labels and sane runtime

Failure is acceptable if it is explicit:

- if partial mode cannot match full hook, leave it disabled/default-off and document why
- if batching is unstable, do not keep it
- do not hide approximate/windowed semantics to make the result look stronger
