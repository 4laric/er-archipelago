# ER-Archipelago superrepo

Makes this root a git repo that **submodules the project forks** (8: the 6 4laric forks plus your
Paramdex and yet-another-tab-control forks) and **tracks the root tooling**
(build.ps1, push.ps1, the SPEC/BRIEF/TODO/HANDOFF docs, `poptracker/`, player yamls). Run once on
Windows; git over the sandbox mount is unreliable, so this is a script you run, not something done
in-session.

## One-time setup

```powershell
cd <repo root>           # the folder containing build.ps1
.\init-superrepo.ps1                       # init + add submodules + commit
# or inspect first:
.\init-superrepo.ps1 -NoCommit             # stage everything, then `git status`
.\init-superrepo.ps1 -DryRun               # print the git commands without running them
.\init-superrepo.ps1 -SuperRemote git@github.com:4laric/er-archipelago.git   # also set origin
```

The script: `git init` (branch `main`) → for each fork `git submodule add --force <url> <path>`
(reuses the existing local clone, pins its **current HEAD**) → records each tracking branch in
`.gitmodules` → stages tooling/docs (`.gitignore` excludes everything else) → commits.

## What is / isn't tracked

| | |
|---|---|
| **Submodules (8 forks)** | Archipelago `ap-sync-2026-06-13`, SoulsRandomizers `ap-sync-2026-06-13`, Dark-Souls-III-Archipelago-client `main`, SoulsFormats `dsms`, SoulsIds `ap-fixes`, nightreign-enemy-rando `master`, Paramdex `master`, yet-another-tab-control `master` |
| **Tracked files** | build.ps1, push.ps1, all `*.md` (SPEC/BRIEF/TODO/HANDOFF/REFERENCE/TRIAGE/SYNC/NOTES/TESTPLAN), `poptracker/`, player `*.yaml`, `.gitignore`, `.gitmodules`, this doc |
| **.gitignored** | `elden_ring_artifacts/` (copyrighted game exe), `gen-test/`, the Nexus package dir, `eldenring.apworld`, `apconfig.json`, `*.log`, `*.bak`, `*.tar.gz`, `__pycache__/` |

> **Paramdex / yet-another-tab-control point at your forks (`4laric/…`), not the upstreams.** They were
> standalone clones before; they're now submodules so the local build patches (yatc's net6.0 retarget)
> ride along in the lockfile. One-time migration: commit each fork's working tree and push it to your
> 4laric remote *before* adding the submodule (or `push.recurseSubmodules=check` will reject the
> superrepo push for an unreachable SHA). See "First-time migration" below.

## Before you run it (pin policy = current HEADs)

A submodule pins a **committed SHA**, so for a clean `clone --recursive` later:

1. **Commit + push** the in-flight work in each fork first (the parallel-claude edits to
   SoulsRandomizers, Archipelago, the client). The script only *warns* on dirty/unpushed; it pins
   the current committed HEAD regardless, and uncommitted edits stay in each submodule's working
   tree.
2. The script's preflight prints which forks are dirty or ahead of their upstream — clear those, or
   accept that the pinned SHA must be pushed before anyone else can fetch it.

## Fresh clone on another machine

```powershell
git clone --recursive git@github.com:4laric/er-archipelago.git
# Paramdex + yet-another-tab-control are now submodules (your 4laric forks) — --recursive brings them.
# elden_ring_artifacts/ is gitignored (game exe) — copy it in from your own machine.
```
(If you cloned without `--recursive`: `git submodule update --init --recursive`.)

## Day-to-day

- **You changed code in a fork:** use `push.ps1 -Superrepo`, which commits+pushes the scoped paths
  in each fork **and then** bumps the superrepo's pinned SHAs + root tooling in one step:
  ```powershell
  .\push.ps1 -Message "what changed" -Superrepo        # forks, then superrepo pointers
  .\push.ps1 -Status -Superrepo                          # preview pending pointer moves
  .\push.ps1 -Message "bump" -Superrepo -Only NONE       # ONLY the superrepo (forks already pushed)
  ```
  The pinned SHAs are a one-line lockfile for "which versions of all 6 forks built together."
  (Manual equivalent: `git add <submodule-path> && git commit -m "bump <fork>"` at the root.)
