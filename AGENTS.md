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

> ### 🛑 NEVER Read/Edit/Write the mount. Not once, not "just to draft a file".
>
> **Every** file you author goes in the sandbox clone via bash, and reaches Alaric **only** by
> `git push`. There is no exception for "I'll just drop the first draft there and fix it later" —
> that is exactly how this goes wrong:
>
> 1. you Write a draft into the mount (it lands in Alaric's *working tree*, untracked/modified);
> 2. you iterate on the same file in the sandbox and push the **fixed** version;
> 3. his tree still holds your **stale draft**, so his next `git pull` collides with it.
>
> This happened on 2026-07-11 across 4 files (`shop_stock.py`, `enemy_drops.py`,
> `datamine_shop_rows.py`, `test_gf_arena_graces.py`) and produced a merge conflict whose HEAD side
> was a pile of bugs the sandbox had already fixed. It cost a session.
>
> **If you slip and touch the mount anyway: revert that file immediately**, before you do anything
> else — `git checkout -- <path>` on the mount, or tell Alaric to `git checkout origin/main -- <path>`.
> Do not leave it for later. Do not assume "it'll get overwritten by the pull" — it won't; it'll
> conflict.
>
> Reading is also unsafe: **the mount can serve a TRUNCATED view of a file.** A size/content diff
> against a mount path will invent corruption that isn't there (see §6). Read git blobs instead:
> `git show origin/main:<path>`.

## 2. The active branch is `main` (this changed — the old advice is inverted)

**`main` is now the live branch on both repos.** The greenfield work was merged into it and the
world ships as game `"Elden Ring"`. Just clone and work on `main`; no checkout dance.

⚠️ This section used to say the opposite — "the active branch is `feat/matt-free-backbone-mvp`, NOT
`main`". That is **stale and now actively harmful**: `feat/matt-free-backbone-mvp` is **0 commits
ahead of `main`** and `main` is **36 ahead of it**, so following the old advice checks you out onto a
branch that is missing all recent work. `origin/HEAD` may still point at the old branch — ignore it.

Verify rather than trust this file (it has been wrong before):

```bash
git fetch origin && git branch -r
git rev-list --count origin/main..origin/feat/matt-free-backbone-mvp   # expect 0
```

## 3. Session setup (sandbox is wiped between sessions — redo each time)

SSH to GitHub is blocked; use HTTPS + a fine-grained PAT (Alaric pastes one per session —
never save it to memory or a repo file):

```bash
printf 'https://x-access-token:%s@github.com\n' "$PAT" > /tmp/.gitcred; chmod 600 /tmp/.gitcred
git config --global credential.helper 'store --file=/tmp/.gitcred'
git config --global user.email 'alaric.mckenzie.boone@gmail.com'; git config --global user.name 'Alaric'
git clone --no-recurse-submodules https://github.com/4laric/er-archipelago.git ~/work/er-archipelago
cd ~/work/er-archipelago && git checkout main    # main IS the live branch (see §2); no checkout dance
git remote set-url origin https://github.com/4laric/er-archipelago.git   # keep the token out of .git/config
git config core.hooksPath tools/hooks                                    # enable the truncation gate
```

Repo is ~83M; `--no-recurse-submodules` keeps it light.

## 4. The Rust client is a separate repo

The client lives in submodule `from-software-archipelago-clients` (crate
`eldenring-archipelago`), branch **`main`**. Clone it over HTTPS the same way.

⚠️ This section used to say **`eldenring-client-draft`**. That branch **no longer exists on origin** —
the client repo has only `main`. (Same correction as §2.) ### You do NOT have to hand every Rust change to Alaric to compile

This section used to say flatly "`cargo build`/`test` runs on Windows". **That is misleading**, and on
2026-07-11 it cost **three** build round-trips on nothing but wrong symbol names. Two ways to get a
compile check without touching the Windows box:

**1. CI is the cheap one — it gates `push` to `main`.**
`from-software-archipelago-clients/.github/workflows/test.yaml` runs on `windows-latest` on every
**push to `main`** (and `workflow_dispatch`), in this order: `cargo build`, then
`cargo test -p er-codec -p er-semver -p er-logic -p eldenring-archipelago`, then `cargo fmt -- --check`,
then `cargo clippy -- -D warnings` **and** `cargo clippy --features=profile -- -D warnings`. It used to
trigger on `pull_request` **only**, so pushes straight to `main` sailed past it; fixed 2026-07-11. So a
`.rs` push buys a full Windows build + test + fmt + clippy for free — a compile error, a broken test, a
format nit, or a clippy lint all come back red.
⚠️ **You cannot READ that run from the agent sandbox.** `git push` over `github.com` works, but
`api.github.com` (and therefore `gh`) is **not reachable here** — it 502s through the egress proxy. So
do NOT tell Alaric you "checked the CI run"; you can't. Push the fix and hand him the Actions link
(`https://github.com/4laric/from-software-archipelago-clients/actions?query=branch%3Amain`) — the runner
(or Alaric) confirms green. Reason about fmt/clippy yourself before pushing instead of relying on seeing
the result.

**2. Cross-compile from Linux — `xcompile-client-linux.sh` (repo root).**
It builds the real `eldenring_archipelago.dll` for `x86_64-pc-windows-msvc` from a Linux host via
`cargo-xwin` (auto-downloads the MSVC CRT/SDK). Needs **sudo, ~4-5 GB free disk, and crates.io reachable**.
⚠️ The agent sandbox usually **cannot** run it — it is disk-capped (~9.6 GB, typically >95% used), so the
SDK download fails. Use it on a real Linux box / WSL2 / a CI runner. Pure-logic crates are host-native
and cheap either way: `cargo test -p er-codec -p er-semver -p er-logic`.

**3. If you still cannot compile, ASK rather than guess.** The `eldenring` crate is **not vendored in the
sandbox**, so its type and method names are unknowable from there. Guessing them is what burned the three
round-trips. Ask Alaric to paste the relevant names once. Known-settled naming lives in the module doc
comments of `check_lots.rs` / `enemy_drops.rs`:

```
eldenring::cs::ItemLotParam_map / ItemLotParam_enemy   (snake_case, not CamelCase)
eldenring::param::ITEMLOT_PARAM_ST                     (ONE row struct shared by BOTH lot tables)
row.set_lot_item_id01..08                              (no underscore before the digits)
use fromsoftware_shared::FromStatic;                   (required for SoloParamRepository::instance_mut)
```

You still need **Windows to RUN** the dll (it hooks a live Elden Ring process). Push your `.rs` fix to
client `main`. The world repo's CI checks the client out at its **own main** (not the pinned gitlink —
see `tests.yaml`), so your fix is exercised and the cross-repo generator gates run **without any
submodule bump**; a stale gitlink never reddens CI. The superproject gitlink is just a pin so a fresh
clone gets the matching DLL, and **`build.ps1 -Rust`/`-All` now auto-bumps it** (guarded: only when the
client submodule is clean, already on `origin/main`, and actually behind the pin — added 2026-07-20,
replacing the hand-run `git add from-software-archipelago-clients && git commit`). So do NOT tell Alaric
to bump it as boilerplate — his next `build.ps1` does it. Verify (see §7) and only mention it if it is
genuinely behind AND he has not re-run the build.

