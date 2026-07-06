# Greenfield Elden Ring apworld

A fresh Archipelago world whose location data is **derived from vanilla game files** (params + MSB +
grace/BonfireWarp anchors) — independent of the existing apworld, with rules keyed by **region only**
so there's no location-name coupling to fight. Read `LESSONS-LEARNED.md` first (design contract).

## Layout
```
greenfield/
  eldenring_gf/
    __init__.py   # World class: items, hub-and-spoke regions, rules, goal, slot_data
    data.py       # GENERATED: HUB, REGIONS (22 locked spokes), LOCATIONS {region:[(name,ap_id,flag)]}
  players/Greenfield.yaml   # isolated player file (game: "Elden Ring (Greenfield)")
  gen_data.py               # regenerate data.py (reads region_map.csv + grace anchors)
  gen-greenfield.ps1        # install world into Archipelago\worlds + generate (isolated)
  patch_build_greenfield.py # add the -Greenfield mode to build.ps1
  region_map.csv            # the data-derived backbone (source for gen_data.py)
```

## Model (Shattering, MVP)
Menu -> Roundtable Hold (free) -> each region, entrance rule `state.has("<Region> Lock")`.
Pool = 22 region locks (progression) + filler; goal = collect all locks. 3,944 flag-keyed checks.

## Run it (Windows; AP gen needs Python 3.11)
Wire the build-script mode once, then use it:
```
python greenfield\patch_build_greenfield.py --apply     # adds -Greenfield to build.ps1
.\build.ps1 -Greenfield
```
`-Greenfield` installs `eldenring_gf` into `Archipelago\worlds\`, then generates in isolation using
`greenfield\players\` (your normal `Players\` and the existing apworld are untouched). Or run the
helper directly: `.\greenfield\gen-greenfield.ps1`. Revert the build.ps1 change with
`python greenfield\patch_build_greenfield.py --revert`.

## Verified (structurally; not yet gen-tested)
World stub-imports; 23 items (22 locks + filler); 24 regions; 3,944 locations == `location_name_to_id`;
itempool count == location count; goal set. build.ps1 patch is byte-safe/self-verifying/ASCII.

## TODO
1. In-game client contract: `regionOpenFlags` (open a region on lock receipt) + `apIdsToItemIds`
   (received-item grants). `locationFlags` (checks) is already emitted.
2. Regenerate data after backbone changes: `python greenfield\gen_data.py`.
3. Port feature modules (num_regions, scaling, boss locks) onto this clean base after MVP boots.
