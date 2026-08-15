# AGENTS.md — orientation for AI agents working on this repo

Read this first. It's the git + regen + test workflow that keeps agent edits safe and
reviewable. For the *quality bar* (what a good change looks like) read `CONTRIBUTING.md`.

---

## 1. There are TWO working copies — know which you're touching

| Copy | Where | Reached by | Use for |
|------|-------|-----------|---------|
| **Mount** | `…\Documents\er-archipelago` (Alaric's real Windows repo) | the harness **Read / Edit / Write** tools | **nothing — not even reading** (see the ban below). Alaric builds/tests/regens here |
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

> ### 🛑 SUBAGENTS DO NOT INHERIT THIS BAN. Restate it in every brief.
>
> A subagent gets your prompt, not this file. If you do not name the ban, it will find the mount by
> `find`/`ls` and read it — the mount path is discoverable and looks like a normal checkout.
>
> **This happened on 2026-07-30.** A survey agent was asked to audit the client for unguarded
> pointer derefs, read the tree through
> `/sessions/<session>/mnt/er-archipelago/from-software-archipelago-clients`, and reported it as
> *"identical tree"* to the sandbox clone. Two of its findings were **false**: it reported the
> boss-sweep flag flush as having no read-back (it calls `sweep_flush::retire`, which is exactly a
> read-back) and `marker::commit` as issuing 66 flag writes per frame (it is idempotent once
> committed). Both were caught only because the findings were re-verified against the clean clone
> before anything was built on them. Guards against non-problems would otherwise have shipped.
>
> So, two rules:
>
> 1. **Put the ban in the brief, with the path**, e.g. *"🛑 Never read `/sessions/*/mnt/er-archipelago`
>    — that is Alaric's live Windows tree and it serves silently TRUNCATED files. Work only in
>    `<your sandbox clone>`."* Also give the agent the clone path it SHOULD use, or it will go
>    looking.
> 2. **Re-verify anything load-bearing a subagent returns**, against the clone, before you act on
>    it — the same standard §7 sets for your own claims. A subagent's citation is a lead, not a
>    fact; a truncated read produces confident, well-formatted, wrong file:line evidence, which is
>    the exact failure mode CONTRIBUTING's "silent wrong answer" section is about.

## 2. Which branch is live CHANGES — verify it, never trust this line

**`main` is the trunk on both repos.** But feature work does not always live there, and *this section
has been wrong twice*, in both directions:

- it once said "the active branch is `feat/matt-free-backbone-mvp`, NOT `main`" — by then that branch
  was 0 ahead of `main` and 36 behind, so following it checked you out onto a tree missing every
  recent commit;
- it was then corrected to a flat "`main` is the live branch, just clone and work on it" — which is
  what you are reading now, and it is **also** incomplete.

**Derived 2026-07-25 — a SNAPSHOT, not the answer. Re-run the commands below before you trust it:**

| repo | trunk | where live work is | note |
|---|---|---|---|
| `er-archipelago` (world) | `main` | **`main`** | `feat/natural-progression-mode` — named here as "live" on 07-24 — is now **0 ahead / 65 behind** `main`: merged and finished. No branch on origin holds live work (see below). Work on `main` |
| `from-software-archipelago-clients` (client) | `main` | `main` | push straight to `main`; that push is the Windows build gate (§4) |

Of the 26 non-`main` branches on the world origin, **21 are 0 ahead** (fully merged) and the other 5
carry 1-3 commits each while sitting 176-654 behind — stale scraps from July 8-21
(`agent/agents-md-client-note`, `agent/coverage-gate`, `agent/main-gate-grace-scadu-altus`,
`agent/surface-and-consumable`, `feat/spirit-ash-tiers`), not workplaces. Worth a skim before you
re-solve something, worth nothing as a base.

⚠️ **This table has now rotted three times, in three different directions:**
`feat/matt-free-backbone-mvp` (already dead when it was recommended) → a flat "`main` is the live
branch" (right trunk, wrong claim about where work happens) → `feat/natural-progression-mode` (true
the day it was written, merged two days later). Its half-life is about a week. **Derive, then read.**

So: **there is no standing answer to "which branch".** Do not read one out of this file. Derive it,
and if the repo state is ambiguous, ask Alaric — a wrong branch costs a whole session's work.

```bash
git ls-remote --heads origin | awk '{print $2}' | sort   # what actually exists, right now
# ahead/behind between trunk and a candidate branch (left = main-only, right = branch-only):
git fetch origin && git rev-list --left-right --count origin/main...origin/<branch>
```

> 🛑 **A `--depth N` clone makes `rev-list --left-right` LIE, silently.** The left-hand (main-only)
> number saturates at your clone depth, so on a `--depth 20` clone every branch reports exactly
> `20 <right>` and they all look equally divergent. It does not warn; it is a confident wrong number
> of precisely the kind CONTRIBUTING's "silent wrong answer" section is about. `git fetch --unshallow`
> before you measure, or don't shallow-clone at all. (Found the hard way, 2026-07-25.)

Read that output the way §7 wants you to read any derivation: a branch that is **0 ahead** of `main`
is a finished/merged branch and is not where work goes; a branch that is **behind** `main` needs a
rebase before you add to it. `origin/HEAD` may still point at a long-dead branch — ignore it.

(Rewritten 2026-07-24: the previous "`main` is the live branch" text was correct about the trunk and
wrong about where work happens, which is the same failure mode as the `feat/matt-free-backbone-mvp`
advice it replaced. The section is now a *procedure*, not a fact, because the fact keeps rotting.)

## 3. Session setup (sandbox is wiped between sessions — redo each time)

SSH to GitHub is blocked; use HTTPS + a fine-grained PAT (Alaric pastes one per session —
never save it to memory or a repo file):

