# Bridge Refit Variance / Rank / Norm Diagnostic — 2026-07-16

**Status:** completed, verified, retrospective, CPU-only.
**Verdict:** *not a norm-only failure; held-out directional/subspace transfer remains the dominant problem.*

## Question

The preceding 24/8 bridge refit was pair-aware against a deranged-pairing null but did not beat the train-target-mean constant baseline in useful held-out geometry.  This bounded follow-up asked:

1. Are the Gemma target deltas so low-rank that a small bridge should have been able to recover them?
2. Is the held-out relative-L2 failure mainly an omitted per-tooth scale/norm calibration?
3. After fitting any such calibration **only on the 24 train rows**, does it improve the frozen eight-row evaluation?

This is a retrospective diagnosis of the existing result, **not** a new bridge fit or a pristine-generalization test.

## Scope and custody

| Item | Value |
|---|---|
| Source bridge artifact | `bridge_refit_eval_20260716T131105Z.pt` |
| Source artifact SHA-256 | `bdc245ad4f3de4e3ba7d52a6a8043f8b3ed3c8609b09608a25be8e2dab2d27ee` |
| Split ID | `4cc6030c0a7485b8cc17c93da6862f602cf0294bceb6a41db5dc08c512d5e3f3` |
| Source runner SHA-256 | `bd7774d01fbeafa2bb67caf19f9e454966aa2792210111d0cad74b39a92b751c` |
| Diagnostic JSON | `bridge_refit_norm_rank_diagnostic_20260716T145624Z.json` |
| Diagnostic JSON SHA-256 | `809ec86e7c37afb491ecdcf9b6c57a774e5aa5492a31d00d125b35ef72e9dcb4` |
| Diagnostic runner SHA-256 | `e754061e9c687dec47a314cb5e1f0ef0da0f4e7a1a5f60254f3ed25af4b0c5a6` |
| Diagnostic runtime | local CPU; Python 3.10; Torch local runtime |

The diagnostic re-hashed every captured train/eval/predicted delta receipt, rehydrated only the saved 64-hidden bridge on CPU, and re-derived the stored held-out prediction metrics.  It did **not** load Mamba or Gemma.  CPU reproduction of the saved ML-WS eval matrices passed at `atol=rtol=1e-5`; maximum absolute coordinate differences were `3.58e-07`, `4.77e-07`, and `3.58e-07` at teeth 29/35/41 respectively.

The original `.pt` was re-hashed after analysis and remained unchanged.  No GPU, activation capture, training, C1/B0, injection, generation, Qdrant, memory, replay, or sleep occurred.

## Method and leakage boundary

All spectra use centered row matrices.  “Effective rank” is the entropy effective rank of the finite sample spectrum; it is **not** a population-rank estimate.  With 24 train rows and eight evaluation rows, numerical rank is bounded by 23 and seven respectively.

For each tooth, the diagnostic retained the source artifact's saved held-out predictions and reconstructed train predictions from the bridge state dict.  It then compared four readouts:

1. **Original** — saved bridge predictions, unchanged.
2. **Train vector-L2 scale** — one nonnegative least-squares scalar per tooth fitted only on the 24 train prediction/target vectors.
3. **Train affine norm** — `target_norm = slope × predicted_norm + intercept`, OLS-fitted only on 24 train rows; evaluation target norm is never used to fit it.
4. **Oracle eval target norm** — each held-out prediction rescaled to its own true held-out target norm.  This is deliberately label-leaking and appears only to separate magnitude from direction error; it is not a deployable method.

Positive scale/norm changes preserve cosine direction.  The existing train-mean constant baseline remains the decision baseline; this diagnosis does not replace it.

## Target and prediction spectrum

| Tooth | Target train effective rank / max 23 | Target eval effective rank / max 7 | Prediction train effective rank / max 23 | Prediction eval effective rank / max 7 | Eval target PC1 energy | Eval prediction PC1 energy |
|---:|---:|---:|---:|---:|---:|---:|
| 29 | 18.905 | 6.446 | 16.235 | 4.128 | 0.261 | 0.533 |
| 35 | 18.537 | 6.196 | 16.119 | 3.908 | 0.304 | 0.563 |
| 41 | 17.483 | 5.122 | 16.324 | 4.514 | 0.438 | 0.489 |

