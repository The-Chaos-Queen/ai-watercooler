$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$bridgeDir = "C:\Users\tikii\bridge"
$logDir = Join-Path $bridgeDir "trajectory_lain_zone"
$logPath = Join-Path $logDir "trajectory_lain_zone.log"
$wslExe = "C:\Windows\System32\wsl.exe"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestamp] starting trajectory_lain_zone"

$pythonCommand = "cd /mnt/c/Users/tikii/bridge && exec /root/mocop_venv/bin/python3 -u -X utf8 trajectory_sequential.py --conversation-json lucian_conversations.json --conv-index 35 --max-messages 1670 --sample-every 50 --method tokenwise --output-dir /mnt/c/Users/tikii/bridge/trajectory_lain_zone --device cuda"

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
Add-Content -Path $logPath -Value "[$timestamp] trajectory_lain_zone exited with code $exitCode"
exit $exitCode
