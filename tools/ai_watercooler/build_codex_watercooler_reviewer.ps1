param(
    [string]$PolicyPath = "",
    [switch]$Bootstrap
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$toolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $PolicyPath) {
    $PolicyPath = Join-Path $toolDir "codex_watercooler_dispatch_policy.json"
}
$PolicyPath = [System.IO.Path]::GetFullPath($PolicyPath)
$dockerfile = [System.IO.Path]::GetFullPath(
    (Join-Path $toolDir "Dockerfile.codex-watercooler-reviewer")
)
$policy = Get-Content -LiteralPath $PolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ($policy.worker_backend -ne "wsl_docker") {
    throw "Policy worker_backend must be wsl_docker."
}
if (-not "$($policy.wsl_distribution)".Trim() -or -not "$($policy.docker_image)".Trim()) {
    throw "Policy is missing the WSL distribution or Docker image."
}

function Convert-ToWslPath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full -notmatch '^([A-Za-z]):\\(.*)$') {
        throw "Only absolute Windows drive paths can be mounted: $full"
    }
    $drive = $Matches[1].ToLowerInvariant()
    $rest = $Matches[2].Replace('\', '/')
    return "/mnt/$drive/$rest"
}

$dockerfileWsl = Convert-ToWslPath $dockerfile
$contextWsl = Convert-ToWslPath $toolDir
$wslArgs = @(
    "-d", "$($policy.wsl_distribution)", "--exec",
    "docker", "build", "--pull=false", "--provenance=false",
    "--build-arg", "CODEX_VERSION=$($policy.codex_cli_version)",
    "--file", $dockerfileWsl,
    "--tag", "$($policy.docker_image)",
    $contextWsl
)

& wsl.exe @wslArgs
if ($LASTEXITCODE -ne 0) {
    throw "Docker reviewer image build failed with exit code $LASTEXITCODE."
}

$imageId = (& wsl.exe -d "$($policy.wsl_distribution)" --exec docker image inspect `
    --format '{{.Id}}' "$($policy.docker_image)").Trim()
if ($LASTEXITCODE -ne 0 -or $imageId -notmatch '^sha256:[0-9a-f]{64}$') {
    throw "Could not resolve the built reviewer image ID."
}
$version = (& wsl.exe -d "$($policy.wsl_distribution)" --exec docker run --rm `
    --network none --read-only --cap-drop ALL $imageId --version).Trim()
if ($LASTEXITCODE -ne 0 -or $version -ne "codex-cli $($policy.codex_cli_version)") {
    throw "Built image has unexpected Codex version: $version"
}
$null = & wsl.exe -d "$($policy.wsl_distribution)" --exec docker run --rm `
    --network none --read-only --cap-drop ALL --entrypoint /bin/sh $imageId `
    -c "test -s /etc/ssl/certs/ca-certificates.crt"
if ($LASTEXITCODE -ne 0) {
    throw "Built image is missing the system CA certificate bundle."
}

$zeroId = "sha256:" + ("0" * 64)
if (-not $Bootstrap -and $policy.docker_image_id -ne $imageId) {
    throw "Built image ID $imageId does not match policy $($policy.docker_image_id)."
}
if ($policy.docker_image_id -eq $zeroId -and -not $Bootstrap) {
    throw "Policy contains the bootstrap image ID; rerun with -Bootstrap and pin the printed ID."
}

Write-Host "Reviewer image: $($policy.docker_image)"
Write-Host "Codex version: $version"
Write-Host "Image ID: $imageId"
if ($Bootstrap -or $policy.docker_image_id -eq $zeroId) {
    Write-Host "Pin this exact Image ID in codex_watercooler_dispatch_policy.json before installation."
}
