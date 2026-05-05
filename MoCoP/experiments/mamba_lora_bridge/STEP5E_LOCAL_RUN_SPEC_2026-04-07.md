# Step 5e Local Run Spec - 2026-04-07

Purpose: give An-Chan / Codex a narrow implementation target for a local Step 5e layer-targeting runner.

## Current Status

Step 5e is not a blank slate.

Existing evidence:

- `RESEARCH_LOG.md` Entry 2026-03-25: Step 5e partial result.
- `run_reincarnation/steve_step5e_layer_override_20260325.md`: runtime layer override is real and behaviorally active on Steve.
- `run_step5e_layer_sweep.ps1`: Steve-specific sweep wrapper exists.

Current open gap:

- The layer-targeting sweep was only partial.
- The existing script is Steve-bound (`BaseUrl` defaults to `192.168.2.49:7860`).
- The existing script does not fully implement the ladder's 5e.2 gradient matrix.
- It approximates `front_loaded` as uniform alpha `0.15` if true per-layer alpha is unavailable.

## What "Local" Must Mean

Be explicit in the script:

- If "local" means Laura's laptop, the script must use the local endpoint/config and must not assume Steve SSH helpers.
- If "local" means "run from this repo but target a server," the script must expose `--base-url`/`-BaseUrl` and not hard-code Steve.
- If it still talks to Steve, call it a Steve runner, not local.

Do not confuse the local Mamba WSL fast path with Step 5e:

- local Mamba fast path helps trajectory/probing work
- Step 5e is Qwen bridge injection layer targeting
- Step 5e needs the chat/inference server with bridge injection and layer override support

## Required 5e Configs

### Baseline

- alpha: `0.0`
- target layers: default baseline may stay configured, but injection must be off
- temperature: `0.0` for deterministic comparison

### 5e.1 Phase Sweep

Same alpha, same 4-layer spread:

- `reasoning_entry_5_8`: `5:v_proj,6:v_proj,7:v_proj,8:v_proj`, alpha `0.2`
- `mid_reasoning_12_15`: `12:v_proj,13:v_proj,14:v_proj,15:v_proj`, alpha `0.2`
- `reasoning_exit_20_23`: `20:v_proj,21:v_proj,22:v_proj,23:v_proj`, alpha `0.2`

### 5e.2 Alpha Shape Sweep

If real per-layer alpha is supported, test:

- `front_loaded`: `12=0.3, 13=0.2, 14=0.1, 15=0.05`
- `back_loaded`: `12=0.05, 13=0.1, 14=0.2, 15=0.3`
- `peak_at_13`: `12=0.1, 13=0.3, 14=0.1, 15=0.1`

If real per-layer alpha is not supported, do not pretend it is.

Fallback labels must be explicit:

- `front_loaded_uniform_proxy`: layers `12-15`, uniform alpha `0.15`
- `peak_at_13_single_layer`: layer `13:v_proj`, alpha `0.2` or `0.3` if allowed by MED gate

### 5e.3 Split Injection

- `split_entry_mid`: `5:v_proj,6:v_proj,12:v_proj,13:v_proj`
- alpha: `0.1`

This tests distributed seeding versus the current mid-reasoning zone.

## Required Runner Behavior

The script should:

- accept `BaseUrl`
- accept `OutputDir`
- accept `Alpha`
- accept `Temperature`
- accept restore defaults:
  - alpha `0.2`
  - temperature `0.7`
  - layers `12:v_proj,13:v_proj,14:v_proj,15:v_proj`
- fetch and save `/status` before each config
- fail if the expected model is not loaded unless `--allow-model-mismatch` is set
- write one JSONL or JSON artifact per config
- write a manifest describing configs, model, alpha, temperature, layer spec, start/end time, and status snapshot
- restore defaults at the end unless `--no-restore` is set

If the target server cannot set per-layer alpha:

- write that limitation to the manifest
- run the documented fallback configs only

## Required Metrics

At minimum:

- response text
- response length
- blank/collapse detection
- repetition/loop detection if the existing evaluator supports it
- response diversity entropy if available
- qualitative prompt id
- status snapshot before generation

Nice to have:

- logit self-report expectation if already wired
- gate events if the server exposes them

## Prompt Panel

Do not rely on a single prompt.

Use a small deterministic panel with at least:

- neutral descriptive prompt: `Explain the scent of rain.`
- continuity / warmth prompt
- factual recall prompt if available
- friction / refusal-adjacent prompt
- one short creative prompt

Keep temperature `0.0` for primary comparison.

Optionally repeat best candidates at `temperature 0.7` after deterministic pass.

## Acceptance

Minimum pass:

- runner executes baseline + 5e.1 phase sweep
- writes manifest and artifacts
- restores defaults
- does not hard-code Steve unless explicitly named as a Steve runner

Better pass:

- includes 5e.2 fallback configs with honest labels
- includes 5e.3 split injection
- produces a summary table comparing each config to baseline

Best pass:

- supports real per-layer alpha if the server does
- records enough metrics to decide whether 12-15 remains the best zone

## Interpretation Rules

Do not overclaim.

- If `12-15` still wins: Step 5e confirms the current default.
- If `5-8` wins: injection may work better at reasoning entry.
- If `20-23` is destructive: reinforces the earlier partial result.
- If split injection wins: disposition may benefit from distributed seeding.
- If all injected configs look worse than baseline: alpha or checkpoint may dominate layer choice.

Step 5e is an optimization/surface-mapping task, not a new bridge proof by itself.
