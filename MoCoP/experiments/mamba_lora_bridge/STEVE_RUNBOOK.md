# Steve-PC Experiment Runbook

Date: 2026-03-25
Workspace: `MoCoP/experiments/mamba_lora_bridge`

This is the current operational handbook for running MoCoP experiments on Steve-PC.
It replaces "go read the handoff and reconstruct the rest from scripts."

## Purpose

Use Steve for:

- live browser-chat qualitative probes on the bridged Qwen 1.5B surface
- alpha / temperature sweeps against the LAN chat server
- recorder-coupled bridge measurements on the 4090 host

Do not use this file for old Opa procedures. Opa has its own runbook in `OPA_RUNBOOK.md`.

## Host Summary

- Host alias: `steve`
- Windows user: `tikii`
- LAN host used in current scripts: `192.168.2.49`
- GPU: RTX 4090 Mobile, 16 GB VRAM
- WSL distro: Ubuntu 24.04 on WSL2
- Remote bridge dir on Windows: `C:\Users\tikii\bridge`
- Same directory in WSL: `/mnt/c/Users/tikii/bridge`
- Python entrypoint for the chat surface: `chat_server.py`

## Preconditions

Before touching Steve:

1. Steve is on the correct Wi-Fi and the network profile is `Private`.
2. `ssh steve` works from the laptop.
3. Steve is not actively being used for something that should not be interrupted.
4. If the task is long-running, coordinate first. Steve is a shared machine, not a headless lab box.

Quick sanity checks from the laptop:

```powershell
ssh steve hostname
Test-NetConnection 192.168.2.49 -Port 22
Test-NetConnection 192.168.2.49 -Port 7860
```

## Canonical Components

The current Steve stack is built around these files:

- `autobiographical_memory.py`
- `chat_server.py`
- `launch_chat_windows.ps1`
- `install_steve_chat_task.ps1`
- `inspect_steve_chat_task.ps1`
- `stop_steve_chat_task.ps1`
- `set_steve_chat_alpha.ps1`
- `set_steve_chat_layers.ps1`
- `set_steve_chat_model.ps1`
- `set_steve_chat_temperature.ps1`
- `steve-wsl.ps1`
- `run_step5d_steve_sweep.ps1`
- `run_steve_midnight_recorder.ps1`
- `steve_chat_config.json`

Scheduled tasks on Steve:

- `MoCoP Steve Chat`
- `MoCoP Steve Chat Indicator`
- optionally `MoCoP Steve Midnight Recorder`

## Current Default State

If nothing else is specified, Steve should be restored to:

- model: `Qwen/Qwen2.5-1.5B`
- alpha: `0.2`
- temperature: `0.7`
- dual gate: enabled
- dual-gate warmup turns: `3`
- dual-gate salience quantile: `0.75`
- dual-gate surprise quantile: `0.75`

Those values live in `steve_chat_config.json` and are consumed by `launch_chat_windows.ps1`.

## Sync Procedure

If you changed Steve-facing code locally, copy the updated files into Steve's bridge dir before reinstalling the task.

Typical targets:

- `autobiographical_memory.py`
- `chat_server.py`
- `launch_chat_windows.ps1`
- `install_steve_chat_task.ps1`
- `inspect_steve_chat_task.ps1`
- `stop_steve_chat_task.ps1`
- any setter or experiment script you modified

Example pattern:

```powershell
scp .\autobiographical_memory.py steve:C:/Users/tikii/bridge/
scp .\chat_server.py steve:C:/Users/tikii/bridge/
scp .\launch_chat_windows.ps1 steve:C:/Users/tikii/bridge/
scp .\install_steve_chat_task.ps1 steve:C:/Users/tikii/bridge/
```

If the launcher or task wiring changed, reinstall after syncing.

## Preferred Remote Execution Path

For WSL-side work on Steve, use `steve-wsl.ps1`, not raw nested commands like:

- `ssh steve "wsl bash -lc '...'"` for nontrivial jobs
- `ssh steve "cat > file"` against the Windows host

Why:

- Windows -> SSH -> WSL -> Bash eats quotes for sport
- Steve's default WSL `python3` does not have the MoCoP torch stack
- writing shell scripts through Windows tools often leaves CRLF behind

`steve-wsl.ps1` fixes the common path by:

