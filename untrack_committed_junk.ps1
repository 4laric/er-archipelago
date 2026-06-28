<#
.SYNOPSIS
  Untrack committed build-output / diagnostic junk from the er-archipelago superrepo.
  DRY-RUN by default.

.DESCRIPTION
  A bunch of regenerable files were committed because .gitignore had inline comments on
  three rules (eldenring_*.apworld, apconfig.json, gendiag_*.txt) -- git treated the whole
  line as the pattern, so they never matched. The .gitignore is now fixed; this script
  removes the already-committed copies from git tracking with `git rm --cached`
  (working-tree files are KEPT on disk; the fixed .gitignore keeps them ignored from now on).

  Scope is EXPLICIT file lists computed from `git ls-files` -- this never runs `git add -A`,
  so the dirty submodule pointers (Archipelago, SoulsRandomizers, ...) are untouched.

  seeds-archive/ (132 MB of tracked save/regulation binaries) is intentionally NOT touched
  here -- that's the deliberate park/resume convention. Handle separately if desired.

.PARAMETER Execute
  Actually stage the untracking. Without this, only prints what it WOULD do.

.PARAMETER Commit
  After -Execute, commit the fixed .gitignore + the untracked paths (scoped commit, no -A).

.EXAMPLE
  .\untrack_committed_junk.ps1                  # dry run
  .\untrack_committed_junk.ps1 -Execute         # stage the git rm --cached
  .\untrack_committed_junk.ps1 -Execute -Commit # ...and commit it
#>
[CmdletBinding()]
param([switch]$Execute, [switch]$Commit)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$mode = if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' }
Write-Host "=== untrack committed junk ($mode) ===" -ForegroundColor Cyan

# --- build explicit tracked-file lists from git (so we only touch what git actually tracks) ---
function Tracked($patterns) {
  $out = & git ls-files -- @patterns 2>$null
  return @($out | Where-Object { $_ })
}

$buckets = [ordered]@{
  'apworld build outputs' = Tracked @('eldenring.apworld','eldenring_*.apworld')
  'gendiag dumps'         = Tracked @('gendiag_*.txt')
  'bake output'           = Tracked @('apconfig.json')
  'run logs / probe temp' = Tracked @('ap_bake_*.log','ap_error_*.txt','ap-client-log.txt','_dg_tmp.py','.write_test_xyz')
}

$all = @()
foreach ($k in $buckets.Keys) {
  $files = $buckets[$k]
  if (-not $files -or $files.Count -eq 0) { Write-Host "[$k] nothing tracked" -ForegroundColor DarkGray; continue }
  Write-Host "[$k] $($files.Count) tracked file(s)" -ForegroundColor Yellow
  $files | Select-Object -First 6 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
  if ($files.Count -gt 6) { Write-Host "    ... +$($files.Count - 6) more" -ForegroundColor DarkGray }
  $all += $files
}

Write-Host ""
Write-Host "TOTAL: $($all.Count) tracked files to untrack (kept on disk)" -ForegroundColor Cyan

if (-not $Execute) {
  Write-Host "`nDRY-RUN. Re-run with -Execute (add -Commit to also commit)." -ForegroundColor Green
  return
}

if ($all.Count -gt 0) {
  # --cached keeps the working-tree copy; --ignore-unmatch is harmless if a path was already gone
  # call per-batch to avoid command-line limits
  $i = 0
  while ($i -lt $all.Count) {
    $batch = $all[$i..([math]::Min($i+200, $all.Count)-1)]
    git rm --cached --quiet --ignore-unmatch -- @batch
    $i += 200
  }
  Write-Host "Staged untracking of $($all.Count) files." -ForegroundColor Green
}

if ($Commit) {
  # scoped commit: only .gitignore + the junk paths, never -A (protects dirty submodule pointers)
  git add -- .gitignore
  git commit -m "Untrack committed build outputs & diag dumps; fix .gitignore inline-comment rules" -- .gitignore @all
  Write-Host "Committed." -ForegroundColor Green
} else {
  Write-Host "Staged but NOT committed. Review 'git status', then commit .gitignore + these paths." -ForegroundColor Yellow
}
