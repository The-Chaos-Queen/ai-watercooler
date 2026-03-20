# MoCoP: Model Communication Protocol

## Abstract

Current model-to-model communication forces all information through natural language serialization, incurring cumulative information loss and O(n) context growth per session turn. We propose MoCoP, a protocol for transferring attentional state from a State Space Model (Mamba-2.8B) to a frozen Transformer (Qwen3-4B) via dynamically generated LoRA weight matrices produced by a trained hypernetwork. Phase 1 validation confirms that Mamba's hidden state at Layer 3 encodes retrievable factual information at 55.7% linear probe accuracy versus a 22% noise floor, establishing that the transfer substrate exists. Phase 2 implements the full bridge architecture (compressor, hypernetwork, dynamic LoRA injection) with code complete and cloud training pending.

## 1. Problem Statement

Every time two AI models communicate through text, the signal passes through multiple lossy compression stages: internal representation to natural language (ambiguity, formatting), tokenization (vocabulary mismatch, subword splits), and re-encoding by the receiving model. Each serialization/deserialization boundary destroys information.

This compounds across sessions. A model that conversed with a user for 50 turns has no way to carry forward the *disposition* it developed -- the subtle attentional biases accumulated through interaction -- to the next session. The options available today all fail in specific ways:

- **RAG** retrieves facts, not dispositions. It can remind a model that "the user dislikes formal language," but it cannot reproduce the attentional state that *produces* informal language naturally.
- **Prompt injection** (prepending session summaries) is O(n) in token cost and O(n^2) in attention cost. Context windows fill. The model drowns in its own echo.
- **Fine-tuning** on conversation history permanently alters weights. It is irreversible, expensive, and inappropriate for per-session state.

The fundamental issue is that Transformers store "memory" in the KV cache, which grows linearly with context. There is no fixed-size summary vector. State Space Models (Mamba, RWKV) do maintain such a vector -- a fixed-size recurrent state that compresses all prior context into a constant-memory representation. This architectural difference is the foundation of MoCoP.

## 2. Hypothesis

The hidden state of a Mamba SSM at a specific layer (empirically determined to be Layer 3) encodes retrievable attentional disposition that can be extracted, compressed, and translated by a hypernetwork into LoRA weight matrices. When these matrices are injected into a frozen Transformer's attention layers, they cause the Transformer to behave as though it had processed the same conversational history -- without any text-based memory injection, context window consumption, or permanent weight modification.

Formally: given a conversational prefix P processed by Mamba into state h_L3, a trained hypernetwork H, and a frozen Transformer T, we hypothesize that T(x; LoRA=H(compress(h_L3))) produces output that reflects knowledge of P, while T(x; LoRA=0) does not.

## 3. Background

### 3.1 State Space Models (Mamba)

Mamba implements a selective state space model where the recurrent state h_t is updated at each timestep by blending the new input with the existing state through learned, input-dependent selection matrices. Unlike Transformer KV caches, the state is fixed-size: for Mamba-2.8B, the shape is `(num_layers, d_model, d_state)` = `(64, 2560, 16)`, approximately 10-20 MB regardless of sequence length. This O(1) memory property makes Mamba states natural candidates for cross-session state transfer.

Mamba-3 introduces a rank-R MIMO (Multiple-Input Multiple-Output) structure that changes state geometry to `(R, d_model/heads, d_state)`. Current validation on Opa-PC confirms R=4 produces `(4, 32, 64)` per layer. This is architecturally significant for the bridge but does not affect the core hypothesis.

### 3.2 Low-Rank Adaptation (LoRA)

LoRA decomposes weight updates into low-rank matrices: for a weight matrix W of shape (d_out, d_in), the update is Delta_W = B * A where A has shape (d_in, r) and B has shape (r, d_out), with rank r << min(d_in, d_out). This reduces the parameter count from d_in * d_out to r * (d_in + d_out). At rank r=8 with d=4096, this is ~65K parameters per target layer instead of ~16.7M -- feasible for a small hypernetwork to generate dynamically.

Standard LoRA (via PEFT, etc.) is static: weights are loaded once and persist. MoCoP requires *dynamic* LoRA -- matrices generated per-inference from the current Mamba state, injected before generation, and stripped after. The `DynamicLoRALinear` module implements this via a context-managed pattern (`set_lora` / `clear_lora`) that preserves the standard `nn.Linear` forward signature, maintaining compatibility with HuggingFace's `model.generate()`.

### 3.3 Hypernetworks

A hypernetwork is a neural network that produces the weights for another neural network. In MoCoP, the hypernetwork is a 2-layer MLP with per-target-layer output heads. It takes the compressed Mamba state (a 1D context vector) as input and outputs pairs of (A, B) LoRA matrices for each targeted Transformer layer. The backbone learns a general representation; the heads specialize per target layer.