## 5. You CAN regenerate + test the apworld in-sandbox

The licensing-restricted game data lives on the **mount** at `elden_ring_artifacts/`
(`.gitignore`d — never commit it). Symlink it in and `gen_data.py` runs:

```bash
ln -sfn <MOUNT>/elden_ring_artifacts ~/work/er-archipelago/elden_ring_artifacts
cd ~/work/er-archipelago/greenfield && python3 gen_data.py    # regenerates eldenring/*.py deterministically
```

Test the world (provisions a Python-3.11 AP runtime under `~/.greenfield-ci`):

```bash
bash greenfield/provision-linux-env.sh        # once per session
AP=~/.greenfield-ci/ap; PY=~/.greenfield-ci/.venv/bin/python
rm -rf "$AP/worlds/eldenring"; cp -r greenfield/eldenring "$AP/worlds/eldenring"
cp greenfield/region_map.csv "$AP/worlds/eldenring/region_map.csv"   # gen INPUT the sweep-scoping oracle needs (else it skips)
cd "$AP" && AP_NONINTERACTIVE=1 SKIP_REQUIREMENTS_UPDATE=1 "$PY" -m pytest -q -p no:cacheprovider worlds/eldenring/tests/
```

Generated files (`eldenring/data.py`, `boss_data.py`, `boss_sweeps.py`, `region_open_flags.py`,
`item_ids.py`, `location_tags.py`, `region_play_ids.py`, …) are **regenerated, never hand-edited** —
change `gen_data.py` and regen. Committing the regenerated data is fine (same artifacts + generator ⇒
byte-matches a Windows regen; the DATA DRIFT gate reconciles if not).

