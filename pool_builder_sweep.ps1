<#
  pool_builder_sweep.ps1 -- convenience wrapper for the ER pool_builder scaling harness.

  Runs worlds/eldenring/tests/pool_builder_sweep.py with your AP python (3.11+),
  from the Archipelago dir, forwarding all args through. Composes the item pool
  over N pinned seeds (default N = 100, 1000) and tallies the make-up + timing
  per N so you can watch it converge. Stops at create_items (no fill), so N=1000
  is cheap.

  USAGE (from the repo root, on Windows)
    .\pool_builder_sweep.ps1
    .\pool_builder_sweep.ps1 --counts 100,1000,5000
    .\pool_builder_sweep.ps1 --intensity 2 --compare
    .\pool_builder_sweep.ps1 --curated --tag curated

  Outputs land in the Archipelago dir:
    poolbuild_sweep_<tag>_<ts>.csv   one row per (N,seed)
    poolbuild_sweep_<tag>_<ts>.md    per-N convergence summary
#>
$ErrorActionPreference = "Stop"
$Repo   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApDir  = Join-Path $Repo "Archipelago"
$Driver = Join-Path $ApDir "worlds\eldenring\tests\pool_builder_sweep.py"

if (-not (Test-Path $Driver)) { throw "driver not found at $Driver -- run from the repo root." }

Push-Location $ApDir
try {
    python "worlds\eldenring\tests\pool_builder_sweep.py" @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
