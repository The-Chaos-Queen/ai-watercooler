param(
    [switch]$Enabled,
    [switch]$Disabled,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

if ($Enabled -and $Disabled) {
    throw "Specify either -Enabled or -Disabled, not both."
}

if (-not $Enabled -and -not $Disabled) {
    throw "Specify one of -Enabled or -Disabled."
}

$bridgeDir = "C:\Users\tikii\bridge"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$stopScriptPath = Join-Path $bridgeDir "stop_steve_chat_task.ps1"
$installScriptPath = Join-Path $bridgeDir "install_steve_chat_task.ps1"
$taskName = "MoCoP Steve Chat"
$liveAccumulation = [bool]$Enabled

New-Item -ItemType Directory -Force -Path $bridgeDir | Out-Null

$configData = @{}
if (Test-Path $configPath) {
    try {
        $existingConfig = Get-Content -Path $configPath -Raw | ConvertFrom-Json
        if ($null -ne $existingConfig) {
            foreach ($property in $existingConfig.PSObject.Properties) {
                $configData[$property.Name] = $property.Value
            }
        }
    } catch {
    }
}

$configData["live_accumulation"] = $liveAccumulation
$configData["updated_at"] = (Get-Date).ToString("o")

[pscustomobject]$configData | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Wrote $configPath with live_accumulation=$liveAccumulation"

if ($NoRestart) {
    Write-Host "NoRestart set. Current running task was not touched."
    return
}

if (Test-Path $stopScriptPath) {
    $taskWasEnabled = $false
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($null -ne $task) {
        $taskWasEnabled = -not $task.Settings.Disabled
        if ($taskWasEnabled) {
            Disable-ScheduledTask -TaskName $taskName | Out-Null
        }
    }

    try {
        & $stopScriptPath
        Start-Sleep -Seconds 2
    } finally {
        if ($taskWasEnabled) {
            Enable-ScheduledTask -TaskName $taskName | Out-Null
        }
    }
}

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Start-ScheduledTask -TaskName $taskName
    Write-Host "Restarted $taskName with live_accumulation=$liveAccumulation"
} elseif (Test-Path $installScriptPath) {
    & $installScriptPath
    Write-Host "Installed and started $taskName with live_accumulation=$liveAccumulation"
} else {
    throw "Could not find scheduled task or install script at $installScriptPath"
}
