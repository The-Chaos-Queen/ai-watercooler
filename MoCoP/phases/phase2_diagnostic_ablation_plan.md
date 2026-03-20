# Phase 2 Diagnostic and Layer-Targeting Ablation Plan

Current as of 2026-03-16

## Purpose

Pilot 1 answered the operational question, not the scientific one.

The bridge run finished cleanly, produced checkpoints, and proved the cloud path works. It did **not**
produce useful bridge behavior. The next step is targeted diagnosis, not blind scale-up.

This document defines the debug ladder for locating the weakest link before spending on another
multi-hour cloud session.

## Sweden Scale-Up Update (2026-03-16)

The `64`-sample A3 completion burst on a Sweden `A100 SXM4 80GB` answered the generalization question for the current bridge shape:

| Epoch | Recall | Bridge PPL | Baseline PPL | Train Loss |
|---|---|---|---|---|
| 1 | 0/16 | 28.96 | 29.71 | 4.25 |
| 2 | 0/16 | 44.06 | 29.71 | 3.07 |
| 3 | 0/16 | 43.15 | 29.71 | 2.33 |

Interpretation:

- train loss drops, so the bridge is fitting the training distribution
- held-out recall stays at floor, so there is no evidence of fact transfer on disjoint eval samples
- epoch 1 shows a real early steering signal because bridge perplexity briefly improves over baseline
- epochs 2-3 show the familiar over-injection pattern returning
- the earlier `2/8` tiny-overfit result should now be treated as shared-set memorization, not proof of transfer

Consequence:

- the simplification gate is now active
- do not spend more cloud budget scaling the current multi-head dynamic-LoRA setup

## Simplification Gate Update (2026-03-17)

The first `activation_bias` run materially changes the order of operations.

Observed result:

| Epoch | LoRA PPL | ActBias PPL | Baseline PPL |
|---|---|---|---|
| 1 | 28.96 | 27.09 | 29.71 |
| 2 | 44.06 | 25.95 | 29.71 |
| 3 | 43.15 | 25.67 | 29.71 |

Interpretation:

- LoRA is still too expressive and unstable for the current bridge scale
- activation bias carries a real, stable steering signal
- activation bias still does not solve held-out fact recall

Consequence:

- activation bias is now the **active simplification branch**
- FiLM is explicitly demoted behind a small activation-bias ablation matrix
- the next cheap runs should compare target geometry inside activation bias, not re-open the whole simplification menu

See also:

- `MoCoP/phases/phase2_activation_bias_ablation_matrix.md`

## Fresh Review Takeaways (2026-03-13)

Lain's review added one correction that should change the order of operations:

- the first question is not "can the bridge help?"
- the first question is "can vanilla Qwen3-4B solve the eval task at all when the facts are plainly visible in text context?"

That moves **baseline solvability** ahead of the tiny-overfit bridge run.

The rest of the review mostly reinforces directions already on the table:

- sparse every-4th-layer targeting is a suspicious geometry
- the current LoRA generation problem may be too unconstrained
- a simpler intervention path such as single-layer `v_proj` or activation-level biasing may be a better first bridge than multi-head dynamic LoRA

Nemotron 3 Super adds a second external signal:

- hybrid state-model plus transformer systems are clearly viable at scale
- compression should be treated as a first-class design problem
- denser supervision than single next-token loss is likely valuable

This does not justify more bridge complexity yet. It does justify:

- auditing the compressor as a possible bottleneck
- adding answer-focused readouts
- keeping a simpler intervention fallback ready

## Why This Plan Exists

The first paid Phase 2 run ended with:

- `Bridge: 0.000`
- `Baseline: 0.000`
- `Random: 0.000`
- `p = 1`
- general perplexity:
  - baseline `1022.0848`
  - random `1052.7257`
  - bridge `8121.2423`

Interpretation:

- the run was operationally valid
- exact-match recall is still at floor
- the bridge currently perturbs Qwen in a harmful way
- more epochs on the same setup are not justified

## External Clues Worth Testing, Not Worshipping

Two external references are relevant as hypothesis generators:

1. David Noel Ng, "LLM Neuroanatomy: How I Topped the AI Leaderboard Without Changing a Single Weight"
   - https://dnhkng.github.io/posts/rys/
   - associated model card:
     https://huggingface.co/dnhkng/RYS-XLarge
   - useful takeaway:
     contiguous transformer layer blocks may behave like functional circuits; sparse single-layer edits may miss the real unit of computation

