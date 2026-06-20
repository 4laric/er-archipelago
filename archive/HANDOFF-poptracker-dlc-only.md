# HANDOFF — PopTracker dlc_only support + Land of Shadow map, 2026-06-16

Full build of dlc_only awareness for the ER-AP PopTracker pack (`poptracker/`), plus a
coordinate-driven Land of Shadow (DLC) map variant. Builds on HANDOFF-poptracker.md (M1/M3a) and
SPEC-poptracker-map.md / SPEC-poptracker-trim.md. All generators run + outputs materialized + lua
syntax-checked + dlc_only behaviour tested end-to-end in this session (embedded Lua via `lupa`).

## What shipped

1. **dlc_only auto-clear (the core ask).** On connect to a dlc_only seed, every NON-DLC check is
   auto-cleared (AvailableChestCount=0) so the ~3752 base-game transit checks don't sit as phantom
   outstanding sections; only the 1154 DLC checks track. Back-compat: missing slot_data key -> 0.
   - Generator emits `scripts/loc_dlc.lua` = `AP_LOC_DLC` (AP loc id -> 1 for DLC-region checks).
   - `scripts/autotracking.lua` (NEW — was referenced by init.lua but never existed) reads
     `slot_data.options` (world_logic, dlc_only, enable_dlc, location_pool) and runs the sweep.
   - Mechanism = auto-clear on connect (Alaric's choice), the same call on_location uses.

2. **logic.lua (NEW — also previously missing).** BFS reachability over the generated
   `region_graph.lua`; defines `can_reach_<slug>` for ALL 161 regions. Key gates always apply;
   region-LOCK gates apply only under region_lock logic (world_logic 0/2). dlc_only reroots the
   graph to `gravesite_plain` (REGION_DLC_ROOT) — you start in the DLC.

3. **Land of Shadow map (M3c).** `tools/dlc_map.py` (NEW) mirrors build_map.py's stylized-hull
   engine for the DLC overworld and emits a `land_of_shadow` map. PNG is rendered directly with PIL
   (no cairosvg needed) so pins align and it loads immediately. New `dlc_only` variant in
   manifest.json + init.lua + `layouts/map_dlc.json`.

4. **Generator plumbing.** `gen_poptracker.py` now calls both map builders, merges the (disjoint)
   pin dicts and the two map defs into one `maps/maps.json`, emits `loc_dlc.lua`, and adds
   `REGION_ALL`/`REGION_IS_DLC`/`REGION_DLC_ROOT` to region_graph.lua. `build_map.build()` now
   returns a 5th value (its map_def); maps.json is written by the generator, not build_map.
   Also created the long-missing `layouts/items_only.json` (list-only variant).

## RE-DUMP — TEED UP (source changes done; run on Windows)

Root cause of the empty DLC map: `EldenCoordinator.ToGlobalCoords` was pre-DLC and returned a
`(1e9, 9999, 9999)` sentinel for every `m61` (Land of Shadow) tile, so DLC overworld points had no
usable coordinates (only ~9 base-adjacent DLC items survived). Fixed in source this session:

1. **EldenCoordinator.cs** — added an `m61` branch mirroring the `m60` tile math, shifted into a
   private tile band (`DlcTileBand = 100`, well above the base `TILE_MAX=55`) so DLC points get a
   coherent gx/gz space of their own and never collide with base scraping or the base map.
2. **ArchipelagoForm.cs** — the coord dump now writes a trailing `mapName` column (item rows use the
   entity MapName; grace rows use `GameData.FormatMap(mapParts)`). `dlc_map.py` auto-detects it and
   filters the DLC overworld by the `m61` prefix; the column is appended last, so every existing
   consumer (`build_map.py`/`dlc_map.py` read by name; `build_location_remoteness.py` and
   `boss_attribution_dryrun.py` slice `[:7]`) is unaffected.

**Run this on Windows (the sandbox can't build C# or run AP):**

1. Rebuild the randomizer (the two .cs changes above) and run a gen with **DLC enabled** (a dlc_only
   or any enable_dlc seed) so DLC item/grace positions are captured. This drops a fresh
   `SoulsRandomizers/ap_location_coords_<stamp>.txt` with real `m61` coords + the `mapName` column.
2. `python poptracker/tools/gen_poptracker.py` — `dlc_map.py` now clears the 20-point threshold,
   draws the Land of Shadow hull, pins DLC regions at coordinate centroids, and rasterizes
   `images/maps/land_of_shadow.png` (PIL). Then `gen_poptracker.py --check` should say `up to date`.
3. Sanity: the generator's stats line should show `dlc_map: land_of_shadow` (not `placeholder`) and
   `dlc_map_regions_pinned` > 0. If the DLC overworld map id isn't `m61`, change `DLC_MAP_PREFIX` in
   `tools/dlc_map.py`.

Note: with real DLC coords, re-running `tools/build_location_remoteness.py` will now give DLC checks
real nearest-grace distances (they were sentinel before) — this can shift which DLC checks count as
"remote" in the trim. Expected/desirable, but only if you rebuild `location_remoteness.py`.
DLC INTERIOR regions (Belurat, Shadow Keep, etc.) still won't pin until their dungeon connect
offsets are built — overworld m61 surface is what this enables. Their checks still track + auto-clear
fine (that path is id-based, not coord-based).

## Validation done this session (Linux sandbox)

- `gen_poptracker.py` runs; `--check` = up to date. Stats: regions 161, dlc_regions 44,
  location_ids 4906, dlc_location_ids 1154, map_pins 115, dlc_map_pins 0 (placeholder).
- All pack JSON parses; all lua compiles (`lupa`); all tool .py parse.
- End-to-end dlc_only test (stubbed Tracker/Archipelago): clear -> 3752/4906 non-DLC sections
  cleared, the 1154 DLC sections untouched; `can_reach_gravesite_plain`=1; with all gate items held
  the reachable set is exactly the 44 DLC regions (base regions excluded as transit).

## STILL NEEDS A REAL POPTRACKER LOAD-TEST (Windows)

The pack has still never been opened in PopTracker (this is the validation gap from the prior
handoff too). Load it, try all three variants (List only / Map / DLC only), connect to a dlc_only
EldenRing AP slot, confirm the non-DLC checks drop off and the DLC checks track. Expect to fix a
schema nit or two. Watch the console for the `[ER-AP]` log lines (logic ready / clear / auto-cleared
N / handlers registered).

## Gotchas / cleanup

- **Mount truncation hazard (sandbox-only).** The Edit/Write tools tail-truncated several files on
  this mount; all were repaired via Python writes and re-verified (parse/compile). On Windows this
  doesn't exist. If you edit the tool .py or the lua by hand, re-run `--check` / a lua compile after.
- **rm is blocked on the mount.** Stray `poptracker/scripts/_probe.lua` (harmless; not loaded by
  init.lua) and the prior `poptracker/_tooltest/` + `poptracker/maps/gen_map.py` should be deleted
  on Windows.
- `package_version` bumped to `0.1.0-beta.4`.
