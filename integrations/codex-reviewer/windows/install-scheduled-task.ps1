param(
    [string]$TaskName = "Watercooler Commit Review Dispatcher",
    [Parameter(Mandatory = $true)]
    [string]$PolicyPath,
    [Parameter(Mandatory = $true)]
    [string]$ConfigPath,
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,
    [Parameter(Mandatory = $true)]
    [string]$SchemaPath,
    [Parameter(Mandatory = $true)]
    [string]$CodexAuthFile,
    [string]$PythonExe = "python",
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

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "run-dispatcher.ps1"))
$hiddenLauncher = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "run-hidden.vbs"))
$PolicyPath = [System.IO.Path]::GetFullPath($PolicyPath)
$ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$SchemaPath = [System.IO.Path]::GetFullPath($SchemaPath)
$CodexAuthFile = [System.IO.Path]::GetFullPath($CodexAuthFile)

foreach ($path in @(
    $runner, $hiddenLauncher, $PolicyPath, $ConfigPath, $RepoRoot,
    $SchemaPath, $CodexAuthFile, $PythonExe
)) {
    if ($path.Contains('"')) {
        throw "Scheduled-task paths may not contain a double quote."
    }
}

& $runner -PolicyPath $PolicyPath -ConfigPath $ConfigPath -RepoRoot $RepoRoot `
    -SchemaPath $SchemaPath -CodexAuthFile $CodexAuthFile -PythonExe $PythonExe `
    -TimeoutSeconds $TimeoutSeconds -MaxAttempts $MaxAttempts `
    -RetryBaseSeconds $RetryBaseSeconds -CheckRuntime
if (-not $SkipPrime) {
    & $runner -PolicyPath $PolicyPath -ConfigPath $ConfigPath -RepoRoot $RepoRoot `
        -SchemaPath $SchemaPath -CodexAuthFile $CodexAuthFile -PythonExe $PythonExe `
        -TimeoutSeconds $TimeoutSeconds -MaxAttempts $MaxAttempts `
        -RetryBaseSeconds $RetryBaseSeconds -Prime
}

$wscript = (Get-Command wscript.exe -ErrorAction Stop).Source
$argumentLine = @(
    "//B", "//NoLogo", "`"$hiddenLauncher`"", "`"$runner`"",
    "`"$PolicyPath`"", "`"$ConfigPath`"", "`"$RepoRoot`"",
    "`"$SchemaPath`"", "`"$CodexAuthFile`"", "`"$PythonExe`"",
    "$TimeoutSeconds", "$MaxAttempts", "$RetryBaseSeconds"
) -join " "

$action = New-ScheduledTaskAction -Execute $wscript -Argument $argumentLine `
    -WorkingDirectory $RepoRoot
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
        "Polls strict commit-review/v1 requests and runs bounded isolated commit reviews."
    )

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
Write-Output "Registered '$TaskName' for $currentUser every $EveryMinutes minute(s)."
Write-Output "Disable: Disable-ScheduledTask -TaskName `"$TaskName`""
Write-Output "Delete: Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false"