The source train matrix itself has effective rank **19.792 / 23**.  Thus this small sample does not support a “targets are essentially one or two directions” explanation.  The bridge predictions are somewhat less diverse than targets on train and conspicuously more concentrated on the held-out rows: prediction PC1 accounts for roughly half of held-out energy at every tooth, versus 26–44% for targets.

That is suggestive of a held-out output-subspace/concentration problem, not proof of a population mechanism.  Eight rows is a very small tribunal; it may not wear a powdered wig.

## Norm signal and train-only fits

| Tooth | Eval mean predicted / target norm | Train norm Pearson r | Eval norm Pearson r | Train affine norm R² | Train vector-L2 scale |
|---:|---:|---:|---:|---:|---:|
| 29 | 0.170 | -0.008 | 0.115 | 0.000063 | 4.719 |
| 35 | 0.964 | 0.148 | -0.295 | 0.021968 | 0.867 |
| 41 | 0.766 | 0.314 | 0.448 | 0.098639 | 0.944 |

Tooth 29 is strongly under-scaled in average held-out norm, but the train norm relationship is effectively absent.  The other teeth are closer in average scale yet also show weak, unstable norm association.  The affine train fits explain at most **9.9%** of train target-norm variance, so there is no evidence here for a reliable input-dependent norm predictor.

## Frozen held-out outcome

Mean cosine is unchanged by direction-preserving norm changes, so the table focuses on mean relative-L2.  Lower is better.

| Tooth | Original bridge | Train vector-L2 scale | Train affine norm | Oracle target norm | Existing train-mean constant |
|---:|---:|---:|---:|---:|---:|
| 29 | 0.962473 | 1.093249 | 1.264868 | 1.168435 | 0.957533 |
| 35 | 1.189888 | 1.119603 | 1.258865 | 1.168277 | 0.965991 |
| 41 | 1.127878 | 1.107415 | 1.247180 | 1.230574 | 0.998807 |

Findings:

- The train-only scalar helps teeth 35 and 41 slightly, but worsens tooth 29 and **does not beat the constant baseline at any tooth**.
- Train affine norm calibration worsens all three held-out relative-L2 scores.
- Even the illegal oracle norm rescale worsens all three scores.  With low directional cosine, forcing the correct vector length exposes rather than repairs the directional error.
- The original bridge still loses constant cosine at teeth 29 and 35, and only tooth 41 has a small cosine advantage.  No norm procedure changes that fact.

## Interpretation and decision

The previous non-win cannot be reduced to “the directional bridge was fine but forgot scale.”  Norm mismatch exists—especially tooth 29—but train-only normalization does not rescue held-out geometry, and perfect held-out norm knowledge would not do so either.

The most defensible reading is:

- the bridge has some pair-specific activation geometry (as the earlier deranged-pairing null showed);
- its held-out predictions are directionally/subspace-misaligned and more concentrated than the retained target variation;
- post-hoc norm calibration is **not** a justified next intervention.

**Decision:** do not deploy a per-tooth scale patch, scale this bridge, fine-tune Gemma from it, reopen C1, or infer behavioral/welfare/identity significance.  If this line continues, prefer a genuinely unseen skeleton corpus and a separately predeclared mapping/objective diagnostic over a larger same-corpus fit or an after-the-fact normalization trick.

This establishes no behavioral benefit, welfare, consciousness, identity, recovery, C1 readiness, or authorization for nonzero steering.

## Reproduction

```bash
cd MoCoP/experiments/mamba_lora_bridge
python3 spikes/analyze_gemma_value_norm_bridge_refit_diagnostic.py \
  --artifact results/bridge_refit_eval/bridge_refit_eval_20260716T131105Z/bridge_refit_eval_20260716T131105Z.pt \
  --out results/bridge_refit_diagnostic/<new-run-id>/<new-run-id>.json
```

The output path must be new; the writer atomically refuses overwrite.
