# Opa-PC WSL Experiment Runbook

Date: 2026-02-27  
Workspace: `MoCoP/experiments/mamba_lora_bridge`

This guide is the shareable standard for running remote experiments on Opa-PC (`192.168.2.194`) without `cmd.exe` quoting issues.

## Problem This Solves

The failure mode we want to avoid:

- Windows `cmd.exe` or nested quoting consumes `| tee` before WSL sees it.
- Long one-line SSH commands get mangled and produce noisy/cut output.
- Logs are dumped inline and burn tokens.

Standard fix:

- Use PowerShell only.
- Use [`opa-wsl.ps1`](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/opa-wsl.ps1).
- Send Bash script text over SSH stdin to `wsl bash -se`.
- Write full logs remotely; retrieve only tail/grep snippets.

## Required Files

- [`opa-wsl.ps1`](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/opa-wsl.ps1)
- [`run_smoke.sh`](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/run_smoke.sh)
- [`run_long_horizon.sh`](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/run_long_horizon.sh)
- [`run_probe.sh`](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/run_probe.sh)
- [`long_horizon_eval.py`](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/long_horizon_eval.py)
- [`mamba_linear_probe.py`](/c:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/mamba_linear_probe.py)

## Prerequisites

1. Windows PowerShell 5+ or PowerShell 7.
2. OpenSSH client (`ssh`, `scp`) available in PATH.
3. Remote SSH access: `USER@192.168.2.194`.
4. On remote host: WSL installed, `/home/user/venv_linux` available, bridge checkout at `/mnt/c/Users/USER/bridge`.

## One-Time Validation

Run from this directory:

```powershell
cd C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge
```

Connectivity + WSL sanity:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
echo "connected"
whoami
uname -a
python3 --version
'@
```

If script execution policy blocks `.ps1`, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\opa-wsl.ps1 -User USER -Run "echo ok"
```

## Sync Files Before Runs

```powershell
scp `
  .\bridge_dataset.py `
  .\check_env.py `
  .\models.py `
  .\cognitive_bridge.py `
  .\long_horizon_eval.py `
  .\mamba_linear_probe.py `
  .\regression_smoke.py `
  .\smoke_test.py `
  .\test_splits.py `
  .\train_bridge.py `
  .\run_smoke.sh `
  .\run_long_horizon.sh `
  .\run_probe.sh `
  USER@192.168.2.194:C:/Users/USER/bridge/
```

## Core Command Patterns

Run arbitrary remote Bash safely:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
/home/user/venv_linux/bin/python regression_smoke.py
/home/user/venv_linux/bin/python test_splits.py
'@
```

Tail logs (token-efficient):

```powershell
.\opa-wsl.ps1 -User USER -TailLog /home/user/long_horizon_output.log -Lines 120
```

Grep high-signal lines:

```powershell
.\opa-wsl.ps1 -User USER -GrepLog /home/user/long_horizon_output.log -Pattern 'Traceback|RuntimeError|ERROR|Probe accuracy|Run complete' -Lines 120
```

## Phase 2 Preflight

Run this before any paid training job. It verifies Python, PyTorch, CUDA, `accelerate`,
bitsandbytes, Hugging Face token resolution, lightweight model access, free disk space
for HF cache plus artifact paths, and that the output/checkpoint directories are writable.

Opa WSL preflight:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
set -euo pipefail
export HF_HOME=/home/user/.cache/huggingface
HF_TOKEN_FILE="$HF_HOME/token"
if [ ! -s "$HF_TOKEN_FILE" ]; then
  HF_TOKEN_FILE=/mnt/c/Users/USER/.cache/huggingface/token
fi
[ -s "$HF_TOKEN_FILE" ] || { echo "Missing non-empty HF token file"; exit 1; }
export HF_TOKEN="${HF_TOKEN:-$(tr -d '\r\n' < "$HF_TOKEN_FILE")}"
cd /mnt/c/Users/USER/bridge
RUN_DIR=/home/user/mocop_phase2_runs/opa_preflight
/home/user/venv_linux/bin/python -X utf8 check_env.py \
  --require-cuda \
  --output-dir "$RUN_DIR" \
  --checkpoint-dir "$RUN_DIR"
'@
```

