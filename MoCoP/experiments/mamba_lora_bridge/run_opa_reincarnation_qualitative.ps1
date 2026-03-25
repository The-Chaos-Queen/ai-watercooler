param(
    [string]$User = "user",
    [int]$MaxNewTokens = 140,
    [switch]$NoSync
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\cerub\OneDrive\Dokumente\LLM"
$bridgeDir = Join-Path $repoRoot "MoCoP\experiments\mamba_lora_bridge"
$runnerPath = Join-Path $bridgeDir "opa-wsl.ps1"
$outputDir = Join-Path $bridgeDir "run_reincarnation"
$timestamp = Get-Date -Format "yyyyMMdd"

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$syncFiles = @(
    (Join-Path $bridgeDir "models.py"),
    (Join-Path $bridgeDir "mamba_runtime_compat.py"),
    (Join-Path $bridgeDir "CHEESE_SHAPING_EPISODES.md"),
    (Join-Path $bridgeDir "cheese_reincarnation_bridge_1.5b_codexfix.pt")
)

if (-not $NoSync) {
    # Explicitly sync the corrected inference script
    & scp (Join-Path $bridgeDir "reincarnated_inference.py") "opa:C:/Users/User/bridge/"
    & scp @syncFiles "opa:C:/Users/User/bridge/"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to sync reincarnation files to Opa."
    }
}

$runs = @(
    @{ Tag = "t07"; Temperature = "0.7" },
    @{ Tag = "t03"; Temperature = "0.3" }
)

foreach ($run in $runs) {
    $remoteResults = "opa_reincarnation_$($run.Tag)_${MaxNewTokens}tok_${timestamp}.txt"
    $localResults = Join-Path $outputDir $remoteResults

    Write-Host "Running Opa reincarnation qualitative pass: temp=$($run.Temperature), max_new_tokens=$MaxNewTokens" -ForegroundColor Cyan

    $script = @"
cd /mnt/c/Users/User/bridge
/home/user/venv_linux/bin/python -X utf8 reincarnated_inference.py --bridge-path cheese_reincarnation_bridge_1.5b_codexfix.pt --results-file $remoteResults --max-new-tokens $MaxNewTokens --temperature $($run.Temperature) --qwen-device cuda:0 --bridge-device cuda:0 --mamba-device cpu
"@

    powershell -NoProfile -ExecutionPolicy Bypass -File $runnerPath -User $User -Run $script

    & scp "opa:C:/Users/User/bridge/$remoteResults" $localResults
    if ($LASTEXITCODE -ne 0) {
        throw "Run completed on Opa but failed to copy back $remoteResults."
    }

    Write-Host "Saved $localResults" -ForegroundColor Green
}

Write-Host "Opa qualitative replication complete." -ForegroundColor Green
