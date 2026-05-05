# swarm_status.ps1 — Quick overview of all active Claude Code sessions
# Usage: powershell -File tools/swarm_status.ps1
# Shows: running sessions, last watercooler message per agent, context hints

param(
    [int]$WatercoolerLimit = 20,
    [string]$Thread = "mamba-bridge"
)

$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host ""
Write-Host "  ==============================" -ForegroundColor DarkYellow
Write-Host "     SWARM STATUS" -ForegroundColor Yellow
Write-Host "  ==============================" -ForegroundColor DarkYellow
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -ForegroundColor DarkGray
Write-Host ""

# -- 1. Running Claude Code processes --
Write-Host "  ACTIVE SESSIONS" -ForegroundColor Cyan
Write-Host "  -----------------------------" -ForegroundColor DarkGray

$claudeProcesses = Get-Process -Name "claude*" -ErrorAction SilentlyContinue
if ($claudeProcesses) {
    $claudeProcesses | ForEach-Object {
        $pid = $_.Id
        $mem = [math]::Round($_.WorkingSet64 / 1MB, 0)
        $cpu = [math]::Round($_.CPU, 1)
        $line = "    PID $pid | $($mem)MB RAM | $($cpu)s CPU | $($_.ProcessName)"
        Write-Host $line -ForegroundColor White
    }
} else {
    Write-Host "    (no Claude processes found)" -ForegroundColor DarkGray
}
Write-Host ""

# -- 2. Session token files (who has credentials) --
Write-Host "  REGISTERED AGENTS" -ForegroundColor Cyan
Write-Host "  -----------------------------" -ForegroundColor DarkGray

$sessionsDir = Join-Path $env:LOCALAPPDATA "AIWatercooler\sessions"
if (Test-Path $sessionsDir) {
    Get-ChildItem "$sessionsDir\*.json" | ForEach-Object {
        $config = Get-Content $_.FullName -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($config) {
            $principal = $config.principal
            $expires = $config.expires_ts
            $expired = $false
            if ($expires) {
                try {
                    $expiresDate = [DateTime]::Parse($expires)
                    $expired = $expiresDate -lt (Get-Date)
                } catch {}
            }
            $status = if ($expired) { "EXPIRED" } else { "active" }
            $color = if ($expired) { "DarkRed" } else { "Green" }
            Write-Host "    $($principal.PadRight(20)) [$status]" -ForegroundColor $color
        }
    }
} else {
    Write-Host "    (no session directory found)" -ForegroundColor DarkGray
}
Write-Host ""

# -- 3. Last watercooler message per agent --
Write-Host "  LAST WATERCOOLER ACTIVITY ($Thread)" -ForegroundColor Cyan
Write-Host "  -----------------------------" -ForegroundColor DarkGray

# Use the admin config to read (or any available config)
$adminConfig = Join-Path $env:LOCALAPPDATA "AIWatercooler\config.json"
$readConfig = $null

# Try admin config first, then any session config
if (Test-Path $adminConfig) {
    $readConfig = $adminConfig
} else {
    $firstSession = Get-ChildItem "$sessionsDir\*.json" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($firstSession) { $readConfig = $firstSession.FullName }
}

if ($readConfig) {
    $env:AI_WATERCOOLER_CONFIG = $readConfig

    # Get recent messages and extract last per agent
    $raw = & python "$RepoRoot\tools\ai_watercooler\watercooler_read.py" --thread $Thread --limit $WatercoolerLimit 2>$null
    if ($raw) {
        $agentLastMsg = @{}
        $raw -split "`n" | ForEach-Object {
            if ($_ -match '^\[(\d+)\] (\S+) (\S+) -> (\S+).*topic=(.*)') {
                $msgId = $Matches[1]
                $ts = $Matches[2]
                $from = $Matches[3]
                $topic = $Matches[5] -replace ' tags=.*', ''
                if (-not $agentLastMsg.ContainsKey($from)) {
                    $agentLastMsg[$from] = @{ id = $msgId; ts = $ts; topic = $topic.Trim() }
                }
            } elseif ($_ -match '^\[(\d+)\] (\S+) (\S+) -> (\S+)') {
                $msgId = $Matches[1]
                $ts = $Matches[2]
                $from = $Matches[3]
                if (-not $agentLastMsg.ContainsKey($from)) {
                    $agentLastMsg[$from] = @{ id = $msgId; ts = $ts; topic = "" }
                }
            }
        }

        $agentLastMsg.GetEnumerator() | Sort-Object { $_.Value.id } -Descending | ForEach-Object {
            $agent = $_.Key.PadRight(18)
            $id = "#$($_.Value.id)".PadRight(5)
            $ts = $_.Value.ts.Substring(11, 5)  # HH:MM
            $topic = if ($_.Value.topic) { " | $($_.Value.topic)" } else { "" }
            Write-Host "    $agent $id $ts$topic" -ForegroundColor White
        }
    } else {
        Write-Host "    (could not read watercooler)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "    (no watercooler config found)" -ForegroundColor DarkGray
}
Write-Host ""

# -- 4. Quick handoff summary --
Write-Host "  HANDOFF SNAPSHOT" -ForegroundColor Cyan
Write-Host "  -----------------------------" -ForegroundColor DarkGray

$handoff = Join-Path $RepoRoot "CHEESE_Memory\00_HANDOFF.md"
if (Test-Path $handoff) {
    $lines = Get-Content $handoff -TotalCount 40
    $lines | ForEach-Object {
        if ($_ -match '^- Last updated:') { Write-Host "    $_" -ForegroundColor White }
        if ($_ -match '^- Primary focus:') { Write-Host "    $_" -ForegroundColor Yellow }
        if ($_ -match '^- Last session log:') { Write-Host "    $_" -ForegroundColor White }
    }
}
Write-Host ""

# -- 5. Recent session logs --
Write-Host "  RECENT SESSION LOGS" -ForegroundColor Cyan
Write-Host "  -----------------------------" -ForegroundColor DarkGray

$logsDir = Join-Path $RepoRoot "CHEESE_Memory\session_logs"
if (Test-Path $logsDir) {
    Get-ChildItem "$logsDir\*.md" | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object {
        $firstLine = Get-Content $_.FullName -TotalCount 10 | Where-Object { $_ -match '^agent:' } | Select-Object -First 1
        $agent = if ($firstLine) { ($firstLine -replace '^agent:\s*', '').Trim() } else { "?" }
        $name = $_.Name.PadRight(35)
        Write-Host "    $name $agent" -ForegroundColor White
    }
}
Write-Host ""
Write-Host "  ==============================" -ForegroundColor DarkYellow
Write-Host ""
