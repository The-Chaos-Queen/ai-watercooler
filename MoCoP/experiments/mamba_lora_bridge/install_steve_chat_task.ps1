$ErrorActionPreference = "Stop"

$taskName = "MoCoP Steve Chat"
$launcherPath = "C:\Users\tikii\bridge\launch_chat_windows.ps1"
$wslExe = "C:\Windows\System32\wsl.exe"
$taskUser = $env:USERNAME

try {
    & $wslExe -u root bash -lc "systemctl disable --now mocop-chat.service >/dev/null 2>&1 || true" | Out-Null
} catch {
    Write-Warning "Could not disable legacy WSL systemd service: $($_.Exception.Message)"
}

if (Get-ScheduledTask -TaskName "MoCoP WSL Keeper" -ErrorAction SilentlyContinue) {
    Disable-ScheduledTask -TaskName "MoCoP WSL Keeper" | Out-Null
}

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    try {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Out-Null
    } catch {
    }
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$launcherPath`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUser
$principal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
