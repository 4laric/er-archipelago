# Handoff — 2026-07-25 (shop placeholder, region gates)

Written for a session picking up cold. Same discipline as the 07-24 handoff: **verify COMMANDS, not
verify RESULTS**, and everything below is labelled VERIFIED (I ran it, and how) or INFERRED.

One addition, learned the hard way today: **the previous handoff's "START HERE" was WRONG in a way
that would have re-shipped a fixed bug.** It said the non-goods fix was "everything is pre-wired, flip
`CAN_WRITE_SLOT_CATEGORY`, no other logic changes." The `RepointToPlaceholder` arm called `zero_slot()`
— so flipping the flag alone would have re-emptied every non-goods check slot. **Read the branch BODY.
Do not trust "pre-wired" in a handoff, including this one.**

---

## 0. Summary

The v0.2 non-goods debt is CLOSED and confirmed in-game. Both repos are green. The next piece is the
shop placeholder, and its one blocking unknown — a second spare goods row — was resolved in-game today.

## 1. START HERE — wire goods row 8853 as the SHOP placeholder

**Everything needed is settled. This is implementation, not design.**

WHY: `shop_preview.rs` deliberately leaves a slot showing its VANILLA name/icon when the slot's vanilla
ware is a real grantable good, because the FMG name entry is **global per goods row** — renaming it
would rename every copy in the player's inventory for the whole run (the `real.contains(&gid)` guard;
tallied as `left vanilla to protect a real good's shared FMG entry`). In-game 2026-07-25 that showed as
a slot reading "Armorer's Cookbook [2]" paying out an Ash of War. The code's own comment names the fix:
repoint the slot at a dedicated placeholder. The blocker was that `check_lots::is_placeholder` nulls
placeholder bag-adds UNCONDITIONALLY and cannot tell a shop row from a lot row — and nulling a shop
bag-add is the retired crash-adjacent path. So shops need their OWN placeholder row.

**VERIFIED in-game today: goods row 8853 is that row.** `!give 0x40002295` grants it; it renders
`[ERROR]` / `?GoodsInfo?` — the game's missing-FMG-entry markers, i.e. no name entry to hijack. Lands in
Key Items, `goodsType 1`, `maxNum 1`, same shape as 8852. Found by `tools/find_spare_goods.py`.

Steps: add `apShopPlaceholderGoods` to `contract.py` (regenerate the mirrors, never hand-edit); scope
the lot-side suppressor so it only nulls the LOT placeholder; repoint shop rows at 8853 and dress it as
8852 is dressed (flower icon + injected GoodsName), or players see `[ERROR]`.

⭐ **DERIVE 8853 into the client from slot_data**, exactly as `apPlaceholderGoods` already is. Never
type the id in two places — I put a wrong decimal for it into the help text of the very command built
to catch wrong ids (§5).

Landing beside it, and NOT before it: **delete `greenfield/eldenring/features/weapon_shop_slots.py`**
(Alaric, 2026-07-25: "full random"). It forces weapon shop slots to hold own-world weapons so the
client's rewrite is weapon→weapon; `SHOP_CTD_GUARD` was removed 2026-07-11 and the placeholder makes it
moot. It is unconditional (no option gates it), so deleting it changes fill — option matrix + fill
regression apply, and `test_gf_weapon_shop_slots.py` should be rewritten to pin the NEW invariant.
**Ordering hazard:** deleting it before the placeholder lands puts non-weapon rewards into weapon rows
while `shop_sell` still rewrites them cross-type natively.

🛑 `/tmp/client-c` holds an abandoned draft (branch `agent/shop-sell-placeholder`, uncommitted). It kept
the vanilla ware instead of using a placeholder, which multiplies the wrong-name slots. **Bin it.**

## 2. Where the code is — VERIFY, do not trust