```bash
printf 'https://x-access-token:%s@github.com\n' "$PAT" > /tmp/.gitcred; chmod 600 /tmp/.gitcred
git config --global credential.helper 'store --file=/tmp/.gitcred'
git config --global user.email 'alaric.mckenzie.boone@gmail.com'; git config --global user.name 'Alaric'
git clone --no-recurse-submodules https://github.com/4laric/er-archipelago.git ~/work/er-archipelago
cd ~/work/er-archipelago && git checkout <the branch you VERIFIED per §2>   # do NOT assume main
git remote set-url origin https://github.com/4laric/er-archipelago.git   # keep the token out of .git/config
git config core.hooksPath tools/hooks                                    # enable the truncation gate
```

Repo is ~83M; `--no-recurse-submodules` keeps it light.

**If you only need to READ or edit a file or two, do not clone 83M.** The sandbox `/` is disk-capped
and usually >95% full, and a second full clone can fail mid-way and leave an unremovable tree owned
by `nobody`. A blobless sparse clone is ~300K and pushes normally:

```bash
git clone --depth 1 --single-branch -b main --filter=blob:none --no-checkout \
    https://github.com/4laric/er-archipelago.git ~/work/er-doc
cd ~/work/er-doc && git sparse-checkout init --no-cone && git sparse-checkout set AGENTS.md
git checkout main
```
(2026-07-30: used exactly this to edit AGENTS.md when a full clone would not fit.)

## 4. The Rust client is a separate repo

The client lives in submodule `from-software-archipelago-clients` (crate
`eldenring-archipelago`), branch **`main`**. Clone it over HTTPS the same way.

⚠️ This section used to say **`eldenring-client-draft`**. That branch **no longer exists on origin** —
the client repo has only `main`. (Same correction as §2.)

### You do NOT have to hand every Rust change to Alaric to compile

This section used to say flatly "`cargo build`/`test` runs on Windows". **That is misleading**, and on
2026-07-11 it cost **three** build round-trips on nothing but wrong symbol names. Two ways to get a
compile check without touching the Windows box:

**1. CI is the cheap one — but ONLY on `main` or a PR. A side-branch push runs NOTHING.**

> ⚠️ **Corrected 2026-07-30.** The heading below used to read "it gates `push` to `main`" and the
> paragraph promised "a `.rs` push buys a full Windows build + test + fmt + clippy for free". True
> for `main`; **false for every other branch**, and the difference is invisible — a side-branch push
> succeeds, no run appears, and nothing says why. The triggers are `pull_request`, `push: [main]`,
> and `workflow_dispatch`, so for work on a branch **open the PR** and the `pull_request` trigger
> gives you the same four gates. Cost when missed: a green-looking push with no compile check at all.
`from-software-archipelago-clients/.github/workflows/test.yaml` runs on `windows-latest` on every
**push to `main`** (and `workflow_dispatch`), in this order: `cargo build`, then
`cargo test -p er-codec -p er-semver -p er-logic -p eldenring-archipelago`, then `cargo fmt -- --check`,
then `cargo clippy -- -D warnings` **and** `cargo clippy --features=profile -- -D warnings`. It used to
trigger on `pull_request` **only**, so pushes straight to `main` sailed past it; fixed 2026-07-11. So a
`.rs` push buys a full Windows build + test + fmt + clippy for free — a compile error, a broken test, a
format nit, or a clippy lint all come back red.
✅ **You CAN read that run from the agent sandbox — so READ IT.** (Corrected 2026-07-25; this block
used to say `api.github.com` "is not reachable here — it 502s through the egress proxy". It is
reachable, and for these PUBLIC repos an occasional read needs **no token**.)

⚠️ **Two API facts added 2026-07-30, both learned the expensive way:**
- **Unauthenticated reads RATE-LIMIT to 403 after roughly ten calls**, and a 403 here looks exactly
  like the "access not enabled" refusal below. Poll a run's status with
  `-H "Authorization: Bearer $PAT"` from the start and the ambiguity never arises.
- ⭐ **REST WRITES WORK with a PAT.** `POST /repos/<owner>/<repo>/pulls` returned **HTTP 201** and
  opened a real PR from the sandbox. A 2026-07-23 note claimed every `api.github.com` write was
  403-gated by the egress proxy "REGARDLESS of the PAT", and that claim had already bought one
  hand-built PowerShell workaround. **Try the call before you build the workaround** (see rule 5,
  *RUN the tool, do not read it* — it applies to claims about the environment too, including the
  ones written in this file).

```bash
curl -s "https://api.github.com/repos/4laric/from-software-archipelago-clients/actions/runs?branch=main&per_page=3" \
  | python3 -c "import sys,json;[print(r['head_sha'][:7],r['status'],r['conclusion']) for r in json.load(sys.stdin)['workflow_runs']]"
```

That false claim has already cost a real bug: on 2026-07-25 `cargo fmt --check` was RED on client
`main` across four commits (`c128ba0`…`a32f685`) while the agent told Alaric "CI is the gate" and never
looked. Hand him the Actions link as well
(`https://github.com/4laric/from-software-archipelago-clients/actions?query=branch%3Amain`), but never
substitute the link for the check — and still reason about fmt/clippy before pushing. CI is a backstop,
not a replacement for thinking.

**2. Cross-compile from Linux — `xcompile-client-linux.sh` (repo root).**
It builds the real `eldenring_archipelago.dll` for `x86_64-pc-windows-msvc` from a Linux host via
`cargo-xwin` (auto-downloads the MSVC CRT/SDK). Needs **sudo, ~4-5 GB free disk, and crates.io reachable**.
⚠️ The agent sandbox usually **cannot** run it — it is disk-capped (~9.6 GB, typically >95% used), so the
SDK download fails. Use it on a real Linux box / WSL2 / a CI runner. Pure-logic crates are host-native
and cheap either way: `cargo test -p er-codec -p er-semver -p er-logic`.