- piping Bash over stdin to `wsl -u root bash -se`
- using the working bridge venv at `/root/mocop_venv/bin/python3`
- normalizing local `RunFile` input to LF before execution

Basic WSL command:

```powershell
powershell -ExecutionPolicy Bypass -File .\steve-wsl.ps1 -Run @'
cd /mnt/c/Users/tikii/bridge
pwd
ls
'@
```

Run a synced Python file inside Steve's actual MoCoP venv:

```powershell
powershell -ExecutionPolicy Bypass -File .\steve-wsl.ps1 -BridgePythonFile ssm_vs_hidden_separation.py
```

Run a local shell script without CRLF pain:

```powershell
powershell -ExecutionPolicy Bypass -File .\steve-wsl.ps1 -RunFile .\some_steve_job.sh
```

## Gotchas (Anda-Conda, 2026-03-28)

1. **`-Run @'...'@` does not work when called from bash.** The PowerShell here-string syntax breaks when Claude Code (bash shell) invokes `powershell -File steve-wsl.ps1 -Run @'...'@`. Use `-RunFile` with a `.sh` script instead.

2. **`-RunFile` needs an absolute path.** Relative paths like `./run_foo.sh` resolve against PowerShell's cwd, which may not be the bridge dir. Always use full paths: `powershell -ExecutionPolicy Bypass -File "C:\Users\cerub\...\steve-wsl.ps1" -RunFile "C:\Users\cerub\...\run_foo.sh"`

3. **Both Opa AND Steve OOM on >10K tokens with single-pass Mamba-2.8b (slow path).** The HuggingFace fallback (no `mamba-ssm` kernels) materializes huge intermediate tensors — 20GB+ for 20K tokens. Fix: use chunked forward passes with cache carry-forward (512 tokens/chunk). See `trajectory_sequential.py` for the pattern.

5. **HF model cache locations:**
   - Steve WSL: `/root/.cache/huggingface/hub/` (Mamba-2.8b already cached)
   - Opa WSL: `/home/user/.cache/huggingface/`
   - Opa Windows: `C:\Users\User\.cache\huggingface\`

4. **Steve's Python is WSL-only.** No Windows Python. The venv is `/root/mocop_venv/bin/python3`. Use `steve-wsl.ps1`, never raw `ssh steve "python ..."`.

## Install / Start / Stop

Install or refresh the scheduled tasks:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\install_steve_chat_task.ps1
```

Inspect current task state and config:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\inspect_steve_chat_task.ps1
```

Stop the live chat cleanly:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\stop_steve_chat_task.ps1
```

Important behavior:

- `install_steve_chat_task.ps1` starts both the chat task and the tray-indicator task.
- the chat task is launched hidden through `wscript.exe` and `launch_hidden_powershell.vbs`
- `steve_chat_indicator.ps1` is intended to be singleton-only; if Steve ever sees multiple `Experiment Status Tracker` windows again, the indicator task likely spawned from an older copy and should be redeployed
- the stop script does not just stop the scheduled task; it also kills any lingering WSL listener on port `7860`

## Runtime Config Knobs

Do not hand-edit process arguments. Change Steve through the config setters unless you are debugging the launcher itself.

Change alpha:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_alpha.ps1 -Alpha 0.2
```

Change model:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_model.ps1 -QwenModelId Qwen/Qwen2.5-1.5B
```

Change temperature:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_temperature.ps1 -Temperature 0.0
```

Change target layers:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_layers.ps1 -TargetLayers "5:v_proj,6:v_proj,7:v_proj,8:v_proj"
```

Important:
- The current 1.5B bridge checkpoint expects `4` bias heads. Single-layer overrides like `13:v_proj` are rejected on purpose and will not be written into config unless explicit head-remap support is added later.

