# Greenfield ER apworld <-> client slot_data contract

AUTO-GENERATED from `eldenring/contract.py` (the single source of truth). Do not edit.

Sub-keys of the `options` echo are listed as `options.<name>` -- the client reads
runtime options ONLY through that sub-dict (er-logic/src/options.rs).

| key | shape | req | profile | producer | client consumer | meaning |
|-----|-------|-----|---------|----------|-----------------|---------|
| `apIdsToItemIds` | SCALAR_INT_MAP | yes | both | core._base_slot_data | core.rs:309 i64_map | AP item id (str) -> ER FullID granted on receipt. |
| `locationFlags` | SCALAR_INT_MAP | yes | both | core._base_slot_data | core.rs:330 i64_to_u32_map | AP location id (str) -> its ER acquisition event flag; the flag-poll detection table. |
| `regionOpenFlags` | SCALAR_INT_MAP | yes | both | core._base_slot_data | region.rs:120 str_to_u32 | '<Region> Lock' -> the region-open event flag set when that lock is received. Keys MUST be exactly '<Region> Lock' matching the client's COARSE_LOCK_ITEMS names. |
| `options` | OPTIONS_DICT | yes | greenfield | core._options_echo | er-logic/options.rs parse_bool_option et al. | runtime option echo sub-dict; every client-read option lives here (features' top-level copies are legacy duplicates the client ignores). |
| `options.death_link` | BOOL_OR_INT | yes | greenfield | core._options_echo | er-logic/options.rs parse_death_link | shared deaths across the multiworld (world.options.death_link). |
| `options.enable_dlc` | BOOL_OR_INT | yes | greenfield | core._options_echo | er-logic/options.rs parse_dlc | RESOLVED DLC bool (dlc_only implies on); gates DLC map-reveal flags. |
| `options.no_weapon_requirements` | BOOL_OR_INT | yes | greenfield | core._options_echo | no_weapon_reqs.rs set_enabled | zero weapon/shield/catalyst + spell stat requirements. |
| `options.completion_scaling` | INT_OR_BOOL | yes | greenfield | core._options_echo | er-logic/scaling.rs:146 parse_bool_option | completion scaling on/off + curve id (nonzero = on; 4 = smoothstep). |
| `options.completion_scaling_floor` | NUMBER | yes | greenfield | core._options_echo | er-logic/scaling.rs floor (client reads f64) | minimum scaling tier as percent of max, applied from the start. |
| `options.global_scadutree_blessing` | INT | yes | greenfield | core._options_echo | scaling.rs scadutree scope | DLC Scadutree blessing scope Choice value (0 off / 1 player_only / 2 scaled). |
| `options.auto_upgrade` | INT | yes | greenfield | core._options_echo (features/upgrades.py) | upgrades.rs set_auto_upgrade / apply_auto_upgrade | auto-upgrade received weapons: 0 = off; nonzero = raise each received weapon to the player's highest held level on its smithing track (raise-only, cap +25 normal / +10 somber). |
| `options.flatten_regular_upgrades` | INT | yes | greenfield | core._options_echo (features/upgrades.py) | upgrades client path | standard-weapon stones/level: 0 = off (vanilla 2/4/6), 1..4 = uniform N/level (tuned ~3). |
| `regionSphereTargets` | SCALAR_INT_MAP |  | greenfield | features/scaling.py (I2; core emits {} transitional) | er-logic/scaling.rs:148 i32_i32_map | {str(i32 region id): i32 target}; flat per-region scaling targets. Keys must parse as i32 (region NAMES are silently dropped by the client -- the 2026-07 dark-scaling bug); ranges (regionSphereTargetRanges) are the live wire. |
| `regionSphereTargetRanges` | TRIPLE_LIST |  | greenfield | features/scaling.py (I2) | er-logic/scaling.rs:150-165 range parse | [[lo,hi,target], ...] play_region/100 sub-id ranges -> scaling target; the live completion-scaling wire (SCALING_WIRE). |
| `completionScalingBasis` | INT |  | greenfield | core._base_slot_data | er-logic/scaling.rs basis parse | scaling basis Choice VALUE (int 1 = sphere); client also tolerates the legacy string form ('sphere'). |
| `areaLockFlags` | TRIPLE_LIST |  | both | (client-derived; folded into regionOpenFlags 2026-07-06) | region.rs derive_area_lock_flags | [lo,hi,open_flag] play_region ranges; locked (kicked) while open_flag is unset. FOLDED 2026-07-06: no longer emitted -- the client derives these from regionOpenFlags + its static REGION_PLAY_IDS geometry (area_locks.py holds the mirror authority + a kept-region coverage assert; test_gf_data.py guards table drift). A legacy seed that still sends a non-empty areaLockFlags is honored by the client as-is. |
| `lockRevealFlags` | LISTVAL_INT_MAP |  | both | (unemitted today; client path LIVE) | region.rs:121 str_to_u32vec | '<Region> Lock' -> map-reveal/enforcement flags set on lock receipt. The client consumer is LIVE (region.rs:121); greenfield does not emit it yet. |
| `regionGraces` | LISTVAL_INT_MAP |  | both | features/graces.py | region.rs:122 str_to_u32vec | '<Region> Lock' -> grace warp flags lit on lock receipt (bundle: all of the region's graces). |
| `startRegion` | STR | yes | both | features/start_grace.py | core.rs:410 as_str | name of the always-kept start region (diagnostic + start anchor). |
| `startGraces` | INT_LIST |  | both | features/start_grace.py | startgrants.rs:58 arr_u32 | grace flags lit at spawn so the first warp is possible (front-door of start region). |
| `startItems` | INT_LIST |  | both | features/start_items.py | startgrants.rs:57 arr_i32 | FullIDs granted once at game start (Torch, Spectral Steed Whistle, ...). |
| `reveal_all_maps` | BOOL |  | both | features/start_grace.py | startgrants.rs as_bool | reveal the whole world map + underground view (client owns the RE'd flag set). |
| `bigTicketLocations` | INT_LIST |  | greenfield | features/big_ticket_locations.py | core.rs self.big_ticket (fallback tracker_regions::big_ticket_set) | AP location ids that are big-ticket THIS seed = is_big_ticket(tags, big_ticket_locations); Enia (EniaShop) always excluded. Client stars/locks these; absent -> client falls back to the static default table. |
| `goalLocations` | INT_LIST | yes | both | features/goal_locations.py | goal.rs parse | AP location ids whose completion == victory; client sends Goal when all are done. |
| `checkItemFlags` | LISTVAL_INT_MAP |  | both | features/check_item_flags.py | detour.rs CHECK_ITEM_FLAGS<u32,Vec<u32>> | vanilla FullID (str) -> the check flags it belongs to; suppresses the vanilla bag-add. |
| `shopRowFlags` | SCALAR_INT_MAP |  | both | features/shops.py | core.rs:359 i64_to_u32_map | ShopLineupParam row id -> eventFlag_forStock written for shop checks. |
| `shopPreviewGoods` | SCALAR_INT_MAP |  | both | features/shops.py | core.rs:353 i64_map | AP location id -> preview goods id shown in the shop slot. |
| `stoneswordVendorRow` | INT |  | greenfield | features/minibaker.py | minibaker.rs configure/run | MINI-BAKER: reserved ShopLineupParam row id the client repurposes into an infinite, always-in-stock Stonesword Key vendor (equipId 8000, sellQuantity -1) so imp-statue checks are never missable. 0/absent = off (row left vanilla). Reserved row is excluded from shop checks in gen_data. See memory er-minibaker-shoplineup. |
| `dungeonSweepFlags` | LISTVAL_INT_MAP |  | both | features/boss_sweeps (P3b client patch) | region.rs:104 as_object | dungeon trigger flag (str) -> the member AP location ids auto-registered on clear. |
| `dungeonSweeps` | ANY |  | both | features/boss_locks.py ({} today; location-keyed variant) | region.rs | location-keyed dungeon sweep spec (needs boss-reward-location join); greenfield emits {} until wired -- flag-keyed dungeonSweepFlags is the live path. |
| `sweepLockGates` | STR_MAP |  | both | features/boss_locks.py ({} today) | region.rs sweep gates | {str(i64 sweep trigger flag): '<Region> Lock'} -- gates a dungeon sweep behind holding the named lock; live client consumer. |
| `progressiveGrants` | NESTED_GRANTS |  | both | features/progressive.py | progressive.rs | item name -> ordered [{goods, flags}] granted on each successive receipt. |
| `death_link` | BOOL_OR_INT |  | both | features/deathlink.py (legacy duplicate of options.death_link) | er-logic/options.rs parse_death_link (reads options.death_link) | legacy top-level copy; the client reads options.death_link -- kept for back-compat. |
| `no_weapon_requirements` | BOOL_OR_INT |  | both | features/weapon_reqs.py (legacy duplicate of options.no_weapon_requirements) | core.rs:304 no_weapon_reqs::set_enabled (reads options path) | legacy top-level copy; the client reads options.no_weapon_requirements. |
| `enable_dlc` | BOOL_OR_INT |  | both | core._options_echo (options.enable_dlc; top-level unemitted) | er-logic/options.rs parse_dlc (reads options.enable_dlc) | DLC / Land of Shadow regions active; the LIVE copy is options.enable_dlc. |
| `completion_scaling` | INT_OR_BOOL |  | greenfield | features/scaling.py (legacy duplicate of options.completion_scaling) | er-logic/scaling.rs:146 (reads options.completion_scaling) | legacy top-level copy of the scaling toggle/curve id (4 = smoothstep). |
| `completion_scaling_floor` | NUMBER |  | greenfield | features/scaling.py (legacy duplicate of options.completion_scaling_floor) | (client reads options.completion_scaling_floor) | legacy top-level copy of the scaling floor percent. |
| `global_scadutree_blessing` | INT |  | greenfield | features/scaling.py (legacy duplicate of options.global_scadutree_blessing) | (client reads options.global_scadutree_blessing) | legacy top-level copy of the Scadutree blessing scope. |
| `versions` | STR |  | both | (optional; unemitted today) | core.rs version gate | apworld semver for the client version gate; emission optional. |
| `world_logic` | STR |  | greenfield | core._base_slot_data | (diagnostic -- no client read) | logic profile tag, e.g. 'region_lock'. |
| `region_count` | ANY |  | greenfield | core._base_slot_data | (diagnostic -- no client read) | len(kept) -- how many regions are in play this seed. |
| `ending_condition` | ANY |  | greenfield | core._base_slot_data | (diagnostic -- no client read) | resolved goal tag: 'region_locks' | 'great_runes'. |
| `great_runes_required` | ANY |  | greenfield | core._base_slot_data | (diagnostic -- no client read) | EFFECTIVE (clamped) Great Rune requirement for the great_runes ending. |
| `great_rune_items` | ANY |  | greenfield | core._base_slot_data | (diagnostic -- no client read) | required Great Rune item names this seed. |
| `bossLocations` | ANY |  | greenfield | features/boss_locks.py | (diagnostic -- no client read) | {region: [boss AP location ids]} for kept regions. |
| `bossLockItems` | ANY |  | greenfield | features/boss_locks.py | er-logic boss_felled / region.rs | {str(boss_flag): {name:'Felled: <Boss>', region, boss_ap_id [, gate:'Boss Key: <Boss>', display_key:<vanilla key name>]}}: kept BASE-game bosses always; DLC bosses added when boss_keys is ON. Client mints the 'Felled:' trophy on boss-defeat (mode A); the mode-B 'gate' (defer own check until key) and 'display_key' (legible vanilla lock name) ride the same entry when boss_keys is ON. |
| `filler_foreign_localized` | ANY |  | greenfield | features/filler_foreign.py | (diagnostic -- no client read) | count of distinct filler names forced local this seed. |
| `pool_builder` | ANY |  | greenfield | features/pool_builder.py | (diagnostic -- no client read) | whether pool curation was enabled this seed. |
| `pool_builder_juice_added` | ANY |  | greenfield | features/pool_builder.py | (diagnostic -- no client read) | resolved juice budget added by the pool builder. |
| `pool_builder_intensity_floor` | ANY |  | greenfield | features/pool_builder.py | (diagnostic -- no client read) | resolved juice rarity floor (1..3). |
| `pool_builder_juice_candidates` | ANY |  | greenfield | features/pool_builder.py | (diagnostic -- no client read) | size of the juice candidate set at this intensity. |
| `pool_builder_juice_pct` | ANY |  | greenfield | features/pool_builder.py | (diagnostic -- no client read) | resolved share (0..100) of the Rune tail replaced with juice. |
| `locationIdsToKeys` | ANY | yes | bedrock | (bedrock apworld) | key_resolver.rs | matt slot key token per location; client resolves token1 -> flag (bedrock path). |
| `itemCounts` | ANY | yes | both | core._base_slot_data (greenfield) / bedrock apworld | core.rs receive.rs itemCounts | per-item quantity map {str(ap_item_id): qty}; client grants full_id x qty. Greenfield emits stack sizes for throwables (x10) and finished pots (x4) (features/filler_curation). |
| `naturalKeyTriggers` | ANY | yes | bedrock | (bedrock apworld) | key_resolver.rs / region.rs | bedrock natural key triggers. |
| `lockGrantItems` | ANY | yes | bedrock | (bedrock apworld) | region.rs | items granted on a region lock receipt (bedrock). |
| `randomStartDoneFlag` | ANY | yes | bedrock | (bedrock apworld) | random start client path | bedrock random-start: flag set when the start warp completed. |
| `randomStartWarpFlag` | ANY | yes | bedrock | (bedrock apworld) | random start client path | bedrock random-start: flag that triggers the start warp. |
| `randomStartAreaId` | ANY | yes | bedrock | (bedrock apworld) | random start client path | bedrock random-start: destination area id. |
| `randomStartGraceId` | ANY | yes | bedrock | (bedrock apworld) | random start client path | bedrock random-start: destination grace id. |
| `fogWalls` | ANY | yes | bedrock | (bedrock apworld) | fog wall client path | bedrock fog-wall spec. |
| `fogWallDebug` | ANY | yes | bedrock | (bedrock apworld) | fog wall client path | bedrock fog-wall debug toggle. |

## Shapes

| shape | client parser |
|-------|---------------|
| SCALAR_INT_MAP | `i64_to_u32_map / i64_map / str_to_u32` |
| LISTVAL_INT_MAP | `str_to_u32vec` |
| STR_MAP | `{key: str} object` |
| TRIPLE_LIST | `parse_triples` |
| INT_LIST | `arr_i32 / arr_u32` |
| BOOL | `as_bool` |
| BOOL_OR_INT | `parse_death_link / parse_dlc (0/1)` |
| INT_OR_BOOL | `parse_bool_option (nonzero = on)` |
| INT | `as_i64` |
| NUMBER | `as_f64` |
| STR | `as_str` |
| NESTED_GRANTS | `progressive.rs custom` |
| OPTIONS_DICT | `options::parse_*_option sub-dict` |
| ANY | `(diagnostic / foreign profile; unvalidated)` |