Cloud preflight uses the same script and should point `--output-dir` at a Linux-local,
persistent path such as `/workspace/mocop_phase2_runs/pilot_01`. Avoid `/dev/shm` for
paid runs because artifacts disappear when the instance stops.

## Full Experiment Procedure

Goal:

- Load Mamba pipeline.
- Run 60 turns.
- Inject facts every 6 turns.
- Collect context/state vectors.
- Train linear classifier probe.
- Validate disjoint synthetic train/val/test splits.
- Run resumable Phase 2 bridge training.
- Report accuracy.

### 1. Smoke Test (Optional but Recommended)

```powershell
.\opa-wsl.ps1 -User USER -Run "bash /mnt/c/Users/USER/bridge/run_smoke.sh"
.\opa-wsl.ps1 -User USER -GrepLog /home/user/smoke_output.log -Pattern 'FAILED|Traceback|SMOKE TEST COMPLETE' -Lines 120
```

### 2. Long-Horizon Run (60 Turns, Inject Every 6)

Foreground run:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
/home/user/venv_linux/bin/python long_horizon_eval.py \
  --turns 60 \
  --inject-every 6 \
  --probe-lags 3,12,24 \
  --export-context-vectors \
  --output-dir long_horizon_runs \
  2>&1 | tee /home/user/long_horizon_output.log
'@
```

Background run (preferred for long sessions):

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
nohup /home/user/venv_linux/bin/python long_horizon_eval.py \
  --turns 60 \
  --inject-every 6 \
  --probe-lags 3,12,24 \
  --export-context-vectors \
  --output-dir long_horizon_runs \
  > /home/user/long_horizon_output.log 2>&1 < /dev/null &
echo "started long_horizon_eval pid=$!"
'@
```

Monitor:

```powershell
.\opa-wsl.ps1 -User USER -TailLog /home/user/long_horizon_output.log -Lines 120
.\opa-wsl.ps1 -User USER -GrepLog /home/user/long_horizon_output.log -Pattern 'Turn [0-9]+/[0-9]+|probe_correct|Run complete|Probe accuracy|Traceback' -Lines 120
```

### 3. Linear Probe Run (Classifier on Mamba State)

Quick sanity (60 turns):

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
bash ./run_probe.sh 60 3,12,24 5 200
'@
```

Decision run (300 turns, ~171 probe samples):

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
bash ./run_probe.sh 300 3,12,24 5 500
'@
```

Probe log triage:

```powershell
.\opa-wsl.ps1 -User USER -GrepLog /home/user/probe_output.log -Pattern 'test_acc|majority|Report written|Traceback|RuntimeError' -Lines 120
```

### 4. Phase 2 Training Run (Bridge)

Pilot run with disjoint fact splits, best-checkpoint tracking, resumable epoch checkpoints,
and Linux-local artifact storage:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
set -euo pipefail
export HF_HOME=/home/user/.cache/huggingface
HF_TOKEN_FILE="$HF_HOME/token"
if [ ! -s "$HF_TOKEN_FILE" ]; then
  HF_TOKEN_FILE=/mnt/c/Users/USER/.cache/huggingface/token
fi
[ -s "$HF_TOKEN_FILE" ] || { echo "Missing non-empty HF token file"; exit 1; }
export HF_TOKEN="${HF_TOKEN:-$(tr -d '\r\n' < "$HF_TOKEN_FILE")}"
cd /mnt/c/Users/USER/bridge
RUN_DIR=/home/user/mocop_phase2_runs/opa_bridge_pilot
mkdir -p "$RUN_DIR"
/home/user/venv_linux/bin/python -X utf8 check_env.py \
  --require-cuda \
  --output-dir "$RUN_DIR" \
  --checkpoint-dir "$RUN_DIR"
nohup /home/user/venv_linux/bin/python train_bridge.py \
  --epochs 3 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 64 \
  --eval-samples 32 \
  --eval-split val \
  --general-eval-samples 16 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  > /home/user/bridge_train_output.log 2>&1 < /dev/null &
echo "started train_bridge pid=$! run_dir=$RUN_DIR"
'@
```

Activation-bias dry-run example:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
/home/user/venv_linux/bin/python -X utf8 train_bridge.py \
  --dry-run \
  --bridge-mode activation_bias \
  --epochs 1 \
  --dry-run-steps 2
'@
```

