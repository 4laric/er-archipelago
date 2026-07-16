# Greenfield Elden Ring apworld

The apworld source for this project's Elden Ring Archipelago world. Location and
item data is **derived from vanilla game files** (params + MSB + grace/BonfireWarp
anchors) — no code or data from any other randomizer — and rules are keyed by
**region only**, so there is no location-name coupling to fight.

The model in one line: the world is Shattered into **31 regions (17 base game +
14 Shadow of the Erdtree)**, each sealed behind a **"\<Region\> Lock"** AP item;
you start at Roundtable Hold, and Leyndell is the goal region.

**The data modules are GENERATED — never hand-edit them.** `eldenring/data.py`
and its siblings (`region_open_flags.py`, `boss_data.py`, `region_graces.py`,
`shop_data.py`, `item_ids.py`, `item_tiers.py`, ...) are written by
`gen_data.py`. Regenerate with `python greenfield/gen_data.py` (or
`.\build.ps1 -Greenfield`, which regenerates, installs, and gens); a gen-input
stamp (`tools/gen_manifest.py`) gates stale data out of packaging and CI.

## Layout
```
greenfield/
  eldenring/              # the world package (ships as eldenring.apworld via build.ps1 -Apworld)
    core.py               # options, regions, rules, goal, slot_data
    data.py               # GENERATED: HUB, REGIONS (31: 17 base + 14 DLC), LOCATIONS {region: [(name, ap_id, flag)]}
    region_spine.py       # SPINE progression order, GOAL_REGION (Leyndell), DLC_REGIONS
    features/             # feature modules (graces, boss locks, pool builder, scaling, upgrades, ...)
    tests/                # the test suite (see tests/README.md)
  gen_data.py             # regenerates the data modules from vanilla game data — the only way to change them
  gen_contract.py         # regenerates CONTRACT.md + the client's generated contract tables
  gen-greenfield.ps1      # regen + install into Archipelago\worlds + isolated gen (what build.ps1 -Greenfield runs)
  CONTRACT.md             # GENERATED apworld <-> client slot_data contract (from eldenring/contract.py)
  IN-GAME-VALIDATION.md   # the in-game proof checklist (tiers, pass/fail)
  presets/                # vetted player yamls (see below)
  playtest-yamls/         # targeted validation yamls (see its README)
  players/                # the isolated player dir build.ps1 -Greenfield gens from
  region_map.csv, *.tsv   # curated gen inputs read by gen_data.py
```

## Entry points

- **Big picture** (pure-runtime model, Region Locks, player setup): the root
  `README.md`.
- **The client contract** (`regionOpenFlags`, `apIdsToItemIds`, `locationFlags`,
  the options echo, ...): `CONTRACT.md`, generated from `eldenring/contract.py`
  — the single source of truth the Rust client
  (`from-software-archipelago-clients`, crates `eldenring-archipelago` +
  `er-logic`) is held to.
- **Test**: `python tools/gf_test.py` — bootstraps a pinned **upstream**
  Archipelago into `.ap-test/`, installs the world, runs the suite; refuses to
  run against a fork. `run_ci.ps1` runs every automated gate.
- **Run a seed**: copy a preset from `presets/` into `players/` and
  `.\build.ps1 -Greenfield`; players start from `release-v0.2/EldenRing.yaml`
  instead (see the root README).

## Curated presets

| Preset | Scope | For |
|--------|-------|-----|
| `presets/first-run.yaml` | base game, 8 regions | a bounded first seed |
| `presets/short-solo.yaml` | base game, 4 regions | a tight ~evening solo run |
| `presets/multiworld-sync.yaml` | base game, 6 regions | a polite footprint for a shared game |
| `presets/base-shattering.yaml` | the whole base game (all 17 regions) | the balanced default marathon |
| `presets/dlc-only.yaml` | only the Shadow of the Erdtree regions (EXPERIMENTAL) | a DLC-only run |

The presets are **generated** by `tools/dump_options_metadata.py` from the live option
surface (the same run that feeds the wizard) — do not hand-edit them; re-run the dump.
Prove a preset generates before a session: copy it into `players/` (clear `players/`
first for a solo seed) and run `.\build.ps1 -Greenfield`.
