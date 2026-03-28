# Opa-PC Experiment Runbook

Date: 2026-03-25
Workspace: `MoCoP/experiments/mamba_lora_bridge`

This is the current operational handbook for running MoCoP experiments on Opa-PC.
Use this for the local CUDA box and `opa-wsl.ps1` workflow. Do not use it for Steve or Vast.ai.

## Purpose

Use Opa-PC for:

- PyTorch / CUDA preflight and environment validation
- regression and split smoke tests
- long-horizon eval and probe runs
- bridge tooling validation
- cheap or dry-run training checks

Do not treat Opa as the default full-training host. The RTX 3070 is the correctness box, not the heavy bridge-training box.

## Host Summary

- Host alias: `opa`
- LAN host: `192.168.2.194`
- GPU: RTX 3070, 8 GB VRAM
- Remote Windows dir: `C:\Users\User\bridge`
- WSL path: `/mnt/c/Users/User/bridge`
- Preferred helper: `opa-wsl.ps1`

## Why This Exists

The failure mode we are avoiding:

- nested `ssh` / `cmd.exe` / WSL quoting mangles commands
- logs spill inline and waste tokens
- Windows SSH defaults to non-UTF-8 behavior

Standard fix:

- use PowerShell only
- use `opa-wsl.ps1`
- send Bash text to WSL safely
- write logs remotely and retrieve only tails or greps

## Required Files

- `opa-wsl.ps1`
- `autobiographical_memory.py`
- `run_opa_reincarnation_qualitative.ps1`
- `run_opa_sjt_behavioral_eval.ps1`
- `ensure_opa_wifi.ps1`
- `install_opa_wifi_watch_task.ps1`
- `check_env.py`
- `run_smoke.sh`
- `run_long_horizon.sh`
- `run_probe.sh`
- `run_format_transplant_probe.sh`
- `long_horizon_eval.py`
- `mamba_linear_probe.py`
- `format_transplant_probe.py`
- `run_sjt_behavioral_eval.py`
- `score_sjt_behavioral_eval.py`
- `train_bridge.py`

## Preconditions

1. `ssh opa` works.
2. WSL is available on Opa.
3. The bridge checkout exists at `/mnt/c/Users/User/bridge`.
4. The Linux venv exists at `/home/user/venv_linux`.
5. For Qdrant-backed D0/D1/sleep work, the venv must also have:
   - `qdrant-client`
   - `sentence-transformers`

Quick sanity:

```powershell
ssh opa hostname
Test-NetConnection 192.168.2.194 -Port 22
```

Package sanity for D1 / sleep:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
/home/user/venv_linux/bin/python - <<'PY'
mods = {}
for name in ("qdrant_client", "sentence_transformers"):
    try:
        __import__(name)
        mods[name] = "ok"
    except Exception as exc:
        mods[name] = repr(exc)
print(mods)
PY
'@
```

## Wi-Fi Resilience Watch

If Opa keeps drifting off `KFCandWatermelon`, install the local watchdog on Opa itself.

One-shot check:

```powershell
powershell -ExecutionPolicy Bypass -File .\ensure_opa_wifi.ps1 -TargetSsid "KFCandWatermelon" -SetPrivate
```

Recurring 5-minute task:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_opa_wifi_watch_task.ps1 -TargetSsid "KFCandWatermelon" -EveryMinutes 5
```

Default log:

```text
C:\Users\User\bridge\logs\opa_wifi_watch.log
```

The enforcement script only attempts a reconnect when:

- Opa is not already on the target SSID
- the target SSID is currently visible

If `-SetPrivate` is present, it also pushes the matching Wi-Fi profile back to `Private` after reconnect.

## One-Time Validation

Run from the bridge workspace:

```powershell
cd C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge
```

Connectivity and WSL sanity:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
echo "connected"
whoami
uname -a
python3 --version
'@
```

If PowerShell blocks script execution:

```powershell
powershell -ExecutionPolicy Bypass -File .\opa-wsl.ps1 -User USER -Run "echo ok"
```

## Sync Before Runs

```powershell
scp `
  .\autobiographical_memory.py `
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

If you plan to run `chat_server.py` on Opa for D2/private-recall work, `autobiographical_memory.py` must be synced together with `chat_server.py`. The inspector/recalled-memory path now depends on it.

## Core Command Patterns

Run arbitrary remote Bash safely:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
/home/user/venv_linux/bin/python regression_smoke.py
/home/user/venv_linux/bin/python test_splits.py
'@
```

Tail logs:

```powershell
.\opa-wsl.ps1 -User USER -TailLog /home/user/long_horizon_output.log -Lines 120
```

Grep high-signal lines:

```powershell
.\opa-wsl.ps1 -User USER -GrepLog /home/user/long_horizon_output.log -Pattern 'Traceback|RuntimeError|ERROR|Probe accuracy|Run complete' -Lines 120
```

## Phase 2 Preflight

Run this before any serious bridge job:

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

## Standard Experiment Modes

### 1. Smoke Test

```powershell
.\opa-wsl.ps1 -User USER -Run "bash /mnt/c/Users/USER/bridge/run_smoke.sh"
.\opa-wsl.ps1 -User USER -GrepLog /home/user/smoke_output.log -Pattern 'FAILED|Traceback|SMOKE TEST COMPLETE' -Lines 120
```

### 2. Long-Horizon Run

Foreground:

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

Background:

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

### 3. Linear Probe

Quick sanity:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
bash ./run_probe.sh 60 3,12,24 5 200
'@
```

