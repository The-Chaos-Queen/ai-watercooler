[CmdletBinding()]
param(
    [string]$User = "root",
    [Parameter(Mandatory = $true)]
    [string]$RemoteHost,
    [int]$Port = 22,
    [Parameter(Mandatory = $true)]
    [string]$RunDir,
    [Parameter(Mandatory = $true)]
    [string]$LogFile,
    [ValidateRange(5, 3600)]
    [int]$PollSeconds = 30,
    [ValidateRange(0, 1000000)]
    [int]$MaxPolls = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Escape-BashSingleQuoted {
    param([Parameter(Mandatory = $true)][string]$Value)
    $replacement = ("'", '"', "'", '"', "'") -join ""
    return ($Value -replace "'", $replacement)
}

function Invoke-RemoteSnapshot {
    $safeRunDir = Escape-BashSingleQuoted -Value $RunDir
    $safeLogFile = Escape-BashSingleQuoted -Value $LogFile

    $scriptBody = @'
set -euo pipefail
RUN_DIR='__RUN_DIR__'
LOG_FILE='__LOG_FILE__'
CHECKPOINT_FILE="$RUN_DIR/bridge_epoch_001.pt"
BEST_FILE="$RUN_DIR/bridge_best.pt"

PROCESS_LINE=""
if [ -d "$RUN_DIR" ]; then
  PROCESS_LINE="$(ps -eo pid,etimes,cmd | grep 'train_bridge.py' | grep -v grep | grep -F -- "$RUN_DIR" | head -n 1 || true)"
fi

LOG_EXISTS=0
LAST_STEP=""
LAST_EVENT=""
FAIL_MATCH=""
if [ -f "$LOG_FILE" ]; then
  LOG_EXISTS=1
  LAST_STEP="$(tail -n 200 "$LOG_FILE" | grep -E 'train epoch=.*step=' | tail -n 1 || true)"
  LAST_EVENT="$(tail -n 200 "$LOG_FILE" | grep -E 'eval epoch=|Saved checkpoint:|Saved resumable checkpoint:|Training finished:' | tail -n 1 || true)"
  FAIL_MATCH="$(tail -n 200 "$LOG_FILE" | grep -E 'Traceback|RuntimeError|CUDA out of memory|Preflight failed|Directory write check failed|Model access check failed|accelerate import failed|bitsandbytes import failed|Transformers import failed|PyTorch import failed' | tail -n 1 || true)"
fi

CHECKPOINT_EXISTS=0
if [ -f "$CHECKPOINT_FILE" ]; then
  CHECKPOINT_EXISTS=1
fi

BEST_EXISTS=0
if [ -f "$BEST_FILE" ]; then
  BEST_EXISTS=1
fi

RESULT="running"
if [ -n "$FAIL_MATCH" ]; then
  RESULT="failure"
elif [ "$CHECKPOINT_EXISTS" = "1" ] && [ -z "$PROCESS_LINE" ]; then
  RESULT="success"
elif [ "$LOG_EXISTS" = "0" ] && [ -z "$PROCESS_LINE" ]; then
  RESULT="idle"
fi

printf 'RESULT=%s\n' "$RESULT"
printf 'PROCESS_LINE=%s\n' "$PROCESS_LINE"
printf 'LOG_EXISTS=%s\n' "$LOG_EXISTS"
printf 'CHECKPOINT_EXISTS=%s\n' "$CHECKPOINT_EXISTS"
printf 'BEST_EXISTS=%s\n' "$BEST_EXISTS"
printf 'LAST_STEP=%s\n' "$LAST_STEP"
printf 'LAST_EVENT=%s\n' "$LAST_EVENT"
printf 'FAIL_MATCH=%s\n' "$FAIL_MATCH"
'@
    $scriptBody = $scriptBody.Replace("__RUN_DIR__", $safeRunDir).Replace("__LOG_FILE__", $safeLogFile)

    $target = "$User@$RemoteHost"
    $sshArgs = @("-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new")
    if ($Port -ne 22) {
        $sshArgs += @("-p", "$Port")
    }
    $sshArgs += @($target, "bash", "-se")

    $raw = $scriptBody | & ssh @sshArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Remote watcher command failed with exit code $LASTEXITCODE."
    }

    $snapshot = @{}
    foreach ($line in $raw) {
        if ($line -notmatch "=") {
            continue
        }
        $parts = $line -split "=", 2
        $snapshot[$parts[0]] = $parts[1]
    }
    return $snapshot
}

function Write-Status {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Snapshot,
        [Parameter(Mandatory = $true)]
        [int]$PollNumber
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $result = $Snapshot["RESULT"]
    $checkpoint = if ($Snapshot["CHECKPOINT_EXISTS"] -eq "1") { "yes" } else { "no" }
    $best = if ($Snapshot["BEST_EXISTS"] -eq "1") { "yes" } else { "no" }

    Write-Host "[$timestamp] poll=$PollNumber result=$result checkpoint=$checkpoint best=$best"
    if ($Snapshot["PROCESS_LINE"]) {
        Write-Host "  process: $($Snapshot["PROCESS_LINE"])"
    }
    if ($Snapshot["LAST_STEP"]) {
        Write-Host "  step: $($Snapshot["LAST_STEP"])"
    }
    if ($Snapshot["LAST_EVENT"]) {
        Write-Host "  event: $($Snapshot["LAST_EVENT"])"
    }
    if ($Snapshot["FAIL_MATCH"]) {
        Write-Host "  failure: $($Snapshot["FAIL_MATCH"])" -ForegroundColor Red
    }
}

$pollNumber = 0
while ($true) {
    $pollNumber += 1
    $snapshot = Invoke-RemoteSnapshot
    Write-Status -Snapshot $snapshot -PollNumber $pollNumber

    switch ($snapshot["RESULT"]) {
        "success" {
            Write-Host ""
            Write-Host "Stage 1 appears complete. Copy off artifacts before terminating the instance."
            Write-Host "  scp -P $Port ${User}@${RemoteHost}:$LogFile <local-destination>"
            Write-Host "  scp -P $Port -r ${User}@${RemoteHost}:$RunDir <local-destination>"
            break
        }
        "failure" {
            Write-Host ""
            Write-Host "Failure markers detected. Inspect the remote log before stopping the instance." -ForegroundColor Red
            exit 2
        }
    }

    if (($MaxPolls -gt 0) -and ($pollNumber -ge $MaxPolls)) {
        break
    }

    Start-Sleep -Seconds $PollSeconds
}
