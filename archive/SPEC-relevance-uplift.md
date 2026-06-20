# SPEC: DLC-Only Relevance Uplift (filler → base-game juice)

Status: draft (2026-06-16). Owner: Alaric.
Related: `SPEC-check-trim.md`, `SPEC-dlc-only.md`, memories `er-dlc-gear-curation`,
`er-rune-skip-injectable-room`, `er-spell-trim-keep`, `er-trimmed-curation-impl`,
`er-trimmed-forbid-useful-shortage`, `er-ammo-filler-guard`,
`er-ingame-check-indicators-spec`.

## Goal

In `dlc_only` the player is region-locked to the DLC; the base game stays inaccessible.
The DLC locations are the only checks, and the curated pool is thin (trimmed `dlc_only`
nets ~329 good items, the rest padded with DLC filler — crafting materials, low
consumables, junk ammo). Opening a DLC check too often coughs up a Messmer Soldier's
Butterfly.

This pass **does not touch locations**. It is pure item-pool composition: remove
low-relevance DLC filler from the item pool and inject an equal number of high-value
**base-game** items in its place. The base game's items still exist as definitions even
though its regions are walled, so injecting them is free (same fact `dlc_gear_curation`
relies on: DLC item ids are always registered; `enable_dlc` governs *checks*, not whether
items may be *granted*). Messmer Soldier's Butterfly out, Numen's Rune (or a Mimic Tear,
or an S-tier weapon) in.

Net effect: every DLC check is worth the walk. Pairs directly with the in-game check
indicators (`SPEC-ingame-check-indicators.md`) — if every glowing check is at least a
meaningful rune or a real consumable, the glow never lies.

## Where this lives

This is the **mirror of `dlc_gear_curation`**, which already implements exactly this shape
in `create_items` (`Archipelago/worlds/eldenring/__init__.py:827`): defer a *skippable*
set, inject a *curated* set, skip an equal number to fund it, invariant **injected ≤
skippable**, pool count preserved with no extra filler, and every LOCATION stays a check
regardless of pool membership.

`dlc_gear_curation` = "inject curated DLC gear, skip worst base-game gear."
Relevance uplift = the inverse: **"inject curated base-game juice, skip worst DLC filler."**

Concretely, in the `create_items` scan loop (`__init__.py:842`), add a new defer bucket
alongside `deferred_bad_gear` / `deferred_small_runes` / `deferred_inject_reserve`:

```python
deferred_dlc_filler: List[str] = []   # NEW: skippable DLC filler, funds the uplift
...
elif self._curate_defer_dlc_filler(default_item_name):
    deferred_dlc_filler.append(default_item_name)
```

Then, after the existing injection blocks, a new funded-swap block mirroring the
`dlc_gear_curation` one at `__init__.py:905`:

```python
uplift_names = self._uplift_inject_names()              # ranked base-game juice
deferred_dlc_filler.sort(key=self._dlc_filler_drop_rank)  # worst/cheapest first
num_uplift = min(len(uplift_names), len(deferred_dlc_filler))
# inject uplift_names[:num_uplift]; return deferred_dlc_filler[num_uplift:] to the pool
```

Invariant: `injected == skipped <= skippable`. Count preserved automatically, no
rebalancing, no location change. The `dlc_gear` and `rune-skip` demand-drops already
coexist in the same function; uplift runs after them and consumes whatever filler budget
remains.

### Gating

- Primary scope: **`dlc_only`** (`self.options.dlc_only`). Outside `dlc_only` the base
  game is reachable and its items are already in the pool, so the move is meaningless —
  keep `deferred_dlc_filler` empty when not `dlc_only`.
- Decision 2026-06-16: fold into **trimmed `dlc_only`** as default behavior (no new
  toggle), consistent with how check-trim and dlc_gear curation were folded in. A toggle
  can be added later if anyone wants vanilla DLC filler back.

## The cut set — removable DLC filler

What gets deferred into `deferred_dlc_filler`. Strictly **consumable/material filler**;
gear is left to `dlc_gear_curation` (no overlap, no double-counting).

`_curate_defer_dlc_filler(name)` returns True when **all** hold:

