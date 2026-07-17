param(
    [string]$PolicyPath = "",
    [int]$TimeoutSeconds = 3600,
    [int]$MaxAttempts = 2,
    [int]$RetryBaseSeconds = 300,
    [switch]$Prime,
    [switch]$Status,
    [switch]$CheckRuntime
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$toolDir = Join-Path $repoRoot "tools\ai_watercooler"
$dispatcher = Join-Path $toolDir "codex_watercooler_dispatch.py"
if (-not $PolicyPath) {
    $PolicyPath = Join-Path $toolDir "codex_watercooler_dispatch_policy.json"
}
$PolicyPath = [System.IO.Path]::GetFullPath($PolicyPath)
$sessionsDir = Join-Path $env:LOCALAPPDATA "AIWatercooler\sessions"

if (-not (Test-Path -LiteralPath $dispatcher -PathType Leaf)) {
    throw "Missing dispatcher: $dispatcher"
}
if (-not (Test-Path -LiteralPath $PolicyPath -PathType Leaf)) {
    throw "Missing dispatcher policy: $PolicyPath"
}

$policy = Get-Content -LiteralPath $PolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($policy.version -ne 1 -or -not "$($policy.principal)".Trim()) {
    throw "Malformed or unsupported dispatcher policy: $PolicyPath"
}
if ($policy.transport_security -ne "trusted_lan_plaintext_residual") {
    throw "Dispatcher policy does not explicitly accept the pinned HTTP LAN residual."
}
if ($policy.worker_backend -ne "wsl_docker" -or -not "$($policy.wsl_distribution)".Trim()) {
    throw "Dispatcher policy does not name the required WSL Docker isolation backend."
}
if ("$($policy.docker_image_id)" -notmatch '^sha256:[0-9a-f]{64}$') {
    throw "Dispatcher policy does not pin an exact Docker image ID."
}
$principal = "$($policy.principal)"
$expectedBaseUrl = "$($policy.expected_base_url)".TrimEnd('/')
$requiredScopes = @("messages:read", "messages:write")
$logsDir = Join-Path $env:LOCALAPPDATA "AIWatercooler\codex_dispatch\$principal\runner_logs"
$codexAuthFile = Join-Path $env:USERPROFILE ".codex\auth.json"
if (-not (Test-Path -LiteralPath $codexAuthFile -PathType Leaf)) {
    throw "Codex auth file not found: $codexAuthFile"
}

function Get-LatestValidSessionConfig {
    if (-not (Test-Path -LiteralPath $sessionsDir -PathType Container)) {
        throw "Session directory not found: $sessionsDir"
    }

    $nowUtc = [DateTime]::UtcNow
    $candidates = Get-ChildItem -LiteralPath $sessionsDir -Filter "$principal-*.json" |
        Sort-Object LastWriteTime -Descending

    foreach ($candidate in $candidates) {
        try {
            $config = Get-Content -LiteralPath $candidate.FullName -Raw -Encoding UTF8 |
                ConvertFrom-Json
            $wirePrincipal = "$($config.principal)".Trim()
            $wireDefault = "$($config.default_from)".Trim()
            $wireUrl = "$($config.base_url)".TrimEnd('/')
            $scopes = @($config.scopes | ForEach-Object { "$_" })
            $scopeSetIsExact = (
                $scopes.Count -eq 2 -and
                $scopes -contains $requiredScopes[0] -and
                $scopes -contains $requiredScopes[1]
            )
            if (
                $wirePrincipal -ne $principal -or
                $wireDefault -ne $principal -or
                $wireUrl -ne $expectedBaseUrl -or
                -not $scopeSetIsExact -or
                -not "$($config.token)".Trim()
            ) {
                continue
            }
            if (-not "$($config.expires_ts)".Trim()) {
                continue
            }
            $expiresUtc = [DateTime]::Parse("$($config.expires_ts)").ToUniversalTime()
            if ($expiresUtc -gt $nowUtc) {
                return $candidate.FullName
            }
        } catch {
            continue
        }
    }

    throw "No unexpired least-privilege session config found for '$principal' in $sessionsDir"
}

$configPath = Get-LatestValidSessionConfig
$arguments = @(
    "-X", "utf8", $dispatcher,
    "--config", $configPath,
    "--policy", $PolicyPath,
    "--repo-root", $repoRoot,
    "--codex-auth-file", $codexAuthFile,
    "--timeout-seconds", "$TimeoutSeconds",
    "--max-attempts", "$MaxAttempts",
    "--retry-base-seconds", "$RetryBaseSeconds"
)
if ($Prime) {
    $arguments += "--prime"
}
if ($Status) {
    $arguments += "--status"
}
if ($CheckRuntime) {
    $arguments += "--check-runtime"
}

$output = & python @arguments 2>&1
$exitCode = $LASTEXITCODE
if ($output) {
    $output | Write-Output
}
if ($exitCode -ne 0) {
    New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
    $stamp = Get-Date -Format "yyyyMMddTHHmmss"
    $failureLog = Join-Path $logsDir "runner_failure_$stamp.log"
    @(
        "timestamp=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz')",
        "exit_code=$exitCode",
        "config=$configPath",
        "policy=$PolicyPath",
        "",
        ($output -join [Environment]::NewLine)
    ) | Set-Content -LiteralPath $failureLog -Encoding UTF8
    throw "Codex Watercooler dispatcher exited with code $exitCode; see $failureLog"
}
