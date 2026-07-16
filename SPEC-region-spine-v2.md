# SPEC-region-spine-v2 — the 54-bucket region spine (bedrock-compat)

**Status: LANDED on `main` (merged 2026-07-12; originally developed on `feat/bedrock-compat`). This
document is the review table for the re-carve; the machine-readable source is
`greenfield/region_groups.py`.**

## What changed and why

Our 20 regions were a lossy collapse of buckets the game already separates. The game's own warp
menu (`BonfireWarpParam.bonfireSubCategoryId` == the runtime `play_region_id` the kick-watch sees)
has **54 explorable buckets**; our `PLAY2AP` covered 16 of them (overworld only) and everything
else was folded through hand tables and map-prefix majority votes. Bedrock's apworld ships region
locks over a finer taxonomy whose names Alaric agreed to adopt; the client enforces a foreign
world's locks by matching its lock item names against `"<Region> Lock"` over OUR region names
(er-logic `region_locks.rs`), so adopting his names where he has one makes his locks enforceable
with zero client changes.

**One source now.** `greenfield/region_groups.py` holds the bucket->region grouping and the names.
Consumers: `gen_data.py` (PLAY2AP + the generated `eldenring/region_play_ids.py`),
`features/area_locks.py` (imports the generated module; its hand REGION_PLAY_IDS table is GONE —
it had drifted: stale `Raya Lucaria Academy`/`Leyndell` keys, 6940/6950 bucketed backwards),
`tools/gen_region_locks.py` (bakes the client table), `tools/datamine_dungeon_regions.py` and
`tools/map_region_oracle.py` (the grace-join oracle fold layer).

**Derived, not pinned.** All of these now derive from the spine with NO new hand fallbacks:
- `REGION_OPEN_FLAGS` — every one of the 31 regions resolves a front door from its own graces;
  `_DLC_OPEN_FALLBACK` and the `_GRACE_PR_REGION` split-map table are deleted; gen hard-fails if
  `REGION_OPEN_PENDING` is ever non-empty.
- The m61 tile->region table (79 hand rows) is now grace-anchor NN like m60's, reproducing 77/79
  hand rows; the 2 disagreements are curated overrides guarded against redundancy.
- `dungeon_regions.tsv` regenerated (90 maps; picked up m30_18 — previously mis-labelled into
  Limgrave — and m25_00 Fog Rift Fort/Finger Birthing Grounds).
- The flag-prefix map recovery learned prefixes 11/12/20/21/35, so the multi-region catch-all
  labels (`'Eternal Cities & Underground Rivers'`, `'Leyndell / Roundtable / Shunning-Grounds'`,
  `'DLC Interior'`, `'Divine Tower'` — whose rows are actually m35!) stopped deciding regions;
  two of those labels are deleted from REGION_MAP outright.

## The table (bucket -> region)

`"` = same as the row above (a deliberate multi-bucket region). Open flag / checks are per REGION.

