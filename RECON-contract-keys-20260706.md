# RECON R1 — slot_data key reconciliation: client (consumer) vs greenfield (producer)

Date: 2026-07-06 · READ-ONLY recon per FABLE-FIX-PARALLELIZATION-PLAN-20260706.md Wave 1 R1.
Client paths relative to `from-software-archipelago-clients/crates/`; greenfield paths relative to
`greenfield/eldenring_gf/`. Nesting: **TOP** = `sd["<key>"]`, **OPTIONS** = `sd["options"]["<key>"]`.

Non-slot_data reads excluded on inspection: `er-logic/src/save_state.rs` (save-file JSON),
`eldenring-archipelago/src/flagpoll.rs:67,74` `location_flags`/`sweep_flags` (apconfig table FILE,
merged after slot_data — not slot_data keys).

---

## Table 1 — CLIENT READS (every slot_data access)

| # | Key | Read at (file:line) | Nesting | Expected shape |
|---|-----|---------------------|---------|----------------|
| 1 | `death_link` | er-logic/options.rs:30 (`parse_death_link`) ← core.rs:303 | **OPTIONS** | bool OR int (nonzero=true) |
| 2 | `enable_dlc` | er-logic/options.rs:25 (`parse_dlc`) ← startgrants.rs:67; PLUS top-level fallback startgrants.rs:67 `.as_bool()` (bool ONLY, int fails) | **OPTIONS** (+TOP bool fallback) | bool-or-int (options) / strict bool (top) |
| 3 | `no_weapon_requirements` | core.rs:304-307 via `parse_bool_option` | **OPTIONS** | bool-or-int |
| 4 | `completion_scaling` | er-logic/scaling.rs:145 + eldenring-archipelago/scaling.rs:33 via `parse_bool_option` | **OPTIONS** | bool-or-int (nonzero=on) |
| 5 | `completion_scaling_floor` | er-logic/scaling.rs:182 `pointer("/options/completion_scaling_floor")` | **OPTIONS** | number as f64 (multiplier, e.g. 1.5) |
| 6 | `auto_upgrade` | core.rs:309 `pointer("/options/auto_upgrade")` | **OPTIONS** | int (i64) |
| 7 | `global_scadutree_blessing` | core.rs:312 `pointer("/options/global_scadutree_blessing")` | **OPTIONS** | int (i64) |
| 8 | `flatten_regular_upgrades` | core.rs:315 `pointer("/options/flatten_regular_upgrades")` | **OPTIONS** | int (nonzero=true) |
| 9 | `apIdsToItemIds` | core.rs:317 `i64_map` | TOP | `{str(i64): i64}` |
| 10 | `itemCounts` | core.rs:318 `i64_map` | TOP | `{str(i64): i64}` (bedrock) |
| 11 | `locationFlags` | core.rs:338 `i64_to_u32_map` (fallback when locationIdsToKeys absent/empty) | TOP | `{str(i64 ap_id): int flag}` scalar values |
| 12 | `locationIdsToKeys` | key_resolver.rs:45,102 | TOP | `{str(loc): "a,b:flag:shopRows:"}` (bedrock/matt) |
| 13 | `shopPreviewGoods` | core.rs:361 `i64_map` | TOP | `{str(loc): int goods_id}` |
| 14 | `shopRowFlags` | core.rs:367 `i64_to_u32_map` | TOP | `{str(row_id): int flag}` |
| 15 | `checkItemFlags` | core.rs:380-395 | TOP | `{str(u32 FullID): [u32 flag,...]}` |
| 16 | `versions` | er-logic/version.rs:15 + core.rs:406 | TOP | str semver range (absent = gate inert) |
| 17 | `startRegion` | core.rs:418 `.as_str()` | TOP | str |
| 18 | `dungeonSweeps` | flagpoll.rs:89 `parse_dungeon_sweeps` | TOP | `{str(i64 trigger loc): [i64 member locs]}` (bedrock) |
| 19 | `dungeonSweepFlags` | flagpoll.rs:104 `parse_sweep_flags` | TOP | `{str(u32 boss flag): [i64 member locs]}` |
| 20 | `sweepLockGates` | flagpoll.rs:119 `parse_sweep_lock_gates` | TOP | `{str(i64 trigger loc): str lock item name}` |
| 21 | `fogWalls` | fogwall.rs:157 | TOP | `[{openFlag:u64, asset:str, label:str, blockId|block:int, x,y,z:f64}]` |
| 22 | `fogWallDebug` | fogwall.rs:164 `.as_bool()` | TOP | strict bool |
| 23 | `goalLocations` | goal.rs:42 | TOP | `[i64 loc ids]` |
| 24 | `areaLockFlags` | region.rs:103 `parse_triples` | TOP | `[[lo,hi,open_flag] i32 triples]` |
| 25 | `randomStartDoneFlag` | region.rs:105 `.as_u64()` | TOP | u32 (0/absent = inert) |
| 26 | `randomStartWarpFlag` | region.rs:109 | TOP | u32 |
| 27 | `randomStartAreaId` | region.rs:113 `.as_i64()` | TOP | i32 |
| 28 | `randomStartGraceId` | region.rs:117 | TOP | u32 |
| 29 | `regionOpenFlags` | region.rs:120 `str_to_u32` | TOP | `{"<Region> Lock": u32 flag}` |
| 30 | `lockRevealFlags` | region.rs:121 `str_to_u32vec` | TOP | `{"<Region> Lock": [u32]}` |
| 31 | `regionGraces` | region.rs:122 `str_to_u32vec` | TOP | `{"<Region> Lock": [u32]}` |
| 32 | `graceItems` | region.rs:123 `str_to_u32` | TOP | `{"Grace: ..." name: u32 flag}` |
| 33 | `naturalKeyTriggers` | region.rs:124, parse_natural_keys region.rs:174-206 | TOP | `{name: {anyOf: [{items:[str], flags:[u32]}]}}` (bedrock) |
| 34 | `lockGrantItems` | region.rs:125 `str_to_i32vec` | TOP | `{lock name: [i32 FullIDs]}` (bedrock) |
| 35 | `startItems` | startgrants.rs:57 `arr_i32` | TOP | `[i32 FullIDs]` |
| 36 | `startGraces` | startgrants.rs:58 `arr_u32` | TOP | `[u32 flags]` |
| 37 | `reveal_all_maps` | startgrants.rs:60 `.as_bool()` | TOP | **strict bool** (int would read as false) |
| 38 | `regionSphereTargets` | er-logic/scaling.rs:148 `i32_i32_map` | TOP | `{str(i32 play_region/100): i32 target}` — non-numeric keys/values SKIPPED |
| 39 | `regionSphereTargetRanges` | er-logic/scaling.rs:153-165 | TOP | `[[lo,hi,target] i64 triples]` in play_region/100 space (LIVE scaling path) |
| 40 | `completionScalingBasis` | er-logic/scaling.rs:177 | TOP | `"sphere"` or int `1` → Sphere; anything else → Geographic |
| 41 | `progressiveGrants` | er-logic/progressive.rs:185-215 | TOP | `{item name: [{goodsList:[u32]|goods:u32, flags:[u32]}]}` |

