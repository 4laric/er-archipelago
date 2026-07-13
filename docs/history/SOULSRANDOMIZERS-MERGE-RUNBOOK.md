# SoulsRandomizers merge — runbook (run on Windows)

## What the divergence actually is
- **ours** `b3e9e47` (branch `ap-sync-2026-06-13`) vs **theirs** `6c1b030`, merge-base `82abd3b`.
- Filtering out line-ending noise, **theirs has only 3 files with real source changes** —
  `ArchipelagoForm.cs`, `EnemyRandomizer.cs`, `MiscSetup.cs` (AP notify / modal-suppression /
  enemy-rando fix). **All three are already in ours, byte-identical in content.**
- ours is a **strict source superset**: adds `RegionFogGates.cs` (+441), 3 test files, DLC-unstrip artifacts.
- Theirs' two real contributions ours lacks:
  1. **LF renormalization + `.gitattributes` (`text=auto`)** — the reason theirs looks like ~45k changed lines.
  2. Nothing else in source.
- The 24 "binary conflicts" (`regulation.bin` + `event/*.emevd.dcx`) are **baked outputs**, not mergeable text.
  ours already contains all of theirs' source logic, so ours' binaries are kept (rebake optional, see step 3).

## Decisions taken
- **Keep ours' content; record theirs as merged** (so it stops showing as diverged).
- **Adopt LF + theirs' `.gitattributes`.**

---

## Commands

```powershell
cd C:\Users\alari\Documents\er-archipelago\SoulsRandomizers

# 0. If git reports "unknown index entry format" (the index was corrupt in the sandbox),
#    rebuild it from HEAD — no working-tree changes:
del .git\index
git reset

# Sanity: should print b3e9e472f057b607c403176280ea35bed0c2bfdc on branch ap-sync-2026-06-13
git rev-parse HEAD
git status   # ensure clean before proceeding

# 1. Adopt theirs' .gitattributes, then renormalize text to LF (binaries excluded by the rules)
git checkout 6c1b030 -- .gitattributes
git add --renormalize .
git commit -m "Adopt .gitattributes (text=auto) + renormalize text to LF"

# 2. Record theirs as merged while keeping ours' tree (ours is the source superset)
git merge -s ours 6c1b030 -m "Merge ap-sync 6c1b030: ours is source superset; LF renorm adopted; binaries kept from ours"

# 3. (OPTIONAL) Gold-standard binaries: rebake regulation.bin / event artifacts from the merged
#    source, then commit. Only needed if you want the artifacts regenerated rather than kept-from-ours.
#    .\build.ps1 ...   # your normal bake
#    git add -A; git commit -m "Rebake artifacts after merge"
```

## Then conclude the superrepo merge with the new submodule pointer

```powershell
cd C:\Users\alari\Documents\er-archipelago

# The superrepo merge is already resolved & staged; SoulsRandomizers currently points at the
# pre-merge ours commit. Update it to the new merge commit, then conclude:
git add SoulsRandomizers
git commit --no-edit
# If it complains about .git\index.lock:  del .git\index.lock   (stale/phantom)  then re-run.
```

## Notes
- `.gitattributes` marks `.dcx/.bin/.dll/.exe/.pdb/.png/.dds/.tpf/.fmg/.bnd/.bhd/.bdt/...` as `binary`,
  so `--renormalize` will not touch any game artifact — only real text (`.cs`, `.md`, etc.).
- No work from theirs is lost: its only source changes already exist in ours; the merge commit
  records its history so it won't resurface as divergence.
