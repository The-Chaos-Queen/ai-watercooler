# Step 1 C3 + Step 4 Controls - A100 Runbook

**Date:** 2026-03-18
**Purpose:** Close the two remaining paid control gates before any more architecture changes or dataset pivots.
**Runs covered:** Step 1 C3 `fixed_mean` eval and Step 4 `constant_bias`
**Decision goal:** determine whether the current `activation_bias` win is sample-dependent transfer or just a learned constant shove

---

## Status

- `--eval-only --eval-adjustment-source fixed_mean` is implemented in `train_bridge.py`
- `--bridge-mode constant_bias` is implemented in `train_bridge.py`
- both paths passed Opa dry-run smoke
- the real Qwen2.5-7B eval stalled on Windows Opa, so these are now **Linux/A100-only decision runs**

---

## Current Comparison Target

Treat this as the canonical control baseline until replaced by a same-host rerun:

- source run: `experiments/mamba_lora_bridge/run_actbias`
- bridge mode: `activation_bias`
- model: `Qwen/Qwen2.5-7B`
- prompt surface: `completion`
- target layers: `12-15` `q_proj + v_proj`
- train/eval surface: `64 train`, `32 val`, `16 general`
- epoch-3 bridge PPL: `25.67`
- epoch-3 baseline PPL: `29.71`

For the current C3 control, use the saved epoch-3 artifacts from that run:

- `run_actbias/bridge_best.pt`
- `run_actbias/train_epoch_003_contexts.pt`

---

## Scientific Mode First

For these two control runs, prioritize comparability over throughput.

- keep the same `Qwen/Qwen2.5-7B` base model
- keep `completion` prompts
- keep the same target layers
- keep `lr=2e-5`
- keep `warmup-steps=2`
- keep `batch-size 1` and `eval-batch-size 1` for the first decision-grade pass
- keep all artifacts on `/workspace`, not `/dev/shm`

The A100 will be underutilized in this strict-control mode. That is acceptable here because the goal is not efficiency; it is an honest comparison against the existing `run_actbias` result.

---

## Pre-Flight Checklist

- [x] C3 eval-only path implemented
- [x] `constant_bias` path implemented
- [x] Opa dry-run smoke passed for both
- [ ] Linux A100 host rented with at least `80 GB` VRAM and `100+ GB` disk
- [ ] Hugging Face token available on host
- [ ] repo synced to host under `/workspace/bridge`
- [ ] `run_actbias/bridge_best.pt` copied to host
- [ ] `run_actbias/train_epoch_003_contexts.pt` copied to host
- [ ] output and log directories created on `/workspace`

---

## Host Layout

Use this exact layout on the rented host:

```bash
/workspace/bridge
/workspace/.hf_home
/workspace/logs
/workspace/mocop_artifacts/run_actbias
/workspace/mocop_phase2_runs/controls
```

---

## Upload Checklist

From the local repo, copy the code and the two required Step 1 artifacts before launching anything:

```bash
HOST=<user>@<host>

scp \
  MoCoP/experiments/mamba_lora_bridge/train_bridge.py \
  MoCoP/experiments/mamba_lora_bridge/models.py \
  MoCoP/experiments/mamba_lora_bridge/cognitive_bridge.py \
  MoCoP/experiments/mamba_lora_bridge/bridge_dataset.py \
  MoCoP/experiments/mamba_lora_bridge/model_defaults.py \
  "$HOST:/workspace/bridge/"

scp \
  MoCoP/experiments/mamba_lora_bridge/run_actbias/bridge_best.pt \
  MoCoP/experiments/mamba_lora_bridge/run_actbias/train_epoch_003_contexts.pt \
  "$HOST:/workspace/mocop_artifacts/run_actbias/"
```

If the host repo was freshly cloned and already up to date, only the two artifacts need copying.

---

## One-Time Host Prep

```bash
export HF_HOME=/workspace/.hf_home
mkdir -p \
  /workspace/.hf_home \
  /workspace/logs \
  /workspace/mocop_artifacts/run_actbias \
  /workspace/mocop_phase2_runs/controls

cd /workspace/bridge
```

Optional sanity check:

```bash
nvidia-smi
```

---

## Run 1: Step 1 C3 Fixed-Mean Eval

This is the cheapest remaining control. It answers:

`Does per-sample variation matter, or is the learned bridge effectively just one average bias vector?`

Important:

- this uses the saved train contexts, so no live Mamba forward path is needed
- this is eval-only, not training
- the checkpoint and contexts must match the same baseline run

Canonical command:

