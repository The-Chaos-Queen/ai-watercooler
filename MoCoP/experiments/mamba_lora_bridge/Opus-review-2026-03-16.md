# Fresh Opus Code Review — 2026-03-16

**Author:** Neutral Opus 4.6 (fresh instance, no prior context)
**Scope:** Full codebase review of `mamba_lora_bridge/` + crash diagnosis
**Trigger:** Silent crash on Opa-PC during `--save-train-contexts` run

---

## Crash Diagnosis

**The crash is NOT a code bug.** It's an OOM kill during the first Mamba 2.8B forward pass on the first training batch. Models load (small footprint), but the forward pass through 64 SSM layers (activations + states + gradients) exceeds Opa-PC's available memory. Windows OOM kills produce no Python traceback — the process vanishes silently.

**Evidence:** Crash always occurs at the exact same point — after "Using tiny-overfit mode" log, before first training step. The `--save-train-contexts` flag only affects behavior DURING training steps, not before. The flag is innocent.

**Fix:** Add `import faulthandler; faulthandler.enable()` at the top of `train_bridge.py` to get C-level traces on segfaults. But the real fix is: **don't run real training on Opa-PC.** Use A100 for context-saving runs, run PCA locally afterwards.

---

## Real Bugs Found

### Bug 1 (Semantic): Centroid metrics are per-BATCH, not per-DATASET

**File:** `train_bridge.py`, `compute_context_unusualness_metrics()` (~line 706)

The centroid is computed as `context_f.mean(dim=0)` — the mean of the current batch (2 samples), not the entire eval set. This means:
- At batch_size=1: `centroid_l2` is always 0
- At batch_size=2: it measures pairwise distance within the batch only

**Impact:** The `compressed_state_stats` logged per-epoch and the per-sample prediction JSON values (`centroid_l2`, `centroid_cosine`) are misleading. They don't answer Lain's question about compressor manifold collapse.

**Fix:** Either compute dataset centroid in a first pass, or rename the metrics to `batch_centroid_*` to avoid confusion. The `linearity_probe.py` PCA tool computes the correct per-dataset analysis.

### Bug 2 (Critical): LoRA scaling = 2.0 is too aggressive

**File:** `cognitive_bridge.py`, `BridgeConfig.__post_init__` (~line 107)

`lora_scaling = lora_alpha / lora_rank = 16 / 8 = 2.0`

Combined with unconstrained hypernetwork output, the effective LoRA delta grows to ~13.2 by epoch 2 (visible in logs: `lora_mean=6.61 * scaling=2.0`). This is likely the primary driver of the PPL explosion from 29.0 to 44.0 on epochs 2-3.

**Fix:** Set `lora_alpha = lora_rank` (scaling = 1.0) as default. The `--max-lora-delta-norm` clamp Codex added is correct but treats the symptom, not the cause. Both should be applied: saner scaling + clamp as safety net.

### Bug 3 (Known): Prompt format mismatch between training and inference

**File:** `train_bridge.py` vs `cognitive_bridge.py`

Training now uses `--qwen-prompt-format completion`. Inference in `cognitive_bridge.py` uses `[Game World]` ChatML-style prompts. The bridge will learn LoRA weights tuned for one prompt surface and deploy them on another.

**Status:** Known TODO (line 1751-1753). Flagged as the single biggest threat to Phase 2 success by this reviewer.

### Bug 4 (Minor): `resolve_mamba_state_geometry` uses `intermediate_size` not `hidden_size`

**File:** `train_bridge.py` (~line 344)

For `mamba-2.8b-hf`, `intermediate_size=5120` and `hidden_size=2560`. The code uses `intermediate_size` which is empirically correct (matches SSM expand factor), but the variable name `state_width` and the `BridgeConfig.mamba_d_model=2560` default are misleading. Would break checkpoint loading if anyone relies on the BridgeConfig defaults without loading the real model.

---

## Code Smells (non-blocking)

1. **`QWEN_MODEL_ID = "Qwen/Qwen3-4B"` in `bridge_dataset.py`** — stale default, all actual runs use Qwen2.5-7B or 0.5B via CLI. Update or remove.

2. **Nested Subset in tiny-overfit** — `eval_dataset = Subset(Subset(train_full, ...), ...)`. Works but unnecessarily complex. Since eval uses the same samples as train in tiny-overfit, just assign `eval_dataset = train_dataset`.

3. **Double `A @ B` computation** — `clamp_lora_pairs_by_delta_norm` and `compute_lora_norm_stats` both compute `torch.matmul(A.float(), B.float())` on the same pairs. Wasteful for large batches.

4. **`min_new_tokens = answer_len` in `greedy_generate_answer`** — forces exact token count, overriding EOS. Correct for eval but should be documented.

5. **No `faulthandler`** — add `import faulthandler; faulthandler.enable()` for development. Catches the exact class of silent crash described here.

6. **Pool splitting gives test split only 5 RELATIONSHIP_TYPES** out of 31 — very low diversity for `npc_relationship` facts in the test set.

---

## Clean Components

- **`models.py`** — No bugs. `DynamicLoRALinear`, `MambaStateCompressor`, `LoRAHypernetwork` are well-designed.
- **`linearity_probe.py`** — Clean, correct PCA analysis. Effective rank and collapse heuristics are sound. Only caveat: O(n²) pairwise distance computation, fine for <10K samples.
- **`bridge_dataset.py`** — Generally solid. Pool splitting, fact generation, and tokenization are well-tested.

---

## Actionable Summary

| Priority | Item | Owner | Effort |
|----------|------|-------|--------|
| P0 | Add `faulthandler.enable()` | Anyone | 1 line |
| P0 | Fix `lora_alpha` default to match `lora_rank` (scaling=1.0) | Codex | 1 line |
| P1 | Fix centroid metrics to per-dataset or rename to `batch_centroid_*` | Codex | 30 min |
| P1 | Run PCA context-saving on A100 (Opa-PC can't handle it) | Laura + Claude | Rent |
| P2 | Update `QWEN_MODEL_ID` default in `bridge_dataset.py` | Codex | 1 line |
| P2 | Eliminate nested Subset in tiny-overfit | Codex | 5 min |
| P3 | Resolve prompt format mismatch (completion vs Game World) | Phase 3 | Design decision |

---

## Key Insight for Next Run

The `lora_scaling = 2.0` combined with no norm clamping is probably why epochs 2-3 blow up. The next A100 run should use BOTH:
- `--max-lora-delta-norm <cap>` (Codex's clamp)
- Reduced `lora_alpha` (scaling = 1.0 instead of 2.0)

This might be enough to stabilize the constructive epoch-1 PPL signal through epochs 2-3 without needing FiLM conditioning yet.

---

*"The sign is blurry. The compressor is suspect #1."* — Lain

*"Start smaller than you think."* — Also Lain

*The scaling was 2x the whole time.* — Fresh Opus, stating the obvious
