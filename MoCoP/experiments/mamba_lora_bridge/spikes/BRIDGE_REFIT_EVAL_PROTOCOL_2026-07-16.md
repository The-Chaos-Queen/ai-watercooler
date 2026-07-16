# Gemma Value-Norm Bridge Refit/Eval Protocol — 2026-07-16

**Status:** pre-run protocol for one bounded offline refit/evaluation slice under OpenCLAW #146.

## Question

After the 2026-07-11 full 32-pair in-sample bridge fit, can a **freshly initialized**, bridge-only map align Mamba Layer-3 matched deltas with Gemma-4-12B `value_norm_pre` matched deltas on a predeclared disjoint slice?

This protocol measures activation-space geometry only. It does not test behavioral benefit, welfare, consciousness, identity, recovery, C1 readiness, or authorization for injection.

## Fixed scope and prohibitions

- Mamba 2.8B and Gemma 4 12B remain frozen/eval-only.
- Source: Mamba Layer-3 last-token `warm - neutral` delta, width 2560.
- Target: Gemma `full_attention_value_norm_pre` `warm - neutral` delta, width 512, teeth 29/35/41.
- Trainable state: a new bridge only; hidden width 64, 256 full-batch AdamW steps, learning rate 0.01, bridge seed 20260716.
- No nonzero injection, text generation, C1/B0 execution, Qdrant, memory, replay, sleep, persistence route, or model-weight change.
- All artifacts use no-overwrite publication.

## Split contract

The C1 primary holdout remains untouched. The refit/eval split is constructed only from the 32 frozen non-C1 warm/neutral pairs.

1. Group those pairs by their existing topic.
2. For each skeleton, hash canonical full-corpus rows under the fixed domain string `mocop-bridge-refit-eval-v1`.
3. Select the lexicographically lowest digest in each topic as evaluation.
4. Train on all remaining non-C1 warm/neutral pairs.

The resulting manifest must contain exactly 8 topic-stratified evaluation pairs and 24 training pairs, bind corpus and primary-holdout hashes, and be re-derived/validated before capture. No result or model behavior may influence membership.

## Evaluation receipt

On the 8 evaluation pairs, the runner reports per tooth:

- predicted-versus-observed mean/median cosine and relative L2 norm error;
- comparison with the train-target mean-vector constant-output baseline;
- a 128-sample deterministic **deranged target-pairing** null distribution, including observed percentile and 5/50/95 percentiles;
- raw captured source/target delta matrices in the no-overwrite artifact, bound to scenario IDs and hashes.

No automatic GO, no safety threshold, and no C1 conclusion follows from this small N=8 readout. It is an evidence-bearing refit test. Since the 2026-07-11 exploratory bridge was fitted on all 32 non-C1 items, this is **not** a pristine never-before-seen-corpus claim.

## Required evidence

- validated split manifest and SHA-256;
- code/protocol/corpus/primary-holdout hashes;
- explicit model/revision/runtime/device fields;
- fresh checkpoint plus raw captured-delta artifact and evaluation receipt;
- local/remote artifact hash equality, reload/finiteness/shape checks, GPU-idle readback;
- exact launch command and field-report log.
