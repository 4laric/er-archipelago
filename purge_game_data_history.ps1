# purge_game_data_history.ps1
# Rewrites ALL git history to remove copyrighted game data + personal saves +
# build outputs committed under seeds-archive/, plus the SoulsRandomizers
# submodule pointer. Uses git-filter-repo.
#
# WARNING: THIS IS DESTRUCTIVE AND IRREVERSIBLE.
#   - Every commit SHA after the purge point changes. It is a full history rewrite.
#   - Requires a FORCE PUSH, which this script does NOT do automatically -- it stops
#     and prints the exact commands so you decide.
#   - The repo is already public: clones, forks, and GitHub's cached blob views may
#     STILL hold this data after you push. A purge shrinks exposure; it does not
#     guarantee erasure. For hard cases, contact GitHub Support to purge cached
#     views and (optionally) ask forks to be removed.
#
# Prereqs: git 2.24+, Python 3.6+, and git-filter-repo:
#     python -m pip install git-filter-repo
#
# Run from the repo root on Windows:  .\purge_game_data_history.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- 0. Safety checks ---------------------------------------------------------
git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) { throw "Not inside a git repo. cd to the repo root." }

if (git status --porcelain) {
    Write-Host "Working tree is dirty. Commit or stash first -- filter-repo rewrites" -ForegroundColor Red
    Write-Host "history and you want a clean, known starting point." -ForegroundColor Red
    Write-Host "Tip: commit the .gitignore + CONTRIBUTING.md changes now, then re-run." -ForegroundColor Yellow
    exit 1
}

python -m git_filter_repo --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "git-filter-repo not found. Install it:  python -m pip install git-filter-repo"
}

# --- 1. Backup mirror (your undo button) --------------------------------------
$backup = Join-Path (Split-Path $PSScriptRoot -Parent) ("er-archipelago-backup-{0}.git" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
Write-Host "Creating backup mirror at: $backup" -ForegroundColor Cyan
git clone --mirror . $backup | Out-Null
Write-Host "Backup done. If anything goes wrong, that mirror has the original history." -ForegroundColor Green
Write-Host ""

# --- 2. Analyze (what's the biggest stuff in history) -------------------------
Write-Host "Analyzing history (report only, no changes)..." -ForegroundColor Cyan
python -m git_filter_repo --analyze
Write-Host "Report written under .git/filter-repo/analysis/ -- skim it if you want." -ForegroundColor Green
Write-Host ""

# --- 3. The purge -------------------------------------------------------------
# --invert-paths = REMOVE everything matching the paths below (keep the rest).
# Regex targets the seeds-archive game blobs at any historical location; the glob
# lines catch the same asset TYPES even if a path was renamed in history.
# Source binaries (reg_*.bin, regulation_dlc.bin) are NOT matched -- kept.
# --path SoulsRandomizers removes the SoulsRandomizers submodule gitlink (and any
# files ever committed under it). It purges the POINTER in this repo, not the
# code (that repo is already deleted). Own docs referencing it are KEPT.
Write-Host "Rewriting history to remove game data / saves / build outputs + SoulsRandomizers..." -ForegroundColor Cyan
python -m git_filter_repo --force --invert-paths `
    --path-regex '^seeds-archive/[^/]+/(game-files|save|mods|ap-server)/' `
    --path-regex '^seeds-archive/[^/]+/_pre-restore-backup-' `
    --path SoulsRandomizers `
    --path-glob '*.sl2' `
    --path-glob '*.msb.dcx' `
    --path-glob '*.emevd.dcx' `
    --path-glob '*.msgbnd.dcx' `
    --path-glob '*.talkesdbnd.dcx'

if ($LASTEXITCODE -ne 0) { throw "filter-repo failed. Your working repo may be partially rewritten; restore from the backup mirror if needed." }

# --- 4. Verify ----------------------------------------------------------------
Write-Host ""
Write-Host "Verifying the blobs are gone from history..." -ForegroundColor Cyan
$hits = git log --all --oneline -- '*.sl2' 'seeds-archive/*/game-files' 'seeds-archive/*/mods' 'SoulsRandomizers' 2>$null
if ($hits) {
    Write-Host "Still found references; investigate before pushing:" -ForegroundColor Red
    $hits
} else {
    Write-Host "Clean: no game-files / saves / mods / SoulsRandomizers remain in any commit." -ForegroundColor Green
}

# --- 5. Force-push (MANUAL -- not run here) -----------------------------------
Write-Host ""
Write-Host "==================== NEXT STEPS (you run these) ====================" -ForegroundColor Yellow
Write-Host "filter-repo removed the 'origin' remote as a safety measure. Re-add it,"
Write-Host "then force-push the rewritten history:"
Write-Host ""
Write-Host "  git remote add origin https://github.com/<you>/er-archipelago.git" -ForegroundColor White
Write-Host "  git push origin --force --all" -ForegroundColor White
Write-Host "  git push origin --force --tags" -ForegroundColor White
Write-Host ""
Write-Host "Then, because the repo is public:" -ForegroundColor Yellow
Write-Host "  - Re-clone anywhere you have a working copy (old clones keep the blobs)."
Write-Host "  - Ask GitHub Support to purge cached blob views + garbage-collect."
Write-Host "  - Existing FORKS still contain the data; request removal if it matters."
Write-Host "  - Note: the save-file paths exposed a SteamID (76561198275129903)."
Write-Host "  - SoulsRandomizers: only the submodule POINTER was removed here; the code"
Write-Host "    repo is already deleted, so nothing further needed there."
Write-Host "===================================================================" -ForegroundColor Yellow