- **Pull everyone's latest pinned versions:** `git submodule update --init --recursive`.
- **Advance a submodule to its branch tip:** `git submodule update --remote <path>` then commit.

## Submodule-aware git config (set by the script)

`.git/config` isn't committed, so `init-superrepo.ps1` re-applies these on every machine. They make
git treat the superrepo like the version-lockfile it is:

| config | value | why |
|---|---|---|
| `status.submoduleSummary` | `true` | `git status` shows *which* submodule commits moved, not just "subproject commit <sha>". |
| `diff.submodule` | `log` | `git diff` shows the commit log of a pointer bump. |
| `fetch.recurseSubmodules` | `on-demand` | pulling the superrepo fetches the submodule commits it references. |
| `push.recurseSubmodules` | `check` | **safety net:** `git push` of the superrepo FAILS if a pinned fork SHA isn't on its remote — exactly the "recursive clone breaks" footgun. Pairs with `push.ps1 -Superrepo` (which pushes forks first). |
| `submodule.recurse` | *off by default* | the one with a tradeoff — see below. |

**`submodule.recurse=true` (the `--recurse-submodules` you're thinking of):** makes `git checkout`,
`git pull`, etc. automatically move submodule working trees to the superrepo's pinned SHAs. It does
NOT affect `git clone` (use `clone --recursive`). It's great on a **consumer/sync machine** (one
command keeps all six forks at the locked versions), but **risky on your dev box**: a `pull`/`checkout`
that brings a new pointer will detach a submodule you're actively committing in. So the script leaves
it OFF by default; run `init-superrepo.ps1 -AutoSyncSubmodules` on machines that only consume the repo.
(You can always sync manually with `git submodule update --init --recursive`.)

## First-time migration: Paramdex + yatc → your forks (run once, on Windows)

These two were standalone clones of the public upstreams. Convert them to submodules backed by your
own forks so the local build patches survive a clean clone. **Do this before** running/re-running
`init-superrepo.ps1` (or pushing the superrepo). Forks `4laric/Paramdex` and
`4laric/yet-another-tab-control` already exist on GitHub.

```powershell
cd <repo root>

# --- yet-another-tab-control: has local edits (the net6.0 csproj retarget) — commit + push ---
cd yet-another-tab-control
git remote rename origin upstream                         # keep the upstream link
git remote add origin git@github.com:4laric/yet-another-tab-control.git
git status                                                # review what you're about to commit
git add -u                                                # stage MODIFIED tracked files only (no bin/obj)
git commit -m "AP build: SDK-style net6.0-windows retarget (GrayIris.Utilities)"
git push -u origin master
cd ..

# --- Paramdex: clean working tree — just publish the branch to your fork ---
cd Paramdex
git remote rename origin upstream
git remote add origin git@github.com:4laric/Paramdex.git
git push -u origin master            # if it was a shallow clone and push complains:
                                     #   git fetch --unshallow upstream ; then re-run the push
cd ..

# --- now register them as submodules (init-superrepo.ps1 does this for you; manual equivalent): ---
git submodule add --force git@github.com:4laric/Paramdex.git Paramdex
git submodule add --force git@github.com:4laric/yet-another-tab-control.git yet-another-tab-control
git config -f .gitmodules submodule.Paramdex.branch master
git config -f .gitmodules submodule.yet-another-tab-control.branch master
git add .gitmodules .gitignore Paramdex yet-another-tab-control
git commit -m "Track Paramdex and yet-another-tab-control as submodules (4laric forks)"
```

`git add -u` (not `-A`) keeps build artifacts out of the yatc commit. If you'd already run an earlier
`git submodule add` pointing at the *upstream* URLs, repoint them:
`git config -f .gitmodules submodule.<name>.url git@github.com:4laric/<name>.git ; git submodule sync`.

## Licensing (do not skip)

`SoulsRandomizers` is a **private** fork (thefifthmatt's randomizer is not freely licensed). Its
submodule URL appears in `.gitmodules`, so **keep the superrepo private** if you push it. The
contents aren't in the superrepo (only a gitlink + URL), but don't make this repo public while it
references the private fork.

Your `Paramdex` and `yet-another-tab-control` forks are forks of permissively-licensed upstreams, so
those can stay public — only `SoulsRandomizers` gates the superrepo's visibility.
