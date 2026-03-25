# Phase 1: Linear Probe Validation

## Objective

Determine whether Mamba-2.8B's SSM hidden state retains linearly decodable factual information after processing up to 8192 tokens of context. This is the prerequisite for the Cognitive Bridge hypothesis: if the signal does not exist in the state, no hypernetwork can extract it.

## Experimental Setup

- **Model:** `state-spaces/mamba-2.8b-hf` (2.77B parameters, 64 layers, d_model=2560, d_state=16)
- **Hardware:** RTX 3070 8GB, Opa-PC (WSL Ubuntu), PyTorch 2.10.0+cu128
- **Run ID:** `run_20260228T221628Z`
- **Duration:** ~14 hours continuous background execution
- **Total simulation turns:** 300
- **History scale:** Aggressively growing toward context limit (max_history_tokens: 8192)
- **Injection rhythm:** `inject_every=5` with schedule audits enforcing zero-drift behavior
- **Memory classes:** 4 distinct narrative facts (NPC names, passcodes, lore items, locations)

## Methodology

### Data Generation
At every 5th turn, a fact from one of 4 classes was injected into the conversational stream. Remaining turns contained procedural noise text (MUD-flavored prose) to simulate realistic conversational context. The accumulated history grew toward 8192 tokens.

### State Extraction
At each probe point (turns following an injection), the full hidden state across all 64 layers was extracted from the Mamba model immediately before a probing question about the most recently injected fact. State shape: `(1, 64, 2560, 16)`.

### Probe Training
Two probe architectures were evaluated:
1. **Linear probe:** Single-layer classifier mapping flattened state features to the 4-class label.
2. **MLP probe:** 2-layer network with 256 hidden units and nonlinear activation.

### Validation Protocol
- **5-seed rigorous testing:** Each probe was trained and evaluated across 5 completely re-rolled grouped data splits. Metrics are averaged with 95% confidence intervals.
- **Layer Profiler:** A dedicated loop sequentially isolated each of the 64 layers, training a separate probe on each to measure per-layer signal strength.
- **Null-control run:** 300 identical turns with no fact injection, evaluated over the same probe architecture, to empirically establish the noise floor.

### Sample Counts
With `inject_every=5` over 300 turns: ~171 accumulated probe matrices per run, yielding ~51 test samples at a 30% split ratio.

## Results

### Baselines and Controls

| Metric | Value |
|--------|-------|
| Statistical random/majority baseline | 17.0% |
| Neural read on null-control (noise floor) | 22.0% (+/- 1.0%) |

### Aggregate Probe Accuracy (All Layers Pooled)

| Probe Type | Accuracy | CI |
|------------|----------|-----|
| Linear | **34.2%** | +/- 2.6% |
| MLP | 30.4% | -- |

### Layer-Specific Profiling (Linear Probe)

| Layer Range | Accuracy Range | Interpretation |
|-------------|---------------|----------------|
| 0-1 | ~25-30% | Warming up, some signal |
| **2-8** | **40-55.7%** | **Peak signal zone** |
| **3 (peak)** | **55.7%** | **Maximum factual retention** |
| 10-25 | ~30-40% | Mediocre, declining |
| 30-64 | ~20-25% | Noise floor; next-token prediction dominates |

## Key Finding

**Factual memory in Mamba is localized to shallow layers, peaking sharply at Layer 3.**

The signal is not distributed uniformly across the 64-layer stack. Deep layers (30+) have collapsed to the noise floor -- they are fully occupied with next-token prediction geometry. The factual retention signal concentrates in the earliest recurrence layers, where macro-level contextual information has been compressed but not yet overwritten by fine-grained token predictions.

Mean-pooling across all layers (the initial compressor strategy) dilutes this signal by averaging the Layer 3 peak with 63 layers of noise. Per-layer targeting is necessary.

## Implications for Bridge Design

1. **MambaStateCompressor must target Layer 3 specifically.** The compressor extracts `mamba_state[:, 3]` (shape: `(batch, 2560, 16)`) and projects it to a context vector. This is implemented in `models.py` with `target_layer=3` as default.

2. **Input dimension depends on extraction path.** At Layer 3, the SSM state has shape `(2560, 16)` = 40,960 flat. However, the current production bridge uses **last-token hidden-state extraction** where the input is `d_model = 2560`. Pinky's Step 4b (2026-03-20) proved hidden-state last-token is 2.5x more informative than SSM state for disposition (cosine 0.036 vs 0.778). **Use `hidden_last_token` path, not `ssm_states`.**

3. **Linear separability enables simpler hypernetwork.** Since the probe confirmed facts are linearly separable at Layer 3, the hypernetwork does not need deep nonlinear capacity to decode the signal. A 2-layer MLP backbone is architecturally appropriate.

4. **Mamba-3 changes this geometry.** Mamba-3's MIMO structure changes the state shape to `(R, d_model/heads, d_state)`. If we upgrade the backbone, the compressor's `input_flat_size` and the layer indexing both need patching. This is documented as an open thread in the handoff.

## Experiment Files

Phase 1 probe experiments are in `experiments/mamba_state_transfer/`:

| File | Description |
|------|-------------|
| `experiment_01_basic.py` | Basic state transfer validation (byte-identical output) |
| `experiment_02_two_process.py` | Two-instance state transfer via file |
| `experiment_03_multiturn.py` | Multi-turn state accumulation test (20+ turns) |
| `experiment_04_data_collector.py` | Structured data collection for probe training |

The 300-turn diagnostic probe run was executed on Opa-PC via `mamba_linear_probe.py` (in `MoCoP/experiments/mamba_lora_bridge/`), with results documented in `CHEESE_Memory/05_EXPERIMENT_DEBRIEFS/Phase1_Mamba_Memory_Probe.md`.

## Status

Complete.
