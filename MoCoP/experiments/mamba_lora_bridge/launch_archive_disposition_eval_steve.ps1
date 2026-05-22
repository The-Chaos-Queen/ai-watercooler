[CmdletBinding()]
param(
    [string]$RemoteHost = "steve"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$steveHelper = Join-Path $scriptDir "steve-wsl.ps1"
$runFile = Join-Path $scriptDir "run_archive_disposition_eval_steve.sh"

$syncFiles = @(
    "ARCHIVE_DISPOSITION_SHAPING_EPISODES_2026-04-11.md",
    "relational_rivalry_eval_panel_v2_2026-04-11.json",
    "run_relational_eval_offline.py",
    "reincarnated_inference.py",
    "models.py"
)

foreach ($name in $syncFiles) {
    $localPath = Join-Path $scriptDir $name
    if (-not (Test-Path -LiteralPath $localPath)) {
        throw "Missing local file: $localPath"
    }
    & scp -o BatchMode=yes -o ConnectTimeout=8 $localPath "${RemoteHost}:C:/Users/tikii/bridge/"
    if ($LASTEXITCODE -ne 0) {
        throw "scp failed for $localPath"
    }
}

if (-not (Test-Path -LiteralPath $steveHelper)) {
    throw "Missing Steve WSL helper: $steveHelper"
}

if (-not (Test-Path -LiteralPath $runFile)) {
    throw "Missing run file: $runFile"
}

& powershell -ExecutionPolicy Bypass -File $steveHelper -RemoteHost $RemoteHost -RunFile $runFile
