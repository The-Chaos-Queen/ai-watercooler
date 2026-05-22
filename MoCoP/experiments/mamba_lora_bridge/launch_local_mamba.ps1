[CmdletBinding()]
param(
    [string]$Distro = "Debian",

    [string]$WslUser = "root",

    [ValidateSet("generate", "probe", "latent")]
    [string]$Mode = "generate",

    [string]$ModelId = "state-spaces/mamba2-370m",

    [string]$Prompt,

    [int]$MaxNewTokens = 96,

    [double]$Temperature = 0.7,

    [double]$TopP = 0.9,

    [switch]$ListPresets,

    [switch]$TrustRemoteCode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $scriptDir "local-wsl.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing local runner: $runner"
}

switch ($Mode) {
    "generate" {
        $pythonArgs = @()
        if ($ListPresets) {
            $pythonArgs += "--list-presets"
        } else {
            $pythonArgs += @(
                "--model-id", $ModelId,
                "--max-new-tokens", "$MaxNewTokens",
                "--temperature", "$Temperature",
                "--top-p", "$TopP"
            )
            if ($Prompt) {
                $pythonArgs += @("--prompt", $Prompt)
            }
            if ($TrustRemoteCode) {
                $pythonArgs += "--trust-remote-code"
            }
        }
        & $runner -Distro $Distro -WslUser $WslUser -BridgePythonFile "local_mamba_runner.py" -PythonArgs $pythonArgs
    }
    "probe" {
        $pythonArgs = @("--model-id", $ModelId)
        & $runner -Distro $Distro -WslUser $WslUser -BridgePythonFile "probe_mamba3.py" -PythonArgs $pythonArgs
    }
    "latent" {
        $pythonArgs = @(
            "--max-new", "$MaxNewTokens"
        )
        if ($Prompt) {
            $pythonArgs += @("--prompt", $Prompt)
        }
        & $runner -Distro $Distro -WslUser $WslUser -BridgePythonFile "mamba_latent_reasoning/run.py" -PythonArgs $pythonArgs
    }
    default {
        throw "Unsupported mode: $Mode"
    }
}
