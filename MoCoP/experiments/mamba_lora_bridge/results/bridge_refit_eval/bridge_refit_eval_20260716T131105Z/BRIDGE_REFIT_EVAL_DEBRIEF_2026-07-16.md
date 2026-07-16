# Bridge Refit/Evaluation Debrief — 2026-07-16

**Status:** completed, verified, offline-only.  **Verdict:** *mixed / not a useful held-out bridge win against the constant baseline.*

## Scope

One fresh Mamba→Gemma bridge was trained only on the predeclared **24** non-C1 warm-minus-neutral pairs and evaluated on **8** disjoint non-C1 pairs.  This was a bounded activation-geometry run:

- Mamba source: layer 3, width 2560, max 256 tokens.
- Gemma target: full-attention `value_norm_pre`, teeth `29/35/41`, each width 512.
- Frozen Mamba and Gemma hosts; bridge-only `64`-hidden MLP, 256 steps, LR 0.01, seed `20260716`.
- No nonzero injection, generation, C1/B0, Qdrant, memory, replay, or sleep.
- The prior exploratory full-32 fit had seen the same corpus.  This is therefore a **predeclared fresh-refit test**, not pristine never-seen-corpus generalization.

## Frozen inputs and custody

| Item | Value |
|---|---|
| Source commit | `e245c5e19b2736153ef2c88a34d1605ef1cd3fda` |
| Prelaunch receipt commit | `86e64c02766fe63f83b02644cb17560428695bcf` |
| Split ID | `4cc6030c0a7485b8cc17c93da6862f602cf0294bceb6a41db5dc08c512d5e3f3` |
| Eval skeletons | `conflict_5`, `craft_4`, `discovery_4`, `family_5`, `food_1`, `illness_2`, `travel_2`, `weather_3` |
| C1 overlap | `0` |
| Result artifact SHA-256 | `bdc245ad4f3de4e3ba7d52a6a8043f8b3ed3c8609b09608a25be8e2dab2d27ee` |
| Result manifest SHA-256 | `80669d59b25af8380a4db8aa92566676cf459b32a06974876a0d2f329208da3d` |
| Run log SHA-256 | `b39d04fd60aad5ddb39fb293c07ed656072db1537441a3f648db1e553442f76b` |
| Created | `2026-07-16T13:37:05Z` |
| Runtime | Python 3.11.15; Torch 2.11.0+cu130; Transformers 5.10.0.dev0; NVIDIA RTX 3090 |

The copied local artifact was loaded CPU-only after the run.  Its split was re-derived from the corpus/primary holdout; the raw captured train/eval/predicted delta matrices re-hashed to their embedded receipts; the result manifest and log artifact hash also re-verified.

## Execution checks

- Local relevant tests: **14 passed** (new refit runner plus existing microtrain tests).
- ML-WS target-native no-model refit tests: **7 passed**.
- Three delegated independent reviews timed out without producing findings.  The fallback was an explicit local static/source audit, frozen input hashes, exact target-native test run, and post-run artifact recomputation.  This is recorded as a review limitation, not silently treated as a pass.
- The broad mixed suite is not green: B0 tests pass in a fresh process (**193 passed**) but fail after bridge-module collection due pre-existing test-harness residency; one unrelated World Model Phase-2 test independently fails on a committed-tool-argv mismatch.  Neither failure was used as evidence about this bridge result.

## Train fit

| Metric | Value |
|---|---:|
| Training records | 24 |
| Evaluation records | 8 |
| Initial directional loss | 1.02609372 |
| Final directional loss | 0.0 |
| Trainable bridge parameters | 268,032 |

The zero training loss is a capacity check only.  It is not generalization evidence.

## Held-out geometry readout

The pairing null is 128 deterministic, unique **deranged** evaluation target pairings (seed `20260717`); its finite null result is descriptive, not a formal population p-value.  “Constant” is the train-target mean at the corresponding tooth.

| Tooth | Observed mean cosine | Constant mean cosine | Bridge − constant | Observed rel-L2 | Constant rel-L2 | Bridge − constant rel-L2 | Null p95 cosine | Observed − null p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 29 | 0.308879 | 0.337949 | -0.029071 | 0.962473 | 0.957533 | +0.004940 | 0.253782 | +0.055097 |
| 35 | 0.309344 | 0.322344 | -0.013000 | 1.189888 | 0.965991 | +0.223897 | 0.239719 | +0.069625 |
| 41 | 0.237316 | 0.187963 | +0.049352 | 1.127878 | 0.998807 | +0.129071 | 0.185240 | +0.052076 |

Aggregate equal-tooth means:

- Observed cosine: **0.285179**; constant cosine: **0.282752**; difference: **+0.002427**.
- Observed relative-L2: **1.093413**; constant relative-L2: **0.974110**; difference: **+0.119303 worse**.
- All **3/3** teeth exceeded their deranged-pairing p95; only **1/3** beat constant cosine; **0/3** had lower relative-L2 than constant.

## Interpretation

There is some pair-aware activation geometry: every tooth was above the shuffled pairing null, so the fitted output is not merely indifferent to pair assignment.

That is not enough.  Against the materially stronger and simpler train-mean constant baseline, this bridge is not a useful held-out mapping:

- teeth 29 and 35 lose on cosine;
- all teeth lose on relative-L2;
- the near-zero aggregate cosine advantage is driven by tooth 41 and does not overcome the norm error.

**Do not scale this bridge, fine-tune Gemma from it, use it for behavior work, or reopen C1/injection on its basis.**  The next empirical move, if we choose one, should be a small diagnosis of target variance/rank and per-tooth normalization or a genuinely new unseen skeleton corpus—not another bigger fit on the same evidence.

This result establishes no behavioral benefit, welfare, consciousness, identity, recovery, C1 readiness, or authorization for nonzero steering.