| play_region | game's own bucket name | region (v2) | open flag | graces | region checks |
|---|---|---|---|---|---|
| 61000 | Limgrave | Limgrave | 73100 | 21 | 294 |
| 61001 | Stormhill / N. Limgrave (Margit, Divine Tower of Limgrave) | " | " | 8 | " |
| 18000 | Stranded Graveyard / Chapel of Anticipation (tutorial; = randomStartAreaId) | " | " | 2 | " |
| 61002 | Weeping Peninsula | Weeping | 73102 | 18 | 153 |
| 62000 | Liurnia of the Lakes | Liurnia | 73202 | 52 | 543 |
| 62001 | Eastern Liurnia / Bellum Highway (Dectus, Church of Inhibition) | " | " | 5 | " |
| 62002 | Moonlight Altar (SW Liurnia) | " | " | 3 | " |
| 39200 | Ruin-Strewn Precipice (Magma Wyrm Makar) | " | " | 3 | " |
| 63000 | Altus Plateau (core) | Altus | 73204 | 19 | 334 |
| 63002 | W. Altus / Auriza / Capital Outskirts approach (Divine Tower of West Altus, Sealed Tunnel) | " | " | 10 | " |
| 63003 | E. Altus / Forbidden Lands / Grand Lift of Rold (Divine Tower of East Altus, Hidden Path to Haligtree) | " | " | 5 | " |
| 63001 | Mt. Gelmir (+ Volcano *surface* caves: Seethewater, Volcano Cave) | Mt. Gelmir | 76350 | 12 | 213 |
| 16000 | Volcano Manor (Rykard interior) | " | " | 8 | " |
| 64000 | Caelid | Caelid | 73207 | 25 | 310 |
| 64001 | Dragonbarrow (Sellia Hideaway, Divine Tower of Caelid) | " | " | 12 | " |
| 64002 | Swamp of Aeonia (Heart of Aeonia) | " | " | 4 | " |
| 65000 | Mountaintops of the Giants — West (Zamor, Castle Sol) | Mountaintops of the Giants | 73017 | 10 | 289 |
| 65001 | Mountaintops — East / Forge of the Giants (Fire Giant, Church of Repose) | " | " | 7 | " |
| 65002 | Consecrated Snowfield (Ordina, Yelough Anix) | " | " | 7 | " |
| 10000 | Stormveil Castle | Stormveil | 71003 | 7 | 119 |
| 14000 | Raya Lucaria Academy | Raya Lucaria Academy | 71402 | 4 | 80 |
| 11000 | Leyndell, Royal Capital | Leyndell | 71102 | 9 | 151 |
| 11050 | Leyndell, Ashen Capital (post-burning) | " | " | 6 | " |
| 19000 | Fractured Marika (final arena) | " | " | 1 | " |
| 35000 | Subterranean Shunning-Grounds | Sewer | 73501 | 5 | 88 |
| 15000 | Elphael, Brace of the Haligtree (Malenia) | Haligtree | 71501 | 5 | 121 |
| 15001 | Miquella's Haligtree | " | " | 4 | " |
| 13000 | Crumbling Farum Azula | Farum Azula | 71303 | 11 | 99 |
| 12010 | Ainsel River / Nokstella | Ainsel River | 71211 | 3 | 112 |
| 12011 | Lake of Rot | " | " | 2 | " |
| 12012 | Ainsel River Depths / Astel | " | " | 5 | " |
| 12020 | Siofra River (Ancestral Woods, Night's Sacred Ground) | Siofra River | 71222 | 6 | 184 |
| 12070 | Siofra River Bank / Worshippers' Woods | " | " | 4 | " |
| 12030 | Deeproot Depths | Deeproot Depths | 71231 | 6 | 78 |
| 12050 | Mohgwyn Palace | Mohgwyn | 71251 | 4 | 84 |
| 6800 | Gravesite Plain (DLC entry overworld) | Gravesite | 76800 | 17 | 369 |
| 6820 | Castle Ensis | Ensis | 76821 | 3 | 13 |
| 6830 | Cerulean Coast | Cerulean | 76831 | 5 | 44 |
| 6840 | Charo's Hidden Grave / Lamenter's Gaol | Charo's | 76841 | 2 | 14 |
| 6850 | Jagged Peak | Jagged Peak | 76840 | 3 | 31 |
| 6851 | Foot of the Jagged Peak / Dragon Communion Altar | " | " | 2 | " |
| 6860 | Abyssal Woods | Abyssal | 76860 | 5 | 30 |
| 28000 | Midra's Manse (Abyssal Woods interior) | " | " | 4 | " |
| 6900 | Scadu Altus | Scadu Altus | 76900 | 18 | 166 |
| 6920 | Scaduview / Hinterland (Shadow Keep environs) | Scaduview | 76935 | 6 | 18 |
| 21000 | Shadow Keep — Main Gate | Shadow Keep | 72102 | 2 | 258 |
| 21001 | Shadow Keep — Church District / Sanctum | " | " | 4 | " |
| 21010 | Shadow Keep — Storehouse / Messmer's Dark Chamber | " | " | 8 | " |
| 6940 | Rauh Ancient Ruins | Ancient Ruins | 76940 | 6 | 37 |
| 6950 | Rauh Base | Rauh Base | 76912 | 5 | 51 |
| 20000 | Belurat, Tower Settlement | Belurat | 72001 | 4 | 95 |
| 20010 | Enir-Ilim (Gate of Divinity — DLC goal) | Enir Ilim | 72012 | 6 | 85 |
| 22000 | Stone Coffin Fissure | Stone Coffin | 72201 | 5 | 20 |
| 11100 | Roundtable Hold (Table of Lost Grace) | Roundtable Hold | — | 1 | 361 |


Roundtable Hold (11100) is the HUB — never a spoke, never gated. Buckets 0 and 10010 are
non-explorable system ids (REGION_ID_MAP.md).

## Bedrock name adoption

Adopted verbatim (his lock item == `"<our region> Lock"`): Weeping, Stormveil, Liurnia, Altus,
Mt. Gelmir, Caelid, Haligtree, Farum Azula, Mohgwyn, Sewer, Gravesite, Ensis, Cerulean, Charo's,
Jagged Peak, Scadu Altus, Shadow Keep, Ancient Ruins, Rauh Base, Belurat, Stone Coffin, Abyssal,
**Enir Ilim** (note: game spells it "Enir-Ilim"; his lock item has no hyphen, interop wins).

NOT adopted (documented so nobody re-litigates silently):
- **Redmane Lock** — Redmane Castle has no play_region of its own (m60 tiles inside 64000); the
  kick cannot gate it. Same class as Ellac/Recluses' below.
- **Volcano Lock** — bucket 16000 (Volcano Manor interior) exists, but the Manor sits ON Mt.
  Gelmir and Rykard is Gelmir's arena major; splitting it would leave Gelmir major-less for a
  ~8-check region. One region: Mt. Gelmir = 63001 + 16000.
- **Ashen Lock** — post-burn Leyndell (11050). Its checks are excluded as dead content
  (2026-07-08 decision) and its graces are burn-gated; it folds into Leyndell.
- **South West / South East / North Underground Locks** — his three-way underground grouping does
  not map onto the game's seven underground buckets; we keep bucket-true regions (Ainsel River /
  Siofra River / Deeproot Depths / Mohgwyn) with our names.

