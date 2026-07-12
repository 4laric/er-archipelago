# bootstrap-ap.ps1 -- put a STOCK upstream Archipelago checkout at .\Archipelago
#
# WHY THIS IS NOT A SUBMODULE
# ---------------------------
# It used to be, and it pointed at a fork of lBedrockl/Archipelago -- 112 commits ahead of upstream,
# carrying DS3/Bedrock-lineage work. A Bedrock fork in the submodule list of a release whose entire pitch
# is "provenance-clean, no Bedrock code" is a contradiction, and it was never needed: CI proves greenfield
# runs on stock upstream Archipelago.
#
# It also does not need to be VERSION CONTROLLED at all. Nothing of ours lives in it. It is a build
# dependency -- the tree the world gets INSTALLED into so we can gen/test against exactly what a player
# runs. So: a pinned clone, gitignored, reproduced by this script.
#
# The pin lives in ONE place -- .ap-version -- read by this script AND by .github/workflows/tests.yaml,
# so the version you develop against and the version CI gates on cannot drift apart.
#
#   .\bootstrap-ap.ps1            # clone/refresh .\Archipelago at the pinned version
#   .\bootstrap-ap.ps1 -Force     # blow it away and re-clone

[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApDir = Join-Path $Repo 'Archipelago'
$Pin = (Get-Content (Join-Path $Repo '.ap-version') -Raw).Trim()
$Upstream = 'https://github.com/ArchipelagoMW/Archipelago.git'

if ($Force -and (Test-Path $ApDir)) {
    Write-Host "bootstrap-ap: removing existing $ApDir"
    Remove-Item -Recurse -Force $ApDir
}

if (-not (Test-Path $ApDir)) {
    Write-Host "bootstrap-ap: cloning stock upstream Archipelago @ $Pin"
    # Shallow: we only ever need the tree at the pin, never its history.
    git clone --depth 1 --branch $Pin $Upstream $ApDir
    if ($LASTEXITCODE -ne 0) { throw "bootstrap-ap: clone failed" }
} else {
    Push-Location $ApDir
    try {
        $origin = (git remote get-url origin).Trim()
        # Guard the exact mistake this script exists to undo: silently developing against a FORK.
        if ($origin -notmatch 'ArchipelagoMW/Archipelago') {
            throw "bootstrap-ap: $ApDir points at '$origin', not upstream ArchipelagoMW. " +
                  "That is how a Bedrock fork got in here. Re-run with -Force."
        }
        git fetch --depth 1 origin tag $Pin 2>&1 | Out-Null
        git checkout -q $Pin
        if ($LASTEXITCODE -ne 0) { throw "bootstrap-ap: checkout of $Pin failed" }
    } finally { Pop-Location }
}

$desc = (git -C $ApDir describe --tags 2>$null)
Write-Host "bootstrap-ap: .\Archipelago is stock upstream @ $Pin ($desc)"
Write-Host "bootstrap-ap: install the world with build.ps1 -- nothing of ours is committed in there."