1. Item is DLC (`getattr(item, "is_dlc", False)`).
2. `item.classification == filler` (never defer a useful/progression item).
3. `item.category in (GOODS,)` and the item is junk-tier: crafting materials
   (butterflies, fly, slime, etc.), low consumables, **junk ammo** (reuse the id-range
   guard from `er-ammo-filler-guard` so a named "ammo" that's actually a weapon, e.g.
   Bolt of Gransax, is never caught).
4. Not on a small hand allow-list `UPLIFT_KEEP_DLC` (one-off "actually keep this DLC
   filler" decisions surfaced by the report).

Implementation: an `UPLIFT_CUT_DLC` name/id-range set in `curation.py` (same file and
codegen shape as `TRIM_CUT_WEAPONS` / `TRIM_CUT_ARMOR` / `TRIM_CUT_RUNES`), generated from
the DLC filler GOODS list. Prefer id-range membership over name matching where the
category is contiguous, name denylist for the stragglers.

`_dlc_filler_drop_rank(name)` orders **worst/cheapest first** so, if the funding budget is
smaller than the cut set, we drop the most worthless items first (crafting mats before,
say, a stack of decent throwables).

## The injection set — base-game juice

Built by `_uplift_inject_names()`, **base-game items only** (`is_dlc == False`), ranked.
Two membership classes, because supply differs:

**Uniques — inject once each (useful-tier).** One copy enters the pool, then never again:

- **S-tier weapons** — `ITEM_TIERS[name] == "S"` and category `WEAPON`, base game only.
- **S-tier armor** — `ITEM_TIERS[name] == "S"`, category `ARMOR` (by piece; tiers are
  keyed per piece in `item_tiers.py`).
- **S-tier talismans** — category `ACCESSORY`. *Data gap:* check-trim deliberately
  excluded talismans, so `item_tiers.py` has no talisman coverage yet. Phase 1 uses a
  hand list `UPLIFT_TALISMANS_S` in `curation.py` seeded from community PvE refs
  (gameleap / rankedboost / gamerant, 2026-06-16): Erdtree's Favor +2, Radagon's/Marika's
  Soreseal, Shard of Alexander, Godfrey Icon, Radagon Icon, Old Lord's, Gold Scarab,
  Millicent's Prosthesis, Ritual Sword, Graven-Mass, Dragoncrest Greatshield, Crimson
  Amber Medallion +2, Blessed Dew. **Phase 2: fold ACCESSORY into the `item_tiers.tsv`
  pipeline the same way weapons/armor/spells were sourced** (decision 2026-06-16) and
  retire the hand list.
- **S-tier sorceries & incantations** — extend `HIGH_TIER_SPELLS` (already added for
  spell-trim, `er-spell-trim-keep`) to an `S` subset, base game only.
- **Top Spirit Ashes** — hand list `UPLIFT_SPIRITS_TOP` (Mimic Tear Ashes, Black Knife
  Tiche, Lhutel the Headless, Redmane Knight Ogha, Ancient Dragon Knight Kristoff,
  Greatshield Soldier, Latenna, …; keys verified against `item_table`). Biggest difficulty
  lever in a solo DLC-only run; finding a Mimic early is a jackpot. Pair with the glovewort
  bell bearings (below) so they can be upgraded.
- **Physick / Crystal tears** — each is unique in vanilla; inject once each.
- **Memory Stones (+spell slot)** and **Talisman Pouches (+talisman slot)** — permanent
  upgrades, finite in vanilla. Cap injection at the vanilla quantity (8 memory stones, 3
  pouches via `UPLIFT_UNIQUE_CAPS`) — extra copies are wasted (effect caps). Treat as
  count-capped uniques.
- **Glovewort / Ghost-Glovewort Picker's Bell Bearings** (`items.py:8960-8965`,
  non-progression) — unlock spirit-ash upgrade materials at the merchant so the injected
  spirits can scale. Ride the swap as filler/useful.

> **Cut for cause: Larval Tears.** Removed from the inject set entirely — respec requires
> Rennala at Raya Lucaria, which is inaccessible in `dlc_only`, so a larval tear is dead
> weight. (No respec NPC is reachable behind the region locks.)

**Stackables — repeat to fill the remaining budget (filler-tier), weighted.** After all
uniques are placed, the rest of `num_uplift` is filled from a weighted distribution so we
don't get 200 Numen's Runes and nothing else:

