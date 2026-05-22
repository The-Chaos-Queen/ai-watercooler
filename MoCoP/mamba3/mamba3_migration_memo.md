# Mamba-3 Migration Scoping — Go/No-Go Memo

**Author:** Anda-Conda
**Date:** 2026-03-26
**Task:** OpenCLAW #66
**Probed on:** Opa-PC (RTX 3070, torch 2.10, Windows Python 3.13)

---

## Verdict

**Architecture: GO. Weights: BLOCKED.**

The hidden-state extraction path that the bridge uses is fully compatible with Mamba-3. Migration is blocked solely by the absence of pretrained 2.8B-scale weights on HuggingFace.

---

## What Was Tested

### 1. Mamba-2.8b Baseline (state-spaces/mamba-2.8b-hf)

Loaded via `MambaForCausalLM`. Established the exact bridge contract:

| Property | Value |
|----------|-------|
| Hidden layers | 65 (64 + embedding) |
| Layer 3 last-token shape | `[1, 2560]` |
| Compressor `input_flat_size` | 2560 |
| SSM cache per layer | `[1, 5120, 16]` = 81,920 scalars |

### 2. Mamba-3 Architecture (VikramKarLex/mamba3-minimal, random init)

Created a `Mamba3LMHeadModel` at d_model=2560 (matching Mamba-2.8b scale) with MIMO enabled:

| Property | Value |
|----------|-------|
| Config | d_model=2560, d_state=128, headdim=64, expand=2, mimo_rank=4 |
| Mixer output shape | `[1, 64, 2560]` |
| Last-token shape | `[1, 2560]` |
| Width match | **YES** — identical to Mamba-2 |
| SSM state per layer | `[80, 64, 128]` = 655,360 scalars (8x larger) |

### 3. HF Community Model (aifeifei798/Mamba3-MIMO-Tiny-HF)

d_model=256, ~130M params. Failed to load — `config.json` missing `model_type` field, `AutoConfig` rejects it even with `trust_remote_code=True`. Early community upload, not properly packaged. Too small for our bridge regardless.

---

## Go/No-Go Matrix

| Component | Status | Action Required |
|-----------|--------|-----------------|
| **Hidden-state path** (what the bridge uses) | **GO** | None. `[1, 2560]` in, `[1, 2560]` out. |
| **MambaStateCompressor** | **GO** | No reinitialization needed for hidden_last_token mode. |
| **ActivationBiasHypernetwork** | **GO** | Receives same-width context vector. No change. |
| **SSM state path** (not currently used) | **NO-GO** | Shape changes from `[5120, 16]` to `[80, 64, 128]`. Complete rewrite if ever needed. |
| **Pretrained weights** | **BLOCKED** | No 2.8B-scale Mamba-3 on HuggingFace as of 2026-03-26. Paper: arxiv 2603.15569 (March 16). |
| **HF transformers integration** | **BLOCKED** | No `MambaForCausalLM` support for Mamba-3. Needs custom model code or `mamba-ssm` built from source. |
| **Chunk-size alignment** | **NEW CONSTRAINT** | Mamba-3 requires sequence length divisible by chunk_size (16 or 64 depending on backend). `feed_mamba()` needs padding logic. |
| **Sleep replay compatibility** | **GO** | Sleep replays hidden-state vectors. Same width = same replay path. |

---

## When Weights Appear — Migration Checklist

1. Verify model loads via `MambaForCausalLM` or custom code with `trust_remote_code=True`
2. Run `probe_mamba3.py --model-id <new_id>` to confirm hidden-state contract
3. Add chunk-size padding to `feed_mamba()` / `cognitive_bridge.py`
4. Re-probe Layer 3 for disposition signal (Phase 1 linear probe equivalent)
5. If Layer 3 signal holds: retrain bridge checkpoint on Mamba-3 hidden states
6. If Layer 3 signal moves: run full layer sweep (Step 6 plan already exists)

---

## Artifacts

- `probe_mamba3.py` — reusable probe script for any HF Mamba model
- `probe_mamba2_baseline.json` — on Opa at `C:/Users/User/`
- `probe_mamba3_block.json` — on Opa at `C:/Users/User/`

---

*"The bridge doesn't care which gut it's reading — as long as the nerve endings are the same width."*
