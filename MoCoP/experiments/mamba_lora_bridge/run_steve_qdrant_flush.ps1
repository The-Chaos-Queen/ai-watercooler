param(
    [int]$MaxItems = 100
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$bridgeDir = "C:\Users\tikii\bridge"
$logDir = Join-Path $bridgeDir "logs"
$scriptPath = Join-Path $bridgeDir "flush_qdrant_pending.py"
$pendingPath = Join-Path $bridgeDir "qdrant_gate_pending.jsonl"
$archivePath = Join-Path $bridgeDir "qdrant_gate_flushed.jsonl"
$wslExe = "C:\Windows\System32\wsl.exe"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir "steve_qdrant_flush_$timestamp.log"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestampIso = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestampIso] starting Steve qdrant flush max_items=$MaxItems"

$wslArgs = @(
    "-u", "root",
    "bash", "-lc",
    "cd /mnt/c/Users/tikii/bridge && exec /root/mocop_venv/bin/python3 -X utf8 flush_qdrant_pending.py --pending-path /mnt/c/Users/tikii/bridge/qdrant_gate_pending.jsonl --archive-path /mnt/c/Users/tikii/bridge/qdrant_gate_flushed.jsonl --qdrant-host 192.168.2.191 --qdrant-port 6333 --qdrant-collection exocortex --qdrant-embedding-model all-MiniLM-L6-v2 --max-items $MaxItems --json"
)

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $wslExe @wslArgs *>> $logPath
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference

$timestampIso = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
Add-Content -Path $logPath -Value "[$timestampIso] Steve qdrant flush exited with code $exitCode"
exit $exitCode