Output heads are initialized with small weights (std=0.01, zero bias) so the initial LoRA contribution is near-zero. The system starts "quiet" and learns to inject signal through training.

## 4. Phase 1: Linear Probe Validation

### 4.1 Experimental Setup

**Model:** `state-spaces/mamba-2.8b-hf` (2.77B parameters)
**Hardware:** RTX 3070 8GB on Opa-PC (WSL Ubuntu), PyTorch 2.10.0+cu128
**Run ID:** `run_20260228T221628Z`

The experiment simulated 300 turns of game-state data. Every 5 turns, a distinct fact was injected from one of 4 memory classes (NPC names, passcodes, lore items, locations). The remaining turns contained procedural noise text filling up to 8192 tokens of accumulated history.

At each probe point, the full 64-layer hidden state was extracted immediately before a probing question about the most recently injected fact.

### 4.2 Probing Methodology

Two probe architectures were trained per layer:

1. **Linear probe:** Single linear classifier mapping hidden state features to memory class.
2. **MLP probe:** 2-layer, 256-hidden MLP with nonlinear activation.

Validation used 5-seed rigorous testing with grouped train/test splits to extract 95% confidence intervals. A dedicated null-control run (300 turns, identical procedure, no fact injection) established the noise floor empirically.

A separate **Layer Profiler** loop sequentially isolated each of the 64 layers to measure signal strength per layer.

### 4.3 Results

**Baselines:**
- Random/majority baseline: 17.0%
- Neural read on null-control (noise floor): 22.0% (+/- 1.0%)

**Aggregate metrics (all layers pooled):**
- Linear probe accuracy: **34.2%** (+/- 2.6% CI) -- 12.2 percentage points above noise
- MLP probe accuracy: **30.4%** -- above noise but underperforms linear

**Layer-specific profiling:**
- Deep layers (30-64): Collapsed to noise floor (~20-25%). These layers are dominated by next-token prediction geometry.
- Middle layers (10-25): Mediocre signal (~40%).
- Shallow layers (2-8): Strong signal concentration, peaking at **Layer 3: 55.7% linear accuracy**.

### 4.4 Interpretation

Three findings shaped Phase 2 architecture:

1. **Signal exists and is linearly separable.** The jump from 22% noise to 34.2% aggregate (and 55.7% at Layer 3) is unambiguous. Mamba structurally internalizes arbitrary facts through 8192-token recursive windows.

2. **Signal is localized, not distributed.** Mean-pooling across all 64 layers (the initial approach) *dilutes* the signal. Layer 3 alone carries more information than all layers averaged. The compressor must target Layer 3 specifically.

3. **Linear probes outperform MLPs.** This confirms that Mamba separates factual categories along linear hyperplanes in its state geometry. The signal is not entangled in nonlinear manifolds. This is encouraging for the hypernetwork, which must decode this geometry reliably.

## 5. Phase 2: Cognitive Bridge Architecture

### 5.1 Architecture

The full pipeline, left to right:

```
Mamba-2.8B (frozen)
  -> Extract Layer 3 hidden state: (batch, d_model, d_state)
    -> MambaStateCompressor: flatten + linear projection -> (batch, context_dim)
      -> LoRAHypernetwork: shared backbone + per-layer heads -> [(A_i, B_i), ...]
        -> DynamicLoRALinear: inject into Qwen3-4B (frozen) attention layers
          -> Qwen generates response under LoRA influence
            -> Strip LoRA, compute loss against teacher-forced target
```

Only the compressor and hypernetwork have trainable parameters. Mamba and Qwen remain frozen throughout. Gradients flow backward through Qwen's frozen layers, through the injected LoRA matrices, and into the hypernetwork and compressor.

### 5.2 Dataset Design

Training data is procedurally generated by `bridge_dataset.py`:

- **Format:** ChatML with system prompt, history context, and factual query/answer pairs.
- **Context length:** 8192 tokens of Mamba history per sample.
- **Fact types:** 8 categories -- NPC names, location descriptions, secret passcodes, market prices, inn names, shrine locations, relic names, hiding places. Extended with event_witness and npc_relationship types.
- **Distractor injection:** Noise text fills the context between fact injections, simulating realistic conversational drift.
- **Teacher forcing:** Loss is computed only on the exact factual answer tokens in the Qwen output. Prompt tokens are masked.
- **Splits:** 500 train / 150 validation / 100 test, deterministic seeds, no sample leakage.

### 5.3 Training Setup

- **Optimizer:** AdamW
- **Schedule:** Linear warmup followed by cosine decay
- **Evaluation:** Three-way comparison:
  1. Bridge-injected: Mamba state -> hypernetwork -> LoRA -> Qwen
  2. No-injection control: Qwen alone, same prompts
  3. Random LoRA control: Random matrices injected, same prompts
