# HANDOFF — PopTracker pack (tracker + map), 2026-06-15

Context for a fresh session. The ER-AP PopTracker pack lives in `poptracker/`. This session took it
from "list-only, never loaded" to "map variant wired + auto-generated from coordinate data." Specs:
`SPEC-poptracker-pack.md` (M1), `SPEC-poptracker-trim.md` (M1.5), `SPEC-poptracker-map.md` (M3).
Background detail is in memory `er-check-trim-spec.md` (the poptracker notes are appended at the end).

## THE ONE CRITICAL NEXT ACTION (do this first, on Windows)

The sandbox this session ran in had a degraded mount that **could not run the generators or write the
tracked pack files**. So the generated outputs below are NOT yet materialized. On the Windows box:

1. `python poptracker/tools/gen_poptracker.py`
   - Regenerates `locations.json` (now with `map_locations` pins), `maps/maps.json`, and rasterizes
     `images/maps/lands_between.png` (needs `pip install cairosvg`; if absent it skips the PNG with a
     warning and you rasterize the SVG yourself).
   - Then `python poptracker/tools/gen_poptracker.py --check` should print `up to date`.
2. **First real PopTracker load-test.** The pack has NEVER been opened in PopTracker. Load it, pick the
   "Map (Lands Between)" variant, connect to an EldenRing AP slot. Use `poptracker/VALIDATE-CHECKLIST.md`.
   Expect to fix a schema nit or two — this is the validation pass, not a known-good asset.

## State of the pack

- **M1 (list-only) — DONE, unvalidated.** Generated items/locations/region-graph + id-keyed
  autotracking (`ap_map.lua`, `loc_map.lua`). Region-level reachability via `region_graph.lua` + BFS.
- **M3a (overworld map variant) — WIRED this session, unvalidated.** Original stylized parchment map
  (convex hull of the real coordinate cloud — NOT ER's true coastline, no game art) with region pins at
  real coordinate centroids. 19 majors labeled; pins emitted for all 115 regions that have coords.
- **M1.5 (trimmed/lean pool awareness) — SPEC ONLY.** apworld half shipped (`location_pool` is in
  `fill_slot_data`); generator half (tag pool membership, hide trimmed sections) not built. See
  `SPEC-poptracker-trim.md`.

## How the map pipeline works (so you can extend it)

- `poptracker/tools/build_map.py` — the map engine. Reads the newest `ap_location_coords_*.txt`
  (repo root or `SoulsRandomizers/`), filters to base overworld (tileX<55, drops sentinels + DLC),
  builds the hull/SVG, computes per-region median centroids via a key→region join parsed from
  `locations.py`'s `location_tables`, and emits: `lands_between_map.svg`, `map_calibration.json`,
  `region_centroids.json`, `region_pins.json`, `maps/maps.json`, and the PNG. Returns the pins dict.
- `gen_poptracker.py` imports `build_map` and calls it inside `generate()`; `emit_locations_json`
  attaches `map_locations` from the pins. **Gated on the dump:** no dump → `build_map` returns empty
  file targets but still reads the COMMITTED `region_pins.json`, so `locations.json` regenerates
  identically on a dump-less machine (no cross-machine `--check` staleness).
- Transform is EXACT (authored in gx/gz space): see `maps/map_calibration.json`. +Z is North (up).
- Orientation verified by name: Limgrave center-south, Caelid east, Liurnia west, Altus north,
  Weeping Peninsula south tip, Mountaintops far NE — all correct.

## Config wired for the map variant

- `manifest.json`: added `map` variant; bumped to `0.1.0-beta.3`; `min_poptracker_version` 0.26.2.
  **Latent bug fixed:** variant flags were `["compact"]` (no autotracking flag) → set BOTH variants to
  `["ap"]` so AP autotracking actually activates.
- `scripts/init.lua`: variant-conditional — `if Tracker.ActiveVariantUID == "map"` → `AddMaps` +
  `layouts/map.json`, else `layouts/items_only.json` (both define `tracker_default`, load exactly one).
- `layouts/map.json`: map widget (`maps:["lands_between"]`, max_width 720) beside the item grid.

## Gotchas / cleanup

- **Mount hazard (sandbox-only).** The agent mount read-truncates file-tool-OVERWRITTEN files and
  blocks tracked pack files — that's why nothing could be run/verified in-session. On a normal machine
  this does not exist. All source files were confirmed written complete (tails intact).
- **Cleanup:** delete the stray `poptracker/_tooltest/` (untracked scratch) and the superseded
  `poptracker/maps/gen_map.py` (old prototype; `build_map.py` replaces it).
- `images/maps/` did not get created in-sandbox; the Windows `gen_poptracker.py` run creates it.

## Next options (none blocking)

- **Build M1.5 generator half** (trimmed/lean): tag each location's pool membership, hide trimmed
  sections on connect. Spec ready.
- **M3b/M3c maps** (undergrounds, Land of Shadow): needs the small `mapName`-column re-dump described in
  `SPEC-poptracker-map.md` (the C# dump in `ArchipelagoForm.RandomizeForArchipelago` already has
  `mapName` in scope), then re-run build_map per map.
- **Coastline refinement:** the hull is a stylized envelope; could hand-trace a more ER-shaped outline
  while keeping the exact transform.
