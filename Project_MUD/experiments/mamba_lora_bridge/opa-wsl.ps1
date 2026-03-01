[CmdletBinding(DefaultParameterSetName = "Run")]
param(
    [Parameter(Mandatory = $true)]
    [string]$User,

    [string]$Host = "192.168.2.194",

    [int]$Port = 22,

    [Parameter(ParameterSetName = "Run", Mandatory = $true)]
    [string]$Run,

    [Parameter(ParameterSetName = "RunFile", Mandatory = $true)]
    [string]$RunFile,

    [Parameter(ParameterSetName = "Tail", Mandatory = $true)]
    [string]$TailLog,

    [Parameter(ParameterSetName = "Grep", Mandatory = $true)]
    [string]$GrepLog,

    [Parameter(ParameterSetName = "Grep", Mandatory = $true)]
    [string]$Pattern,

    [ValidateRange(1, 20000)]
    [int]$Lines = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Escape-BashSingleQuoted {
    param([Parameter(Mandatory = $true)][string]$Value)
    return ($Value -replace "'", "'\"'\"'")
}

function Invoke-RemoteWslBash {
    param([Parameter(Mandatory = $true)][string]$ScriptText)

    $target = "$User@$Host"
    $sshArgs = @()
    if ($Port -ne 22) {
        $sshArgs += @("-p", "$Port")
    }
    $sshArgs += @($target, "wsl", "bash", "-se")

    $ScriptText | & ssh @sshArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Remote command failed with exit code $LASTEXITCODE."
    }
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
        $fileText = Get-Content -Raw -LiteralPath $RunFile
        @"
set -euo pipefail
$fileText
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