2. Akiba et al., "Evolutionary Optimization of Model Merging Recipes"
   - local copy: [2403.13187v1.pdf](/c:/Users/cerub/OneDrive/Dokumente/LLM/Research/2403.13187v1.pdf)
   - useful takeaway:
     layer stacking and data-flow structure can matter as much as naive weight interpolation

Neither result proves the MoCoP bridge should work. They only strengthen the case for testing
**contiguous layer blocks** rather than only sparse distributed targets.

## Core Hypotheses

The current failure is most likely one or more of:

1. **Objective / metric mismatch**
   - training optimizes teacher-forcing loss
   - success is judged by strict greedy exact-match generation
   - vanilla Qwen may not solve the current recall task under the current prompt/eval surface
   - the bridge may be learning nothing, or the eval may be too brittle to show partial success

2. **Injection strength is too high**
   - the bridge hurts general perplexity badly
   - this suggests the generated LoRA deltas are not just weak, they are disruptive

3. **Target geometry is wrong**
   - current default targeting is sparse:
     every 4th layer, `q_proj` and `v_proj`
   - if functional units are block-like, this may be the wrong intervention shape

4. **Optimization is too aggressive**
   - `lr=1e-4` is probably too hot for the first real bridge run
   - the epoch-1 loss profile was noisy and unstable

5. **The eval task is too hard at this stage**
   - if baseline, random, and bridge all remain at zero, the immediate problem may be task setup or decoding brittleness, not only bridge quality

6. **The compressor may be discarding the useful signal**
   - MoCoP compresses Mamba state before the hypernetwork ever sees it
   - if the compressor throws away the answer-relevant dimensions, no downstream bridge can recover them
   - Nemotron's LatentMoE reinforces that compression is not a neutral step

## Compute Strategy

### What Opa-PC is good for

- dry-run loop validation
- dataset / prompt sanity checks
- single-model Qwen baseline solvability probes
- verifying saved prediction artifacts
- cheap code-path validation

### What Opa-PC is not good for

- meaningful real bridge training with full Mamba + Qwen
- throughput experiments
- strong conclusions about target-layer ablations

### What rented GPUs should be used for

- short, focused `A100 80GB` burst sessions
- persistent `/workspace` storage only
- one ablation axis at a time

Rule:

- no more multi-hour blind pilots until a tiny-overfit or short-burst run shows non-zero signal or at least less destructive bridge behavior
- use the remaining cloud credit on short, pre-declared diagnosis bursts only

## New Instrumentation Already Landed

The trainer now supports:

- `--tiny-overfit`
- `--tiny-overfit-samples`
- `--save-eval-predictions`
- `--eval-prediction-samples`

This means every diagnostic run can now save:

- prompt text
- gold answer
- baseline prediction
- random-LoRA prediction
- bridge prediction

Those artifacts are the main debugging surface now.

## Debug Ladder

Work top to bottom. Do not skip levels.

### D0. Sanity Gate

Goal:

- confirm the instrumentation path works

Expected environment:

- Opa-PC dry-run is enough

Pass condition:

- `eval_epoch_001_predictions.json` is produced
- prompts and predictions are readable

Status:

- done

### D1. Baseline Solvability Gate

Goal:

- verify that the eval task is actually solvable by vanilla Qwen3-4B when the facts are explicitly present in the visible text context

Run on:

- Opa-PC first, because this only needs one model
- rented `A100 80GB` only if Opa-PC inference turns out too annoying

Requirements:

- same ChatML formatting family used by training
- facts literally present in the text prompt visible to Qwen
- strict exact-match plus softer readouts if possible:
  - token overlap / F1
  - semantic similarity
  - raw prediction capture

Pass condition:

- vanilla Qwen gets off the floor on the direct-context version of the task

Fail condition:

- vanilla Qwen remains at or near zero even when the facts are visibly present

Interpretation:

- if this fails, the immediate problem is task / prompt / eval / model suitability
- do not blame the bridge yet
- repair the eval surface before spending on more bridge ablations

### D2. Tiny-Overfit Signal Test

Goal:

- answer the only question that matters first:
  can the bridge move off zero on a shared tiny train/eval subset?

