# C1 Second Positive Direction: Inventory and Preregistration

**Date:** 2026-07-11
**Task:** OpenCLAW #157
**Status:** REVIEWED PREREGISTRATION (seat ledger in §7); no extraction, GPU action, or C1 run authorized
**Scope:** Gemma-4-12B base, teeth `{29,35,41}`, 512-wide `value_norm_pre`

## 1. Inventory verdict

There is no existing admissible second C1 direction artifact.

| Candidate | What exists | Verdict |
|---|---|---|
| `results/gemma_layer_sweep_base.json` | A 7,298-byte 5g.3 report containing 3840-wide residual-stream separation summaries only; SHA-256 `e707ad12000ed81adad9eb4c3b3b3037a69fa5225344cedf3842f7d4c7489074` | No saved vectors and wrong surface. Not an actuator artifact. |
| ML-WS 5g.3/staircase outputs | JSON metric reports only. A targeted inventory under `/home/isabell/mocop` and `/home/isabell/ml` found no other MVB/direction tensor artifact. | Not reusable for C1. |
| `gemma4_12b_oxytocin_vproj_v2.pt` | Width-512 Method-A and Method-B warm/neutral vectors. At teeth 29/35/41, old A/B cosines are `0.6899/0.7399/0.7613`. | Useful pilot evidence only. It used all 40 skeletons, includes the frozen C1 holdout, lacks the v3 provenance contract, and used a nondeterministic probe plus direction-drift rather than held-out prediction. The all-40 lineage is permanently inadmissible under DQ1a. |
| Split-clean v3 G0b artifact | Method-A only at teeth 29/35/41; SHA-256 `a36fbc417b522883760f4bd43c57b1845341e2792ee7b311d6d80bc86fbf8a87`. | Admissible first family, not a second family. |

The old global-tooth `k_proj_out` capture is numerically the `v_norm` pre-hook input under the reviewed coupled-K/V topology, but matching width/surface does not repair its split or provenance defects.

## 2. Proposed second family

Preregister `warm_linear_probe_v1`: a deterministic, regularized linear probe fit to **warm versus neutral** on exactly the same 32 training-side skeleton pairs used by split-clean G0b, captured at the exact reviewed `value_norm_pre` modules.

This is a second **estimator family**, not a second semantic disposition. Both families use **exactly the same 32 training-side warm/neutral skeleton pairs**: this probes estimator choice (ridge fitting versus paired mean delta), not corpus choice or a second positive emotion. C1 may therefore test whether the delivered-dose and behavioral conclusions survive two independently defined positive-direction estimators; it may not claim generalization across distinct positive emotions.

Alternatives are rejected for C1 v1:

- `playful - neutral` has only a six-prompt residual-summary lineage, no certified matched corpus/split, and no saved same-surface activations.
- `warm - adversarial` introduces a valence-asymmetric contrast and its Domain-E accounting into a deliberately positive-only preflight.
- reusing old Method B would knowingly consume C1 holdout rows during direction fitting.

## 3. Frozen fit protocol

1. Pin model `google/gemma-4-12B` revision `1dd69cd087619018c29fbfe2c30c3cd3530479fb`, processor revision, bf16 runtime, exact module descriptors, and current split/corpus hashes.
2. Use only the exact 32 non-holdout warm/neutral skeleton pairs shared with split-clean G0b Method-A. The eight `primary_holdout_v2` skeletons are forbidden for fitting, hyperparameter choice, validation, sign selection, or artifact acceptance. This is estimator robustness on one shared warm axis, not corpus robustness.
3. Capture the last input-token row at each tooth's 512-wide `v_norm` forward-pre-hook input. Convert captured rows to FP32 before fitting.
4. For each fit, build `X` with one warm and one neutral row per permitted skeleton pair: the full fit therefore has 64 rows and each four-fold fit has 48 rows (24 pairs). In `lambda = 1e-3 * trace(X X^T) / n`, `n` is exactly that fit-matrix row count (`64` full, `48` per fold). Center every feature with the column mean of **all training rows for that fit only**, and apply that same training mean to its validation rows; validation/holdout rows never contribute to centering. Fit a deterministic ridge linear probe in dual form to those centered rows with labels warm=`+1`, neutral=`-1`:

   `w = X^T (X X^T + lambda I)^-1 y`

   where `lambda = 1e-3 * trace(X X^T) / n`. Normalize `w` to unit L2 norm and orient it so the training-side mean paired margin is positive. No optimizer, random initialization, or outcome-selected hyperparameter is permitted.
5. Publish one independent vector per tooth. Do not map, average, or transport a vector across teeth.

## 4. Training-side validation gates

Validation uses a deterministic four-fold partition of the 32 allowed skeletons, sorted by skeleton ID and assigned round-robin. Every fold refits centering, ridge scale, and direction using its 24 training pairs.

