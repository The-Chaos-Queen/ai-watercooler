$taskName = "MoCoP Steve Chat"
$indicatorTaskName = "MoCoP Steve Chat Indicator"
$bridgeDir = "C:\Users\tikii\bridge"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$currentAlpha = "0.2 (default)"
$currentQwenModelId = "Qwen/Qwen2.5-7B (default)"
$currentTargetLayers = "12:v_proj,13:v_proj,14:v_proj,15:v_proj (default)"
$currentTemperature = "0.7 (default)"
$currentUserLabel = "Laura (default)"
$currentModelLabel = "Me (default)"
$currentDualGateEnabled = "true (default)"
$currentDualGateWarmupTurns = "3 (default)"
$currentDualGateSalienceQuantile = "0.75 (default)"
$currentDualGateSurpriseQuantile = "0.75 (default)"
$currentDualGateSupportedTensionEnabled = "false (default)"
$currentDualGateTensionSalienceSupportRatio = "0.55 (default)"
$currentLiveAccumulation = "false (default)"

if (Test-Path $configPath) {
    try {
        $config = Get-Content -Path $configPath -Raw | ConvertFrom-Json
        if ($null -ne $config.alpha -and "$($config.alpha)".Trim()) {
            $currentAlpha = "$($config.alpha)".Trim()
        }
        if ($null -ne $config.qwen_model_id -and "$($config.qwen_model_id)".Trim()) {
            $currentQwenModelId = "$($config.qwen_model_id)".Trim()
        }
        if ($null -ne $config.target_layers -and "$($config.target_layers)".Trim()) {
            $currentTargetLayers = "$($config.target_layers)".Trim()
        }
        if ($null -ne $config.temperature -and "$($config.temperature)".Trim()) {
            $currentTemperature = "$($config.temperature)".Trim()
        }
        if ($null -ne $config.user_label -and "$($config.user_label)".Trim()) {
            $currentUserLabel = "$($config.user_label)".Trim()
        }
        if ($null -ne $config.model_label -and "$($config.model_label)".Trim()) {
            $currentModelLabel = "$($config.model_label)".Trim()
        }
        if ($null -ne $config.dual_gate_enabled -and "$($config.dual_gate_enabled)".Trim()) {
            $currentDualGateEnabled = "$($config.dual_gate_enabled)".Trim()
        }
        if ($null -ne $config.dual_gate_warmup_turns -and "$($config.dual_gate_warmup_turns)".Trim()) {
            $currentDualGateWarmupTurns = "$($config.dual_gate_warmup_turns)".Trim()
        }
        if ($null -ne $config.dual_gate_salience_quantile -and "$($config.dual_gate_salience_quantile)".Trim()) {
            $currentDualGateSalienceQuantile = "$($config.dual_gate_salience_quantile)".Trim()
        }
        if ($null -ne $config.dual_gate_surprise_quantile -and "$($config.dual_gate_surprise_quantile)".Trim()) {
            $currentDualGateSurpriseQuantile = "$($config.dual_gate_surprise_quantile)".Trim()
        }
        if ($null -ne $config.dual_gate_supported_tension_enabled -and "$($config.dual_gate_supported_tension_enabled)".Trim()) {
            $currentDualGateSupportedTensionEnabled = "$($config.dual_gate_supported_tension_enabled)".Trim()
        }
        if ($null -ne $config.dual_gate_tension_salience_support_ratio -and "$($config.dual_gate_tension_salience_support_ratio)".Trim()) {
            $currentDualGateTensionSalienceSupportRatio = "$($config.dual_gate_tension_salience_support_ratio)".Trim()
        }
        if ($null -ne $config.live_accumulation -and "$($config.live_accumulation)".Trim()) {
            $currentLiveAccumulation = "$($config.live_accumulation)".Trim()
        }
    } catch {
        $currentAlpha = "invalid config"
        $currentQwenModelId = "invalid config"
        $currentTargetLayers = "invalid config"
        $currentTemperature = "invalid config"
        $currentUserLabel = "invalid config"
        $currentModelLabel = "invalid config"
        $currentDualGateEnabled = "invalid config"
        $currentDualGateWarmupTurns = "invalid config"
        $currentDualGateSalienceQuantile = "invalid config"
        $currentDualGateSurpriseQuantile = "invalid config"
        $currentDualGateSupportedTensionEnabled = "invalid config"
        $currentDualGateTensionSalienceSupportRatio = "invalid config"
        $currentLiveAccumulation = "invalid config"
    }
}

$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName
$indicatorState = "missing"
if (Get-ScheduledTask -TaskName $indicatorTaskName -ErrorAction SilentlyContinue) {
    $indicatorState = (Get-ScheduledTask -TaskName $indicatorTaskName).State
}

[pscustomobject]@{
    TaskName = $task.TaskName
    TaskPath = $task.TaskPath
    State = $task.State
    LastRunTime = $info.LastRunTime
    LastTaskResult = $info.LastTaskResult
    Execute = $task.Actions.Execute
    Arguments = $task.Actions.Arguments
    ConfigPath = $configPath
    CurrentAlpha = $currentAlpha
    CurrentQwenModelId = $currentQwenModelId
    CurrentTargetLayers = $currentTargetLayers
    CurrentTemperature = $currentTemperature
    CurrentUserLabel = $currentUserLabel
    CurrentModelLabel = $currentModelLabel
    CurrentDualGateEnabled = $currentDualGateEnabled
    CurrentDualGateWarmupTurns = $currentDualGateWarmupTurns
    CurrentDualGateSalienceQuantile = $currentDualGateSalienceQuantile
    CurrentDualGateSurpriseQuantile = $currentDualGateSurpriseQuantile
    CurrentDualGateSupportedTensionEnabled = $currentDualGateSupportedTensionEnabled
    CurrentDualGateTensionSalienceSupportRatio = $currentDualGateTensionSalienceSupportRatio
    CurrentLiveAccumulation = $currentLiveAccumulation
    IndicatorTaskName = $indicatorTaskName
    IndicatorState = $indicatorState
} | Format-List