Decision run:

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

### 3b. Format-Transplant Control

Cheap threat-to-validity control for the original Phase 1 probe. This reruns the Layer 3 probe on multiple prompt surfaces and reports:

- within-format accuracy
- train-on-one-format / test-on-another-format transplant accuracy
- pooled mixed-format accuracy

Foreground:

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
bash ./run_format_transplant_probe.sh 300 3,12,24 5 300 5
'@
```

Monitor:

```powershell
.\opa-wsl.ps1 -User USER -TailLog /home/user/format_transplant_probe.log -Lines 120
```

Artifacts:

- `/mnt/c/Users/USER/bridge/format_transplant_probe_runs/`
- `/home/user/format_transplant_probe.log`

### 4. Bridge Training Dry-Run / Small Pilot (Legacy SSM Baseline)

Use this path for dry-runs and small correctness checks, not as the default long paid run.

Important: `train_bridge.py` is the older baseline training path and still extracts Mamba `ssm_states`. It is not the current `hidden_last_token` reincarnation path used by Steve chat, `train_cheese_bridge.py`, or `reincarnated_inference.py`. Treat results from this section as baseline/legacy evidence unless and until that training path is explicitly migrated.

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

Small resumable pilot:

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

Training log triage:

```powershell
.\opa-wsl.ps1 -User USER -TailLog /home/user/bridge_train_output.log -Lines 120
.\opa-wsl.ps1 -User USER -GrepLog /home/user/bridge_train_output.log -Pattern 'train epoch|eval epoch|Saved checkpoint|Training finished|Traceback|RuntimeError' -Lines 120
```

### 5. Reincarnation Qualitative Compare

Use the dedicated runner for the bridge-backed Qwen qualitative pass. This is the canonical Opa-side smoke for the Steve `4090` reincarnation comparison. It syncs the minimum file set, runs `temp 0.7` and `temp 0.3`, and copies the result files back into the local repo.

Run from the bridge workspace:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_opa_reincarnation_qualitative.ps1 -User USER -MaxNewTokens 140
```

Notes:

- Opa is an RTX `3070`, not an `A100`. Treat this as a qualitative smoke or portability check, not the full stronger-host replication.
- The runner uses `opa-wsl.ps1` internally and executes with `/home/user/venv_linux/bin/python`.
- Use `-NoSync` only if the bridge files are already current on Opa and you are rerunning the same setup.

Expected outputs:

- local: `.\run_reincarnation\opa_reincarnation_t07_<tokens>tok_<date>.txt`
- local: `.\run_reincarnation\opa_reincarnation_t03_<tokens>tok_<date>.txt`
- remote staging: `C:\Users\User\bridge\opa_reincarnation_*.txt`

### 5b. SJT Behavioral Eval Pilot

Use this for the cheap forced-choice warmth/care pilot on a fresh Opa live chat surface.

Run from the bridge workspace:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_opa_sjt_behavioral_eval.ps1 -User USER
```

Notes:

- The runner launches a fresh Opa chat instance for baseline `alpha 0.0`, runs the panel, then replaces it with a fresh candidate `alpha 0.2` instance and scores the comparison.
- Outputs land in `.\behavioral_eval_runs\opa_sjt_<timestamp>\`.
- If Opa is flaky on the LAN, fix host reachability first; do not fall back to ad-hoc nested SSH/WSL commands.

## Reporting Helper

Report the latest probe run:

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
report = os.path.join(runs[-1], "report.json")
with open(report, "r", encoding="utf-8") as fh:
    data = json.load(fh)
print(json.dumps({
    "run": runs[-1],
    "test_acc": data.get("test_acc"),
    "majority_acc": data.get("majority_acc"),
    "lags": data.get("lags"),
}, indent=2))
PY
'@
```

## Artifact Locations

- `/home/user/long_horizon_output.log`
- `/home/user/probe_output.log`
- `/home/user/bridge_train_output.log`
- `/home/user/mocop_phase2_runs/`
- `/mnt/c/Users/USER/bridge/mamba_probe_runs/`
- `.\run_reincarnation\opa_reincarnation_*.txt`

## Warnings

- Opa is for validation and moderate experiments. Do not assume it can survive full bridge training.
- Always use `python -X utf8` when invoking Python over SSH if output may contain non-ASCII.
- Keep logs remote; do not stream giant outputs into the chat surface.
- If Opa goes missing from the LAN, suspect Wi-Fi or Windows network profile before blaming the code.

## Related Files

- `VASTAI_RUNBOOK.md` - paid cloud pilot path
- `RUNBOOK.md` - compatibility index for old references
- `opa-wsl.ps1` - the actual remote execution helper