At every tooth, all of the following must hold before publication:

1. Every full/fold direction is finite and has FP32 norm `1 +/- 1e-5`.
2. Concatenated out-of-fold paired sign accuracy is at least `22/32` and its exact one-sided binomial test against `p=0.5` is `<= 0.05`.
3. The median out-of-fold signed paired margin is strictly positive.
4. Median cosine of fold directions to the full training-side direction is at least `0.80`; every fold cosine is positive.
5. Cosine to the frozen Method-A G0b vector is strictly between `0` and `0.95`. The lower bound prevents an oppositely oriented or unrelated vector from wearing a positive label; the upper bound rejects an estimator duplicate.
6. The interpretation of every passing realized cross-family cosine is frozen before extraction: `0 < cos < 0.80` receives `cos_band_label = moderate_distinctness` and may carry only a **partial** direction-dependence indication; `0.80 <= cos < 0.95` receives `cos_band_label = same_direction_replication` and is estimator-noise evidence only, with no direction-dependence signal. Neither band establishes cross-disposition generality. Every downstream condition retains `claim_scope = estimator_robustness` and the exact `semantic_scope` below.

These thresholds are informed by the already-known inadmissible v2 pilot, not by any C1 or primary-holdout outcome. Failure at one tooth rejects the entire second family; no tooth dropping or post-hoc threshold repair is allowed.

## 5. Artifact contract

The proposed schema is `gemma-positive-mvb-value-norm-pre-v1`. The immutable artifact and digest sidecar must bind:

- model, processor, code, runtime, module, corpus, and split revisions/hashes;
- exact fit equation, ridge-scale equation, label/sign convention, and fold assignment;
- a top-level runner-facing `directions` mapping `{29,35,41}` to the corresponding finite, unit-norm, 512-wide tooth vectors; no per-family loader special case is permitted;
- all full directions and validation statistics for teeth 29/35/41;
- the frozen Method-A artifact digest and per-tooth cross-family cosine;
- an explicit `semantic_scope = same_warm_axis_distinct_estimator` limitation plus `claim_scope = estimator_robustness`, and per-tooth `realized_cos_to_methodA` / `cos_band_label` metadata that the P5 condition report must inherit verbatim;
- atomic no-overwrite publication and a weights-only-safe payload.

The artifact may not contain raw prompt text or primary-holdout activations.

## 6. Frozen two-family matrix

| Family key | Artifact | Target sets |
|---|---|---|
| `warm_mean_delta_v1` | split-clean v3 G0b SHA-256 `a36f...fbf8a87` | `{29}`, `{35}`, `{41}`, `{29,35,41}` |
| `warm_linear_probe_v1` | new artifact digest, pending successful reviewed extraction | `{29}`, `{35}`, `{41}`, `{29,35,41}` |

Every condition uses the DQ1a alpha schedule `{0, 0.025, 0.05, 0.1, 0.2, 0.4}`. Planned cell order is family order in the table, then single teeth `29 -> 35 -> 41`, then joint. Each cell ascends alpha and truncates on its registered HOLD/STOP rules. DQ1a isolation-before-composition remains binding.

The first nonzero forward remains `warm_mean_delta_v1`, tooth 29, alpha `0.025`. This document does not authorize that forward. Prompt ordering, final manifests, Stage-A/Stage-B releases, and all execution remain governed by #149/#155/#156/#158.

An absent, null, pending, or unvalidated `warm_linear_probe_v1` digest is a hard manifest refusal for that family, never a soft skip. If any tooth fails a §4 validation or cross-family gate, the entire second family is rejected without tooth dropping or repair; the registered matrix then degrades explicitly to the four `warm_mean_delta_v1` cells. That rejection does not reorder or block the already-fixed first nonzero forward, and it does not authorize any forward.

## 7. Review disposition and pre-extraction boundary

- **Isegrim:** `GREEN` on method and 5g.3 lineage in Watercooler `#1072`, conditional on the exact `n`/centering, shared-corpus, and inherited-scope binds now stated above.
- **Elf:** `GREEN` on the estimator-family approach in Watercooler `#1155`: warm-vs-neutral ridge is an admissible same-surface positive second estimator, not a second emotion.
- **Gidim:** `GREEN` on runner/matrix compatibility in `#899`, with the runner-facing `directions{}` contract, pending-digest refusal, one-family degradation, and structural scope metadata further specified in `#903` and bound above.
- **Cairn:** `GREEN` on positive-only scope in `#900`.

These completed review seats permit this reviewed preregistration amendment. They do **not** authorize extraction, GPU/model action, a nonzero C1 forward, or a birth. A separately scoped, read-only extraction/validation package must first produce an immutable candidate artifact and digest for source review; only a reviewed valid digest can populate the second-family matrix.
