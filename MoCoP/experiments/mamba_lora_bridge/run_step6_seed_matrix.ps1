[CmdletBinding()]
param(
    [string]$User = "root",
    [Parameter(Mandatory = $true)]
    [string]$RemoteHost,
    [int]$Port = 22,
    [string]$RepoRoot = "/workspace/bridge",
    [string]$RunRoot = "/workspace/mocop_step6_runs",
    [string[]]$Seeds = @("7", "42", "1337"),
    [string]$RunSetId = $(Get-Date -Format "yyyyMMddTHHmmss"),
    [Parameter(Mandatory = $true)]
    [string]$TrainCommandTemplate,
    [string]$EvalCommandTemplate = "",
    [string]$PanelPath = "MoCoP/experiments/mamba_lora_bridge/step6_eval_panel.json",
    [switch]$Execute
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Expand-Template {
    param(
        [Parameter(Mandatory = $true)][string]$Template,
        [Parameter(Mandatory = $true)][hashtable]$Values
    )

    $result = $Template
    foreach ($key in $Values.Keys) {
        $result = $result.Replace($key, $Values[$key])
    }
    return $result
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$stagingRoot = Join-Path $scriptDir ("run_reincarnation\step6_seed_matrix_" + $RunSetId)
New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null

$normalizedRepoRoot = $RepoRoot.TrimEnd("/")
$normalizedRunRoot = $RunRoot.TrimEnd("/")
$panelRemotePath = "$normalizedRepoRoot/$PanelPath"
$target = "$User@$RemoteHost"
$scpBase = @()
$sshBase = @("-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new")
if ($Port -ne 22) {
    $scpBase += @("-P", "$Port")
    $sshBase += @("-p", "$Port")
}

$manifest = @()

foreach ($seed in $Seeds) {
    $seedName = "seed_$seed"
    $remoteDir = "$normalizedRunRoot/$RunSetId/$seedName"
    $trainLog = "$remoteDir/train.log"
    $evalLog = "$remoteDir/eval.log"

    $localSeedDir = Join-Path $stagingRoot $seedName
    New-Item -ItemType Directory -Force -Path $localSeedDir | Out-Null

    $values = @{
        "{seed}"      = "$seed"
        "{run_dir}"   = $remoteDir
        "{train_log}" = $trainLog
        "{eval_log}"  = $evalLog
        "{panel}"     = $panelRemotePath
    }

    $trainCommand = Expand-Template -Template $TrainCommandTemplate -Values $values
    $evalCommand = ""
    if ($EvalCommandTemplate) {
        $evalCommand = Expand-Template -Template $EvalCommandTemplate -Values $values
    }

    $trainScriptPath = Join-Path $localSeedDir "train.sh"
    $evalScriptPath = Join-Path $localSeedDir "eval.sh"

    $trainScript = @"
#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$remoteDir"
cd "$normalizedRepoRoot"
$trainCommand
"@
    Set-Content -Path $trainScriptPath -Value $trainScript -Encoding UTF8

    if ($evalCommand) {
        $evalScript = @"
#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$remoteDir"
cd "$normalizedRepoRoot"
$evalCommand
"@
        Set-Content -Path $evalScriptPath -Value $evalScript -Encoding UTF8
    }

    $manifest += [pscustomobject]@{
        seed              = [int]$seed
        run_set_id        = $RunSetId
        remote_dir        = $remoteDir
        train_log         = $trainLog
        eval_log          = $evalLog
        panel_path        = $panelRemotePath
        local_train_script = $trainScriptPath
        local_eval_script  = if ($evalCommand) { $evalScriptPath } else { $null }
    }

    if ($Execute) {
        & scp @scpBase $trainScriptPath "$target:$remoteDir/train.sh"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to copy train.sh for seed $seed"
        }

        if ($evalCommand) {
            & scp @scpBase $evalScriptPath "$target:$remoteDir/eval.sh"
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to copy eval.sh for seed $seed"
            }
        }

        $launchCmd = "mkdir -p '$remoteDir' && chmod +x '$remoteDir/train.sh' && cd '$remoteDir' && nohup ./train.sh > '$trainLog' 2>&1 < /dev/null & echo started seed=$seed log=$trainLog"
        & ssh @sshBase $target $launchCmd
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to launch seed $seed on $RemoteHost"
        }
    }
}

$manifestPath = Join-Path $stagingRoot "manifest.json"
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "Step 6 seed matrix staged at $stagingRoot" -ForegroundColor Green
Write-Host "Manifest: $manifestPath" -ForegroundColor Green
if (-not $Execute) {
    Write-Host "Preview only. Re-run with -Execute to copy train/eval scripts to the remote host and launch train.sh per seed." -ForegroundColor Yellow
}