Note: `world_logic` is declared in contract_gen.rs:46 but NO client code reads it (declaration only).

---

## Table 2 — GREENFIELD EMITS

| # | Key | Producer (file:line) | Nesting | Shape emitted |
|---|-----|----------------------|---------|---------------|
| 1 | `world_logic` | core.py:357 | TOP | str "region_lock" |
| 2 | `locationFlags` | core.py:358 | TOP | `{str(ap_id): int flag}` scalar |
| 3 | `apIdsToItemIds` | core.py:359 | TOP | `{str: int}` |
| 4 | `regionOpenFlags` | core.py:360 | TOP | `{"<R> Lock": int}` |
| 5 | `region_count` | core.py:361 | TOP | int |
| 6 | `completionScalingBasis` | core.py:362 | TOP | int 1 |
| 7 | `regionSphereTargets` | core.py:363 | TOP | `{region NAME str: float 0..1}` |
| 8 | `ending_condition` | core.py:367 | TOP | str |
| 9 | `great_runes_required` | core.py:368 | TOP | int |
| 10 | `great_rune_items` | core.py:369 | TOP | [str] |
| 11 | `areaLockFlags` | features/area_locks.py:89 | TOP | `[[pid,pid,flag]]` |
| 12 | `bossLocations` | features/boss_locks.py:59 | TOP | `{region: [ap_ids]}` |
| 13 | `dungeonSweepFlags` | features/boss_locks.py:64 (only if dungeon_sweep!=0) | TOP | `{str(flag): [ap_ids]}` |
| 14 | `dungeonSweeps` | features/boss_locks.py:66 (only if dungeon_sweep!=0) | TOP | `{}` always empty |
| 15 | `sweepLockGates` | features/boss_locks.py:67 (only if dungeon_sweep!=0; bare string literal) | TOP | `{}` always empty |
| 16 | `checkItemFlags` | features/check_item_flags.py:64 | TOP | `{str(FullID): [flags]}` |
| 17 | `death_link` | features/deathlink.py:18 | **TOP** | bool |
| 18 | `filler_foreign_localized` | features/filler_foreign.py:123 | TOP | int (diag) |
| 19 | `goalLocations` | features/goal_locations.py:90 | TOP | [int] |
| 20 | `regionGraces` | features/grace_rando.py:64 | TOP | `{"<R> Lock": [flags]}` |
| 21 | `graceItems` | features/grace_rando.py:64 | TOP | `{name: flag}` |
| 22 | `pool_builder` | features/pool_builder.py:194-198 | TOP | bool (diag) |
| 23 | `pool_builder_juice_added` | pool_builder.py:194-198 | TOP | int (diag) |
| 24 | `pool_builder_intensity_floor` | pool_builder.py:194-198 | TOP | int (diag) |
| 25 | `pool_builder_juice_candidates` | pool_builder.py:194-198 | TOP | int (diag) |
| 26 | `progressiveGrants` | features/progressive.py:120 | TOP | `{name: [{goods:int, flags:[]}]}` |
| 27 | `completion_scaling` | features/scaling.py:40 | **TOP** | int 4 (curve id) |
| 28 | `completion_scaling_floor` | features/scaling.py:41 | **TOP** | int |
| 29 | `global_scadutree_blessing` | features/scaling.py:42 | **TOP** | int |
| 30 | `shopRowFlags` | features/shops.py:77 | TOP | `{int row_id: flag}` (JSON-serializes to str keys) |
| 31 | `shopPreviewGoods` | features/shops.py:77 | TOP | `{ap_id: goods}` |
| 32 | `startRegion` | features/start_grace.py:61-65 | TOP | str (HUB) |
| 33 | `startGraces` | features/start_grace.py:61-65 | TOP | [int flags] |
| 34 | `reveal_all_maps` | features/start_grace.py:61-65 | TOP | bool (real bool — matches strict as_bool) |
| 35 | `startItems` | features/start_items.py:60 | TOP | [int FullIDs] |
| 36 | `no_weapon_requirements` | features/weapon_reqs.py:26 | **TOP** | bool |

