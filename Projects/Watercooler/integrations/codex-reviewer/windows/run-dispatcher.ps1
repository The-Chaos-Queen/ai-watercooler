param(
    [Parameter(Mandatory = $true)]
    [string]$PolicyPath,
    [Parameter(Mandatory = $true)]
    [string]$ConfigPath,
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,
    [Parameter(Mandatory = $true)]
    [string]$SchemaPath,
    [Parameter(Mandatory = $true)]
    [string]$CodexAuthFile,
    [string]$PythonExe = "python",
    [string]$RuntimeDir = "",
    [int]$TimeoutSeconds = 3600,
    [int]$MaxAttempts = 2,
    [int]$RetryBaseSeconds = 300,
    [switch]$Prime,
    [switch]$Status,
    [switch]$CheckRuntime
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PolicyPath = [System.IO.Path]::GetFullPath($PolicyPath)
$ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$SchemaPath = [System.IO.Path]::GetFullPath($SchemaPath)
$CodexAuthFile = [System.IO.Path]::GetFullPath($CodexAuthFile)
foreach ($file in @($PolicyPath, $ConfigPath, $SchemaPath, $CodexAuthFile)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Required file not found: $file"
    }
}
if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) {
    throw "Repository root not found: $RepoRoot"
}

$arguments = @(
    "-X", "utf8", "-m", "watercooler.dispatcher.commit_review",
    "--config", $ConfigPath,
    "--policy", $PolicyPath,
    "--repo-root", $RepoRoot,
    "--schema", $SchemaPath,
    "--codex-auth-file", $CodexAuthFile,
    "--timeout-seconds", "$TimeoutSeconds",
    "--max-attempts", "$MaxAttempts",
    "--retry-base-seconds", "$RetryBaseSeconds"
)
if ($RuntimeDir) {
    $arguments += @("--runtime-dir", [System.IO.Path]::GetFullPath($RuntimeDir))
}
if ($Prime) { $arguments += "--prime" }
if ($Status) { $arguments += "--status" }
if ($CheckRuntime) { $arguments += "--check-runtime" }

$output = & $PythonExe @arguments 2>&1
$exitCode = $LASTEXITCODE
if ($output) { $output | Write-Output }
if ($exitCode -ne 0) {
    $failureRoot = if ($RuntimeDir) {
        [System.IO.Path]::GetFullPath($RuntimeDir)
    } else {
        Join-Path $env:LOCALAPPDATA "Watercooler\commit_review_dispatch\runner_logs"
    }
    New-Item -ItemType Directory -Force -Path $failureRoot | Out-Null
    $stamp = Get-Date -Format "yyyyMMddTHHmmss"
    $failureLog = Join-Path $failureRoot "runner_failure_$stamp.log"
    @(
        "timestamp=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz')",
        "exit_code=$exitCode",
        "",
        ($output -join [Environment]::NewLine)
    ) | Set-Content -LiteralPath $failureLog -Encoding UTF8
    throw "Watercooler commit-review dispatcher exited with code $exitCode; see $failureLog"
}
