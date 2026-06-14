# ER-Archipelago superrepo

Makes this root a git repo that **submodules the 6 4laric forks** and **tracks the root tooling**
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
| **Submodules (6 forks)** | Archipelago `ap-sync-2026-06-13`, SoulsRandomizers `ap-sync-2026-06-13`, Dark-Souls-III-Archipelago-client `main`, SoulsFormats `dsms`, SoulsIds `ap-fixes`, nightreign-enemy-rando `master` |
| **Tracked files** | build.ps1, push.ps1, all `*.md` (SPEC/BRIEF/TODO/HANDOFF/REFERENCE/TRIAGE/SYNC/NOTES/TESTPLAN), `poptracker/`, player `*.yaml`, `.gitignore`, `.gitmodules`, this doc |
| **.gitignored** | `Paramdex/`, `yet-another-tab-control/` (third-party upstreams), `elden_ring_artifacts/` (copyrighted game exe), `gen-test/`, the Nexus package dir, `eldenring.apworld`, `apconfig.json`, `*.log`, `*.bak`, `*.tar.gz`, `__pycache__/` |

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
# the 2 upstreams are NOT submodules — re-clone them into the root:
git clone https://github.com/soulsmods/Paramdex.git
git clone https://github.com/thefifthmatt/yet-another-tab-control.git
# elden_ring_artifacts/ is gitignored (game exe) — copy it in from your own machine.
```
(If you cloned without `--recursive`: `git submodule update --init --recursive`.)

## Day-to-day

- **You changed code in a fork:** commit+push inside the submodule as usual, then in the superrepo
  `git add <submodule-path> && git commit -m "bump <fork>"` to move the pinned SHA. `push.ps1`
  already commits inside each repo; the superrepo just records which SHAs go together — a one-line
  lockfile for "which versions of all 6 forks built together."
- **Pull everyone's latest pinned versions:** `git submodule update --init --recursive`.
- **Advance a submodule to its branch tip:** `git submodule update --remote <path>` then commit.

## Licensing (do not skip)

`SoulsRandomizers` is a **private** fork (thefifthmatt's randomizer is not freely licensed). Its
submodule URL appears in `.gitmodules`, so **keep the superrepo private** if you push it. The
contents aren't in the superrepo (only a gitlink + URL), but don't make this repo public while it
references the private fork.