```bash
export HF_HOME=/workspace/.hf_home
RUN_ROOT=/workspace/mocop_phase2_runs/controls
RUN_ID=step1_c3_fixed_mean_run_actbias_e3
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE=/workspace/logs/${RUN_ID}.log
ART_ROOT=/workspace/mocop_artifacts/run_actbias

mkdir -p "$RUN_DIR"

nohup python -X utf8 train_bridge.py \
  --eval-only \
  --bridge-mode activation_bias \
  --resume-from "$ART_ROOT/bridge_best.pt" \
  --eval-adjustment-source fixed_mean \
  --fixed-mean-contexts-path "$ART_ROOT/train_epoch_003_contexts.pt" \
  --qwen-model-id Qwen/Qwen2.5-7B \
  --qwen-prompt-format completion \
  --no-4bit \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 64 \
  --eval-samples 32 \
  --eval-split val \
  --general-eval-samples 16 \
  --lr 2e-5 \
  --warmup-steps 2 \
  --target-layers "12:q_proj,12:v_proj,13:q_proj,13:v_proj,14:q_proj,14:v_proj,15:q_proj,15:v_proj" \
  --save-eval-predictions \
  --eval-prediction-samples 16 \
  --seed 1337 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started C3 fixed_mean pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

Expected artifacts:

- `eval_comparison_latest.json`
- `eval_comparison_history.jsonl`
- `eval_epoch_001_comparison.json`
- `eval_epoch_001_predictions.json`
- full log

---

## Run 2: Step 4 Constant-Bias Training

Launch this only after the C3 job has produced its comparison JSON.

This run answers:

`Does the Mamba-derived path beat a single learned static bias trained under the same outer loss?`

Canonical command:

```bash
export HF_HOME=/workspace/.hf_home
RUN_ROOT=/workspace/mocop_phase2_runs/controls
RUN_ID=step4_constant_bias_q25_midblock_qv
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_FILE=/workspace/logs/${RUN_ID}.log

mkdir -p "$RUN_DIR"

nohup python -X utf8 train_bridge.py \
  --bridge-mode constant_bias \
  --qwen-model-id Qwen/Qwen2.5-7B \
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
  --save-eval-predictions \
  --eval-prediction-samples 16 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --seed 1337 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started constant_bias pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

Expected artifacts:

- `bridge_best.pt`
- `bridge_epoch_001.pt`
- `bridge_epoch_002.pt`
- `bridge_epoch_003.pt`
- `eval_comparison_latest.json`
- `eval_comparison_history.jsonl`
- `eval_epoch_001_comparison.json`
- `eval_epoch_002_comparison.json`
- `eval_epoch_003_comparison.json`
- prediction JSONs
- full log

---

## Monitoring

Step 1 C3:

```bash
tail -n 80 /workspace/logs/step1_c3_fixed_mean_run_actbias_e3.log
grep -E "eval-only|general_ppl|saved_comparison|Traceback|RuntimeError" /workspace/logs/step1_c3_fixed_mean_run_actbias_e3.log | tail -n 80
```

Step 4 constant bias:

```bash
tail -n 80 /workspace/logs/step4_constant_bias_q25_midblock_qv.log
grep -E "epoch=|general_ppl|saved_comparison|Traceback|RuntimeError" /workspace/logs/step4_constant_bias_q25_midblock_qv.log | tail -n 120
```

If anything crashes, preserve the log before restarting.

---

## Pullback Checklist

Copy artifacts home before terminating the host.

Minimum pullback set:

- C3 run directory
- Step 4 run directory
- both log files
- `bridge_best.pt`
- `bridge_epoch_003.pt`

Example:

```bash
HOST=<user>@<host>
LOCAL_ROOT=MoCoP/experiments/mamba_lora_bridge

scp -r \
  "$HOST:/workspace/mocop_phase2_runs/controls/step1_c3_fixed_mean_run_actbias_e3" \
  "$LOCAL_ROOT/"

scp -r \
  "$HOST:/workspace/mocop_phase2_runs/controls/step4_constant_bias_q25_midblock_qv" \
  "$LOCAL_ROOT/"

scp \
  "$HOST:/workspace/logs/step1_c3_fixed_mean_run_actbias_e3.log" \
  "$HOST:/workspace/logs/step4_constant_bias_q25_midblock_qv.log" \
  "$LOCAL_ROOT/"
```

---

## Decision Rules

Interpret the two controls together, not in isolation.

| Result | Meaning | Immediate next move |
|---|---|---|
| `fixed_mean ~= learned` and `constant_bias ~= activation_bias` | the current win is basically a learned constant offset | do not claim A->B transfer |
| `fixed_mean ~= learned` but `constant_bias` is worse | the learned direction matters, but per-sample variation is not doing work yet | channel may exist, but sample-specific transfer is still unproven |
| `fixed_mean` is worse and `constant_bias` is worse | strongest current evidence that sample-dependent information survives A->B | Step 1 and Step 4 both PASS |
| `constant_bias` beats activation_bias | Mamba-derived pathway is currently hurting | revisit mapping before Step 2b |

For Step 4 specifically, treat `constant_bias` within roughly `1 PPL` of the Mamba-derived run as a practical fail unless another metric clearly disagrees.

---

## Do Not Do

- do not spend paid time on Step 2b before these two controls exist
- do not switch prompt format mid-control
- do not switch target layers mid-control
- do not use `/dev/shm` for checkpoints or logs
- do not terminate the host before pulling artifacts home

---

## Bottom Line

This host rental is not for exploration. It is for closing the control gap.

Run `C3` first. Run `constant_bias` second. Compare both against `run_actbias`. Then decide whether the current A->B claim survives contact with controls.
