# Matt oracle: roadmap for improving check accuracy

`tools/matt_oracle.py` (AGENTS.md "MATT ORACLE") is the only independent second opinion our
generated tables have. This page tracks what it has already bought us and what is still open,
ranked by how many wrong checks each item can fix per hour of work. Licence boundary applies to
every step: read his checkout locally, commit only our own flags, names and reasons.

## Done

- Item-identity gate (class A) and missing-slot gate (class B) fail on any NEW disagreement.
- `flag_lots.tsv` datamine refreshed and `--check` wired into `regen_all.py` and CI (PR #1480).
- Rennala 177/197, Great Rune 191-196 recorded as KEYING, not gaps.
- **Items 1, 2 and 6 (2026-09-08).** `gen_data`'s lot-reconcile pass makes the check's own
  ItemLotParam row the authority on which item it holds, closing all 99 DLC upgrade-material
  disagreements and restoring the stack quantities they had been silently paying as x1. Class A
  went 107 -> 8 (agreement 97.4% -> 99.8%). 400282/400283/400285 re-adjudicated from OPEN to
  BUNDLE (each fires two map lots); 400358 corroborated on our side against the param. None of
  400282/3/5/400390 is a shop row -- no ShopLineupParam row names them -- and the flagless
  infinite-stock shop ids are written down as out of scope in `shop_data.py`'s header.
- **Item 3 (the 45 `_B_OPEN` missing slots) is triaged and the `_B_OPEN` bin is RETIRED.** Verdict:
  1 KEYING, 44 SCOPE, **0 addable**. The ranked entry below predicted "real pickups to add"; none of
  them survived the evidence, because every one is already refused by a NAMED gen_data exclusion or
  by the region derivation itself. Kept here in full as the worked example of the rule that matters:
  **a disagreement with his table is evidence that we should LOOK, not evidence that we are wrong.**
  The groups, and the flag ints, are in `tools/matt_oracle.py` next to their reasons.

## Open, ranked

1. ~~99 DLC upgrade-material tier disagreements.~~ **Done 2026-09-08** -- see above.

2. ~~4 wrong-item rows (400282/400283/400285/400358).~~ **Done 2026-09-08** -- see above.

3. ~~**45 missing slots (class B `_B_OPEN`).**~~ **DONE — and the answer was not the expected one.**
   The predicted real gaps (Forager Brood Cookbooks, second Blessing of Marika, second Academy
   Glintstone Key, the Rise talisman, the Furnace Golem drop) are each already excluded ON PURPOSE:
   `_UNPLACEABLE_DLC_COOKBOOKS`, `_SHEET_DROPS`, `_UNREACHABLE_DEAD`, `_WORLDLESS_SINGLES`. The
   400xxx band is not "modelled elsewhere under a different flag" either — those rows are
   `Global / Common-event (unplaced)`, and `tools/datamine_unplaced_globals.py` takes 32 of them as
   candidates and **resolves zero**, refusing each by name (talk ESD names only a common bucket;
   ambiguous across 2-5 maps because the NPC relocates; no evidence in any corpus).

   **THE RESIDUAL DEBT, restated honestly** — 26 flags are real, separately-collectable pickups we
   do not ship, blocked on ONE missing fact each: a region. The bar is a witness (an observed MSB
   map, an item coordinate, a single-map EMEVD or talk-ESD award), recorded as a hand pin in
   `gen_data.GLOBAL_RECOVER`. 530935, the second Blessing of Marika, is the best-evidenced: the tool's
   own docstring carries boblerrr's 2026-08-07 report of collecting both lots on one character. This
   is now an item 4-shaped problem (region assignment), not an item 3-shaped one, and it needs a
   product ruling or an in-game witness per flag — it is NOT delegable as a triage.

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

6. ~~4 shop-vs-lot flags (400282/400283/400285/400390).~~ **Done 2026-09-08** -- none of them is
   a shop row, and the flagless infinite-stock shop ids are now recorded as out of scope by
   design in `shop_data.py`.

7. **Derive new tables, validate against him.**
   - ~~`enemy_drops` from NpcParam / ItemLotParam_enemy, count-checked against his 393 `enemy`
     slots (`docs/history/TODO-baker-era.md:394`).~~ **DONE 2026-09-08.**
     `tools/datamine_enemy_drops.py` -> `greenfield/enemy_drops.tsv` (16,151 rows; 244 ONE-TIME
     flagged rows over 174 flags, 173 of which are already `LOCATIONS` flags). The count check is
     `matt_oracle.py --report` class C, report-only: his `enemy*` family is 413 slots today, not
     393, and the flag join is 169 both / 5 ours-only / 244 his-only. **No AP locations were added**
     — whether flagged enemy drops become checks is still the product ruling this item flagged.
   - Boss taxonomy (overworld / minidungeon / cave / catacomb / dragon / furnace golem) from our own
     map data, histogram-checked against his tags.
   - Reachability: use his 174-area graph only as a coverage counter. Author the logic ourselves.

## Operating rules

- Every fix removes an allowlist entry; a stale entry is a warning, so the lists only shrink.
- Run `python tools/matt_oracle.py --souls-rando-dir <checkout> --report --json out.json` before and
  after each PR and quote the class counts in the PR body.
- Delegable to Opus: items 1, 2, 5 sub-classes, 6. (Item 3 is done.)
  Items 4 and 7 need a product ruling per region or table.
