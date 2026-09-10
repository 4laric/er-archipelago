# Furnace golem datamine

Run: 2026-09-10T06:57:45.135886+00:00

Scanned 1346 Witchy MSB directories, 34681 Enemy/DummyEnemy XMLs, and 589 event scripts.

**Result: 8 distinct c5170 entities, 9 placements, 16 guaranteed item rewards.**

The extra placement is entity 2045460200 in map versions m61_11_11_02 and m61_11_11_12. It is one encounter, not two.

The repository note naming c4900 is incorrect for this corpus. The full enemy-part scan finds zero c4900 records.

Each golem awards one tear plus one Furnace Visage through common event 90005301. Its NPC enemy-lot table rolls only an empty slot. Death flags and item acquisition flags are separate columns; do not substitute one for the other.

| Event map | Entity ID | Death flag | Award base lot | Drops |
|---|---:|---:|---:|---|
| m61_45_46_00;m61_45_46_10 | 2045460200 | 2045460200 | 2045460500 | Furnace Visage x1; Crimson-Sapping Cracked Tear x1 |
| m61_50_46_00 | 2050460300 | 2050460300 | 2050460500 | Furnace Visage x1; Bloodsucking Cracked Tear x1 |
| m61_50_46_00 | 2050460310 | 2050460310 | 2050460510 | Furnace Visage x1; Oil-Soaked Tear x1 |
| m61_46_39_00 | 2246390200 | 2046390200 | 2046390060 | Furnace Visage x1; Glovewort Crystal Tear x1 |
| m61_46_42_00 | 2246420300 | 2046420300 | 2046420980 | Furnace Visage x1; Deflecting Hardtear x1 |
| m61_48_40_00 | 2248400200 | 2048400200 | 2048400020 | Furnace Visage x1; Viridian Hidden Tear x1 |
| m61_48_46_00 | 2248460291 | 2248460291 | 2048460700 | Crimsonburst Dried Tear x1; Furnace Visage x1 |
| m61_51_45_00 | 2251450280 | 2251450280 | 2051450700 | Furnace Visage x1; Cerulean-Sapping Cracked Tear x1 |

## Evidence and limits

- `placements.tsv`: all nine original records, NPC IDs, raw map-local XYZ, map versions, source paths, and hashes.
- `encounters.tsv`: deduplicated entities and event call file/line references.
- `drops.tsv`: all sixteen item rows, quantities, weights, item IDs, and acquisition flags.
- `manifest.json`: timestamp, scan coverage, and hashes of the source files used in the joins.
- Coordinates belong to the containing MSB map, not the fine map embedded in the part name.
- `npc_getSoul_raw` is the raw param reward; scaling effects were not evaluated, so it is not a final in-game rune payout.
- Static datamine of the local unpacked corpus. No live-game test, world regeneration, or taxonomy integration was performed.
- Common event 90005301 waits for CharacterRatioDead, delays, sets the death flag, and awards the item-lot group in the player's own world. See the exact common-event source reference in the manifest.
