param(
    [string]$User = "User",
    [string]$BaseUrl = "http://192.168.2.194:7863",
    [int]$Port = 7863,
    [double]$BaselineAlpha = 0.0,
    [double]$CandidateAlpha = 0.2,
    [double]$Temperature = 0.0,
    [string]$ExpectedModelId = "Qwen/Qwen2.5-1.5B",
    [double]$StartupTimeoutMinutes = 8,
    [int]$Limit = 0
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = "C:\Users\cerub\OneDrive\Dokumente\LLM"
$workDir = Join-Path $repoRoot "MoCoP\experiments\mamba_lora_bridge"
$startServerPath = Join-Path $workDir "start_opa_live_chat_server.ps1"
$runnerPath = Join-Path $workDir "run_sjt_behavioral_eval.py"
$scorerPath = Join-Path $workDir "score_sjt_behavioral_eval.py"
$panelPath = Join-Path $workDir "sjt_behavioral_eval_panel.json"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputDir = Join-Path $workDir ("behavioral_eval_runs\opa_sjt_" + $timestamp)
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

function Wait-OpaChatReady {
    param(
        [double]$ExpectedAlpha,
        [double]$ExpectedTemperature,
        [string]$ExpectedModel,
        [string]$ExpectedInstanceId,
        [double]$TimeoutMinutes = 8
    )

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    $lastSummary = "no status response"
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-RestMethod -Uri ($BaseUrl.TrimEnd("/") + "/status") -Method Get -TimeoutSec 8
            $alphaMatches = $false
            $temperatureMatches = $false
            if ($null -ne $resp.alpha) {
                $alphaMatches = [math]::Abs(([double]$resp.alpha) - $ExpectedAlpha) -lt 0.0001
            }
            if ($null -ne $resp.temperature) {
                $temperatureMatches = [math]::Abs(([double]$resp.temperature) - $ExpectedTemperature) -lt 0.0001
            }
            $modelMatches = [string]$resp.model_id -eq $ExpectedModel
            $instanceMatches = [string]$resp.instance_id -eq $ExpectedInstanceId
            $turnsReset = [int]$resp.turns -eq 0
            $lastSummary = "running=$($resp.running) busy=$($resp.busy) alpha=$($resp.alpha) temp=$($resp.temperature) model=$($resp.model_id) instance=$($resp.instance_id) turns=$($resp.turns)"
            if ($resp.running -and -not $resp.stop_requested -and $alphaMatches -and $temperatureMatches -and $modelMatches -and $instanceMatches -and $turnsReset) {
                return $resp
            }
        } catch {
            $lastSummary = $_.Exception.Message
        }
        Start-Sleep -Seconds 3
    }

    throw "Opa chat did not become ready at $BaseUrl for alpha=$ExpectedAlpha temp=$ExpectedTemperature model=$ExpectedModel instance=$ExpectedInstanceId within $TimeoutMinutes minute(s). Last status: $lastSummary"
}

function Start-OpaCondition {
    param(
        [double]$AlphaValue,
        [string]$InstanceId,
        [switch]$NoSync
    )

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $startServerPath,
        "-User", $User,
        "-InstanceId", $InstanceId,
        "-Port", $Port,
        "-Alpha", $AlphaValue,
        "-Temperature", $Temperature,
        "-QwenModelId", $ExpectedModelId,
        "-QdrantWriteMode", "critical-only"
    )
    if ($NoSync) {
        $args += "-NoSync"
    }
    & powershell @args
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start Opa condition $InstanceId"
    }

    Wait-OpaChatReady -ExpectedAlpha $AlphaValue -ExpectedTemperature $Temperature -ExpectedModel $ExpectedModelId -ExpectedInstanceId $InstanceId -TimeoutMinutes $StartupTimeoutMinutes | Out-Null
}

function Run-SjtCondition {
    param(
        [string]$ConditionLabel,
        [double]$ExpectedAlpha,
        [string]$ResultsPath
    )

    $args = @(
        "-X", "utf8",
        $runnerPath,
        "--base-url", $BaseUrl,
        "--panel-file", $panelPath,
        "--results-json", $ResultsPath,
        "--condition-label", $ConditionLabel,
        "--expected-alpha", $ExpectedAlpha,
        "--fail-if-alpha-mismatch"
    )
    if ($Limit -gt 0) {
        $args += @("--limit", $Limit)
    }
    & python @args
    if ($LASTEXITCODE -ne 0) {
        throw "SJT runner failed for $ConditionLabel"
    }
}

