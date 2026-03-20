# Phase 2 A100 Quick Tiny-Overfit Plan

**Current as of:** 2026-03-16
**Status:** Completed diagnostic burst; next move is the simplification gate

## Purpose

This is the concrete paid-GPU plan for the next MoCoP burst.

It is intentionally narrow:

- do not implement the disposition benchmark yet
- do not resume `run_pilot_01`
- do not run long bridge training
- do not change more than one major axis at a time

The only question for this burst is:

> Can the bridge produce any non-zero or less-destructive signal on a shared tiny subset when the host model and optimizer setup are no longer obviously bad?

## Outcome: Sweden 64-Sample A3 Completion Burst (2026-03-16)

The answer is now clear for the current dynamic-LoRA setup:

| Epoch | Recall | Bridge PPL | Baseline PPL | Train Loss |
|---|---|---|---|---|
| 1 | 0/16 | 28.96 | 29.71 | 4.25 |
| 2 | 0/16 | 44.06 | 29.71 | 3.07 |
| 3 | 0/16 | 43.15 | 29.71 | 2.33 |

Interpretation:

- the bridge definitely learns something, because train loss falls steadily
- the bridge does **not** generalize to the disjoint eval set, because recall stays `0/16`
- epoch 1's `bridge_ppl < baseline_ppl` is a real early steering signal
- epochs 2-3 show over-injection again, so the useful signal is unstable
- the earlier `2/8` tiny-overfit result should now be treated as memorization of a shared subset, not transfer

Decision:

- do **not** scale this exact dynamic-LoRA setup to more samples
- move to the simplification gate next:
  - activation bias
  - FiLM-style conditioning
  - or LoRA norm clamping / another reduced intervention

## What We Accept From The Neutral Opus Review

- The disposition eval spec is real research work, but it is still downstream of bridge viability.
- DD0 in the disposition spec is underpowered in its current form and should not be treated as a decision-grade gate yet.
- Embedding similarity can confound topic with tone unless the prompt families are topic-controlled.
- The summary control needs tighter authorship and quality rules before it becomes a serious comparison.
- Temperature-0-only evaluation is good for determinism but not sufficient for the full later disposition claim.

## What We Do Not Accept From The Neutral Opus Review

- "D1 is unresolved" is stale.
  - The repo now treats direct-context solvability as established for the selected host candidates.
- "Switching away from Qwen3-4B is escapism" is too strong.
  - Host selection and bridge diagnosis were explicitly separated on purpose.
  - `Qwen/Qwen2.5-7B` and `mistralai/Mistral-Nemo-Base-2407` are the locked clean host candidates now.

## Fixed Decisions For This Burst

1. Primary host: `Qwen/Qwen2.5-7B`
2. Validation host: `mistralai/Mistral-Nemo-Base-2407`, only if Qwen shows signal worth validating
3. Hardware: `1x A100 80GB`
4. Storage: persistent `/workspace` only
5. Prompt surface: base-model-friendly `completion`, not ChatML
6. First phase: quick tiny-overfit only
7. No disposition-eval implementation work during this burst

## Important Correction To The Old Tiny-Overfit Command

The older canonical tiny-overfit command kept the default `--warmup-steps 200`.

That is wrong for a tiny-overfit run:

- `16` train samples
- batch size `2`
- `2` epochs
- total train steps = `16`

With the scheduler in `train_bridge.py`, a huge warmup means the run spends almost the entire burst below the intended learning rate. For quick tiny-overfit diagnostics, use:

- `--warmup-steps 2`

This is the most important operational correction in this plan.

## Second Correction: Base-Model Prompt Surface

The current locked hosts are base models, not chat models. The bridge trainer
previously wrapped fact questions in ChatML, which pushed Qwen into prompt-echo
failures like `What is` and `When does`.

For the next burst:

- use `--qwen-prompt-format completion`
- treat D1 and bridge-eval baselines separately
- do not expect the no-bridge baseline to become fact-correct just because the
  prompt surface improves, because the facts are still hidden in Mamba state

The success criterion for this fix is:

- baseline outputs become well-formed completions instead of ChatML echo
- bridge accuracy can be measured against a sane prompt surface

## Preflight

Run this once on the rented host before any paid training:

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
export RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"

mkdir -p "$HF_HOME" "$RUN_ROOT"

if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

cd "$REPO_ROOT"

python -X utf8 check_env.py \
  --require-cuda \
  --output-dir "$RUN_ROOT/preflight_q25_tiny" \
  --checkpoint-dir "$RUN_ROOT/preflight_q25_tiny"
```

Do not continue if preflight fails.

## Run Template

Use this shell wrapper for every run:

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
export RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"
RUN_ID="<fill_me>"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_DIR="$RUN_ROOT/logs"
LOG_FILE="$LOG_DIR/${RUN_ID}.log"

mkdir -p "$HF_HOME" "$RUN_DIR" "$LOG_DIR"

if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

cd "$REPO_ROOT"
```

## Run A1: Qwen2.5-7B Sparse Default, LR 2e-5

