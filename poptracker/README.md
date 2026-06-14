# Elden Ring Archipelago — PopTracker pack (M0 skeleton)

Status: **M0 (skeleton, pipeline proof)**. Generates and loads, no real logic or map yet. See
`../SPEC-poptracker-pack.md` for the design and `../TODO.md` #15 for the milestone ladder.

## What M0 is
A code-GENERATED pack (the apworld has 161 regions / ~4,900 locations and churns, so hand-authoring
would rot). `tools/gen_poptracker.py` parses the apworld source and emits the location-shaped files:

| File | Generated? | Source |
|------|-----------|--------|
| `items/items.json` | yes | `items.py` — 31 region-lock items + curated key items (90 total) |
| `locations/locations.json` | yes | `locations.py` — 161 region nodes, checks as sections |
| `layouts/item_grid.json` | yes | derived from items.json (rows of 8) |
| `scripts/ap_map.lua` | yes | AP item id → pack code (authoritative; 90 ids) |
| `scripts/loc_map.lua` | yes | AP location id → region name (authoritative; 4,906 ids) |
| `manifest.json`, `layouts/items_only.json`, `scripts/{init,logic,autotracking}.lua` | no (stable, hand-authored) | — |

### How the authoritative ids work (no datapackage needed)
The apworld assigns each item/location an `ap_code` at runtime, and `__init__.py` sets
`item_name_to_id`/`location_name_to_id = {name: ap_code}` — so **`ap_code` IS the AP network id**
the tracker receives. `gen_poptracker.py` runs in RUNTIME mode: it imports `items.py` + `locations.py`
standalone (stubbing only `BaseClasses`, faking the `worlds.eldenring` package) and reads the real
`item_table` / `location_dictionary`. No datapackage, no name-matching. If that import ever fails it
falls back to ast parsing and skips the id maps (autotracking would then need name-keying) — the
`mode` field in the generator's output line tells you which ran.

M0 deliberately ships the **compact / list-only** variant: no map images, so it sidesteps the
map-art licensing question (the SPEC's pre-M0 blocker). Everything is shown as an item grid; the
location nodes exist and are reachable-by-default.

## Regenerate (do this when apworld logic/locations change)
```
python3 tools/gen_poptracker.py            # regenerate items/locations/item_grid JSON
python3 tools/gen_poptracker.py --check    # CI: exit 1 if committed JSON is stale
```
Import-free (uses `ast`), so it runs on Python 3.10+ without the AP framework. Wire `--check` into
`build.ps1` (`-Pack`?) so a locations.py change without a regen fails loudly.

## Status of the M1 work items (see BRIEF-poptracker-pipeline.md)
- **DONE — authoritative item ids.** `ap_map.lua` maps AP item id → pack code; `autotracking.lua:on_item`
  is id-keyed. No more name-matching.
- **DONE — authoritative location ids.** `loc_map.lua` maps AP location id → `@Region/Section` code
  (4,906 ids). Section names are sanitized (`/`→`-`) so they don't collide with PopTracker's
  `@region/section` path separator; `on_location` clears the exact section.
- **DONE — region-graph reachability.** `region_graph.lua` (generated from `create_connection` edges +
  `_add_entrance_rule` gates) + `logic.lua` BFS from Limgrave. Gates are classified by the apworld
  method that adds them: `_region_lock` gates apply only when region gating is active (`world_logic
  < 3`); `set_rules` gates (Academy Glintstone Key, shackles, …) apply in all modes. Sub-regions
  inherit reachability. Sanity-checked: 13 regions reachable at sphere 1, 160 with all locks, 27 in
  open mode. (Region-LEVEL; per-location item rules remain M2 — they need the apworld declarative-
  rules refactor.)
- **TODO — load in PopTracker.** JSON/Lua follow PACKS.md but haven't been opened in the app here
  (no Lua interpreter in this env); first remaining step is to load it and fix any schema nits.
- **Later — maps/pins** (M3, blocked on map-art licensing) and **real icons** (M3; one grey 16×16
  placeholder for now).

## Not yet validated against PopTracker itself
The JSON/Lua follow the PopTracker pack schema (PACKS.md) but have NOT been loaded in the app here.
First M1 step: open in PopTracker, fix any manifest/layout schema nits, confirm it connects to an
EldenRing slot.
