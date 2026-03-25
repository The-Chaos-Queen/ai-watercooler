param(
    [Parameter(Mandatory = $true)]
    [double]$Temperature,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$bridgeDir = "C:\Users\tikii\bridge"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$stopScriptPath = Join-Path $bridgeDir "stop_steve_chat_task.ps1"
$installScriptPath = Join-Path $bridgeDir "install_steve_chat_task.ps1"
$taskName = "MoCoP Steve Chat"
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$temperatureText = $Temperature.ToString($culture)

if ($Temperature -lt 0.0) {
    throw "Temperature must be >= 0."
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

$configData["temperature"] = $temperatureText
$configData["updated_at"] = (Get-Date).ToString("o")

[pscustomobject]$configData | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Wrote $configPath with temperature=$temperatureText"

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
    Write-Host "Restarted $taskName with temperature=$temperatureText"
} elseif (Test-Path $installScriptPath) {
    & $installScriptPath
    Write-Host "Installed and started $taskName with temperature=$temperatureText"
} else {
    throw "Could not find scheduled task or install script at $installScriptPath"
}
