[CmdletBinding()]
param(
    [string]$RemoteHost = "steve",
    [string]$RemoteBridgeDir = "C:/Users/tikii/bridge",
    [string]$RemoteMaskReport = "/mnt/c/Users/tikii/bridge/persistent_subnetwork_report.json",
    [string]$RemoteOutputDir = "/mnt/c/Users/tikii/bridge/step5e_mask_runs",
    [string[]]$MaskModes = @("persistent_zero", "variable_zero"),
    [int]$EpisodeIndex = 2,
    [int]$MaxNewTokens = 200,
    [double]$Temperature = 0.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))
$steveWsl = Join-Path $scriptDir "steve-wsl.ps1"
$runnerLocal = Join-Path $scriptDir "run_step5e_layer_sweep.py"
$maskReportLocal = Join-Path $scriptDir "persistent_subnetwork_results\persistent_subnetwork_report.json"

if (-not (Test-Path -LiteralPath $runnerLocal)) {
    throw "Missing local runner: $runnerLocal"
}
if (-not (Test-Path -LiteralPath $maskReportLocal)) {
    throw "Missing local mask report: $maskReportLocal"
}
if (-not (Test-Path -LiteralPath $steveWsl)) {
    throw "Missing Steve WSL helper: $steveWsl"
}

Write-Host "`n=== Step 5e Mask Ablation on Steve ===" -ForegroundColor Cyan
Write-Host "Remote host: $RemoteHost"
Write-Host "Remote bridge dir: $RemoteBridgeDir"
Write-Host "Mask modes: $($MaskModes -join ', ')"
Write-Host "Episode index: $EpisodeIndex"
Write-Host "Output dir: $RemoteOutputDir"

Write-Host "`nSyncing patched runner and mask report to Steve..." -ForegroundColor Yellow
& scp $runnerLocal "${RemoteHost}:${RemoteBridgeDir}/run_step5e_layer_sweep.py"
if ($LASTEXITCODE -ne 0) { throw "scp failed for run_step5e_layer_sweep.py" }
& scp $maskReportLocal "${RemoteHost}:${RemoteBridgeDir}/persistent_subnetwork_report.json"
if ($LASTEXITCODE -ne 0) { throw "scp failed for persistent_subnetwork_report.json" }

$pythonArgs = @(
    "--append-mask-ablation",
    "--experiments", "5e.mask",
    "--episode-index", "$EpisodeIndex",
    "--temperature", "$Temperature",
    "--max-new-tokens", "$MaxNewTokens",
    "--mask-report", "$RemoteMaskReport",
    "--output-dir", "$RemoteOutputDir"
)
$pythonArgs += "--mask-modes"
$pythonArgs += $MaskModes

Write-Host "`nLaunching Steve WSL runner..." -ForegroundColor Yellow
& $steveWsl -RemoteHost $RemoteHost -BridgePythonFile "run_step5e_layer_sweep.py" -PythonArgs $pythonArgs
if ($LASTEXITCODE -ne 0) { throw "Steve mask ablation run failed." }

Write-Host "`nMask ablation run completed." -ForegroundColor Green
Write-Host "Results should be under: $RemoteOutputDir"
