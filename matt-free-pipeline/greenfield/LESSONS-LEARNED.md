# Matt-free apworld — architecture lessons (apply to the greenfield build)

Distilled from the retrofit attempt (2026-07-05). The retrofit proved the *data* is sound but that
the existing apworld is too matt-coupled to be the clean home. These are the design rules for the
fresh world.

## Provenance / data
1. **Location SET + keys are matt's; region PLACEMENT is a re-derivable fact.** The whole backbone
   is regenerated matt-free from vanilla params (`ItemLotParam_map/_enemy`, `ShopLineupParam`) + MSB
   Treasure/EMEVD + grace/BonfireWarp anchors. Names are functional, not matt's prose. Keep it that way.
2. **Overworld tile→region is solved matt-free** via grace anchors: `grace_flags.tsv` (flag→m60 tile)
   ⋈ `grace_region_map` (flag→play_region_id) ⋈ `REGION_ID_MAP.md` (play_region→name), nearest-neighbor
   in the tile grid. Don't hand-guess tile boxes; don't reuse the apworld's matt placement.
3. **Quest/NPC/common-event items have no data-derivable region** → exclude (questlines are
   derandomized anyway). Scattered upgrade mats (smithing stones, glovewort, golden runes) can't have
   one region → filler, not a placed check.

## Client contract (the clean seam — reuse the existing client)
4. The client consumes **`locationFlags` = {ap_id: [game event flag]}** from slot_data (built from a
   detection table). That's the ONLY location→client coupling. A synthetic `key` string is only needed
   to pass the apworld's "has a key" gate — no matt keys, no `key_resolver`.
5. Region unlocks ride the existing client's **`lockRevealFlags`** path (set region-open flags on lock
   receipt). Reuse `build_region_lock_slot_data` shape from `map_region_data.py`.
6. Received-item GRANTS need **`apIdsToItemIds`** (AP item id → game item id). MVP gen doesn't need it;
   in-game item grants do. Lock items are synthetic (grant = set region-open flag), not game items.

## Why the retrofit failed (what greenfield must NOT inherit)
7. The existing apworld is wired to matt's **location NAMES** across ≥3 independent mechanisms, each a
   separate KeyError once names change:
   - `create_items`: `item_table[location.default_item_name]`
   - `_add_location_rule` → `_is_location_available` → `location_dictionary[name]`
   - `rule_builder` geographic rules → `world.get_location(name)` (deep in AP core, unguardable)
   - plus `_key_rules`, warp rules, boss rules, num_regions spine — all name-keyed.
   Guarding them just *disables* the logic; the result is meaningless. **Greenfield writes rules FOR the
   matt-free regions, keyed by region, never by matt location name.**
8. **`item_table` = `_vanilla_items + _dlc_items + _grace_items` (3288 keys), NOT every `ERItemData`
   literal.** Validate any default item against the real `item_table`, not a regex over source.

## Greenfield design (MVP = Shattering)
9. **Hub-and-spoke region graph.** Menu → Roundtable Hold (free) → each region, entrance rule
   `state.has("<Region> Lock")`. That IS the Shattering ("region iff lock, except Roundtable"); no
   inter-region geography needed for MVP. ~34 regions, one lock item each (progression).
10. **Goal**: `completion_condition = state.has_all(all_locks)` (must explore every region). Simple,
    winnable, no matt-location dependency.
11. **Item pool**: N region locks (progression) + fill the rest (checks − locks) with filler. Keep a
    single generic filler item for MVP; swap to real game items + `apIdsToItemIds` later.
12. **Region names are the world's OWN** (Limgrave, Caelid, … + DLC), taken straight from the backbone
    mapping — no coarse "Overworld m60_XX" leaking into regions (the generator collapses tiles → majors).
13. **Port your OWN feature modules deliberately** (num_regions, scaling, boss locks). They're your
    authorship, not matt's — they drop onto a clean location base once the MVP boots. num_regions is
    the marquee mode, so treat it as its own milestone after the MVP gens + boots.

## Tooling gotchas (cost us the most time this session)
14. **The apworld is a git SUBMODULE with an unborn HEAD** — files live in the *index* (staged). Restore
    with `git checkout -- <path>` **inside the submodule**, not from the superrepo.
15. **The sandbox mount cannot reliably read/write large files** (`cp` produced 0-byte copies; writes
    truncate). Edit big files only on Windows.
16. **Never text-mode whole-file rewrite a large source file** — it corrupted `__init__.py`/`slot_data.py`
    to one line. Patches must be **binary, newline-preserving, self-verifying** (assert a sentinel like
    `location_name_to_id` survives; abort + restore on mismatch). Run patches on Windows.
17. Gen is Windows-only (AP needs Python 3.11). Sandbox can `ast.parse`/stub-import to structurally
    verify, not gen.

## What the retrofit DID validate (so greenfield stands on it)
- Backbone data loads as a real apworld: 161 region keys, **3,944 placeable checks**, 331 filler-fallback
  defaults, 34 populated regions.
- `create_items` passes — the item pool assembles from backbone defaults.
- Region creation + the `locationFlags` client contract are wired and structurally sound.
