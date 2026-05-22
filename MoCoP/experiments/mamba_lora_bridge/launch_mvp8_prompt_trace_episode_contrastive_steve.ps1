[CmdletBinding()]
param(
    [switch]$SkipSync
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$trainFile = Join-Path $scriptDir "train_cheese_bridge.py"
$runFile = Join-Path $scriptDir "run_mvp8_prompt_trace_episode_contrastive_steve.sh"
$steveHelper = Join-Path $scriptDir "steve-wsl.ps1"

if (-not $SkipSync) {
    Write-Host "Syncing train_cheese_bridge.py to Steve..."
    scp -o BatchMode=yes -o ConnectTimeout=6 $trainFile "steve:C:/Users/tikii/bridge/"
    Write-Host "Sync complete."
} else {
    Write-Host "Skipping sync and using the current Steve copy of train_cheese_bridge.py."
}

Write-Host "Launching mvp8 prompt-trace contrastive training on Steve..."
powershell -ExecutionPolicy Bypass -File $steveHelper -RunFile $runFile
