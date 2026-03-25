param(
    [Parameter(Mandatory = $true)]
    [string]$QwenModelId,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$bridgeDir = "C:\Users\tikii\bridge"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$stopScriptPath = Join-Path $bridgeDir "stop_steve_chat_task.ps1"
$installScriptPath = Join-Path $bridgeDir "install_steve_chat_task.ps1"
$taskName = "MoCoP Steve Chat"
$modelText = $QwenModelId.Trim()

if (-not $modelText) {
    throw "QwenModelId must not be empty."
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

$configData["qwen_model_id"] = $modelText
$configData["updated_at"] = (Get-Date).ToString("o")

[pscustomobject]$configData | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Wrote $configPath with qwen_model_id=$modelText"

if ($NoRestart) {
    Write-Host "NoRestart set. Current running task was not touched."
    return
}

if (Test-Path $stopScriptPath) {
    & $stopScriptPath
    Start-Sleep -Seconds 2
}

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Start-ScheduledTask -TaskName $taskName
    Write-Host "Restarted $taskName with qwen_model_id=$modelText"
} elseif (Test-Path $installScriptPath) {
    & $installScriptPath
    Write-Host "Installed and started $taskName with qwen_model_id=$modelText"
} else {
    throw "Could not find scheduled task or install script at $installScriptPath"
}
