param(
    [double]$Alpha = 0.2,
    [double]$Temperature = 0.0,
    [string]$QwenModelId = "Qwen/Qwen2.5-1.5B",
    [string]$BridgePath = "cheese_reincarnation_bridge_1.5b_codexfix.pt"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$bridgeDir = "C:\Users\tikii\bridge"
$logDir = Join-Path $bridgeDir "logs"
$wslExe = "C:\Windows\System32\wsl.exe"
$stopScriptPath = Join-Path $bridgeDir "stop_steve_chat_task.ps1"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir "steve_midnight_recorder_$timestamp.log"
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$alphaText = $Alpha.ToString($culture)
$temperatureText = $Temperature.ToString($culture)

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (Test-Path $stopScriptPath) {
    & $stopScriptPath
}

$timestampIso = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestampIso] starting Steve midnight recorder alpha=$alphaText temperature=$temperatureText model=$QwenModelId"

$wslArgs = @(
    "-u", "root",
    "bash", "-lc",
    "cd /mnt/c/Users/tikii/bridge && exec /root/mocop_venv/bin/python3 -X utf8 step5d_bridge_recorder.py --bridge-path $BridgePath --qwen-model-id $QwenModelId --temperature $temperatureText --alpha $alphaText --output-dir /mnt/c/Users/tikii/bridge/bridge_recorder_runs"
)

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $wslExe @wslArgs *>> $logPath
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference

$timestampIso = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestampIso] Steve midnight recorder exited with code $exitCode"
exit $exitCode
