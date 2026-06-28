<#
.SYNOPSIS
  Finish the superrepo cleanup: (A) register SoulsFormatsNEXT as a submodule,
  (B) stage + commit the real new Rust source and cleanup tooling.
  DRY-RUN by default.

.DESCRIPTION
  (A) SoulsFormatsNEXT/ is currently a loose nested clone (origin fswap/SoulsFormatsNEXT,
      branch master). This registers it as a submodule like the other 6 forks, writing
      a .gitmodules entry + gitlink at its current HEAD. (No re-clone -- git adds the
      existing repo in place.)

  (B) Stages genuine work that was sitting untracked and commits it (scoped paths only,
      never `git add -A`, so dirty submodule pointers stay untouched):
        - rust-client-spike/crates/er-logic/              (new logic crate)
        - rust-client-spike/crates/eldenring-ap/src/game/{console,deathlink,features,progressive,upgrades}.rs
        - untrack_committed_junk.ps1, cleanup_apworld_cruft.ps1, finish_repo_cleanup.ps1

  Run untrack_committed_junk.ps1 FIRST if you haven't (this script doesn't repeat it).

.PARAMETER Execute   Actually run git. Without it, prints the commands only.
.PARAMETER Commit    After -Execute staging, create the two scoped commits.
.PARAMETER SubmoduleUrl   Override the submodule URL (default: the clone's origin).

.EXAMPLE
  .\finish_repo_cleanup.ps1
  .\finish_repo_cleanup.ps1 -Execute
  .\finish_repo_cleanup.ps1 -Execute -Commit
#>
[CmdletBinding()]
param(
  [switch]$Execute,
  [switch]$Commit,
  [string]$SubmoduleUrl = 'git@github.com:fswap/SoulsFormatsNEXT.git',
  [string]$SubmoduleBranch = 'master'
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$mode = if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' }
Write-Host "=== finish repo cleanup ($mode) ===" -ForegroundColor Cyan

function Run($desc, [scriptblock]$cmd) {
  Write-Host "  $desc" -ForegroundColor DarkGray
  if ($Execute) { & $cmd }
}

# ---------- (A) register SoulsFormatsNEXT as a submodule ----------
Write-Host "`n[A] SoulsFormatsNEXT -> submodule ($SubmoduleUrl @ $SubmoduleBranch)" -ForegroundColor Yellow
if (-not (Test-Path 'SoulsFormatsNEXT/.git')) {
  Write-Host "    SoulsFormatsNEXT/ is not a git clone here -- skipping (A)." -ForegroundColor Red
} else {
  Write-Host "    git submodule add -b $SubmoduleBranch --force -- $SubmoduleUrl SoulsFormatsNEXT" -ForegroundColor DarkGray
  if ($Execute) {
    git submodule add -b $SubmoduleBranch --force -- $SubmoduleUrl SoulsFormatsNEXT
    if ($LASTEXITCODE -ne 0) { throw "submodule add failed ($LASTEXITCODE)" }
  }
  if ($Commit) {
    Run "git commit .gitmodules + SoulsFormatsNEXT gitlink" {
      git commit -m "Add SoulsFormatsNEXT as submodule (fswap, master)" -- .gitmodules SoulsFormatsNEXT
    }
  }
}

# ---------- (B) stage + commit real source / tooling ----------
$paths = @(
  'rust-client-spike/crates/er-logic',
  'rust-client-spike/crates/eldenring-ap/src/game/console.rs',
  'rust-client-spike/crates/eldenring-ap/src/game/deathlink.rs',
  'rust-client-spike/crates/eldenring-ap/src/game/features.rs',
  'rust-client-spike/crates/eldenring-ap/src/game/progressive.rs',
  'rust-client-spike/crates/eldenring-ap/src/game/upgrades.rs',
  'untrack_committed_junk.ps1',
  'cleanup_apworld_cruft.ps1',
  'finish_repo_cleanup.ps1'
) | Where-Object { Test-Path $_ }

Write-Host "`n[B] stage real source / tooling ($($paths.Count) paths)" -ForegroundColor Yellow
$paths | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
if ($Execute) {
  git add -- @paths
  Write-Host "    staged." -ForegroundColor Green
  if ($Commit) {
    git commit -m "Add er-logic crate, eldenring-ap game modules, and repo cleanup scripts" -- @paths
    Write-Host "    committed." -ForegroundColor Green
  }
}

Write-Host "`n=== done ($mode) ===" -ForegroundColor Cyan
if (-not $Execute) { Write-Host "Re-run with -Execute (add -Commit to also commit)." -ForegroundColor Green }