Resume from a prior epoch checkpoint:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
set -euo pipefail
export HF_HOME=/home/user/.cache/huggingface
HF_TOKEN_FILE="$HF_HOME/token"
if [ ! -s "$HF_TOKEN_FILE" ]; then
  HF_TOKEN_FILE=/mnt/c/Users/USER/.cache/huggingface/token
fi
[ -s "$HF_TOKEN_FILE" ] || { echo "Missing non-empty HF token file"; exit 1; }
export HF_TOKEN="${HF_TOKEN:-$(tr -d '\r\n' < "$HF_TOKEN_FILE")}"
cd /mnt/c/Users/USER/bridge
RUN_DIR=/home/user/mocop_phase2_runs/opa_bridge_pilot
nohup /home/user/venv_linux/bin/python train_bridge.py \
  --epochs 3 \
  --batch-size 1 \
  --eval-batch-size 1 \
  --train-samples 64 \
  --eval-samples 32 \
  --eval-split val \
  --general-eval-samples 16 \
  --save-checkpoints \
  --checkpoint-every 1 \
  --output-dir "$RUN_DIR" \
  --resume-from "$RUN_DIR/bridge_epoch_001.pt" \
  > /home/user/bridge_train_output.log 2>&1 < /dev/null &
echo "resumed train_bridge pid=$! run_dir=$RUN_DIR"
'@
```

Training log triage:

```powershell
.\opa-wsl.ps1 -User USER -TailLog /home/user/bridge_train_output.log -Lines 120
.\opa-wsl.ps1 -User USER -GrepLog /home/user/bridge_train_output.log -Pattern 'train epoch|eval epoch|Saved checkpoint|Training finished|Traceback|RuntimeError' -Lines 120
```

## First Paid Cloud Pilot (Vast.ai)

Fixed policy for the first paid run:

- Eval split: `val` only. Preserve `test` for post-pilot confirmation.
- Prompt alignment: deferred. The first paid run judges bridge viability only, not
  deployment realism.
- Architecture: Mamba-2 baseline only. Do not mix in Mamba-3, LoRA-rank sweeps, or
  multi-layer compressor changes.

Provider target:

- Provider: Vast.ai
- GPU: `1x A100 80GB` or `1x A100-SXM4-80GB`
- Region preference: Czech Republic first, then Germany / Netherlands / Poland
- Host filters: verified datacenter, reliability `>= 0.98`, Linux image with CUDA 12.x
- Container disk: `>= 64 GB`, `100 GB` preferred
- Storage rule: keep `HF_HOME`, `RUN_ROOT`, logs, and checkpoints on `/workspace` or an attached volume, not `/dev/shm`
- Pilot-1 hard cap: `20 EUR`
- Total exploratory budget before review: `100 EUR`

Expected pilot footprint:

- Stage 1 is a gated 1-epoch run that proves the host, checkpoint path, and logs are clean.
- Stage 2 resumes only if epoch 1 looks healthy.
- Observed on 2026-03-10: an A100 40GB host used about `35.8 GiB` VRAM at `--batch-size 1`
  while GPU utilization stayed around `21%`, so the preferred follow-up host is an `80GB`
  card with a larger training batch.
- Realistic total within `100 EUR`: about 4-8 A100 pilot-length runs, depending on the
  host price on the day and whether stage-1 gating rejects any host.

Stage 1: gate on epoch 1 only.

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

Stage 2: resume only if epoch 1 completed cleanly. On an `80GB` host, start the resumed
run at `--batch-size 2`; test `4` only after a short smoke confirms headroom and stable loss.

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

If the resumed `80GB` host still has large VRAM headroom after warmup, clone the command,
test `--batch-size 4` in a short verification run, and keep it only if throughput improves
without destabilizing loss.

Expected artifacts:

- `$RUN_DIR/bridge_best.pt`
- `$RUN_DIR/bridge_epoch_001.pt`
- `$RUN_DIR/bridge_epoch_<epoch>.pt`
- `$LOG_FILE`
- Eval summaries in the training log (`Bridge`, `Baseline`, `Random`, `p=...`)

Stop conditions:

- Preflight fails. Do not start the paid run.
- Stage 1 fails to produce `bridge_epoch_001.pt`.
- Stage 1 log shows `Traceback`, `RuntimeError`, CUDA OOM, NaN/Inf loss, or clearly broken throughput.
- Do not start Stage 2 until Stage 1 has been reviewed.
- Any `Traceback`, `RuntimeError`, CUDA OOM, or NaN/Inf loss appears in the log.
- Model download or auth failures persist after fixing `HF_TOKEN`.
- An interruptible host is reclaimed before the first checkpoint.

Post-run sync:

- Copy `$RUN_DIR` and `$LOG_FILE` back before terminating the instance.
- Review metrics before spending beyond the `20 EUR` pilot-1 cap.

### 5. Report Accuracy from Latest Probe Run

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
/home/user/venv_linux/bin/python - <<'PY'
import glob
import json
import os
import sys

runs = sorted(glob.glob("mamba_probe_runs/run_*"))
if not runs:
    print("No probe runs found.", file=sys.stderr)
    sys.exit(1)

report_path = os.path.join(runs[-1], "report.json")
with open(report_path, "r", encoding="utf-8") as fp:
    report = json.load(fp)

probe = report["probe_result"]
print("report_path:", report_path)
print("test_acc:", round(float(probe["test_acc"]), 4))
print("majority_test_acc:", round(float(probe["majority_test_acc"]), 4))
print("samples_test:", int(probe["samples_test"]))
print("interpretation:", report["interpretation"])
PY
'@
```

