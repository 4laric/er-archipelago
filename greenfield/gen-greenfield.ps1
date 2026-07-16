# Greenfield ER apworld: install into Archipelago\worlds and generate in isolation.
# Called by build.ps1 -Greenfield, or run directly:  .\greenfield\gen-greenfield.ps1
param([string]$Repo = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = "Stop"
$Here    = Join-Path $Repo "greenfield"
$ApDir   = Join-Path $Repo "Archipelago"
$WorldSrc = Join-Path $Here "eldenring"
$WorldDst = Join-Path $ApDir "worlds\eldenring"
$Players  = Join-Path $Here "players"

# Regenerate the data-derived modules (item_ids.py incl. DLC_ITEM_NAMES, data.py, shop_data.py,
# boss_sweeps.py, ...) from elden_ring_artifacts BEFORE copying the world, so the deployed apworld
# always ships freshly-generated data. gen_data.py is matt-free and deterministic.
$BossDrops = Join-Path (Split-Path $Here -Parent) "tools\datamine_boss_drops.py"
Write-Host "[greenfield] datamining boss-drop flags ($BossDrops)" -ForegroundColor Cyan
& python $BossDrops
if ($LASTEXITCODE -ne 0) { throw ("[greenfield] datamine_boss_drops.py FAILED (exit {0})" -f $LASTEXITCODE) }
$BossHealthbars = Join-Path (Split-Path $Here -Parent) "tools\datamine_boss_healthbars.py"
Write-Host "[greenfield] datamining boss-healthbar set ($BossHealthbars)" -ForegroundColor Cyan
& python $BossHealthbars
if ($LASTEXITCODE -ne 0) { throw ("[greenfield] datamine_boss_healthbars.py FAILED (exit {0})" -f $LASTEXITCODE) }
$GenData = Join-Path $Here "gen_data.py"
Write-Host "[greenfield] regenerating data ($GenData)" -ForegroundColor Cyan
& python $GenData
if ($LASTEXITCODE -ne 0) { throw ("[greenfield] gen_data.py FAILED (exit {0})" -f $LASTEXITCODE) }

# Gate: the generated modules must match a hash of the inputs on disk (SPEC-gen-input-hash-gate).
# Refuses to install/generate stale or partially-written data -- the invariant that retires the
# "NEEDS WINDOWS REGEN" marker. tools/gen_manifest.py is the one definition of the hash.
$GenManifest = Join-Path (Split-Path $Here -Parent) "tools\gen_manifest.py"
$StampJson   = Join-Path $WorldSrc "_gen_stamp.json"
Write-Host "[greenfield] verifying gen-input stamp" -ForegroundColor Cyan
& python $GenManifest --verify $StampJson
if ($LASTEXITCODE -ne 0) { throw ("[greenfield] gen-input stamp STALE/UNVERIFIABLE (exit {0}) -- rerun gen_data.py" -f $LASTEXITCODE) }

# Install the world into $ApDir\worlds\eldenring via the ONE definition of "the installed world":
# tools/gf_test.py --install-only. It copies the package PLUS every beside-package input the oracle
# suites need (region_map.csv, *.tsv incl. play_region_buckets.tsv, region_groups.py, the shipping
# EldenRing.yaml) and fails loudly if a REQUIRED_INPUT is missing. This used to be a hand-maintained
# copy block here, and it drifted from gf_test.py twice (shop_rows.tsv, then region_groups.py) --
# each time a test went RED locally and GREEN in CI for no reason but a missing copy. One definition,
# no drift. (--install-only does not touch the AP checkout itself; $ApDir stays whatever it is.)
Write-Host "[greenfield] installing world -> $WorldDst (tools/gf_test.py --install-only)" -ForegroundColor Cyan
& python (Join-Path $Repo "tools\gf_test.py") --install-only --ap-dir $ApDir
if ($LASTEXITCODE -ne 0) { throw ("[greenfield] world install FAILED (exit {0})" -f $LASTEXITCODE) }

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$genLog = Join-Path $Repo "generate_greenfield_$ts.log"
Write-Host "[greenfield] generating (isolated player files: $Players)" -ForegroundColor Cyan
Push-Location $ApDir
try {
    $env:AP_NONINTERACTIVE = "1"
    cmd /c "python Generate.py --player_files_path `"$Players`" > `"$genLog`" 2>&1"
    $genExit = $LASTEXITCODE
} finally { Pop-Location }

Write-Host ("[greenfield] raw log -> {0}" -f $genLog) -ForegroundColor Green
$er = Select-String -LiteralPath $genLog -Pattern 'ER_COUNTS|checks=' -ErrorAction SilentlyContinue
if ($er) { foreach ($m in $er) { Write-Host ("  " + $m.Line.Trim()) -ForegroundColor Green } }
if ($genExit -ne 0) {
    Get-Content -LiteralPath $genLog -Tail 25 | Write-Host
    throw ("[greenfield] generation FAILED (exit {0}) -- see {1}" -f $genExit, $genLog)
}
Write-Host "[greenfield] OK" -ForegroundColor Green