Greenfield emits **NO `"options"` sub-dict anywhere** (grep: zero hits across eldenring_gf).
Merge path: registry.merge_slot_data (registry.py:70-78, collision-checked, accepts ANY key) →
contract.validate_slot_data strict (core.py:373-374; contract.py:246-263 ignores unknown keys).

---

## Table 3 — GAP TABLE (per client-read key)

| Client key (nesting client wants) | Verdict | Detail |
|---|---|---|
| `apIdsToItemIds` TOP | **OK** | core.py:359 |
| `locationFlags` TOP | **OK** | core.py:358 (scalar, post-2026-07-06 fix) |
| `regionOpenFlags` TOP | **OK** | core.py:360 |
| `areaLockFlags` TOP | **OK** | area_locks.py:89 |
| `checkItemFlags` TOP | **OK** | check_item_flags.py:64 |
| `goalLocations` TOP | **OK** | goal_locations.py:90 |
| `regionGraces` TOP | **OK** | grace_rando.py:64 |
| `graceItems` TOP | **OK** | grace_rando.py:64 |
| `progressiveGrants` TOP | **OK** | progressive.py:120 (`goods` single form; client accepts) |
| `shopRowFlags` TOP | **OK** | shops.py:77 |
| `shopPreviewGoods` TOP | **OK** | shops.py:77 |
| `startRegion` TOP | **OK** | start_grace.py |
| `startGraces` TOP | **OK** | start_grace.py |
| `startItems` TOP | **OK** | start_items.py:60 |
| `reveal_all_maps` TOP | **OK** | start_grace.py emits real bool; client as_bool strict — fine |
| `dungeonSweepFlags` TOP | **OK** (conditional) | boss_locks.py:64; absent when dungeon_sweep==0 (client tolerant) |
| `completionScalingBasis` TOP | **OK** | core.py:362 emits int 1; client accepts int 1 → Sphere |
| `sweepLockGates` TOP | **OK-EMPTY** | boss_locks.py:67 always `{}` (ungated by design); bare literal, undeclared in contract.py |
| `dungeonSweeps` TOP | **OK-EMPTY** (bedrock key) | boss_locks.py:66 always `{}`; contract tags producer "(bedrock apworld)" — profile blemish |
| `death_link` **OPTIONS** | **WRONG-NESTING** (F1) | deathlink.py:18 emits TOP; client options.rs:30 reads options/ → DeathLink dark |
| `no_weapon_requirements` **OPTIONS** | **WRONG-NESTING** (F1) | weapon_reqs.py:26 emits TOP; core.rs:304 reads options/ → dark |
| `completion_scaling` **OPTIONS** | **WRONG-NESTING** (F1) | scaling.py:40 emits TOP int 4; scaling.rs:145 reads options/ → scaling never arms |
| `completion_scaling_floor` **OPTIONS** | **WRONG-NESTING** (F1) | scaling.py:41 emits TOP; er-logic/scaling.rs:182 pointer /options/ → floor always 0 |
| `global_scadutree_blessing` **OPTIONS** | **WRONG-NESTING** (F1) | scaling.py:42 emits TOP; core.rs:312 pointer /options/ → blessing always 0 |
| `enable_dlc` OPTIONS (+TOP bool fallback) | **MISSING** (F1-adjacent) | NO greenfield emission at all (contract.py:201 claims producer "core (options echo)" — false); DLC map-reveal (startgrants.rs:66-67) dark |
| `auto_upgrade` OPTIONS | **MISSING** | no producer; core.rs:309 → auto-upgrade always 0/off |
| `flatten_regular_upgrades` OPTIONS | **MISSING** | no producer; core.rs:315 → always off |
| `regionSphereTargetRanges` TOP | **MISSING** (F3) | no producer anywhere in eldenring_gf; the LIVE scaling wire (scaling.rs:150-165); undeclared in contract.py |
| `regionSphereTargets` TOP | **WRONG-SHAPE** | core.py:363 emits {region NAME: float}; client i32_i32_map (scaling.rs:126-136) needs {str(i32): i32} → parses to EMPTY. With ranges also missing, parse_scaling_config returns None (refuse-to-arm) |
| `versions` TOP | **MISSING** (soft) | no producer; version gate deliberately inert when absent (version.rs:13-18) — decide: emit or leave; undeclared in contract.py |
| `itemCounts` TOP | MISSING-BY-DESIGN | bedrock profile (contract.py:220); client defaults fine |
| `locationIdsToKeys` TOP | MISSING-BY-DESIGN | bedrock profile; absence selects the greenfield locationFlags fallback (core.rs:335-343) — this is the intended path switch |
| `naturalKeyTriggers` TOP | MISSING-BY-DESIGN | bedrock (contract.py:211); empty = inert |
| `lockGrantItems` TOP | MISSING-BY-DESIGN | bedrock (contract.py:214); empty = inert |
| `lockRevealFlags` TOP | **MISSING (declared "(future)")** | contract.py:151 declares BOTH-profile w/ producer "(future) per-region map reveal"; no emission; client tolerates absent. Confirm intent — per-region map reveal rides this key |
| `randomStartDoneFlag/WarpFlag/AreaId/GraceId` TOP | MISSING-BY-DESIGN | bedrock random-start residue (region.rs:105-118); 0-defaults inert under greenfield hub start; undeclared in contract.py |
| `fogWalls` / `fogWallDebug` TOP | MISSING-BY-DESIGN (for now) | fogwall.rs:157,164; BUILTIN_WALLS compile-time fallback runs regardless; undeclared in contract.py |

