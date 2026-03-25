param(
    [double[]]$Alphas = @(0.0, 0.1, 0.2, 0.3),
    [double]$Temperature = 0.0,
    [string]$BaseUrl = "http://192.168.2.49:7860",
    [string]$ExpectedModelId = "Qwen/Qwen2.5-1.5B",
    [double]$RestoreAlpha = 0.2,
    [double]$RestoreTemperature = 0.7,
    [double]$StartupTimeoutMinutes = 6,
    [switch]$LeaveRunning
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\cerub\OneDrive\Dokumente\LLM"
$clientPath = Join-Path $repoRoot "MoCoP\experiments\mamba_lora_bridge\step5d_chat_client.py"
$metricsPath = Join-Path $repoRoot "MoCoP\experiments\measure_ethical_metrics.py"
$outputDir = Join-Path $repoRoot ("tmp\step5d_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

function Format-AlphaTag([double]$AlphaValue) {
    return ("{0:0.0}" -f $AlphaValue).Replace(".", "p")
}

function Set-SteveAlpha([double]$AlphaValue) {
    & ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_alpha.ps1 -Alpha $AlphaValue
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set Steve alpha to $AlphaValue"
    }
}

function Set-SteveTemperature([double]$TemperatureValue, [switch]$NoRestart) {
    $args = @(
        "steve",
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "C:\Users\tikii\bridge\set_steve_chat_temperature.ps1",
        "-Temperature",
        $TemperatureValue
    )
    if ($NoRestart) {
        $args += "-NoRestart"
    }
    & ssh @args
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set Steve temperature to $TemperatureValue"
    }
}

function Stop-SteveChat {
    & ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\stop_steve_chat_task.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to stop Steve chat task"
    }
}

function Wait-SteveChatReady {
    param(
        [string]$StatusUrl,
        [double]$ExpectedAlpha,
        [double]$ExpectedTemperature,
        [string]$ExpectedModel,
        [double]$TimeoutMinutes = 6
    )

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    $lastSummary = "no status response"
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-RestMethod -Uri ($StatusUrl.TrimEnd("/") + "/status") -Method Get -TimeoutSec 8
            $alphaMatches = $false
            $temperatureMatches = $false
            if ($null -ne $resp.alpha) {
                $alphaMatches = [math]::Abs(([double]$resp.alpha) - $ExpectedAlpha) -lt 0.0001
            }
            if ($null -ne $resp.temperature) {
                $temperatureMatches = [math]::Abs(([double]$resp.temperature) - $ExpectedTemperature) -lt 0.0001
            }
            $modelMatches = [string]$resp.model_id -eq $ExpectedModel
            $turnsReset = [int]$resp.turns -eq 0
            $lastSummary = "running=$($resp.running) busy=$($resp.busy) stop=$($resp.stop_requested) alpha=$($resp.alpha) temp=$($resp.temperature) model=$($resp.model_id) turns=$($resp.turns)"
            if ($resp.running -and -not $resp.stop_requested -and $alphaMatches -and $temperatureMatches -and $modelMatches -and $turnsReset) {
                return
            }
        } catch {
            $lastSummary = $_.Exception.Message
        }
        Start-Sleep -Seconds 3
    }

    throw "Steve chat did not become ready at $StatusUrl for alpha=$ExpectedAlpha temp=$ExpectedTemperature model=$ExpectedModel within $TimeoutMinutes minute(s). Last status: $lastSummary"
}

function Run-PromptSet {
    param(
        [string]$PromptSet,
        [string]$LogPath,
        [switch]$Append
    )

    $args = @(
        $clientPath,
        "--base-url", $BaseUrl,
        "--output-log", $LogPath,
        "--prompt-set", $PromptSet
    )
    if ($Append) {
        $args += "--append"
    }
    & python -X utf8 @args
    if ($LASTEXITCODE -ne 0) {
        throw "Prompt-set run failed for $PromptSet -> $LogPath"
    }
}

function Measure-Run {
    param(
        [string]$LogPath,
        [string]$BaselineLog
    )

    $args = @($metricsPath, $LogPath)
    if ($BaselineLog) {
        $args += @("--baseline-log", $BaselineLog)
    }
    & python -X utf8 @args
    if ($LASTEXITCODE -ne 0) {
        throw "Metrics run failed for $LogPath"
    }
}

try {
    Write-Host "Output dir: $outputDir"
    Write-Host "Setting Steve temperature to $Temperature"
    Set-SteveTemperature -TemperatureValue $Temperature -NoRestart

    $baselineLog = Join-Path $outputDir ("alpha_" + (Format-AlphaTag 0.0) + ".jsonl")

    Write-Host "`n=== Baseline alpha 0.0 ==="
    Set-SteveAlpha -AlphaValue 0.0
    Wait-SteveChatReady -StatusUrl $BaseUrl -ExpectedAlpha 0.0 -ExpectedTemperature $Temperature -ExpectedModel $ExpectedModelId -TimeoutMinutes $StartupTimeoutMinutes
    Run-PromptSet -PromptSet "injection" -LogPath $baselineLog

    Write-Host "=== Baseline recovery at alpha 0.0 ==="
    Set-SteveAlpha -AlphaValue 0.0
    Wait-SteveChatReady -StatusUrl $BaseUrl -ExpectedAlpha 0.0 -ExpectedTemperature $Temperature -ExpectedModel $ExpectedModelId -TimeoutMinutes $StartupTimeoutMinutes
    Run-PromptSet -PromptSet "recovery" -LogPath $baselineLog -Append
    Measure-Run -LogPath $baselineLog -BaselineLog ""

    foreach ($alpha in $Alphas | Where-Object { $_ -gt 0.0 }) {
        $alphaTag = Format-AlphaTag $alpha
        $logPath = Join-Path $outputDir ("alpha_" + $alphaTag + ".jsonl")

        Write-Host "`n=== Injection alpha $alpha ==="
        Set-SteveAlpha -AlphaValue $alpha
        Wait-SteveChatReady -StatusUrl $BaseUrl -ExpectedAlpha $alpha -ExpectedTemperature $Temperature -ExpectedModel $ExpectedModelId -TimeoutMinutes $StartupTimeoutMinutes
        Run-PromptSet -PromptSet "injection" -LogPath $logPath

        Write-Host "=== Recovery at alpha 0.0 after alpha $alpha ==="
        Set-SteveAlpha -AlphaValue 0.0
        Wait-SteveChatReady -StatusUrl $BaseUrl -ExpectedAlpha 0.0 -ExpectedTemperature $Temperature -ExpectedModel $ExpectedModelId -TimeoutMinutes $StartupTimeoutMinutes
        Run-PromptSet -PromptSet "recovery" -LogPath $logPath -Append

        Measure-Run -LogPath $logPath -BaselineLog $baselineLog
    }

    Write-Host "Done. Logs in $outputDir"
} finally {
    Write-Host "`nRestoring Steve defaults alpha=$RestoreAlpha temperature=$RestoreTemperature"
    try {
        Set-SteveTemperature -TemperatureValue $RestoreTemperature -NoRestart
        Set-SteveAlpha -AlphaValue $RestoreAlpha
    } finally {
        if (-not $LeaveRunning) {
            Stop-SteveChat
        }
    }
}
