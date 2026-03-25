$ErrorActionPreference = "Stop"

$chatTaskName = "MoCoP Steve Chat"
$indicatorTaskName = "MoCoP Steve Chat Indicator"
$launcherPath = "C:\Users\tikii\bridge\launch_chat_windows.ps1"
$indicatorPath = "C:\Users\tikii\bridge\steve_chat_indicator.ps1"
$hiddenLauncherPath = "C:\Users\tikii\bridge\launch_hidden_powershell.vbs"
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

if (Get-ScheduledTask -TaskName $chatTaskName -ErrorAction SilentlyContinue) {
    try {
        Stop-ScheduledTask -TaskName $chatTaskName -ErrorAction SilentlyContinue | Out-Null
    } catch {
    }
}

if (Get-ScheduledTask -TaskName $indicatorTaskName -ErrorAction SilentlyContinue) {
    try {
        Stop-ScheduledTask -TaskName $indicatorTaskName -ErrorAction SilentlyContinue | Out-Null
    } catch {
    }
}

$chatAction = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "`"$hiddenLauncherPath`" `"$launcherPath`""

$indicatorAction = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "`"$hiddenLauncherPath`" `"$indicatorPath`""

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
    -TaskName $chatTaskName `
    -Action $chatAction `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Register-ScheduledTask `
    -TaskName $indicatorTaskName `
    -Action $indicatorAction `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName $indicatorTaskName
Start-ScheduledTask -TaskName $chatTaskName
