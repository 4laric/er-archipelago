<#
.SYNOPSIS
  Turn the er-archipelago root into a git "superrepo" that submodules the project forks and
  tracks the root tooling/docs (build.ps1, push.ps1, SPEC/BRIEF/TODO docs, poptracker/, player yamls).

.DESCRIPTION
  - Submodules (at their CURRENT committed HEAD): Archipelago, SoulsRandomizers,
    Dark-Souls-III-Archipelago-client, SoulsFormats, SoulsIds, nightreign-enemy-rando,
    Paramdex, yet-another-tab-control.
  - Paramdex and yet-another-tab-control point at YOUR forks (4laric), not the upstreams, so the
    local build patches (yatc's net6.0 retarget) travel with the lockfile. Push those forks first.
  - Generated/large/copyright files are .gitignored (see .gitignore).
  - Reuses each existing local clone (git submodule add --force) instead of re-cloning.

  Run from the repo root on Windows:  .\init-superrepo.ps1
  Safe to re-run: already-added submodules are skipped.

.PARAMETER SuperRemote
  Optional remote URL for the superrepo itself (e.g. git@github.com:4laric/er-archipelago.git).
  Added as 'origin' but NOT pushed (push manually after review).

.PARAMETER NoCommit
  Stage everything but don't create the initial commit (lets you inspect `git status` first).

.PARAMETER DryRun
  Print what would happen without running any git command that mutates state.

.NOTES
  Pin policy: CURRENT HEADs. If a subrepo has uncommitted or unpushed work the script WARNS but
  proceeds (the submodule pins the current committed SHA; uncommitted edits stay in the working
  tree). Push each fork's branch before others try to clone --recursive, or the pinned SHA is
  unreachable. SoulsRandomizers is PRIVATE (licensing) — keep the superrepo private if you push it.
#>
[CmdletBinding()]
param(
    [string]$SuperRemote = "",
    [switch]$NoCommit,
    [switch]$DryRun,
    # Set submodule.recurse=true so `git checkout`/`pull` auto-sync submodule working trees to the
    # pinned SHAs. GREAT on a consumer/sync clone; RISKY on your dev box, where it can detach a
    # submodule you're actively committing in. Off by default; pass on machines that only consume.
    [switch]$AutoSyncSubmodules
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# path => @{ url; branch }   (order preserved; all point at 4laric forks)
$subs = [ordered]@{
    "Archipelago"                       = @{ url = "git@github.com:4laric/Archipelago.git";                       branch = "ap-sync-2026-06-13" }
    "SoulsRandomizers"                  = @{ url = "git@github.com:4laric/SoulsRandomizers.git";                  branch = "ap-sync-2026-06-13" }
    "Dark-Souls-III-Archipelago-client" = @{ url = "git@github.com:4laric/Dark-Souls-III-Archipelago-client.git"; branch = "main" }
    "SoulsFormats"                      = @{ url = "git@github.com:4laric/SoulsFormats.git";                      branch = "dsms" }
    "SoulsIds"                          = @{ url = "git@github.com:4laric/SoulsIds.git";                          branch = "ap-fixes" }
    "nightreign-enemy-rando"            = @{ url = "git@github.com:4laric/nightreign-enemy-rando.git";            branch = "master" }
    # Forks of the third-party upstreams — keep the local build patches in the lockfile.
    "Paramdex"                          = @{ url = "git@github.com:4laric/Paramdex.git";                          branch = "master" }
    "yet-another-tab-control"           = @{ url = "git@github.com:4laric/yet-another-tab-control.git";           branch = "master" }
}

function Run([string]$cmd) {
    Write-Host ">> $cmd" -ForegroundColor Cyan
    if (-not $DryRun) { Invoke-Expression $cmd }
}

# --- sanity: are we at the right root? ---
if (-not (Test-Path ".\build.ps1")) {
    throw "build.ps1 not found in $PSScriptRoot — run this from the er-archipelago root."
}
if (-not (Test-Path ".\.gitignore")) {
    Write-Warning ".gitignore missing — submodule contents/generated files may get staged. Create it first."
}

# --- 1. git init (default branch 'main') ---
if (-not (Test-Path ".\.git")) {
    Run "git init"
    Run "git symbolic-ref HEAD refs/heads/main"
} else {
    Write-Host "superrepo already initialized." -ForegroundColor Green
}

# --- 1b. submodule-aware config (local to this clone; .git/config isn't committed, so this
#         script re-applies it on every machine). All safe-always except submodule.recurse. ---
Write-Host "`n--- configuring submodule-aware git ---" -ForegroundColor Yellow
# Show which submodule commits moved in `git status` / `git diff` (the lockfile is the point).
Run "git config status.submoduleSummary true"
Run "git config diff.submodule log"
# Fetch referenced submodule commits when pulling the superrepo.
Run "git config fetch.recurseSubmodules on-demand"
# On `git push`, FAIL if a pinned submodule SHA isn't on its remote (can't be cloned otherwise).
# This reinforces push.ps1 -Superrepo (which pushes the forks first).
Run "git config push.recurseSubmodules check"
if ($AutoSyncSubmodules) {
    Run "git config submodule.recurse true"
    Write-Host "submodule.recurse=true (checkout/pull will move submodule HEADs to pinned SHAs)." -ForegroundColor Green
} else {
    Write-Host "submodule.recurse left OFF (dev-safe). Re-run with -AutoSyncSubmodules on consumer clones." -ForegroundColor Green
}

# --- 2. preflight: warn (don't stop) on dirty / unpushed forks ---
Write-Host "`n--- preflight (pin policy = current HEADs) ---" -ForegroundColor Yellow
foreach ($path in $subs.Keys) {
    if (-not (Test-Path (Join-Path $path ".git"))) {
        Write-Warning "$path is not a local git clone — SKIPPING (clone it first or remove from `$subs)."
        continue
    }
    $dirty = git -C $path status --porcelain
    if ($dirty) {
        Write-Warning "$path has uncommitted changes; the submodule pins the current COMMITTED HEAD (those edits stay in the working tree)."
    }
    $upstream = git -C $path rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null
    if ($LASTEXITCODE -eq 0 -and $upstream) {
        $ahead = git -C $path rev-list --count "$upstream..HEAD" 2>$null
        if ([int]$ahead -gt 0) {
            Write-Warning "$path is $ahead commit(s) ahead of $upstream — PUSH before others clone --recursive, or the pinned SHA is unreachable."
        }
    } else {
        Write-Warning "$path has no upstream tracking branch — ensure '$($subs[$path].branch)' is pushed to origin."
    }
}

# --- 3. add submodules at current HEAD (reuse existing clones) ---
Write-Host "`n--- adding submodules ---" -ForegroundColor Yellow
foreach ($path in $subs.Keys) {
    if (-not (Test-Path (Join-Path $path ".git"))) { continue }
    $already = git config --file .gitmodules --get "submodule.$path.url" 2>$null
    if ($already) { Write-Host "already a submodule: $path" -ForegroundColor Green; continue }

    $u = $subs[$path].url
    $b = $subs[$path].branch
    # --force reuses the existing local clone instead of re-cloning from the URL.
    Run "git submodule add --force `"$u`" `"$path`""
    # Record the tracking branch so `git submodule update --remote` pulls the right branch later.
    Run "git config -f .gitmodules `"submodule.$path.branch`" `"$b`""
}

# --- 4. stage tooling/docs/.gitignore/.gitmodules (gitignore excludes the rest) ---
Write-Host "`n--- staging root files ---" -ForegroundColor Yellow
Run "git add -A"

# --- 5. commit ---
if (-not $NoCommit) {
    Run 'git commit -m "Superrepo: submodule 4laric forks; track tooling, docs, poptracker"'
} else {
    Write-Host "NoCommit set — review with: git status" -ForegroundColor Green
}

# --- 6. optional superrepo remote (not pushed) ---
if ($SuperRemote) {
    $hasOrigin = git remote 2>$null | Select-String -SimpleMatch "origin"
    if (-not $hasOrigin) { Run "git remote add origin `"$SuperRemote`"" }
    Write-Host "origin set to $SuperRemote — review, then: git push -u origin main" -ForegroundColor Green
}

Write-Host "`nDone. Inspect with: git submodule status ; git log --oneline -1" -ForegroundColor Green
