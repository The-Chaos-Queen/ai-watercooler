[CmdletBinding()]
param(
    [int]$MaxWaitMinutes = 180,
    [int]$PollSeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$launchScript = Join-Path $scriptDir "launch_mvp8_prompt_trace_episode_contrastive_steve_detached.ps1"
$logPath = Join-Path $scriptDir "mvp8_prompt_trace_episode_contrastive_watch.log"
$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)

function Write-Log {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $logPath -Append
}

Write-Log "Watcher started. Waiting for Steve SSH on 192.168.2.49:22."

while ((Get-Date) -lt $deadline) {
    try {
        Write-Log "Attempting detached mvp8 launch."
        & $launchScript *>&1 | Tee-Object -FilePath $logPath -Append
        Write-Log "Launch script finished."
        exit 0
    }
    catch {
        Write-Log ("Launch attempt failed: " + $_.Exception.Message)
        Write-Log "Steve still unreachable. Sleeping for $PollSeconds seconds."
        Start-Sleep -Seconds $PollSeconds
    }
}

Write-Log "Watcher timed out after $MaxWaitMinutes minutes without reaching Steve."
exit 1
