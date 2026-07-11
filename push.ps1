# push.ps1 -- commit & push across the ER Archipelago repos
#
# Usage (from the repo root):
#   .\push.ps1 -Status                      # show pending changes in every repo
#   .\push.ps1 -Message "what changed"      # commit (scoped paths only) + push, all repos
#   .\push.ps1 -Message "..." -Only Archipelago,Client    # subset (match Name below)
#   .\push.ps1 -Message "..." -Superrepo    # ...then bump the superrepo submodule pointers + tooling
#   .\push.ps1 -Status -Superrepo           # also show pending pointer moves at the root
#   .\push.ps1 -Message "bump" -Superrepo -Only NONE   # ONLY the superrepo (skip all subrepos)
#
# Notes:
#  - Adds are SCOPED per repo so build/bake outputs never get committed (Rust target\ in the
#    client, output\ zips in Archipelago, VS build results in SoulsFormatsNEXT). .gitignore is a
#    backstop, not the primary guard -- the scoped pathspecs are.
#  - The tree is PUBLIC + pure-runtime now: the old thefifthmatt-licensed SoulsRandomizers fork and
#    the retired C++ DS3 client are GONE, so their private-remote warnings are gone too.
#  - SoulsFormatsNEXT tracks fswap's upstream; a push there may need permission (the loop already
#    warns on push failure and keeps the commit locally).
#  - archipelago_rs is a STANDALONE clone (upstream PR workspace), consumed by the client as a git
#    dependency, NOT a submodule -- it is intentionally not managed here. Commit/push it by hand.
#  - -Superrepo handles the ROOT git repo (see init-superrepo.ps1 / SUPERREPO-SETUP.md): it stages
#    the changed submodule gitlinks + root tooling/docs and commits+pushes them, so "which SHAs of
#    all forks went together" is recorded in one step. Without -Superrepo, root files belong to NO
#    repo and are not covered.

[CmdletBinding()]
param(
    [string]$Message = "",
    [string[]]$Only = @(),
    [switch]$Status,
    [switch]$Superrepo
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

# Individually committed + pushed forks (scoped adds). A repo with no scoped changes is skipped.
$Repos = @(
    @{ Name = "Archipelago"
       Adds = @("worlds/eldenring") },
    @{ Name = "Client"
       Dir  = "from-software-archipelago-clients"
       Adds = @("crates", "Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "*.md", "MIT-LICENSE",
                ":(exclude)*.bak") },
    @{ Name = "SoulsFormatsNEXT"
       Adds = @("SoulsFormats", "*.md")
       Warn = "tracks fswap upstream -- push may need permission" }
)

function Step($msg) { Write-Host "`n==== $msg" -ForegroundColor Cyan }

foreach ($repo in $Repos) {
    if ($Only.Count -gt 0 -and $Only -notcontains $repo.Name) { continue }
    $dir  = if ($repo.Dir) { $repo.Dir } else { $repo.Name }
    $path = Join-Path $Root $dir
    if (-not (Test-Path (Join-Path $path ".git"))) {
        Write-Warning "$($repo.Name): not a git repo at $dir, skipping"
        continue
    }

    Step $repo.Name
    if ($repo.Warn) { Write-Host "  ! $($repo.Warn)" -ForegroundColor Yellow }
    Push-Location $path
    try {
        # Stale lock from a crashed git process blocks everything; detect it loudly.
        if (Test-Path ".git\index.lock") {
            Write-Warning "stale .git\index.lock present -- if no git process is running:"
            Write-Warning "  Remove-Item `"$path\.git\index.lock`""
            continue
        }

        $branch = git branch --show-current
        if (-not $branch) {
            Write-Warning "detached HEAD -- name it first (git switch -c <branch>), skipping"
            continue
        }

        if ($Status) {
            git status -s -- $repo.Adds
            $pending = git status --porcelain -- $repo.Adds
            Write-Host "  [$branch] $(@($pending).Count) change(s) in scoped paths"
            continue
        }

        if (-not $Message) { throw "provide -Message (or use -Status)" }

        git add -- $repo.Adds
        git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) {
            git commit -m $Message
            git push
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "push failed (no fork remote / no permission?). Commit is safe locally."
            }
        } else {
            Write-Host "  (no changes in scoped paths)"
        }
    } finally { Pop-Location }
}

# ---- superrepo: bump submodule pointers + root tooling (runs AFTER the subrepo pushes above,
#      so the gitlinks reflect the new HEADs). See init-superrepo.ps1 / SUPERREPO-SETUP.md.
if ($Superrepo) {
    Step "superrepo (root: submodule pointers + tooling)"

    if (-not (Test-Path (Join-Path $Root ".git"))) {
        Write-Warning "root is not a git repo yet -- run .\init-superrepo.ps1 first."
    }
    else {
        # The submoduled forks (see .gitmodules) + the root files worth tracking. The root
        # .gitignore excludes generated/large/private-upstream paths; these pathspecs stage only
        # real source. "*.ps1" catches all root tooling scripts so this list stops going stale.
        $SubPaths = @("Archipelago", "from-software-archipelago-clients", "SoulsFormatsNEXT",
                      "Paramdex", "nightreign-enemy-rando")
        $Tooling  = @("*.ps1", "*.md", "*.yaml", "poptracker", ".gitignore", ".gitmodules")
        $RootSpec = $SubPaths + $Tooling

        Push-Location $Root
        try {
            if (Test-Path ".git\index.lock") {
                Write-Warning "stale .git\index.lock at root -- if no git process is running:"
                Write-Warning "  Remove-Item `"$Root\.git\index.lock`""
            }
            else {
                $branch = git branch --show-current
                if (-not $branch) {
                    Write-Warning "superrepo in detached HEAD -- name it first (git switch -c main), skipping"
                }
                elseif ($Status) {
                    git submodule status
                    git status -s -- $RootSpec
                    $pending = git status --porcelain -- $RootSpec
                    Write-Host "  [$branch] $(@($pending).Count) change(s) in submodule pointers + tooling"
                }
                elseif (-not $Message) {
                    throw "provide -Message (or use -Status) for the superrepo"
                }
                else {
                    git add -- $RootSpec
                    git diff --cached --quiet
                    if ($LASTEXITCODE -ne 0) {
                        git commit -m $Message
                        git push
                        if ($LASTEXITCODE -ne 0) {
                            Write-Warning "superrepo push failed (no origin / no permission?). Commit is safe locally."
                        }
                    }
                    else {
                        Write-Host "  (no submodule-pointer or tooling changes to commit)"
                    }
                }
            }
        } finally { Pop-Location }
    }
}
