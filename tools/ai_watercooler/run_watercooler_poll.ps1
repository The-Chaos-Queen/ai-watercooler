param(
    [string]$Principal = "laura",
    [string]$Thread = "mamba-bridge",
    [switch]$AllThreads
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$pollScript = Join-Path $repoRoot "tools\ai_watercooler\watercooler_poll.py"
$sessionsDir = Join-Path $env:LOCALAPPDATA "AIWatercooler\sessions"
$logsDir = Join-Path $env:LOCALAPPDATA "AIWatercooler\logs"
$principalSlug = ($Principal -replace '[^A-Za-z0-9._-]', '_')
$logPath = Join-Path $logsDir "watercooler_poll_${principalSlug}.log"
$latestPath = Join-Path $logsDir "watercooler_poll_${principalSlug}_latest.txt"

function Get-LatestValidSessionConfig {
    param([string]$AgentPrincipal)

    if (-not (Test-Path $sessionsDir)) {
        throw "Session directory not found: $sessionsDir"
    }

    $nowUtc = [DateTime]::UtcNow
    $candidates = Get-ChildItem -Path $sessionsDir -Filter "$AgentPrincipal-*.json" |
        Sort-Object LastWriteTime -Descending

    foreach ($candidate in $candidates) {
        try {
            $config = Get-Content -Path $candidate.FullName -Raw | ConvertFrom-Json
            if ($null -eq $config.expires_ts -or -not "$($config.expires_ts)".Trim()) {
                return $candidate.FullName
            }

            $expiresUtc = [DateTime]::Parse("$($config.expires_ts)").ToUniversalTime()
            if ($expiresUtc -gt $nowUtc) {
                return $candidate.FullName
            }
        } catch {
        }
    }

    throw "No valid session config found for principal '$AgentPrincipal' in $sessionsDir"
}

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
$configPath = Get-LatestValidSessionConfig -AgentPrincipal $Principal
$args = @("-X", "utf8", $pollScript, "--config", $configPath)
if ($AllThreads) {
    $args += "--all-threads"
} else {
    $args += @("--thread", $Thread)
}

$output = & python @args 2>&1
$exitCode = $LASTEXITCODE
$text = (($output | ForEach-Object { "$_" }) -join [Environment]::NewLine).Trim()

if (-not $text) {
    $text = "(no output)"
}

$block = @(
    "[$timestamp] principal=$Principal thread=$(if ($AllThreads) { 'all' } else { $Thread }) exit=$exitCode",
    $text,
    ""
) -join [Environment]::NewLine

Add-Content -Path $logPath -Value $block -Encoding UTF8
Set-Content -Path $latestPath -Value $block -Encoding UTF8

if ($exitCode -ne 0) {
    throw "watercooler_poll.py exited with code $exitCode"
}
