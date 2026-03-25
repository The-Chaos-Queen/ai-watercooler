# Vast.ai Experiment Runbook

Date: 2026-03-25
Workspace: `MoCoP/experiments/mamba_lora_bridge`

This is the current handbook for paid cloud bridge runs on Vast.ai.
Use it for staged A100 pilots, not for Steve or Opa.

## Purpose

Use Vast.ai for:

- paid A100 bridge-training runs
- multi-epoch replication that exceeds Opa's capacity
- controlled stage-1 / stage-2 pilot execution
- current 7B reincarnation quick-runs when Steve/Opa are too small

Do not improvise host storage, logging, or resume policy on the day of run. That is exactly how credits get burned.

## Run Classes

There are two different run classes in this file. Keep them separate:

- Current recommended path: `7B Reincarnation Quick Run` using `record_cheese_batch.py`, `train_cheese_bridge.py`, and `reincarnated_inference.py`. This is the current `hidden_last_token` disposition-transfer path.
- Legacy baseline path: `Legacy Stage 1 / Stage 2` using `train_bridge.py`. This is older baseline work and still uses Mamba `ssm_states`.

If your goal is current reincarnation/disposition transfer, skip directly to the 7B section after bootstrap and preflight.

## Fixed Policy For Legacy Baseline Pilot

For the first paid bridge run class:

- eval split: `val` only
- preserve `test` for post-pilot confirmation
- prompt alignment: deferred
- architecture: Mamba-2 baseline only
- do not mix in Mamba-3, LoRA-rank sweeps, or compressor redesigns during the pilot

Important distinction:

- the Legacy Stage 1 / Stage 2 path below uses `train_bridge.py`, which is the older baseline pipeline and still operates on Mamba `ssm_states`
- the `7B Reincarnation Quick Run` section later in this file is the current `hidden_last_token` disposition-transfer path
- do not treat those as interchangeable just because they share a host

## Host Selection

Preferred host profile:

- provider: Vast.ai
- GPU: `1x A100 80GB` or `1x A100-SXM4-80GB`
- region preference: Czech Republic first, then Germany / Netherlands / Poland
- host filters: verified datacenter, reliability `>= 0.98`, Linux image with a driver/toolchain pair you can validate on boot
- container disk: `>= 64 GB`, `100 GB` preferred

Budget policy:

- pilot-1 hard cap: `20 EUR`
- exploratory budget before review: `100 EUR`

Storage rules:

- keep `HF_HOME`, `RUN_ROOT`, logs, and checkpoints on `/workspace` or attached persistent storage
- do not rely on `/dev/shm` for paid-run artifacts

## Expected Footprint For Legacy Baseline

- Legacy Stage 1 is a gated one-epoch run to prove the host, checkpoint path, and logs are clean.
- Legacy Stage 2 resumes only if epoch 1 looks healthy.
- Observed on 2026-03-10: an A100 40GB host used about `35.8 GiB` VRAM at `--batch-size 1`, so the preferred follow-up host is `80GB`.
- On `80GB`, resume at `--batch-size 2` first. Only test `4` after a short stability check.

## Bootstrap Before Any Paid Run

Reality from the 2026-03-25 A100 SXM4 rental:

- default pip `torch 2.11` was incompatible with the host's CUDA 12.0-class driver and made `model.to("cuda")` fail
- `mamba-ssm` was not installed, so Mamba fell back to the slow sequential path
- the host looked superficially fine until large models loaded, which is exactly how paid minutes get burned

Safe policy:

- do not trust the preinstalled Python stack
- pin PyTorch to a wheel that matches the driver you actually rented
- verify `torch.cuda.is_available()` before loading Qwen or Mamba
- require `mamba-ssm` and `causal-conv1d` before calling the host GPU-ready

Known-safe fallback for the current Vast.ai pattern:

