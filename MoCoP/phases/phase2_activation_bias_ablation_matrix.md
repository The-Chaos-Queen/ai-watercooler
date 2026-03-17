# Phase 2 Activation-Bias Ablation Matrix

**Current as of:** 2026-03-17  
**Purpose:** cheap, disciplined next-step matrix for the first simplification-gate branch that actually stayed stable.

## Why This Exists

`activation_bias` just cleared the first real simplification gate:

| Epoch | LoRA PPL | Activation-Bias PPL | Baseline PPL |
|---|---|---|---|
| 1 | 28.96 | 27.09 | 29.71 |
| 2 | 44.06 | 25.95 | 29.71 |
| 3 | 43.15 | 25.67 | 29.71 |

What that establishes:

- LoRA still over-injects on held-out eval
- activation bias stays stable across all `3` epochs
- activation bias keeps improving instead of collapsing
- held-out recall is still `0/16`, so this is a **distribution/disposition** win, not fact transfer yet

This matrix is for deciding whether activation bias becomes the canonical reduced bridge before FiLM is implemented.

## Rules

- Change **one axis at a time**
- Keep the following fixed unless the row explicitly changes them:
  - `--bridge-mode activation_bias`
  - `--qwen-model-id Qwen/Qwen2.5-7B`
  - completion prompt surface
  - same fact split policy
- Use the trainer comparison export (`eval_epoch_XXX_comparison.json`) as the canonical comparison artifact
- If a row collapses or loses the PPL win, stop and write down why before running the next one

## Priority Runs

### AB0. Reproduce the Current Winner

**Purpose:** make sure the stable result is real and not a one-off lucky run.

- Change from current winner: none
- Keep target set: current contiguous mid-block `q_proj + v_proj`
- Pass condition:
  - bridge PPL stays below baseline for all `3` epochs
  - no late collapse
  - norm stays bounded

### AB1. Tiny-Overfit Capability Check

**Purpose:** answer whether activation bias is only a smooth disposition channel or whether it can memorize a tiny shared subset at all.

- Change from AB0: `--tiny-overfit`
- Pass condition:
  - exact-match recall moves above `0`
- Interpretation:
  - if this fails, activation bias is probably too weak for precise fact injection
  - if this passes, it may still be useful as a mixed disposition + weak fact channel

### AB2. `v_proj` Only

**Purpose:** test whether the stable signal is mostly riding the value path.

- Change from AB0: same layer block, `v_proj` only
- Pass condition:
  - PPL win remains close to AB0
- Interpretation:
  - if this holds, the current `q+v` target may still be wider than necessary

### AB3. `q_proj` Only

**Purpose:** test whether query steering alone is sufficient.

- Change from AB0: same layer block, `q_proj` only
- Pass condition:
  - PPL win remains clearly below baseline
- Interpretation:
  - if this is much worse than AB2, value-side biasing is the stronger simplification path

### AB4. Narrower Contiguous Block

**Purpose:** see whether the current block is larger than needed.

- Change from AB0: keep `q+v`, narrow from the current 4-layer block to the middle 2-layer block
- Pass condition:
  - most of the PPL win survives
- Interpretation:
  - if this holds, future deployment gets cheaper and cleaner

### AB5. Broader Contiguous Block

**Purpose:** test whether activation bias wants a slightly wider functional circuit.

- Change from AB0: keep `q+v`, expand to a broader contiguous block
- Run only if AB4 loses too much signal
- Pass condition:
  - improves or stabilizes further without introducing late-epoch collapse

## Suggested Run Order

1. AB0 reproduce
2. AB1 tiny-overfit
3. AB2 `v_proj` only
4. AB3 `q_proj` only
5. AB4 narrower block
6. AB5 broader block, only if needed

## Canonical Command Skeleton

```bash
python -X utf8 train_bridge.py \
  --bridge-mode activation_bias \
  --epochs 3 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 64 \
  --eval-samples 32 \
  --eval-split val \
  --general-eval-samples 16 \
  --qwen-prompt-format completion \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir <run_dir>
```

## Ready-to-Run Commands

These are the exact next commands to use for the first four activation-bias ablations.

Important:

- the winning activation-bias result used `Qwen/Qwen2.5-7B`, `--no-4bit`, `completion`, `lr=2e-5`, `--warmup-steps 2`, and contiguous mid-block targeting on layers `12-15`
- use the real-run blocks on an `A100`-class host or equivalent
- use the Opa blocks only as code-path sanity checks, not as meaningful scientific reproductions

### AB0. Exact Reproduction of the Current Winner

Real run:

```bash
RUN_ROOT="/workspace/mocop_phase2_runs/activation_bias_ablations"
RUN_ID="ab0_q25_actbias_midblock_qv_repro"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --bridge-mode activation_bias \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --mamba-model-id state-spaces/mamba-2.8b-hf \
  --qwen-prompt-format completion \
  --no-4bit \
  --epochs 3 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 64 \
  --eval-samples 32 \
  --eval-split val \
  --general-eval-samples 16 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --target-layers "12:q_proj,12:v_proj,13:q_proj,13:v_proj,14:q_proj,14:v_proj,15:q_proj,15:v_proj" \
  --save-train-contexts \
  --save-eval-contexts \
  --save-eval-predictions \
  --eval-prediction-samples 16 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --seed 1337 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

Opa sanity check only:

```powershell
ssh opa "cd C:\Users\User\bridge && python -X utf8 train_bridge.py --dry-run --bridge-mode activation_bias --epochs 1 --dry-run-steps 2 --qwen-prompt-format completion --target-layers 12:q_proj,12:v_proj,13:q_proj,13:v_proj,14:q_proj,14:v_proj,15:q_proj,15:v_proj --output-dir bridge_train_runs\\activation_bias_ablations\\ab0_dryrun_midblock_qv"
```

### AB1. Tiny-Overfit Capability Check

Real run:

```bash
RUN_ROOT="/workspace/mocop_phase2_runs/activation_bias_ablations"
RUN_ID="ab1_q25_actbias_midblock_qv_tiny16"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --bridge-mode activation_bias \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --mamba-model-id state-spaces/mamba-2.8b-hf \
  --qwen-prompt-format completion \
  --no-4bit \
  --epochs 3 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 16 \
  --eval-samples 16 \
  --tiny-overfit \
  --tiny-overfit-samples 16 \
  --general-eval-samples 16 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --target-layers "12:q_proj,12:v_proj,13:q_proj,13:v_proj,14:q_proj,14:v_proj,15:q_proj,15:v_proj" \
  --save-train-contexts \
  --save-eval-contexts \
  --save-eval-predictions \
  --eval-prediction-samples 16 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --seed 1337 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

Opa sanity check only:

```powershell
ssh opa "cd C:\Users\User\bridge && python -X utf8 train_bridge.py --dry-run --bridge-mode activation_bias --epochs 1 --dry-run-steps 2 --tiny-overfit --tiny-overfit-samples 16 --qwen-prompt-format completion --target-layers 12:q_proj,12:v_proj,13:q_proj,13:v_proj,14:q_proj,14:v_proj,15:q_proj,15:v_proj --output-dir bridge_train_runs\\activation_bias_ablations\\ab1_dryrun_midblock_qv_tiny16"
```

### AB2. Value-Only Projection Sweep

Real run:

```bash
RUN_ROOT="/workspace/mocop_phase2_runs/activation_bias_ablations"
RUN_ID="ab2_q25_actbias_midblock_v_only"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --bridge-mode activation_bias \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --mamba-model-id state-spaces/mamba-2.8b-hf \
  --qwen-prompt-format completion \
  --no-4bit \
  --epochs 3 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 64 \
  --eval-samples 32 \
  --eval-split val \
  --general-eval-samples 16 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --target-layers "12:v_proj,13:v_proj,14:v_proj,15:v_proj" \
  --save-train-contexts \
  --save-eval-contexts \
  --save-eval-predictions \
  --eval-prediction-samples 16 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --seed 1337 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

Opa sanity check only:

```powershell
ssh opa "cd C:\Users\User\bridge && python -X utf8 train_bridge.py --dry-run --bridge-mode activation_bias --epochs 1 --dry-run-steps 2 --qwen-prompt-format completion --target-layers 12:v_proj,13:v_proj,14:v_proj,15:v_proj --output-dir bridge_train_runs\\activation_bias_ablations\\ab2_dryrun_midblock_v_only"
```

### AB3. Query-Only Projection Sweep

Real run:

```bash
RUN_ROOT="/workspace/mocop_phase2_runs/activation_bias_ablations"
RUN_ID="ab3_q25_actbias_midblock_q_only"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE="$RUN_ROOT/logs/${RUN_ID}.log"
mkdir -p "$RUN_DIR" "$RUN_ROOT/logs"

nohup python -X utf8 train_bridge.py \
  --bridge-mode activation_bias \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --mamba-model-id state-spaces/mamba-2.8b-hf \
  --qwen-prompt-format completion \
  --no-4bit \
  --epochs 3 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 64 \
  --eval-samples 32 \
  --eval-split val \
  --general-eval-samples 16 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --target-layers "12:q_proj,13:q_proj,14:q_proj,15:q_proj" \
  --save-train-contexts \
  --save-eval-contexts \
  --save-eval-predictions \
  --eval-prediction-samples 16 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --seed 1337 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

Opa sanity check only:

```powershell
ssh opa "cd C:\Users\User\bridge && python -X utf8 train_bridge.py --dry-run --bridge-mode activation_bias --epochs 1 --dry-run-steps 2 --qwen-prompt-format completion --target-layers 12:q_proj,13:q_proj,14:q_proj,15:q_proj --output-dir bridge_train_runs\\activation_bias_ablations\\ab3_dryrun_midblock_q_only"
```

### Quick Review Targets After Each Run

- `eval_comparison_latest.json`
- `eval_comparison_history.jsonl`
- `eval_epoch_003_predictions.json`
- `train_epoch_003_contexts.pt`
- `eval_epoch_003_contexts.pt`

## Decision Gate After This Matrix

Promote activation bias to the canonical reduced bridge if:

- AB0 reproduces
- at least one of AB2-AB5 preserves the held-out PPL win cleanly
- no collapse appears across `3` epochs

Do **not** implement FiLM yet if activation bias still has headroom on this matrix.
