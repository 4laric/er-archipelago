# matt-free ER location pipeline — handoff

Goal: generate an Archipelago ER location set **from vanilla game data only** (no matt's rando
keys/descriptions, no Bedrock apworld). Keyed by the game's own event flags; the client watches
those flags. See the sibling `.md` docs for the reasoning/measurements behind each stage.

## Inputs (must exist under `elden_ring_artifacts/`)
- `vanilla_er/vanilla_er/*.csv` — Smithbox param dump (ItemLotParam_map/_enemy, ShopLineupParam,
  EquipParamGoods, NpcParam, Paramdex Names). This is the primary source.
- `mapstudio/*-msb-dcx/` — WitchyBND-decompiled MSBs (Event/Treasure carries `<ItemLotID>`;
  Part/Enemy carries `<NPCParamID>`).
- `event/*.emevd.dcx.js` — decompiled per-map event scripts.
- Reference only: `Archipelago/worlds/eldenring/er_static_detection_table.json` (current apworld
  flags) + `locations.py` (used to name/validate, NOT copied into output).

NOTE: scripts use absolute sandbox paths (`/sessions/.../mnt/...`). Update the `BASE/OUT/APW`
constants at the top of each script to your paths before running.

## Run order
1. `build_locations.py`  → `curated_locations.csv` + `synthetic_flags.csv` + first `locations_generated.py`
   - Walks params → candidate locations. Drops respawnables (`getItemFlagId==0`). Tags
     `crafting_material` (`EquipParamGoods.goodsType==2`), `filler` (item placed in ≥40 one-time
     lots = spam), `synthetic` (flag with no param source). Columns incl. `in_matt_set` (dial vs matt).
