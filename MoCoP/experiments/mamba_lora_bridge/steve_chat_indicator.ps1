$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class SteveChatNativeMethods {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern bool DestroyIcon(IntPtr handle);
}
"@

$indicatorMutexCreated = $false
$indicatorMutex = New-Object System.Threading.Mutex($true, "Local\MoCoP.SteveChatIndicator", [ref]$indicatorMutexCreated)
if (-not $indicatorMutexCreated) {
    exit 0
}

$bridgeDir = "C:\Users\tikii\bridge"
$configPath = Join-Path $bridgeDir "steve_chat_config.json"
$logPath = Join-Path $bridgeDir "logs\steve_chat_windows_task.log"
$chatTaskName = "MoCoP Steve Chat"
$pollUrl = "http://127.0.0.1:7860/status"
$openUrl = "http://192.168.2.49:7860/"

function New-SteeringIcon {
    param(
        [string]$BulbColor,
        [string]$BaseColor = "#5a6170"
    )

    $bitmap = New-Object System.Drawing.Bitmap 16, 16
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.Clear([System.Drawing.Color]::Transparent)

    $bulbBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml($BulbColor))
    $baseBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml($BaseColor))
    $outlinePen = New-Object System.Drawing.Pen ([System.Drawing.ColorTranslator]::FromHtml("#1f2430"), 1)

    $graphics.FillEllipse($bulbBrush, 2, 1, 12, 10)
    $graphics.DrawEllipse($outlinePen, 2, 1, 12, 10)
    $graphics.FillRectangle($baseBrush, 5, 9, 6, 4)
    $graphics.FillRectangle($baseBrush, 6, 13, 4, 2)
    $graphics.DrawRectangle($outlinePen, 5, 9, 6, 4)
    $graphics.DrawRectangle($outlinePen, 6, 13, 4, 2)

    $handle = $bitmap.GetHicon()
    $icon = [System.Drawing.Icon]::FromHandle($handle).Clone()
    [SteveChatNativeMethods]::DestroyIcon($handle) | Out-Null

    $outlinePen.Dispose()
    $baseBrush.Dispose()
    $bulbBrush.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()

    return $icon
}

function Read-SteeringConfig {
    $result = @{
        alpha = "0.2"
        qwen_model_id = "Qwen/Qwen2.5-1.5B"
        temperature = "0.7"
    }

    if (-not (Test-Path $configPath)) {
        return $result
    }

    try {
        $config = Get-Content -Path $configPath -Raw | ConvertFrom-Json
        if ($null -ne $config.alpha -and "$($config.alpha)".Trim()) {
            $result.alpha = "$($config.alpha)".Trim()
        }
        if ($null -ne $config.qwen_model_id -and "$($config.qwen_model_id)".Trim()) {
            $result.qwen_model_id = "$($config.qwen_model_id)".Trim()
        }
        if ($null -ne $config.temperature -and "$($config.temperature)".Trim()) {
            $result.temperature = "$($config.temperature)".Trim()
        }
    } catch {
    }

    return $result
}

function Get-SteeringStatus {
    $config = Read-SteeringConfig
    $taskState = "Unknown"
    try {
        $taskState = (Get-ScheduledTask -TaskName $chatTaskName -ErrorAction Stop).State.ToString()
    } catch {
    }

    $healthy = $false
    $busy = $false
    $statusLabel = "offline"
    $lastError = ""

    try {
        $resp = Invoke-RestMethod -Uri $pollUrl -Method Get -TimeoutSec 3
        if ($resp.running -and -not $resp.stop_requested) {
            $healthy = $true
            $busy = [bool]$resp.busy
            $statusLabel = if ($busy) { "active | busy" } else { "active" }
            if ($resp.last_error) {
                $lastError = "$($resp.last_error)"
            }
        } elseif ($resp.stop_requested) {
            $statusLabel = "stopping"
        }
    } catch {
        if ($taskState -eq "Running") {
            $statusLabel = "starting"
        }
    }

    return @{
        healthy = $healthy
        busy = $busy
        statusLabel = $statusLabel
        taskState = $taskState
        alpha = $config.alpha
        qwen_model_id = $config.qwen_model_id
        temperature = $config.temperature
        lastError = $lastError
    }
}

