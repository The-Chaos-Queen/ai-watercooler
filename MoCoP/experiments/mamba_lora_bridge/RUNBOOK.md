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
cd C:\Users\cerub\OneDrive\Dokumente\LLM\Project_MUD\experiments\mamba_lora_bridge
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
  .\models.py `
  .\cognitive_bridge.py `
  .\long_horizon_eval.py `
  .\mamba_linear_probe.py `
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
python3 regression_smoke.py
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

## Full Experiment Procedure

Goal:

- Load Mamba pipeline.
- Run 60 turns.
- Inject facts every 6 turns.
- Collect context/state vectors.
- Train linear classifier probe.
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
python3 long_horizon_eval.py \
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
nohup python3 long_horizon_eval.py \
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

### 4. Report Accuracy from Latest Probe Run

```powershell
.\opa-wsl.ps1 -User USER -Run @'
cd /mnt/c/Users/USER/bridge
python3 - <<'PY'
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

Log files:

- `/home/user/long_horizon_output.log`
- `/home/user/probe_output.log`
- `/home/user/smoke_output.log`

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