2. `region_assign.py`    → `lot_to_map.tsv` must exist first (produced by the MSB Treasure walk — see
   MATT-FREE-EXTRACTION / this repo's history; regenerate by scanning `mapstudio/*-msb-dcx/Event/
   Treasure/*.xml` for `<ItemLotID>` → map=folder). Assigns region from MSB Treasure.
3. `merge_regions.py`    → final `region_map.csv` + `flag_to_region.csv` + final `locations_generated.py`
   - Merges MSB Treasure + per-map EMEVD (lot/flag references) + the enemy NpcParam→MSB chain.

## Current state (2026-07-05)
- Locations: **5,163** (dial via `in_matt_set`/`filler`; matt's real set ≈ 4,150; `in_matt_set==1` ≈ 4,481).
- Synthetic (client-set) flags: **54** (`synthetic_flags.csv`).
- Region coverage: **2,791 / 5,163 = 54%** placed from game data (treasure 2,135 + emevd/enemy 656).
  `locations_generated.py` imports clean; each entry has `region`, `map_id`, `region_method`
  (treasure|emevd|pending), so resolved vs pending is explicit.

## STRUCTURAL CEILING (important)
MSBs place items ONLY via Event/Treasure — fully parsed. The 45% `REGION_PENDING` are awarded by
COMMON events / boss-death / NPC-gift / merchant, which have **no per-map placement to parse**. The
enemy NpcParam→MSB walk was run to completion: only 8/74 needed enemies are statically placed; the
rest are event-spawned. So further region gains are NOT more MSB parsing — they're item-CLASS lookups:

- **Shops (525)** → region = merchant's location (merchant→map table, ~40 merchants).
- **Boss drops / Great Runes (~26)** → boss → arena map (hand table).
- **Common-event tail** (physick tears, map stelae, NPC gifts) → assign by hand or leave "global".

## BUCKET TAKEDOWN — `resolve_buckets.py` (2026-07-05, DONE)
Confirmed the ceiling first: flag-prefix→map is only **58%** reliable and systematically confuses
Stormveil (m10) with Limgrave overworld (m60), so it is NOT used. The remainder is item-class /
judgment tables, exactly as predicted. `resolve_buckets.py` reads `region_map.csv` (KEEPS the
2,791 treasure/emevd rows) and resolves the 2,372 pending:

- **shop (525)** → ShopLineupParam ID hundred-block → region table (`SHOP_BLOCK`, confidence-tagged).
  After web-confirming merchant identities: **184 high, 255 med, 86 low**. Remembrance shop rows all
  point at Roundtable Hold (fixed: shop branch runs before the boss-name match). Web-confirmed:
  100200→Liurnia (War Counselor Iji, via Carian Filigreed Crest + Carian sorceries),
  102200→Gravesite Plain DLC (Moore, via Sanguine Amaryllis/Black Pyrefly),
  100900→Siofra/Nokron (Abandoned Merchant, Larval Tear + Nascent Butterfly).
  Nomadic blocks 100500-100800 pinned by signature stock (Waypoint note, Crimson Amber Medallion,
  Land of Reeds set). Facts only — no wiki prose copied into the pipeline.
- **boss_arena (30)** → Great Runes (`GREAT_RUNE`, high) + known remembrances (`REMEMBRANCE`, med).
- **synthetic (54)** → apworld area-code prefix in the location name → region (`AREACODE`, med).
  NOTE: uses the apworld's own naming for the region only (placement fact, not description) — flagged.
- **global (1,778)** → honestly-unplaced common-event tail (crystal tears 65xxx, crafting pots 66xxx,
  cookbooks 67xxx, event-spawned enemy drops). One item drops in many regions → a specific region
  would be fabrication. Left as region "Global / Common-event (unplaced)", method `global`.

Result: **region-placed 2,791→3,385 (54%→65%)**, global tail 1,778 (34%), 290 regions.
`locations_generated.py` regenerated (imports clean, 5,163 locs, method col = treasure|emevd|
shop_merchant|boss_arena|synthetic_areacode|global). Per-row audit trail incl. confidence in
`bucket_resolution_report.csv` (2,372 rows).

## GLOBAL TAIL — `resolve_global_tail.py` (2026-07-05, runs AFTER resolve_buckets.py)
Refines the 1,778 `global` rows with data-clean signals only:
- **map_name (2)** — item name starts `Map:` → region is in the name (high).
- **flag_prefix (415)** — learns prefix→region from the 2,791 ground-truth (treasure/emevd) rows;
  applies the longest prefix with support≥3 and purity≥0.85 to non-filler rows (med if ≥0.95 else
  low). Ambiguous prefixes (Stormveil m10 vs Limgrave overworld m60) fail purity and stay global —
  no fabrication. Placed interior-dungeon items correctly (Catacombs m30, Caves m31, Leyndell m11…).
- **boss_arena +10** — folded the 10 DLC Shadow-of-the-Erdtree remembrances into `REMEMBRANCE`.
- **global_filler (592)** — spam (≥40 lots) + scattered upgrade mats (smithing stones/glovewort/
  golden runes) → `Global / Filler (scattered by design)`. Honest: one item, dozens of spots.
- **global (759, 14%)** — irreducible tail: quest/NPC-gift/common-event items with no placement.

- **cookbook (42)** — `COOKBOOK` name→region table, web-confirmed (facts only, no wiki prose):
  base-game ones to their region (Perfumer's→Altus, Glintstone Craftsman's [8]→Consecrated Snowfield,
  Fevor's→Limgrave…), DLC families to Land of Shadow sub-areas (Scadu Altus, Shadow Keep, Jagged Peak,
  Abyssal Woods…).

Result: **real-region placed 65%→74% (3,854/5,163)**, 308 regions. Audit trail =
`tail_resolution_report.csv`. Run order now: resolve_buckets.py → (cp region_map to PIPE) →
resolve_global_tail.py. Remaining 717 `global` (13%) = bell bearings + crystal tears (~60, web-
tableable if ever wanted) + ~650 quest/NPC/common-event items that stay global by nature —
especially fine since questlines were derandomized (those slots aren't checks).

## REFINEMENTS 2026-07-05 (Alaric observations)
- **Multi-merchant / scroll-gated items** — an item sold across >1 merchant block (e.g. Glintblade
  Phalanx: Sellen/Thops/Seluvis/Miriel via Royal House Scroll; consumables like Stonesword Key at
  every nomadic merchant) can't have ONE region. `resolve_buckets.py` now detects equipId-across->1-
  block and tags those **203 rows** `shop_multi` → "Multiple merchants (various regions)". This dropped
  low-confidence shop guesses 86→49.
- **m61 = DLC** (Land of Shadow), not a Lands Between tile. `resolve_global_tail.py` normalizes any
  `Overworld m61_*` → "Land of Shadow (DLC)" (363 rows: 239 treasure + 124 flag_prefix).

## SUB-BLOCK CORRECTIONS 2026-07-05 (Alaric ground-truth, screenshots + play knowledge)
`SHOP_ID_RULES` (exact shop-ID ranges, checked before the hundred-block) fix cases where one block
holds two merchants or a non-merchant lineup:
- **102300 is TWO merchants**: IDs 102300-08 = Count Ymir sorceries → Cathedral of Manus Metyr (DLC);
  IDs 102350-55 = Bayle/Ghostflame incantations (trade dragon hearts) → Grand Altar of Dragon
  Communion (Jagged Peak, DLC). (Was mislabeled Raya Lucaria.)
- **600000 / 1600100 / 1600400 / 9000000 / 9001000 are NOT merchants** → `shop_reference` (starting
  gear, caster kit, gallery lists; items are really placed in the world — e.g. Glintstone Staff =
  noble-sorcerer drop S of Waypoint Ruins, Clawmark Seal = Gurranq, Stars of Ruin = Lusat/Sellen
  questline, Axe Talisman = Mistwood Ruins basement). 20 rows, excluded from region placement.
- **101800 = Twin Maiden Husks** (Roundtable Hold), Alaric-confirmed: Scimitar/Battle Axe/Rapier/
  Heater Shield/Blue Cipher Ring/Trick-Mirrors. Promoted low→high.

**Final: real-region placed 3,944/5,163 = 76%.** Low-confidence review list = **39** rows
(`low_confidence_review.csv`): 24 flag_prefix (Land of Shadow DLC, sub-area unconfirmed) + 15
shop_merchant (block 100900 Abandoned Merchant → Siofra/Nokron, coarse). shop_multi 189 (multi-
merchant), shop_reference 20, global_filler 578 (scattered), global 621 (irreducible quest/NPC tail).

**Judgment calls for Alaric to confirm/correct** (15 shop rows tagged `low`, block 100900):
1. In-game check on the residual low blocks: 100900 (Siofra/Nokron?), 101800 (Roundtable mixed?),
   102300 & 1600400 (Raya Lucaria sorceries?), 600000 + 1600100 + 9000000/1000 (unknown singles /
   tutorial). Alaric offered to verify these in-game.
2. Whether the 1,778 `global` tail stays global or gets hand-assigned by class.
3. RESOLVED — remembrance shop rows now all → Roundtable Hold (Enia derandomized anyway).

## Also open (not region-related)
- Overworld tiles are resolved to exact `m60_XX_YY` but not grouped into named areas
  (Limgrave/Caelid…) — needs a tile-grid; boundary tiles straddle regions.
- Wiring this backbone into an actual apworld `__init__.py` + slot_data (the client already consumes
  `location→flag`; drop the matt `key_resolver`).
