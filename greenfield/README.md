# Greenfield Elden Ring apworld

A fresh Archipelago world whose location data is **derived from vanilla game files** (params + MSB +
grace/BonfireWarp anchors) — independent of the existing apworld, with rules keyed by **region only**
so there's no location-name coupling to fight. Read `LESSONS-LEARNED.md` first (design contract).

## Layout
```
greenfield/
  eldenring/
    __init__.py   # World class: items, hub-and-spoke regions, rules, goal, slot_data
    data.py       # GENERATED: HUB, REGIONS (31: 17 base + 14 DLC), LOCATIONS {region:[(name,ap_id,flag)]}
  players/Greenfield.yaml   # isolated player file (game: "Elden Ring")
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
`-Greenfield` installs `eldenring` into `Archipelago\worlds\`, then generates in isolation using
`greenfield\players\` (your normal `Players\` and the existing apworld are untouched). Or run the
helper directly: `.\greenfield\gen-greenfield.ps1`. Revert the build.ps1 change with
`python greenfield\patch_build_greenfield.py --revert`.

## Curated presets (start here)
Rather than hand-tune the ~46-option surface, copy one of the vetted presets in `presets/` into
`players/` (rename per slot) and generate. Each one gen-tests clean and keeps the safety defaults
(Torrent whistle + Roundtable hub start, so no mountless-open-world softlock):

| Preset | Scope | For |
|--------|-------|-----|
| `presets/sync-friendly.yaml` | 4 spine regions, real items, meaningful checks | flagship 2-slot+ multiworld, ~4-8h evening |
| `presets/standard.yaml` | full base-game Shattering | the balanced default |
| `presets/kitchen-sink.yaml` | everything on, base + DLC (EXPERIMENTAL) | maxed marathon; rough pacing by design |

`num_regions` is pinned explicitly in every preset (never rely on its default). Prove a preset
generates before a session -- copy it into a temp player dir and run AP `Generate.py`:
```
cp presets/sync-friendly.yaml players/          # (clear players/ first for a solo seed)
( cd $AP && AP_NONINTERACTIVE=1 SKIP_REQUIREMENTS_UPDATE=1 python Generate.py     --player_files_path <repo>/greenfield/players --outputpath <out> )
```

## Verified (structurally; not yet gen-tested)
World stub-imports; 23 items (22 locks + filler); 24 regions; 3,944 locations == `location_name_to_id`;
itempool count == location count; goal set. build.ps1 patch is byte-safe/self-verifying/ASCII.

## TODO
1. In-game client contract: `regionOpenFlags` (open a region on lock receipt) + `apIdsToItemIds`
   (received-item grants). `locationFlags` (checks) is already emitted.
2. Regenerate data after backbone changes: `python greenfield\gen_data.py`.
3. Port feature modules (num_regions, scaling, boss locks) onto this clean base after MVP boots.
