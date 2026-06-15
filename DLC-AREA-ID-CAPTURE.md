# DLC region area_id capture + inference (2026-06-15)

Physical region-lock enforcement reads the FieldArea area id (@0xE4) and kicks/warps if the
current area falls in a locked region's `area_ids` range. This doc records what was INFERRED from
the msb/map ids in `location script/itemslots.yaml` and what still needs an in-game `area=` capture.

## Two id schemes (confirmed in base game)
- **Interiors / legacy dungeons / undergrounds** report a MAP-BLOCK-derived id: `mNN_BB -> NN*1000 + BB*10`
  (confirmed: Siofra `m12_07` = 12070). Width-9 ranges per block, like base Siofra `(12020,12029)`.
- **Overworld** reports a PLACE-NAME id, NOT the tile id (confirmed: Weeping=61002, Altus=63000 -- these
  are NOT the `m60` tile ids). So overworld region ids cannot be inferred from msb names; they must be
  captured in-game.

## DONE -- 4 interior DLC regions WIRED (inferred, map_region_data.py)
These regions ARE wholly interior maps with a 1:1 lock, so they're complete:

| Region              | msb        | area_ids (wired) | lock              |
|---------------------|------------|------------------|-------------------|
| Belurat             | m20_00     | (20000, 20009)   | Belurat Lock      |
| Enir Ilim (GOAL)    | m20_01     | (20010, 20019)   | Enir Ilim Lock    |
| Shadow Keep         | m21_00/01/02| (21000, 21029)  | Shadow Keep Lock  |
| Stone Coffin Fissure| m22_00     | (22000, 22009)   | Stone Coffin Lock |

STILL INFERRED (one analogy step from the confirmed underground scheme). CONFIRM on first DLC run:
walk into Belurat, read the `area=` log -- expect 20000 (or 200xxxx -> client //100 -> 20000-ish).
If it matches, the scheme holds for ALL interiors below; if not, adjust the *1000+*10 mapping.

## READY TO WIRE -- interior sub-dungeons (after the scheme is confirmed)
Access verified via the region graph (the PARENT lock that gates entry, not just the name). Skip the
ones whose parent is Gravesite Plain (the FREE hub -- enforcing them would wrong-kick).

| Sub-dungeon                 | msb    | area_ids        | parent lock        | note |
|-----------------------------|--------|-----------------|--------------------|------|
| Midra's Manse               | m28_00 | (28000, 28009)  | Abyssal Lock       | end of Abyssal Woods |
| Scorpion River Catacombs    | m40_01 | (40010, 40019)  | Rauh Base Lock     | |
| Darklight Catacombs         | m40_02 | (40020, 40029)  | Recluses' Lock     | Recluses'->Darklight->Abyssal |
| Bonny Gaol                  | m41_01 | (41010, 41019)  | Scadu Altus Lock   | |
| Lamenter's Gaol             | m41_02 | (41020, 41029)  | Charo's Lock       | |
| Ruined Forge of Starfall    | m42_02 | (42020, 42029)  | Scadu Altus Lock   | |
| Taylew's Ruined Forge       | m42_03 | (42030, 42039)  | Rauh Base Lock     | |
| Rivermouth Cave             | m43_00 | (43000, 43009)  | Ellac Lock         | Ellac not in REGIONS yet |
| Finger Birthing Grounds     | m25_00 | (25000, 25009)  | Scadu Altus Lock   | behind Metyr/Ymir quest |
| Fog Rift Catacombs          | m40_00 | (40000, 40009)  | Gravesite = FREE   | DO NOT enforce |
| Belurat Gaol                | m41_00 | (41000, 41009)  | Gravesite = FREE   | DO NOT enforce (entered from Gravesite) |
| Ruined Forge Lava Intake    | m42_00 | (42000, 42009)  | Gravesite = FREE   | DO NOT enforce |
| Dragon's Pit                | m43_01 | (43010, 43019)  | Gravesite = FREE   | leads to Jagged Peak Foot |

## MUST CAPTURE IN-GAME -- overworld regions (place-name ids, NOT inferable)
The DLC overworld is one continuous map (`m61_44`..`m61_54`), and the tiles are SHARED across regions
(e.g. tile `m61_48` appears in Gravesite, Scadu Altus, Cerulean, Charo's, Rauh Base, Abyssal Woods).
So tile ids cannot distinguish regions -- the per-region PLACE-NAME id is the only valid signal.

Walk into each region, read the `RegionLock: area=...` log line, and fill `map_region_data.REGIONS`.
The m61 tiles below are orientation only (where each region lives).

| Region               | m61 tiles (orientation)        | place-name area_id |
|----------------------|--------------------------------|--------------------|
| Gravesite Plain      | m61_44-49 (FREE hub)           | capture (or leave [] -- it's free) |
| Castle Ensis         | ~m61_47/48 (open castle)       | capture |
| Fog Rift Fort        | ~m61_47                        | capture |
| Scadu Altus          | m61_47-51                      | capture |
| Cerulean Coast       | m61_46-49                      | capture |
| Charo's Hidden Grave | m61_46-49                      | capture |
| Rauh Base            | m61_44-48                      | capture |
| Ancient Ruins of Rauh| m61_44-47                      | capture |
| Abyssal Woods        | m61_48-53                      | capture |
| Jagged Peak Foot     | m61_49/51/52                   | capture |
| (Jagged Peak summit) | m61_53/54                      | capture (Bayle) |

FIRST overworld capture also RESOLVES the scheme: if `area=` is 68xxx/69xxx -> place-name (expected);
if it's 614xx -> tile id (then enforcement granularity needs rethinking, since tiles are shared).
