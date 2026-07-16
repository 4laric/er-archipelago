# Greenfield ER apworld — architecture lessons

Distilled from the retrofit attempt (2026-07-05). The retrofit proved the *data* is sound but that
the existing apworld is too coupled to its original location names to be the clean home. These are
the design rules for the greenfield world.

## Data / provenance
1. **The location set is data-derived.** The backbone is regenerated from vanilla game files
   (`ItemLotParam_map/_enemy`, `ShopLineupParam`) + MSB Treasure/EMEVD + grace/BonfireWarp anchors.
   Names are functional. Keep it that way — no importing the old set.
2. **Overworld tile -> region is solved from map data** via grace anchors: `grace_flags.tsv`
   (flag->m60 tile) join `grace_region_map` (flag->play_region_id) join `REGION_ID_MAP.md`
   (play_region->name), nearest-neighbor in the tile grid. Don't hand-guess tile boxes.
3. **Quest/NPC/common-event items have no data-derivable region** -> excluded. Scattered upgrade mats
   can't have one region -> filler, not a placed check.

## Client contract (reuse the existing runtime client)
4. The only location->client coupling is **`locationFlags` = {ap_id: [game event flag]}** in
   slot_data. No original-set keys, no key resolver.
5. Region unlocks ride the client's region-open-flag path (set open flags on lock receipt) -> emit
   `regionOpenFlags`. Received-item grants need `apIdsToItemIds` (locks = set region-open flag).

## Why the retrofit failed (do NOT inherit this)
6. The existing apworld is wired to specific location NAMES across >=3 independent, seed-dependent
   mechanisms, each a separate crash once names change:
   - `create_items`: `item_table[location.default_item_name]`
   - `_add_location_rule` -> `_is_location_available` -> `location_dictionary[name]`
   - `rule_builder` geographic rules -> `world.get_location(name)` (deep in AP core, unguardable)
   - plus key rules, warp rules, boss rules, the num_regions spine.
   Guarding them just DISABLES the logic. **Greenfield keys every rule by REGION, never by location name.**
7. **`item_table` = `_vanilla_items + _dlc_items + _grace_items` (~3288 keys)**, NOT every source item
   literal. Validate any default item against the real table.

## Greenfield design (MVP = Shattering)
8. **Hub-and-spoke.** Menu -> Roundtable Hold (free) -> each region gated by `state.has("<Region> Lock")`.
   That IS the Shattering; no inter-region geography for MVP. ~22 regions, one lock each (progression).
9. **Goal** = `state.has_all(all_locks)`. Simple, winnable, no location-name dependency.
10. **Pool** = N locks (progression) + filler. Single generic filler for MVP; real items + `apIdsToItemIds` later.
11. **Regions are the world's own** clean names (Limgrave, Caelid, Land of Shadow, ...); the generator
    collapses overworld tiles into majors so no raw tile leaks into the region set.
12. **Port your OWN feature modules deliberately** (num_regions is the marquee mode, then scaling,
    boss locks) onto this clean base once the MVP gens + boots. They're your authorship — they move over.

## Tooling gotchas (cost the most time)
13. The existing apworld is a git SUBMODULE with an UNBORN HEAD — files live in the index (staged);
    restore with `git checkout -- <path>` INSIDE the submodule.
14. The sandbox mount can't reliably read/write large files (0-byte `cp`, truncation) — edit big files
    only on Windows.
15. Never text-mode whole-file-rewrite a large source file (it collapsed `__init__.py` to one line).
    Patches must be binary, newline-preserving, self-verifying (assert a sentinel survives; abort +
    restore on mismatch), ASCII for .ps1, and run on Windows.
16. Gen is Windows-only (AP needs Python 3.11); the sandbox can only `ast.parse`/stub-import to verify.

## What the retrofit validated (greenfield stands on it)
Backbone loads as a real apworld; item pool assembles from defaults; region creation + the
`locationFlags` contract are structurally sound. 3,944 placeable checks across the clean region set.
