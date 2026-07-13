# package_client_bundle.ps1 -- build a standalone me3 bundle of the ER Archipelago CLIENT.
#
# The client is apworld-AGNOSTIC. It drives any Elden Ring apworld that emits either our slot_data
# contract or the matt-style location keys, and it falls back to STATIC game-derived tables for
# everything a foreign apworld does not send. So it can be handed to another apworld author as a
# self-contained folder: they point it at their server and play.
#
# Produces:  dist\er-ap-client-<sha>\   and a .zip beside it
#
#   eldenring_archipelago.dll   the client (built by .\build.ps1 -Rust)
#   ap.me3                      the me3 ModProfile (loads the DLL as a native, vanilla exe)
#   apconfig.json               server / slot (blank is fine -- the in-game overlay asks)
#   check_lots_table.json       vanilla suppression. Derived from ItemLotParam = GAME data, not seed
#                               data, so ONE static file suppresses the vanilla ware at every check
#                               for ANY apworld. Without it a check pays out the vanilla item AND the
#                               AP item.
#   shoplineup_flags.json       shop-row -> eventFlag_forStock. Lets shop purchases self-detect.
#                               Without it, shop checks never fire.
#   ap-package\                 optional cosmetic icon override (if built)
#   README.md                   install + what the client needs from a slot_data
#
# Usage:
#   .\build.ps1 -Rust                    # build the DLL first
#   .\tools\package_client_bundle.ps1
[CmdletBinding()]
param(
    [string]$Dll,                       # default: the -Rust output
    [string]$OutDir                     # default: <repo>\dist
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot

if (-not $Dll) {
    $Dll = Join-Path $Repo "from-software-archipelago-clients\target\x86_64-pc-windows-msvc\release\eldenring_archipelago.dll"
}
if (-not (Test-Path $Dll)) {
    throw "client DLL not found: $Dll`nBuild it first:  .\build.ps1 -Rust"
}
if (-not $OutDir) { $OutDir = Join-Path $Repo "dist" }

# Stamp the bundle with the CLIENT commit it was built from. A bundle you cannot trace back to a
# commit is a bug report you cannot action.
Push-Location (Join-Path $Repo "from-software-archipelago-clients")
try { $sha = (git rev-parse --short HEAD).Trim() } catch { $sha = "unknown" }
Pop-Location

$name   = "er-ap-client-$sha"
$bundle = Join-Path $OutDir $name
if (Test-Path $bundle) { Remove-Item $bundle -Recurse -Force }
New-Item -ItemType Directory -Force -Path $bundle | Out-Null

Copy-Item $Dll (Join-Path $bundle "eldenring_archipelago.dll") -Force
Write-Host "  eldenring_archipelago.dll  (client $sha)"

# The two STATIC tables. Both are derived from the game's own params -- game data, not seed data --
# which is exactly why one copy works for every apworld and every seed.
foreach ($t in @("check_lots_table.json", "shoplineup_flags.json")) {
    $src = Join-Path $Repo "greenfield\eldenring\$t"
    if (-not (Test-Path $src)) {
        throw "$t missing from greenfield\eldenring. Regenerate: python tools\gen_check_lots_table.py / gen_shoplineup_flags.py"
    }
    Copy-Item $src (Join-Path $bundle $t) -Force
    Write-Host "  $t"
}

# me3 profile. disable_arxan: the client hooks native code (AddItemFunc) that Arxan would revert.
$profileText = @"
profileVersion = "v1"
savefile = "AP_me3.sl2"
disable_arxan = true

[[supports]]
game = "eldenring"

[[natives]]
path = 'eldenring_archipelago.dll'
"@
Set-Content -Path (Join-Path $bundle "ap.me3") -Value $profileText -Encoding UTF8
Write-Host "  ap.me3"

# Blank config: the in-client connect overlay collects server/slot/password in-game, so a blank file
# is a valid starting point rather than a broken one.
$cfg = @"
{
  "url": "",
  "slot": "",
  "password": ""
}
"@
Set-Content -Path (Join-Path $bundle "apconfig.json") -Value $cfg -Encoding UTF8
Write-Host "  apconfig.json  (blank -- fill in-game, or edit)"

# Optional cosmetic icon override.
$pkg = Join-Path $Repo "me3\ap-package"
if (Test-Path (Join-Path $pkg "menu")) {
    Copy-Item $pkg (Join-Path $bundle "ap-package") -Recurse -Force
    $profileText = $profileText -replace "\[\[natives\]\]", "[[packages]]`npath = 'ap-package'`n`n[[natives]]"
    Set-Content -Path (Join-Path $bundle "ap.me3") -Value $profileText -Encoding UTF8
    Write-Host "  ap-package\  (AP icon override; profile updated)"
} else {
    Write-Host "  ap-package\ absent -- shipping without the AP icon override (cosmetic only)" -ForegroundColor Yellow
}

$readme = Join-Path $Repo "release-v0.2\CLIENT-BUNDLE-README.md"
if (Test-Path $readme) {
    Copy-Item $readme (Join-Path $bundle "README.md") -Force
    Write-Host "  README.md"
} else {
    Write-Warning "  release-v0.2\CLIENT-BUNDLE-README.md missing -- bundle ships with no instructions"
}

$zip = Join-Path $OutDir "$name.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $bundle "*") -DestinationPath $zip
Write-Host ""
Write-Host "bundle -> $bundle" -ForegroundColor Green
Write-Host "zip    -> $zip" -ForegroundColor Green
