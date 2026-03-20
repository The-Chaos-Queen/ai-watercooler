# Phase 2 A100 A1 Quickstart

**Purpose:** one copy-paste launch for the first paid tiny-overfit burst, plus the minimum review checklist.

## What This Run Is

- Host: `Qwen/Qwen2.5-7B`
- Prompt surface: `completion`
- Geometry: sparse default
- LR: `2e-5`
- Warmup: `2`
- Goal: find out whether the bridge is still mechanically destructive on a tiny shared subset under a cleaner setup

## Preflight

Run this once on the rented `1x A100 80GB` host:

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

If preflight fails, stop there.

## Launch A1

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
export RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"
RUN_ID="q25_tiny_default_lr2e5"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_DIR="$RUN_ROOT/logs"
LOG_FILE="$LOG_DIR/${RUN_ID}.log"

mkdir -p "$HF_HOME" "$RUN_DIR" "$LOG_DIR"

if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

cd "$REPO_ROOT"

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

## Fast Log Checks

Use these while the run is active:

```bash
tail -n 80 /workspace/mocop_phase2_runs/logs/q25_tiny_default_lr2e5.log
```

```bash
grep -E "train epoch|eval epoch|general_ppl|Saved checkpoint|Training finished|Traceback|RuntimeError|CUDA" \
  /workspace/mocop_phase2_runs/logs/q25_tiny_default_lr2e5.log | tail -n 80
```

## Post-Run Checklist

Required files:

- `/workspace/mocop_phase2_runs/q25_tiny_default_lr2e5/bridge_epoch_001.pt`
- `/workspace/mocop_phase2_runs/q25_tiny_default_lr2e5/eval_epoch_001_predictions.json`
- `/workspace/mocop_phase2_runs/logs/q25_tiny_default_lr2e5.log`

Check in this order:

1. Did the run finish without `Traceback`, `RuntimeError`, CUDA OOM, or NaN/Inf loss?
2. Did baseline stop prompt-echoing and produce sane completion-style answers?
3. Did bridge exact-match move above zero?
4. Is `general_ppl bridge` still catastrophically above baseline/random?
5. Open `eval_epoch_001_predictions.json` and label the bridge outputs:
   - closer than baseline/random
   - formatting-only miss
   - semantically close miss
   - generic fallback
   - full derailment

## Decision After A1

- If `bridge` is still dead and outputs are nonsense: do not scale up, go to A2 (`lr=1e-5`).
- If `bridge` is less destructive but still zero: inspect predictions before changing geometry.
- If `bridge` shows any non-zero or clearly closer outputs: A2 becomes optional, and A3 mid-block geometry is justified.

## Copy Back Before Terminating Host

```bash
cd /workspace/mocop_phase2_runs
find q25_tiny_default_lr2e5 logs -maxdepth 2 -type f \
  \( -name "*.log" -o -name "*.json" -o -name "*.pt" \) \
  | sort
```

Copy the full run directory and the log before killing the instance.