### F1 CONFIRMED — client reads under `sd["options"]`, greenfield emits TOP-LEVEL (5 keys):
1. `death_link` (deathlink.py:18)
2. `no_weapon_requirements` (weapon_reqs.py:26)
3. `completion_scaling` (scaling.py:40)
4. `completion_scaling_floor` (scaling.py:41)
5. `global_scadutree_blessing` (scaling.py:42)

### F1-adjacent — client reads under `sd["options"]`, greenfield emits NOTHING (3 keys):
6. `enable_dlc` (client also checks top-level, strict-bool only)
7. `auto_upgrade`
8. `flatten_regular_upgrades`

All 8 are fixed at once by the I1 central `sd["options"] = {...}` echo.

### DEAD EMISSIONS — greenfield emits, NO client code reads (11 keys):
`world_logic` (core.py:357; contract-declared, client declares but never reads) ·
`region_count` (core.py:361) · `ending_condition` (core.py:367) · `great_runes_required`
(core.py:368) · `great_rune_items` (core.py:369) · `bossLocations` (boss_locks.py:59) ·
`filler_foreign_localized` (filler_foreign.py:123) · `pool_builder`, `pool_builder_juice_added`,
`pool_builder_intensity_floor`, `pool_builder_juice_candidates` (pool_builder.py:194-198).
All diagnostic/informational. Fine to keep, but each needs a contract.py declaration (or an
explicit EXTRA_OK/diag list) once emission becomes contract-gated, or strict-emit will reject them.
Undeclared today: all except `world_logic`; also undeclared: `bossLocations`, `sweepLockGates`,
`region_count`, `completionScalingBasis`, and the whole scaling trio.