## Artifact Locations

On remote bridge path (`/mnt/c/Users/USER/bridge`):

- `long_horizon_runs/run_<timestamp>/summary.json`
- `long_horizon_runs/run_<timestamp>/context_vectors.jsonl`
- `long_horizon_runs/run_<timestamp>/turns.jsonl`
- `long_horizon_runs/run_<timestamp>/probes.csv`
- `mamba_probe_runs/run_<timestamp>/report.json`
- `mamba_probe_runs/run_<timestamp>/probe_rows.jsonl`
- Bridge training artifacts live wherever `--output-dir` points.
- Recommended Opa path: `/home/user/mocop_phase2_runs/opa_bridge_pilot`
- Recommended cloud path: `/workspace/mocop_phase2_runs/pilot_01`

Log files:

- `/home/user/long_horizon_output.log`
- `/home/user/probe_output.log`
- `/home/user/smoke_output.log`
- `/home/user/bridge_train_output.log`

## Anti-Patterns (Do Not Use)

Avoid commands like this from `cmd.exe`:

```powershell
ssh USER@192.168.2.194 "wsl bash -lc 'python3 ... | tee /home/user/log.txt'"
```

Reason:

- The Windows shell layer may consume pipes/quotes before WSL parsing.
- Failures are intermittent and hard to debug.

Use `opa-wsl.ps1` instead.

## Probe Schedule Safety

The probe scheduler can experience **lag drift** when an injection turn and a probe due-turn collide.
With `inject_every=6` and `lags=[3,12,24]`, probe turns shift by 1+ turns, corrupting lag measurements.

**Default safe config**: `inject_every=5` (zero drift for lags 3,12,24).

Expected sample counts with `inject_every=5`:

| Turns | Probe Rows | Test Samples (30%) |
|-------|-----------|--------------------|
| 60    | ~27       | ~8                 |
| 120   | ~63       | ~19                |
| 300   | ~171      | ~51                |
| 500   | ~291      | ~87                |

The script will **fail fast** if drift is detected. To override: `--allow-lag-drift`.
To find valid configs: the script prints zero-drift candidates in the error message.

## Troubleshooting

- `Remote command failed with exit code 255`:
  - SSH auth/host connectivity issue.
- `Schedule audit detected lag drift`:
  - Use the recommended `inject_every` from the error message (default: 5).
- `run_probe.sh: unrecognized arguments`:
  - Remote script is stale; sync latest `run_probe.sh`.
- `Test split too small`:
  - Increase `--turns` or lower `--min-test-samples`.
- No grep output:
  - Pattern not present yet; use `-TailLog` first.
- Progress bars/noisy logs:
  - Scripts already set `HF_HUB_DISABLE_PROGRESS_BARS=1`; verify updated files on remote.
