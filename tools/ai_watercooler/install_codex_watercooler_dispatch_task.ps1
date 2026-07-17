param(
    [string]$TaskName = "AI Watercooler Codex Review Dispatcher",
    [string]$PolicyPath = "",
    [int]$EveryMinutes = 2,
    [int]$TimeoutSeconds = 3600,
    [int]$MaxAttempts = 2,
    [int]$RetryBaseSeconds = 300,
    [switch]$SkipPrime
)

$ErrorActionPreference = "Stop"

if ($EveryMinutes -lt 1 -or $EveryMinutes -gt 1439) {
    throw "EveryMinutes must be between 1 and 1439."
}
if ($TimeoutSeconds -lt 60 -or $TimeoutSeconds -gt 7200) {
    throw "TimeoutSeconds must be between 60 and 7200."
}

$runner = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "run_codex_watercooler_dispatch.ps1"
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "Missing runner script: $runner"
}
$hiddenLauncher = Join-Path (Split-Path -Parent $runner) "run_codex_watercooler_dispatch_hidden.vbs"
if (-not (Test-Path -LiteralPath $hiddenLauncher -PathType Leaf)) {
    throw "Missing silent task launcher: $hiddenLauncher"
}
if (-not $PolicyPath) {
    $PolicyPath = Join-Path (Split-Path -Parent $runner) "codex_watercooler_dispatch_policy.json"
}
$PolicyPath = [System.IO.Path]::GetFullPath($PolicyPath)
if ($runner.Contains('"') -or $hiddenLauncher.Contains('"') -or $PolicyPath.Contains('"')) {
    throw "Task paths may not contain a double quote."
}

& $runner -PolicyPath $PolicyPath -TimeoutSeconds $TimeoutSeconds `
    -MaxAttempts $MaxAttempts -RetryBaseSeconds $RetryBaseSeconds -CheckRuntime

if (-not $SkipPrime) {
    & $runner -PolicyPath $PolicyPath -TimeoutSeconds $TimeoutSeconds `
        -MaxAttempts $MaxAttempts -RetryBaseSeconds $RetryBaseSeconds -Prime
}

$wscript = (Get-Command wscript.exe -ErrorAction Stop).Source
$argumentLine = @(
    "//B",
    "//NoLogo",
    "`"$hiddenLauncher`"",
    "`"$runner`"",
    "`"$PolicyPath`"",
    "$TimeoutSeconds",
    "$MaxAttempts",
    "$RetryBaseSeconds"
) -join " "

$action = New-ScheduledTaskAction -Execute $wscript -Argument $argumentLine `
    -WorkingDirectory (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $runner)))
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Seconds ($TimeoutSeconds + 300)) `
    -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $currentUser `
    -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings `
    -Principal $taskPrincipal -Description (
        "Polls strict codex-review/v1 requests and runs a bounded host-isolated Codex commit review."
    )

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
$registered = Get-ScheduledTask -TaskName $TaskName
Write-Host "Registered '$TaskName' for $currentUser every $EveryMinutes minute(s)."
Write-Host "MultipleInstances=$($registered.Settings.MultipleInstances); ExecutionTimeLimit=$($registered.Settings.ExecutionTimeLimit)."
Write-Host "The task runs only in the current interactive user session through a no-window wscript launcher."
Write-Host "Disable: Disable-ScheduledTask -TaskName `"$TaskName`""
Write-Host "Delete: Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false"