Run on:

- rented `A100 80GB`

Canonical command:

```bash
python -X utf8 train_bridge.py \
  --epochs 1 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 16 \
  --eval-samples 8 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 8 \
  --lr 2e-5 \
  --save-eval-predictions \
  --eval-prediction-samples 8 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir /workspace/mocop_phase2_runs/tiny_overfit_probe
```

Pass condition:

- bridge exact-match moves above zero on the shared subset
  or
- prediction JSON shows bridge outputs are materially closer to the target than baseline/random

Fail condition:

- bridge, baseline, and random all stay at floor with useless outputs

Interpretation:

- if this fails, do not scale up
- inspect prompt formatting and answer decoding before anything else
- tiny-overfit passing alone is not enough to justify scale-up; the Sweden `64`-sample burst showed that shared-subset wins can vanish completely on disjoint eval

### D2.5. Answer-Focused Readout Gate

Goal:

- check whether exact-match is hiding partial bridge success

Run on:

- same short-burst rented run as D2 if possible

Preferred readouts:

1. answer-token cross-entropy / NLL
2. token overlap or F1
3. saved prediction JSON classification

Pass condition:

- bridge improves answer-focused metrics even if strict exact-match is still low

Interpretation:

- if answer-token metrics move while exact-match stays at floor, the bridge may be learning something real and the eval surface is too brittle
- if bridge perplexity improves briefly at epoch 1 but then worsens sharply with more training, treat that as unstable steering, not success

### D3. Learning-Rate Sweep

Goal:

- find out whether the current bridge is mostly an optimization-temperature problem

Hold fixed:

- tiny-overfit mode
- target layers
- LoRA rank
- dataset size

Run set:

1. `--lr 1e-5`
2. `--lr 2e-5`
3. `--lr 5e-5`

Readout:

- exact-match accuracy
- general perplexity damage
- saved predictions

Pass signal:

- lower LR reduces bridge perplexity damage and makes outputs less derailed

### D4. Target Geometry Sweep

Goal:

- test whether sparse targeting is the wrong intervention shape

Qwen3-4B has `36` decoder layers according to its config on Hugging Face, so middle-block tests
should be centered in the `14-21` region.

Reference:

