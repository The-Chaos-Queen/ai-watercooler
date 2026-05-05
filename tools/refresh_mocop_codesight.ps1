param(
    [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

$mocopRoot = Join-Path $RepoRoot "MoCoP"
$codesightEntry = Join-Path $RepoRoot "tools\codesight\dist\index.js"

if (-not (Test-Path $codesightEntry)) {
    throw "CodeSight is not built at $codesightEntry. Run: cd tools\codesight; npm install"
}

if (-not (Test-Path $mocopRoot)) {
    throw "MoCoP root not found at $mocopRoot"
}

Push-Location $mocopRoot
try {
    node $codesightEntry --wiki -o .codesight
    node $codesightEntry --mode knowledge -o .codesight
}
finally {
    Pop-Location
}

Write-Host "Updated MoCoP CodeSight artifacts:"
Write-Host "  MoCoP\.codesight\wiki\index.md"
Write-Host "  MoCoP\.codesight\CODESIGHT.md"
Write-Host "  MoCoP\.codesight\KNOWLEDGE.md"
