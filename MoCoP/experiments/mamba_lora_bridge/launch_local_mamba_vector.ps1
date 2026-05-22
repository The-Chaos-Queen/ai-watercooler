[CmdletBinding()]
param(
    [string]$Distro = "Debian",

    [string]$WslUser = "root",

    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [string]$OutputDir = "C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP\experiments\mamba_lora_bridge\run_reincarnation\local_vectors",

    [string]$ModelId = "state-spaces/mamba-2.8b-hf",

    [int]$TargetLayer = 3,

    [int]$MaxTokens = 4096,

    [ValidateSet("one_shot", "rolling_chunked", "rolling_turnwise")]
    [string]$Mode = "rolling_turnwise",

    [int]$ChunkSize = 128,

    [int]$ProgressEvery = 50,

    [ValidateSet("cpu", "cuda", "auto")]
    [string]$Device = "auto"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-WindowsPathToWsl {
    param([Parameter(Mandatory = $true)][string]$PathText)

    $resolved = [System.IO.Path]::GetFullPath($PathText)
    if ($resolved -match '^(?<drive>[A-Za-z]):\\(?<rest>.*)$') {
        $drive = $Matches['drive'].ToLowerInvariant()
        $rest = ($Matches['rest'] -replace '\\', '/')
        if ([string]::IsNullOrWhiteSpace($rest)) {
            return "/mnt/$drive"
        }
        return "/mnt/$drive/$rest"
    }
    throw "Could not convert Windows path to WSL path: $resolved"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $scriptDir "local-wsl.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing local runner: $runner"
}

$resolvedInput = [System.IO.Path]::GetFullPath($InputPath)
if (-not (Test-Path -LiteralPath $resolvedInput)) {
    throw "Input file not found: $resolvedInput"
}

$resolvedOutputDir = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $resolvedOutputDir | Out-Null

$pythonArgs = @(
    "--input-path", (Convert-WindowsPathToWsl -PathText $resolvedInput),
    "--output-dir", (Convert-WindowsPathToWsl -PathText $resolvedOutputDir),
    "--model-id", $ModelId,
    "--target-layer", "$TargetLayer",
    "--max-tokens", "$MaxTokens",
    "--device", $Device,
    "--mode", $Mode,
    "--chunk-size", "$ChunkSize",
    "--progress-every-chunks", "$ProgressEvery"
)

& $runner -Distro $Distro -WslUser $WslUser -BridgePythonFile "extract_single_mamba_vector.py" -PythonArgs $pythonArgs
