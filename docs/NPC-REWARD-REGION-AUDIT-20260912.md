# NPC reward region audit — 2026-09-12

Scope: quick screen of the 55 distinct dialogue-award target flags in
questline_dag.tsv against current generated locations, after the Black Knifeprint
fix in PR #1555. Twelve additional targets have a differing prerequisite-source
region. A prerequisite's region is a lead, not proof of the reward's location.

Ran tools/matt_oracle.py against the local matt-oracle-reference checkout.
Its independent region queue corroborates disagreement for ten of the twelve;
item-identity/missing-slot gates pass. No upstream labels or descriptions are
copied here. The oracle's regional clustering is not a placement authority.

## Corrections implemented in PR #1555

| Flag | Reward | Current | Corrected | Our evidence |
| --- | --- | --- | --- | --- |
| 400320 | Prosthesis-Wearer Heirloom | Haligtree | Caelid | gen_data's existing quest adjudication traces needle handover -> state 4186 -> lot 103200; both relocating NPC script copies include the award. region_map.csv instead assigns Haligtree by flag prefix. |
| 400391 | Carian Inverted Statue | Roundtable Hold | Liurnia | t106016000_x37 awards lot 103910; the quest DAG resolves its prerequisite to Liurnia. The raw region pipeline labels the lot globally unplaced; x28/x29 use the local handover latch 1034509421 in m60_34_50. |
| 400600 | Golden Lion Shield | Enir Ilim | Shadow Keep | gen_data already traces Freyja's letter flag 21019371 to x52 / lot 106000 in t417002101; flag_lots has no independent death-drop lot for this flag. GLOBAL_RECOVER currently pins the reward to Enir Ilim. |
| 400722 | Gourmet Scorpion Stew | Gravesite | Belurat | gen_data traces Grandam's x39 -> x48 -> lot 107220 with flags 20009286/20009290; m20_00 event 20000702 governs refusal. Current manual region override is Gravesite. |

All four were independently queued by the Matt oracle. Their generator assignments
are now corrected and regression-tested; they have not been live-verified.

## Remaining screen hits — not adjudicated as errors

| Flag | Reward | Current | Reason to avoid an automatic move |
| --- | --- | --- | --- |
| 400070 | Tonic of Forgetfulness | Altus | Multiple dialogue owners/source regions; resolve actual acquisition alternatives. |
| 400080 | Irina's Letter | Weeping | Prerequisite source says Leyndell; oracle does not flag the current assignment. |
| 400090 | Volcano Manor Invitation | Mt. Gelmir | Relocating NPC scripts; distinguish invitation handover from later residence. |
| 400103 | Starlight Shards | Raya Lucaria Academy | Multiple Sellen scripts and differing source regions. |
| 400260 | Glowstone | Caelid | A dialogue-source region alone cannot locate the reward. |
| 400281 | Scepter of the All-Knowing | Leyndell | A Roundtable prerequisite does not prove a Roundtable acquisition. |
| 400610 | Cross Map | Gravesite | Multiple lots and source regions; oracle does not flag the assignment. |
| 400612 | Furnace Visage | Shadow Keep | Shared NPC dialogue copies and contradictory source regions. |

Do not batch-reassign these from prerequisite regions or script folder names.
For each fix, resolve the award's state and NPC placement, change the generator,
regenerate, and test the distinct acquisition rather than the item name alone.
The four corrections above were subsequently implemented at the user's request;
the remaining eight screen hits are unchanged.