Hypothesis:

- the old host plus hot optimizer may have been part of the failure
- a cleaner host plus sane LR plus real LR exposure may move the bridge off total floor

Command:

```bash
RUN_ID="q25_tiny_default_lr2e5"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --qwen-prompt-format completion \
  --epochs 2 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 16 \
  --eval-samples 8 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 8 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --save-eval-predictions \
  --eval-prediction-samples 8 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

## Run A2: Qwen2.5-7B Sparse Default, LR 1e-5

Hypothesis:

- if A1 is still too destructive, the remaining problem may be optimization temperature

Command:

```bash
RUN_ID="q25_tiny_default_lr1e5"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --qwen-prompt-format completion \
  --epochs 2 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 16 \
  --eval-samples 8 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 8 \
  --lr 1e-5 \
  --warmup-steps 2 \
  --save-eval-predictions \
  --eval-prediction-samples 8 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

## Run A3: Qwen2.5-7B Contiguous Mid-Block, Q+V, LR 2e-5

`Qwen/Qwen2.5-7B` has `28` decoder layers, so the middle 4-layer test block is `12-15`.

Hypothesis:

- sparse every-4th-layer edits may miss the real functional circuit
- contiguous mid-block targeting may reduce incoherent residual-stream disruption
- keep LR fixed at `2e-5` so geometry is the only meaningful change from A1

Command:

```bash
RUN_ID="q25_tiny_midblock_qv_lr2e5"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --qwen-prompt-format completion \
  --epochs 2 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 16 \
  --eval-samples 8 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 8 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --target-layers "12:q_proj,12:v_proj,13:q_proj,13:v_proj,14:q_proj,14:v_proj,15:q_proj,15:v_proj" \
  --save-eval-predictions \
  --eval-prediction-samples 8 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

## Run A4: Qwen2.5-7B Contiguous Mid-Block, V-Proj Only, LR 2e-5

Hypothesis:

- full `q_proj + v_proj` generation may still be over-injecting
- `v_proj` only is the cleanest next simplification available without code changes
- keep LR fixed at `2e-5` so projection family is the only meaningful change from A3

Command:

```bash
RUN_ID="q25_tiny_midblock_v_lr2e5"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --qwen-prompt-format completion \
  --epochs 2 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 16 \
  --eval-samples 8 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 8 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --target-layers "12:v_proj,13:v_proj,14:v_proj,15:v_proj" \
  --save-eval-predictions \
  --eval-prediction-samples 8 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

## Optional Run B1: Mistral-Nemo Validation

Do **not** run this unless at least one Qwen run shows signal worth validating.

Signal worth validating means any one of:

- bridge exact-match rises above zero
- bridge perplexity is no longer catastrophically worse than baseline
- prediction JSON shows bridge answers are materially closer than baseline/random on multiple rows

Command:

```bash
RUN_ID="mnemo_tiny_default_lr2e5"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --qwen-model-id mistralai/Mistral-Nemo-Base-2407 \
  --qwen-prompt-format completion \
  --epochs 2 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 16 \
  --eval-samples 8 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 8 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --save-eval-predictions \
  --eval-prediction-samples 8 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

## Review Checklist After Each Run

Required artifacts:

- `bridge_epoch_001.pt`
- `eval_epoch_001_predictions.json`
- training log with eval lines

Check in this order:

1. Did the run finish without `Traceback`, `RuntimeError`, CUDA OOM, or NaN/Inf loss?
2. Did baseline stop prompt-echoing and produce sane completion-style answers?
3. Is bridge exact-match still zero?
4. Is `general_ppl bridge` still catastrophically above baseline/random?
5. Do saved predictions show:
   - exact wins
   - near misses
   - formatting-only misses
   - generic fallback
   - full derailment

Label each run as exactly one of:

- `dead`
- `harmful`
- `neutral`
- `promising`

## Stop Rules

Stop the burst immediately if:

- preflight fails
- model download/auth fails and cannot be fixed quickly
- two consecutive Qwen runs are both `dead`
- two consecutive Qwen runs are both `harmful` with no prediction closeness improvement
- the host becomes unstable or artifact transfer looks unreliable

Do **not** spend the remaining budget on the disposition benchmark after this burst.

If all Qwen runs are still destructive, the next move is not more LoRA runs.
The next move is the already-declared simplification gate:

- activation bias
- FiLM-style conditioning
- or another reduced intervention path

## Post-Run Copy Back

Before terminating the instance:

```bash
cd /workspace/mocop_phase2_runs
find . -maxdepth 2 -type f \
  \( -name "*.log" -o -name "*.json" -o -name "*.pt" \) \
  | sort
```

Copy the full run directories and logs back locally, then checksum them before terminating the host.

## Bottom Line

This burst answered the smaller, harder question honestly.

There is a **trace** of usable early signal, visible in epoch 1 perplexity, but it does not survive disjoint evaluation and it collapses into over-injection with more training.

The next move is not more scale on the same bridge. The next move is a simpler intervention.