**2a. What the sandbox CAN and CANNOT build. `cargo` is absent, but you can INSTALL it — the
2026-07-24 "rustup is unreachable" finding was wrong, and the real blocker is `TMPDIR`.**
`cargo test -p er-logic` is the workhorse for anything decision-shaped (the whole replay tier lives
there, ~443 host tests, seconds to run). It is not preinstalled. `sudo` really is blocked
(no-new-privileges, so `apt-get install cargo` fails), but `sh.rustup.rs` is **reachable** — what
failed on 07-24 was `mktemp -d`, because `$TMPDIR` and `$HOME` both point at `/sessions/<session>/`,
which is a SHARED 9.8 GB volume that is routinely 100% full. rustup reports that as
`error: command failed: mktemp -d`, which reads like a network/permission failure and is not one.
Point everything at `/tmp` (a different device, `/dev/sda1`, usually with room) and it just works:

```bash
export TMPDIR=/tmp RUSTUP_HOME=/tmp/rustup CARGO_HOME=/tmp/cargo CARGO_TARGET_DIR=/tmp/ertarget
curl -sSf https://sh.rustup.rs -o /tmp/ru.sh
sh /tmp/ru.sh -y --profile minimal --default-toolchain stable --no-modify-path   # ~40s
export PATH=/tmp/cargo/bin:$PATH
cargo test -p er-logic          # + cargo fmt -p er-logic -- --check, cargo clippy ... -D warnings
```

⚠️ It is ~1.8 GB installed (toolchain 1.2 G + registry 0.5 G) against a ~2 GB budget on `/tmp`, so
you cannot hold it AND `greenfield/provision-linux-env.sh` at once. Do the Rust half first, then
`rm -rf /tmp/rustup /tmp/cargo` and provision the Python env (which also needs `HOME` and
`GF_CI_HOME` redirected off `/sessions`: `HOME=/tmp/gfhome GF_CI_HOME=/tmp/gfci bash
greenfield/provision-linux-env.sh`). Reinstalling rust later costs ~40s.

Run `command -v cargo` before you plan around it, and if you choose not to install it, say plainly
that the Rust side is UNVERIFIED here and let the Windows CI be the gate. Do not describe a test run
you could not perform. The
`eldenring-archipelago` and `shared` crates **never** build here (imgui / MSVC / detour deps); verify a
change to those by inspection plus, if the risk is a type or symbol name, a throwaway crate that
typechecks the call against the real dependency version (e.g. `windows 0.62.2`). Do not report an
un-built `eldenring-archipelago` change as "verified" — push it and let the Windows CI say so.

**3. READ THE PINNED CRATE SOURCE. It is right here, and this section used to say it wasn't.**

⚠️ **Corrected 2026-07-30.** This point read: *"The `eldenring` crate is **not vendored in the
sandbox**, so its type and method names are unknowable from there."* The second half is **false**, and
believing it meant guessing (or asking Alaric to paste) names that were sitting on disk the whole time.

Any `cargo build`/`test` in the client workspace populates `$CARGO_HOME/git/checkouts/`. With the §2a
env (`CARGO_HOME=/tmp/cargo`):

```bash
grep -A3 'name = "eldenring"' Cargo.lock          # get the pinned rev -- do NOT guess it
ls /tmp/cargo/git/checkouts/fromsoftware-rs-*/    # >1 rev can be present; pick the LOCKED one
sed -n '1,80p' /tmp/cargo/git/checkouts/fromsoftware-rs-*/<rev>/crates/eldenring/src/cs/item_id.rs
```

On 2026-07-30 this settled, in one session, four things that had been open, guessed, or wrong:

* `param_id_raw, set_param_id_raw: 27, 0` (`cs/item_id.rs:56`) — the CATEGORY-STRIPPED row. That
  discharged a `NOTE(windows-verify)` in `reconcile_io.rs` which had parked a double-mask alternative
  in a comment as "MUST CONFIRM ON WINDOWS with a set->readback". No Windows run was ever needed.
* `is_normal_items_full()` / `is_key_items_full()` / `is_multiplay_key_items_full()`, plus per-list
  `_len`/`_capacity` and `global_capacity` (`cs/player_game_data.rs:424-618`) — the game keeps its own
  inventory-fullness bookkeeping. Read it rather than inferring capacity from a scan.
* `key_items_accessor` vs `key_items_head` (`:444`, `:485`) — comparing the two pointers tells you at
  runtime whether the accessor has switched to the multiplay key list.
* `pub storage: Option<OwnedPtr<EquipInventoryData>>` (`:138`) — the storage box is reachable; the
  client just never reads it.

🛑 **Source-verified is NOT compiled, and the two are different words** (same rule as §5's
"static-validated" vs "regenerated"). A throwaway `cargo check` crate depending on `eldenring` still
FAILS on Linux — `windows-future 0.2.1` does not typecheck against the resolved `windows-core`, and
copying the client `Cargo.lock` does not fix it because the root package differs. So: source-verify
every field and method name you use (cheap, and strictly better than guessing), then let the Windows
CI be the compile gate, and **say which of the two you did.**

**3b. Only if the name genuinely is not in the pinned source, ASK rather than guess.** Guessing is what
burned the three round-trips. Known-settled naming also lives in the module doc comments of
`check_lots.rs` / `enemy_drops.rs`:

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

## 5. What you can run in-sandbox: the tests, and (since `gen_inputs.db`) the regen too

⚠️ **Re-corrected 2026-08-06 — the regen DOES run in-sandbox now, via `gen_inputs.db`.**
`tools/gen_inputs.py` (2026-07-27) postdates the 2026-07-24 correction below and was built to end
exactly this hand-off: the bundle carries every param CSV and FMG/EMEVD input `gen_data` reads,
verbatim, and it is **committed** (~9 MB). So:

```bash
python tools/gen_inputs.py --extract elden_ring_artifacts   # ~1450 files, ~98 MB
python greenfield/gen_data.py
```

**Prove it before you trust it: run that on an UNMODIFIED tree and require `git diff` to be empty.**
It was, on `47df8f2` — byte-identical to the committed output, which is what makes a sandbox regen
real rather than a fake one. If that diff is ever non-empty, your bundle and the committed modules
disagree and you must stop, not "fix" the diff.

Two things this does NOT change: the **MSBs are deliberately not in the bundle**, so the Tier-2 MSB
datamines in §5a still need the box; and the §1 mount ban is untouched — extract into the sandbox
clone, never symlink the mount.

