# Handoff — 2026-07-24 bug hunt (playtest-driven)

Written for a fresh session picking up cold. Everything below is either **VERIFIED** (I ran it and
say how) or **INFERRED** (labelled, with what would confirm it). The previous handoff's worst failure
was stating repo facts that had rotted by the time anyone read them, so **this file states verify
COMMANDS, not verify RESULTS**, wherever the answer can move.

---

## 0. The one-line summary

A long playtest turned into a bug hunt. Almost nothing found was a bug *in* natural-progression mode
— the mode's full-map roaming surfaced **latent client bugs**, including a use-after-free CTD and
three separate classes of check that silently gave the player nothing. v0.2.9 shipped (apworld +
client together). Both repos are green except one known cross-repo drift on world `main`.

---

## 1. START HERE — the next piece

**Finish the non-goods check suppression, and delete the duplicate-item wart v0.2.9 shipped with.**

Why this one: it is shipped debt with a player-visible symptom, the design is already settled, the
change is small, and it needs exactly one unknown resolved.

* What shipped: `eee9b1b` (client) stopped emptying non-goods check lot slots. Emptying removed the
  pickup, and the pickup IS the check — so gear chests, scarab Ash-of-War drops and boss drops gave
  nothing at all. The stopgap leaves the vanilla ware on the shelf, so **players now sometimes get a
  duplicate vanilla item alongside the AP item** (documented in `release-v0.2/KNOWN-ISSUES.md`).
* The real fix, already scaffolded: repoint non-goods slots at the AP goods placeholder like goods
  slots, which needs the slot's **category** field written alongside its id — `check_lots.rs` only
  ever writes id/num, which is why zeroing was reached for.
* **Everything is pre-wired.** Flip `CAN_WRITE_SLOT_CATEGORY` (`crates/eldenring-archipelago/src/check_lots.rs`)
  and `er_logic::check_neutralise::plan` starts repointing non-goods exactly like goods. No other
  logic changes.
* **THE ONE BLOCKER:** the per-slot category setter name on `ITEMLOT_PARAM_ST`. Do NOT guess it —
  AGENTS.md §4 is explicit, and guessing crate symbols has cost three build round-trips before.
  Ask Alaric, or read it off the `eldenring` crate on his box. Expect something shaped like
  `set_lot_item_category01..08`.
* Ships in the client bundle; **no regen needed**. Add a `check_neutralise` test for the
  `can_write_slot_category = true` path (it exists and is currently unexercised in production).

**If that is blocked**, take **#192 → #202** instead: extend `tools/datamine_play_regions.py` to emit
the RAW `PlayRegionParam` ids per bucket (it currently emits only `id // 100`), which unblocks the
Margit / Limgrave Tower Bridge boundary fix. Alaric has already decided **Margit sits OUTSIDE
Stormveil**. Standing preference, stated 2026-07-24: **improve the datamine tool rather than take an
in-game probe** whenever a file could answer.

---

## 2. Where the code is (VERIFY, do not trust this table)

```bash
git ls-remote --heads origin | awk '{print $2}' | sort
git fetch origin && git rev-list --left-right --count origin/main...origin/<branch>
```

As of writing: world `main` carries v0.2.9 and both agent branches are merged into it;
`feat/natural-progression-mode` is ~30 commits ahead of main and NOT merged. Client repo works
directly on `main`.

AGENTS.md §2 is now a *procedure*, not a fact — it has named the wrong branch twice. Read it, then run
the commands anyway.

---

## 3. What shipped today

### Client (`from-software-archipelago-clients`, main) — all VERIFIED green in CI

| commit | what |
|---|---|
| `a3016f5` | build was broken since `dc2bd41` (`fetch_update` deprecated under `-D warnings`) |
| `c71f550`, `805ac65` | fmt + clippy, which had **never run** because they sit behind the build |
| `21b1ca1` | boss sweeps never set their members' acquisition flags → dead pickups |
| `eee9b1b` | non-goods check lots were ZEROED → dead checks (see §1) |
| `c7087c2` | **THE CTD**: use-after-free on a cached inventory pointer |
| `01e257a`+ | overlay toasts for grants that apply no item (flask first) |
| `8c48cc6` | flask: explain an absorbed ladder rung; toast the effect, not the receipt |