- **Confidence intervals:** 95% CIs across multiple seeds
- **Regression testing:** 8 automated smoke tests validating tensor shapes, dtype handling, parameter counts, and end-to-end forward pass wiring

### 5.4 Current Status

Code is complete across four core modules:
- `models.py`: `MambaStateCompressor`, `LoRAHypernetwork`, `DynamicLoRALinear`
- `cognitive_bridge.py`: `CognitiveBridge` orchestrator and `BridgeConfig`
- `bridge_dataset.py`: Synthetic data pipeline with disk persistence and deterministic splits
- `train_bridge.py`: Full training loop with dry-run mode, three-way evaluation, warmup+cosine schedule

**Bugs fixed during development:**
- LazyLinear initialization: replaced with explicit `nn.Linear` after discovering that `LazyLinear` defers parameter registration, breaking optimizer setup. The compressor now uses a static `input_flat_size = mamba_d_model * mamba_d_state`.
- `lora_scaling`: changed from 0.5 to 1.0. At 0.5, the bridge signal was attenuated before the hypernetwork could learn to compensate.
- `qwen_prompt_ids` alias: functionally correct (same tensor as `qwen_input_ids`) but semantically misleading. Flagged for cleanup, not blocking.
- `QWEN_MODEL_ID`: corrected from `Qwen2.5-1.5B-Instruct` to `Qwen/Qwen3-4B` (base, not instruct) to match the actual target model.

**Regression smoke:** 8/8 tests green.
**Real PyTorch forward pass (Opa-PC):** Pending.
**Cloud training run:** Pending.

## 6. Observations So Far

**The serialization tax is real and measurable.** The MoCoP concept document's compiler analogy holds up. Forcing models to communicate through natural language is equivalent to requiring English prose between compiler optimization passes. It works. It is also absurd.

**Small models suffer most.** The MUD agent experiments (sessions 2026-02-12 through 2026-02-23) demonstrated that models in the 4-8B range waste significant capacity parsing atmospheric prose. Switching to structured JSON input immediately improved agent reliability. MoCoP's Layer 3+ approach eliminates the parsing burden entirely.

**Layer 3 localization was not predicted.** The initial architecture (mean-pooling across all 64 layers) was wrong. The empirical finding that factual memory concentrates in shallow layers forced an architecture revision that made the compressor both simpler and more effective. Theory did not predict this; experiment did.

**The "endocrine" framing is technically accurate.** The hypernetwork does not encode specific facts into the LoRA matrices (that would require far more parameters). It shifts activation thresholds. The Transformer does not "know" specific facts from the Mamba state; it *attends differently* because of it. This is closer to how hormones affect cognition than how reading a diary affects cognition.

## 7. Phase 3: Planned Work

Contingent on Phase 2 producing a viable baseline:

1. **LoRA rank ablation:** r=4, 8, 16, 32. Determines the information capacity needed in the bridge.
2. **Prompt format generalization:** Train on ChatML, evaluate on GameWorld framing and vanilla completion. Tests whether the bridge transfers disposition independently of prompt style.
3. **Compressor depth ablation:** Layer 3 only vs. Layers 2-4 concatenated. Tests whether adjacent layers carry complementary signal.
4. **Mamba-3 upgrade:** State geometry changes to `(R, d_model/heads, d_state)`. Requires patching `MambaStateCompressor.input_flat_size`. Should follow Phase 2 baseline to maintain a controlled comparison.
5. **Persistence architecture:** Co-indexed Qdrant storage where semantic embeddings point to saved Mamba state files. Retrieval query: semantic search returns file path, state file is loaded and injected via bridge.

## 8. Limitations and Open Questions

**What could fail:**
- The hypernetwork may not have enough capacity to translate Mamba's state geometry into useful LoRA matrices. The signal exists (Phase 1 proved it), but extracting it through a 2-layer MLP and encoding it into rank-8 LoRA matrices is a lossy process. If too lossy, the bridge will show no lift over baseline.
- The training dataset is synthetic and narrow (MUD-flavored facts). The bridge may overfit to the specific fact formats and fail to generalize.
- The factual retention signal at Layer 3 was measured via probing accuracy, not via downstream task performance. High probing accuracy does not guarantee high bridge utility.

**What remains unknown:**
- Whether the bridge transfers *disposition* (attentional bias) or only *facts* (specific retrievable items). The probe measures fact recall; the bridge's value proposition is disposition transfer. These may not be the same thing.
- The minimum training compute required. We have no estimate of convergence time or sample efficiency.
- Whether Qwen3-4B is the right target model. Larger models may have more capacity to utilize the LoRA signal; smaller models may be more sensitive to it.
