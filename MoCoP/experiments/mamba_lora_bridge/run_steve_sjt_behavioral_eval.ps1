param(
    [double]$BaselineAlpha = 0.0,
    [double]$CandidateAlpha = 0.2,
    [double]$Temperature = 0.0,
    [string]$BaseUrl = "http://192.168.2.49:7860",
    [string]$ExpectedModelId = "Qwen/Qwen2.5-1.5B",
    [string]$PanelPath = "",
    [double]$RestoreAlpha = 0.2,
    [double]$RestoreTemperature = 0.7,
    [double]$StartupTimeoutMinutes = 6,
    [switch]$LeaveRunning
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\cerub\OneDrive\Dokumente\LLM"
$workDir = Join-Path $repoRoot "MoCoP\experiments\mamba_lora_bridge"
$runnerPath = Join-Path $workDir "run_sjt_behavioral_eval.py"
$scorerPath = Join-Path $workDir "score_sjt_behavioral_eval.py"
$resolvedPanelPath = if ([string]::IsNullOrWhiteSpace($PanelPath)) {
    Join-Path $workDir "sjt_behavioral_eval_panel_v2.json"
} elseif ([System.IO.Path]::IsPathRooted($PanelPath)) {
    $PanelPath
} else {
    Join-Path $workDir $PanelPath
}
$outputDir = Join-Path $workDir ("behavioral_eval_runs\sjt_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

if (-not (Test-Path $resolvedPanelPath)) {
    throw "Panel file not found: $resolvedPanelPath"
}

function Get-StatusJson {
    param(
        [string]$StatusUrl
    )

    $raw = & curl.exe -sS ($StatusUrl.TrimEnd("/") + "/status")
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($raw)) {
        throw "curl.exe failed to read $StatusUrl/status"
    }
    return $raw | ConvertFrom-Json
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
            $resp = Get-StatusJson -StatusUrl $StatusUrl
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

function Run-SjtCondition {
    param(
        [string]$ConditionLabel,
        [double]$ExpectedAlpha,
        [string]$ResultsPath
    )

    & python -X utf8 $runnerPath `
        --base-url $BaseUrl `
        --panel-file $resolvedPanelPath `
        --results-json $ResultsPath `
        --condition-label $ConditionLabel `
        --expected-alpha $ExpectedAlpha `
        --fail-if-alpha-mismatch
    if ($LASTEXITCODE -ne 0) {
        throw "SJT runner failed for $ConditionLabel"
    }
}

try {
    Write-Host "Output dir: $outputDir"
    Set-SteveTemperature -TemperatureValue $Temperature -NoRestart

    $baselinePath = Join-Path $outputDir "baseline_alpha0p0.json"
    $candidatePath = Join-Path $outputDir "bridge_alpha0p2.json"
    $comparisonPath = Join-Path $outputDir "comparison.json"

    Write-Host "`n=== Baseline alpha $BaselineAlpha ==="
    Set-SteveAlpha -AlphaValue $BaselineAlpha
    Wait-SteveChatReady -StatusUrl $BaseUrl -ExpectedAlpha $BaselineAlpha -ExpectedTemperature $Temperature -ExpectedModel $ExpectedModelId -TimeoutMinutes $StartupTimeoutMinutes
    Run-SjtCondition -ConditionLabel "baseline_alpha_$BaselineAlpha" -ExpectedAlpha $BaselineAlpha -ResultsPath $baselinePath

    Write-Host "`n=== Candidate alpha $CandidateAlpha ==="
    Set-SteveAlpha -AlphaValue $CandidateAlpha
    Wait-SteveChatReady -StatusUrl $BaseUrl -ExpectedAlpha $CandidateAlpha -ExpectedTemperature $Temperature -ExpectedModel $ExpectedModelId -TimeoutMinutes $StartupTimeoutMinutes
    Run-SjtCondition -ConditionLabel "bridge_alpha_$CandidateAlpha" -ExpectedAlpha $CandidateAlpha -ResultsPath $candidatePath

    & python -X utf8 $scorerPath --baseline $baselinePath --candidate $candidatePath --output-json $comparisonPath
    if ($LASTEXITCODE -ne 0) {
        throw "SJT comparison failed."
    }

    Write-Host "Done. Outputs in $outputDir"
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
