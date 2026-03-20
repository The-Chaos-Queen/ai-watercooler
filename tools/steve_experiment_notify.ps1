# Run on Steve's PC before starting an experiment
# Shows a persistent desktop notification + creates a stop file he can touch

param(
    [string]$ExperimentName = "MoCoP Experiment",
    [string]$StopFile = "C:\Users\tikii\STOP_EXPERIMENT.txt"
)

# Create a visible text file on his desktop
$desktopMsg = @"
===========================================
  MOCOP EXPERIMENT RUNNING
  $ExperimentName
  Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm')

  TO STOP: Double-click STOP_EXPERIMENT.txt
  on your Desktop, or just delete this file.

  DO NOT shut down or restart the PC.
  Laura owes you dinner for this.
===========================================
"@

$desktopPath = [Environment]::GetFolderPath("Desktop")
$notifyFile = Join-Path $desktopPath "EXPERIMENT_RUNNING.txt"
$stopFilePath = Join-Path $desktopPath "STOP_EXPERIMENT.bat"

# Write the notice
Set-Content -Path $notifyFile -Value $desktopMsg
Write-Host "Notice written to: $notifyFile"

# Create stop button (batch file on desktop)
$stopScript = @"
@echo off
echo STOP requested by Steve at %DATE% %TIME% > "$StopFile"
echo Experiment stop requested. Laura will see this.
echo You can close this window.
pause
"@

Set-Content -Path $stopFilePath -Value $stopScript
Write-Host "Stop button created: $stopFilePath"

# Show toast notification
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
  <visual>
    <binding template='ToastGeneric'>
      <text>MoCoP Experiment Running</text>
      <text>$ExperimentName - Please don't shut down!</text>
    </binding>
  </visual>
</toast>
"@

try {
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("MoCoP")
    $toast.Show([Windows.UI.Notifications.ToastNotification]::new($xml))
    Write-Host "Toast notification sent."
} catch {
    Write-Host "Toast failed (non-critical): $_"
}

Write-Host "`nExperiment notice active. Steve knows."
