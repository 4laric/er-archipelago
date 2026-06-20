# SPEC: PopTracker pack for the Elden Ring apworld

Status: FUTURE PROJECT, not started. (Alaric, 2026-06-11)
Prerequisite knowledge: PopTracker packs are folders/zips of JSON (UI, items, map pins) +
Lua (logic, auto-tracking). Docs: https://github.com/black-sliver/PopTracker (PACKS.md).
For interim tracking, Universal Tracker already works with this apworld.

## Goal

A map-based auto-tracking pack: connect to the AP slot, see which checks are reachable
under the apworld's logic, pinned on Lands Between / underground / Land of Shadow maps,
updating live as items arrive and checks complete.

## Guiding decision: GENERATE, don't hand-author

This apworld has ~3,700+ locations (4,300+ with DLC) and its logic/locations still churn.
A hand-built pack would rot immediately. The pack should be code-generated from the
apworld source by a script in this repo:

```
tools/gen_poptracker.py
  reads:  Archipelago/worlds/eldenring/{locations.py,items.py,__init__.py options}
  emits:  pack/items.json, pack/locations/*.json, pack/scripts/logic/regions.lua
```

Hand-authored, stable-by-nature pieces: manifest, layouts, map images, pin coordinates
(see below), item icons, top-level Lua glue. Everything location-shaped is generated.

## Pack anatomy & work items

### 1. manifest.json (trivial)
- `game_name` must match the AP game name "EldenRing" for auto-connect.
- Variants: `base`, `dlc` (location set + extra maps), maybe `compact` (no map, list only).

### 2. Auto-tracking glue (small, fiddly)
- PopTracker's AP interface: `Archipelago.AddClearHandler / AddItemHandler /
  AddLocationHandler / AddRetrievedHandler` in `scripts/autotracking.lua`.
- On slot connect, read **slot_data** to set pack toggles: `enable_dlc`, `world_logic`
  (region_lock vs open changes the whole reachability model), `ending_condition`,
  `dungeon_sweep` (cosmetic only), `great_runes_required`, `missable/excluded behavior`.
- Map AP item ids -> pack item codes via the generated table (ap_code is stable in
  items.py, so generate the mapping; do NOT key on names at runtime).

### 3. items.json (generated + curated icon list)
Track only logic-relevant items (~60-100), not the whole pool:
- Region locks (the 99999 sentinel keys) when world_logic=region_lock — one toggle each.
- Great Runes (+ count vs `great_runes_required`), Rold/Dectus medallion halves,
  Academy Glintstone Key, Rusty Key, Chrysalids' Memento-class quest keys,
  Spirit Calling Bell, Imbued Sword Keys (count), Stonesword Keys (count!),
  Pureblood Knight's Medal, Haligtree medallion halves, Cursemark of Death,
  Fingerslayer Blade, Dark Moon Ring, drawing-room key items.
- DLC: Messmer kindling (count vs messmer_kindle_required), gaol keys, Prayer Room Key,
  o Mother / Hole-Laden Necklace-class quest gates, Scadutree fragments (count, QoL only).
- Flag consumables as `consumable` with counts; keys as `toggle`; runes as `progressive`
  if staged thresholds matter.
- Icons: crop from community icon sheets or draw 32x32 originals. DO NOT ship ripped
  game assets without checking the pack-hosting rules (packs repo rejects some).

### 4. Maps + pin coordinates (THE big manual cost)
- Map images: need redistributable map art — options: (a) hand-traced/stylized map
  (safe), (b) community CC map renders (verify license), (c) in-game screenshot stitches
  (gray area; most ER packs-adjacent projects use these anyway). Decide before building.
- ~4,300 individual pins is not happening. Pin at **region granularity** (the 161
  apworld regions): one pin per region; clicking shows the region's location list
  (PopTracker does this natively: multiple sections per location node).
  Coordinates needed: 161 x/y pairs per map — one sitting with a coordinate-picker
  helper (PopTracker has a debug overlay; or build a tiny HTML click-to-record page).
- Maps: overworld, underground (Siofra/Ainsel/Deeproot/Mohgwyn), Land of Shadow,
  plus optional legacy-dungeon insets later. Interiors live as list-only sections
  under their region pin — no interior maps in v1.

### 5. Logic (generated; the risky part)
- Source of truth is `__init__.py`'s rules (`_add_location_rule` lambdas + region
  connections). Lambdas don't serialize, so the generator needs the rules in a
  declarative form first. REFACTOR PREREQUISITE in the apworld: migrate rules to a
  data table (`location name -> requirement expr` strings like
  `"Spirit Calling Bell" and can_reach("Liurnia")`), which __init__ compiles into
  lambdas and the generator translates to PopTracker access rules (Lua `$can_reach`
  helpers + item codes). This refactor also benefits the apworld itself (testability).
- Region graph: generate from region_order/region connections + lock items under
  region_lock logic; under open logic most regions collapse to "reachable".
- v1 simplification is acceptable: region-level reachability only (a region pin is
  green if the region is reachable; per-location nuance only where rules name specific
  items, e.g. Bell/quest checks). This matches how most large-game packs start.

### 6. Layouts (small)
- Standard two-pane: item grid + map. Settings popout for variant toggles that
  slot_data can't set (e.g. "hide missables", "hide shop checks").
- Checked/swept locations grey out via the location handler (dungeon sweep just shows
  up as a burst of cleared pins — no special handling).

## Sync & CI
- `gen_poptracker.py --check` in the build script (build.ps1 -Pack?) to fail loudly when
  locations.py adds/renames regions without regenerated pack data.
- Pack version = apworld version (the "versions" lockstep string), since logic must match.

## Milestones
1. **M0 — skeleton (a weekend):** manifest, autotracking glue, generated items.json,
   ONE map image, 10 region pins, no logic (everything "reachable"). Proves the pipeline.
2. **M1 — full regions:** all 161 region pins + generated location lists; coarse
   region-graph logic for region_lock mode. This is already a useful tracker.
3. **M2 — rules:** apworld declarative-rules refactor + generated per-location rules
   (quest gates, key items, Bell, medallions).
4. **M3 — DLC variant + polish:** Land of Shadow map, kindling counts, icons, settings.

## Open questions
- Map art licensing (decides option a/b/c above) — settle before M0.
- Whether to upstream the pack next to the apworld repo or keep it in this monorepo
  (suggest: `poptracker/` here, zipped by build.ps1).
- Stonesword Key tracking: counts are logic-relevant only if the apworld ever models
  imp statues (it currently doesn't) — keep as QoL counter until then.
