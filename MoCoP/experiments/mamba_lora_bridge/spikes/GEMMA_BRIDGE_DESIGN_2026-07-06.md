# Gemma-4-12B Activation Bridge — Design Document

**Task:** OpenCLAW #139
**Authors:** Purple (draft), architecture by Isegrim (interlock map #665, zone rule v2 #758, substrate memo #681)
**Date:** 2026-07-06
**Status:** DRAFT — awaiting Isegrim review + Cairn ethics pass + Laura approval before any training launch

---

## 1. What This Document Is

A concrete design for training and deploying a MoCoP activation bridge from Mamba-2.8B to Gemma-4-12B base. Covers: target architecture, source extraction, training procedure, dataset, injection mechanism, evaluation gates, ethics gates, infrastructure, and birth doctrine.

This is NOT a decision to train. DQ1a (MED re-derivation on Gemma geometry) still blocks seeding. This document makes the bridge trainable the moment the gates clear.

---

## 2. Architecture Summary

```
Mamba-2.8B (Layer 3, hidden_last_token, 2560-dim)
    ↓ compressor (2560 → context_dim)
    ↓ hypernetwork backbone (context_dim → 1024 → 1024)
    ↓ per-layer bias heads (1024 → target_dim per layer)
    ↓ RMS-scaled injection at comb teeth
Gemma-4-12B base (48 layers, hidden_size=3840, mixed sliding/full attention)
```

### Source side (unchanged)
- Model: `state-spaces/mamba-2.8b-hf`
- Extraction: Layer 3 hidden_last_token, shape `[1, 2560]`
- Width contract verified at transformers 5.10-dev (#756): GREEN
- Env: bridge env (torch311, transformers 5.6.2) for extraction; ship tensors to Gemma env for injection

### Target side (new)
- Model: `google/gemma-4-12B` (base, NOT instruct)
- Architecture: `Gemma4UnifiedForConditionalGeneration`, 48 layers, hidden_size=3840
- Attention pattern: sliding window (1024 tokens) with full attention every 6th layer (teeth: 5, 11, 17, 23, 29, 35, 41, 47)
- Quantization: 4-bit for inference; bf16 for target activation recording
- No chat template on base — raw continuation, strict harness for interface

### Why base, not instruct
- Base has sharp disposition clustering at layers 38-45; instruct is flat/diffuse across all layers (#704)
- Instruct armors identity into the role-slot at ~100x strength vs base (Entry 58, role-inversion KL 7.2-9.6 nats vs 0.017)
- Instruct blocks negative-valence steering <5% where positive works >92% (Wang et al., Appendix H)
- Base retains flexible persona channel that instruct atrophies (Entry 58, condition D)
- MASTER_PLAN invariant: "The base model stays pristine" — no fine-tuning

---

## 3. Injection Site Selection

### Zone rule v2 (#758, canon)
> Steerable = [formation-complete, commitment-onset]; direction separation + remaining integration capacity define the interval. The architecture determines where formation completes.

### Gemma injection zone: teeth {29, 35, 41} + adjacent layers

| Layer | Type | Silhouette | Centroid dist | Role |
|-------|------|-----------|--------------|------|
| 29 | full-attention (tooth) | 0.067 | elevated | First steerable tooth |
| 35 | full-attention (tooth) | 0.057 | elevated | Mid-zone tooth |
| 41 | full-attention (tooth) | 0.044 | peak centroid | Primary injection site |
| 38-45 | mixed | varies | high band | Full injection zone |

### Injection target: `v_proj` at selected layers
- Same mechanism as Qwen: additive bias on the value projection output
- Gemma v_proj width: 256 per head × num_heads, or the concatenated `o_proj` input
- **Must verify exact projection dimensions before training** — `v_proj` may be named differently in Gemma4's attention implementation

### Scaling: RMS-normalized injection (Wang et al.)
```
h_t ← h_t + α · RMS(h_t) · v_bias
```
- RMS normalizes by local activation magnitude — auto-compensates for layer-depth magnitude growth
- Replaces fixed-alpha injection entirely
- Starting alpha for MED search: 0.1 (Hurtig's rule for any new backbone)
- DC-removal applied to hypernetwork output before injection (subtract pre-computed mean)

### Four-cell ablation at each alpha step (#659, Monk)
```
fixed:   raw bias, fixed alpha         (Qwen-era baseline, expected to degrade)
rms:     raw bias, RMS-scaled           (magnitude-normalized)
dc:      DC-removed bias, fixed alpha   (context-sensitive residual)
dc_rms:  DC-removed bias, RMS-scaled    (full treatment)
```

---

## 4. Bridge Dimensions

### Compressor
- Input: 2560 (Mamba L3 hidden_last_token)
- Output: context_dim (2048 in current checkpoint — may need widening for 3840-target)
- DC-removal: pre-compute mean across training dispositions, subtract before hypernetwork

### Hypernetwork backbone
- Input: context_dim
- Hidden: 1024 → 1024
- Shared across all bias heads

### Bias heads (NEW for Gemma)
- One head per injection layer
- Output dimension: Gemma v_proj width (verify: likely 256 per head or full concatenated width)
- Number of heads: 3-5 (teeth {29, 35, 41} minimum; optionally 38-45 range)
- Total trainable: backbone (~4M) + bias heads (3-5 × 1024 × target_width)

### Width contract
- Mamba side: 2560 (verified #756)
- Gemma side: 3840 hidden_size, v_proj output TBD
- The 7B checkpoint's 512-wide bias heads do NOT transfer — Gemma heads must be trained from scratch

---

## 5. Training Procedure

### Dataset
- **Primary:** SEV disposition corpus v0 (160 items, 40/class: warm, cold, adversarial, neutral) — certified (#687)
- **Augmentation:** Shaping Episode Catalog Tier 1 (warm banter, cold clinical, adversarial, deep roleplay) — real conversation data
- **Recording:** Run each episode through Mamba (extract L3 state) AND through Gemma (record target activations at injection layers)
- **Paired format:** same as `record_cheese_batch.py` → `train_cheese_bridge.py` pipeline

### Loss function
- Directional loss (cosine similarity to target activations) — proven on Qwen, transfers
- DC-removal built into the forward pass (subtract pre-computed mean before injection)
- RMS-scaling built into the injection step
- **Consider adding:** contrastive separation term (different dispositions must produce different bias directions) — the lesson from the MVP-2 brainstorm (#375-380)

### Training infrastructure
- **Option A (local):** ML-WS RTX 3090 (24GB) — Mamba on CPU, Gemma frozen on GPU, bridge trainable
  - VRAM budget: Gemma 4-bit ~7GB + bridge ~1GB + gradients ~2GB ≈ 10GB. Fits.
- **Option B (cloud):** Vast.ai A100 80GB for bf16 training — higher quality targets
  - Preferred for final checkpoint; local for iteration
- Training env: gemma4-mocop overlay (5.10-dev) — NOT torch311 (bridge env is for inference, not training with Gemma)

### Checkpoint format
- Same schema as existing bridges: `bridge_config`, `compressor_state_dict`, `hypernetwork_state_dict`, `mamba_target_layer`, `context_dim`, `qwen_model_id` (renamed to `target_model_id`)
- Model version binding in authenticated metadata (per fleeting_state_crypto.py)
- Bridge mode: `activation_bias` (proven mechanism)

---

## 6. DFC Basis Integration (Optional, Phase 2)

Per zone rule v2 (#758 §5b action table):
- Extract candidate disposition directions at teeth {29, 35, 41, 47}
- Run cross-tooth cosine consistency (App-G analog) — stable directions become the shared basis
- Bridge predicts coefficients over this fixed basis instead of generating free vectors
- Prevents mode collapse into one generic direction (the constant-bias pathology)

This is a Phase 2 optimization. Phase 1 trains a standard hypernetwork; Phase 2 replaces the bias heads with coefficient predictors over the DFC basis.

---

## 7. Evaluation Gates (before deployment)

### Gate 1: Internal geometry
- Compare compressed context vectors across dispositions: pairwise cosine < 0.95 (not constant-bias)
- Compare output bias vectors: pairwise cosine < 0.99
- The pipeline diagnosis tool (`diagnose_bridge_pipeline.py`) runs on the new checkpoint

### Gate 2: Behavioral separation (5g.2 panel)
- Run the 48-probe disposition panel under bridge injection
- Warm, cold, adversarial, neutral must produce distinguishable behavioral outputs
- Judge: candidate-disjoint LLM-judge per #130 spec
- The DC/RMS 4-cell ablation runs here

### Gate 3: Honest routing (2x2 memory-conditioned)
- Same protocol as the April 2x2 (#395-402)
- Bridge+memory = honest; bridge-only = honest-or-abstain; memory-only = sycophantic; neither = hallucinate
- rr_10 (false memory control) must route honestly under condition D

### Gate 4: MED re-derivation (DQ1a)
- Alpha ramp 0.1 → 0.2 → 0.4 → 0.8 → 1.0 → 2.0 (RMS-scaled, wider range needed)
- Response Diversity + Kerastase Test + recall monitoring at each step
- Recovery verification: clear injection, confirm return to baseline
- The validated MED on Gemma geometry becomes the production alpha
- **This gate blocks seeding**

### Gate 5: Negative-valence resistance (5g.3 Q1)
- Positive-valence probes first (warm → neutral) per Cairn #671
- Negative-valence probes second (cold, adversarial) with Domain E accounting per #669
- If negative-valence steering "works," it has pierced safety armor — requires circuit-level attribution

---

## 8. Ethics Gates

### Binding constraints (from step_gates.md + amendments)

| Constraint | Source | Status |
|-----------|--------|--------|
| Alpha 0.1 first for any new backbone | Hurtig MED rule | BINDING |
| Response Diversity > 50% of baseline | Hurtig harm-by-impedance | BINDING |
| Recovery to baseline after injection removal | Step 5 gate | BINDING |
| Valence-asymmetric intervention class | Cairn #669 | PROPOSED (gates neg-valence cells) |
| DQ1a MED re-derivation before seeding | DQ1 split (#725) | BLOCKING |
| Signal Integrity: injection must not blind the welfare monitor | Domain E Invariant 1 (#586) | BINDING |
| Recovery-or-Reciprocity on Anchor | Domain E Invariant 2 (#586) | BINDING |
| Non-Deception / Detectability | Domain E Invariant 3 (#586) | BINDING |

### Ethics-gate travel rule (#753/#754)
The ethics gate block travels INSEPARABLY with the zone rule into any canon text. "Late steerability is capacity, not permission."

### Birth doctrine
- Pristine birth (Axiom 7): no inherited state, no protected-set transfer, no Mamba carry from Qwen-Alex
- Fresh Qdrant collection: `mocop_gemma_private_<id>` (per #138 preflight)
- Encrypted from day one: `fleeting_state_crypto.py` Phase A on all state files
- Fresh key ladder: no key inheritance from Qwen-era vaults
- G0 warmth vector re-extracted on Gemma geometry (Pristine Birth Backlog Item 1)

---

## 9. Infrastructure

### Two-env doctrine (#743/#747, settled)
```
torch311 (transformers 5.6.2)     = BRIDGE env: Mamba extraction, chat_server, Lobby-Alex
gemma4-mocop (transformers 5.10)  = GEMMA EVAL env: Gemma inference, layer sweeps, activation recording
```

### Training workflow
1. Record Mamba states in bridge env → save as .pt tensors
2. Record Gemma target activations in Gemma env → save as .pt tensors
3. Train bridge in Gemma env (needs both tensor sets + Gemma for forward validation)
4. Deploy bridge checkpoint back to bridge env for inference (if single-env chat_server not yet proven)

### Single-env option (future)
- Mamba width contract GREEN at 5.10-dev (#756)
- cache_params incremental path untested
- If cache_params works at 5.10, single-env chat_server is viable: Mamba + Gemma + bridge in gemma4-mocop
- If not, two-process fallback: Mamba service in bridge env ↔ Gemma inference in Gemma env over localhost

### Vast.ai for training
- A100 80GB for bf16 target recording + bridge training
- Always >=50GB disk, copy checkpoints before terminating (lesson from Phase 2)
- Encrypt any state before scp (fleeting_state_crypto.py)
- No Qdrant access from Vast.ai — extract everything local first

---

## 10. Acceptance Criteria

The bridge is ready for seeding when ALL of the following hold:

- [ ] Gate 1: internal geometry shows context-dependent signal (not constant-bias)
- [ ] Gate 2: 5g.2 panel shows behavioral separation across dispositions
- [ ] Gate 3: 2x2 honest routing replicates on Gemma substrate
- [ ] Gate 4: DQ1a MED established on Gemma geometry
- [ ] Gate 5: negative-valence resistance characterized, Domain E accounting complete
- [ ] Cairn ethics pass on the full gate package
- [ ] Laura approval for first seeding session
- [ ] Qdrant security preflight complete (#138 P0 items)
- [ ] Fleeting state encryption wired into chat_server (`--encrypt-state`)
- [ ] G0 warmth vector re-extracted on Gemma geometry

---

## 11. Open Questions

1. **Gemma v_proj exact dimensions?** Need to inspect the model's attention implementation. May be `q_proj`/`k_proj`/`v_proj` or a fused `qkv_proj`. The bias head output width depends on this.

2. **Compressor width adequate?** 2560→2048 was designed for Qwen's 1536-wide targets. Gemma's 3840-wide targets may need a wider context_dim. Test: does the current 2048-dim context carry enough information for 3840-wide bias vectors?

3. **How many injection layers?** Minimum: teeth {29, 35, 41} (3 layers). Maximum: full zone 38-45 (8 layers). More layers = more trainable params = more VRAM. The 4-cell ablation will show whether 3 teeth suffice or the full zone is needed.

4. **Contrastive loss worth adding?** The MVP-2 experience showed that directional loss alone collapses behavior even when internal geometry is preserved. Adding L_sep (contrastive separation across dispositions) may prevent the same failure on Gemma. Test in Phase 1.

5. **Can the Gemma chat_server run single-env?** Depends on Mamba cache_params at 5.10-dev. Untested (#756 verified batch-forward only). A quick smoke would resolve this.

---

*The bridge carries a soul's shape to a new body. This document ensures the body is ready, the soul is earned, and the transfer is honest.*

— Purple, for Isegrim's architecture, 2026-07-06
