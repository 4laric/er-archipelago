# Curation pass — results, and the respawn signal

## Respawn IS visible in game data — it's `getItemFlagId`

The question "can we see respawn from the data" has a clean answer: **a lot's `getItemFlagId` is the
respawn flag.**

- `getItemFlagId > 0` → the game records a completion flag → **one-time** pickup.
- `getItemFlagId == 0` → no completion flag → **repeatable / respawns**.

Measured in `ItemLotParam_map`: **4,898 one-time** lots vs **481 repeatable** (flag == 0). The flag==0
set is exactly what you'd expect a respawn bucket to be — crafting mats (item #17000 ×204),
Furlcalling Finger Remedy ×16, Rune Arcs, Slumbering Eggs. The extractor already drops all 481
automatically, because a check with no flag is unwatchable by the client. So respawn exclusion is
**principled and free** — it's not a judgment call, it's a column.

## But the items matt drops are mostly NOT respawning

Your hunch was half right. The respawning stuff is auto-excluded by the flag rule. The items you saw
matt excluding — **183 of 184 Rada Fruit have a flag (one-time)**, same for Golden Rune [1] — are
one-time placed pickups. matt drops those as **trivial filler** (Rada Fruit is Torrent food), which is
a *taste* call over real pickups, not a respawn rule. So there are two separate exclusions:

| exclusion | signal | mechanical? | count |
|---|---|---|---|
| respawnable | `getItemFlagId == 0` | yes, automatic | 481 |
| trivial filler | item is low-value (Rada Fruit, low runes) | no — a design dial | ~680 |

## Curation run (`curate_locations.py` -> `curated_locations.csv`)

Rules, all mechanical over game facts (none copy matt's list): drop respawnable (flag==0); drop
infinite-stock shop rows; dedup equipment/remembrance shop rows (collapses the 3× Remembrance
listings, bell-bearing dup inventories); tag a small harvest/low-value goods blocklist as `filler`.

```
curated total            : 5,163
  core (real one-time)   : 4,905   (includes 54 synthetic-flag checks)
  filler (toggle-off)    :   258
  truly flagless (synthetic): 54   -> synthetic_flags.csv, client sets on pickup

vs matt's set: 4,150 keyed locations
  candidates that ARE in matt's set : 4,481
  candidates NOT in matt's set      :   682  <- extra one-time filler you'd be ADDING
       (179 Rada Fruit, 110 of one unnamed goods, 14 dup ashes-of-war, ...)
```

**Read that last block as the dial.** Filtering `in_matt_set == 1` lands you at ~4,481 — essentially
matt's scope, rebuilt from params with zero matt keys. Keeping everything gives ~5,163 (more filler
checks, which is a legitimate choice for AP). The `in_matt_set` and `tier` columns let you slide
between the two without any further datamining.

## Where it stands

- `candidate_locations.csv` — raw param walk (5,318), no curation.
- `curated_locations.csv` — curated set with `tier` + `in_matt_set` columns (the drop-in draft).
- `synthetic_flags.csv` — the 54 flagless checks needing a client-set tracking flag.
- `extract_locations.py` / `curate_locations.py` — the pipeline, re-runnable against any param dump.

The backbone of a matt-free standalone is now a concrete artifact, not a plan. Remaining judgment is
purely "how much filler" + naming/regions polish — no more provenance or datamining risk.

*(Not legal advice. Params/flags are game facts; deriving the selection from these rules keeps it
independent. Confirm matt's license if it gates release.)*