## The two physically un-gateable folds (measured)

The kick-watch works on play_region; a place that shares a bucket with its parent CANNOT be
separately gated. Do not invent a mechanism:
- **Ellac River** — graces 76812 (m61_47_43), 76830 (m61_47_41) -> bucket **6800** = Gravesite.
- **Recluses' River** — graces 76917 (m61_50_45), 76918 (m61_50_44) -> bucket **6900** = Scadu
  Altus (6900 also holds Fog Rift Fort — REGION_ID_MAP.md "Shared buckets").
Bedrock's "Ellac Lock" / "Recluses' Lock" therefore have no enforceable geometry here; the client
reports such a lock item as un-gateable rather than pretending.

## Notable placements the review should eyeball

- **Metyr / Cathedral of Manus Metyr.** The Cathedral surface is Scaduview (6920), but Metyr's
  ARENA is m25_00 whose own grace the game buckets **6900 = Scadu Altus** (MSB truth 510550 ->
  m25_00). Her remembrance check is therefore a Scadu Altus check, and the Hole-Laden-Necklace
  gate keeps `"Scadu Altus"` as its parent.
- **Scaduview is its own region** (6920, 18 checks). The old "fold into Shadow Keep, only
  reachable through the Keep" curation predates lock-lit grace bundles; folded in, its back-exit
  grace would have become the Keep's numerically-first overworld front door.
- **Stormveil's front door moved 71002 -> 71003**: two graces on the m10 map carry bucket 61001
  (Stormhill) in the game's own menu, so they now ride Limgrave's bundle — which matches what the
  kick-watch would enforce at those graces.
