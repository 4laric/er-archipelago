# SPEC: PopTracker pack — map + region pins (M3)

Status: SPEC, not started (Alaric, 2026-06-15). Unblocked in large part by the coordinate dump
produced during the check-trim work (`SoulsRandomizers/ap_location_coords_*.txt`).
Builds on: `poptracker/` M1 (region nodes, `loc_map.lua`, `region_graph.lua`, reachability) —
SPEC-poptracker-pack.md §4/§5, BRIEF-poptracker-pipeline.md. Independent of M1.5 trim work
(SPEC-poptracker-trim.md); they compose.

## Goal

A map-based view: region pins on Lands Between / underground / Land of Shadow images, colored by
reachability (the M1 region graph already computes this), each pin opening the region's existing
location-section list. List-only `compact` variant stays; map is an additional variant.

## What changed since the original M3 estimate

The old SPEC called pin placement "THE big manual cost" — hand-placing 161 region pins per map with
a coordinate picker. **That cost is largely gone.** `ap_location_coords_*.txt` already holds global
game coordinates (`gx/gy/gz`) + tile coords (`tileX/tileZ`) for every grace (422) and every AP
item-location (~3,200), 3,624 rows. So pins are DERIVED, not hand-placed:

1. Calibrate a world→image transform ONCE per map (eyeball the pixel position of a few known graces).
2. Each region pin = centroid of its member locations' transformed coordinates.

Reachability coloring is free: a pin's region already has a reachable/blocked state from
`logic.lua`. The map is a pure display layer over M1 — no logic changes.

## The one hard gate: map-art licensing (unchanged)

Need REDISTRIBUTABLE images for: overworld, the undergrounds (Siofra / Ainsel / Deeproot /
Mohgwyn), Land of Shadow. Three options, decide before building anything else:
- (a) hand-traced / stylized map — safe to ship, labor-heavy.
- (b) community CC map renders — verify the specific license permits redistribution in a pack.
- (c) in-game screenshot stitches — gray area; common in ER-adjacent projects but not clearly safe.

**Nothing else in this spec proceeds until this is settled.** Everything below assumes an image per
map exists and may be shipped in the pack.

## Prerequisite: one small re-dump (add a map-id column)

The current dump flattened every position through `coord.ToGlobalCoords(mapName, pos)` and DROPPED
`mapName` — header is `type / key / tileX / tileZ / gx / gy / gz`. Global XZ is enough for a single
overworld map, but undergrounds sit *beneath* the overworld in XZ, so a location can't be routed to
the correct map image by coordinate alone.

- Fix: in the C# dump (`ArchipelagoForm.RandomizeForArchipelago`, the block next to the grace dump),
  `mapName` is already in scope where `ToGlobalCoords(mapName, pos)` is called — emit it as an extra
  column (`area`/`mapName`). Cheap, mirrors the existing dump exactly.
- Re-run a single gen on Windows to regenerate the dump with the column (same RUN ORDER as
  SPEC-check-trim Phase 2: build randomizer → gen once → dump lands in `SoulsRandomizers/`).
- The `mapName`/tile prefix (overworld `m60_*`, underground `m61_*`, DLC `m21_*` etc.) is the routing
  key that assigns each location — and thus each region — to a map image.

## Design

### A. Calibration (new tool)

`tools/build_map_pins.py` (or fold into `build_location_remoteness.py`'s sibling set):
1. Read the newest `ap_location_coords_*.txt` (now with `area`).
2. Per map, a small hand-authored calibration table: 2–3 reference points = (location/grace key →
   pixel x,y you read off the shipped image once). ER's overworld is an axis-aligned 256m tile grid,
   so the transform is almost certainly scale+offset (solve from 2 points); keep a general affine
   solve (3 points, least-squares) in case a map needs rotation/skew.
3. Group locations by region (reuse the generator's `_LOC_REGION` map), transform each location's
   `(gx, gz)` → image pixels, take the centroid → one pin per region per map.
4. Emit `poptracker/maps/pins.<map>.json` (or a single `pins.json` keyed by map) = region → {x,y}.
   Also emit a residual report (max/mean pixel error of the reference fit) so a bad calibration is
   visible.

### B. Generator extension

`gen_poptracker.py`:
- Consume `pins.json`; for each region node in `locations.json`, attach `map_locations`
  (`{map, x, y}`) for the map(s) that region appears on (routed by `area`).
- Emit a `maps` manifest section (image path, size per map) — hand-author the image filenames, the
  rest generated.
- Fold `pins.json` freshness into `--check` so a region added to `locations.py` without a pin regen
  fails loudly.
- Extend the stdout line with a `pinned_regions` count.

### C. Layout / variant

- New variant `map` alongside `compact` in `manifest.json` (`compact` list-only stays the default-safe
  option since it needs no art).
- Two-pane layout: map pane + item grid; clicking a region pin shows that region's existing sections
  (PopTracker renders multiple sections per location node natively — same nodes M1 already emits).
- Pin color = region reachability from `logic.lua` (reachable / blocked); checked sections grey out via
  the existing `on_location` handler — no new autotracking.

## Coordinate gotchas

- **Underground overlaps overworld in XZ** — route by `area`/`mapName`, never by XZ. This is the whole
  reason for the re-dump.
- **Multiple maps share regions rarely** — most regions live on exactly one map; handle the few that
  span (e.g. a cave mouth on the surface, body underground) by allowing a region to carry pins on more
  than one map (`map_locations` is a list).
- **DLC (Land of Shadow)** is its own coordinate space and its own image — same calibration recipe,
  separate reference table. Composes with the M1.5 `enable_dlc` show/hide of DLC region nodes.
- **gy (height) is unused** for 2D pins but keep it in the dump; it disambiguates stacked points if a
  future per-location pin pass (out of scope) ever happens.

## Milestone slicing

1. **M3a — overworld only.** Settle art (1 image) → re-dump with `area` → calibrate overworld →
   generate pins → map variant. Useful immediately; defers undergrounds/DLC.
2. **M3b — undergrounds.** Add the 4 underground maps (art + per-map calibration), route by `area`.
3. **M3c — Land of Shadow.** DLC map + calibration; gate nodes on `enable_dlc`.
4. **Polish.** Real 32×32 icons (still the M0 grey placeholder), settings popout.

## Test plan

- `build_map_pins.py` reference-fit residual under a few pixels per map; `pinned_regions` ≈ 161 for the
  full set (fewer per individual map). `--check` exits 1 if `pins.json` is stale vs `locations.py`.
- In PopTracker: load the `map` variant → region pins render at sane positions on the image; connect a
  `region_lock` seed → reachable regions' pins light, blocked ones dimmed; receive a lock item → its
  pin opens; click a pin → that region's section list; check a location → its section greys out.
  Spot-check 5–10 well-known regions (Limgrave, Stormveil, Raya Lucaria, Caelid, Altus) against the
  real map.

## Out of scope

- Per-LOCATION pins (one pin per check) — region-granularity only, same as M1. The coords support it,
  but ~3,200 pins is a separate, heavier pass.
- Per-location item RULES (M2 apworld declarative-rules refactor) — independent.
- Interior/legacy-dungeon inset maps — list-only sections under their region pin, as in M1.

## Open questions

- Map-art license choice (a/b/c) — the gate; settle first.
- Is overworld really a clean scale+offset, or is there a tile rotation? Resolve empirically from the
  reference fit residual during M3a calibration.
- Ship pins for the few cross-map regions on both maps, or pick a primary? Decide when the routing
  data is in hand.