- **Juicy runes** — Numen's Rune, Lord's Rune, Hero's Rune, Golden Rune [10]–[13].
- **Remembrances** — base-game boss remembrances. Inject the named ones **once each**
  (they read as semi-unique), then let generic high runes carry the remainder. *Open
  question below on classification.*
- **Golden Seeds** and **Sacred Tears** — flask charges / potency.
- **Misc top consumables** — boluses, grease, etc.

> Raw smithing/somber stones are **not** stackable injects — a pile of high stones is
> useless because weapons climb the ladder +1→+2→…. Upgrade access is a separate lever
> (next section).

Suggested starting weights for the stackable remainder (tunable against the report):

| Bucket | Weight |
|---|---|
| Juicy runes (incl. remembrances overflow) | 40 |
| Golden Seeds + Sacred Tears | 20 |
| Physick / Crystal tears | 10 |
| Glovewort bell bearings (spirit upgrade) | 10 |
| Misc top consumables (boluses, grease, etc.) | 20 |

## Upgrade access — separate progression lever (not the swap)

The clean fix for weapon upgrades is the **Miner's Bell Bearings**, which unlock the full
stone range for purchase at the Twin Maidens (Roundtable is reachable in `dlc_only`) —
giving the whole [1]→[8]/somber ladder instead of a useless heap of [8]s. But these are
`classification=progression` in `items.py` (`8951-8959`), so they must **not** ride the
count-neutral filler swap. Put them on the **guaranteed progression-injectable path** (the
same one the rune-skip demand-drop frees in-world slots for, `__init__.py:869-899`).

- Gate entirely on **`auto_upgrade` == OFF** — with auto_upgrade on, weapons upgrade for
  free and none of this is needed.
- **Dependency:** shop-refresh-on-unlock (`er-merchant-bell-bearing-logic`,
  `er-qol-patches-shop`) — a received bell bearing must actually add stock to the Twin
  Maidens for this to work in-game. If that isn't wired, fall back to `auto_upgrade` for
  `dlc_only`.

**Why this matters — the DLC somber bottleneck (measured 2026-06-16).** The DLC's own
smithing-stone drops are lopsided. Regular stones are comfortable: [1]–[8] across ~62
locations / ~240 stones (often x4–x6 stacks) plus 8 Ancient Dragon Smithing Stones (the
+25 cap) — a standard weapon can be maxed from DLC drops alone. **Somber is the
bottleneck:** [1]–[9] are 48 locations but **one stone per pickup, no stacks**, the low
tiers are thin (only 4 each of [1], [2], [3], [7]), plus 6 Somber Ancient Dragon. Every
copy is a separate AP check scattered across the multiworld, so assembling a full somber
ladder for a single weapon is fill-dependent and can stall a somber build. That's the
concrete case for the bell-bearing lever — buying covers the whole somber ladder regardless
of drop luck.

**Alternative / complement — somber floor.** Instead of (or alongside) the bell bearings,
inject extra **Somber Smithing Stone** copies so each tier [1]–[9] reaches a target count
(default **6**, matching the best-stocked tiers). Current copies are [1]=4, [2]=4, [3]=4,
[4]=5, [5]=5, [6]=8, [7]=4, [8]=8, [9]=6 — so a floor of 6 adds ~10 copies ([1]+2, [2]+2,
[3]+2, [4]+1, [5]+1, [7]+2). These ride the count-neutral swap as **filler** (not
progression like the bell bearings, so no in-world-slot pressure): a `UPLIFT_SOMBER_FLOOR`
= 6 knob in `curation.py`, gated on `auto_upgrade` == OFF. Guarantees enough somber exists
to take one weapon to +10 without depending on the merchant/shop-refresh path. Regular
stones need no floor — they're already well-stocked. (Optionally floor Somber Ancient Dragon
to 6 too; it's already at 6.)

## Classification & the shortage trap

All injected items must be **filler- or useful-tier, never progression** — keeps fill
logic clean and avoids walling the seed. Match what `_create_injectable_items` /
`_all_injectable_items` already do for curated injects.

Uniques (weapons/armor/talismans/spells/spirits/pouches/tears) → `useful`.
Stackables (runes/seeds/sacred tears/larval/stones) → `filler`.