- Old front doors that were latently WRONG and are now fixed by derivation: Scadu Altus was
  76834 (a **Cerulean** grace), Ancient-Ruins-of-Rauh was 76803 (a **Gravesite** grace), Abyssal
  was 72801 (the **Midra's Manse interior** grace).
- **Valiant Gargoyles (510100) -> Siofra River** and **Mimic Tear (510340) -> Siofra River**: both
  hand pins previously said "Nokstella" in comments; the arenas are the Siofra Aqueduct / Night's
  Sacred Ground (Nokron). Verify in-game.
- `'Land of Shadow (DLC)'` / `'DLC Dungeon'` labels still fall back to **Gravesite**; rows with
  usable maps/tiles resolve finer first. `'DLC Legacy Dungeon'` -> Belurat unchanged.

## MajorBoss coverage (regen-time invariant still hard-fails)

The un-collapse moved four arena majors into split-out regions (Rennala -> Raya Lucaria Academy,
Morgott -> Leyndell, Rellana -> Ensis, Putrescent Knight -> Stone Coffin), so their parents got
curated MAJOR_BOSS_EXTRAS again (all existing in-region checks, validated by the invariant):
Liurnia = Magma Wyrm Makar (510260), Altus = Godefroy the Grafted (1039507100), Sewer = Mohg the
Omen (510250), Gravesite = Blackgaol Knight (530820, MEDIUM).

**Four regions have NO MajorBoss check**: **Cerulean, Charo's, Rauh Base, Scaduview**. No reliable
in-region major-boss drop exists in current data (Cerulean's named bosses drop nothing that is a
check; Charo's gaol boss likewise). The progression_surface feasibility ladder covers them (locks
for those regions place on the next rung); flagged here rather than inventing flags.

## num_regions semantics shift

`num_regions: N` still keeps the first N of SPINE (or N rolled) + the goal region — but the spine
is **31 regions now (17 base + 14 DLC), goal = Leyndell** (the capital is first-class again; the
capital-ending checks live there, and `leyndell_runes_required` now reads "on top of the
**Leyndell** Lock"). The same N yields a smaller world than v0.2's 20-region spine — e.g. N=3 was
Limgrave+Weeping+Stormveil+goal(Altus incl. the capital); it is now Limgrave+Weeping+Stormveil
+goal(Leyndell only). Players' yamls keep generating; the meaning of mid-range N shifts toward
"more, smaller regions". Sewer/Raya/Leyndell/the DLC splits also mean base-game N in `spine`
order reaches the capital two rungs later than before.

## Scadutree blessing floors (feel values — review)

Per-region now (features/scaling.py): Ensis/Cerulean/Charo's = 2 (were inside Gravesite's 1),
Stone Coffin = 10 (keeps its old per-bucket override), Scaduview = 10, Rauh Base = 10. Same
"~3-4 under vanilla expectation" rule; playtest like the boss scaling tiers.

## Known-red tests (deliberate — a tuning decision, not a regression to hide)

`test_gf_filler_economy_floor.py::{FillerEconomyFloor,DefaultRecipeEconomyFloor}::
test_early_weapon_upgrade_is_affordable` fail on this branch: with 31 finer regions,
`num_regions: 4 (rolled)` keeps a smaller slice of the world, and the early-sphere Smithing
Stone [1] supply lands at 20 where the derived floor wants 24 (6 stones to +3 at a 25% clear
rate). The floor is DERIVED and the shape change is the point of the surgery, so silently
re-tuning the stone supply here would launder a real design consequence into a green test.
Decide: widen the stone_ramp top-up to be sphere-aware (it currently measures its deficit
against global supply — the exact blind spot this suite documents), or accept the leaner early
economy. Everything else in the suite (682 tests) passes.

## Sweep coverage note

Boss sweeps re-derive per region (231 triggers, 30 regions). The three seated DLC overworld divvy
bosses (Ghostflame Dragon / Furnace Golem / Blackgaol Knight) now divvy whatever fine region their
m61 map-prefix majority resolves to; small DLC regions without a legacy-class boss (Cerulean,
Charo's) simply have no convenience sweep — never load-bearing, but worth a playtest look.
