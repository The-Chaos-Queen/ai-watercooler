param(
    [string]$TaskName = "AI Watercooler Poll (negentropy)",
    [string]$Principal = "negentropy",
    [string]$Thread = "mamba-bridge",
    [int]$EveryMinutes = 15,
    [switch]$AllThreads
)

$ErrorActionPreference = "Stop"

if ($EveryMinutes -lt 1 -or $EveryMinutes -gt 1439) {
    throw "EveryMinutes must be between 1 and 1439."
}

$scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "run_watercooler_poll.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "Missing runner script: $scriptPath"
}

$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$taskCommand = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`" -Principal `"$Principal`""
if ($AllThreads) {
    $taskCommand += " -AllThreads"
} else {
    $taskCommand += " -Thread `"$Thread`""
}

& schtasks.exe /Create /TN $TaskName /SC MINUTE /MO $EveryMinutes /ST $startTime /TR $taskCommand /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks.exe failed while creating $TaskName"
}

Write-Host "Registered scheduled task '$TaskName' every $EveryMinutes minute(s) starting at $startTime for principal '$Principal'."
