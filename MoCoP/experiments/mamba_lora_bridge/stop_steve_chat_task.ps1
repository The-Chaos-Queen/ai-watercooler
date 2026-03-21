$ErrorActionPreference = "Stop"

$taskName = "MoCoP Steve Chat"
$wslExe = "C:\Windows\System32\wsl.exe"

try {
    & $wslExe -u root bash -lc "pkill -INT -f 'chat_server.py' >/dev/null 2>&1 || true" | Out-Null
    Start-Sleep -Seconds 3
} catch {
    Write-Warning "Could not send SIGINT to chat_server.py: $($_.Exception.Message)"
}

try {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Out-Null
} catch {
}
