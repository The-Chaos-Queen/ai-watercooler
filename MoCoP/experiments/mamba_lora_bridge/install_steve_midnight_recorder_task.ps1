param(
    [string]$TaskName = "MoCoP Steve Midnight Recorder",
    [int]$Hour = 0,
    [int]$Minute = 5
)

$ErrorActionPreference = "Stop"

if ($Hour -lt 0 -or $Hour -gt 23) {
    throw "Hour must be between 0 and 23."
}
if ($Minute -lt 0 -or $Minute -gt 59) {
    throw "Minute must be between 0 and 59."
}

$runnerPath = "C:\Users\tikii\bridge\run_steve_midnight_recorder.ps1"
$taskUser = $env:USERNAME

$now = Get-Date
$scheduledAt = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $Hour -Minute $Minute -Second 0
if ($scheduledAt -le $now) {
    $scheduledAt = $scheduledAt.AddDays(1)
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    try {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
    } catch {
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runnerPath`""

$trigger = New-ScheduledTaskTrigger -Once -At $scheduledAt
$principal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Write-Host "Registered '$TaskName' for $($scheduledAt.ToString('yyyy-MM-dd HH:mm'))."
