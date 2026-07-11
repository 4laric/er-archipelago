# Location-category audit (ground-truth confirmed)

Running audit of apworld location categories against **game ground truth**, so each category can be
marked 100%-confirmed. Method for every category:

1. Find the goods id(s) from `msg/.../GoodsName.fmg.xml`.
2. Extract every placement from `elden_ring_artifacts/vanilla_er/vanilla_er/ItemLotParam_map.csv`
   and `ItemLotParam_enemy.csv` (match `lotItemId0N == goods id`, `lotItemCategory0N == 1`), keyed by
   `getItemFlagId` — this is the authoritative set.
3. Diff that against the flags the apworld actually exposes in `greenfield/eldenring/data.py`.
4. Fix any real gap in the **generator** (`gen_data.py`), never by hand-editing generated data.

A single acquisition flag = a single AP check. Where two item-lots share one `getItemFlagId`
(e.g. a boss that drops a Seed *and* a spirit ash), there can only be one check for that flag; the
co-located item is not independently randomizable.

---

## Golden Seed — CONFIRMED (after fix) · goods id 10010

**Ground truth:** 43 `ItemLotParam_map` lots + 1 `ItemLotParam_enemy` lot = **44** placements.

- The 43 map lots all carry a real `getItemFlagId` → representable as flag-keyed checks.
- The 1 enemy lot (id 40 = **Kenneth Haight** NPC-kill drop) has `getItemFlagId 0` → **cannot** be a
  flag-keyed check in the matt-free client. Stays vanilla. This is the only non-representable Seed.

**Before:** apworld exposed 41/43 map lots. Two were dropped by the generator:

| flag | lot(s) | issue | fix |
|------|--------|-------|-----|
| `510280` | 10280 = Golden Seed, 10281 = Banished Knight Oleg (ash) | shared-flag pickup; `region_map` labeled it Golden Seed but the flag-tile decode couldn't place it, so recovery dropped it | `GLOBAL_RECOVER[510280] = "Limgrave"` (Stormhill golden sapling, wiki #3) |
| `520160` | 20160 = Redmane Knight Ogha (ash), 20161 = Golden Seed | shared-flag pickup; scan named the flag after the lower lot id (the ash), losing the Seed, and it was dropped too | `GLOBAL_RECOVER[520160] = "Caelid"` + `ROW_ITEM_NAME_FIX[520160] = "Golden Seed"` (War-Dead Catacombs Putrid Tree Spirit, wiki #17) |

Neither co-located ash (Oleg 201000, Ogha 257000) is a check anywhere else, so recovering these flags
as Golden Seeds loses nothing.

**After fix:** `data.py` yields **43/43** flag-keyed Golden Seeds (verified by sandbox regen:
`Limgrave :: Golden Seed [f510280]`, `Caelid :: Golden Seed [f520160]`; total checks +2).

> Regen note: these are appended as *recovered* rows, which shifts the positional ap-ids of later
> recovered rows. The generator's `MAJOR_BOSS_EXTRAS` invariant hard-codes some recovered ap-ids and
> will fire on regen (its intended safety-valve) — those ap-ids must be re-synced during the Windows
> regen. Do the regen on Windows (`python greenfield/gen_data.py`); the sandbox regen diverges from the
> committed data at baseline and is not canonical for ap-ids.

---

## Sacred Tear — CONFIRMED (already correct) · goods id 10020

**Ground truth:** 13 `ItemLotParam_map` lots, 0 enemy. The apworld already exposes **all 13**, none
missing or spurious — no fix needed.

| region | flag |
|--------|------|
| Limgrave | 1043357100, 1046387100 |
| Weeping Peninsula | 1041337200, 1044337100 |
| Liurnia of the Lakes | 1036497000, 1037497100, 1039397000 |
| Altus Plateau | 1039527400, 1040517400 |
| Mt. Gelmir | 39207170 |
| Caelid | 1050387020 |
| Mountaintops of the Giants | 1051537800, 1054557800 |

The common "12 churches" wiki list omits the **Mt. Gelmir** lot (`39207170`, flag format unlike the
others but a real placement). The apworld's 13 is correct; the wiki list was the incomplete one.

---

## Achievement / Major Boss (non-remembrance) — CONFIRMED (after fix) · 18 bosses

Remembrance bosses are tracked separately. Method here: resolve each boss's **signature drop** to its
item id (`WeaponName`/`GoodsName`/`ProtectorName`/`GemName` FMG), find the `ItemLotParam` lot's
`getItemFlagId`, then check that flag's presence **and region** in `data.py`.

Result: 8 were already correct; **4 were mis-regioned** (check existed, wrong region); **6 had no check
at all**. All 18 now resolve to a check in the correct region.

**6 missing → recovered (`GLOBAL_RECOVER` + `_BOSS_DROP_EXTRAS`).** Same "unplaced common-event" class
as the dropped Golden Seeds:

| boss | drop | flag | region |
|------|------|------|--------|
| Red Wolf of Radagon | Memory Stone | `60440` | Liurnia (Raya Lucaria) |
| Dragonkin Soldier of Nokstella | Frozen Lightning Spear | `510090` | Eternal Cities |
| Godskin Duo | Bell Bearing [4] / Black Flame Tornado | `510140` | Farum Azula |
| Magma Wyrm Makar | Magma Wyrm's Scalesword | `510260` | Liurnia (Ruin-Strewn Precipice) |
| Ancestor Spirit | Ancestral Follower Ashes | `510320` | Eternal Cities (Siofra) |
| Golden Hippopotamus | Aspects of the Crucible: Thorns | `510440` | Shadow Keep (DLC) |

**4 mis-regioned → corrected** (re-region only; ap-ids unchanged):

| boss | flag | was | now | mechanism |
|------|------|-----|-----|-----------|
| Royal Knight Loretta | `510810` | Roundtable Hold (HUB) | Liurnia (Caria Manor) | `GLOBAL_RECOVER` |
| Valiant Gargoyles | `510100` | Altus (mis-tiled m35 Divine Tower) | Eternal Cities (Nokstella) | `FLAG_REGION_OVERRIDE` |
| Mimic Tear | `510340` | Roundtable Hold (HUB, mislabeled "Larval Tear") | Eternal Cities (Nokstella) | `GLOBAL_RECOVER` (was `HUB`) |
| Godskin Noble | `510210` | Altus | Mt. Gelmir (Volcano Manor) | `GLOBAL_RECOVER` |

Mimic Tear note: flag `510340` is one boss pickup (lot 10340 = Larval Tear ×2, lot 10341 = Silver Tear
Mask), not scattered copies — the prior `HUB` was based on the "Larval Tear" mislabel.

**8 already correct:** Margit (`60510`, Stormveil), Leonine Misbegotten (`510800`, Weeping), Elemer of
the Briar (`510820`, Altus), Mohg the Omen (`510250`, Altus = Leyndell/Shunning-Grounds fold), Commander
Niall (`510840`, Mountaintops), Loretta Knight of the Haligtree (`510190`, Haligtree), Bayle (`510630`,
Jagged Peak), Godfrey First Elden Lord (Talisman Pouch, tracked).

**Talisman Pouches (all 3 attributed + regioned, 2026-07-10).** All share item `10040`, so they were
datamined via EMEVD:

| flag | source | was | now | evidence |
|------|--------|-----|-----|----------|
| `60510` | Margit the Fell Omen | Stormveil | Stormveil (unchanged) | lot 10000, m10 |
| `60500` | Finger Reader **Enia** (Roundtable, 2-Great-Rune reward) | Weeping (mis-decoded m30 Hero's Graves) | **Roundtable Hold** | m11_10 event 11100797 gates on `!EventFlag(60500)` after batch flags 3487/3489 |
| `60520` | **Godfrey** First Elden Lord (golden shade, Leyndell→Altus) | Caelid (mis-tiled m34_13) | **Altus Plateau** | re-referenced by the Divine Tower of Caelid event 90005110 (m34_13) — same m34 mis-tile as Radahn/Rennala |

Both re-regioned via `FLAG_REGION_OVERRIDE` (no ap-id change).

---

## Great Runes — one mis-region (progression-stranding) · flags 171-176

Datamined from a live seed report (Morgott's Great Rune appeared in Farum Azula). Ground truth: each
great rune drops from its shardbearer's region.

| flag | rune | boss region | was | fix |
|------|------|-------------|-----|-----|
| 171 | Godrick's | Stormveil | Stormveil ✓ | — |
| 172 | Radahn's | Caelid | Caelid ✓ | — |
| **173** | **Morgott's** | **Leyndell → Altus** | **Farum Azula** ✗ | `FLAG_REGION_OVERRIDE[173]="Altus Plateau"` |
| 174 | Rykard's | Mt. Gelmir | Mt. Gelmir ✓ | — |
| 175 | Mohg's | Mohgwyn Palace | Mohgwyn Palace ✓ | — |
| 176 | Malenia's | Haligtree | Haligtree ✓ | — |

`173` was mis-tiled to `m13` (Crumbling Farum Azula, where flag 173 is referenced by the endgame
Erdtree sequence) by the EMEVD scan; its sibling Rem. of the Omen King (`510040`) is correctly Altus.
**Severity: this can produce UNBEATABLE seeds** — a region-lock placed on this location reads as
reachable from Farum Azula but is physically behind Morgott in Altus (often the goal region), so a
progression lock parked there becomes circular. Fix verified via `/tmp` regen (`f173` → Altus Plateau).

> Same regen caveat as Golden Seeds: the 6 recovered checks shift later recovered ap-ids and the
> `MAJOR_BOSS_EXTRAS` invariant must be re-synced on the **Windows** regen. The 4 region corrections do
> NOT add checks, so they don't shift ap-ids.
