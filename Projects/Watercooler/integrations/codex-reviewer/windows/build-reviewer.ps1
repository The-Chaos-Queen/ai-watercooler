param(
    [Parameter(Mandatory = $true)]
    [string]$PolicyPath,
    [switch]$Bootstrap
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$integrationDir = Split-Path -Parent $scriptDir
$dockerfile = [System.IO.Path]::GetFullPath((Join-Path $integrationDir "Dockerfile"))
$PolicyPath = [System.IO.Path]::GetFullPath($PolicyPath)

if (-not (Test-Path -LiteralPath $PolicyPath -PathType Leaf)) {
    throw "Policy file not found: $PolicyPath"
}
if (-not (Test-Path -LiteralPath $dockerfile -PathType Leaf)) {
    throw "Dockerfile not found: $dockerfile"
}

$policy = Get-Content -LiteralPath $PolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($policy.worker_backend -notin @("docker", "wsl_docker")) {
    throw "Policy worker_backend must be docker or wsl_docker."
}
if ($policy.worker_backend -eq "wsl_docker" -and -not "$($policy.wsl_distribution)".Trim()) {
    throw "wsl_docker requires a WSL distribution."
}
if (-not "$($policy.docker_image)".Trim() -or -not "$($policy.codex_cli_version)".Trim()) {
    throw "Policy is missing the Docker image or Codex CLI version."
}

function Convert-ContainerHostPath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($policy.worker_backend -eq "docker") {
        return $full
    }
    if ($full -notmatch '^([A-Za-z]):\\(.*)$') {
        throw "WSL Docker can mount only absolute Windows drive paths: $full"
    }
    $drive = $Matches[1].ToLowerInvariant()
    $rest = $Matches[2].Replace('\', '/')
    return "/mnt/$drive/$rest"
}

function Invoke-PolicyDocker([string[]]$Arguments) {
    if ($policy.worker_backend -eq "docker") {
        & docker @Arguments
    } else {
        & wsl.exe -d "$($policy.wsl_distribution)" --exec docker @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed with exit code $LASTEXITCODE."
    }
}

$dockerfileHost = Convert-ContainerHostPath $dockerfile
$contextHost = Convert-ContainerHostPath $integrationDir
Invoke-PolicyDocker @(
    "build", "--pull=false", "--provenance=false",
    "--build-arg", "CODEX_VERSION=$($policy.codex_cli_version)",
    "--file", $dockerfileHost,
    "--tag", "$($policy.docker_image)",
    $contextHost
)

$imageId = (Invoke-PolicyDocker @(
    "image", "inspect", "--format", "{{.Id}}", "$($policy.docker_image)"
)).Trim()
if ($imageId -notmatch '^sha256:[0-9a-f]{64}$') {
    throw "Could not resolve the built reviewer image ID."
}
$version = (Invoke-PolicyDocker @(
    "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
    $imageId, "--version"
)).Trim()
if ($version -ne "codex-cli $($policy.codex_cli_version)") {
    throw "Built image has unexpected Codex version: $version"
}
Invoke-PolicyDocker @(
    "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
    "--entrypoint", "/bin/sh", $imageId,
    "-c", "test -s /etc/ssl/certs/ca-certificates.crt"
) | Out-Null

$zeroId = "sha256:" + ("0" * 64)
if (-not $Bootstrap -and $policy.docker_image_id -eq $zeroId) {
    throw "Policy contains the bootstrap image ID. Pin the built ID before runtime use."
}
if (-not $Bootstrap -and $policy.docker_image_id -ne $imageId) {
    throw "Built image ID $imageId does not match policy $($policy.docker_image_id)."
}

Write-Output "Reviewer image: $($policy.docker_image)"
Write-Output "Codex version: $version"
Write-Output "Image ID: $imageId"
if ($Bootstrap) {
    Write-Output "Copy the example policy outside the repository and pin this exact Image ID."
}
