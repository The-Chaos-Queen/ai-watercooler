param(
    [string]$TaskName = "MoCoP Opa WiFi Watch",
    [string]$TargetSsid = "KFCandWatermelon",
    [string]$InterfaceAlias = "Wi-Fi",
    [int]$EveryMinutes = 5,
    [int]$ConnectWaitSeconds = 15,
    [string]$LogPath = "C:\Users\User\bridge\logs\opa_wifi_watch.log"
)

$ErrorActionPreference = "Stop"

if ($EveryMinutes -lt 1 -or $EveryMinutes -gt 1439) {
    throw "EveryMinutes must be between 1 and 1439."
}

$scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "ensure_opa_wifi.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "Missing WiFi enforcement script: $scriptPath"
}

$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$taskCommand = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`" -TargetSsid `"$TargetSsid`" -InterfaceAlias `"$InterfaceAlias`" -ConnectWaitSeconds $ConnectWaitSeconds -LogPath `"$LogPath`" -SetPrivate"

& schtasks.exe /Create /TN $TaskName /SC MINUTE /MO $EveryMinutes /ST $startTime /TR $taskCommand /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks.exe failed while creating '$TaskName'."
}

Write-Host "Registered scheduled task '$TaskName' every $EveryMinutes minute(s) starting at $startTime."
Write-Host "Target SSID: $TargetSsid"
Write-Host "Log path: $LogPath"
