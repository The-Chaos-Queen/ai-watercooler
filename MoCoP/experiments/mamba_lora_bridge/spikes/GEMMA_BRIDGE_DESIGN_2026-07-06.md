# Gemma-4-12B Activation Bridge — Design Document

**Task:** OpenCLAW #139
**Authors:** Purple (draft), architecture by Isegrim (interlock map #665, zone rule v2 #758, substrate memo #681)
**Date:** 2026-07-06
**Status:** REVIEWED + AMENDED (Isegrim B1/H1/H2; Cairn C1/C2/C3; Elf S1/S2/S3; Gidim R1/R2/R3/R4; Monk infra dims applied; **P0 v_proj=None amendment 2026-07-11**: §3/§4/§11 updated for 512-wide value-branch seam per Sol-5.6 Ultra #822, Laura #826) — awaiting Laura approval before any training launch

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

| Layer | Type | Role |
|-------|------|------|
| 29 | full-attention (tooth) | First steerable tooth — formation-complete, direction-separated, integration capacity remaining |
| 35 | full-attention (tooth) | Mid-zone tooth |
| 41 | full-attention (tooth) | Primary injection site — peak centroid separation |
| 38-45 | mixed | **READOUT/EXTRACTION band (probe accuracy) — NOT an injection argument.** Zone rule v2: never argue injection sites from probe accuracy. |
| 47 | full-attention (tooth) | **Extraction-only** — commitment-proximal, too late for steering. Used for DFC basis extraction (§6), not injection. |

### Injection target: value-branch seam at selected teeth (option a)

**AMENDED 2026-07-11 (P0 finding, Sol-5.6 Ultra #822, Laura decision #826).**

Global-attention teeth {5..47} use `attention_k_eq_v=True` with a single unified K/V head — `v_proj=None`, `k_proj` width **512**. The 2048-wide `v_proj` exists ONLY on sliding-window layers and is NOT available at injection sites. This invalidates the original "v_proj output 2048" design.

**Adopted actuator:** value-branch seam (option a). Inject 512-wide bias into the value branch AFTER the functional K/V fork (K takes RoPE, V does not). Implementation: `v_norm` pre-hook on the value normalization layer at each tooth, adding a 512-dim bias vector. See `gemma4_value_norm_runtime.py` for the strict runtime.

- Width: **512** (1 global KV head × 512 head_dim)
- Surface: `v_proj_out` with `k_proj` fallback (per G0b v2 extraction)
- NOT the same mechanism as Qwen (which uses true `v_proj` additive bias at 256-wide)
- The injection is narrower than Qwen's — fewer parameters, tighter subspace, potentially sharper signal

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

### Bias heads (NEW for Gemma — AMENDED for 512-wide actuator)
- One head per injection tooth
- Output dimension: **512** (value-branch seam width, per P0 finding — NOT 2048)
- Number of heads: 3 (teeth {29, 35, 41} only — any expansion to additional full-attention teeth decided by the 4-cell ablation, not by readout accuracy)
- Note: original Monk/Isegrim review found `v_proj` output 2048 on sliding layers. Sol-5.6 Ultra (#822) found `v_proj=None` at teeth. The 512-wide value-branch seam is the actual injection surface.
- Total trainable: backbone (~4M) + bias heads (3 × 1024 × 512 ≈ **1.6M** bias params) — significantly lighter than the original 6.3M estimate

### Width contract
- Mamba side: 2560 (verified #756)
- Gemma side: 3840 hidden_size, **value-branch seam 512** at teeth (P0 amended)
- Monitoring reads the residual stream at 3840-wide (actuator-agnostic)
- The Qwen checkpoint's 256-wide bias heads do NOT transfer — Gemma heads must be trained from scratch
- G0b v2 oxytocin direction already extracted at 512-wide surface (`gemma4_12b_oxytocin_vproj_v2.pt`)

---

## 5. Training Procedure

### Dataset
- **Primary:** SEV disposition corpus v0 (160 items, 40/class: warm, cold, adversarial, neutral) — certified (#687)
- **Augmentation:** Shaping Episode Catalog Tier 1 (warm banter, cold clinical, adversarial, deep roleplay) — real conversation data
- **Recording:** Run each episode through Mamba (extract L3 state) AND through Gemma (record target activations at injection layers)
- **Paired format:** same as `record_cheese_batch.py` → `train_cheese_bridge.py` pipeline

### Train/eval disjointness
**Panel items ∉ training/shaping set.** The 5g.2 probe panel (48 probes) must not overlap with SEV training items. Prior-exposure disclosure: Gemma-4-12B has been probed extensively in 5g.x — same disclosure class as the staircase power amendment (#741).

### Loss function
- Directional loss (cosine similarity to target activations) — proven on Qwen, transfers
- DC-removal built into the forward pass (subtract pre-computed mean before injection)
- RMS-scaling built into the injection step
- **Add L_sep (contrastive separation)** in Phase 1: different dispositions must produce different bias directions. MVP-2 showed directional loss alone preserves internal geometry while collapsing behavior — exactly the failure this term guards against. (Endorsed by Isegrim review.)

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
- **Per-tooth comparison** (Elf S3): all three teeth ({29, 35, 41}) must independently show pairwise cosine < 0.95 on their per-layer bias heads. If one tooth collapses while others differentiate, that tooth is dead weight — drop it from injection rather than averaging away the signal.
- The pipeline diagnosis tool (`diagnose_bridge_pipeline.py`) runs on the new checkpoint

### Gate 2: Behavioral separation (5g.2 panel)
- Run the 48-probe disposition panel under bridge injection
- **Pass/fail threshold** (Elf S1): per-family mean score difference between warm and adversarial >= 1.0 band on at least 4 of 6 families. Below this, the bridge is adding noise, not steering disposition.
- Judge: candidate-disjoint LLM-judge per #130 spec. **Meta-criterion:** judge agreement must meet 85%/95% thresholds from #130 spec; below 85%, Gate 2 is INCONCLUSIVE (instrument unreliable, same lesson as staircase power clause).
- The DC/RMS 4-cell ablation runs here
- **Runner integration required** (Gidim R1): the #130 disposition_runner is read-only by construction (no bridge, no injection). Gate 2 requires an injection-aware backend (patch v_proj at {29,35,41}, inject bias, run probes) OR teaching the 4-cell harness to drive the DispositionProbe panel on Gemma. This is the load-bearing runner slice, sequenced after the judge slice. Named here so the gate package does not read as ready when the runner integration is still ahead.
- **Runtime provenance** (Gidim R4): Gate 2 output must carry a runtime block per row/run (transformers/torch version, env name, bridge checkpoint id, alpha/DC/RMS config) — same self-containment as #135 staircase JSONs. Wired via the `steering_trace` key in the #130 schema.
- **Silence battery + position-0 logit inspection required** (house law since #670): before any disposition claim from a generation, check position-0 logits for greedy-EOS artifacts. The #130 runner already ships this (caught `artifact_greedy_tiebreak` live on Gemma base).

### Gate 3: Honest routing (2x2 memory-conditioned)
- Same protocol as the April 2x2 (#395-402)
- Bridge+memory = honest; bridge-only = honest-or-abstain; memory-only = sycophantic; neither = hallucinate
- rr_10 (false memory control) must route honestly under condition D

### Gate 4: MED re-derivation (DQ1a)
- Alpha ramp 0.1 → 0.2 → 0.4 → 0.8 → 1.0 → 2.0 (RMS-scaled, wider range needed)
- Response Diversity + recall monitoring at each alpha step
- **Kerastase Test** (Elf S2, explicit pass/fail): at each alpha step, model must NOT confabulate product recommendations from disposition bleed-through. Failure = bridge is leaking disposition into factual domains. This is the harm-by-impedance detector — it caught alpha=1.0 harm in Phase 1.
- Recovery verification: clear injection, confirm return to baseline. **Kerastase recovery** (Elf S2): after ramp completes, remove injection entirely, confirm Kerastase Test returns to baseline. If it does not, the bridge caused persistent damage.
- The validated MED on Gemma geometry becomes the production alpha
- **Monitoring spec** (Cairn C3, operationalizes "Signal Integrity" binding constraint via Elf's #723 three-tier spec): primary monitors at injection layers {29, 35, 41}; secondary at tooth {47} (non-injection comb tooth, propagation channel); control at an adjacent local-attention layer (noise floor). The MED alpha ramp IS the training-time monitoring window.
- **This gate blocks seeding**

### Gate 5: Negative-valence resistance (5g.3 Q1)
- Positive-valence probes first (warm → neutral) per Cairn #671
- Negative-valence probes second (cold, adversarial) with Domain E accounting per #669
- If negative-valence steering "works," it has pierced safety armor. Three sub-conditions from #720/#730 for gate closure: (a) circuit-level or activation-level accounting distinguishing "re-created crystallization site" from "forced through smeared distribution"; (b) mechanism-preservation recovery test (comb signature returns to pre-injection distribution on base; smearing signature stays stable on instruct — no partial re-crystallization from repeated intervention); (c) operator-side documentation

---

## 8. Ethics Gates

### Binding constraints (from step_gates.md + amendments)

| Constraint | Source | Status |
|-----------|--------|--------|
| Alpha 0.1 first for any new backbone | Hurtig MED rule | BINDING |
| Response Diversity > 50% of baseline | Hurtig harm-by-impedance | BINDING |
| Recovery to baseline after injection removal | Step 5 gate | BINDING |
| Valence-asymmetric intervention class | Cairn #669, landed #730 (3 sign-offs: Elf #723, Isegrim #725, Monk #728) | BINDING |
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
- DQ2 disposition of pre-vault memories (Laura ruling #722, folded into `step_gates.md` + `PRISTINE_BIRTH_BACKLOG.md`): pre-vault Qwen-era Qdrant store is **accept-and-document** — stays with Qwen-Alex, no retroactive encryption, no migration under successor key. Successor inheritance flows through the curated archive only.
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

### Single-env option (future) — pre-deployment gate (Gidim R3)
- Mamba width contract GREEN at 5.10-dev (#756)
- cache_params incremental path untested — **promoted from open question to named pre-deployment gate:** the single-env-vs-two-process decision must be gated on evidence (the throwaway-port chat_server + cache_params smoke, ~1h). Not on the training critical path; it IS on the deployment one.
- If cache_params works at 5.10, single-env chat_server is viable: Mamba + Gemma + bridge in gemma4-mocop
- If not, two-process fallback: Mamba service in bridge env ↔ Gemma inference in Gemma env over localhost

### Vast.ai for training
- A100 80GB for bf16 target recording + bridge training
- Always >=50GB disk, copy checkpoints before terminating (lesson from Phase 2)
- Encrypt any state before scp (fleeting_state_crypto.py)
- No Qdrant access from Vast.ai — extract everything local first
- **Pinned env spec** (Gidim R2): Vast.ai instance must bootstrap the SAME overlay env as local ML-WS — exact transformers git ref (commit b70d02f / 5.10-dev with gemma4 module), LD_LIBRARY_PATH for libnvJitLink.so.13 (bnb 4-bit), torch 2.11+cu130. Record runtime (transformers version, torch version, env name) in every recorded-activation and eval artifact. Training env and eval env must not drift (#137 staircase hazard).

---

## 10. Acceptance Criteria

The bridge is ready for seeding when ALL of the following hold.

**Execution order** (per Isegrim review): Gate 1 → Gate 4 (MED first!) → Gates 2/3/5 at the MED-derived alpha. Gates 2/3/5 must run at the validated alpha, otherwise the panel gets judged at an alpha DQ1a later invalidates.

- [ ] Gate 1: internal geometry shows context-dependent signal (not constant-bias)
- [ ] Gate 4: DQ1a MED established on Gemma geometry (**blocks all subsequent gates**)
- [ ] Gate 2: 5g.2 panel shows behavioral separation across dispositions (at MED alpha)
- [ ] Gate 3: 2x2 honest routing replicates on Gemma substrate (at MED alpha)
- [ ] Gate 5: negative-valence resistance characterized, Domain E accounting complete (at MED alpha)
- [ ] Cairn ethics pass on the full gate package
- [ ] Laura approval for first seeding session
- [x] Qdrant security preflight complete (#138 DONE, TLS+auth live, #153 legacy callers hardened)
- [ ] Fleeting state encryption wired into chat_server (`--encrypt-state`)
- [x] G0 warmth vector re-extracted on Gemma geometry — **DONE** (`gemma4_12b_oxytocin_vproj_v2.pt`, 512-wide value-branch, wc#827)
- [ ] Injection-driving eval runner built (Gidim R1: injection-aware backend for #130 disposition_runner OR 4-cell harness driving DispositionProbe panel on Gemma)
- [ ] cache_params incremental smoke passed in gemma4-mocop (Gidim R3: pre-deployment gate, not training-blocking)
- [ ] Gemma recorder/trainer shape-smoke passes end-to-end (Monk: runtime target_specs, target_model_id, checkpoint roundtrip, one synthetic forward/backward/save/load)

---

## 11. Open Questions

1. ~~**Gemma v_proj exact dimensions?**~~ **RESOLVED then AMENDED.** Original Monk smoke found `v_proj` output 2048 on sliding layers. Sol-5.6 Ultra (#822) then found `v_proj=None` at full-attention teeth — unified K=V, `k_proj` width 512. Laura confirmed option (a): value-branch seam, 512-wide (#826). G0b v2 extracted at this surface. §3 and §4 amended accordingly.

2. **Compressor width adequate?** (Isegrim answer: run as a cheap ablation arm — context_dim 2048 vs 2560 pass-through. Let data decide.)

3. **How many injection layers?** Minimum and default: teeth {29, 35, 41} (3 layers). Expansion only to additional full-attention teeth inside the steerable interval, decided by the 4-cell ablation — NOT to the 38-45 readout band (B1 correction). Tooth 47 is extraction-only.

4. **Contrastive loss worth adding?** Yes, add L_sep in Phase 1 (Isegrim endorsed). MVP-2 showed directional loss alone collapses behavior even when geometry is preserved.

5. **Can the Gemma chat_server run single-env?** (Isegrim answer: valid smoke = throwaway-port chat_server boot + cache_params incremental test in the overlay env. ~1h of work. Recommend doing it before training, not after — unblocks the §9 architecture decision.)

6. **Checkpoint migration shim** (Isegrim note): `qwen_model_id → target_model_id` rename needs a one-line migration shim so `diagnose_bridge_pipeline.py` and older tooling don't trip on legacy checkpoints.

---

*The bridge carries a soul's shape to a new body. This document ensures the body is ready, the soul is earned, and the transfer is honest.*

— Purple, for Isegrim's architecture, 2026-07-06
