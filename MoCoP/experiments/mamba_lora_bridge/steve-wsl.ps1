[CmdletBinding(DefaultParameterSetName = "Run")]
param(
    [string]$RemoteHost = "steve",

    [int]$Port = 22,

    [string]$WslUser = "root",

    [string]$BridgeDir = "/mnt/c/Users/tikii/bridge",

    [string]$PythonBin = "/root/mocop_venv/bin/python3",

    [Parameter(ParameterSetName = "Run", Mandatory = $true)]
    [string]$Run,

    [Parameter(ParameterSetName = "RunFile", Mandatory = $true)]
    [string]$RunFile,

    [Parameter(ParameterSetName = "BridgePythonFile", Mandatory = $true)]
    [string]$BridgePythonFile,

    [Parameter(ParameterSetName = "Tail", Mandatory = $true)]
    [string]$TailLog,

    [Parameter(ParameterSetName = "Grep", Mandatory = $true)]
    [string]$GrepLog,

    [Parameter(ParameterSetName = "Grep", Mandatory = $true)]
    [string]$Pattern,

    [string[]]$PythonArgs = @(),

    [ValidateRange(1, 20000)]
    [int]$Lines = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Escape-BashSingleQuoted {
    param([Parameter(Mandatory = $true)][string]$Value)
    $replacement = ("'", '"', "'", '"', "'") -join ""
    return ($Value -replace "'", $replacement)
}

function Convert-ToLf {
    param([Parameter(Mandatory = $true)][string]$Text)
    return ($Text -replace "`r`n", "`n" -replace "`r", "`n")
}

function Invoke-RemoteWslBash {
    param([Parameter(Mandatory = $true)][string]$ScriptText)

    $target = $RemoteHost
    $sshArgs = [System.Collections.Generic.List[string]]::new()
    if ($Port -ne 22) {
        $null = $sshArgs.Add("-p")
        $null = $sshArgs.Add("$Port")
    }
    foreach ($arg in @($target, "wsl", "-u", $WslUser, "bash", "-se")) {
        $null = $sshArgs.Add($arg)
    }

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = "ssh"
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $quotedArgs = foreach ($arg in $sshArgs) {
        if ($arg -match '\s') {
            '"' + ($arg -replace '"', '\"') + '"'
        } else {
            $arg
        }
    }
    $psi.Arguments = $quotedArgs -join " "

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi
    $null = $process.Start()

    $normalized = Convert-ToLf -Text $ScriptText
    $process.StandardInput.Write($normalized)
    if (-not $normalized.EndsWith("`n")) {
        $process.StandardInput.Write("`n")
    }
    $process.StandardInput.Close()

    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    if ($stdout) {
        [Console]::Out.Write($stdout)
    }
    if ($stderr) {
        [Console]::Error.Write($stderr)
    }

    if ($process.ExitCode -ne 0) {
        throw "Remote command failed with exit code $($process.ExitCode)."
    }
}

function Join-BashArgs {
    param([string[]]$Values)

    if (-not $Values -or $Values.Count -eq 0) {
        return ""
    }

    $escaped = foreach ($value in $Values) {
        "'" + (Escape-BashSingleQuoted -Value $value) + "'"
    }
    return " " + ($escaped -join " ")
}

$scriptBody = switch ($PSCmdlet.ParameterSetName) {
    "Run" {
        @"
set -euo pipefail
$Run
"@
    }
    "RunFile" {
        if (-not (Test-Path -LiteralPath $RunFile)) {
            throw "RunFile not found: $RunFile"
        }
        $fileText = Convert-ToLf -Text (Get-Content -Raw -LiteralPath $RunFile)
        @"
set -euo pipefail
$fileText
"@
    }
    "BridgePythonFile" {
        $safeBridgeDir = Escape-BashSingleQuoted -Value $BridgeDir
        $safePythonBin = Escape-BashSingleQuoted -Value $PythonBin
        $scriptPath = $BridgePythonFile
        if (-not [System.IO.Path]::IsPathRooted($scriptPath)) {
            $scriptPath = "$BridgeDir/$BridgePythonFile"
        }
        $scriptPath = $scriptPath -replace "\\", "/"
        $safeScriptPath = Escape-BashSingleQuoted -Value $scriptPath
        $argText = Join-BashArgs -Values $PythonArgs
        @"
set -euo pipefail
cd '$safeBridgeDir'
exec '$safePythonBin' -X utf8 '$safeScriptPath'$argText
"@
    }
    "Tail" {
        $safePath = Escape-BashSingleQuoted -Value $TailLog
        @"
set -euo pipefail
tail -n $Lines '$safePath'
"@
    }
    "Grep" {
        $safePath = Escape-BashSingleQuoted -Value $GrepLog
        $safePattern = Escape-BashSingleQuoted -Value $Pattern
        @"
set -euo pipefail
grep -nE '$safePattern' '$safePath' | tail -n $Lines || true
"@
    }
    default {
        throw "Unsupported parameter set: $($PSCmdlet.ParameterSetName)"
    }
}

Invoke-RemoteWslBash -ScriptText $scriptBody