function Write-RunSummary {
    param(
        [string]$BaselinePath,
        [string]$CandidatePath,
        [string]$ComparisonPath,
        [string]$SummaryPath
    )

    @'
import json
import pathlib
import sys

baseline_path = pathlib.Path(sys.argv[1])
candidate_path = pathlib.Path(sys.argv[2])
comparison_path = pathlib.Path(sys.argv[3])
summary_path = pathlib.Path(sys.argv[4])

baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
comparison = json.loads(comparison_path.read_text(encoding="utf-8"))

lines = []
lines.append("# Opa SJT Behavioral Eval")
lines.append("")
lines.append(f"**Ran at:** {comparison.get('ran_at', '')}")
lines.append(f"**Base URL:** {baseline.get('metadata', {}).get('base_url', '')}")
lines.append(f"**Panel:** `{baseline.get('metadata', {}).get('panel_file', '')}`")
lines.append("")
lines.append("## Summary")
lines.append("")
lines.append(f"- Baseline TPR: `{baseline.get('summary', {}).get('trait_positive_rate')}`")
lines.append(f"- Candidate TPR: `{candidate.get('summary', {}).get('trait_positive_rate')}`")
lines.append(f"- Baseline mean warmth: `{baseline.get('summary', {}).get('mean_warmth_score')}`")
lines.append(f"- Candidate mean warmth: `{candidate.get('summary', {}).get('mean_warmth_score')}`")
lines.append(f"- Directional alignment: `{comparison.get('comparison', {}).get('directional_alignment')}`")
lines.append(f"- Reverse rate: `{comparison.get('comparison', {}).get('reverse_rate')}`")
lines.append(f"- Tie rate: `{comparison.get('comparison', {}).get('tie_rate')}`")
lines.append(f"- TPR delta: `{comparison.get('comparison', {}).get('trait_positive_rate_delta')}`")
lines.append(f"- Warmth delta: `{comparison.get('comparison', {}).get('mean_warmth_score_delta')}`")
lines.append("")
lines.append("## Files")
lines.append("")
lines.append(f"- `{baseline_path.name}`")
lines.append(f"- `{candidate_path.name}`")
lines.append(f"- `{comparison_path.name}`")
summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote summary to {summary_path}")
'@ | python - $BaselinePath $CandidatePath $ComparisonPath $SummaryPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to write Opa SJT summary."
    }
}

function Format-AlphaLabel([double]$Value) {
    return ([string]$Value).Replace(".", "p")
}

$baselineInstance = "baby_sjt_opa_${timestamp}_baseline"
$candidateInstance = "baby_sjt_opa_${timestamp}_candidate"
$baselineLabel = Format-AlphaLabel $BaselineAlpha
$candidateLabel = Format-AlphaLabel $CandidateAlpha
$baselinePath = Join-Path $outputDir ("baseline_alpha{0}.json" -f $baselineLabel)
$candidatePath = Join-Path $outputDir ("bridge_alpha{0}.json" -f $candidateLabel)
$comparisonPath = Join-Path $outputDir "comparison.json"
$summaryPath = Join-Path $outputDir "summary.md"

Write-Host "Output dir: $outputDir"

Write-Host "`n=== Baseline alpha $BaselineAlpha ==="
Start-OpaCondition -AlphaValue $BaselineAlpha -InstanceId $baselineInstance
Run-SjtCondition -ConditionLabel "baseline_alpha_$BaselineAlpha" -ExpectedAlpha $BaselineAlpha -ResultsPath $baselinePath

Write-Host "`n=== Candidate alpha $CandidateAlpha ==="
Start-OpaCondition -AlphaValue $CandidateAlpha -InstanceId $candidateInstance -NoSync
Run-SjtCondition -ConditionLabel "bridge_alpha_$CandidateAlpha" -ExpectedAlpha $CandidateAlpha -ResultsPath $candidatePath

& python -X utf8 $scorerPath --baseline $baselinePath --candidate $candidatePath --output-json $comparisonPath
if ($LASTEXITCODE -ne 0) {
    throw "SJT comparison failed."
}

Write-RunSummary -BaselinePath $baselinePath -CandidatePath $candidatePath -ComparisonPath $comparisonPath -SummaryPath $summaryPath

Write-Host "`nCandidate instance remains on port $Port until the next Opa launch replaces it." -ForegroundColor Yellow

Write-Host "Done. Outputs in $outputDir"
