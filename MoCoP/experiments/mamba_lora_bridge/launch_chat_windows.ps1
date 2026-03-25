$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$bridgeDir = "C:\Users\tikii\bridge"
$logDir = Join-Path $bridgeDir "logs"
$logPath = Join-Path $logDir "steve_chat_windows_task.log"
$wslExe = "C:\Windows\System32\wsl.exe"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$defaultAlpha = 0.2
$defaultTemperature = 0.7
$defaultQwenModelId = "Qwen/Qwen2.5-1.5B"
$defaultTargetLayers = ""
$defaultDualGateEnabled = $true
$defaultDualGateWarmupTurns = 3
$defaultDualGateSalienceQuantile = 0.75
$defaultDualGateSurpriseQuantile = 0.75
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$alpha = $defaultAlpha
$temperature = $defaultTemperature
$qwenModelId = $defaultQwenModelId
$targetLayers = $defaultTargetLayers
$dualGateEnabled = $defaultDualGateEnabled
$dualGateWarmupTurns = $defaultDualGateWarmupTurns
$dualGateSalienceQuantile = $defaultDualGateSalienceQuantile
$dualGateSurpriseQuantile = $defaultDualGateSurpriseQuantile

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestamp] starting MoCoP Steve chat task"

if (Test-Path $configPath) {
    try {
        $config = Get-Content -Path $configPath -Raw | ConvertFrom-Json
        if ($null -ne $config.alpha -and "$($config.alpha)".Trim()) {
            $rawAlpha = "$($config.alpha)".Trim()
            $parsedAlpha = 0.0
            if (
                [double]::TryParse($rawAlpha, [System.Globalization.NumberStyles]::Float, $culture, [ref]$parsedAlpha) -or
                [double]::TryParse($rawAlpha, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::CurrentCulture, [ref]$parsedAlpha)
            ) {
                $alpha = $parsedAlpha
            } else {
                Add-Content -Path $logPath -Value "[$timestamp] invalid alpha in config, using default: $rawAlpha"
            }
        }
        if ($null -ne $config.qwen_model_id -and "$($config.qwen_model_id)".Trim()) {
            $qwenModelId = "$($config.qwen_model_id)".Trim()
        }
        if ($null -ne $config.target_layers -and "$($config.target_layers)".Trim()) {
            $targetLayers = "$($config.target_layers)".Trim()
        }
        if ($null -ne $config.temperature -and "$($config.temperature)".Trim()) {
            $rawTemperature = "$($config.temperature)".Trim()
            $parsedTemperature = 0.0
            if (
                [double]::TryParse($rawTemperature, [System.Globalization.NumberStyles]::Float, $culture, [ref]$parsedTemperature) -or
                [double]::TryParse($rawTemperature, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::CurrentCulture, [ref]$parsedTemperature)
            ) {
                $temperature = $parsedTemperature
            } else {
                Add-Content -Path $logPath -Value "[$timestamp] invalid temperature in config, using default: $rawTemperature"
            }
        }
        if ($null -ne $config.dual_gate_enabled) {
            try {
                $dualGateEnabled = [System.Convert]::ToBoolean($config.dual_gate_enabled)
            } catch {
                Add-Content -Path $logPath -Value "[$timestamp] invalid dual_gate_enabled in config, using default: $($config.dual_gate_enabled)"
            }
        }
        if ($null -ne $config.dual_gate_warmup_turns -and "$($config.dual_gate_warmup_turns)".Trim()) {
            $rawWarmup = "$($config.dual_gate_warmup_turns)".Trim()
            $parsedWarmup = 0
            if ([int]::TryParse($rawWarmup, [ref]$parsedWarmup)) {
                $dualGateWarmupTurns = $parsedWarmup
            } else {
                Add-Content -Path $logPath -Value "[$timestamp] invalid dual_gate_warmup_turns in config, using default: $rawWarmup"
            }
        }
        if ($null -ne $config.dual_gate_salience_quantile -and "$($config.dual_gate_salience_quantile)".Trim()) {
            $rawSalienceQuantile = "$($config.dual_gate_salience_quantile)".Trim()
            $parsedSalienceQuantile = 0.0
            if (
                [double]::TryParse($rawSalienceQuantile, [System.Globalization.NumberStyles]::Float, $culture, [ref]$parsedSalienceQuantile) -or
                [double]::TryParse($rawSalienceQuantile, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::CurrentCulture, [ref]$parsedSalienceQuantile)
            ) {
                $dualGateSalienceQuantile = $parsedSalienceQuantile
            } else {
                Add-Content -Path $logPath -Value "[$timestamp] invalid dual_gate_salience_quantile in config, using default: $rawSalienceQuantile"
            }
        }
        if ($null -ne $config.dual_gate_surprise_quantile -and "$($config.dual_gate_surprise_quantile)".Trim()) {
            $rawSurpriseQuantile = "$($config.dual_gate_surprise_quantile)".Trim()
            $parsedSurpriseQuantile = 0.0
            if (
                [double]::TryParse($rawSurpriseQuantile, [System.Globalization.NumberStyles]::Float, $culture, [ref]$parsedSurpriseQuantile) -or
                [double]::TryParse($rawSurpriseQuantile, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::CurrentCulture, [ref]$parsedSurpriseQuantile)
            ) {
                $dualGateSurpriseQuantile = $parsedSurpriseQuantile
            } else {
                Add-Content -Path $logPath -Value "[$timestamp] invalid dual_gate_surprise_quantile in config, using default: $rawSurpriseQuantile"
            }
        }
    } catch {
        Add-Content -Path $logPath -Value "[$timestamp] failed to read config, using default alpha: $($_.Exception.Message)"
    }
}

