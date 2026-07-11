# Elden Ring Archipelago — client `slot_data` contract

**What this is.** The runtime client (`eldenring-archipelago`) drives the game entirely from the
`slot_data` an apworld returns from `fill_slot_data()`. This document is the exact set of keys the
client reads, their JSON shapes, whether they're required, and what each does. If your `.apworld`
emits these keys with these shapes, this client will detect location checks, grant received items,
gate/warp regions, light graces, reveal maps, run shops, and send Goal — no client changes needed.

It is **auto-generated from the client's own contract definition** (`contract.py` / `contract_gen.rs`),
so it always matches what the client actually validates. Two companion files ship with this spec:

- `contract.json` — the same contract, machine-readable (validate your slot_data against it in CI).
- `contract_gen.rs` — the client's actual validator (`fn validate(sd) -> Vec<String>`); the client
  runs it on connect and logs any mismatch as `contract: SHAPE '<key>' expected <Shape>`.

## Conventions

- **FullID** (item id space): `category_nibble | param_id`. `WEAPON = 0x00000000`, `PROTECTOR/armor
  = 0x10000000`, `ACCESSORY/talisman = 0x20000000`, `GOODS = 0x40000000`, `GEM/ash = 0x80000000`.
  e.g. Torch (weapon 24000000) = `24000000`; Spectral Steed Whistle (goods 130) = `1073741954`.
- **Event flags** are ER game event flags (group-allocated; invented ids no-op). Map/grace/region
  flags are the real vanilla flags.
- **Detection model** is `own_world`: on a check pickup the client suppresses the vanilla item,
  reports the location, and grants back whatever the multiworld placed there via `apIdsToItemIds`.

## Shapes

| shape | JSON form | client parser | example |
|-------|-----------|---------------|---------|
| `SCALAR_INT_MAP` | object, string key -> **integer** value (NOT a list) | `i64_to_u32_map / i64_map / str_to_u32` | `{"7770029": 60290}` |
| `LISTVAL_INT_MAP` | object, string key -> **array of integers** | `str_to_u32vec` | `{"Limgrave Lock": [73000, 73003, 73005]}` |
| `TRIPLE_LIST` | array of `[int, int, int]` triples | `parse_triples` | `[[61000, 61000, 73100], [10000, 10000, 200]]` |
| `INT_LIST` | array of integers | `arr_i32 / arr_u32` | `[24000000, 1073741954]` |
| `BOOL` | boolean | `as_bool` | `true` |
| `BOOL_OR_INT` | boolean, or integer 0/1 (tolerant) | `parse_death_link / parse_dlc` | `true   (or 1)` |
| `STR` | string | `as_str` | `"Limgrave"` |
| `NESTED_GRANTS` | object, name -> array of `{"goods": int, "flags": [int]}` | `progressive.rs custom` | `{"Flask of Crimson Tears": [{"goods": 1073742018, "flags": []}]}` |

> The single most common integration bug is emitting a `SCALAR_INT_MAP` key (e.g. `locationFlags`)
> with **list** values `{"id": [flag]}` instead of scalar `{"id": flag}`. The client parses it to
> empty and silently detects nothing. The validator catches exactly this.

## Core keys (read by the client in every profile)

