# Greenfield ER apworld — handoff (2026-07-05)

## State: WORKING MVP (committed + pushed)
The greenfield world generates a complete, winnable Shattering seed end to end. AP recognizes it as
its own game ("Elden Ring", 23 items, 3,944 locations); fill placed all 3,922 pool items,
playthrough calculated, `AP_*.zip` produced. Branch: `feat/matt-free-backbone-mvp`.

This is a from-scratch, data-derived world with rules keyed by **region only** — no coupling to the
original apworld's location names (that coupling is what killed the earlier retrofit). Read
`LESSONS-LEARNED.md` before changing anything; it's the design contract and explains WHY it's built
this way.

## Where things are
- `greenfield/eldenring/__init__.py` — the World class (items, hub-and-spoke regions, rules, goal,
  slot_data). Hand-written, static.
- `greenfield/eldenring/data.py` — GENERATED: `HUB`, `REGIONS` (22 locked spokes), `LOCATIONS`
  {region:[(name, ap_id, flag)]}.
- `greenfield/gen_data.py` — regenerates data.py from `greenfield/region_map.csv` + grace anchors
  (`elden_ring_artifacts/`). Run after any backbone change.
- `greenfield/region_map.csv` — the matt-free location backbone (source of truth for the data).
- `greenfield/players/Greenfield.yaml` — isolated player file (`game: "Elden Ring"`).
- `greenfield/gen-greenfield.ps1` — installs the world into `Archipelago\worlds\` + gens in isolation.
- `greenfield/patch_build_greenfield.py` — adds the `-Greenfield` mode to build.ps1 (applied).
- The backbone pipeline (how region_map.csv was derived) lives in `matt-free-pipeline/`.

## How to run
```
.\build.ps1 -Greenfield        # install + gen in isolation (normal Players\ + apworld untouched)
```
Regenerate data after backbone edits: `python greenfield\gen_data.py`.

## Next work (priority order — all additive, no whack-a-mole)
1. **In-game boot (client contract).** Gen works; booting needs slot_data to also emit:
   - `regionOpenFlags` = {"<Region> Lock": [open_flag]} so the client flips a region open on lock
     receipt. Reuse the region open/reveal flags in `Archipelago/worlds/eldenring/map_region_data.py`
     (`REGIONS`/`build_region_lock_slot_data`) — map each greenfield region to its open flag.
   - `apIdsToItemIds` = {ap_item_id: game_item_id} for received-item grants. Locks are synthetic
     (grant = set region-open flag, no game item); filler needs a real game item id.
   `locationFlags` (checks) is already emitted, so checks should register once connected.
2. **Port num_regions** (the marquee mode) onto this clean base, then scaling, boss locks. They're
   Alaric's own code in the existing apworld — portable, but do it deliberately after boot works.
3. **Refine coarse regions** if desired: DLC collapses into a few big buckets (Land of Shadow, etc.),
   undergrounds into "Eternal Cities". Tune `REGION_MAP`/`PLAY2AP` in `gen_data.py`.
4. **Low-confidence placements** to audit in-game: `matt-free-pipeline/low_confidence_review.csv`
   (39 rows: overworld DLC sub-area + block-100900 Abandoned Merchant).

## Gotchas (learned the hard way this session)
- The existing apworld (`Archipelago/`) is a git SUBMODULE with an UNBORN HEAD — files live in the
  index; restore with `git checkout -- <path>` INSIDE the submodule.
- The sandbox mount can't reliably read/write large files (0-byte `cp`, truncation). Edit big files
  (e.g. `__init__.py`, `build.ps1`) ONLY on Windows.
- Never text-mode whole-file-rewrite a large source file (it collapsed `__init__.py` to one line).
  Patches must be binary, newline-preserving, self-verifying, ASCII for .ps1 — and run on Windows.
- AP gen needs Python 3.11 (Windows); the sandbox can only `ast.parse`/stub-import to verify.
- `item_table` = `_vanilla_items + _dlc_items + _grace_items` (~3288), NOT every source item literal.

## Cleanup / status
- The RETROFIT approach is ABANDONED (the existing apworld is too name-coupled). If its patch is still
  applied on any machine: `python patch_use_mattfree_backbone.py --revert`.
- `matt-free-pipeline/greenfield/` (old `eldenring_mf` naming) is SUPERSEDED by this `greenfield/` dir
  — safe to delete.