```bash
python -m pip install --upgrade --index-url https://download.pytorch.org/whl/cu121 "torch==2.5.1+cu121"
python -m pip install --upgrade mamba-ssm causal-conv1d
```

If the rental uses a different driver family, adjust the wheel accordingly. Until we maintain an explicit image table, do not assume the Vast.ai image label is truthful enough on its own.

Minimal must-pass bootstrap check:

```bash
nvidia-smi
python - <<'PY'
import torch
print("torch", torch.__version__)
print("torch_cuda_build", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
if not torch.cuda.is_available():
    raise SystemExit("cuda is not available; fix torch/driver before loading models")
import mamba_ssm, causal_conv1d
print("mamba_fast_path", "ok")
PY
```

## Day-of-Run Preflight

Run inside the Vast instance shell:

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
if [ -d /workspace ]; then
  export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
  RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"
else
  export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
  RUN_ROOT="${RUN_ROOT:-$HOME/mocop_phase2_runs}"
fi

mkdir -p "$HF_HOME"
if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

RUN_ID="${RUN_ID:-pilot_01}"
RUN_DIR="$RUN_ROOT/$RUN_ID"
mkdir -p "$RUN_DIR"
cd "$REPO_ROOT"

nvidia-smi

python - <<'PY'
import torch
print("torch", torch.__version__)
print("torch_cuda_build", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
if not torch.cuda.is_available():
    raise SystemExit("cuda is not available; stop the rental here")
probe = torch.zeros(1, device="cuda")
print("probe_device", probe.device)
import mamba_ssm, causal_conv1d
print("mamba_fast_path", "ok")
PY

python -X utf8 check_env.py \
  --require-cuda \
  --output-dir "$RUN_DIR" \
  --checkpoint-dir "$RUN_DIR"
```

If preflight fails, stop there. Do not “just try the training anyway.”

## Legacy Stage 1

Gate on epoch 1 only:

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
if [ -d /workspace ]; then
  export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
  RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"
else
  export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
  RUN_ROOT="${RUN_ROOT:-$HOME/mocop_phase2_runs}"
fi

mkdir -p "$HF_HOME"
if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

RUN_ID="${RUN_ID:-pilot_01}"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_DIR="$RUN_ROOT/logs"
LOG_FILE="$LOG_DIR/${RUN_ID}.log"

mkdir -p "$RUN_DIR" "$LOG_DIR"
cd "$REPO_ROOT"

python -X utf8 check_env.py \
  --require-cuda \
  --output-dir "$RUN_DIR" \
  --checkpoint-dir "$RUN_DIR"

nohup python -X utf8 train_bridge.py \
  --epochs 1 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 256 \
  --eval-samples 64 \
  --eval-split val \
  --general-eval-samples 32 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "started train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

## Legacy Stage 2

Resume only if Stage 1 completed cleanly:

```bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/bridge}"
if [ -d /workspace ]; then
  export HF_HOME="${HF_HOME:-/workspace/.hf_home}"
  RUN_ROOT="${RUN_ROOT:-/workspace/mocop_phase2_runs}"
else
  export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
  RUN_ROOT="${RUN_ROOT:-$HOME/mocop_phase2_runs}"
fi

mkdir -p "$HF_HOME"
if [ -z "${HF_TOKEN:-}" ]; then
  [ -s "$HF_HOME/token" ] || { echo "Missing non-empty $HF_HOME/token"; exit 1; }
  export HF_TOKEN="$(tr -d '\r\n' < "$HF_HOME/token")"
fi

RUN_ID="${RUN_ID:-pilot_01}"
RUN_DIR="$RUN_ROOT/$RUN_ID"
LOG_DIR="$RUN_ROOT/logs"
LOG_FILE="$LOG_DIR/${RUN_ID}_resume.log"

mkdir -p "$RUN_DIR" "$LOG_DIR"
cd "$REPO_ROOT"

