# MoCoP -- Master Plan

**Last updated:** 2026-03-25
**Author:** Laura (concept + direction), multi-agent team (implementation)

## Vision

MoCoP is a system for transferring attentional state between AI models without serializing through natural language. The core idea: Mamba (a state space model) accumulates conversational context into a fixed-size hidden state. A trained hypernetwork reads that state and produces activation bias vectors that are injected into a frozen Transformer's v_proj layers (Qwen), causing it to *behave* as though it remembers the prior context -- without spending a single token on retrieval or history injection.

> **Note:** The original design used dynamic LoRA weight injection. This was abandoned after epoch-2 over-injection collapse (PPL 44 vs baseline 29). The current mechanism is **activation bias injection at v_proj layers 12-15** (~5K trainable parameters), which is stable, reversible, and produces the inverted-U dose-response at alpha 0.2. Older references to "LoRA injection" in this document describe the historical design intent, not the current system.

This is not memory retrieval. It is identity continuity. The analogy is hormonal, not archival: we are not building a diary the Transformer reads before each session. We are building an endocrine system that shifts the Transformer's activation thresholds based on accumulated experience. The Transformer does not *read* the memory. It *feels* the memory, the same way adrenaline changes your reaction time without you reading an instruction manual.

## What This Is Not

- **Not RAG.** Retrieval-Augmented Generation fetches text snippets and prepends them to context. MoCoP injects state directly into model weights. No tokens consumed, no context window occupied.
- **Not prompt injection.** Prompt-based memory ("System: you are angry at the goblin") is O(n) in token cost and O(n^2) in attention cost. It scales linearly with history length and quadratically in compute. MoCoP is O(1) -- one fixed-size state injection regardless of history length.
- **Not fine-tuning on conversation history.** Fine-tuning permanently alters model weights. MoCoP's activation bias injection is ephemeral: applied before generation, removed after. The base model stays pristine.
- **Not a chatbot memory system.** Commercial "memory" features (Claude memory, ChatGPT memory) store and retrieve facts as text. MoCoP transfers *attentional disposition* -- not what the model knows, but how it attends.

## Phase Overview

| Phase | Name | Status | Key Output |
|-------|------|--------|------------|
| 1 | Linear Probe Validation | Complete | Layer 3 peaks at 55.7% vs 22% noise floor |
| 2 | Cognitive Bridge Training | Step 5d Complete | Activation bias injection validated. Alpha 0.2 = MED (6/6 recall, entropy UP, recovery 1.0, distress 0). Dual saliency gate live on Steve. Compressor bypass resolved the PCA collapse. |
| 3 | Ablations + Cloud Scale | Planned | LoRA rank sweep, Mamba-3 path |
| 4 | Deployment | Planned | Persistent co-indexed Qdrant + state vectors |

## Success Criteria

### Phase 1: Signal Confirmation
- **Criterion:** Linear probe trained on Mamba hidden states achieves statistically significant accuracy above noise floor for factual recall.
- **Result:** 55.7% at Layer 3 vs 22% noise floor (p < 0.05 across 5-seed validation). Complete.

