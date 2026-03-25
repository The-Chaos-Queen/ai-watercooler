param(
    [Parameter(Mandatory = $true)]
    [string]$TargetLayers,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$bridgeDir = "C:\Users\tikii\bridge"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$stopScriptPath = Join-Path $bridgeDir "stop_steve_chat_task.ps1"
$installScriptPath = Join-Path $bridgeDir "install_steve_chat_task.ps1"
$taskName = "MoCoP Steve Chat"
$targetText = $TargetLayers.Trim()

if (-not $targetText) {
    throw "TargetLayers must not be empty."
}

$pieces = $targetText -split ","
foreach ($piece in $pieces) {
    $part = $piece.Trim()
    if (-not $part) {
        throw "TargetLayers contains an empty entry."
    }
    if ($part -notmatch '^\d+(?::[A-Za-z_][A-Za-z0-9_]*)?$') {
        throw "Invalid target layer entry '$part'. Use layer:proj pairs like 5:v_proj."
    }
}

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

$configData["target_layers"] = $targetText
$configData["updated_at"] = (Get-Date).ToString("o")

[pscustomobject]$configData | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Wrote $configPath with target_layers=$targetText"

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
    Write-Host "Restarted $taskName with target_layers=$targetText"
} elseif (Test-Path $installScriptPath) {
    & $installScriptPath
    Write-Host "Installed and started $taskName with target_layers=$targetText"
} else {
    throw "Could not find scheduled task or install script at $installScriptPath"
}