Stage a change without interrupting the current live chat:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_alpha.ps1 -Alpha 0.1 -NoRestart
```

Config keys currently respected by the launcher:

- `alpha`
- `qwen_model_id`
- `qdrant_write_mode`
- `temperature`
- `target_layers`
- `dual_gate_enabled`
- `dual_gate_warmup_turns`
- `dual_gate_salience_quantile`
- `dual_gate_surprise_quantile`

Qdrant write semantics on Steve:

- `direct`: write immediately, fall back to retry-queue on failure
- `pending`: normal gate memories queue for sleep reconciliation, not auto-replay
- `critical-only`: safety-critical memories write immediately; noncritical gate memories queue for sleep reconciliation

Pending queue behavior after the sleep-handoff fix:

- rows tagged `replay_policy=sleep` stay in `qdrant_gate_pending.jsonl` until `sleep_reconcile.py` or a manual flush handles them
- rows tagged `replay_policy=retry` are still auto-replayed by the background worker when the sink is healthy again
- `NOTE` / `CONSOLIDATE` events queue normally, but a `DISMISS` with `open_tension=true` is also forced into the sleep queue with `reason=queued:sleep_tagged`
- `sleep_gate_events_latest.jsonl` is the wake-to-sleep audit stream; it should mirror every gate-time sleep candidate, including open-tension dismissals that would otherwise look like `qdrant=false`
- `/status` now exposes `qdrant_sleep_pending_count` and `qdrant_retry_pending_count` so you can tell which kind of backlog you are looking at
- `/status` also exposes `open_tension_count` and `sleep_tagged_count` so you can tell whether the gate is only observing or actually handing events to sleep

## Health Checks

### 1. LAN / HTTP sanity

```powershell
Invoke-WebRequest http://192.168.2.49:7860/
Invoke-RestMethod http://192.168.2.49:7860/status
```

What good looks like:

- HTTP root returns `200`
- `/status` returns `running=true`
- `alpha`, `temperature`, and `model_id` match the intended config
- `turns=0` after a fresh restart

### 2. WSL listener sanity

```powershell
powershell -ExecutionPolicy Bypass -File .\steve-wsl.ps1 -Run "ss -ltnp | grep 7860"
```

You want to see Python listening on `0.0.0.0:7860`.

### 3. Portproxy sanity

```powershell
ssh steve "cmd /c netsh interface portproxy show v4tov4"
```

You want:

- listen `0.0.0.0:7860`
- connect address equal to the current WSL IP, not `127.0.0.1`

`launch_chat_windows.ps1` rewrites this on every start by resolving the current WSL IP first.

## Standard Experiment Modes

### A. Qualitative browser chat

Use when you want live probing through the browser surface.

1. Ensure Steve is at the intended model / alpha / temperature.
2. Inspect task state.
3. Open `http://192.168.2.49:7860/` in a browser.
4. Use the status pill and stop button in the UI as the first-line sanity check.

Notes:

- browser chat keeps in-memory session history for the running process
- restarting the task clears the live session memory but keeps transcript files on disk
- the tray indicator should stay running even when the chat task is parked
- for ad hoc WSL experiments, sync the file with `scp` and run it through `steve-wsl.ps1 -BridgePythonFile ...`
- the browser UI now has a right-side live inspector for runtime, gate, recall, and the last memory packet when `chat_server.py` and `autobiographical_memory.py` are current on Steve

### A.1 Deploy the live memory inspector

Use this when you want the chat surface plus the live memory-pipeline pane.

From the laptop repo root:

```powershell
cd C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge
scp .\autobiographical_memory.py steve:C:/Users/tikii/bridge/
scp .\chat_server.py steve:C:/Users/tikii/bridge/
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\install_steve_chat_task.ps1
```

Then open:

```text
http://192.168.2.49:7860/
```

What you should see:

- left pane: normal chat
- right pane: live inspector
  - runtime
  - last gate
  - last recall
  - last memory packet

If the browser still shows the old single-column UI, the host is still serving an older `chat_server.py`.

### B. Step 5d alpha sweep

Use when you want the scripted minimum-effective-dose pass.

Run from the repo on the laptop:

```powershell
cd C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge
powershell -ExecutionPolicy Bypass -File .\run_step5d_steve_sweep.ps1
```

What it does:

- sets Steve temperature
- runs baseline `alpha 0.0`
- runs the configured alpha sweep
- checks `/status` after each restart
- writes logs locally under `tmp\step5d_*`
- restores defaults at the end
- parks Steve unless `-LeaveRunning` is set

### C. Recorder-coupled pass

Use when you want bridge entropy / diversity / drift measurements rather than chat-only output.