```bash
git ls-remote --heads origin | awk '{print $2}' | sort
git fetch origin && git rev-list --left-right --count origin/main...origin/<branch>
```
As of writing: world `main` carries the merged natural-progression work (PR #208, 35 commits) and
`feat/natural-progression-mode` is 0 ahead. Client works on `main`. AGENTS.md §2 is a PROCEDURE.

CI is readable from the sandbox: `api.github.com` works UNAUTHENTICATED for public run/job metadata;
only **log download** needs a PAT.

## 3. What shipped today

| repo | sha | what |
|---|---|---|
| world | `b1458a6` | finale test: the start anchor's free Lock made an entrance leg unfalsifiable (~3%/run) |
| client | `1121d93` | **non-goods check slots REPOINTED** (id + category). ✅ confirmed in-game |
| client | `24e2bf4` | one predicate for both arms; retire the ZERO vocabulary |
| world | `41d2554` | natural-progression merge (clears #196: main now derives 4853 locations) |
| world | `c03a1a1` | **grace-straddle screen** + `tools/find_spare_goods.py` |
| world | `d46bb99` | find_spare_goods: select on `disableParam_NT`, not absence of references |
| client | `0fe3536`/`bdee14f` | `!give <fullId> [qty]` debug probe |

## 4. Open, with the state of the evidence

* **44 straddling graces / 117 minority-side checks** (`test_gf_grace_straddle.py`, pinned as a
  RATCHET). Two derivations disagree; the screen does NOT say which is wrong. Needs triage into
  map-version (`Leyndell, Capital of Ash` is legitimate) / true-border / real defect. Largest suspects:
  `Summonwater Village Outskirts` (Limgrave=8, Caelid=7), `Isolated Merchant's Shack`,
  `Third Church of Marika`, `Craftsman's Shack`. **Do NOT add exemptions to go green.**
* **Root cause of the region class (#202-shaped).** 42 of the 203 m60 tiles checks reference have NO
  entry in `play_region_buckets.tsv`, so they fall to a nearest-neighbour tile guess that never fails.
  Plus `// 100` collapses the game's own subdivision (Weeping 61002 and Limgrave 61000 are one bucket).
  Fix = `datamine_play_regions.py --emit` RAW PlayRegionParam ids (#192), and make the uncovered case
  DEFAULT loudly rather than answer.
* **`lotItemCategory 6` (sorcery) check slots** still unexercised in-game. INFERRED low risk: cat 6
  rides the already-shipping goods path.
* **A repeating crash signature.** Two captures, identical RVAs (`+0xc57676`, `+0x16ccf33`, `+0xc571c2`,
  `+0x269f907`, `+0x269fac9`), exception `0x80000003` = STATUS_BREAKPOINT — **not** the `0xC0000005`
  of a use-after-free, and not #198's profile. Both occurrences look like Alaric closing the game.
  Benign unless it fires mid-play; if it does, symbolize those RVAs against the PDB.

## 5. Things I got WRONG today — do not inherit them

1. **Briefed a subagent to "sell the placeholder" without checking the suppressor could scope it.**
   Fable declined and was right. A brief is where an assumption gets laundered into a requirement.
2. **Told Alaric CONTRACT.md needed a regen on his box.** It derives from `contract.py` alone; the
   sandbox does it fine. CI went red on it. The question is which INPUTS a generator needs, not whether
   the word "generated" applies.
3. **Wrote a spare-row finder that ranked by ABSENCE of references** and returned 1137 of 2326 rows.
   Absence is invisible evidence — EMEVD/ESD can award a row with no param reference. The game ships
   the answer: `disableParam_NT`.
4. **Put a wrong id (`1073750549`, = row 8725) in the `!give` help text**, in the same sentence as the
   correct hex, in the command built to catch wrong ids. Prefer hex; derive ids, never type them twice.
5. **Repeated a stale memory claim** that `apply_auto_upgrade` had zero coverage. It has 17 tests plus
   `upgrades_replay.rs`. Verify coverage claims before repeating them.
6. **Used `git commit -m` with backticks in bash** — command substitution gutted a load-bearing
   sentence from a pushed commit message. Use `-F <file>`.

## 6. Working notes NOT in AGENTS.md / CONTRIBUTING

* **Backgrounded jobs do not survive a `mcp__workspace__bash` call** (`bwrap --die-with-parent`), and
  the timeout is hard-capped at 45s. A long run looks like a hang. Chunk it — the apworld suite runs in
  four file-slices. `/tmp` persists across sessions AND uids; a leftover dir owned by another user
  silently hijacked a provision.
* **Do not hand-install the world into an AP checkout.** AGENTS.md §5's snippet copies only
  `region_map.csv` and yields 10 spurious failures. `tools/gf_test.py --ap-dir <dir>` copies every
  `greenfield/*.tsv|csv`, `region_groups.py` and `EldenRing.yaml`.
* **You can derive a crate setter name without asking.** Clone `vswarte/fromsoftware-rs` at the SHA
  `Cargo.lock` pins: the paramdef XML gives the field's real decl (and its TYPE, which a CSV header
  dump cannot), `tools/param-generator/src/rust.rs` emits `set_{normalize_name(field)}`. Validate
  `normalize_name` on a known-true pair first. That is how `set_lot_item_category01..08` (`i32`, not
  the `u8` the last handoff implied) was settled without a round trip.
* `param_headers/` (committed) indexes every param column name; `column_to_params.tsv` is the reverse
  lookup. Headers only — no values, so it is committable.
