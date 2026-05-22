[CmdletBinding()]
param(
    [string]$User = "User",
    [string]$InstanceId = "baby_d2_live_20260327T1331",
    [int]$Port = 7863,
    [double]$Alpha = 0.2,
    [double]$Temperature = 0.7,
    [string]$QwenModelId = "Qwen/Qwen2.5-1.5B",
    [string]$QdrantWriteMode = "critical-only",
    [int]$EpisodeIndex = 2,
    [switch]$BlindDispositionUi,
    [switch]$NoSync,
    [int]$ReadyTimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = "C:\Users\cerub\OneDrive\Dokumente\LLM"
$bridgeDir = Join-Path $repoRoot "MoCoP\experiments\mamba_lora_bridge"
$runnerPath = Join-Path $bridgeDir "opa-wsl.ps1"
$remoteBridgeWin = "C:/Users/User/bridge"
$remoteBridgeWsl = "/mnt/c/Users/User/bridge"
$runDir = "$remoteBridgeWsl/live_runs/$InstanceId"
$collection = "mocop_private_$InstanceId"
$tempRunFile = Join-Path $env:TEMP ("opa-live-chat-{0}.sh" -f $InstanceId)
$blindDispositionSwitch = if ($BlindDispositionUi) { " \`n  --blind-disposition-ui" } else { "" }
$statusUrl = "http://192.168.2.194:$Port/status"

function Get-ServerStatus {
    param([string]$Url)

    try {
        return Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 5
    } catch {
        return $null
    }
}

if (-not $NoSync) {
    & scp `
        (Join-Path $bridgeDir "autobiographical_memory.py") `
        (Join-Path $bridgeDir "chat_server.py") `
        "opa:$remoteBridgeWin/"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to sync chat_server.py/autobiographical_memory.py to Opa."
    }
}

$remoteScript = @"
set -euo pipefail
cd $remoteBridgeWsl
mkdir -p '$runDir'
pkill -f 'chat_server.py.*--port $Port' 2>/dev/null || true
sleep 2
exec /home/user/venv_linux/bin/python -X utf8 chat_server.py \
  --qwen-model-id $QwenModelId \
  --alpha $Alpha \
  --temperature $Temperature \
  --episode-index $EpisodeIndex \
  --host 0.0.0.0 \
  --port $Port \
  --instance-id $InstanceId \
  --no-shared-memory \
  --qdrant-collection $collection \
  --qdrant-write-mode $QdrantWriteMode \
  --transcript-path '$runDir/chat_session_latest.txt' \
  --turn-log-path '$runDir/chat_turns_latest.jsonl' \
  --dual-gate-log-path '$runDir/dual_gate_turns_latest.jsonl' \
  --dual-gate-memory-path '$runDir/salience_memory_latest.jsonl' \
  --dual-gate-sleep-path '$runDir/sleep_gate_events_latest.jsonl' \
  --dual-gate-surprise-path '$runDir/surprise_events_latest.jsonl' \
  --qdrant-pending-path '$runDir/qdrant_gate_pending.jsonl' \
  --qdrant-flushed-path '$runDir/qdrant_gate_pending.flushed.jsonl' \
  --memory-formation-log-path '$runDir/memory_formation_log.jsonl' \
  --recall-log-path '$runDir/private_recall_log.jsonl' \
  --failure-log-path '$runDir/failure_log.jsonl'$blindDispositionSwitch
"@

Set-Content -LiteralPath $tempRunFile -Value $remoteScript -Encoding UTF8

$previousStatus = Get-ServerStatus -Url $statusUrl
$previousStartedAt = ""
if ($null -ne $previousStatus -and $null -ne $previousStatus.started_at) {
    $previousStartedAt = [string]$previousStatus.started_at
}

$argList = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", $runnerPath,
    "-User", $User,
    "-RunFile", $tempRunFile
)

Start-Process -FilePath "powershell.exe" -ArgumentList $argList -WindowStyle Hidden | Out-Null

$deadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
$ready = $false
$startedAt = ""
do {
    Start-Sleep -Seconds 2
    $status = Get-ServerStatus -Url $statusUrl
    if ($null -eq $status) {
        continue
    }

    $instanceMatches = ([string]$status.instance_id -eq $InstanceId)
    $running = [bool]$status.running
    $startedAt = if ($null -ne $status.started_at) { [string]$status.started_at } else { "" }
    $newBootSeen = $false

    if ($previousStartedAt) {
        $newBootSeen = ($startedAt -ne "") -and ($startedAt -ne $previousStartedAt)
    } else {
        $uptime = 999999.0
        if ($null -ne $status.uptime_s -and "$($status.uptime_s)" -ne "") {
            try {
                $uptime = [double]$status.uptime_s
            } catch {
                $uptime = 999999.0
            }
        }
        $newBootSeen = ($uptime -lt 15.0)
    }

    if ($running -and $instanceMatches -and $newBootSeen) {
        $ready = $true
        break
    }
} while ((Get-Date) -lt $deadline)

if (-not $ready) {
    throw "Opa live chat server did not reach a fresh ready state on port $Port within $ReadyTimeoutSeconds seconds."
}

Write-Host "Started Opa live chat server for $InstanceId on port $Port (alpha=$Alpha temp=$Temperature model=$QwenModelId started_at=$startedAt)" -ForegroundColor Green