### Phase 2: Bridge Viability
- **Criterion:** Qwen with activation bias injection (from Mamba state via hypernetwork) achieves measurably higher fact retention and response quality than baseline Qwen, while remaining reversible and non-harmful.
- **Minimum bar:** Higher factual recall than no-injection baseline; entropy must not drop >50%; recovery ≥0.95 after alpha removal; distress markers = 0.
- **Result:** PASS at alpha 0.2 on Steve/4090 (6/6 recall vs 4/6 baseline, entropy UP, recovery 1.0, distress 0). A100 replication pending (OpenCLAW #41).

### Phase 3: Configuration Optimization
- **Criterion:** Identify optimal LoRA rank and compressor configuration through systematic ablation. Determine whether Mamba-3 improves bridge quality enough to justify architecture changes.
- **Minimum bar:** At least one configuration outperforms the Phase 2 baseline by >5% absolute on the same eval set.

### Phase 4: Live Deployment
- **Criterion:** End-to-end deployment in at least one target application (MUD NPC memory or Prosthetic hand controller continuity) with measurable improvement in cross-session behavioral consistency.
- **Minimum bar:** Qualitative evaluation by Laura showing state transfer produces coherent continuation behavior across sessions.

## Infrastructure Dependencies

| Resource | Role | Status |
|----------|------|--------|
| Opa-PC (192.168.2.194) | RTX 3070 8GB, local GPU for smoke tests and probing | Available, validated |
| Vast.ai A100 SXM4 80GB | Cloud GPU for Phase 2 training | Used for multiple runs (~$15 total through Phase 2) |
| Qdrant (192.168.2.191:6333) | Vector store for semantic indexing of state files | Running, ~12,700 entries |
| WSL on Opa-PC | Linux environment for CUDA/PyTorch | Configured, venv ready |

**VRAM budget (Phase 2 training on A100 80GB):**
- Qwen2.5-7B (bf16 or --no-4bit): ~14 GB
- Mamba-2.8B in bf16: ~5.6 GB
- Hypernetwork + compressor + gradients + optimizer: ~4-8 GB
- Total: ~24-28 GB (fits on A100 80GB at batch-size 1; too large for Opa-PC 3070 8GB)

## Open Questions

1. **Compressor depth.** Is Layer 3 alone sufficient, or would including Layers 2-4 improve bridge quality? Phase 1 only tested per-layer isolation, not multi-layer concatenation.

2. **Mamba-3 state geometry.** Mamba-3 introduces a rank-R MIMO structure. State shape changes from `(batch, num_layers, d_model, d_state)` to `(batch, R, d_model/heads, d_state)` with R=4 currently producing `(batch, 4, 32, 64)`. The `MambaStateCompressor.input_flat_size` must be patched if the backbone changes. When to make this switch relative to Phase 2 baseline is undecided.

3. **Prompt format generalization.** The bridge is trained on ChatML-formatted data with MUD-flavored facts. Will it generalize to other prompt formats (vanilla completion, GameWorld framing, instruction format)? Unknown until Phase 3 ablation.

4. **LoRA rank sensitivity.** The hypernetwork generates LoRA matrices at rank r=8 by default. The optimal rank is unknown. Too low and the bridge lacks expressivity; too high and the hypernetwork must output more parameters, making it harder to train.

5. **Decay characteristics.** Phase 1 showed signal at 8192 tokens. What happens at 16k? 32k? Mamba's recurrent state theoretically handles infinite context, but the factual signal may decay below the probe threshold at longer horizons.

6. **Effective dimensionality of bridge signal.** ~~How much information does the hypernetwork actually transfer vs. how much of the LoRA injection is noise? PCA / intrinsic dimensionality analysis on the generated LoRA weights would answer this, but has not been attempted.~~ **ANSWERED (2026-03-16):** PCA on compressed context vectors shows effective rank of 2.53/2048 (train) and 1.62/2048 (eval). The compressor collapses all inputs to near-scalar. This is the primary bottleneck. See `experiments/mamba_lora_bridge/PCA_DIAGNOSTIC_2026-03-16.md`.

## Known Limitations

- **Mamba base model quality.** Mamba-2.8B is not instruction-tuned. It cannot reliably produce structured output (JSON) without LoRA or constrained decoding. This limits its standalone utility as a MUD agent but does not affect its role as a state encoder.
- **Single-GPU training constraint.** The full pipeline (Mamba frozen + Qwen frozen + hypernetwork trainable) requires both models in VRAM simultaneously. The local RTX 3070 (8GB) is marginal; cloud GPU is likely required for real training runs.
- **Compressor collapse.** PCA diagnostic (2026-03-16) confirmed the MambaStateCompressor reduces 2048-dim context vectors to effective rank ~2.5. The hypernetwork receives near-identical inputs for every sample. This is the primary blocker for generalization. Repair paths: compressor bypass, wider bottleneck, contrastive loss, or multi-layer concatenation.
- **SSH reliability.** Windows SSH to Opa-PC truncates output aggressively. The `opa-wsl.ps1` runbook mitigates this but adds operational friction.
- **Dataset is synthetic.** Training data comes from a procedural generator with 8 fact types and MUD-flavored distractors. Real conversational data has not been tested.
