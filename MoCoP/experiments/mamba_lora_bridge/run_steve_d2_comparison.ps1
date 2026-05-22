<#
    Run D2 eval with BOTH factual and full styles for direct comparison.
    Usage: .\run_steve_d2_comparison.ps1

    This runs two sequential Steve evaluations:
    1. factual (new default)
    2. full (old default, baseline comparison)

    Both use the same pipeline: birth -> seed -> sleep -> eval -> copy-back.
    Compare answer_accuracy and explicit_memory_language_rate between runs.
#>

param(
    [int]$Port = 7863,
    [double]$Alpha = 0.2,
    [double]$Temperature = 0.0,
    [string]$QwenModelId = "Qwen/Qwen2.5-1.5B"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ts = Get-Date -Format "yyyyMMddTHHmmss"
$bridgeDir = Join-Path "C:\Users\cerub\OneDrive\Dokumente\LLM" "MoCoP\experiments\mamba_lora_bridge"
$runScript = Join-Path $bridgeDir "run_steve_d2_private_recall.ps1"

Write-Host "`n=== RUN 1: factual mode ===" -ForegroundColor Green
& $runScript -InstanceId "steve_d2_factual_$ts" -ExplicitRecallStyle "factual" -Alpha $Alpha -Temperature $Temperature -QwenModelId $QwenModelId -Port $Port

Write-Host "`n=== RUN 2: full mode (baseline) ===" -ForegroundColor Yellow
& $runScript -InstanceId "steve_d2_full_$ts" -ExplicitRecallStyle "full" -Alpha $Alpha -Temperature $Temperature -QwenModelId $QwenModelId -Port $Port

Write-Host "`n=== COMPARISON ===" -ForegroundColor Cyan
$artifactRoot = Join-Path $bridgeDir "run_reincarnation"
$factualResult = Join-Path $artifactRoot "steve_d2_factual_$ts" "steve_d2_private_recall_eval.json"
$fullResult = Join-Path $artifactRoot "steve_d2_full_$ts" "steve_d2_private_recall_eval.json"

if ((Test-Path $factualResult) -and (Test-Path $fullResult)) {
    Write-Host "`nFactual:" -ForegroundColor Green
    python -c "import json; d=json.load(open(r'$factualResult')); print(f'  answer_accuracy: {d[\"answer_accuracy\"]}'); print(f'  memory_language: {d[\"explicit_memory_language_rate\"]}')"
    Write-Host "`nFull (baseline):" -ForegroundColor Yellow
    python -c "import json; d=json.load(open(r'$fullResult')); print(f'  answer_accuracy: {d[\"answer_accuracy\"]}'); print(f'  memory_language: {d[\"explicit_memory_language_rate\"]}')"
} else {
    Write-Host "One or both result files not found. Check run_reincarnation/ manually." -ForegroundColor Red
}
