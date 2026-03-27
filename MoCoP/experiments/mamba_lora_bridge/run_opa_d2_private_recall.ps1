param(
    [string]$User = "user",
    [string]$InstanceId = "",
    [int]$Port = 7863,
    [switch]$NoSync
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = "C:\Users\cerub\OneDrive\Dokumente\LLM"
$bridgeDir = Join-Path $repoRoot "MoCoP\experiments\mamba_lora_bridge"
$runnerPath = Join-Path $bridgeDir "opa-wsl.ps1"
$artifactRoot = Join-Path $bridgeDir "run_reincarnation"

if ([string]::IsNullOrWhiteSpace($InstanceId)) {
    $InstanceId = "baby_d2_smoke_{0}" -f (Get-Date -Format "yyyyMMddTHHmmss")
}

$remoteBridgeWin = "C:/Users/User/bridge"
$remoteBridgeWsl = "/mnt/c/Users/User/bridge"
$remoteRunWin = "$remoteBridgeWin/d2_runs/$InstanceId"
$remoteRunWsl = "$remoteBridgeWsl/d2_runs/$InstanceId"
$remoteSnapshotWsl = "$remoteRunWsl/snapshots"
$remoteCollection = "mocop_private_$InstanceId"

$localRunDir = Join-Path $artifactRoot $InstanceId
New-Item -ItemType Directory -Force -Path $localRunDir | Out-Null

$syncFiles = @(
    "autobiographical_memory.py",
    "birth.py",
    "chat_server.py",
    "d2_private_recall_eval.py",
    "d2_seed_prompts.txt",
    "run_sleep_cycle.py",
    "sleep_ethics_gate.py",
    "sleep_flush.py",
    "sleep_reconcile.py",
    "step5d_chat_client.py"
) | ForEach-Object { Join-Path $bridgeDir $_ }

if (-not $NoSync) {
    Write-Host "Syncing D2 files to Opa..." -ForegroundColor Cyan
    & scp @syncFiles "opa:$remoteBridgeWin/"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to sync D2 files to Opa."
    }
}

Write-Host "Creating private D2 instance $InstanceId on Opa..." -ForegroundColor Cyan
& $runnerPath -User $User -Run @"
cd $remoteBridgeWsl
/home/user/venv_linux/bin/python -X utf8 birth.py --instance-id $InstanceId
/home/user/venv_linux/bin/python -X utf8 birth.py --verify $InstanceId
"@

$remoteScript = @'
set -euo pipefail

cd __BRIDGE_WSL__

INSTANCE='__INSTANCE__'
COLLECTION='__COLLECTION__'
RUN_DIR='__RUN_DIR__'
SNAPSHOT_DIR='__SNAPSHOT_DIR__'
PORT='__PORT__'

mkdir -p "\$RUN_DIR" "\$SNAPSHOT_DIR"
rm -f "\$RUN_DIR/chat_server.log" "\$RUN_DIR/chat_server.pid"
rm -f "\$RUN_DIR/opa_d2_seed_turns.jsonl" "\$RUN_DIR/opa_d2_private_recall_eval.json"
rm -f "\$RUN_DIR/chat_session_latest.txt" "\$RUN_DIR/chat_turns_latest.jsonl" "\$RUN_DIR/dual_gate_turns_latest.jsonl"
rm -f "\$RUN_DIR/salience_memory_latest.jsonl" "\$RUN_DIR/sleep_gate_events_latest.jsonl" "\$RUN_DIR/surprise_events_latest.jsonl"
rm -f "\$RUN_DIR/qdrant_gate_pending.jsonl" "\$RUN_DIR/qdrant_gate_pending.flushed.jsonl" "\$RUN_DIR/qdrant_gate_pending.reconciled.jsonl"
rm -f "\$RUN_DIR/memory_formation_log.jsonl" "\$RUN_DIR/private_recall_log.jsonl" "\$RUN_DIR/disposition_snapshot_latest.json"

