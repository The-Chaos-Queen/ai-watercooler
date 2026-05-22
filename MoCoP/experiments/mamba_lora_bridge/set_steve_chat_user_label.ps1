param(
    [Parameter(Mandatory = $true)]
    [string]$UserLabel,
    [string]$ModelLabel = "",
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$bridgeDir = "C:\Users\tikii\bridge"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$stopScriptPath = Join-Path $bridgeDir "stop_steve_chat_task.ps1"
$installScriptPath = Join-Path $bridgeDir "install_steve_chat_task.ps1"
$taskName = "MoCoP Steve Chat"

$userLabelText = $UserLabel.Trim()
$modelLabelText = $ModelLabel.Trim()

if (-not $userLabelText) {
    throw "UserLabel must not be empty."
}

if ($userLabelText -match "[`r`n]") {
    throw "UserLabel must not contain newlines."
}

if ($modelLabelText -and $modelLabelText -match "[`r`n]") {
    throw "ModelLabel must not contain newlines."
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

$configData["user_label"] = $userLabelText
if ($modelLabelText) {
    $configData["model_label"] = $modelLabelText
} elseif (-not $configData.ContainsKey("model_label")) {
    $configData["model_label"] = "Me"
}
$configData["updated_at"] = (Get-Date).ToString("o")

[pscustomobject]$configData | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Wrote $configPath with user_label=$userLabelText model_label=$($configData["model_label"])"

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
    Write-Host "Restarted $taskName with user_label=$userLabelText"
} elseif (Test-Path $installScriptPath) {
    & $installScriptPath
    Write-Host "Installed and started $taskName with user_label=$userLabelText"
} else {
    throw "Could not find scheduled task or install script at $installScriptPath"
}