---

## DECLARATIONS NEEDED (feeds I1 spine brief)

### A. New nested container — the options echo (fixes F1, all 8 keys at once)
Declare ONE key in contract.py and emit it centrally in core.py `_base_slot_data` (or fill_slot_data):

| Key | Nesting | Shape | Contents |
|---|---|---|---|
| `options` | TOP | dict (needs new OPTIONS_DICT shape checker w/ per-subkey checks) | sub-keys below |

Sub-keys the client reads (all inside `sd["options"]`):
- `death_link` — bool-or-int (echo `world.options.death_link.value`)
- `enable_dlc` — bool-or-int (echo the RESOLVED dlc bool, core.py:190-191 semantics, incl. dlc_only implying on)
- `no_weapon_requirements` — bool-or-int
- `completion_scaling` — bool-or-int (nonzero = on; current emission `4` is fine as truthy curve id)
- `completion_scaling_floor` — number (client reads as_f64; int serializes fine)
- `global_scadutree_blessing` — int
- `auto_upgrade` — int (0 = off; needs an option or a constant 0 until the feature exists gf-side)
- `flatten_regular_upgrades` — int 0/1 (same note)

Decision for I1: keep the existing top-level `death_link`/`no_weapon_requirements`/scaling-trio
emissions as legacy duplicates or remove them. Client reads ONLY the options path for all five, so
removal is safe client-wise; keeping both costs nothing but must not trip the merge collision check
(the echo is core-emitted; features currently emit the top-level twins — if BOTH stay, they live at
different paths so no collision; if features move into the echo, delete the feature emissions).

### B. New/changed top-level scaling keys (coordinates with I2/R2)
| Key | Nesting | Shape | Action |
|---|---|---|---|
| `regionSphereTargetRanges` | TOP | `[[lo, hi, target]]` int triples, play_region/100 sub-id space | DECLARE (new) + PRODUCE in features/scaling.py (per R2 spec); required=False |
| `regionSphereTargets` | TOP | today {name: float} — client-unparseable | Either RESHAPE to `{str(i32): i32}` or demote to explicit diag key (rename e.g. `regionSphereTargetsInfo`) and fix contract.py:144-146 stale "(informational; not enforced)" doc — the client DOES try to parse it (scaling.rs:148) |

### C. Declarations for keys the client reads that contract.py lacks entirely
| Key | Nesting | Shape | Note |
|---|---|---|---|
| `sweepLockGates` | TOP | `{str(i64): str}` | already emitted (boss_locks.py:67, bare literal — switch to contract const); client flagpoll.rs:119 |
| `versions` | TOP | str semver range | declare + decide whether greenfield emits (gate currently inert absent) |
| `completionScalingBasis` | TOP | `"sphere"` \| int 1 \| other=geographic | already emitted core.py:362, undeclared |
| `randomStartDoneFlag` / `randomStartWarpFlag` / `randomStartAreaId` / `randomStartGraceId` | TOP | int | BEDROCK-profile declarations (no gf producer) |
| `fogWalls` | TOP | list of wall objects | BEDROCK/ANY-profile declaration (no gf producer yet) |
| `fogWallDebug` | TOP | bool | same |

### D. Declarations needed only if emission becomes contract-gated (F2 strict-emit)
Diag keys to declare (profile GREENFIELD, shape ANY or exact, doc "diagnostic — no client read"):
`region_count`, `ending_condition`, `great_runes_required`, `great_rune_items`, `bossLocations`,
`filler_foreign_localized`, `pool_builder`, `pool_builder_juice_added`,
`pool_builder_intensity_floor`, `pool_builder_juice_candidates`.

### E. Producer-string corrections in existing contract.py declarations
- `enable_dlc` (contract.py:201): producer says "core (options echo)" — no such echo exists; make it true (A above).
- `lockRevealFlags` (contract.py:151): producer "(future)" — confirm or implement; client path is live (region.rs:121).
- `dungeonSweeps` (contract.py:217): tagged BEDROCK w/ producer "(bedrock apworld)" but boss_locks.py:66 emits it (empty) — either stop emitting or retag.
