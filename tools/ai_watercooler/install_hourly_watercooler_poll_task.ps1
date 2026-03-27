param(
    [string]$TaskName = "AI Watercooler Hourly Poll",
    [string]$Principal = "laura",
    [int]$Minute = 35
)

$ErrorActionPreference = "Stop"

if ($Minute -lt 0 -or $Minute -gt 59) {
    throw "Minute must be between 0 and 59."
}

$scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "run_watercooler_poll.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "Missing runner script: $scriptPath"
}

$now = Get-Date
$startTime = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $now.Hour -Minute $Minute -Second 0
if ($startTime -le $now) {
    $startTime = $startTime.AddHours(1)
}
$startTimeText = $startTime.ToString("HH:mm")

$taskCommand = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`" -Principal `"$Principal`" -AllThreads"

& schtasks.exe /Create /TN $TaskName /SC HOURLY /MO 1 /ST $startTimeText /TR $taskCommand /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks.exe failed while creating $TaskName"
}

Write-Host "Registered scheduled task '$TaskName' to run hourly at minute $Minute (next run $($startTime.ToString('yyyy-MM-dd HH:mm')))."