| key | shape | | profile | client reads in | meaning |
|-----|-------|-----|---------|-----------------|---------|
| `apIdsToItemIds` | `SCALAR_INT_MAP` | **required** | both | core.rs:309 i64_map | AP item id (str) -> ER FullID granted on receipt. |
| `locationFlags` | `SCALAR_INT_MAP` | **required** | both | core.rs:330 i64_to_u32_map | AP location id (str) -> its ER acquisition event flag; the flag-poll detection table. |
| `regionOpenFlags` | `SCALAR_INT_MAP` | **required** | both | region.rs:120 str_to_u32 | '<Region> Lock' -> the region-open event flag set when that lock is received. |
| `areaLockFlags` | `TRIPLE_LIST` | **required** | both | region.rs:103 parse_triples | [lo,hi,open_flag] play_region ranges; locked (kicked) while open_flag is unset. |
| `lockRevealFlags` | `LISTVAL_INT_MAP` | optional | both | region.rs:121 str_to_u32vec | '<Region> Lock' -> map-reveal/enforcement flags set on lock receipt. |
| `regionGraces` | `LISTVAL_INT_MAP` | optional | both | region.rs:122 str_to_u32vec | '<Region> Lock' -> grace warp flags lit on lock receipt (bundle=all, freebie=front door). |
| `startRegion` | `STR` | **required** | both | core.rs:410 as_str | name of the always-kept start region (diagnostic + start anchor). |
| `startGraces` | `INT_LIST` | optional | both | startgrants.rs:58 arr_u32 | grace flags lit at spawn so the first warp is possible (front-door of start region). |
| `startItems` | `INT_LIST` | optional | both | startgrants.rs:57 arr_i32 | FullIDs granted once at game start (Torch, Spectral Steed Whistle, ...). |
| `reveal_all_maps` | `BOOL` | optional | both | startgrants.rs as_bool | reveal the whole world map + underground view (client owns the RE'd flag set). |
| `goalLocations` | `INT_LIST` | **required** | both | goal.rs parse | AP location ids whose completion == victory; client sends Goal when all are done. |
| `checkItemFlags` | `LISTVAL_INT_MAP` | optional | both | detour.rs CHECK_ITEM_FLAGS<u32,Vec<u32>> | vanilla FullID (str) -> the check flags it belongs to; suppresses the vanilla bag-add. |
| `shopRowFlags` | `SCALAR_INT_MAP` | optional | both | core.rs:359 i64_to_u32_map | ShopLineupParam row id -> eventFlag_forStock written for shop checks. |
| `shopPreviewGoods` | `SCALAR_INT_MAP` | optional | both | core.rs:353 i64_map | AP location id -> preview goods id shown in the shop slot. |
| `dungeonSweepFlags` | `LISTVAL_INT_MAP` | optional | both | region.rs:104 as_object | dungeon trigger flag (str) -> the member AP location ids auto-registered on clear. |
| `progressiveGrants` | `NESTED_GRANTS` | optional | both | progressive.rs | item name -> ordered [{goods, flags}] granted on each successive receipt. |
| `death_link` | `BOOL_OR_INT` | optional | both | options::parse_death_link | shared deaths across the multiworld. |
| `enable_dlc` | `BOOL_OR_INT` | optional | both | options::parse_dlc | DLC / Land of Shadow regions active; gates the DLC map-reveal flags. |

## Alternate / profile-specific keys

The client supports two ways to wire **location detection**: emit event flags directly
(`locationFlags`, the greenfield path) **or** emit matt-style location keys (`locationIdsToKeys`,
the bedrock path — the client resolves `token1` -> flag). Provide one. Keys below are read by the
client but are specific to one profile:

| key | shape | | profile | client reads in | meaning |
|-----|-------|-----|---------|-----------------|---------|
| `regionSphereTargets` | `ANY` | optional | greenfield | (informational) | region -> sphere target [0..1] for completion scaling; not enforced by the client. |
| `graceItems` | `SCALAR_INT_MAP` | optional | greenfield | region.rs:123 str_to_u32 | scatter grace item name -> the single grace flag it lights when received. |
| `world_logic` | `STR` | optional | greenfield | (informational) | logic profile tag, e.g. 'region_lock'. |
| `locationIdsToKeys` | `ANY` | optional | bedrock | key_resolver.rs | matt slot key token per location; client resolves token1 -> flag (bedrock path). |
| `naturalKeyTriggers` | `ANY` | optional | bedrock | key_resolver.rs / region.rs | bedrock natural key triggers. |
| `lockGrantItems` | `ANY` | optional | bedrock | region.rs | items granted on a region lock receipt (bedrock). |
| `dungeonSweeps` | `ANY` | optional | bedrock | region.rs | bedrock dungeon sweep spec (greenfield uses dungeonSweepFlags). |
| `itemCounts` | `ANY` | optional | bedrock | core.rs | per-item quantity map. |

## Minimal viable slot_data

A region-lock seed needs at least: `apIdsToItemIds`, `locationFlags` (or the key path),
`regionOpenFlags`, `areaLockFlags`, `startRegion`, `goalLocations`. Everything else is optional and
enables a feature (graces, map reveal, shops, sweeps, deathlink, progressives).

```jsonc
{
  "apIdsToItemIds":  {"7770001": 1073750026},         // AP item id -> ER FullID granted on receipt
  "locationFlags":   {"7770001": 60290},              // AP location id -> its ER acquisition flag
  "regionOpenFlags": {"Caelid Lock": 73202},          // lock item -> region-open flag set on receipt
  "areaLockFlags":   [[62000, 62002, 73202]],         // [lo,hi,open_flag] play_region ranges, kicked while unset
  "startRegion":     "Limgrave",
  "goalLocations":   [7770875, 7770876, 7770885]      // all-done => client sends Goal
}
```

## Questions

The contract lives in one file on the client side; if you need a key the client doesn't yet read,
or a shape adjusted, that's a one-line change plus a regen of these three artifacts. Happy to add
`bedrock`-profile keys to the shared contract so both apworlds validate against the same source.
