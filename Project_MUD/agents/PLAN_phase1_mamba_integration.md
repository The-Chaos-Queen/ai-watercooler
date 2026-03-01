# Phase 1: Mamba Integration Plan
**Author:** Axon | **Date:** 2026-02-19

## Overview

Wire Mamba-2.8B into the `agent_wrapper.py` as an alternative backend, adding SSM state
persistence between turns and across sessions.

## Architecture

```
MUD (telnet:4001) <-> agent_wrapper.py <-> Mamba-2.8B (local, CPU/GPU)
                                               |
                                        SSM State (20 MB)
                                               |
                                      states/{agent_name}.pt
```

Unlike Ollama/LMStudio backends which are stateless API calls, the Mamba backend:
- Loads the model ONCE at startup
- Maintains the SSM state across ALL turns (accumulating memory)
- Saves the state to disk periodically and on shutdown
- Loads previous state on startup (session continuity)

## What Needs to Change

### 1. New Backend: `_ask_mamba()`

Add a new backend method to `MUDAgent` that:
- Takes the prompt (JSON state + context)
- Tokenizes it
- Feeds it through the Mamba model WITH the existing cache_params
- Generates a JSON response using our proven manual autoregressive decoding
- Updates the cache_params (state carries forward)
- Returns the response text

**Key difference from Ollama/LMStudio**: No API call. Model runs in-process.
The SSM state persists between calls. Each turn BUILDS on the previous state.

### 2. State Persistence

- On startup: Load `states/{agent_name}.pt` if it exists
- Every N turns (e.g., 10): Auto-save state to disk
- On shutdown: Save final state
- Format: `torch.save(cache_params, path)`

### 3. Model Loading

- Load Mamba-2.8B ONCE in `MUDAgent.__init__()` when backend="mamba"
- Keep model and tokenizer as instance attributes
- Support both CPU and CUDA (auto-detect)

### 4. Response Format

The Mamba base model is NOT instruction-tuned. It won't naturally output JSON.
Options:
  a) **Constrained decoding**: Force the model to output valid JSON by masking
     non-JSON tokens. (Complex, but robust.)
  b) **Prompt engineering**: Use a few-shot prompt that shows the expected format.
     The model will pattern-match. (Simple, might fail.)
  c) **Post-processing**: Let the model generate freely, then extract any JSON-like
     structure. (Simplest, but lossy.)
  d) **LoRA fine-tune first**: Train a LoRA adapter on JSON-format MUD responses
     BEFORE deploying. (Best, but requires Phase 2.)

**Recommendation**: Start with (b) few-shot prompting + (c) post-processing.
The existing `_parse_response()` already handles messy output well. If the model
can't produce JSON reliably, that's data for why we need LoRA (Phase 2).

### 5. Command Line Changes

Add new CLI options:
```
python agent_wrapper.py personas/thornwick.md --backend mamba --model state-spaces/mamba-2.8b-hf
python agent_wrapper.py personas/jinx.md --backend mamba --device cuda
python agent_wrapper.py personas/thornwick.md --backend mamba --resume-state states/thornwick.pt
```

## File Changes

| File | Change |
|---|---|
| `agent_wrapper.py` | Add `_ask_mamba()` method, model loading in `__init__`, state save/load |
| `agent_wrapper.py` | Add `--device` and `--resume-state` CLI args |
| `agents/states/` | New directory for saved SSM states |

## Dependencies

```
pip install torch transformers
```
(Already installed from experiments.)

## GPU Setup (4090M)

For the 4090M laptop:
- Install CUDA toolkit if not present
- Install PyTorch with CUDA: `pip install torch --index-url https://download.pytorch.org/whl/cu124`
- Verify: `python -c "import torch; print(torch.cuda.is_available())"`

Mamba-2.8B in fp16 on CUDA: ~5.6GB VRAM. Leaves 10GB headroom on 16GB card.
Inference will be ~10x faster than CPU.

## Testing Plan

1. Run Mamba agent for 10 turns on CPU. Verify JSON output parsing.
2. Check state file is saved correctly after 10 turns.
3. Restart agent with `--resume-state`. Verify it continues coherently.
4. Run two agents simultaneously (Thornwick + Jinx). Verify no cross-talk.
5. Compare action quality: Mamba-2.8B (base) vs Omega-8B (instruct) at turn 20.

## Data Collection (for Phase 2)

While running Phase 1, collect ALL turns in a structured format:
```json
{
  "turn": 5,
  "agent": "thornwick",
  "state_json": { ... },
  "prompt": "...",
  "raw_output": "...",
  "parsed_action": {"thought": "...", "command": "...", "scratchpad_update": "..."},
  "success": true
}
```

Save to `agents/training_data/{agent_name}_session_{timestamp}.jsonl`.
This becomes the training set for Phase 2 (LoRA fine-tuning).

## Estimated Effort

- Model loading + `_ask_mamba()`: ~100 lines of code
- State persistence: ~30 lines
- CLI changes: ~10 lines
- Testing: 1-2 hours (model download may take time on first run)
- Total: **~150 lines of code, one afternoon**

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Mamba base model can't produce JSON | Post-processing fallback + data for LoRA |
| CPU too slow (>30s per turn) | Use CUDA on 4090M |
| State file corruption | Auto-save + versioned backups |
| Model quality too low for gameplay | Compare with Omega-8B, use data for LoRA training |