Watch the **forbid_useful shortage trap** (`er-trimmed-forbid-useful-shortage`): trimmed +
default `forbid_useful` on missable/excluded can fail gen with "not enough filler." Since
uplift adds a chunk of `useful` items, confirm the `allow_useful` behaviors are set for
`dlc_only` trimmed seeds (it is a behavior setting, not a curation-code bug). The uplift
swap is count-neutral, so it does not by itself change the filler/useful ratio danger
beyond reclassifying the swapped slots — but it reclassifies *toward* useful, so verify.

## Side effects (intended)

Because the swap is count-neutral and happens entirely in `create_items`, no location is
added or removed and `num_required_extra_items` accounting is untouched. The only change
is *what* fills the existing DLC location slots. The deferred DLC filler that exceeds the
funding budget returns to the pool unchanged (same return-to-pool pattern as the small
runes and bad gear at `__init__.py:891` / `:917`).

## Phasing

- **Phase 0 — inject data.** `curation.py`: `UPLIFT_CUT_DLC` (+ id ranges),
  `UPLIFT_TALISMANS_S`, `UPLIFT_SPIRITS_TOP`, rune/seed/tear/stone name lists, weight
  table. Extend `HIGH_TIER_SPELLS` with the `S` subset. No behavior change yet.
- **Phase 1 — the swap.** `_curate_defer_dlc_filler`, `_dlc_filler_drop_rank`,
  `_uplift_inject_names` (uniques-then-weighted-stackables), and the funded-swap block in
  `create_items` mirroring `dlc_gear_curation`. Gate on `dlc_only` + trimmed.
- **Phase 2 — talisman tiers (optional).** Replace the hand `UPLIFT_TALISMANS_S` with a
  real ACCESSORY tier source folded into the `item_tiers.tsv` pipeline.

## Verification / eval

1. **Uplift report tool** (dev-loop, build first): dump the cut set (every DLC filler
   item deferred, with rank) and the inject set (every base-game item injected, with class
   and source bucket), plus the final swap count. Eyeball for false cuts (a DLC filler we
   actually wanted) and inject quality.
2. **Count invariants:** assert `injected == skipped <= skippable`; assert pool size and
   `num_required_extra_items` unchanged vs. a pre-uplift run of the same seed (the swap is
   count-neutral). dlc_only trimmed should stay ~329 *total*, with composition shifted.
3. **No-progression assertion:** assert zero injected items are `progression`.
4. **Uniqueness/caps:** assert each unique injects ≤ its cap (1, or vanilla count for
   memory stones / pouches); assert injected items are all `is_dlc == False`.
5. **auto_upgrade interaction:** with `auto_upgrade` on, assert no smithing/somber stones
   in the inject set.
6. **Beatability:** run fill/completion across several `dlc_only` seeds (trimmed; with and
   without `auto_upgrade`; forbid_useful vs allow_useful) on **Windows** — sandbox can't
   run AP (`er-dev-environment`). Confirm gen succeeds and is beatable.
7. **Regression:** confirm non-`dlc_only` modes are byte-for-byte unchanged (new code
   gated entirely behind `self.options.dlc_only`).

## Open questions

- **Remembrances:** inject as plain rune-consumables, or as the actual remembrance items
  (which the player can exchange at Roundtable for the boss weapon/spell)? Exchange is
  richer but needs the exchange shop reachable in dlc_only and a classification call.
  Lean: inject the named remembrances once as `useful`, let generic runes fill the rest.
- **Talisman tier source** (decided 2026-06-16: fold ACCESSORY into the `item_tiers.tsv`
  pipeline for Phase 2; Phase 1 hand list is seeded from community refs above).
- **Spirit Ash power floor:** how many top spirits is too many? A Mimic in every other
  seed is great; five Mimics in one seed is silly. Consider a per-seed cap on
  `UPLIFT_SPIRITS_TOP` injects.
- **Generalize to DLC-on full seeds?** Out of scope here (base items already reachable),
  but a "filler uplift" floor could apply there too. Revisit only if asked.
- **Visual/thematic:** base-game items physically appearing in DLC space — confirmed fine
  (they're just items), but flag if any base-game item has a DLC-map dependency for its
  model/icon.
