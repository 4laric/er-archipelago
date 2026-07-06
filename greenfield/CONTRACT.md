# Greenfield ER apworld <-> client slot_data contract

AUTO-GENERATED from `eldenring_gf/contract.py` (the single source of truth). Do not edit.

| key | shape | req | profile | producer | client consumer | meaning |
|-----|-------|-----|---------|----------|-----------------|---------|
| `apIdsToItemIds` | SCALAR_INT_MAP | yes | both | core._base_slot_data | core.rs:309 i64_map | AP item id (str) -> ER FullID granted on receipt. |
| `locationFlags` | SCALAR_INT_MAP | yes | both | core._base_slot_data | core.rs:330 i64_to_u32_map | AP location id (str) -> its ER acquisition event flag; the flag-poll detection table. |
| `regionOpenFlags` | SCALAR_INT_MAP | yes | both | core._base_slot_data | region.rs:120 str_to_u32 | '<Region> Lock' -> the region-open event flag set when that lock is received. |
| `regionSphereTargets` | ANY |  | greenfield | core._base_slot_data | (informational) | region -> sphere target [0..1] for completion scaling; not enforced by the client. |
| `areaLockFlags` | TRIPLE_LIST | yes | both | features/area_locks.py | region.rs:103 parse_triples | [lo,hi,open_flag] play_region ranges; locked (kicked) while open_flag is unset. |
| `lockRevealFlags` | LISTVAL_INT_MAP |  | both | (future) per-region map reveal | region.rs:121 str_to_u32vec | '<Region> Lock' -> map-reveal/enforcement flags set on lock receipt. |
| `regionGraces` | LISTVAL_INT_MAP |  | both | features/grace_rando.py | region.rs:122 str_to_u32vec | '<Region> Lock' -> grace warp flags lit on lock receipt (bundle=all, freebie=front door). |
| `graceItems` | SCALAR_INT_MAP |  | greenfield | features/grace_rando.py | region.rs:123 str_to_u32 | scatter grace item name -> the single grace flag it lights when received. |
| `startRegion` | STR | yes | both | features/start_grace.py | core.rs:410 as_str | name of the always-kept start region (diagnostic + start anchor). |
| `startGraces` | INT_LIST |  | both | features/start_grace.py | startgrants.rs:58 arr_u32 | grace flags lit at spawn so the first warp is possible (front-door of start region). |
| `startItems` | INT_LIST |  | both | features/start_items.py | startgrants.rs:57 arr_i32 | FullIDs granted once at game start (Torch, Spectral Steed Whistle, ...). |
| `reveal_all_maps` | BOOL |  | both | features/start_grace.py | startgrants.rs as_bool | reveal the whole world map + underground view (client owns the RE'd flag set). |
| `goalLocations` | INT_LIST | yes | both | features/goal_locations.py | goal.rs parse | AP location ids whose completion == victory; client sends Goal when all are done. |
| `checkItemFlags` | LISTVAL_INT_MAP |  | both | features/check_item_flags.py | detour.rs CHECK_ITEM_FLAGS<u32,Vec<u32>> | vanilla FullID (str) -> the check flags it belongs to; suppresses the vanilla bag-add. |
| `shopRowFlags` | SCALAR_INT_MAP |  | both | features/shops.py | core.rs:359 i64_to_u32_map | ShopLineupParam row id -> eventFlag_forStock written for shop checks. |
| `shopPreviewGoods` | SCALAR_INT_MAP |  | both | features/shops.py | core.rs:353 i64_map | AP location id -> preview goods id shown in the shop slot. |
| `dungeonSweepFlags` | LISTVAL_INT_MAP |  | both | features/boss_sweeps (P3b client patch) | region.rs:104 as_object | dungeon trigger flag (str) -> the member AP location ids auto-registered on clear. |
| `progressiveGrants` | NESTED_GRANTS |  | both | features/progressive.py | progressive.rs | item name -> ordered [{goods, flags}] granted on each successive receipt. |
| `death_link` | BOOL_OR_INT |  | both | features/deathlink.py | options::parse_death_link | shared deaths across the multiworld. |
| `enable_dlc` | BOOL_OR_INT |  | both | core (options echo) | options::parse_dlc | DLC / Land of Shadow regions active; gates the DLC map-reveal flags. |
| `world_logic` | STR |  | greenfield | core._base_slot_data | (informational) | logic profile tag, e.g. 'region_lock'. |
| `locationIdsToKeys` | ANY |  | bedrock | (bedrock apworld) | key_resolver.rs | matt slot key token per location; client resolves token1 -> flag (bedrock path). |
| `naturalKeyTriggers` | ANY |  | bedrock | (bedrock apworld) | key_resolver.rs / region.rs | bedrock natural key triggers. |
| `lockGrantItems` | ANY |  | bedrock | (bedrock apworld) | region.rs | items granted on a region lock receipt (bedrock). |
| `dungeonSweeps` | ANY |  | bedrock | (bedrock apworld) | region.rs | bedrock dungeon sweep spec (greenfield uses dungeonSweepFlags). |
| `itemCounts` | ANY |  | bedrock | (bedrock apworld) | core.rs | per-item quantity map. |

## Shapes

| shape | client parser |
|-------|---------------|
| SCALAR_INT_MAP | `i64_to_u32_map / i64_map / str_to_u32` |
| LISTVAL_INT_MAP | `str_to_u32vec` |
| TRIPLE_LIST | `parse_triples` |
| INT_LIST | `arr_i32 / arr_u32` |
| BOOL | `as_bool` |
| BOOL_OR_INT | `parse_death_link / parse_dlc` |
| STR | `as_str` |
| NESTED_GRANTS | `progressive.rs custom` |
| ANY | `(bedrock; not greenfield-validated)` |
