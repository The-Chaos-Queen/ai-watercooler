$ErrorActionPreference = "Stop"

$taskName = "MoCoP Steve Chat"
$wslExe = "C:\Windows\System32\wsl.exe"

function Get-ChatServerPids {
    try {
        $raw = & $wslExe -u root bash -lc "ss -ltnp '( sport = :7860 )' 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u" 2>$null
        $lines = @($raw) | ForEach-Object { "$_".Trim() } | Where-Object { $_ -match '^\d+$' }
    } catch {
        $lines = @()
    }
    return $lines
}

function Wait-ForChatServerStop {
    param([int]$TimeoutSec = 20)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $taskRunning = $false
        try {
            $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            if ($null -ne $task) {
                $taskRunning = ($task.State -eq "Running")
            }
        } catch {
        }

        $chatRunning = (Get-ChatServerPids).Count -gt 0
        if (-not $taskRunning -and -not $chatRunning) {
            return $true
        }

        Start-Sleep -Seconds 1
    }

    return $false
}

function Send-ChatSignal([string]$SignalName) {
    $pids = Get-ChatServerPids
    if ($pids.Count -eq 0) {
        return
    }

    $pidList = ($pids -join " ")
    try {
        & $wslExe -u root bash -lc "kill -$SignalName $pidList >/dev/null 2>&1 || true" | Out-Null
    } catch {
        Write-Warning "Could not send SIG$($SignalName) to Steve chat listener PID(s) $($pidList): $($_.Exception.Message)"
    }
}

try {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Out-Null
} catch {
}

Send-ChatSignal -SignalName "INT"
if (Wait-ForChatServerStop -TimeoutSec 25) {
    Write-Host "Stopped $taskName cleanly."
    return
}

Send-ChatSignal -SignalName "TERM"
if (Wait-ForChatServerStop -TimeoutSec 20) {
    Write-Host "Stopped $taskName after SIGTERM."
    return
}

Send-ChatSignal -SignalName "KILL"
if (Wait-ForChatServerStop -TimeoutSec 20) {
    Write-Host "Stopped $taskName after SIGKILL."
    return
}

$remainingPids = Get-ChatServerPids
throw "Failed to stop $taskName cleanly. Remaining listener PID(s) on 7860: $($remainingPids -join ', ')"
