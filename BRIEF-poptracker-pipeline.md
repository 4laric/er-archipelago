# BRIEF: PopTracker pack — M1 (full regions + real logic) building on the M0 skeleton

Repo: monorepo `poptracker/` (pack JSON + Lua) and `poptracker/tools/` (the generator), plus a
read of the apworld source `Archipelago/worlds/eldenring`. **Contract-FREE** (the pack consumes
slot_data read-only; it never changes it) → runs PARALLEL with every other brief. See
BRIEF-PARALLEL-INDEX.md. TODO #15 / SPEC-poptracker-pack.md.

> No Windows needed for the generator (Python 3.10+, import-free `ast`). PopTracker itself is needed
> to actually load/test the pack — that's Alaric's machine.

## Where it stands now (M0 + most of M1 id-table work DONE, this session)
`poptracker/` has a generating, JSON-valid pack: `tools/gen_poptracker.py` (161 region nodes, 90
tracked items, 4,906 location ids), `items/items.json`, `locations/locations.json`,
`layouts/item_grid.json`, stable `manifest.json` + `layouts/items_only.json` +
`scripts/{init,logic,autotracking}.lua`, a placeholder icon, `--check` for CI. Compact/list-only
(no map → no map-art license needed). Read `poptracker/README.md` first.

**Authoritative ids are already generated (no datapackage needed).** The generator runs in RUNTIME
mode: it imports items.py + locations.py standalone (stubbing only `BaseClasses`) and reads the real
`item_table` / `location_dictionary`, whose `ap_code` == the AP network id. It emits
`scripts/ap_map.lua` (item id → pack code) and `scripts/loc_map.lua` (location id → region), and
`autotracking.lua` is already id-keyed for both `on_item` and `on_location`. So former M1 items
"real ap_code table" and "location-id table" are DONE — verify them when you load the pack.

## M1 work items remaining (in dependency order)

1. **Load it in PopTracker, fix schema nits.** The pack follows PACKS.md but was never opened in the
   app here. Open it, resolve any manifest/layout/items schema errors, confirm it connects to an
   `EldenRing` AP slot, the item grid renders, and `on_item` lights up locks/keys as they arrive
   (the ids are real, so this should just work). This is the gate — do it first.

2. **DONE — per-SECTION location clearing.** `loc_map.lua` now maps each AP location id to its exact
   `@Region/Section` code; the generator sanitizes section names (`/`→`-`) so they don't collide
   with PopTracker's path separator, and `on_location` clears that exact section. Verify visually
   when you load the pack (checks should grey out individually).

3. **DONE — region-graph reachability (region level).** `region_graph.lua` is generated from
   `create_connection` edges + `_add_entrance_rule` gates; `logic.lua` does a BFS from Limgrave.
   Gates classified by adding method: `_region_lock` → applies only when `world_logic < 3`;
   `set_rules` (Academy Key, shackles, …) → all modes. Sub-regions inherit. Sanity-checked in Python
   (13 reachable at sphere 1 / 160 with all locks / 27 open). Per-LOCATION item rules remain M2 (the
   apworld declarative-rules refactor; do NOT parse the `_add_location_rule` lambdas, they don't
   serialize). Possible M1 polish: model the 1 untracked gate ("O Mother" → Hinterland) and the 1
   region with no edge (`ruined_forge_lava_intake`, currently defaults to reachable).

4. **slot_data wiring.** `autotracking.lua:on_clear` already READS `world_logic`/`enable_dlc`/
   `ending_condition`/`great_runes_required`; make them ACT: `world_logic` switches the reachability
   model (feeds item 3), `enable_dlc` shows/hides the `dlc`-tagged region nodes (already tagged in
   locations.json), the rest filter/display.

5. **`--check` into the build.** Wire `python tools/gen_poptracker.py --check` into `build.ps1`
   (a `-Pack` switch?) so a locations.py/items.py change without a regen fails the build. Pack
   version tracks the apworld `versions` lockstep string (manifest `package_version`).

## Out of scope (later milestones)
- **M2** = apworld declarative-rules refactor (`location → requirement expr` table) + generated
  per-location rules. That refactor lives in the apworld brief family, not here; it's the M2 blocker.
- **M3** = maps + region pins (BLOCKED on map-art licensing — settle that first), real 32×32 icons,
  Land of Shadow map, kindling/Scadutree counts, settings popout.

## Test plan
Generator: `gen_poptracker.py` then `--check` exits 0; intentionally edit a region in locations.py →
`--check` exits 1. In PopTracker: connect to a `region_lock` seed → only reachable regions light;
receive a lock item → its region (and graces, cosmetically) becomes reachable; check a location →
its section clears. Connect to an `open`/DLC seed → DLC regions appear, most regions reachable.

## Contract: none. Read slot_data only; never emit or require a new slot_data key or version bump.