start_server() {
  PYTHONUNBUFFERED=1 /home/user/venv_linux/bin/python -X utf8 chat_server.py \
    --qwen-model-id Qwen/Qwen2.5-1.5B \
    --alpha 0.2 \
    --temperature 0.7 \
    --host 0.0.0.0 \
    --port "\$PORT" \
    --instance-id "\$INSTANCE" \
    --no-shared-memory \
    --qdrant-collection "\$COLLECTION" \
    --qdrant-write-mode critical-only \
    --transcript-path "\$RUN_DIR/chat_session_latest.txt" \
    --turn-log-path "\$RUN_DIR/chat_turns_latest.jsonl" \
    --dual-gate-log-path "\$RUN_DIR/dual_gate_turns_latest.jsonl" \
    --dual-gate-memory-path "\$RUN_DIR/salience_memory_latest.jsonl" \
    --dual-gate-sleep-path "\$RUN_DIR/sleep_gate_events_latest.jsonl" \
    --dual-gate-surprise-path "\$RUN_DIR/surprise_events_latest.jsonl" \
    --qdrant-pending-path "\$RUN_DIR/qdrant_gate_pending.jsonl" \
    --qdrant-flushed-path "\$RUN_DIR/qdrant_gate_pending.flushed.jsonl" \
    --memory-formation-log-path "\$RUN_DIR/memory_formation_log.jsonl" \
    --recall-log-path "\$RUN_DIR/private_recall_log.jsonl" \
    > "\$RUN_DIR/chat_server.log" 2>&1 < /dev/null &
  SERVER_PID=\$!
  echo "\$SERVER_PID" > "\$RUN_DIR/chat_server.pid"
  echo "[d2] started chat_server pid=\$SERVER_PID"
}

wait_ready() {
  /home/user/venv_linux/bin/python - <<'PY'
import json
import sys
import time
import urllib.request

url = "http://127.0.0.1:__PORT__/status"
deadline = time.time() + 900
last_error = None
while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        print("[d2] status ready")
        print(json.dumps(payload, indent=2))
        sys.exit(0)
    except Exception as exc:
        last_error = repr(exc)
        time.sleep(5)
print(f"[d2] server failed to become ready: {last_error}", file=sys.stderr)
sys.exit(1)
PY
}

stop_server() {
  if [ -f "\$RUN_DIR/chat_server.pid" ]; then
    SERVER_PID="\$(cat "\$RUN_DIR/chat_server.pid" || true)"
    if [ -n "\$SERVER_PID" ] && kill -0 "\$SERVER_PID" 2>/dev/null; then
      kill "\$SERVER_PID" 2>/dev/null || true
      wait "\$SERVER_PID" 2>/dev/null || true
    fi
  fi
}

trap 'stop_server' EXIT

start_server
wait_ready

echo "[d2] seeding prompts"
/home/user/venv_linux/bin/python -X utf8 step5d_chat_client.py \
  --base-url "http://127.0.0.1:\$PORT" \
  --output-log "\$RUN_DIR/opa_d2_seed_turns.jsonl" \
  --prompt-file d2_seed_prompts.txt \
  --phase-label d2_seed

echo "[d2] stopping server for sleep cycle"
stop_server

echo "[d2] running sleep cycle"
/home/user/venv_linux/bin/python -X utf8 run_sleep_cycle.py \
  --pending-path "\$RUN_DIR/qdrant_gate_pending.jsonl" \
  --mamba-state __BRIDGE_WSL__/mamba_bootstrap_state_latest.pt \
  --snapshot-dir "\$SNAPSHOT_DIR" \
  --snapshot-path "\$RUN_DIR/disposition_snapshot_latest.json" \
  --collection "\$COLLECTION" \
  --host 192.168.2.191

start_server
wait_ready

echo "[d2] running explicit recall eval"
/home/user/venv_linux/bin/python -X utf8 d2_private_recall_eval.py \
  --base-url "http://127.0.0.1:\$PORT" \
  --output-json "\$RUN_DIR/opa_d2_private_recall_eval.json"

echo "[d2] final status"
/home/user/venv_linux/bin/python - <<'PY'
import json
import urllib.request
with urllib.request.urlopen("http://127.0.0.1:__PORT__/status", timeout=10) as resp:
    payload = json.loads(resp.read().decode("utf-8"))
print(json.dumps(payload, indent=2))
PY

stop_server
trap - EXIT
'@

$remoteScript = $remoteScript.Replace("__BRIDGE_WSL__", $remoteBridgeWsl)
$remoteScript = $remoteScript.Replace("__INSTANCE__", $InstanceId)
$remoteScript = $remoteScript.Replace("__COLLECTION__", $remoteCollection)
$remoteScript = $remoteScript.Replace("__RUN_DIR__", $remoteRunWsl)
$remoteScript = $remoteScript.Replace("__SNAPSHOT_DIR__", $remoteSnapshotWsl)
$remoteScript = $remoteScript.Replace("__PORT__", "$Port")

Write-Host "Running end-to-end D2 cycle on Opa..." -ForegroundColor Cyan
& $runnerPath -User $User -Run $remoteScript

Write-Host "Copying D2 artifacts back..." -ForegroundColor Cyan
& scp -r "opa:$remoteRunWin" $localRunDir
if ($LASTEXITCODE -ne 0) {
    throw "D2 run finished on Opa but artifact copy-back failed."
}

Write-Host "D2 artifacts saved to $localRunDir" -ForegroundColor Green
