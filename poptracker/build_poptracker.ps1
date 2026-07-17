# Build the ER-AP PopTracker pack's GENERATED output from the greenfield apworld + committed coord
# facts. Run directly:  .\poptracker\build_poptracker.ps1   (optionally -Check to fail on staleness).
#
# Regenerates the source/generated split's generated half (see poptracker/.gitignore):
#   images/maps/*.png, maps/maps.json, scripts/{loc_map,loc_dlc,ap_map,region_graph}.lua,
#   locations/locations.json, items/items.json, layouts/item_grid.json
# The committed source (SVG hulls, calibration/centroids/pins, hand Lua, manifest, layouts) is the
# input; gen_poptracker.py reads greenfield/eldenring + greenfield/item_grace_coords.tsv.
param(
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [switch]$Check   # verify-only: nonzero exit if any generated file is stale (for CI)
)
$ErrorActionPreference = "Stop"
$Gen = Join-Path $Repo "poptracker\tools\gen_poptracker.py"
$args = @($Gen)
if ($Check) { $args += "--check" }

Write-Host "[poptracker] $(if ($Check) {'checking'} else {'generating'}) pack data ($Gen)" -ForegroundColor Cyan
& python @args
if ($LASTEXITCODE -ne 0) {
    if ($Check) { throw "[poptracker] pack data is STALE -- run .\poptracker\build_poptracker.ps1" }
    throw ("[poptracker] gen_poptracker.py FAILED (exit {0})" -f $LASTEXITCODE)
}
Write-Host "[poptracker] done" -ForegroundColor Green