**Do NOT hand Alaric a per-file regen checklist.** On his box `build.ps1 -All` (⊃ `-Greenfield`) runs
the WHOLE deterministic regen: `gen-greenfield.ps1` → the datamine + `gen_data.py`, which rewrites
**every** `eldenring/*.py` generated module **and** re-blesses both stamp files (`_gen_stamp.json` +
each module's `_GEN_STAMP`), and it also regenerates the client's THREE cross-repo tables
(`tracker_regions.rs`, `contract_gen.rs`, and `region_locks.rs` — the last baked from the
`region_groups` spine via `tools/gen_region_locks.py`; it was omitted from `build.ps1` until
2026-07-17, so a `region_groups` change used to ship a stale client `region_locks.rs` until the
`test_gf_data` / `gen_region_locks --check` drift gate failed — now wired). So if your change touched a GENERATOR or a gen INPUT
(`gen_data.py`, `region_groups.py`, a datamined `.tsv`/`.csv`), say it **once** — "needs a
`-Greenfield`/`-All` regen on your box" — never a file-by-file "remember to regenerate X.py, re-bless
the stamps, rerun the tracker gen, …". He runs `-All`; it covers all of it. If you already regenerated
in-sandbox per this section, the committed data is correct and byte-matches his regen — the ONLY thing
his run adds is the real artifact-hash stamp, which the freshness gate flags for him on its own. Don't
narrate that as a chore.

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
- `git fetch` + `git rebase origin/main` before pushing (Alaric pushes concurrently, often
  mid-session — re-fetch late, not once at the start); resolve/regen if the rebase touched
  generated files, then `git push origin HEAD:main`.
  ⚠️ This bullet used to name `feat/matt-free-backbone-mvp` as the rebase/push target. That was
  **stale and contradicted §2** — rebasing onto it would drop every recent commit. `main` is the
  target on both repos. (Corrected 2026-07-14.)
- Relay commit SHAs to Alaric explicitly. Two things NOT to recite as boilerplate:
  - **"needs a submodule bump"** — VERIFY before saying it. `git ls-tree origin/main from-software-archipelago-clients`
    (the pinned gitlink) vs `git ls-remote https://github.com/4laric/from-software-archipelago-clients.git refs/heads/main`
    (client HEAD). Equal ⇒ already current, say nothing. `build.ps1 -Rust`/`-All` AUTO-bumps the gitlink
    (guarded; see §4), so even when it is behind, Alaric's next build fixes it — mention it only if it is
    behind AND he has not re-run the build. The world CI tests against client main regardless, so a bump
    is never required for green CI. (Corrected 2026-07-20: this line used to demand a bump unconditionally.)
  - **"needs a Windows cargo build"** — only when you actually pushed a client `.rs` change (the push-to-`main`
    CI does that build; hand over the Actions link, don't claim you read the run).
