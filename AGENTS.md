# AGENTS.md — orientation for AI agents working on this repo

Read this first. It's the git + regen + test workflow that keeps agent edits safe and
reviewable. For the *quality bar* (what a good change looks like) read `CONTRIBUTING.md`.

---

## 1. There are TWO working copies — know which you're touching

| Copy | Where | Reached by | Use for |
|------|-------|-----------|---------|
| **Mount** | `…\Documents\er-archipelago` (Alaric's real Windows repo) | the harness **Read / Edit / Write** tools | reading; Alaric builds/tests here |
| **Sandbox clone** | `~/work/er-archipelago` (a fresh clone in the Linux sandbox) | **bash** (`mcp__workspace__bash`) | **all editing, regen, tests, commits, pushes** |

They are different filesystems. `Edit` writes the mount; `bash` sees the sandbox clone.
**Do all real work in the sandbox clone via bash.** If you edit the mount by accident,
revert it so Alaric's `git pull` stays clean. This mismatch has cost round-trips.

## 2. The active branch is `feat/matt-free-backbone-mvp` — NOT `main`

`main` is a stale public snapshot (no `greenfield/`, ~dozens of commits behind). Cloning
defaults to it and looks empty of all recent work — that's the trap, not a broken clone.
Always:

```bash
git checkout -B feat/matt-free-backbone-mvp origin/feat/matt-free-backbone-mvp
```

## 3. Session setup (sandbox is wiped between sessions — redo each time)

SSH to GitHub is blocked; use HTTPS + a fine-grained PAT (Alaric pastes one per session —
never save it to memory or a repo file):

```bash
printf 'https://x-access-token:%s@github.com\n' "$PAT" > /tmp/.gitcred; chmod 600 /tmp/.gitcred
git config --global credential.helper 'store --file=/tmp/.gitcred'
git config --global user.email 'alaric.mckenzie.boone@gmail.com'; git config --global user.name 'Alaric'
git clone --no-recurse-submodules https://github.com/4laric/er-archipelago.git ~/work/er-archipelago
cd ~/work/er-archipelago && git checkout -B feat/matt-free-backbone-mvp origin/feat/matt-free-backbone-mvp
git remote set-url origin https://github.com/4laric/er-archipelago.git   # keep the token out of .git/config
git config core.hooksPath tools/hooks                                    # enable the truncation gate
```

Repo is ~83M; `--no-recurse-submodules` keeps it light.

## 4. The Rust client is a separate repo

The client lives in submodule `from-software-archipelago-clients` (crate
`eldenring-archipelago`), branch **`eldenring-client-draft`**. Clone it over HTTPS the same
way. Edit `.rs` files here, but **`cargo build`/`test` runs on Windows** (net/detour deps are
Windows-only). Push your `.rs` fix to `eldenring-client-draft`; Alaric pulls + builds and bumps
the submodule pointer. The `er-logic` crate is host-testable (`cargo test -p er-logic`) if a
Rust toolchain is present.

## 5. You CAN regenerate + test the apworld in-sandbox

The licensing-restricted game data lives on the **mount** at `elden_ring_artifacts/`
(`.gitignore`d — never commit it). Symlink it in and `gen_data.py` runs:

```bash
ln -sfn <MOUNT>/elden_ring_artifacts ~/work/er-archipelago/elden_ring_artifacts
cd ~/work/er-archipelago/greenfield && python3 gen_data.py    # regenerates eldenring_gf/*.py deterministically
```

Test the world (provisions a Python-3.11 AP runtime under `~/.greenfield-ci`):

```bash
bash greenfield/provision-linux-env.sh        # once per session
AP=~/.greenfield-ci/ap; PY=~/.greenfield-ci/.venv/bin/python
rm -rf "$AP/worlds/eldenring_gf"; cp -r greenfield/eldenring_gf "$AP/worlds/eldenring_gf"
cd "$AP" && AP_NONINTERACTIVE=1 SKIP_REQUIREMENTS_UPDATE=1 "$PY" -m pytest -q -p no:cacheprovider worlds/eldenring_gf/tests/
```

Generated files (`eldenring_gf/data.py`, `boss_data.py`, `boss_sweeps.py`, `region_open_flags.py`,
`item_ids.py`, `location_tags.py`, …) are **regenerated, never hand-edited** — change `gen_data.py`
(or the upstream `matt-free-pipeline/`) and regen. Committing the regenerated data is fine (same
artifacts + generator ⇒ byte-matches a Windows regen; the DATA DRIFT gate reconciles if not).

### Datamine joins that work in the sandbox
- **Item-lot flag → map:** the flag encodes it — `X0SS7000` = map `mX_SS` (e.g. `40017000` = `m40_01`).
- **Map/sub-dungeon → region:** join `grace_flags.tsv` (mapTile→warp) → `grace_region_map*.tsv`
  (warp→play_region) → `REGION_ID_MAP.md` (play_region→region). Use this instead of MSBs —
  `soulstruct` is **Oodle-blocked** on packed `.msb.dcx` (the Oodle DLL is Windows-only).
- Decompiled EMEVD is greppable text at `elden_ring_artifacts/event/*.emevd.dcx.js`.

## 6. The truncation gate (why edits are safe)

The sandbox mount can silently truncate/NUL-pad large writes. Tools guard against it:
- `tools/check_integrity.py` — flags zero-byte / NUL / truncated-syntax / EOF-imbalance
  (`--staged`, `--tracked`, or explicit files). Runs as the `core.hooksPath tools/hooks`
  pre-commit hook (`git commit --no-verify` to bypass).
- `tools/safe_publish.sh SRC DST` — atomic same-FS rename publish with byte+sha verify.
- Run `check_integrity` against **git blobs / the real clone**, not sandbox *mount* paths
  (the mount can serve a truncated view and false-alarm).

## 7. Commit + push checklist

- Edit in the sandbox clone; regen if you touched a generator; run the tests.
- Stage explicitly — **never `git add -A`** (the repo is public and game-data-purged; don't
  leak the artifacts symlink). `git diff --cached --stat` before committing.
- The pre-commit hook runs `check_integrity --staged` automatically.
- `git fetch` + `git rebase origin/feat/matt-free-backbone-mvp` before pushing (Alaric pushes
  concurrently); resolve/regen if the rebase touched generated files, then
  `git push origin HEAD:feat/matt-free-backbone-mvp`.
- Relay commit SHAs + "needs a Windows cargo build / submodule bump" to Alaric explicitly.
