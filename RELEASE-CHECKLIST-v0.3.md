# ER Archipelago — v0.3.0 Release Checklist

**Written 2026-07-31 by an independent verification pass.** Every ✅ below was produced by running
the command shown, in this sandbox, against world `5835854` and client `7cc7cd4`. Nothing here was
copied forward from the v0.2 checklist, and nothing is marked green on the strength of a commit
message.

> **The rule for this file is unchanged: RUN the gate, don't read it.** It is inherited from
> `RELEASE-CHECKLIST-v0.2.md`, which was itself rewritten because the previous one had gone stale in
> both directions.

---

## The window

| | |
|---|---|
| Last **published** release | `v0.2.18` — tag `97f3dda`, 2026-07-30 |
| World `main` at verification | `5835854` |
| Client `main` at verification | `7cc7cd4` |
| Commits in the window | **19** world (58 files, +2403/-154) · **28** client (27 files, +2672/-158) |
| Contract hash | `d970dd88` → `00a04676` → **`5e8b11c9`** |

⚠️ `0.2.19` exists **in-tree only** — it was bumped at `7f4ee63` and never tagged or published.
There is no v0.2.19 release. The v0.3.0 window is therefore everything after the `v0.2.18` tag.
⚠️ Tag `v0.2.17` (`6f994f0`) is a hotfix line that is **not an ancestor of main**. Do not diff
against it.

---

## ✅ Verified (command shown; each was run)

| Gate | Evidence |
|---|---|
| Apworld unit tests | `pytest worlds/eldenring/tests` over all 110 files — **1195 passed, 1 failed, 180 skipped, 266,209 subtests** |
| Cross-side gates ARMED | `client_contract_paths` 4 ✅ · `scaling_ladder_mirror` 21 ✅ · `client_can_sell_mirror` 2 ✅ · `client_resets_are_called` 4 ✅ — all four run, none dormant |
| Contract agreement | `contract.py` computes `5e8b11c9`; client `contract_gen.rs:201` says `5e8b11c9` — **match** |
| Generated tables not stale | `gen_region_locks` → unchanged · `gen_contract` → 3/3 unchanged · `git diff` empty on **both** repos |
| Full regen reproduces | `gen_data.py` rc 0, then `gen_inputs.py --verify-regen HEAD` → *"11 module body hashes match HEAD; counts match"*. Post-regen diff is 12 files × 1 line, `inputs_hash` only — the documented spurious-regen signature; every `body_sha256` identical |
| Fuzz clean | `fuzz_gf.py`, 2 batches × 2 seeds (`--fuzz-seed 20260731`, `424242`) — **100.0% clean, FILLERROR 0 / CRASH 0 / HANG 0** |
| Fill regression | `fill_regression --selftest` ✅ · `--count 1` 11/11, spill `{0: 11}` |
| Wizard not drifted | wizard `--check` over 36 options — clean |
| Repo tooling suites | 11/11 rc=0 under the `generators`-job invocation |
| **Gitlink == client main** | 🛑 **the row that was missing.** v0.3.7 tagged a pin 5 client merges old; v0.3.8 was 11 behind on the morning of the cut. `generators` cannot see staleness (it checks out the client AT the gitlink); `client-main-drift` sees it and says so with a `::notice::` on non-PR runs only. The tag job now REFUSES a stale pin (`ALLOW_STALE_PIN=1` to override) |
| Channels ledger | `python tools/check_channels.py` — stable/beta both name real refs |
| Wizard deployed from the tag | `ER_STATIC_DIR=... tools/deploy_wizard.sh` after promoting `stable` in `release/CHANNELS.tsv` |

### The one unit failure is a bug in the test, not in the data

```
test_gf_data.py::GreenfieldAreaLockGeometry::test_generated_client_table_matches_the_source_tables
FileNotFoundError: '.../tools/gen_region_locks.py'   (test_gf_data.py:314)
```

