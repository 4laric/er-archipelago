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

   **The review queue is built** (`--region-queue`, 2026-09-08). 218 rows in
   `greenfield/evidence/oracle-region-queue.tsv`, each with `status` (open / confirmed-ours /
   moved), `reviewer` and `note`. The check browser has an **Oracle region review** facet and the
   player review notebook a queue view; both put OUR evidence beside each row — assigned region,
   the derivation step that assigned it, map tile, nearest grace and the region that grace maps to
   (47 rows have a grace candidate that differs from the assignment), and the
   `check_region_second_opinion.tsv` wiki row where one exists (12 rows). A reviewer rules in the
   notebook, downloads the notebook backup, and `tools/apply_oracle_verdicts.py` writes the
   verdicts back into the tsv. 🛑 The queue file carries nothing of his: it records only THAT a
   second source disagrees for that flag. **Still open:** working the 218, then the ladder fixes
   for the `moved` rows, then the escalation to FAIL.

5. **Missable tagging.**
   Semantics differ, so no blanket gate. Two clean sub-classes: mark the three Furnace Golem crystal
   tears (65430/65450/65460) missable; reconsider 60510 (Talisman Pouch) which we call questline and
   he calls a plain boss drop. Target: raise `missable_locations.py` toward his 168 joinable rows
   with a curated fail-list.

   **The review queue is built** (`--missable-queue`, 2026-09-08), on the SAME mechanism as item 4
   rather than a parallel one. The bare tag disagreement is ~68 joinable flags, which is not a
   signal — the two models draw the missable line in different places. So a row is queued only on
   the three-way intersection: he tags it missable, our `MISSABLE_LOCATIONS` does not, AND our own
   `questline_conditions.tsv` shows a `DIALOGUE_STEP` / `NPC_STATE` / `ITEM_POSSESSION` root on the
   award site. That is **29 flags / 35 rows** in `greenfield/evidence/oracle-missable-queue.tsv`,
   each with `status` (open / confirmed-not-missable / missable), `reviewer` and `note`. The check
   browser has an **Oracle missable review** facet and the notebook a matching queue view; both put
   OUR evidence beside each row — our current missable status, the condition rows and what each one
   waits on (named with our own `flag_names`), the quest features that mention the flag, and the
   region. `tools/apply_oracle_verdicts.py --queue missable` writes the verdicts back, refusing a
   `missable` verdict that does not name a mechanism (`limited-consumable` / `killable-npc` /
   `questline-progress`), since gen_data's missable classes are a closed vocabulary.
   🛑 The queue file carries nothing of his: it records only THAT a second source disagrees.
   **Still open:** working the 29, then applying the `missable` rows through the normal derivation
   in `greenfield/gen_data.py`, then the two named sub-classes above (65430/65450/65460, 60510).

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
   - ~~Boss taxonomy (overworld / minidungeon / cave / catacomb / dragon / furnace golem) from our own
     map data, histogram-checked against his tags.~~ **DONE**: `tools/gen_boss_taxonomy.py` ->
     `tables/boss_taxonomy.py`, 253 bosses over 11 classes, printed as report class **D**.
     Evergaols are EMEVD-derived (the arena-seal common-event family), not a hand-typed list.
     Furnace golems are now derived too (#1540/#1543): eight c5170 encounters, sixteen rewards,
     joined from MSB entities through common event 90005301 to the full item-lot group.
     The taxonomy contains 253 encounters. The earlier c4900/no-roster claim was incorrect.
   - ~~Reachability: use his 174-area graph only as a coverage counter. Author the logic
     ourselves.~~ **DONE (counter only)**: report class **E** prints `our graph reaches 30 regions
     / 56 grace-warp groups; his reaches 174 areas`, his side computed at run time and never
     committed. The counter is the whole of it — authoring finer logic of our own is still open,
     and the ratio is what says how much finer it would have to get.

8. **Pin bump, 2026-09-22.** The workflow pin moved from `dc643124` (2026-09-02) to `61014252`
   (2026-09-22). Between them his slot table added and removed **nothing**; 620 slots moved
   between his areas as he split 174 areas into 363, and 25 tags changed. Both gates were green
   at both pins with the same allowlists. Effects: the region queue went 196 -> 177 rows (21
   left on the finer partition, 2 arrived), the missable queue is unchanged at 30 gated rows.
   His Tarnished-Edition content (spiritspring stones, the new field items) landed in
   `itemevents.txt` and `annotations.txt`, not in `itemslots.txt`, so the oracle still sees none
   of it and his 19 `tarnished`-tagged slots stay excluded. Not bumped: nothing since 2.7.1.0 is
   comparable yet.

   **What the bump surfaced, and the fact that matters more than any count in this file.** His
   2026-09-14 commit "External item rando data structures" adds `ExternalItemPreset` /
   `ExternalLocationData` to his randomizer, with a `FromArchipelago(slotData, scoutedLocations)`
   constructor under `#if ARCHIPELAGO`: the randomizer itself consumes an AP seed, maps each AP
   location onto one of his slot keys by `LocationScopeKey` plus lot/shop param ids, and writes
   the permutation. That is the Bedrock client path, in his tree, keyed on the same table this
   oracle reads. Read-only for us under the licence; recorded here so the next "are we chasing
   parity by hand" discussion starts from it.

9. **Uncovered rows (report class I, 2026-09-22).** Every class above starts from HIS slots. This
   one starts from OURS: 640 of our 4,932 rows (13%) have no Event-scope counterpart in his table
   and get no second opinion from any section. Section A's 99.8% is agreement over the other
   4,292 only. By class from our own names and flag bands: **426 shop rows** whose flag a shop
   DebugText line of his names (a counterpart keyed on the shop row, the cheap extension: join
   them into section A), **159 sweep-granted rows**, **32 gestures** (a class he does not model),
   13 common-event 400k rows, 10 other. `--report` lists the 10.

10. **Missable queue widened (2026-09-22).** Item 5's three-way intersection excludes, by
    construction, the case that strands a seed: he tags a flag missable and OUR extractor sees no
    losable root at all, i.e. we may have missed the gate. Those **70 rows** are now queued under
    a second basis, `second-source-missable-disagrees-no-local-gate`, with an empty
    `our_conditions`, beside the 30 gated ones. A reviewer rules them from the award site's
    ESD/EMEVD callers, not from the absence of a row.

## Ownership (read before treating a queue as owed work)

**2026-09-22: handed off.** Per-check accuracy work is stopped. [HANDOFF-CHECK-ACCURACY.md](HANDOFF-CHECK-ACCURACY.md)
is the entry point for anyone picking it up and states the shipping bar: sweep-granted is
reachable, everything else is play at your own risk.

The region queue holds **143 open rows** and the missable queue **100 open rows** as of
2026-09-22. Every verdict recorded so far was made by Codex during evidence passes; no human has
worked either queue. **Neither queue is a commitment.** They are intake for a reviewer who has not
been assigned, and until one is, a row in them is a question nobody has been asked. Until an
owner is named, the working accuracy bar is: region-level logic is authoritative, per-check
placement is best effort and corrected from reports, quest-gated items are filler until a gate is
proven. If that bar changes, this section is where the owner and the date go.

## Operating rules

- Every fix removes an allowlist entry; a stale entry is a warning, so the lists only shrink.
- Run `python tools/matt_oracle.py --souls-rando-dir <checkout> --report --json out.json` before and
  after each PR and quote the class counts in the PR body.
- Delegable to Opus: items 1, 2, 5 sub-classes, 6. (Item 3 is done.)
  Items 4 and 7 need a product ruling per region or table.
