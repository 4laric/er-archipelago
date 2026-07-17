# SPEC — Location descriptions in the tracker

Status: IN PROGRESS 2026-07-17 (Alaric). Core waterfall + wiring + tests landed in-sandbox; the
nearest-grace coordinate datamine runs on Windows (see §4).
Owner: Alaric

## Problem

The in-client tracker (`docs/history/SPEC-item-tracker.md`) renders each remaining check by its AP
**location name**, which `gen_data` mints as `{region} :: {item} [f{flag}]`. When a region holds
several checks of the *same* vanilla item — four `Scadutree Fragment`, several `Revered Spirit Ash` —
the only thing separating them is the opaque `[f<flag>]`, so the player sees an undifferentiated wall
of identical rows and can't tell which to go get. Alaric, 2026-07-17: "the locations need to have
descriptions."

## Mechanism

AP has no separate per-location description field, and the tracker shows only the name, so the
description is **appended to the generated name**:

```
{region} :: {item} - {description} [f{flag}]
```

The `[f{flag}]` stays as the final, globally-unique tiebreaker; the item substring and the `[f...]`
suffix are both preserved, so name-substring consumers and flag-extraction (`\[f\d+\]`) are
unaffected. Only *exact full-name* equality assertions change — there is exactly one in the suite
(`test_gf_gestures`), and it stays green because gestures are excluded (below).

## The waterfall (`greenfield/desc_sources.py`)

`describe()` is pure and data-injected (every source is a dict), so it unit-tests with no artifacts
and no Archipelago (`eldenring/tests/test_gf_location_desc.py`). First non-empty layer wins:

| # | Layer | Source | Notes |
|---|-------|--------|-------|
| 1 | override | `location_descriptions.tsv` (flag→EN) | hand-authored, ALWAYS wins; where you fix any auto-descriptor or name a special case ("Remembrance of the Shadow Sunflower" → `Scadutree Avatar`) |
| 2 | boss | `boss_names` (flag→name) | boss/remembrance drops → boss name. Currently empty (`_BOSS_NAMES = {}`); remembrances are already unique so this is polish. TODO: a drop-flag→boss-name join (BOSS_HEALTHBARS is keyed by defeat flag, not drop flag). |
| 3 | spot | `treasure_name_en.tsv` (flag→EN) | CURATED place phrases. Most raw `msb_flag_region.treasure_name` values are asset-id noise (`award`/`c0000_9000`/bare `宝死体NNN`); the good ones are a JP place phrase after a colon. `clean_treasure_name()` isolates candidates; a human translates them here. |
| 4 | grace | `nearest_grace.tsv` (flag→grace name) | rendered `near <grace>`. The real locator for the Scadutree ×4 case. Produced by the Windows coord datamine (§4). |
| 5 | locale | method + map sub-tile | always-available last resort, e.g. `treasure · m20_01`. Requires a real map token, so shops/hub checks (no map) and gestures stay bare — "some are self-explanatory". |

Every source file is **optional**: an absent tsv makes its layer no-op, so generation never depends
on the Windows datamine having run. `gen_data` loads them (`_load_flag_str_tsv`) and calls
`describe()` at the name-build site.

## §4 — nearest-grace coordinate datamine (Windows)

Grace-distance used to come from the old C# randomizer's `ap_location_coords` dump; that tool was
purged in the greenfield restructure, so `tools/build_location_remoteness.py` /
`Archipelago/worlds/eldenring/location_remoteness.py` are dead relics. The coordinates are re-sourced
from the witchy'd MSBs, mirroring two verified datamines
(`datamine_msb_item_regions.py` for flag derivation, `datamine_arena_graces.py` for map-local
positions):

1. **`tools/datamine_item_grace_coords.py`** (RUN ON WINDOWS) → `greenfield/item_grace_coords.tsv`
   (`kind key map_id x y z name`). Item XYZ from the enemy part (enemy drops) or the treasure part
   (treasure); grace XYZ + name from the positioned `grace_flags.tsv` + `REGION_ID_MAP.md`.
   Two spots need on-box validation, flagged in the file: (A) treasure part→position resolution,
   (B) grace-name lookup (supply `grace_names.tsv` if the `REGION_ID_MAP.md` parse is thin).
2. **`tools/build_nearest_grace.py`** (pure, tested — `eldenring/tests/test_gf_nearest_grace.py`) →
   `greenfield/nearest_grace.tsv`. Nearest grace per item, **same-map only** (map-local frame, the
   rule arena_graces relies on). `--max-dist` caps far matches.

Commit `nearest_grace.tsv` so the sandbox consumes it on the next regen.

## Who runs what

- **In-sandbox / CI (verified):** the waterfall, gen_data wiring, the curated/override tsvs, the
  nearest-grace math, and all layers except grace. `python3 desc_sources`-side tests pass.
- **Windows (`build.ps1 -Greenfield`):** the full regen (reads raw artifacts) that actually rewrites
  the enriched names into `data.py`, plus the coord datamine (§4). Changing names is an AP-facing
  change — run the full `pytest` after regen.

## Open follow-ups

- Populate `nearest_grace.tsv` via §4 (unblocks the Scadutree ×4 case; today they fall to the
  map-sub-tile locale, which still collides for two checks sharing a sub-tile).
- Expand `treasure_name_en.tsv` from the seed-tool candidates.
- Optional layer-2 boss-name join if the auto boss name is wanted beyond overrides.
- Optional: bearing/distance in the grace layer (`near X, 60m NE`) — coords already support it.
