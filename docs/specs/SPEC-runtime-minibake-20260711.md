# SPEC — Runtime mini-bake: rewrite CHECK lots to synthetic ids, and delete vanilla-suppress

**Status:** SPEC. Not started. Blocked on a row-supply count (see §4).
**Date:** 2026-07-11
**Supersedes:** nothing. **Would retire:** `features/check_item_flags.py`, `er_logic::vanilla_suppress`,
the `check_item_flags_lookup` branch of `detour.rs`, and `greenfield/eldenring/repeatable_goods.py`.

---

## 1. The problem this kills

The client's vanilla suppressor is keyed on the **item id**, because `detour.rs` only ever sees `raw_id`
off the `AddItemFunc` buffer — it cannot tell *where* an item came from. `checkItemFlags` maps
`{vanilla FullID -> the check flags that ware backs}` and `should_suppress()` eats the bag-add until
**every** one of those flags is collected.

So a ware that merely *happens* to back some check is eaten from **every** source:

| ware | checks it backs | consequence |
|---|---|---|
| Golden Rune [1] | 46 | every Golden Rune [1] eaten until all 46 collected |
| Stonesword Key | 32 | " |
| Rune Arc | 25 | " |

Mine an ore node in a tunnel → you get a Smithing Stone → that stone is some check's ware → **eaten**.
That is the playtest report that started this (Alaric, 2026-07-11: *"the stones that are in tunnels.
non-respawning, yet today they're just suppressed"*). It was also silently eating **83%** of the
rerolled enemy drops.

### What we shipped instead (the stopgap, commit `<this>`)

`gen_data` derives `REPEATABLE_GOODS` — every goods id obtainable from a **non-check** source (an
unflagged `ItemLotParam` lot, a shop row, a crafting recipe) — and `check_item_flags` refuses to arm
suppression for those. 703 armed suppressions → 467; goods-category ones → 132. Eaten drop slots:
83% → **0%**.

**The stopgap has a real cost.** For those ~243 shared wares, the vanilla item is no longer suppressed
*at the check either* — so at a check whose vanilla ware is a Smithing Stone, you now get **the vanilla
stone AND the AP item**. A double-dip, on an item you could have farmed anyway. It is strictly better
than killing all farming, but it is a leak, and it is the reason this spec exists.

---

## 2. The real fix

We can now **write `ItemLotParam` at runtime** — `enemy_drops.rs` proves it, and `shop_sell.rs` /
`shop_flags.rs` already write `ShopLineupParam`. So do what the retired offline baker did to
`regulation.bin`, but live:

> **Rewrite every CHECK lot's item slot to a SYNTHETIC goods id that encodes its AP location.**

Then:

* a check pickup is **unambiguous** — `detour.rs` already has the branch:
  `is_synthetic_goods(raw_id)` → `params::goods_row_fields()` → `decode_synthetic()` →
  report the AP location, suppress the world pickup;
* **no vanilla ware is ever handed out at a check**, so there is nothing to leak and nothing to
  double-dip;
* the entire id-keyed suppressor **disappears**: `checkItemFlags`, `vanilla_suppress`,
  `REPEATABLE_GOODS`, and the `KNOWN_COLLECTED_FLAGS` re-pickup discriminator all become dead code;
* every vanilla pickup — ore nodes, farmed drops, crafted items, shop buys — just **works**, because
  nothing is watching item ids any more.

This is the same architecture the baker had, minus `regulation.bin`. It is the last big piece of the
pure-runtime story.

---

## 3. Why it is clean

The synthetic scheme already exists and is already wired end-to-end; we would only be changing **who
writes the synthetic id into the lot** (runtime param write, instead of an offline regulation bake).
`decode_synthetic` reads the AP location out of unused fields of an `EquipParamGoods` row —
`vagrant_item_lot_id`, `vagrant_bonus_ene_drop_item_lot_id`, `basic_price`. Nothing about that
mechanism needs to change.

---

## 4. THE BLOCKER — count the spare goods rows first

`goods_row_fields(row_id)` looks up an **existing** `EquipParamGoods` row. The synthetic id must
therefore *be* a real goods row, because the game has to be able to grant it, draw its icon, and name
it. The baker **added** rows to `regulation.bin`. **At runtime we can write rows but we cannot add
them.**

So the whole spec turns on one number:

> **How many `EquipParamGoods` rows are free to repurpose, versus how many checks need one?**

* checks needing a synthetic id: ~**4,800** (all flagged `ItemLotParam_map` lots in scope)
* spare goods rows: **UNKNOWN — count this first.**

If the spare count is far below the check count, this spec is dead as written and needs a different
encoding (ideas, unvalidated):

* **(a) Reuse a small pool + a lot→location map.** Doesn't work naively: the detour sees only the item
  id, not the lot that produced it. Would need a hook at the *lot award* site rather than the bag-add.
* **(b) Only synth the checks that actually collide.** Hybrid: synth the ~243 shared-ware checks
  (killing the double-dip exactly where it occurs) and leave unique wares on the id-keyed suppressor,
  which is already sound for them. Needs only ~243 spare rows — **plausibly the realistic version.**
* **(c) Hook the item-lot award instead of `AddItemFunc`.** Removes the ambiguity at the source and
  needs no synthetic ids at all. Biggest RE effort; also the most correct.

**(b) is the recommended first move** — it is the smallest change that removes the leak, and its row
budget is two orders of magnitude smaller.

---

## 5. Definition of done

1. Count spare `EquipParamGoods` rows. Record the number here. **Do this before anything else.**
2. Pick (b) or (c) based on that number.
3. Runtime pass writes synthetic ids into the chosen check lots (mirror `enemy_drops.rs`).
4. Delete the id-keyed suppressor for those checks; verify in-game that:
   - a tunnel ore node hands you a real Smithing Stone,
   - the check at that same ware hands you the AP item and **not** the vanilla ware,
   - a farmed enemy drop of a shared ware is not eaten.
5. Retire `repeatable_goods.py` and the stopgap in `check_item_flags.py` if (c) makes them moot.

---

## 6. Related

* `er-vanilla-suppress-collected-set-fix` — the current re-pickup discriminator (COLLECTED set, not
  the live flag). Retired by this spec.
* `features/minibaker.py` / `minibaker.rs` — the existing, working precedent: one reserved
  `ShopLineupParam` row repurposed at runtime into the infinite Stonesword Key vendor. This spec is
  that idea, generalised to `ItemLotParam`.
* `enemy_drops.rs` — proves runtime `ItemLotParam` writes work.
