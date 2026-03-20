# Codex Task Queue — 2026-03-15 (Post-Burst)

Context: A3 (contiguous mid-block layers 12-15, q+v, lr=2e-5) produced the first non-zero bridge signal. Two prompt surfaces tested (ChatML: 2/8 recall, completion: 1/8 recall but best PPL at 29.14 vs baseline 30.99). Next burst will scale A3 to 64 samples. These tasks prepare for that.

---

## Task 1: Disable 4-bit on A100 by Default

**File:** `train_bridge.py`
**Why:** We ran on A100-80GB with 81GB free VRAM. 4-bit quantization adds dequantization overhead for zero benefit on this hardware. The `--no-4bit` flag exists but the default is still 4-bit.

**What to do:**
- Add `--auto-precision` or similar flag that detects available VRAM and skips 4-bit when there's headroom (e.g., >40GB free after model estimate)
- OR: just add a log line warning when 4-bit is used on a GPU with >40GB free, so the operator knows to pass `--no-4bit`
- Do NOT change the default — just make it obvious when 4-bit is wasteful
- Verify `--no-4bit` actually works end-to-end (it may not have been tested recently)

---

## Task 2: Replace Python Token Loop with model.generate()

**File:** `train_bridge.py`, function `greedy_generate_answer` at ~line 567
**Why:** The eval loop uses a hand-rolled Python token-by-token generation loop. `model.generate(max_new_tokens=N, do_sample=False)` does the same thing but faster (fused kernels, KV cache management, etc.). On Pilot 1, eval took ~2 hours for 96 samples at batch-size 1. This is the biggest time sink.

**What to do:**
- Replace the Python loop with `model.generate(max_new_tokens=answer_len, do_sample=False)`
- There's already a TODO comment at line 573-574 saying exactly this
- Make sure the LoRA injection is still active during generate (the patched layers must stay patched during the forward passes inside generate)
- Test: run `--dry-run` and verify eval predictions match before and after the change
- If `model.generate()` doesn't respect the dynamic LoRA patches, document why and leave the Python loop

---

## Task 3: Reconstruction Error Logging (from previous queue)

**File:** `train_bridge.py`
**Why:** The compressor's per-sample reconstruction error might be a latent surprise signal. If samples the bridge struggles to compress correlate with semantic novelty, we have a proto-novelty detector for free.

**What to add:**
- During eval, log the `MambaStateCompressor`'s per-sample reconstruction loss (MSE between input hidden state and reconstructed state)
- Save to the eval JSON alongside existing metrics
- Format: `{"sample_id": N, "reconstruction_mse": float, ...}`
- Also log mean and variance of reconstruction error per epoch to the training log
- Append-only — do not change any existing behavior

---

## Task 4: Linearity Collapse Probe (from previous queue)

**File:** New script: `linearity_probe.py`
**Why:** Paper arXiv:2602.21204 showed TTT mechanisms can collapse to linear attention. We need to verify our hypernetwork is genuinely nonlinear. Now that we have working checkpoints (run_a3/bridge_best.pt), this is testable.

**What to build:**
- Load a bridge checkpoint
- Collect N input-output pairs from the hypernetwork (compressed Mamba states → generated LoRA A,B matrices)
- Fit a linear mapping via least squares
- Compute linearity_ratio = ||Y - Y_linear|| / ||Y||
- Print verdict and save to JSON
- Should work with both `run_a1/` and `run_a3/` checkpoints

---

## Task 5: Review Everything With Fresh Eyes

**Why:** You're a fresh instance. The codebase has been touched by multiple agents (Codex, Sonnet subagents, Claude). Things may have drifted.

**What to do:**
- Read `train_bridge.py` end to end. Flag anything that smells wrong.
- Verify `--qwen-model-id` flows through all paths (a Sonnet added this today)
- Verify `--qwen-prompt-format completion` flows through dataset generation AND eval (landed today by a previous Codex instance)
- Check `bridge_dataset.py` for any hardcoded assumptions about Qwen3-4B that break with Qwen2.5-7B
- Check if the `--target-layers` parser handles the A3 format correctly: `"12:q_proj,12:v_proj,13:q_proj,13:v_proj,14:q_proj,14:v_proj,15:q_proj,15:v_proj"`

---

## Context Files
- `MoCoP/mocop-review-lain.md` — architecture review, recommended simplification path
- `MoCoP/phases/phase2_a100_quick_tiny_overfit_plan.md` — the run plan with A3 as winner
- `MoCoP/experiments/mamba_lora_bridge/target_models.md` — 5 locked base models
- `MoCoP/experiments/mamba_lora_bridge/disposition_eval_spec.md` — future eval framework (shelved until bridge scales)
- `MoCoP/theory/TTT_as_Linear_Attention_2602.21204.md` — why we need the linearity probe

## Run Artifacts
- `run_a1/` — sparse default, ChatML, 1/8 recall
- `run_a3/` — contiguous q+v, ChatML, 2/8 recall (best recall)
- `run_a3_completion/` — contiguous q+v, completion prompts, 1/8 recall but best PPL (29.14)
- `run_a4/` — contiguous v only, ChatML, 1/8 recall, worst PPL

## Status Update (Purple, 2026-03-19)

**This task queue is largely SUPERSEDED by the activation-bias discovery.** The A3 tiny-overfit framing is historical; the live question is now the activation-bias control hierarchy (per-sample > fixed_mean >> constant_bias) and Step 5 substrate change.

| Task | Status | Notes |
|------|--------|-------|
| 1: 4-bit flag | **DONE** | `--no-4bit` flag works. WARNING log added when >40GB free. No `--auto-precision` but warning suffices. |
| 2: model.generate() | **DONE** | `greedy_generate_answer()` now uses `qwen_model.generate()` with fallback. |
| 3: Reconstruction error | **DONE** | `train_bridge.py` now writes per-sample `reconstruction_mse` rows to `eval_epoch_*_reconstruction.json`, mirrors the metric into saved prediction rows, and logs mean/variance per eval epoch via a logging-only affine decoder fit on train contexts. |
| 4: Linearity probe | **DONE** | `linearity_probe.py` exists (762 lines). Supports both `context-pca` and `hyper-linearity` modes. |
| 5: Fresh review | **DONE** | `--qwen-model-id`, `--qwen-prompt-format`, `--target-layers` all verified flowing through. |

### Post-Activation-Bias Artifacts (added since this queue was written)
- `baseline_solvability_probe.py` — D1 gate test
- `bias_analysis.py` — bias norm/cosine/PCA analysis
- `run_actbias/` — primary activation-bias run (winner)
- `run_constant_bias/`, `run_constant_bias_10ep/`, `run_constant_bias_seed42/` — Step 4 controls
- `run_bypass_raw/` — Step 2 compressor bypass (failed)
- `step1_c3_fixed_mean_no4bit/` — C3 fixed-mean control
- `activation_sessions/` — Cassian's disposition evidence experiment

## Original Priority Order (historical)
5 (fresh review) → 2 (generate speed) → 1 (4-bit flag) → 3 (reconstruction logging) → 4 (linearity probe)

*Start smaller than you think.* — Lain
