# SPEC — Map tracker (PopTracker pack revival)

Status: PLAN 2026-07-17 (Alaric: "let's do it right, and make a proper map tracker"). Supersedes the
scattered `docs/specs/SPEC-poptracker-*.md` / `HANDOFF-poptracker-*.md` set (recovered from history for
reference). Owner: Alaric.

## The one idea

**One coordinate datamine feeds everything.** The old PopTracker pack and the old grace-distance tool
both drank from the same well — the C# randomizer's `ap_location_coords_*.txt` dump — and that well was
capped when the C# randomizer was purged. Re-source those coordinates once, from the witchy'd MSBs, and
the same output drives (a) the location descriptions (`desc_sources` layer 4, nearest grace) and (b) the
map tracker's pins. Do the datamine right and the map "just works," because:

**The map is not a licensed image.** `build_map.py` draws a *stylized hull* from the coordinate facts
(`_hull` → `_densify` → `_chaikin`), authored directly in game `gx/gz` space. Original art, zero game
assets, and the world→image transform is exact *by construction*, so region pins are the centroids of
their checks' transformed coordinates — **derived, never hand-placed.** The licensing gate that
SPEC-poptracker-map.md called the blocker is dissolved. Everything hinges on coordinates.

## What already exists (recovered from `7e8255a~1` into `poptracker/`)

A near-complete pack, deleted in the v0.1 cleanup only because its coordinates went stale:
- **Map generators** `tools/build_map.py` (overworld hull), `tools/dlc_map.py` (Land of Shadow),
  `tools/gen_poptracker.py` (pack generator).
- **Art/coord facts** `maps/lands_between_map.svg`, `land_of_shadow_map.svg`, `map_calibration.json`,
  `region_centroids.json`, `region_pins.json` (committed pins so the pack builds with no dump present).
- **Logic** `scripts/region_graph.lua` + `logic.lua` (BFS reachability), `autotracking.lua`,
  `loc_map.lua` / `loc_dlc.lua`, `init.lua`, `manifest.json`, `layouts/*.json`, `items/items.json`.
- **Modes** `dlc_only` auto-clear + a Land-of-Shadow map variant; `location_pool` (trim/lean) awareness
  designed in SPEC-poptracker-trim.md.

## What is stale (the port — old apworld model → greenfield)

The pack was generated against the pre-greenfield apworld (`Archipelago/worlds/eldenring/{locations,items,__init__}.py`).
Greenfield replaced that data model, so the generator's *readers* are what's stale, not the pack idea:

| Piece | Old source | Greenfield source | Work |
|-------|-----------|-------------------|------|
| coordinates | C# `ap_location_coords_*.txt` | `tools/datamine_item_grace_coords.py` (witchy MSBs) | re-source; emit global `gx/gz` |
| location → region | `locations.py` `location_tables` `key=` | `eldenring/data.py` `LOCATIONS` (region → (name, apid, flag)) | port `key_to_region` |
| item table / ap codes | `items.py` `item_table` | `eldenring/item_ids.py` + `data.py` | port `items_from_ast` / runtime import |
| region graph / gates | `__init__.py` `create_connection` / `_add_entrance_rule` | `region_groups` / `region_spine` / boss-lock model | regenerate `region_graph.lua` + `logic.lua` |
| slot_data keys | `world_logic`, `enable_dlc`, `location_pool`, `dlc_only` | current `contract.py` `fill_slot_data` | verify keys + back-compat defaults |

## Coordinate contract (the foundation — P0)

`datamine_item_grace_coords.py` must emit, per check and per grace, the schema `build_map.py` +
`build_nearest_grace.py` consume:

```
type   key(flag)   tileX  tileZ   gx    gy    gz    mapName
```

- Item/grace **map-local** XYZ come from the MSB Part/Enemy + Event/Treasure parts and the positioned
  `grace_flags.tsv` (already proven in `datamine_arena_graces.py`).
- **Global** `gx/gy/gz` = replicate the C# `EldenCoordinator.ToGlobalCoords`: overworld `m60_XX_YY`
  tiles sit on a 256 m grid (`gx = XX*256 + localX`, etc.); the `m61` DLC tiles use a private tile band
  (`DlcTileBand=100`, above base `TILE_MAX=55`) — the fix noted in `[[er-poptracker-dlc-only]]`.
  Legacy/underground/interior maps are separate coordinate spaces → own sub-maps or (DLC interiors) no
  pin yet, checks still track.
- Validate the transform against the committed `map_calibration.json` + a handful of known graces
  before trusting a full run.

## Phasing (each phase is a reviewable checkpoint)

- **P0 — Coordinates.** Redesign `datamine_item_grace_coords.py` to emit the dump above (global coords +
  tileX/Z + mapName). Unit-test the tile transform on synthetic + a small staged MSB sample. This alone
  finishes the *descriptions* (nearest grace) too.
- **P1 — Map from coords.** Point `build_map.py`/`dlc_map.py` at the new dump; port `key_to_region` to
  `data.py`; regenerate the hull, `region_pins.json`, `region_centroids.json`. Split committed **source**
  (SVG, calibration, pins, Lua glue) from **generated** output (PNG, `maps.json`, `loc_map.lua`) — a
  `.gitignore` + a `build_poptracker.ps1` entry — so the pack stops being a "formless blob."
- **P2 — Logic / reachability.** Regenerate `region_graph.lua` + `logic.lua` from the greenfield region
  model (`region_groups`/`region_spine`/boss locks) instead of the old `create_connection` AST.
- **P3 — Autotracking / slot_data.** Verify `autotracking.lua` against the current AP location/item ids
  and `contract.py` slot_data (`world_logic`, `enable_dlc`, `location_pool`, `dlc_only`) with
  missing-key back-compat; version-lockstep `manifest.package_version` to the apworld `versions`.
- **P4 — Windows PopTracker load-test.** Load all variants on a real slot; watch `[ER-AP]` logs. (Only
  Windows/PopTracker can do this; the generators + logic are host-testable here.)

## Gates & known limits

- **Licensing:** resolved — stylized hull is original art.
- **DLC interiors** (dungeons inside Land of Shadow): no dungeon coordinate offsets, so they don't pin;
  their checks still track/auto-clear. Documented limit, not a bug.
- **Generated data can lag** the apworld: keep the version-lockstep gate (SPEC-poptracker-trim §Contract).
- **Windows-only** steps: the datamine (raw MSBs) and the PopTracker load-test. Everything else — the
  generators, the hull math, the Lua logic — is authored and host-tested in-repo.
