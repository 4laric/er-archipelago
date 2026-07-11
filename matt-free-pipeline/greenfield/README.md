# Greenfield matt-free Elden Ring apworld (MVP)

A fresh AP world built on the matt-free backbone — no inheritance from the matt-coupled apworld.
Rules are keyed by **region only**, so the whack-a-mole that killed the retrofit can't happen here.
Read `LESSONS-LEARNED.md` first — it's the design contract.

## Structure
```
eldenring_mf/
  __init__.py    # World class: items, regions (hub-and-spoke), rules, goal, slot_data
  data.py        # GENERATED: HUB, REGIONS (33 locked spokes), LOCATIONS {region:[(name,ap_id,flag)]}
gen_greenfield_data.py   # regenerates data.py from Archipelago/worlds/eldenring/matt_free_locations.py
```

## Model (Shattering)
- Menu → **Roundtable Hold** (free) → each region; entrance rule = `state.has("<Region> Lock")`.
- Item pool = 33 region locks (progression) + filler; goal = collect all locks.
- 3,944 checks across 33 spokes + hub, each carrying its game event flag.

## Verified (structurally, stub-imported — AP gen is Windows/py3.11 only)
item/location id maps build; 3,944 locations == `location_name_to_id`; every spoke lock is a real
item; itempool count == location count; completion condition set. NOT yet gen-tested.

## To gen a seed (Windows)
1. Copy the `eldenring_mf/` folder into `Archipelago/worlds/` (or zip it as `eldenring_mf.apworld`).
2. yaml: `game: "Elden Ring Matt-Free"` (no options needed for MVP).
3. Run your generate. This world is independent of the matt apworld — gen it in isolation first.

## TODO (in priority order)
1. **Client contract for in-game**: emit `regionOpenFlags` ({"<Region> Lock": [open_flag]}) so the
   client flips a region open on lock receipt (reuse `map_region_data.py` reveal/open flags), and
   `apIdsToItemIds` for received-item grants (locks = set region-open flag; filler = a real game item).
   `locationFlags` (checks) is already emitted.
2. **Regenerate data**: `python gen_greenfield_data.py` after any backbone change.
3. **Port feature modules** from the old apworld (your authorship, not matt's): num_regions (marquee),
   scaling, boss locks — onto this clean base, once the MVP gens + boots.
4. Real filler items (not one generic "Rune") + item classifications for a richer pool.