⚠️ **Corrected 2026-07-24, and now superseded in part by the note above.** This section used to say
"You CAN regenerate + test the apworld in-sandbox" and told you to `ln -sfn <MOUNT>/elden_ring_artifacts …`
into the sandbox clone. **That half was wrong and stays wrong**: symlinking the mount violates the §1
ban outright (and a truncated mount read of a param CSV is a silent-wrong-answer machine). The other
half — "a full `gen_data.py` regen needs the FMG/EMEVD/MSB side of `elden_ring_artifacts/` that the
sandbox does not have" — was true when written and is no longer.

**The licensing-restricted game data is Windows-only and stays there.** It is never copied, never
symlinked, never committed (`.gitignore`d).

- **Regen runs in the sandbox** off `gen_inputs.db` (above), and in CI. `build.ps1 -Greenfield` /
  `-All` on Alaric's box remains the Windows path and the only one that covers §5a Tier 2. If you
  regenerated here, say **"regenerated in-sandbox from `gen_inputs.db`, clean-tree diff verified
  empty"** — that is a different claim from "static-validated" and from "needs a regen on your box",
  and all three are still different words. Never fake one.
- **A small param-CSV subset can be staged in the sandbox** for datamine-shaped static work; the tools
  that support it honour the `ER_ARTIFACTS_VV` env override (`tools/datamine_flag_lots.py`,
  `tools/gen_check_lots_table.py`). This is *opt-in staging for a specific investigation*, not a
  standing capability — assume it is absent unless you put it there this session.
- **Static validation is the sandbox ceiling** for anything artifact-derived: you can prove a
  grouping/predicate/shape claim against staged CSVs, and you must label it as static-validated when
  you hand it over. "Static-validated" and "regenerated" are different words; do not swap them.
- **The world's pytest suite DOES run here**, and should, on every Python change (below).

Test the world in-sandbox (provisions a Python-3.11 AP runtime under `~/.greenfield-ci`) — from the
repo root of your sandbox clone:

```bash
bash greenfield/provision-linux-env.sh        # once per session
AP=~/.greenfield-ci/ap; PY=~/.greenfield-ci/.venv/bin/python
rm -rf "$AP/worlds/eldenring"; cp -r greenfield/eldenring "$AP/worlds/eldenring"
cp greenfield/region_map.csv "$AP/worlds/eldenring/region_map.csv"   # gen INPUT the sweep-scoping oracle needs (else it skips)
cd "$AP" && AP_NONINTERACTIVE=1 SKIP_REQUIREMENTS_UPDATE=1 "$PY" -m pytest -q -p no:cacheprovider worlds/eldenring/tests/
```

Generated files (`eldenring/data.py`, `boss_data.py`, `boss_sweeps.py`, `region_open_flags.py`,
`item_ids.py`, `location_tags.py`, `region_play_ids.py`, …) are **regenerated, never hand-edited** —
change `gen_data.py` and regen — **on Windows** (§5 above). The generator is deterministic, so the same
artifacts + generator byte-match wherever they run and the DATA DRIFT gate reconciles if they don't; that
is why committing regenerated data is fine when the regen was real. It is not a licence to produce one
here without the artifacts.

