$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$bridgeDir = "C:\Users\tikii\bridge"
$logDir = Join-Path $bridgeDir "logs"
$logPath = Join-Path $logDir "steve_chat_windows_task.log"
$wslExe = "C:\Windows\System32\wsl.exe"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestamp] starting MoCoP Steve chat task"

$wslIp = ((& $wslExe -u root sh -lc "hostname -I").Trim() -split "\s+")[0]
if (-not $wslIp) {
    throw "Could not determine WSL IP for Steve chat portproxy."
}

cmd /c "netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=7860" | Out-Null
cmd /c "netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=7860 connectaddress=$wslIp connectport=7860" | Out-Null
Add-Content -Path $logPath -Value "[$timestamp] portproxy -> $wslIp:7860"

$wslArgs = @(
    "-u", "root",
    "bash", "-lc",
    "cd /mnt/c/Users/tikii/bridge && exec /root/mocop_venv/bin/python3 -X utf8 chat_server.py --temperature 0.7 --max-new-tokens 200 --host 0.0.0.0 --port 7860"
)

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $wslExe @wslArgs *>> $logPath
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestamp] chat task exited with code $exitCode"
exit $exitCode
