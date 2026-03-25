param(
    [double]$Alpha = 0.2,
    [double]$Temperature = 0.0,
    [string]$BaseUrl = "http://192.168.2.49:7860",
    [string]$ExpectedModelId = "Qwen/Qwen2.5-1.5B",
    [double]$RestoreAlpha = 0.2,
    [double]$RestoreTemperature = 0.7,
    [string]$RestoreLayers = "12:v_proj,13:v_proj,14:v_proj,15:v_proj",
    [double]$StartupTimeoutMinutes = 6,
    [switch]$LeaveRunning
)

# Step 5e: Layer Targeting Sweep
# Purple (2026-03-25)
# Requires: Codex's --target-layers override + set_steve_chat_layers.ps1

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\cerub\OneDrive\Dokumente\LLM"
$clientPath = Join-Path $repoRoot "MoCoP\experiments\mamba_lora_bridge\step5d_chat_client.py"
$metricsPath = Join-Path $repoRoot "MoCoP\experiments\measure_ethical_metrics.py"
$outputDir = Join-Path $repoRoot ("tmp\step5e_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Write-Host "`n=== STEP 5e: Layer Targeting Sweep ===" -ForegroundColor Cyan
Write-Host "Alpha: $Alpha | Temp: $Temperature | Output: $outputDir"

# --- Helper functions (same pattern as step5d sweep) ---

function Set-SteveAlpha([double]$AlphaValue) {
    & ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_alpha.ps1 -Alpha $AlphaValue
    if ($LASTEXITCODE -ne 0) { throw "Failed to set alpha to $AlphaValue" }
}

function Set-SteveTemperature([double]$TemperatureValue, [switch]$NoRestart) {
    $sshArgs = @("steve", "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", "C:\Users\tikii\bridge\set_steve_chat_temperature.ps1",
        "-Temperature", $TemperatureValue)
    if ($NoRestart) { $sshArgs += "-NoRestart" }
    & ssh @sshArgs
    if ($LASTEXITCODE -ne 0) { throw "Failed to set temperature to $TemperatureValue" }
}

function Set-SteveLayers([string]$LayerSpec) {
    & ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_layers.ps1 -TargetLayers $LayerSpec
    if ($LASTEXITCODE -ne 0) { throw "Failed to set layers to $LayerSpec" }
}

function Stop-SteveChat {
    & ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\stop_steve_chat_task.ps1
    if ($LASTEXITCODE -ne 0) { throw "Failed to stop Steve chat" }
}

function Wait-SteveChatReady {
    $deadline = (Get-Date).AddMinutes($StartupTimeoutMinutes)
    while ((Get-Date) -lt $deadline) {
        try {
            $status = Invoke-RestMethod "$BaseUrl/status" -TimeoutSec 5
            if ($status.running -eq $true) {
                Write-Host "  Steve ready: model=$($status.model_id) alpha=$($status.alpha) layers=$($status.target_layers)" -ForegroundColor Green
                return
            }
        } catch {}
        Start-Sleep -Seconds 5
        Write-Host "  Waiting for Steve..." -ForegroundColor Yellow
    }
    throw "Steve did not become ready within $StartupTimeoutMinutes minutes"
}

function Run-Probe([string]$Tag, [string]$OutputFile) {
    Write-Host "  Running probe: $Tag" -ForegroundColor Cyan
    & python $clientPath --base-url $BaseUrl --output-log $OutputFile --user-label $Tag 2>&1
    if (Test-Path $OutputFile) {
        & python $metricsPath $OutputFile 2>&1
    }
}

# --- 5e.1: Phase Sweep ---

$phaseSweepConfigs = @(
    @{ Name = "reasoning_entry_5_8";  Layers = "5:v_proj,6:v_proj,7:v_proj,8:v_proj" },
    @{ Name = "mid_reasoning_12_15";  Layers = "12:v_proj,13:v_proj,14:v_proj,15:v_proj" },
    @{ Name = "reasoning_exit_20_23"; Layers = "20:v_proj,21:v_proj,22:v_proj,23:v_proj" }
)

Write-Host "`n--- 5e.1: Phase Sweep (alpha=$Alpha, temp=$Temperature) ---" -ForegroundColor Magenta

# First run baseline (no injection)
Set-SteveTemperature -TemperatureValue $Temperature -NoRestart
Set-SteveAlpha -AlphaValue 0.0
Wait-SteveChatReady
$baselineFile = Join-Path $outputDir "5e1_baseline_alpha0p0.jsonl"
Run-Probe -Tag "5e1_baseline" -OutputFile $baselineFile

foreach ($config in $phaseSweepConfigs) {
    Write-Host "`n  Config: $($config.Name) -> $($config.Layers)" -ForegroundColor White
    Set-SteveLayers -LayerSpec $config.Layers
    Set-SteveAlpha -AlphaValue $Alpha
    Wait-SteveChatReady
    $alphaTag = ("{0:0.0}" -f $Alpha).Replace(".", "p")
    $outFile = Join-Path $outputDir "5e1_$($config.Name)_alpha${alphaTag}.jsonl"
    Run-Probe -Tag "5e1_$($config.Name)" -OutputFile $outFile
}

# --- 5e.2: Per-Layer Alpha Gradient ---

$gradientConfigs = @(
    @{
        Name = "front_loaded"
        # Layer 12=0.3, 13=0.2, 14=0.1, 15=0.05 (avg 0.1625)
        # Implemented as: set layers 12-15, then use per-layer alpha if server supports it
        # Fallback: test uniform at 0.15 (approx average) if per-layer alpha not available
        Layers = "12:v_proj,13:v_proj,14:v_proj,15:v_proj"
        Alpha = 0.15
        Note = "front_loaded_approx"
    },
    @{
        Name = "peak_at_13"
        # Only inject at layer 13 (the sharpest separator per Cassian)
        Layers = "13:v_proj"
        Alpha = $Alpha
        Note = "single_layer_peak"
    }
)

Write-Host "`n--- 5e.2: Gradient / Single-Layer Tests ---" -ForegroundColor Magenta

foreach ($config in $gradientConfigs) {
    Write-Host "`n  Config: $($config.Name) -> $($config.Layers) alpha=$($config.Alpha)" -ForegroundColor White
    Set-SteveLayers -LayerSpec $config.Layers
    Set-SteveAlpha -AlphaValue $config.Alpha
    Wait-SteveChatReady
    $tag = "5e2_$($config.Name)"
    $outFile = Join-Path $outputDir "$tag.jsonl"
    Run-Probe -Tag $tag -OutputFile $outFile
}

# --- 5e.3: Double Injection (Split Dose) ---

Write-Host "`n--- 5e.3: Double Injection (split dose) ---" -ForegroundColor Magenta

# Inject at reasoning entry + mid-reasoning simultaneously
# Layers 5-6 + 12-13 at alpha 0.1 each (total load = 4 layers at 0.1)
$splitConfig = @{
    Name = "split_entry_mid"
    Layers = "5:v_proj,6:v_proj,12:v_proj,13:v_proj"
    Alpha = 0.1
}

Write-Host "`n  Config: $($splitConfig.Name) -> $($splitConfig.Layers) alpha=$($splitConfig.Alpha)" -ForegroundColor White
Set-SteveLayers -LayerSpec $splitConfig.Layers
Set-SteveAlpha -AlphaValue $splitConfig.Alpha
Wait-SteveChatReady
$outFile = Join-Path $outputDir "5e3_$($splitConfig.Name).jsonl"
Run-Probe -Tag "5e3_$($splitConfig.Name)" -OutputFile $outFile

# --- Restore defaults ---

Write-Host "`n--- Restoring defaults ---" -ForegroundColor Yellow
Set-SteveLayers -LayerSpec $RestoreLayers
Set-SteveTemperature -TemperatureValue $RestoreTemperature -NoRestart
Set-SteveAlpha -AlphaValue $RestoreAlpha

if (-not $LeaveRunning) {
    Write-Host "  Parking Steve..." -ForegroundColor Yellow
    Stop-SteveChat
}

# --- Summary ---

Write-Host "`n=== STEP 5e COMPLETE ===" -ForegroundColor Green
Write-Host "Results in: $outputDir"
Write-Host "`nConfigs tested:"
Write-Host "  5e.1 Phase sweep:     baseline, layers 5-8, 12-15, 20-23"
Write-Host "  5e.2 Gradient:        front-loaded (avg 0.15), peak-at-13 only"
Write-Host "  5e.3 Double injection: layers 5-6 + 12-13 at alpha 0.1"
Write-Host "`nCompare all .jsonl files in $outputDir against the baseline."