$alphaArg = $alpha.ToString($culture)
$temperatureArg = $temperature.ToString($culture)
$dualGateWarmupArg = $dualGateWarmupTurns.ToString($culture)
$dualGateSalienceArg = $dualGateSalienceQuantile.ToString($culture)
$dualGateSurpriseArg = $dualGateSurpriseQuantile.ToString($culture)

$wslIp = ((& $wslExe -u root sh -lc "hostname -I").Trim() -split "\s+")[0]
if (-not $wslIp) {
    throw "Could not determine WSL IP for Steve chat portproxy."
}

cmd /c "netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=7860" | Out-Null
cmd /c "netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=7860 connectaddress=$wslIp connectport=7860" | Out-Null
Add-Content -Path $logPath -Value "[$timestamp] portproxy -> $($wslIp):7860"
Add-Content -Path $logPath -Value "[$timestamp] chat alpha -> $alphaArg"
Add-Content -Path $logPath -Value "[$timestamp] chat model -> $qwenModelId"
Add-Content -Path $logPath -Value "[$timestamp] chat temperature -> $temperatureArg"
if ($targetLayers) {
    Add-Content -Path $logPath -Value "[$timestamp] chat target_layers -> $targetLayers"
}
Add-Content -Path $logPath -Value "[$timestamp] dual gate -> $dualGateEnabled warmup=$dualGateWarmupArg salience_q=$dualGateSalienceArg surprise_q=$dualGateSurpriseArg"

$dualGateSwitch = ""
if (-not $dualGateEnabled) {
    $dualGateSwitch = " --no-dual-gate"
}

$targetLayersSwitch = ""
if ($targetLayers) {
    $targetLayersSwitch = " --target-layers $targetLayers"
}

$pythonCommand = "cd /mnt/c/Users/tikii/bridge && exec /root/mocop_venv/bin/python3 -X utf8 chat_server.py --qwen-model-id $qwenModelId --temperature $temperatureArg --alpha $alphaArg --dual-gate-warmup-turns $dualGateWarmupArg --dual-gate-salience-quantile $dualGateSalienceArg --dual-gate-surprise-quantile $dualGateSurpriseArg --max-new-tokens 200 --host 0.0.0.0 --port 7860$dualGateSwitch$targetLayersSwitch"

$wslArgs = @(
    "-u", "root",
    "bash", "-lc",
    $pythonCommand
)

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $wslExe @wslArgs *>> $logPath
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestamp] chat task exited with code $exitCode"
exit $exitCode