**Do NOT hand Alaric a per-file regen checklist.** On his box `build.ps1 -All` (⊃ `-Greenfield`) runs
the WHOLE deterministic regen: `gen-greenfield.ps1` → the datamine + `gen_data.py`, which rewrites
**every** `eldenring/*.py` generated module **and** re-blesses both stamp files (`_gen_stamp.json` +
each module's `_GEN_STAMP`), and it also regenerates the client's THREE cross-repo tables
(`tracker_regions.rs`, `contract_gen.rs`, and `region_locks.rs` — the last baked from the
`region_groups` spine via `tools/gen_region_locks.py`; it was omitted from `build.ps1` until
2026-07-17, so a `region_groups` change used to ship a stale client `region_locks.rs` until the
`test_gf_data` / `gen_region_locks --check` drift gate failed — now wired). So if your change touched a
GENERATOR or the region spine (`gen_data.py`, `region_groups.py`), say it **once** — "needs a
`-Greenfield`/`-All` regen on your box" — never a file-by-file "remember to regenerate X.py, re-bless
the stamps, rerun the tracker gen, …". He runs `-All`; it covers all of that. What you should NOT do is
claim the regen is already done: the artifacts are not here (§5), so the generated modules in your
commit are whatever the last real regen produced. Say "needs a `-Greenfield` on your box" once and stop.

> ⚠️ **A datamined `greenfield/*.tsv` is the EXCEPTION — `-All` does NOT regenerate it.** `gen_data`
> *consumes* those tables; it does not emit them. If your ROOT fix is in a datamine tool (e.g.
> `datamine_grace_ground.py`), its `--emit` is a **manual step you run FIRST**, then `-All`. Do not
> fold it into "just run -All" — see §5a.

### 5b. Standing up the AP env IN THE AGENT SANDBOX -- the recipe that actually works

`greenfield/provision-linux-env.sh` is the supported path and it is what to use on WSL2 or a real
box. **In the Cowork agent sandbox it does not finish**, for reasons that all look like something
else, so here is the working sequence and the trap behind each step. (Derived 2026-07-27; it ends
with `16 passed, 9766 subtests` on the AP-dependent half, so the whole pytest suite -- not just the
AP-free tier -- runs in-sandbox.)

```bash
O=/sessions/<session>/mnt/outputs          # the ONLY volume with room; / and /sessions run 100% full
# 1. Python 3.11 -- 3.10 IS NOT ENOUGH (AP 0.6.7 uses typing.Self in worlds/AutoWorld.py)
curl -sSL -C - -o $O/py311.tar.gz \
  "https://releases.astral.sh/github/python-build-standalone/releases/download/20260602/cpython-3.11.15%2B20260602-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
mkdir -p $O/py311 && tar -xzf $O/py311.tar.gz -C $O/py311 --skip-old-files   # RE-RUN until complete
PY=$O/py311/python/bin/python3.11
# 2. deps, in CHUNKS (the harness caps a bash call at 45s and pip is slow on the mount)
$PY -m pip install -q --no-cache-dir pyyaml typing-extensions platformdirs certifi colorama
$PY -m pip install -q --no-cache-dir schema jsonschema pathspec pytest
# 3. Archipelago at the pin, SPARSE (a full checkout will not finish inside one call)
git clone --depth 1 --branch "$(tr -d '[:space:]' < .ap-version)" --single-branch \
  https://github.com/ArchipelagoMW/Archipelago.git $O/gfci/ap
cd $O/gfci/ap && git sparse-checkout set --no-cone \
  '/*.py' '/worlds/*.py' '/worlds/generic/**' '/test/**' '/data/**' '/rule_builder/**'
# 4. install the world (AGENTS §5) and run
rm -rf worlds/eldenring && cp -r <repo>/greenfield/eldenring worlds/eldenring
cp <repo>/greenfield/region_map.csv worlds/eldenring/region_map.csv
TMPDIR=/tmp AP_NONINTERACTIVE=1 SKIP_REQUIREMENTS_UPDATE=1 \
  $PY -m pytest -q -p no:cacheprovider worlds/eldenring/tests/
```

**The four traps, each of which reads as a different problem than it is:**

- 🛑 **`TMPDIR` must be `/tmp` for pytest, and NOT on the outputs mount.** pytest's capture tmpfile
  vanishes there and you get `FileNotFoundError ... _pytest/capture.py:592 res = self.tmpfile.read()`
  at the END of a run -- which reads like a broken test, not a broken environment. (`HOME` and the
  pip/uv caches, by contrast, MUST be off `/sessions`, which is routinely 100% full -- same finding
  as the rustup `TMPDIR` note in §4. The two want opposite volumes; set them separately.)
- 🛑 **`uv python install 3.11` will not finish.** It downloads fine but then unpacks ~120 MB of
  small files onto the slow mount, and the per-call timeout kills it mid-extract leaving nothing
  behind. This looks like a network failure and is not one. Fetch the tarball with `curl -C -`
  (resumable across calls) and extract it yourself with `--skip-old-files`, which makes re-running
  effectively resumable too.
- 🛑 **A full AP checkout will not finish either** (~3500 files). Sparse-checkout it — but use
  `--no-cone` with the pattern list above. ⚠️ **`init --cone` does NOT keep the root `.py` files**,
  whatever this doc used to say: it leaves you with `test/` and `worlds/` only, and you then chase
  `ModuleNotFoundError: BaseClasses` → `pathspec` → `rule_builder` one 45 s call at a time, each of
  which reads like a missing dependency rather than a missing checkout. `rule_builder/` is needed
  too (`worlds/AutoWorld.py` imports it) and is easy to miss. Some unrelated worlds
  then fail to import (`worlds.sm` wants `variaRandomizer`); AP logs it and carries on with the rest
  registered. Harmless -- do not chase it.
- ⚠️ Python **3.10 is present and will get you a long way in** before dying on `typing.Self`. Check
  `python3 -V` before assuming the sandbox python is usable.

With this up you can run the AP-dependent tests, `tools/fill_regression.py`, and -- once
`tools/gen_inputs.py --extract` has put the inputs in place -- `gen_data.py` itself. That is the
difference between handing Alaric a tool to run and handing him a result.

### 5a. TWO regen tiers — do not conflate them (the spurious-regen trap)

More than one agent has "fixed" a datamine, told Alaric to "just run `-All`", and shipped nothing —
because `-All` ran `gen_data` against the **stale** tsv. Others hand-edited a `--emit` output to fake
the fix, desyncing it from its tool. **CI catches neither** (the tsvs are tracked; the artifacts/MSBs
are absent in CI). Know which tier your change is in:

- **Tier 1 — automated by `build.ps1 -All`/`-Greenfield`, and by `tools/regen_all.py`.** The chain
  is `datamine_boss_drops.py` → `datamine_boss_healthbars.py` → `gen_data.py` (rewrites the
  `eldenring/*.py` modules **and writes `_GEN_STAMP`**) → the cross-repo tables (`gen_region_locks`,
  `gen_contract`, `gen_area_tiers --check`) → **the three offline pages + `questline_dag.tsv`**.
  A change in `gen_data.py`, `region_groups.py`, a boss-drop/healthbar input, or any
  `eldenring/*.py` consumer → **`-All` covers it. Say it once.**

  🛑 **THE PAGES ARE PART OF TIER 1, and this doc used to omit them** (issue #699, 2026-08-15).
  `er-archipelago-check-browser.html`, `-desc-triage.html` and `-questline-dag.html` EMBED
  `inputs_hash`, so **any** change that moves the stamp — including a comment edit to `gen_data.py`,
  which is `FILE_INPUTS[0]` — re-stales all three, and the only thing that notices is CI's byte
  diff (`apworld generated output is STALE`). PR #698 went red for exactly one such line. That is
  why the recipe below is a single command and not a list.

  🛑🛑🛑 **AGENTS: THE TIER-1 REGEN IS A PRECONDITION OF YOUR PR, NOT A HANDOFF.** §5 above says the
  regen runs in the sandbox off the committed `gen_inputs.db`; this is the rule that follows from it.
  If your branch touches `gen_data.py`, `region_groups.py`, `region_spine.py`, or any
  `gen_manifest.FILE_INPUTS` entry, **run the full chain and commit its output before opening the
  PR.** A "source half" PR whose description asks Alaric to regen is not a deliverable — `.ps1` is a
  convenience wrapper, not a platform requirement:

  ```bash
  python3 tools/regen_all.py     # THE regen. inputs -> datamines -> gen_data (+stamp) -> tables -> pages
  git status --short             # everything it lists is generated output that belongs in THIS commit
  ```

  **One command on purpose.** `tools/regen_all.py` holds the step list; `build.ps1` and the CI
  `generators` job invoke the same file, so this block cannot drift from what CI checks — which it
  had, silently, for as long as the pages have been stamped. `python3 tools/regen_all.py --list`
  prints the steps and runs nothing. Sandbox-safe: the client-dependent steps SKIP loudly when the
  submodule is absent, and `--phases modules,pages` narrows it if you know what you are doing.
  `greenfield/eldenring/tests/test_gf_regen_all.py` is the gate that keeps the list complete — it
  goes red if a stamp-bearing artifact, or a `tools/build_*.py` that writes a root page, is not
  reachable from the entrypoint.

  🛑 **Order, not taste: the stamp is written and THEN read.** Finish every source edit first
  (`gen_data.py` is a declared input — a *comment* re-stales it), then run the entrypoint once.
  Rebuilding a page before the stamp leaves it carrying the previous hash, which is a red CI diff
  with no visible cause; it cost six rounds on world PR #481.

  **Why this is a rule and not advice (PR #526, 2026-08-10).** A region merge shipped as a source
  half, merged, and left `main` unable to regen. The regen was the only thing that would have found
  the tail: `MAJOR_BOSS_EXTRAS` and `features/legacy_key_gates` were still keyed on the folded region
  name, plus six test files. ⭐ **A region rename/merge has a source tail that grep does not find,**
  because the references are data keys in tables you did not think to open — and since every one is a
  `raise SystemExit`, **an aborting gate hides the next**, so they surface one per run. Budget 3–4
  regen loops for a region change and spend them before pushing, not one per CI round-trip.

- **Tier 2 — MANUAL, never in any `.ps1`.** The tracked `greenfield/*.tsv` tables are `gen_data`
  **inputs**, each emitted by its own datamine tool, run by hand — several need the unpacked witchy'd
  MSBs the build never touches. If your fix's root is one of these, run that tool's `--emit` yourself,
  **commit the regenerated tsv**, and only THEN does `-All` (via `gen_data`) pick it up. **Order is
  emit → gen_data, not the reverse**, and both land in the SAME commit.

  | tracked table | emitted by | needs |
  |---|---|---|
  | `grace_ground.tsv` | `tools/datamine_grace_ground.py --emit` | witchy'd m60/m61 **+ interior** MSBs |
  | `arena_graces.tsv` | `tools/datamine_arena_graces.py` | witchy'd MSBs |
  | `grace_names.tsv` | `tools/datamine_grace_names.py` | params / msgbnd |
  | `grace_flags.tsv`, `grace_region_map.tsv` | `tools/regen_grace_tables.py` | `BonfireWarpParam` |
  | `play_region_buckets.tsv` | `tools/datamine_play_regions.py` | `PlayRegionParam` |
  | `item_grace_coords.tsv` | `tools/datamine_item_grace_coords.py` | MSBs / params |
  | `dungeon_regions.tsv` | `tools/datamine_dungeon_regions.py` | committed grace tsvs |
  | `msb_flag_region.tsv` | `tools/datamine_msb_item_regions.py` | witchy'd MSBs |
  | `nearest_grace.tsv`, `tile_grace.tsv` | `tools/build_nearest_grace.py --extra-coords greenfield/boss_reward_coords.tsv`, `tools/build_tile_grace.py` | committed grace tsvs (sandbox-runnable) |
  | `shop_rows.tsv` | `tools/datamine_shop_rows.py` | params |
  | `synthetic_flag_recovery.tsv` | `tools/recover_synthetic_flags.py` | committed tsvs |

  If you **can't** run the MSB-gated tool in-sandbox (no unpacked MSBs here), say so plainly and hand
  Alaric the exact `--emit` command **and** the emit → `-All` order — never imply `-All` covers it.
  If you **can** (MSBs staged / a sandbox-runnable tool), emit it here and commit the fresh tsv so
  the tree is self-consistent. Never hand-edit a `--emit` output to nudge one row; re-emit the whole file.

### Datamine joins that work in the sandbox
- **Item-lot flag → map:** the flag encodes it — `X0SS7000` = map `mX_SS` (e.g. `40017000` = `m40_01`).
- **Map/sub-dungeon → region:** join `grace_flags.tsv` (mapTile→warp) → `grace_region_map*.tsv`
  (warp→play_region) → `REGION_ID_MAP.md` (play_region→region). Use this instead of MSBs —
  `soulstruct` is **Oodle-blocked** on packed `.msb.dcx` (the Oodle DLL is Windows-only).
- Decompiled EMEVD is greppable text at `elden_ring_artifacts/event/*.emevd.dcx.js`.
- **Reading the corpus by hand:** open `er-archipelago-check-browser.html` (root, no server, no
  artifacts). One offline page over all checks — full-text search plus facets for region, tag,
  map tile, and *property* (`missable`, `has lot gate`, `no map position`, `no nearest grace`,
  `shop row`), with per-check item lots, shop rows, gates, maps and nearest grace. Regenerate with
  **`python3 tools/regen_all.py`** (§5a) after any `gen_data.py` run — not the builder alone, which
  is how three stamped pages ended up with three different owners; it is AP-free and joins only
  committed greenfield data, so it can be rebuilt in the sandbox. CI regenerates it and fails on a
  non-empty diff, and `tests/test_gf_check_browser.py` gates totality/agreement/determinism.
  It is a **reader**, not an oracle: it shows what the world already declares, and any number it
  displays is a join over the same tsvs the generators use.
- **Gate evidence is PLURAL.** The browser joins all four corpora that document gating and counts
  them separately: `lot_gates` 110 · `treasure_enablers` 136 · `esd_gifts` 48 · `esd_gates` 405 —
  **union 684**, not 110. Each is rendered beside its own tsv header VERBATIM, one click away,
  because those headers carry the polarity rules: `EndIf` has INVERTED sense, `self_set_flags` is a
  MEMO not a prerequisite, and `NO_ENTITY_HANDLE` is *proof of no gating*, not mystery. 🛑 Never
  flatten a verdict to "gated: yes/no" — a test fails if you normalise the strings away. A check
  with nothing in all four is labelled **"absence of evidence across four tables"**, not "ungated"
  (the 5 Edgar checks read exactly this way — see the ObjAct third gate class).
- **Negative space.** The same page carries the join RESIDUALS — 450 rows that exist in a side
  table but are not checks (268 itemlot flags, 80 shop rows, 51 flagless ESD gift lots, 51 phantom
  verdicts). Search there before announcing a "missing check": that residual is where
  "~126 invisible lots" and "27 phantoms" both came from. A blank reason means **nobody recorded
  one** — an honest unknown, not an invitation to guess.
- **Map tab.** Plots the CURRENT FILTER on the committed poptracker maps, coloured by region, so a
  misregioned check is a colour outlier instead of a datamine and a tile-straddle question is "look
  at the border". 1930 of 4879 place; the header states the non-plottable interior count every
  time, because a map that quietly omits them implies spatial coverage the data lacks. Uses the
  same `world_xz` as the triage tool (one implementation, one test) and each map's OWN calibration
  — projecting DLC through the base transform puts every Shadow-Realm check in the sea, plausibly
  enough to be believed, so a test forbids it.
- **Diff a build.** Load an older `er-archipelago-check-browser.html`; it re-extracts that build's
  payload and reports what actually MOVED — checks added/removed, region changes, tag flips,
  name/description churn, nearest-grace churn — keyed by AP id, with both `inputs_hash` stamps
  shown. This is how you review a regen: the generated `.py` diffs run to thousands of unreadable
  lines. 🛑 **A REVIEW AID, NOT A GATE.** CI's byte-staleness check is the gate. If diff says
  "nothing changed" while the bytes changed, that is a FINDING, not a pass — and the page says so.
- **Permalinks.** Facets, query, sort and selection serialise into `location.hash`, so a handoff
  can cite `…#gate=enabler:%20NO_ENABLER&r=Limgrave` instead of pasting a list that rots. Reopening
  an old link against a newer build re-derives the number; if a filter term no longer matches
  anything the page shows a red banner saying so, rather than a quiet zero.

### QUESTLINE DAG — `er-archipelago-questline-dag.html`

The third stamped page, and until issue #699 it was named in **no** doc — not here, not in
CONTRIBUTING — which is precisely how PR #698 shipped it stale. `tools/build_questline_dag.py`
emits `greenfield/questline_dag.tsv` (SPEC-questline-dag tier 1: *emit the graph, assert nothing*)
and `tools/build_questline_dag_page.py` renders it as one mermaid graph per connected component —
the unit of browsing is the CLUSTER, because the graph is 136 mostly-disjoint components, not one
DAG. Mermaid is fetched from a CDN at VIEW time, so the build is offline-safe and byte-deterministic.
Both ride `tools/regen_all.py`. `tests/test_gf_questline_dag.py` gates the **tsv** (corroboration,
the SPEC §7 acceptance cases, freshness); `test_gf_regen_all.py` is what keeps the **page** from
falling out of the chain. 🛑 An edge is co-occurrence plus a polarity rule, not proof;
`sense=unknown` (108 of 280) must not be reasoned with, and absence is not evidence of safety.

### DESC-TRIAGE — authoring `location_descriptions.tsv`

`er-archipelago-desc-triage.html` (root, rebuilt by `python3 tools/regen_all.py` — §5a) ranks checks by how
badly they need a hand description and puts them **on the committed overworld maps**, because the
question you have to answer when writing one is "which of these four is this?" — MEASURED, 986
checks carry a `collision_ordinals()` "(N)" suffix across 306 families, meaning the waterfall could
not tell them apart. Pick a row, see it and its indistinguishable siblings plotted together, type
what makes it different, export a `flag<TAB>description` TSV to paste into
`greenfield/location_descriptions.tsv` (layer 1, always wins), then regenerate
(`python3 tools/regen_all.py`).

The need score is a **triage heuristic, not a truth claim**, and is rendered decomposed so you can
disagree per row: no item name +100, indistinguishable sibling +50, bare +25, machine locale +20,
coarse tile-grace +10, important tag +15, bulk filler −30.

**Overworld coordinate fold — the part to be careful with.** The 4th map-id field is
`[version][lod]`; LOD is documented (`tests/test_gf_lod_tile_regions.py`, `gen_data.py:177`).
Placement uses

    lod = int(suffix[1]) if a 4th field else (2 if tileX < 30 else 0)   # merchant ids are truncated
    pitch = 256 << lod
    world = tile*pitch + local + (pitch-256)/2

then `poptracker/maps/map_calibration*.json`. Two parts are **INFERRED, documented nowhere**: the
`(pitch-256)/2` centring term, and "3-field id + low tile = truncated LOD2" (merchant rows lose the
suffix in `datamine_merchant_shops._map_id`). Evidence for the centring term: without it all 18
LOD2 rows sit 244–463 m outside the tile their own flag encodes, and with it five coarse merchant
tiles land 50–122 m from a real named grace. `test_gf_desc_triage.py` pins it with hand-computed
cases and asserts every projected point lands inside its map — so if it is wrong, it is wrong
*visibly and consistently*, not silently. To falsify: check one of those five merchants in game.

**🛑 MEASURED AND KILLED 2026-07-27 — do not rebuild this.** When the full msg set landed,
`PlaceName` (1007 ids) × `WorldMapPointParam` (472 markers, 289 resolving to a real place name with
a position and a reveal flag) looked like the obvious way to upgrade the weak descriptors. It is
not, and the number is not close:

| | |
|---|---|
| weak-descriptor checks (bare 144 / machine-locale 181 / coarse "around" 656) | **982** |
| …of those, having ANY datamined coordinate | **80 (8%)** |
| …within 300 m of a named map point | **17 (2%)** |

**The ceiling is the CHECKS, not the map points.** 902 of the 982 have no position at all — they are
weak *because* they are unplaced, so no spatial source can reach them, and a better place-name
corpus changes nothing. Of the 80 that ARE placed, 17 do get a name (21% of the addressable set),
which is fine and worthless at that scale.

**🛑 AND THE MSB ROUTE IS ALSO DEAD — retracted 2026-07-27, same day I specced it.** The obvious
follow-up was "distil the missing positions out of the MSBs on the box". The measurement looked
compelling: 505 live checks are seen by `msb_flag_region` but have no coordinate, and 537 of the
546 missing rows are `source=event`. I read that as "the two datamines read different MSB record
types — one reads Event records, the other Treasure records" and wrote a spec plus a probe.

**Wrong, and `datamine_msb_item_regions.py`'s own docstring says so.** `source=event` does not mean
an MSB Event record. It means the map was attributed from **EMEVD** — those items are boss drops
and event awards that are *"NOT NpcParam drops and NOT map Treasures"* and have **no MSB presence at
all**. Their `treasure_name` (`common90005300`) is the EMEVD **award site**, which I read as an MSB
asset marker. There is nothing in any MSB to extract a position from.

So the honest bottom line: **there is no large MSB win available.** Only **9** checks have an MSB
`treasure` record and no coordinate — the coords datamine is essentially complete for things the
MSBs actually place. The unplaced population is unplaced because it is awarded by script, sold by a
merchant, or dropped by an enemy.

That leaves exactly one route: a **NON-spatial** descriptor — who drops it, which quest, which
merchant. `TalkMsg` and the 365-file talk ESD are both bundled now, which makes that newly viable.

⚠️ For anyone reaching for the MSBs anyway, the layout is
`elden_ring_artifacts/{mapstudio,map}/<map_id>-msb-dcx/` with witchy's per-record XML underneath
(`Event/Treasure/*.xml`, `Part/Enemy/*.xml`, `Region/Other/*.xml`). Tools search both roots.

✅ FIXED 2026-08-04 (issue #338). `tools/build_nearest_grace.py` no longer has its own fold: the
one in `tools/overworld_fold.py` is now shared by the nearest-grace builder, the check browser and
the desc-triage page, and `test_gf_nearest_grace.py::test_there_is_exactly_one_overworld_fold`
asserts they are the SAME OBJECT rather than merely agreeing. The old copy folded at *256 regardless
of LOD and its regex required a trailing `_`, so all 725 three-field overworld item rows failed to
normalise while all 225 grace rows did -- the two sides of the join could never share a key.
Recovered 421 checks; 17 of them reach the player as a descriptor (the rest already had a better
layer). It also retired the 18 matches the 2000 m cap was catching at 8.7-10.4 km, which were the
"Altar South spans four regions" straddle phantom -- those now land 30-356 m from a sensible grace.
🛑 Still true and NOT fixed: the 134 checks that render a bare map id are starved of COORDINATES,
not of a join -- zero of them have a `nearest_grace` row even now. That half of #338 stands.

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
- **CROSS-REPO CHANGE? The ORDER is fixed, and the gitlink bump is part of the change, not a follow-up.**
  Anything that moves `contract_gen.rs` or `region_locks.rs` (a new slot_data key, a new option subkey, a
  version bump, a region-spine edit) has a client half and a world half:
  1. Land the **client** PR first, so the generated file exists on client `main`.
  2. In the **world** PR, bump the gitlink **in the same commit as the generated-output change**:
     `git update-index --cacheinfo 160000,<client-sha>,from-software-archipelago-clients`, then confirm with
     `git ls-tree HEAD | grep 160000`.
  CI's `generators` job regenerates INTO a checkout of the pinned commit and fails on a non-empty diff, so a
  bump left for a separate follow-up commit leaves a window where main is red and a tag cut from it ships an
  apworld against a DLL that disagrees with it. (Before 2026-08-02 that job read client `main` instead and
  the window was invisible: world main `0ff714c` pinned `c2fc8ed`, which announced
  `APWORLD_VERSION_EXPECTED = "0.3.0"` while the world was already 0.3.1, and every gate was green.)
  The `client-main-drift` job — push-to-main and nightly, never on a PR — watches the other direction.
- Player-visible change? The `release/CHANGELOG.md` line goes in **this** commit and the
  version's `BLURB-v<version>.md` grows with it -- `python tools/check_release_notes.py`
  (CONTRIBUTING rule 14). Do not leave it for tag time; that is how the blurb series died.
- `git fetch` + rebase onto **the branch you verified in §2** before pushing (Alaric pushes
  concurrently, often mid-session — re-fetch late, not once at the start); resolve/regen if the rebase
  touched generated files, then `git push origin HEAD:<that branch>`.
  ⚠️ Do not copy a branch name out of this file into a `push` command. This bullet has named the wrong
  target twice (`feat/matt-free-backbone-mvp`, then a flat `main` while world work was on
  `feat/natural-progression-mode`, now merged). Client fixes go to client `main`; world work goes wherever
  §2's verify command says it is. (Corrected 2026-07-14, re-corrected 2026-07-24 and 2026-07-25.)
- Relay commit SHAs to Alaric explicitly. Two things NOT to recite as boilerplate:
  - **"needs a submodule bump"** — VERIFY before saying it. `git ls-tree origin/main from-software-archipelago-clients`
    (the pinned gitlink) vs `git ls-remote https://github.com/4laric/from-software-archipelago-clients.git refs/heads/main`
    (client HEAD). Equal ⇒ already current, say nothing. `build.ps1 -Rust`/`-All` AUTO-bumps the gitlink
    (guarded; see §4), so a pin that is merely BEHIND on client-only work gets fixed by Alaric's next build
    — mention that case only if he has not re-run the build.
    ⚠️ **Re-corrected 2026-08-02: this bullet used to end "the world CI tests against client main regardless,
    so a bump is never required for green CI." That is no longer true, and the sentence it replaced was the
    reason the pin could rot.** The `generators` job now checks the client out AT THE GITLINK, so a bump IS
    required for green CI whenever the change moves a cross-repo generated artifact — see the next bullet.
  - **"needs a Windows cargo build"** — only when you actually pushed a client `.rs` change (the push-to-`main`
    CI does that build; hand over the Actions link, don't claim you read the run).
