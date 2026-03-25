param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("direct", "pending", "critical-only")]
    [string]$Mode,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$bridgeDir = "C:\Users\tikii\bridge"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$stopScriptPath = Join-Path $bridgeDir "stop_steve_chat_task.ps1"
$installScriptPath = Join-Path $bridgeDir "install_steve_chat_task.ps1"
$taskName = "MoCoP Steve Chat"

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

$configData["qdrant_write_mode"] = $Mode
$configData["updated_at"] = (Get-Date).ToString("o")

[pscustomobject]$configData | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Wrote $configPath with qdrant_write_mode=$Mode"

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
    Write-Host "Restarted $taskName with qdrant_write_mode=$Mode"
} elseif (Test-Path $installScriptPath) {
    & $installScriptPath
    Write-Host "Installed and started $taskName with qdrant_write_mode=$Mode"
} else {
    throw "Could not find scheduled task or install script at $installScriptPath"
}
