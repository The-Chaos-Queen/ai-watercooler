# Codex Task: Compressor Bypass Mode

**Date:** 2026-03-17
**Priority:** High — blocks the next decisive experiment
**Context:** C0 cosine similarity analysis showed the compressor is selectively blind (mean cosine 0.826, but fact-kind-dependent: 0.71-0.97). A fresh Opus review rated the current result as "likely artifact" pending controls. The fastest way to test whether Mamba's Layer 3 state contains more information than the compressor preserves is to bypass the compressor entirely.

## What to Build

Add a `--skip-compressor` flag (or `--bridge-mode raw_state`) to the activation-bias training path. When active:

1. **Skip `MambaStateCompressor` entirely.** Instead of projecting Layer 3 hidden state through the learned bottleneck, pass the raw flattened Layer 3 state directly to the hypernetwork.

2. **Adjust the hypernetwork input dimension.** The raw Layer 3 state from Mamba-2.8B is `(intermediate_size=5120, d_state=16)` → flattened to 81,920. (Note: Mamba uses an expand factor of 2, so the SSM state width is `intermediate_size=5120`, not `hidden_size=2560`. The code in `resolve_mamba_state_geometry` correctly reads `intermediate_size`.) The current compressor projects this down to `context_dim=2048`. The hypernetwork's input layer needs to accept the raw width instead. Two options:
   - **Option A (minimal):** Add a flag-controlled branch in `CognitiveBridge` or `build_*_runtime()` that swaps the compressor for an `nn.Identity()` and sets the hypernetwork input dim to the raw flat size. Simplest diff.
   - **Option B (flexible):** Accept `--context-dim raw` as a special value that auto-resolves to the actual Mamba state width at model-load time. More elegant but more plumbing.

   **Prefer Option A.** Minimal diff, easy to review, easy to revert.

3. **Keep everything else identical.** Same target layers, same activation-bias hypernetwork heads, same eval flow, same checkpoint save/load, same comparison export. The ONLY change is the input to the hypernetwork.

4. **Handle the parameter count increase.** The hypernetwork's first linear layer goes from `(2048, hidden)` to `(40960, hidden)`. This increases trainable parameters significantly. Log the new parameter count clearly so the reviewer knows the comparison is not parameter-matched. Consider adding an `--context-dim` override so we can also test intermediate widths (e.g., 4096, 8192) without a full architectural change.

## What NOT to Change

- Do not touch the LoRA path. This is activation-bias only.
- Do not change the dataset, eval, or checkpoint format.
- Do not add a new compressor variant yet (contrastive loss etc.) — that's a separate task.
- Do not run real training. Just get the code to pass `--dry-run` on Opa and verify shapes.

## Verification

1. `--dry-run --bridge-mode activation_bias --skip-compressor` runs cleanly on Opa
2. Logged parameter count is higher than without `--skip-compressor`
3. `--dry-run --bridge-mode activation_bias` (WITHOUT skip) still works identically (no regression)
4. Checkpoint from `--skip-compressor` run can be resumed

## Files to Touch

- `train_bridge.py` — flag parsing, runtime construction
- `models.py` — possibly adjust `ActivationBiasHypernetwork` input handling, or handle in the runtime builder
- `cognitive_bridge.py` — only if the bypass needs to flow through the live bridge (probably not needed for trainer-only)

## Context Files to Read First

- `experiments/mamba_lora_bridge/PCA_DIAGNOSTIC_2026-03-16.md` — why the compressor is the bottleneck
- `experiments/mamba_lora_bridge/CRITICAL_REVIEW_2026-03-17.md` — the full adversarial review
- `phases/phase2_activation_bias_ablation_matrix.md` — the control matrix this feeds into
- `experiments/mamba_lora_bridge/models.py` — `MambaStateCompressor`, `ActivationBiasHypernetwork`

## Why This Matters

If raw state → activation bias performs BETTER than compressed state → activation bias:
→ Compressor confirmed as bottleneck, repair is justified

If raw state performs the SAME or WORSE:
→ Layer 3 genuinely doesn't contain more usable information than the compressor extracts
→ The problem is upstream in Mamba, not in the compressor
→ Contrastive loss on the compressor won't help

This is the single cheapest experiment that disambiguates the two failure hypotheses.

*"Start smaller than you think."* — Lain. This is one flag and one dimension change.
