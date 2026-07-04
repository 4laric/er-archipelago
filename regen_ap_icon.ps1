# regen_ap_icon.ps1 -- regenerate the AP flower icon override and stage it into me3.
#
# me3\ap-package\menu is currently EMPTY, so AP items fall back to the vanilla
# Telescope texture until this runs. This is a thin wrapper over the EXISTING
# pipeline (do not reinvent it):
#
#   1. build_ap_icon.py --icon01 ...   -> writes build\ap_icon01\menu\{hi,low}\01_common.tpf.dcx
#                                         (the REAL shop/inventory icon; the SB_Icon sheet).
#                                         00_solo.* is a harmless extra some steps also emit.
#   2. build.ps1 -Me3Deploy            -> stages build\ap_icon*\menu\... into me3\ap-package\menu.
#
#   Pinned (verified from offline params 2026-07-04):
#     EquipParamGoods 2040 = Telescope ; iconId = 92
#
# REQUIREMENTS (Windows)
#   - build_ap_icon.py  -- NOTE: this is NOT tracked in the repo. It must exist in your
#                          working tree (pass -IconPy if it lives elsewhere). If it's lost,
#                          it has to be recovered/recreated before the icon can be rebuilt.
#   - Python on PATH (or pass -Python).
#   - The vanilla menu textures from a UXM-UNPACKED Elden Ring: pass -MenuSrc at the
#     game's "menu" dir (contains hi\ and low\).
#
# USAGE (from repo root)
#   .\regen_ap_icon.ps1 -MenuSrc "D:\ELDEN RING\Game\menu" -DryRun   # echo the commands
#   .\regen_ap_icon.ps1 -MenuSrc "D:\ELDEN RING\Game\menu"           # generate + stage
#   .\regen_ap_icon.ps1 -MenuSrc "..." -SkipDeploy                   # generate only

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$MenuSrc,
    [int]$IconId = 92,
    [string]$IconPy = (Join-Path $PSScriptRoot "build_ap_icon.py"),
    [string]$Python = "python",
    [switch]$SkipDeploy,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Repo = $PSScriptRoot
$PkgMenuHi = Join-Path $Repo "me3\ap-package\menu\hi"

function Info($m) { Write-Host "[icon] $m" }
function Warn($m) { Write-Host "[warn] $m" -ForegroundColor Yellow }
function Die($m)  { throw "[icon] $m" }

function Run([string]$exe, [string[]]$cmdArgs) {
    $shown = '"' + $exe + '" ' + ($cmdArgs -join ' ')
    Write-Host "       > $shown" -ForegroundColor DarkGray
    if ($DryRun) { return }
    & $exe @cmdArgs
    if ($LASTEXITCODE -ne 0) { Die "command failed (exit $LASTEXITCODE): $shown" }
}

# --- preflight -------------------------------------------------------------
if (-not (Test-Path $IconPy)) {
    Die "build_ap_icon.py not found at $IconPy. It is NOT tracked in the repo -- recover it from your Windows working tree or a backup (or pass -IconPy <path>). Without it the icon cannot be rebuilt."
}
if (-not (Test-Path $MenuSrc)) {
    Die "menu source not found: $MenuSrc (point -MenuSrc at the UXM-unpacked game's 'menu' dir)."
}
Info "Telescope iconId $IconId ; menu source: $MenuSrc"
if ($DryRun) { Info "DRY RUN -- commands are printed, not executed." }

# --- 1. generate the icon bundles -----------------------------------------
Info "Generating AP flower bundles (01_common, hi+low) ..."
Run $Python @(
    "`"$IconPy`"",
    "--icon01",
    "--icon-id", "$IconId",
    "--black-to-alpha",
    "--bundles", "hi,low",
    "--menu", "`"$MenuSrc`""
)

# --- 2. stage into me3\ap-package -----------------------------------------
if ($SkipDeploy) {
    Info "-SkipDeploy: generated bundles left under build\ap_icon01\ ; not staged."
} else {
    Info "Staging into me3\ap-package (build.ps1 -Me3Deploy) ..."
    Run (Join-Path $Repo "build.ps1") @("-Me3Deploy")
}

# --- verify ----------------------------------------------------------------
if (-not $DryRun -and -not $SkipDeploy) {
    $staged = @(Get-ChildItem -Path $PkgMenuHi -Recurse -File -ErrorAction SilentlyContinue)
    if ($staged.Count -eq 0) {
        Warn "me3\ap-package\menu\hi is still empty after -Me3Deploy -- check build_ap_icon.py output under build\ap_icon01\."
        exit 2
    }
    Info "Staged $($staged.Count) file(s) into me3\ap-package\menu\hi."
}

Info "DONE. Verify in-game (shop list, inventory grid, pickup popup), then package_release.ps1."
