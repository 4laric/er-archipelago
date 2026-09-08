# Matt oracle: roadmap for improving check accuracy

`tools/matt_oracle.py` (AGENTS.md "MATT ORACLE") is the only independent second opinion our
generated tables have. This page tracks what it has already bought us and what is still open,
ranked by how many wrong checks each item can fix per hour of work. Licence boundary applies to
every step: read his checkout locally, commit only our own flags, names and reasons.

## Done

- Item-identity gate (class A) and missing-slot gate (class B) fail on any NEW disagreement.
- `flag_lots.tsv` datamine refreshed and `--check` wired into `regen_all.py` and CI (PR #1480).
- Rennala 177/197, Great Rune 191-196 recorded as KEYING, not gaps.

## Open, ranked

1. **99 DLC upgrade-material tier disagreements (class A, `_A_OPEN_DLC_MATERIAL`).**
   The datamine refresh did not close these: the oracle compares the curated `item_name` column,
   which was never regenerated from the lot. Step: regenerate `LOCATION_ITEM` names for the 99
   flags from the refreshed `flag_lots.tsv`, diff against his, and expect the class to collapse to
   zero. Wrong tier means wrong filler weight and, for stones, wrong logic on upgrade gating.
   Also covers the 37 rows where the curated name no longer matches the lot (silent x1).

2. **4 wrong-item rows (class A OPEN: 400282/400283/400285/400358).**
   Verify against the lot in `flag_lots.tsv`; fix the row, drop the allowlist entry. Half an hour.

3. **45 missing slots (class B `_B_OPEN`).**
   Triage into three bins: real pickups to add to `data.LOCATIONS` (Forager Brood Cookbooks, the
   second Blessing of Marika and Academy Glintstone Key, the Rise talisman, one Furnace Golem drop),
   quest rewards in the 400xxx band we model elsewhere under a different flag (record as KEYING),
   and anything auto-granted (record as SCOPE). Each bin shrinks the allowlist rather than growing it.

4. **Region assignment for "(region unconfirmed)" rows.**
   About 218 of 4027 joinable rows disagree, clustered on cookbooks, crystal tears and perfume
   bottles our generator could not place. Rule: where his area maps unambiguously to exactly one of
   our regions, treat the disagreement as a resolvable TODO and fix it through the normal derivation
   ladder (`M61_TILE_CURATED`, `DUNGEON_REGION_CURATED`, `region_overrides.tsv` only as last resort),
   never by writing his area names into the tree. Escalate that subset from report to FAIL once
   cleared. The two DLC-membership rows (520800, 530950) belong here.

5. **Missable tagging.**
   Semantics differ, so no blanket gate. Two clean sub-classes: mark the three Furnace Golem crystal
   tears (65430/65450/65460) missable; reconsider 60510 (Talisman Pouch) which we call questline and
   he calls a plain boss drop. Target: raise `missable_locations.py` toward his 168 joinable rows
   with a curated fail-list.

6. **4 shop-vs-lot flags (400282/400283/400285/400390).**
   Overlaps item 2. Decide once whether these are shop rows; the 253 flagless infinite-stock shop
   ids he tracks are out of scope by design and should be written down as such in `shop_data.py`.

7. **Derive new tables, validate against him.**
   - `enemy_drops` from NpcParam / ItemLotParam_enemy, count-checked against his 393 `enemy` slots
     (`docs/history/TODO-baker-era.md:394`).
   - ~~Boss taxonomy (overworld / minidungeon / cave / catacomb / dragon / furnace golem) from our own
     map data, histogram-checked against his tags.~~ **DONE**: `tools/gen_boss_taxonomy.py` ->
     `tables/boss_taxonomy.py`, 245 bosses over 11 classes, printed as report class **C**.
     Evergaols are EMEVD-derived (the arena-seal common-event family), not a hand-typed list.
     ONE class is still open and is emitted empty on purpose: `furnace_golem`, because no boss
     healthbar, no `NpcName` row and no MSB in the artifact bundle leaves nothing of ours to
     enumerate. His `furnacegolem` tag carries 16 slots, so that is a real ~10-boss family we do
     not model. Deriving it needs c4900 placements added to the artifact bundle.
   - ~~Reachability: use his 174-area graph only as a coverage counter. Author the logic
     ourselves.~~ **DONE (counter only)**: report class **D** prints `our graph reaches 30 regions
     / 56 grace-warp groups; his reaches 174 areas`, his side computed at run time and never
     committed. The counter is the whole of it — authoring finer logic of our own is still open,
     and the ratio is what says how much finer it would have to get.

## Operating rules

- Every fix removes an allowlist entry; a stale entry is a warning, so the lists only shrink.
- Run `python tools/matt_oracle.py --souls-rando-dir <checkout> --report --json out.json` before and
  after each PR and quote the class counts in the PR body.
- Delegable to Opus: items 1, 2, 3 (triage output reviewed by a human), 5 sub-classes, 6.
  Items 4 and 7 need a product ruling per region or table.
