# Checks, Progression & Filler — how the Elden Ring pool works

A short guide to what actually gets randomized, what "counts" for progression, and
how the item pool splits up — with real numbers from the current apworld.

> Your seed prints its own exact figures. After generation the apworld emits an
> `ER_COUNTS` line (checks, progression, local) that the build surfaces — treat the
> numbers below as structure and ballpark, and that line as ground truth for a
> specific seed.

---

## What is a check?

A **check** is a randomized location — a spot in the world that normally hands you
an item, but now hands over an Archipelago item (yours or another player's). Chests,
enemy and boss drops, NPC gifts, corpses, and merchant slots are all checks. Finding
one *sends* whatever's there into the multiworld.

The Elden Ring location table defines about **4,900 possible checks**:

| Source | Checks |
|---|---:|
| Base game | ~3,741 |
| Shadow of the Erdtree (DLC) | ~1,154 |
| **Full table** | **~4,900** |

No single seed uses all of them. The active set shrinks based on your options:

- **DLC off** removes the ~1,154 Land of Shadow checks.
- **The Shattering** (`num_regions`) seals whole regions — only the kept majors are
  live, so a short run uses a fraction of the base table (see the per-region table
  below to see how it adds up).
- **`location_pool: trimmed`** curates the set down further.
- **Missable** locations (~365 in the base game — NPC-death drops and the like) and
  **shop** slots (~446) are still checks, but special: see below.

Transitions with no item (major world events) are not checks — they're just used to
keep the logic honest.

---

## Progression vs useful vs filler

Every item Archipelago places carries a **classification** that tells the generator
how much it matters. Across the whole Elden Ring catalog of **3,277 item types**:

| Class | Types | What it means |
|---|---:|---|
| Progression | 220 | Required to reach other checks or the goal. Always placed so it's obtainable in order. |
| Useful | 25 | Strong but not required — top-tier gear/upgrades you're glad to get. |
| Filler | 3,032 | Everything else — never gates anything. |

**Progression** is the spine of a run. In Elden Ring that's the region keys/locks
(the heart of the Shattering), plus the classic route-openers:

- the 7 Great Runes (+ Great Rune of the Unborn),
- the 5 route medallions — Dectus (Left/Right), Rold, Haligtree Secret (Left/Right),
- key items — Stonesword Keys, whetblades, Cursemark of Death, and so on.

A given seed only uses the progression it needs, plus the **region-lock items
generated for that seed** (one per gated region — these are made at generation time,
so they're on top of the 220 catalog types).

**Useful** items never block you. **Filler** is runes, consumables, crafting
materials, low-tier gear, and a light seasoning of deliberate comedy junk
(`junk_retention`). By category the catalog is mostly goods and gear:

| Category | Types |
|---|---:|
| Goods (consumables, materials, runes...) | 1,832 |
| Armor | 621 |
| Weapons | 564 |
| Talismans | 155 |
| Ashes of War | 105 |

Two safety rules worth knowing: **missable** and **excluded** locations never hold
progression or useful items — they're filler-only, so you can't lose a run by missing
an NPC drop. And `important_locations` lets you *protect* meaningful spots
(remembrances, golden-seed trees, churches, Scadutree fragments, revered ashes) so
they hold something worth the trip.

---

## Local vs foreign filler

This only matters in a **multiworld**. In a solo seed every check holds one of your
own Elden Ring items — 100% local, zero foreign.

In a shared game, items travel between worlds:

- Elden Ring keeps its **filler local** by default (`local_item_option`): junk goods
  stay in Elden Ring instead of clogging other players' worlds. Your *gear*
  (weapons, armor, talismans, ashes of war) can still travel to others.
- **Foreign** items are other games' items sitting in your Elden Ring checks. How
  many depends on the room — the number and size of the other worlds.
- `curated_fill` adds a dial, `filler_foreign_pct` (default 15%), that opens a slice
  of your filler slots to incoming foreign filler when you want more cross-pollination.

So in a small room your checks stay mostly local; in a big room, more of them hold
other games' items — which is the whole point of a multiworld.

---

## Example runs (approximate)

Ballpark shapes for common configs. Absolute check counts are pre-trim sums of the
active regions; your `ER_COUNTS` line is the real figure.

| Config | Checks | Progression (gating) | Useful | Filler | Foreign |
|---|---:|---:|---:|---:|---:|
| The Shattering, `num_regions: 4`, base, **solo** | several hundred (kept majors only) | a handful — ~4 region locks + required runes/medallions/keys | up to ~25 | the rest | 0 (solo) |
| The Shattering, `num_regions: 4`, base, **4-player** | same checks | same | same | most | ~15% of filler (with `curated_fill`) |
| Full base game, no shatter, solo | ~3,700 | small — vanilla route items only | ~25 | thousands | 0 |
| Messmer / `dlc_only`, `trimmed`, solo | ~470 | the DLC lock breadcrumb + Scadu-fragment soft-gates | ~25 | the rest | 0 |

The recurring point: **progression is always a small set** — even a big seed gates on
well under thirty true progression items. Almost everything you pick up is useful or
filler; the locks and route items are the thin thread the generator guarantees you
can always follow to the goal.

---

## Per-region check counts (base game)

How the base table distributes — useful for seeing how a Shattering run's kept regions
sum up. (Counts include missable and shop slots.)

| Region | Checks | Region | Checks |
|---|---:|---|---:|
| Liurnia of the Lakes | 337 | Limgrave | 224 |
| Altus Plateau | 220 | Caelid | 206 |
| Roundtable Hold (hub) | 178 | Leyndell, Royal Capital | 120 |
| Mountaintops of the Giants | 128 | Stormveil Castle | 117 |
| Mt. Gelmir | 108 | Consecrated Snowfield | 101 |
| Weeping Peninsula | 100 | Siofra River | 79 |
| Deeproot Depths | 70 | Raya Lucaria Academy | 69 |
| Subterranean Shunning-Grounds | 69 | Dragonbarrow | 62 |
| Farum Azula Main | 58 | Capital Outskirts | 58 |
| Nokron, Eternal City | 56 | Mohgwyn Palace | 55 |
| Caria Manor | 55 | Ainsel River Main | 46 |
| Stormhill | 45 | Farum Azula | 44 |

(Smaller caves, catacombs, and tunnels add the rest; full detail lives in the
apworld's `locations.py`.)