Run directly on Steve:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\run_steve_midnight_recorder.ps1 -Alpha 0.2 -Temperature 0.0
```

What it does:

- stops the normal chat task first
- runs `step5d_bridge_recorder.py` inside WSL
- writes recorder outputs under `C:\Users\tikii\bridge\bridge_recorder_runs\`
- writes a run log under `C:\Users\tikii\bridge\logs\`

### D. Sleep threshold sweep

Use when sleep reconciliation is behaving honestly, but you need to tune classification thresholds against a real archived pending batch instead of guessing.

Run from the laptop after syncing the helper:

```powershell
scp .\sleep_threshold_sweep.py steve:C:/Users/tikii/bridge/
powershell -ExecutionPolicy Bypass -File .\steve-wsl.ps1 -BridgePythonFile sleep_threshold_sweep.py `
  -PythonArgs '--pending-path','qdrant_gate_pending.reconciled_<timestamp>.jsonl','--mamba-state','mamba_bootstrap_state_latest.pt','--replay-device','cuda','--only-writing'
```

What it does:

- loads one archived pending batch
- computes same-space Mamba replay once
- sweeps `strength_threshold` / `coherence_threshold` without reloading Mamba for every combo
- prints which threshold pairs would write, weaken, or discard each entry

Use this before touching defaults in `sleep_reconcile.py`.

## Artifacts and Logs

Useful locations on Steve:

- `C:\Users\tikii\bridge\logs\steve_chat_windows_task.log`
- `C:\Users\tikii\bridge\logs\steve_midnight_recorder_<timestamp>.log`
- `C:\Users\tikii\bridge\bridge_recorder_runs\`
- `C:\Users\tikii\bridge\chat_session_latest.txt`
- `C:\Users\tikii\bridge\chat_turns_latest.jsonl`

Useful locations on the laptop:

- `tmp\step5d_*` for scripted sweep logs and metrics
- `tmp\steve_dual_gate\` for dual-gate verification captures

## Known Good Defaults and Warnings

- The recommended live surface is base `Qwen/Qwen2.5-1.5B`, not `-Instruct`.
- The current minimum effective dose is `alpha 0.2`.
- Do not use the old broken bridge checkpoints with the wrong head width.
- Steve does not have the Mamba fast path installed; sequential fallback is expected.

## Failure Signatures

### SSH is dead

Likely causes:

- Steve is on the wrong Wi-Fi
- Windows network profile flipped back to `Public`
- Steve is asleep

### TCP to `7860` works but HTTP hangs

Most likely:

- stale or wrong Windows `portproxy`
- reinstall / restart the Steve chat task so `launch_chat_windows.ps1` rewrites the portproxy to the live WSL IP

### A Python script says `ModuleNotFoundError: No module named 'torch'`

You hit Steve's wrong Python.

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\steve-wsl.ps1 -BridgePythonFile your_script.py
```

Do not trust `/usr/bin/python3` on Steve for MoCoP work.

### Task says it restarted but old process is still there

Use the real stop path:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\stop_steve_chat_task.ps1
```

Then start again through the scheduled task path.

### Browser surface acts strange after a config change

Check `/status` before trusting the UI. The intended model / alpha / temperature must be visible there, not just in the config file.

### A remote shell script fails with weird syntax or `pipefail` nonsense

Common cause:

- the file was written with CRLF from Windows
- or you are nesting too many quote layers through raw `ssh steve "wsl bash -lc ..."`

Fix:

- use `steve-wsl.ps1 -RunFile ...`
- or sync the file with `scp` and run it via `steve-wsl.ps1`

## Etiquette and Cleanup

- Prefer hidden scheduled-task launches over manual visible shells.
- If Steve is actively being used, avoid long runs unless coordinated.
- Do not leave noisy background work running without the tray indicator and stop path intact.
- When done, restore the default config and usually park the chat task.

Common restore sequence:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_model.ps1 -QwenModelId Qwen/Qwen2.5-1.5B
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_temperature.ps1 -Temperature 0.7
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_alpha.ps1 -Alpha 0.2
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\stop_steve_chat_task.ps1
```

Then confirm the indicator is still alive:

```powershell
ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\inspect_steve_chat_task.ps1
```

## Related Files

- `archive/STEVE_PC_HANDOFF_2026-03-20.md` - historical Steve field notes and original handoff context
- `STEVE_PC_HANDOFF.md` - redirect stub kept only for backward compatibility
- `steve-wsl.ps1` - WSL helper for Steve to avoid Windows -> SSH -> WSL quote hell
- `OPA_RUNBOOK.md` - Opa-PC local validation and experiment runbook
- `VASTAI_RUNBOOK.md` - paid cloud pilot runbook
- `step5d_min_dose_protocol.md` - the ethics-gated alpha-sweep protocol
