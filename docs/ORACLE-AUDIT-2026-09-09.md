# Oracle and quest-logic audit, 2026-09-09

Baseline: world `444487873e6597eb20e4e0033900d28fd526522d`, oracle pin
`dc643124be5990e5a9dbe29177ed26dea3642171`. Run the existing tool with `--report`;
on Windows use `python -X utf8` so redirected diagnostics remain printable.

The item-identity and missing-slot gates pass. The region report has 211 disagreements over
4,291 joined rows. The missable report has 67 oracle-only flags and 112 ours-only flags;
the two models do not define missability identically. These are investigation queues, not
populations to copy into the world. The unmodified bundle regeneration produced no content diff.

## Previous work and remaining gaps

- PRs #1497 and #1499 resolved the large identity discrepancy and classified missing slots.
  Classification did not recover the 26 unplaced common-event rewards: their regions still
  need evidence. The existing roadmap records that distinction.
- PRs #1496 and #1501 added region and missable review queues. Today's #1520, #1523 and
  #1524 already address player-reported key gates, region assignments and the Ymir chain.
- The graph coverage report counts 30 regions and 56 grace groups against 174 oracle areas.
  Counts do not establish equivalent access. Region availability, quest prerequisites,
  physical key functionality and permanent loss are separate claims.
- Issue #1321's Euporia conjunction remains blocked on an exact route/check population.
  The issue explicitly rejects selecting neighbouring flag numbers as a substitute.
- Issue #1085's extracted condition cones include unresolved roots. Those roots cannot
  become executable AND requirements: alternative paths and state transitions need review.

## Two verified omissions in the gift screen

`esd_gifts.tsv` records only negative collection latches for both rewards below. That is a
local fact about the award, not proof that the NPC offers it on first talk. The caller's
dispatch and the common event state manager impose additional requirements.

| Check | Award and caller evidence in the bundled v1.17 scripts | Lost prerequisite |
|---|---|---|
| Glintstone Kris, f400101 | Map lot 101010; t316211400_x37 -> x43 -> x47, and t316206000_x37 -> x44 -> x48, dispatch only at 3468. Common event 3479 advances to 3468 while alive (3460) after (3363 OR 7609) AND 9118 AND 1034509256. Award-site latch is 14009266. | Sellen's quest state and living dialogue path; t316211400's entry binds dead-state flag 3463, checked by x9. |
| Prosthesis-Wearer Heirloom, f400320 | Map lot 103200; t348006000_x36 -> x44 -> x45 and t348001500_x36 -> x43 -> x44 dispatch only at 4186. Common event 4199 advances 4185 -> 4186 while alive (4180) after 1050389255. t348006000_x60 sets that flag and consumes goods 8976. Award-site latch is 1050389257. | Millicent's post-needle state and living dialogue path; the entry binds dead-state flag 4183, checked by x9. |

The normal hand-reviewed `QUEST_GATED_FLAGS` set now protects these two rewards. No new
region, key, or client state write is inferred. Both ESD variants were checked; neither
is an independent free acquisition route. The regression checks the generated tags for
every AP row of each flag, while the existing missable world tests exercise actual item
rules for default, progression-only and off settings.

## Next useful passes

1. Continue the remaining gift queue by complete NPC family, following callers as well as
   award-site predicates. Preserve genuine first-talk and alternate death-drop routes.
2. Resolve region disagreements with our PlayArea, placement and route evidence. A nearest
   grace or oracle cluster alone does not establish which side of a locked door holds a check.
3. For reviewed quest rules, test separate states: home region alone, each missing key/region,
   all prerequisites, and every documented alternative including sweeps. A placement exclusion
   prevents a self-lock; it does not prove the check is reachable.

This pass establishes two placement fixes, not full parity or live-game validation.