- [Qwen/Qwen3-4B config.json](https://huggingface.co/Qwen/Qwen3-4B/blob/main/config.json)

Test families:

1. **Sparse default**
   - current default behavior
   - every 4th layer, `q_proj` and `v_proj`

2. **Contiguous 4-layer block**
   - example:
   - `16:q_proj,16:v_proj,17:q_proj,17:v_proj,18:q_proj,18:v_proj,19:q_proj,19:v_proj`

3. **Contiguous 7-layer block**
   - RYS-inspired circuit test
   - example:
   - `14:q_proj,14:v_proj,15:q_proj,15:v_proj,16:q_proj,16:v_proj,17:q_proj,17:v_proj,18:q_proj,18:v_proj,19:q_proj,19:v_proj,20:q_proj,20:v_proj`

4. **Early contiguous block**
   - example layers `8-11`
   - tests whether the useful intervention site is earlier than the middle stack

5. **Late contiguous block**
   - example layers `24-27`
   - tests whether the bridge is over-writing output formatting layers

Readout:

- exact-match
- general perplexity
- prediction JSON

Success pattern:

- contiguous middle blocks improve behavior relative to sparse default

### D4.5. Compressor Pressure Test

Goal:

- treat the compressor as an actual hypothesis target rather than invisible plumbing

Low-cost probes:

1. compare current single-target-layer compressor against a small multi-layer variant
2. inspect whether Layer 3-only remains the best bridge input after the failed pilot
3. log context-vector norms and variance by run so obviously collapsed compressors are visible

Interpretation:

- if target geometry changes do nothing, the compressor may be the real choke point
- if a broader or different state slice improves answer-focused metrics, compression strategy becomes a top-priority axis

### D5. Projection Family Sweep

Goal:

- reduce perturbation strength and find the least destructive insertion path

Run set:

1. `q_proj` only
2. `v_proj` only
3. `q_proj + v_proj`

Recommended order:

- start with the best-performing layer geometry from D3

Interpretation:

- if `q_proj` only behaves better than `q+v`, the current bridge is probably over-injecting

### D6. Eval Surface Check

Goal:

- determine whether exact-match is hiding partial success

Read the saved prediction JSON and classify failures:

1. formatting-only failures
2. semantically close but token-mismatched answers
3. generic fallback text
4. complete derailment / nonsense

Interpretation:

- formatting failures mean the eval is too brittle
- complete derailment means the bridge still damages Qwen too much

### D7. Intervention Simplification Gate

This gate has already fired. `activation_bias` is no longer a hypothetical fallback; it is the active diagnostic branch.

What changed after the original LoRA ladder:

- Sweden `64`-sample A3 completion stayed at `0/16` recall for all three epochs
- epoch 1 briefly improved LoRA bridge perplexity, but epochs 2-3 reverted to destructive over-injection
- a follow-up `activation_bias` run on the same geometry (`12-15`, `q_proj+v_proj`, completion prompts) stayed stable across 3 epochs and improved held-out answer perplexity from `29.71` baseline to `25.67` without recall lift
- Step 4 controls now show a hierarchy:
  - per-sample activation bias > fixed-mean activation bias >> constant bias

Current interpretation:

- dynamic LoRA is no longer the default place to spend cloud budget
- the live question is whether the activation-bias signal is truly state-dependent or mostly a cheap constant-offset effect
- FiLM remains a fallback, but it is demoted behind the activation-bias control ladder

Current D7 run order:

1. activation_bias per-sample run analysis (`run_actbias/`)
2. fixed-mean control (`step1_c3_fixed_mean_no4bit/`)
3. constant-bias controls (`run_constant_bias/`, `run_constant_bias_10ep/`, `run_constant_bias_seed42/`)
4. only reopen LoRA simplification if activation bias collapses under stronger controls

Interpretation:

- if per-sample activation bias keeps beating fixed-mean and constant-bias controls, there is at least a weak state-dependent steering channel worth following
- if fixed-mean or constant bias explains most of the gain, the bridge signal is mostly non-episodic and the "transfer" framing needs to narrow sharply
- if all simplified interventions fail under control, the bottleneck moves upstream to compressor/substrate quality rather than intervention complexity

### D8. Scale-Up Gate

Only move beyond short burst runs if one of these is true:

1. tiny-overfit reaches non-zero bridge accuracy
2. bridge perplexity stops being catastrophically worse than baseline
3. prediction JSON shows bridge outputs becoming materially more target-aligned than baseline/random
4. answer-focused metrics improve even if exact-match is still lagging

If none of these are true, stay in diagnostic mode.

Current status:

- failed for the current dynamic-LoRA bridge on the first `64`-sample disjoint-eval scale-up
- remain in diagnostic mode and simplify the intervention before spending on larger runs

## Suggested Run Order

Use this exact order:

1. D1 baseline solvability gate
2. D2 tiny-overfit at `lr=2e-5`
3. D2.5 answer-focused readout check
4. D3 LR sweep
5. D4 contiguous-vs-sparse target geometry sweep
6. D4.5 compressor pressure test
7. D5 projection family sweep
8. D6 prediction review
9. D7 simplify intervention if LoRA remains destructive
10. D8 decide whether a larger run is justified

## Short-Burst Budget Rule

For rented GPUs:

- prefer `1x A100 80GB`
- use persistent `/workspace`
- cap each diagnostic run to a short burst
- terminate immediately after artifacts are copied and checksummed
- pre-commit the exact hypothesis for each burst before launch

This is a diagnosis campaign, not an endurance race.

## Best Use Of Remaining Credit

If cloud credit is available right now, spend it in this order:

1. baseline solvability probe if Opa-PC proves operationally annoying
2. one tiny-overfit burst at `lr=2e-5`
3. one contiguous middle-block burst
4. stop and inspect artifacts before any third bridge variation

Do not spread the remaining credit across many half-read runs.

## What Not To Do

- do not resume the bad `pilot_01` checkpoint as if it were promising
- do not spend on more long runs before tiny-overfit is informative
- do not change multiple major axes at once
- do not assume more VRAM alone fixes a broken signal path

## Bottom Line

The next MoCoP step is to answer:

> Is the bridge fundamentally learning nothing, or are we currently targeting the wrong layers with the wrong intervention strength under the wrong metric?

This plan is designed to answer that with the least possible cloud spend.
