# package_release.ps1 -- assemble the player-facing ER Archipelago release bundle.
#
# Pure-runtime: NO FromSoftware game data ships. This wraps the three things a
# player needs into one zip:
#   1. eldenring.apworld            (built by build.ps1 -Apworld)
#   2. me3\ runtime                 (client DLL + ap-package AP-icon override +
#                                    er_static_detection_table.json + apconfig.json)
#   3. the flagship yaml + SETUP.md + CHANGELOG.md
# (The PopTracker pack stays in the repo, not bundled; the built-in F6 tracker ships.)
#
# The AP-icon override IS me3\ap-package (a me3 VFS texture swap: AP items show the
# flower icon). It is bundled by copying me3\ wholesale; the script WARNS if the
# ap-package menu textures are missing so an empty icon package never ships silently.
#
# Usage (from the repo root):
#   .\package_release.ps1                 # build apworld, stage, zip -> dist\
#   .\package_release.ps1 -SkipApworld    # reuse the existing eldenring.apworld
#   .\package_release.ps1 -Version 0.1    # version tag used in the zip name
#   .\package_release.ps1 -DryRun         # stage + report only; do not zip
#
# Exit codes: 0 = clean, 2 = staged but with warnings (review before shipping).

[CmdletBinding()]
param(
    [string]$Version = "0.1",
    [switch]$SkipApworld,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Repo  = $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Name  = "ER-Archipelago-v$Version"
$Dist  = Join-Path $Repo "dist"
$Stage = Join-Path $Dist $Name
$Rel   = Join-Path $Repo "release-v0.1"
$Warnings = New-Object System.Collections.Generic.List[string]

function Info($m) { Write-Host "[pkg]  $m" }
function Warn($m) { Write-Host "[warn] $m" -ForegroundColor Yellow; $Warnings.Add($m) | Out-Null }
function Die($m)  { throw "[pkg] $m" }

# ---------------------------------------------------------------------------
# 1. Fresh apworld
# ---------------------------------------------------------------------------
$Apworld = Join-Path $Repo "eldenring.apworld"
if (-not $SkipApworld) {
    Info "Building fresh apworld (build.ps1 -Apworld) ..."
    & (Join-Path $Repo "build.ps1") -Apworld
    if ($LASTEXITCODE -ne 0) { Die "build.ps1 -Apworld failed (exit $LASTEXITCODE)." }
}
if (-not (Test-Path $Apworld)) {
    Die "eldenring.apworld not found at $Apworld. Run without -SkipApworld, or build it first."
}

# ---------------------------------------------------------------------------
# 2. Clean staging dir
# ---------------------------------------------------------------------------
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
Info "Staging into $Stage"

# ---------------------------------------------------------------------------
# 3. apworld
# ---------------------------------------------------------------------------
Copy-Item $Apworld (Join-Path $Stage "eldenring.apworld") -Force
Info "+ eldenring.apworld"

# ---------------------------------------------------------------------------
# 4. me3 runtime (client + AP-icon override + config)
# ---------------------------------------------------------------------------
$Me3Src = Join-Path $Repo "me3"
if (-not (Test-Path $Me3Src)) { Die "me3\ runtime folder not found at $Me3Src." }
$Me3Dst = Join-Path $Stage "me3"
Copy-Item $Me3Src $Me3Dst -Recurse -Force
Info "+ me3\ (runtime bundle)"

# Hard requirements: without these the game will not load the client.
$Dll   = Join-Path $Me3Dst "eldenring_archipelago.dll"
$Prof  = Join-Path $Me3Dst "ap.me3"
if (-not (Test-Path $Dll))  { Die "missing client DLL: me3\eldenring_archipelago.dll" }
if ((Get-Item $Dll).Length -lt 1024) { Die "client DLL looks empty ( < 1 KB ): $Dll" }
if (-not (Test-Path $Prof)) { Die "missing me3 profile: me3\ap.me3" }

# Detection table + config: warn (not fatal) if absent.
if (-not (Test-Path (Join-Path $Me3Dst "er_static_detection_table.json"))) {
    Warn "me3\er_static_detection_table.json is missing -- the client needs it at runtime."
}

# AP-icon override = me3\ap-package\menu textures. Warn loudly if empty so a
# bundle without the flower-icon swap never ships silently.
$IconMenu = Join-Path $Me3Dst "ap-package\menu"
$IconFiles = @()
if (Test-Path $IconMenu) {
    $IconFiles = @(Get-ChildItem -Path $IconMenu -Recurse -File -ErrorAction SilentlyContinue)
}
if ($IconFiles.Count -eq 0) {
    Warn "AP-icon override is EMPTY (me3\ap-package\menu has no texture files). The flower-icon swap will NOT be in this bundle -- stage the icon TPF/DCX into me3\ap-package\menu before shipping."
} else {
    Info "+ AP-icon override ($($IconFiles.Count) texture file(s) in ap-package\menu)"
}

# Ship a GENERIC apconfig so a personal slot name never leaks into the release.
$ApConfig = Join-Path $Me3Dst "apconfig.json"
'{"url":"localhost:38281","slot":"Player1","seed":"","client_version":null,"password":null}' |
    Set-Content -Path $ApConfig -Encoding ASCII -NoNewline
Info "+ apconfig.json (generic template: localhost / Player1)"

# ---------------------------------------------------------------------------
# 5. Flagship yaml + docs
#    (PopTracker pack is intentionally NOT bundled -- it lives in the repo for
#    anyone who wants it; the built-in F6 tracker is the shipped tracker.)
# ---------------------------------------------------------------------------
$Docs = @(
    @{ src = (Join-Path $Rel "EldenRing-Shattering.yaml"); required = $true  },
    @{ src = (Join-Path $Rel "SETUP.md");                  required = $true  },
    @{ src = (Join-Path $Rel "CHANGELOG.md");              required = $true  }
)
foreach ($d in $Docs) {
    if (Test-Path $d.src) {
        Copy-Item $d.src $Stage -Force
        Info ("+ " + (Split-Path $d.src -Leaf))
    } elseif ($d.required) {
        Die ("missing required file: " + $d.src)
    }
}

# ---------------------------------------------------------------------------
# 7. Manifest + zip
# ---------------------------------------------------------------------------
Info "----- bundle contents -----"
Get-ChildItem -Path $Stage -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($Stage.Length + 1)
    $kb  = [math]::Round($_.Length / 1KB, 1)
    Write-Host ("       {0,8} KB  {1}" -f $kb, $rel)
}
$totalMB = [math]::Round((Get-ChildItem -Path $Stage -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
Info "total staged size: $totalMB MB"

if ($DryRun) {
    Info "DryRun: staged at $Stage (no zip written)."
} else {
    $Zip = Join-Path $Dist ("{0}-{1}.zip" -f $Name, $Stamp)
    if (Test-Path $Zip) { Remove-Item $Zip -Force }
    Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Zip -Force
    Info "zip written: $Zip"
}

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
if ($Warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "[pkg] DONE with $($Warnings.Count) warning(s):" -ForegroundColor Yellow
    foreach ($w in $Warnings) { Write-Host "        - $w" -ForegroundColor Yellow }
    exit 2
} else {
    Info "DONE clean -- bundle ready."
    exit 0
}