The CTD is the headline. `grant_full_id` handed the game's AddItemFunc an inventory pointer captured
once and trusted forever; a map load frees it, so every grant after the first load was a coin flip on
freed memory. Symbolized from `crash-8548` against the PDB — that stack is what identified it, after
my own first theory (enemy scaling walking a dying ChrIns) was **wrong**.

### World (`er-archipelago`)

On `main` via the backport: multi-merchant hand-pin hard-error, ShopSlot pins re-keyed to the merchant
(talk ESD), alt-currency missable widened to `costType != 0`, v0.2.9 changelog, and the
`package_release.ps1` cross-repo gate (`d807616`).

On `feat/natural-progression-mode`: strict field-sweep eligibility + Summonwater regression guard,
count-gate data, born-softlock fix, the `GOAL_REGION` KeyError fix + invariant test, and the fuzz-gate
changes (100% bar, crash-is-not-a-statistic, stdin closed).

---

## 4. Open, with the state of the evidence

* **#198 second CTD (fast travel).** OPEN. Stack has **no client frames**, does **not** reproduce on
  demand (same save, same grace, same build, no crash), so my earlier "deterministic" claim is
  RETRACTED in the issue. **INFERRED:** it may be late fallout from `c7087c2` — a use-after-free can
  damage memory that faults elsewhere much later, which fits every axis we have. **Falsifiable:** if
  it never recurs on builds ≥ `c7087c2`, that was it. Do not close on absence of evidence.
* **#196 world `main` CI is RED**, `generators` job, `tracker_regions.rs` 465 lines. NOT a main
  defect: client main's copy was generated from the feature branch's data (4853 locations vs main's
  4848). Clears when the branch merges. `package_release.ps1` now refuses to package into this state.
* **#191 co-check derive** — still parked; `co_check_ids.tsv` is at the earlier 26-row state.
  `flag_lots.tsv` already proves the shape: **292 flags own >1 slot, 584 extra items**. No MSB rescan
  needed. Needs a go/no-go, `--alloc`, regen.
* **#195** field-sweep audit: the 43 recovery-claimed-m60 + 77 no-recovery rows still need an
  EMEVD→entity→MSB derivation that emits candidates **with an ambiguity marker**.
* **#202 Margit / Tower Bridge**, **#203 flask ladder floor** (design call), **#193** harness.

---

## 5. Things I got WRONG today — do not inherit them

1. **Predicted the CTD was enemy scaling.** It was the grant path. The PDB settled it in one command.
2. **Guessed rustfmt's preferences twice, in opposite directions.** Read the CI diff; never reason
   about formatting.
3. **Let a scripted edit skip silently** instead of raising → broke the build (`8c48cc6`). That is
   CONTRIBUTING rule 9, and I had assertions everywhere else in the same session.
4. **Introduced a silent last-write-wins** while fixing one: `DRAGONHEART_FLAGS[flag] = costType` when
   a flag can carry several. Caught only because a labelled regen showed a count *drop*.
5. **Stated an invariant too strictly** (`goal in kept`), which failed on the conditional finale
   region — and in failing revealed a real hole in the fix it was guarding.
6. **Clobbered my own uncommitted edit** with `git checkout <branch> -- <file>`.

The pattern: every one was caught by an instrument, none by reasoning. Prefer the tally, the CI diff,
the symbolized stack, the regen printout.

---

## 6. Working notes that are NOT in AGENTS.md / CONTRIBUTING

Both files were updated today (`29b2a25`) — read them, they are current. Not in them:

* `api.github.com` **IS** reachable from the agent sandbox with a PAT. Read the CI run; do not claim
  you read it if you did not. (AGENTS.md said the opposite and four red runs went unseen.)
* No Rust toolchain in the sandbox and no way to install one (sudo blocked, `sh.rustup.rs`
  unreachable). `cargo` fmt/clippy are guess-and-check against CI — budget round trips, or fix the
  sandbox.
* Alaric runs **PowerShell**: `$env:VAR`, backtick continuation. No `^`, no `%VAR%`.
* The mount is off-limits for reads AND writes. Clone from GitHub; deliver by `git push`.
