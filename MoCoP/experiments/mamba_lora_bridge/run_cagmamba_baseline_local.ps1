Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$wslWrapper = Join-Path $PSScriptRoot "local-wsl.ps1"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starting CAGMamba Gated Residual Fusion Baseline Training" -ForegroundColor Cyan
Write-Host "Alpha: 0.1 (MED recalibration)" -ForegroundColor Cyan
Write-Host "Diversity Constraint: 0.1" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$args = @(
    "--input-gated-residual",
    "--alpha", "0.1",
    "--diversity-loss-weight", "0.1",
    "--episodes-file", "CHEESE_SHAPING_EPISODES.md",
    "--output-name", "cagmamba_baseline_alpha0.1",
    "--epochs", "10",
    "--lr", "5e-4",
    "--log-every", "10"
)

& $wslWrapper -BridgePythonFile "train_cheese_bridge.py" -PythonArgs $args

Write-Host "Training command complete." -ForegroundColor Green