`test_gf_data.py:310` derives the repo root positionally (`dirname(dirname(dirname(HERE)))`) instead
of importing `_util.find_repo_root` — the exact idiom `_util` exists to kill. The test has almost
certainly never executed: it skips unless the client sits beside AP, which the CI `tests` job does
not arrange. **The invariant it targets is independently green** (`gen_region_locks` → *"Unchanged
region_locks.rs"*). Fix the test; it is not a release blocker, but it is a gate that has been
reporting nothing.

---

## 🔴 Blockers

### 1. The submodule gitlink ships the wrong client

World `main` pins the client at `c3958b6`. That commit's `contract_gen.rs:201` says
`CONTRACT_HASH = "00a04676"` while announcing `APWORLD_VERSION_EXPECTED = "0.2.19"` — so a bundle cut
from the pin carries a DLL that claims the right version and speaks the wrong contract, and lands on
the mismatch branch at `core.rs:615-631`. Worse, `scadu_blessing.rs` (241 lines) **does not exist at
the pin**: the marquee Scadutree feature would ship with only its world half.

`git diff --stat c3958b6..7cc7cd4` = 14 files, +702.

CI does not catch this: `tests.yaml:168-174` checks the client out from `main` directly, deliberately
bypassing the gitlink. **This is the v0.2.17 failure mode again** — one version number over two
different builds — and it is one line to fix. Fixed on `release/v0.3.0`.

### 2. The fast-travel CTD fix has never been played

`c3995ed` is on client main and the diagnosis is as strong as a diagnosis gets without a playtest —
six crashes, six `foreign-blocks: HIT`, zero misses, one allocation site. But the commit message says
*"Not compiled locally; CI is the gate,"* and **no session on a build containing the fix is recorded
in either repo**. Every build fielded to date crashes. Issue **#198** (Rampart Gaol warp CTD) is
still open and must not be closed on the strength of the code alone.

### 3. A dormant gate is RED — and it is a `num_regions` soft-lock

`test_gf_grace_skip_oracle.py` is referenced only by `greenfield/ci-linux.sh:112`, which no workflow
invokes, so it skips in every automated job. Armed against the bundle it produces **2 failures**:

- 12 boss-gated graces present in the EMEVD oracle are absent from `gen_data._BOSS_GATED_GRACE_FLAGS`
- flag **76412** is emitted as a grantable region grace — a warp *behind boss fog*, which is exactly
  the soft-lock the skip-set exists to prevent

This matters more in v0.3.0 than it would have in v0.2.18, because **`num_regions` now defaults to 6**
— rolled seeds are the common case, not the exotic one. Caveat: this was run against `gen_inputs.db`
rather than full Windows artifacts, so the *count* wants a confirming run on Windows before it is
settled. The presence of 76412 does not.

### 4. Two untriaged player reports

- **#230** — Deeproot start; the waygate wants 2 Great Runes and both reachable Great Runes are
  behind it. A logic soft-lock. No labels, filed 2026-07-30.
- **#225** — dropping any item loses it permanently, including AP-received items. Mechanism
  UNVERIFIED.

---

## 🟠 Judgement calls

- **Client PR #10** — *drive the blessing from fragments RECEIVED, not fragments held.* A genuine
  correctness fix: reveering at a DLC grace **consumes** fragments, so a bag-walk-derived blessing
  collapses to 0 mid-run and `drive()` has no raise-only clamp. It also retro-proves the cap: 46
  fragment locations → max level 18, so the old cap of 20 was unreachable. The option defaults off,
  so this is not a hard blocker — but the feature is the marquee item of the release and it is wrong
  without this.
- **#231** — an unguarded path that produces the reported symptom is traced: Dragon Communion checks
  are in `SHOP_ROW_FLAGS` (`7770607 -> [101951]`), those rows are `costType != 0` (Dragon Hearts),
  and `rune_pricing.py:145-175` has **no costType guard**, so a rolled rune price lands in hearts via
  `shop_prices.rs:119-127`. The reporter says *Great Rune*, and Great Runes are provably not in
  `RUNE_PAYOUT` — so the mechanism is confirmed in code but its link to that screenshot is
  UNVERIFIED. Same bug class as `shop_stock.py:14-20`, which has shipped once already.
- **`KNOWN-ISSUES.md` is stamped "current as of v0.2.11"** — seven releases stale, tracked by #212.
  It still lists the rune-price bug, which merged as PR #227 (`f7463ea`/`e68c816`) and shipped in
  v0.2.18. The fast-travel-crash entry needs rewriting against `c3995ed`. The "1% of checks give a
  Rune" figure needs re-deriving. **Do not ship v0.3.0 behind this file as written.**

---

## 🟡 Built but never played — belongs in KNOWN-ISSUES, not in the blocker list

Nine items, headed by the four open `needs-playtest` issues #233, #234, #235 and #239/#240.
#239 cannot make a seed unwinnable (all three grants are in `_NO_PROGRESSION_APS`); #240 is an inert
option. The Scadutree blessing (Lever D) needs a **DLC seed** specifically, and the hint button needs
a Windows validation pass.

---

## ❌ NOT verified — these are not failures, they are gaps

Say "did not run", never "passed":

- Multiworld smoke (exit 4 — no `worlds/hk` in the sparse checkout)
- `fill_regression --count 8` (one complete run; 36/44 clean at `--count 4` before the time wall)
- Large-batch fuzz (only 4 seeds total)
- **CI status on `main`** — the Actions API needs auth and returns 403 unauthenticated
- Anything requiring Windows artifacts, a compiled DLL, or the game itself. **No in-game behaviour in
  this release has been observed by this pass.**

---

## Tag sequence (unchanged from v0.2, with one addition)

0. **Bump the submodule gitlink to client `main` and confirm `git ls-tree HEAD` shows it** — new step,
   see blocker 1.
1. `git tag -a v0.3.0` on the apworld, and on the client at the pinned gitlink. They must match.
2. Attach `eldenring.apworld` + the client `.dll` from a clean `build.ps1`.
3. Release notes from `release/CHANGELOG.md`, v0.3.0 entry. **Two defaults changed** —
   `num_regions` and `num_regions_order` — and that is the single most likely support question.

## The one-line answer

**Not yet.** Blocker 1 is one line and is already fixed on the branch. Blockers 2 and 3 are the real
gate: the crash fix has never been played, and a `num_regions` soft-lock oracle is red in a release
whose headline change is that `num_regions` is now on by default.