$greenIcon = New-SteeringIcon -BulbColor "#51d26d"
$redIcon = New-SteeringIcon -BulbColor "#d45858"

$contextMenu = New-Object System.Windows.Forms.ContextMenuStrip
$statusItem = New-Object System.Windows.Forms.ToolStripMenuItem
$statusItem.Enabled = $false
$contextMenu.Items.Add($statusItem) | Out-Null
$contextMenu.Items.Add("-") | Out-Null

$openItem = New-Object System.Windows.Forms.ToolStripMenuItem "Open Chat"
$openItem.Add_Click({ Start-Process $openUrl })
$contextMenu.Items.Add($openItem) | Out-Null

$startItem = New-Object System.Windows.Forms.ToolStripMenuItem "Start Chat"
$startItem.Add_Click({
    try {
        Start-ScheduledTask -TaskName $chatTaskName | Out-Null
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Could not start MoCoP Steve Chat.`n$($_.Exception.Message)", "MoCoP", "OK", "Error") | Out-Null
    }
})
$contextMenu.Items.Add($startItem) | Out-Null

$stopItem = New-Object System.Windows.Forms.ToolStripMenuItem "Stop Chat"
$stopItem.Add_Click({
    try {
        & (Join-Path $bridgeDir "stop_steve_chat_task.ps1")
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Could not stop MoCoP Steve Chat.`n$($_.Exception.Message)", "MoCoP", "OK", "Error") | Out-Null
    }
})
$contextMenu.Items.Add($stopItem) | Out-Null

$logItem = New-Object System.Windows.Forms.ToolStripMenuItem "Open Chat Log"
$logItem.Add_Click({
    if (Test-Path $logPath) {
        Start-Process notepad.exe $logPath
    }
})
$contextMenu.Items.Add($logItem) | Out-Null

$contextMenu.Items.Add("-") | Out-Null
$exitItem = New-Object System.Windows.Forms.ToolStripMenuItem "Exit Indicator"
$contextMenu.Items.Add($exitItem) | Out-Null

$notifyIcon = New-Object System.Windows.Forms.NotifyIcon
$notifyIcon.Visible = $true
$notifyIcon.ContextMenuStrip = $contextMenu
$notifyIcon.Text = "MoCoP Steve Chat"
$notifyIcon.Icon = $redIcon
$notifyIcon.Add_DoubleClick({ Start-Process $openUrl })

$appContext = New-Object System.Windows.Forms.ApplicationContext

function Update-Indicator {
    $status = Get-SteeringStatus
    $isHealthy = [bool]$status.healthy
    $statusText = $status.statusLabel
    $modelSuffix = $status.qwen_model_id -replace '^Qwen/', ''
    if ($modelSuffix.Length -gt 28) {
        $modelSuffix = $modelSuffix.Substring(0, 28)
    }

    $notifyIcon.Icon = if ($isHealthy) { $greenIcon } else { $redIcon }
    $notifyIcon.Text = "MoCoP: $statusText | a=$($status.alpha) | t=$($status.temperature)"
    $statusItem.Text = "Status: $statusText | task=$($status.taskState) | a=$($status.alpha) | t=$($status.temperature)"
    $openItem.Enabled = $isHealthy
    $stopItem.Enabled = ($status.taskState -eq "Running")
    $startItem.Enabled = ($status.taskState -ne "Running")
    $logItem.Enabled = (Test-Path $logPath)
}

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 5000
$timer.Add_Tick({ Update-Indicator })
$timer.Start()

$exitItem.Add_Click({
    $timer.Stop()
    $notifyIcon.Visible = $false
    $appContext.ExitThread()
})

Update-Indicator
try {
    [System.Windows.Forms.Application]::Run($appContext)
} finally {
    $timer.Stop()
    $notifyIcon.Visible = $false
    $notifyIcon.Dispose()
    $greenIcon.Dispose()
    $redIcon.Dispose()
    $indicatorMutex.ReleaseMutex() | Out-Null
    $indicatorMutex.Dispose()
}
