$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$bridgeDir = "C:\Users\tikii\bridge"
$logDir = Join-Path $bridgeDir "logs"
$logPath = Join-Path $logDir "steve_chat_windows_task.log"
$wslExe = "C:\Windows\System32\wsl.exe"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$defaultAlpha = 0.2
$defaultTemperature = 0.7
$defaultQwenModelId = "Qwen/Qwen2.5-7B"
$defaultTargetLayers = ""
$defaultQdrantWriteMode = "pending"
$defaultUserLabel = "User"
$defaultModelLabel = "Me"
$defaultDualGateEnabled = $true
$defaultDualGateWarmupTurns = 3
$defaultDualGateSalienceQuantile = 0.75
$defaultDualGateSurpriseQuantile = 0.75
$defaultDualGateSupportedTensionEnabled = $false
$defaultDualGateTensionSalienceSupportRatio = 0.55
$defaultEpisodeIndex = 2
$defaultBlindDispositionUi = $false
$defaultLiveAccumulation = $false
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$alpha = $defaultAlpha
$temperature = $defaultTemperature
$qwenModelId = $defaultQwenModelId
$targetLayers = $defaultTargetLayers
$qdrantWriteMode = $defaultQdrantWriteMode
$userLabel = $defaultUserLabel
$modelLabel = $defaultModelLabel
$dualGateEnabled = $defaultDualGateEnabled
$dualGateWarmupTurns = $defaultDualGateWarmupTurns
$dualGateSalienceQuantile = $defaultDualGateSalienceQuantile
$dualGateSurpriseQuantile = $defaultDualGateSurpriseQuantile
$dualGateSupportedTensionEnabled = $defaultDualGateSupportedTensionEnabled
$dualGateTensionSalienceSupportRatio = $defaultDualGateTensionSalienceSupportRatio
$episodeIndex = $defaultEpisodeIndex
$blindDispositionUi = $defaultBlindDispositionUi
$liveAccumulation = $defaultLiveAccumulation

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function ConvertTo-BashArg {
    param([AllowNull()][string]$Value)

    if ($null -eq $Value) {
        return "''"
    }

    return "'" + ($Value -replace "'", "'`"`'`"`'") + "'"
}

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
        if ($null -ne $config.qdrant_write_mode -and "$($config.qdrant_write_mode)".Trim()) {
            $rawQdrantWriteMode = "$($config.qdrant_write_mode)".Trim()
            if ($rawQdrantWriteMode -in @("direct", "pending", "critical-only")) {
                $qdrantWriteMode = $rawQdrantWriteMode
            } else {
                Add-Content -Path $logPath -Value "[$timestamp] invalid qdrant_write_mode in config, using default: $rawQdrantWriteMode"
            }
        }
        if ($null -ne $config.user_label -and "$($config.user_label)".Trim()) {
            $rawUserLabel = "$($config.user_label)".Trim()
            if ($rawUserLabel -match "[`r`n]") {
                Add-Content -Path $logPath -Value "[$timestamp] invalid user_label in config, using default: contains newline"
            } else {
                $userLabel = $rawUserLabel
            }
        }
        if ($null -ne $config.model_label -and "$($config.model_label)".Trim()) {
            $rawModelLabel = "$($config.model_label)".Trim()
            if ($rawModelLabel -match "[`r`n]") {
                Add-Content -Path $logPath -Value "[$timestamp] invalid model_label in config, using default: contains newline"
            } else {
                $modelLabel = $rawModelLabel
            }
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
        if ($null -ne $config.dual_gate_supported_tension_enabled) {
            try {
                $dualGateSupportedTensionEnabled = [System.Convert]::ToBoolean($config.dual_gate_supported_tension_enabled)
            } catch {
                Add-Content -Path $logPath -Value "[$timestamp] invalid dual_gate_supported_tension_enabled in config, using default: $($config.dual_gate_supported_tension_enabled)"
            }
        }
        if ($null -ne $config.dual_gate_tension_salience_support_ratio -and "$($config.dual_gate_tension_salience_support_ratio)".Trim()) {
            $rawSupportRatio = "$($config.dual_gate_tension_salience_support_ratio)".Trim()
            $parsedSupportRatio = 0.0
            if (
                [double]::TryParse($rawSupportRatio, [System.Globalization.NumberStyles]::Float, $culture, [ref]$parsedSupportRatio) -or
                [double]::TryParse($rawSupportRatio, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::CurrentCulture, [ref]$parsedSupportRatio)
            ) {
                $dualGateTensionSalienceSupportRatio = $parsedSupportRatio
            } else {
                Add-Content -Path $logPath -Value "[$timestamp] invalid dual_gate_tension_salience_support_ratio in config, using default: $rawSupportRatio"
            }
        }
        if ($null -ne $config.episode_index -and "$($config.episode_index)".Trim()) {
            $rawEpisodeIndex = "$($config.episode_index)".Trim()
            $parsedEpisodeIndex = 0
            if ([int]::TryParse($rawEpisodeIndex, [ref]$parsedEpisodeIndex)) {
                $episodeIndex = $parsedEpisodeIndex
            } else {
                Add-Content -Path $logPath -Value "[$timestamp] invalid episode_index in config, using default: $rawEpisodeIndex"
            }
        }
        if ($null -ne $config.blind_disposition_ui) {
            try {
                $blindDispositionUi = [System.Convert]::ToBoolean($config.blind_disposition_ui)
            } catch {
                Add-Content -Path $logPath -Value "[$timestamp] invalid blind_disposition_ui in config, using default: $($config.blind_disposition_ui)"
            }
        }
        if ($null -ne $config.live_accumulation) {
            try {
                $liveAccumulation = [System.Convert]::ToBoolean($config.live_accumulation)
            } catch {
                Add-Content -Path $logPath -Value "[$timestamp] invalid live_accumulation in config, using default: $($config.live_accumulation)"
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
$dualGateSupportRatioArg = $dualGateTensionSalienceSupportRatio.ToString($culture)
$episodeIndexArg = $episodeIndex.ToString($culture)

$wslIp = ((& $wslExe -u root sh -lc "hostname -I").Trim() -split "\s+")[0]
if (-not $wslIp) {
    throw "Could not determine WSL IP for Steve chat portproxy."
}

cmd /c "netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=7860" | Out-Null
cmd /c "netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=7860 connectaddress=$wslIp connectport=7860" | Out-Null
Add-Content -Path $logPath -Value "[$timestamp] portproxy -> $($wslIp):7860"
Add-Content -Path $logPath -Value "[$timestamp] chat alpha -> $alphaArg"
Add-Content -Path $logPath -Value "[$timestamp] chat model -> $qwenModelId"
Add-Content -Path $logPath -Value "[$timestamp] prompt labels -> $userLabel / $modelLabel"
Add-Content -Path $logPath -Value "[$timestamp] chat temperature -> $temperatureArg"
Add-Content -Path $logPath -Value "[$timestamp] chat episode_index -> $episodeIndexArg"
Add-Content -Path $logPath -Value "[$timestamp] chat blind_disposition_ui -> $blindDispositionUi"
Add-Content -Path $logPath -Value "[$timestamp] chat live_accumulation -> $liveAccumulation"
if ($targetLayers) {
    Add-Content -Path $logPath -Value "[$timestamp] chat target_layers -> $targetLayers"
}
Add-Content -Path $logPath -Value "[$timestamp] qdrant write mode -> $qdrantWriteMode"
Add-Content -Path $logPath -Value "[$timestamp] dual gate -> $dualGateEnabled warmup=$dualGateWarmupArg salience_q=$dualGateSalienceArg surprise_q=$dualGateSurpriseArg"
Add-Content -Path $logPath -Value "[$timestamp] supported tension attend -> $dualGateSupportedTensionEnabled ratio=$dualGateSupportRatioArg"

$dualGateSwitch = ""
if (-not $dualGateEnabled) {
    $dualGateSwitch = " --no-dual-gate"
}

$targetLayersSwitch = ""
if ($targetLayers) {
    $targetLayersSwitch = " --target-layers $(ConvertTo-BashArg $targetLayers)"
}

$supportedTensionSwitch = ""
if ($dualGateSupportedTensionEnabled) {
    $supportedTensionSwitch = " --dual-gate-supported-tension-enabled --dual-gate-tension-salience-support-ratio $dualGateSupportRatioArg"
}

$blindDispositionSwitch = ""
if ($blindDispositionUi) {
    $blindDispositionSwitch = " --blind-disposition-ui"
}

$liveAccumulationSwitch = ""
if ($liveAccumulation) {
    $liveAccumulationSwitch = " --live-accumulation"
}

$qwenModelIdArg = ConvertTo-BashArg $qwenModelId
$qdrantWriteModeArg = ConvertTo-BashArg $qdrantWriteMode
$userLabelArg = ConvertTo-BashArg $userLabel
$modelLabelArg = ConvertTo-BashArg $modelLabel

$pythonCommand = "cd /mnt/c/Users/tikii/bridge && exec /root/mocop_venv/bin/python3 -X utf8 chat_server.py --qwen-model-id $qwenModelIdArg --temperature $temperatureArg --alpha $alphaArg --episode-index $episodeIndexArg --dual-gate-warmup-turns $dualGateWarmupArg --dual-gate-salience-quantile $dualGateSalienceArg --dual-gate-surprise-quantile $dualGateSurpriseArg --qdrant-write-mode $qdrantWriteModeArg --user-label $userLabelArg --model-label $modelLabelArg --max-new-tokens 200 --host 0.0.0.0 --port 7860$dualGateSwitch$supportedTensionSwitch$targetLayersSwitch$blindDispositionSwitch$liveAccumulationSwitch"

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