[ -f "$RUN_DIR/bridge_epoch_001.pt" ] || { echo "Missing $RUN_DIR/bridge_epoch_001.pt"; exit 1; }

nohup python -X utf8 train_bridge.py \
  --epochs 5 \
  --batch-size 2 \
  --eval-batch-size 2 \
  --train-samples 256 \
  --eval-samples 64 \
  --eval-split val \
  --general-eval-samples 32 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  --resume-from "$RUN_DIR/bridge_epoch_001.pt" \
  > "$LOG_FILE" 2>&1 < /dev/null &
echo "resumed train_bridge pid=$! log=$LOG_FILE run_dir=$RUN_DIR"
```

If the resumed `80GB` host still has large VRAM headroom after warmup, test `--batch-size 4` only in a short verification run first.

## Expected Artifacts

- `$RUN_DIR/bridge_best.pt`
- `$RUN_DIR/bridge_epoch_001.pt`
- `$RUN_DIR/bridge_epoch_<epoch>.pt`
- stage logs in `$RUN_ROOT/logs/`
- eval summaries in the training log

## Stop Conditions

Stop the paid run if any of these happen:

- preflight fails
- `torch.cuda.is_available()` is false or a tiny CUDA probe tensor fails
- `mamba-ssm` / `causal-conv1d` are missing and Mamba would run on sequential fallback
- Legacy Stage 1 does not produce `bridge_epoch_001.pt`
- the log shows `Traceback`, `RuntimeError`, CUDA OOM, or NaN / Inf loss
- model download or auth failures persist after fixing `HF_TOKEN`
- the host is interruptible and gets reclaimed before the first checkpoint
- Legacy Stage 1 has not been reviewed yet and someone tries to jump straight to Legacy Stage 2

## Post-Run Sync

Before terminating the instance:

1. copy `$RUN_DIR`
2. copy the relevant log file
3. review metrics before spending beyond the pilot cap

## 7B Reincarnation Quick Run (2026-03-25, Cassian)

Successfully trained on A100 SXM4 80GB. This is the current recommended paid-run path for the CHEESE disposition bridge:

```bash
# After bootstrap (PyTorch cu121 + mamba-ssm installed and preflight passing):
cd /workspace/bridge

# Step 1: Record 7B activation targets (Mamba on GPU, Qwen on GPU)
python3 record_cheese_batch.py

# Step 2: Train bridge (50 epochs, ~2 minutes)
python3 train_cheese_bridge.py --epochs 50 --lr 1e-3 --output-name cheese_reincarnation_bridge_7b.pt

# Step 3: Inference test
python3 reincarnated_inference.py \
  --bridge-path cheese_reincarnation_bridge_7b.pt \
  --max-new-tokens 200 --temperature 0.7 \
  --qwen-device cuda:0 --mamba-device cuda:0 --bridge-device cuda:0
```

**Note:** Scripts default to 1.5B. For 7B, sed-replace `Qwen/Qwen2.5-1.5B` -> `Qwen/Qwen2.5-7B` in all three scripts, plus update output names and target dirs. Proper CLI flags are still the right fix.

**Results (2026-03-25):** Loss 29.8 → 0.025. 7B shows disposition transfer without degeneration — model asks questions instead of reciting, philosophizes instead of quoting Quora. Unlike 1.5B, the 7B retains enough capacity for coherence alongside disposition.

**Total cost:** ~$0.50 (30 minutes including model downloads).

## Known Follow-Up Code Fixes

- Add proper CLI model-id flags to the 7B quick-run scripts so nobody has to sed-replace model names by hand.
- Add a `--skip-recording` mode to `train_cheese_bridge.py` so reruns from saved activation tensors do not reload Mamba + Qwen unnecessarily on rented hosts.

## Related Files

- `OPA_RUNBOOK.md` - Opa-PC local validation path
- `RUNBOOK.md` - compatibility index for old references
- `watch_vast_stage1.ps1` - local watcher helper if still used
