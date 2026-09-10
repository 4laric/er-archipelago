# Furnace golem check integration — 2026-09-10

Follow-up to the evidence-only PR #1540, tracked in #1543.

The generator now joins the eight c5170 encounters to all sixteen acquisition flags in
`drops.tsv`. `regions.tsv` records explicit project-region adjudications using the containing
MSB coordinate frame, elevation, nearby graces, existing region boundaries and player evidence.
These are region rulings, not newly measured PlayRegion collision volumes. Raw MSBs were not
rescanned here: all eighteen bundled event/param/FMG source hashes match the scan manifest.

The unmodified generator reproduced the committed tables with an empty git diff before edits.
The shared overworld fold was used on each containing MSB frame; part-name map IDs were not
used as coordinate frames. The version duplicate remains one encounter.

| Reward pair | Region correction |
|---|---|
| Crimson-Sapping / Furnace Visage | Both to Ancient Ruins (previously Scadu Altus / Rauh Base) |
| Viridian Hidden / Furnace Visage | Tear to Cerulean; visage already Cerulean |
| Glovewort / Furnace Visage | Tear to Cerulean; visage already Cerulean |
| Bloodsucking / Furnace Visage | Visage to Scadu Altus; tear already Scadu Altus |
| Oil-Soaked / Furnace Visage | Visage to Scadu Altus; tear already Scadu Altus |
| Crimsonburst / Furnace Visage | Restore missing visage in Scadu Altus |
| Deflecting / Furnace Visage | Both remain Gravesite |
| Cerulean-Sapping / Furnace Visage | Both remain Scadu Altus |

The missing visage (acquisition flag 2048467701) is lot 2048460701, the second row of the
2048460700 group awarded by m61_48_46_00 common-event 90005301 for entity 2248460291.
The older worldless audit searched for that individual lot and missed the base-group award.
Its exclusion and oracle missing-slot allowance are retired. The recovered row is appended,
preserving every existing check ID; the world gains one location, to 4,932.

Descriptors identify the golem rather than implying a ground pickup. Existing filler-sweep
behavior is regenerated normally; the added taxonomy does not create eight new sweep triggers.
The taxonomy uses eight death flags, never the sixteen separate acquisition flags.

This resolves placement and reward identity. It does not establish pot/crafting access
predicates for armoured or inactive golems, or change missable protection. Those require the
separate logic audit already recorded in the manual-review report. No live-game test was run.

Validation: 82 focused tests (including coverage and access census) passed after the
recovery, along with 33/33 fill-regression generations across 11 configurations and
the Bumper Stickers multiworld smoke. All 4,931 existing checks retain their IDs;
flag 2048467701 is appended as AP ID 7774642. Six existing checks change region.

Sweep audit by (trigger, acquisition flag): one added member (the restored visage),
zero lost, and 25 re-owned. Three visages follow their corrected regions; the other
22 remain within Shadow Keep as its remainder allocation rebalances. Crimsonburst
retains its existing map recovery and sweep owner. Total sweep links: 4,115.

Final retest after preserving the short-flag recovery: 188 focused tests and all
33 fill-regression generations pass. The remaining applicable generator suites pass locally.
