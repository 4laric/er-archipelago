# Handoff — 2026-07-25 evening (shop display, rune pricing, the lot-gates hunt)

Written for a session picking up cold. Same discipline as the handoffs before it: **verify COMMANDS,
not verify RESULTS**, everything labelled VERIFIED (and how) or INFERRED.

One thing learned the hard way today, and it is the same lesson the morning handoff carried:
**this document is where an assumption gets laundered into a requirement.** Its predecessor's
"START HERE" would have re-shipped a fixed bug and collapsed a working per-slot design into one
shared row. So: read the code, not this file's confidence. §5 lists what I got wrong, and it is long.

---

## 0. Summary

Shops are largely FIXED and confirmed in-game. Rune pricing shipped. The "checks gated behind another
region's flag" hunt produced working machinery, three standing screens, and **no bug** — the class
Alaric found is real but sits outside what the tooling can currently see, and we now know exactly
where it is not.

Heads: world `67d97c5`, client `9c4e3d9`.

---

## 1. Shops — what shipped, all confirmed in-game

Five separate defects, found in this order. Each was confirmed by Alaric in a live playtest.

| # | defect | fix |
|---|---|---|
| 1 | **The preview override was INERT.** `shopPreviewGoods` repoints a slot at a spare goods row and the client rewrote that row's FMG/icon — but NOTHING wrote `ShopLineupParam.equipId`, so the menu kept rendering the vanilla ware. Live since 2026-07-20. | client `c128ba0` — `er_logic::shop_repoint` + caller |
| 2 | **Own-world UNSELLABLE rewards** (gem/Ash of War) kept their vanilla preview, hit the real-good FMG guard, showed the vanilla name | world `e48505a` |
| 3 | **`shop_preview` latched DONE on a write of ZERO** — `extend_swap_overrides` returns 0 while the MSG repo is down and asks the caller to retry; it didn't, so the whole override was lost per session | client `16612fc` |
| 4 | 🛑 **shop_sell OWNERSHIP derived from `plan`** — `plan` holds only rows still needing a write, so on the idempotent re-run it is EMPTY and the pass "owns nothing". `shop_repoint` then dragged **354 rows** off their native sale. MY BUG, introduced with the ownership set. | client `a32f685` |
| 5 | ⭐ **`ShopLineupParam.nameMsgId` — the row LABELS ITSELF.** Rewriting equipId/equipType leaves that override pointing at the ware you replaced, and the MENU PREFERS IT. Hence `?ProtectorName?` over correct armour stats, and slots reading `Ash of War: No Skill` / `Note: Waypoint Ruins`. | client `8d2c153`, confirmed `cleared 21 row-level nameMsgId override(s)` |

⭐ **The diagnostic that cracked #5: the item displayed CORRECTLY IN THE INVENTORY.** Same id, same
FMG, right name — so nothing was wrong with the text, and every FMG theory died at once. **When a
name is wrong in ONE menu, check another menu before touching the FMG.**

⚠️ `ShopLineupParam` also carries its own **`iconId`** — same trap, NOT yet cleared. If a repointed
slot ever shows the wrong icon while the name is right, that is where to look.

**Spare pool criterion** (world `39a6d45`): the pool needed TWO properties and had one. SAFETY
(nothing else wears the row) vs WRITABILITY (**the FMG must already have an ENTRY**).
`extend_swap_overrides` only REDIRECTS an id already in a vanilla group — it cannot ADD one, and
`build_block`'s inject path needs ids above every vanilla id. So rows chosen *because* they had no
name were exactly the ones that could never get one → `?GoodsName?`. Fixed by also requiring
`g in texts`; an EMPTY entry (the `[ERROR]` render, what 8852 is) is ideal. Pool 83 → 65.

⚠️ **Still open:** FMG categories 20/24 (GoodsInfo/Caption) have NARROWER group coverage than 10
(Name). A run wrote `names=9/13, infos=2/13`. So a slot can show a correct AP name over a
`?GoodsInfo?` description. The filter only tests GoodsName; extending it to GoodsInfo.fmg.xml would
shrink the pool further and may not be worth it.

---

## 2. Rune pricing — shipped

World `3f3f590` + `c8151c8`, client `82d56e3`. A shop check keeps the price of the ware it USED to
sell, so a 3500-rune slot could sell a Golden Rune [1] — randomised reward, un-randomised cost, and a
slot nobody presses. Now rolled into `[0, 2x the rune's own worth]`.

⭐ **Worth is the PAYOUT, not the merchant price.** My first version priced off `GOODS_PRICE`, which
for a rune is a **10x markup** — Alaric saw 34191 / 78140 / 192430 on the shelf. `GOODS_PRICE // 10`
reproduces the published Golden Rune ladder exactly (200, 400, 800 … 10000 for [1]..[13]), and that
ladder is now a TEST, so the assumption cannot rot silently.

Scope is the whole rune family (Golden/Hero's/Lord's/Numen's), anchored so `Rune Arc` and the Great
Runes can never match. Frozen ON in `defaults.FROZEN_OPTIONS`.

---

## 3. Regions — what landed, and one thing REVERTED

* **Cave of Knowledge is Limgrave** (`a193ddb`). The EMEVD attribution put flags 18007000/18007020 in
  m10_01; the FLAG encodes m18_00, and `dungeon_regions.tsv` independently resolves m18_00 → Limgrave.
  ⭐ The two rows with a CONCRETE attribution were the WRONG ones; their six siblings had `map=PENDING`
  and fell to a default that happened to be right.
* **Nine misfiled dungeon checks** (`8d0a31b`) — m40–m43/m21_01 flags filed under m18_00. ⭐ Alaric:
  *"should be grace checkable"* — it was: every one of those maps holds ONE grace, and Fog Rift
  Catacombs / Belurat Gaol / Taylew's Ruined Forge / Messmer's Dark Chamber are all DLC. 9/9.
  🛑 **m40–m43 are the DLC small-dungeon ranges**; base-game catacombs/caves/tunnels are m30/m31/m32.
  ⚠️ I then claimed this "moves nine checks between regions". It moved NONE (`dc791c9` corrects it):
  gen_data already decodes the map from the flag for interior prefixes. The bad column only reached
  the layer-4 DESCRIPTION.
* **Grace-straddle screen: 44/117 → 39/98**, and ⭐ **only ~2 of the 19 cleared were real defects.**
  The rest was the oracle reporting its own bugs — see `gf-grace-straddle-suspect-the-oracle` memory.
  Duplicate grace NAMES (`f1f672a`, now keyed on the grace's flag) and an UNCAPPED nearest-neighbour
  (`c24490f`; `Altar South` "spanned four regions" because 12 checks 8.7–10.4 KM away anchored to it).
* 🛑 **`tile_pr` refusal REVERTED** (`ea5ccd7`, `8ff2e44`). Making an unanchored tile DEFAULT is right
  in principle (rule 1) and broke `test_gf_lod_tile_regions`: it quarantined THREE checks a prior fix
  had established real regions for. Two states — known/unknown — cannot express it. **The honest
  shape is THREE: known / GUESSED (regions the check but barred from progression) / unknown.** That is
  a design change, not a predicate. `tile_pr_strict` is in the file, unused and annotated;
  `test_gf_tile_anchor_coverage.py` pins the exposure (144 tiles, 640 checks resolved by a guess).
  ⚠️ Also reverted: grace-first regioning. It is the finer derivation, but the grace join is what the
  straddle screen compares AGAINST — region a check by its own grace and the oracle goes circular.

---

## 4. The lot-gates hunt — machinery built, NO BUG FOUND

**The target.** `f67050`, the cookbook Roderika leaves at Stormhill Shack, is regioned Limgrave
CORRECTLY — that is where the player stands, and the region drives the kick. But the pickup does not
EXIST until you rest at a grace in Liurnia. So the generator asserts a reachability it does not have.
**That is a missing ACCESS RULE, not a misregion**, and no region oracle can see it because the region
is right.

**Built:** `tools/datamine_lot_gates.py` (EMEVD scan → `greenfield/lot_gates.tsv`),
`datamine_msb_item_regions.py --emit-assets` (→ `treasure_assets.tsv`), `--probe`, and ⭐ **`--explain
FLAG`** — traces ONE check end to end in 0.05s. Build that FIRST next time; I built it seventh, after
five multi-minute full scans that each answered one question.

**Measured, and these are the numbers that matter:**

* `AwardItemLot` is RARE — 19 literal sites + 1 common event, total. Scripted awards are not the
  mechanism in ER.
* Of 3573 treasures, **only 230 have an asset EntityID**; 3017 are **EntityID 0**. An asset with no
  entity cannot be named by `EnableAssetTreasure`, so 230 is the WHOLE addressable population, not a
  shortfall.
* Of the old "186 unresolved" treasure sites, **148 are `ForceCharacterTreasure`** — CHARACTER
  entities, a different mechanism. Of the 38 real asset sites, 21 resolve.
* **`f67050`'s own asset has EntityID 0.** The asset join can never reach it. Its gating is something
  else.
* Triage of the 104 pairs: **0 cross-region, out of the 17 where BOTH sides resolve.** Only 17 gate
  flags decode to a region at all. Pinned by `test_gf_lot_gates_cross_region.py`, whose docstring says
  exactly that so a green tick is not read as a clean bill of health.

### 🟠 THE ONE OBVIOUS NEXT STEP
**The 148 `ForceCharacterTreasure` sites.** 宝死体 means "treasure CORPSE" — these are body pickups,
which is very likely Roderika's class. It needs a character-entity → lot join. `--emit-assets` already
searches `Part/Enemy`, and measured `Enemy=0` for TREASURE parts, so the link is NOT via
`TreasurePartName`; it will be the character part's own lot or an ESD.

Do NOT start by widening the EMEVD scan. Start with `--explain` on a known corpse pickup and look at
what the record actually contains.

---

## 5. Things I got WRONG today — do not inherit them

1. **Claimed "all nine Church of Pilgrimage checks now resolve to Weeping".** They did not; the Sacred
   Tear is still Limgrave. I replayed `_region_of_raw`'s rule instead of tracing the call — production
   takes the MSB branch. THREE separate times today I asserted an effect from a rule replay rather
   than an observation.
2. **Pushed `ea5ccd7` after running a FILTERED suite** (`-k "grace_key or straddle …"`) and called it
   green. The full suite was red and had been since the regen. "It passed the tests I thought were
   relevant" is "it genned on my one yaml".
3. **`cargo fmt --check` was RED on client main from `c128ba0` to `a32f685`** — my unformatted file —
   while I told Alaric CI was the gate without reading it. **Read the run.**
4. **Deleted four live functions** removing dead `_sense()`: my guard asserted the block CONTAINED the
   target, never that it was ONLY the target. Broke main. An AST check ("every called name resolves")
   is three lines and would have caught it.
5. **Five structural guesses about the MSB, all wrong**: `Parts/Asset`, `Parts/`, asset≈lot numbering,
   `StartDisabled` marks gated pickups, treasure parts might be Enemies. Each produced a confident
   EMPTY result that reads as "the data is not there". **Dump the layout before proposing a shape.**
6. **Reported 19 cross-region gates that were all artifacts** — comparing a raw region_map LABEL
   against a resolved region NAME. `Overworld m60_48_57_00` and `Mountaintops of the Giants` are the
   same place.
7. **Priced runes off the merchant price** (10x the payout) and shipped it.
8. **Two performance bugs of my own making**, each found by telemetry I had added the round before:
   an O(files×treasures) rescan, and "found" conflated with "resolved" so an EntityID-0 part triggered
   a full map index build (~3000 times; most of a 45-minute run).

**Fable's review (`637e0ff`) found four MORE paths that emitted confident-wrong rows**, each with a
repro: the direct part lookup trusting a filename over `<Name>`; my regex speedup disagreeing with the
DOM on nested tags; duplicate `<Name>` resolved by filesystem order; and a MEASURED-DEAD join left in
as an `or` that could fabricate a gate edge. **Ask Fable to review datamine tools before shipping
them.**

---

## 6. Working notes not in AGENTS.md / CONTRIBUTING

* ⭐ **Rust DOES install in the sandbox.** The 07-24 "sh.rustup.rs unreachable" finding was wrong; the
  blocker is `TMPDIR`/`HOME` on a 100%-full `/sessions`. Point them at `/tmp` — see AGENTS.md §4/2a,
  corrected in `71d22a0`. ~1.8 GB, will not coexist with the AP env; do the Rust half, delete it, then
  provision Python.
* `nearest_grace.tsv` now carries a **`grace_key`** column (the grace's own warpUnlockFlag). Seven
  display NAMES are shared by two distant graces — group on the key. gen_data reads it and
  `test_gf_grace_key_dependency.py` fails if a regen drops it.
* `csv.DictReader` takes the FIRST line as the header, and several greenfield tsvs open with a `#`
  comment. That silently makes every field name wrong and the join EMPTY — which reads as "the data is
  not there". Filter comments before DictReader.
* `check_integrity` read docstring BODIES as code (no triple-quote case), so prose apostrophes
  produced false delimiter warnings — 6 of 9 on the tracked tree. Fixed `3f6768d`. A pre-commit gate
  that cries wolf teaches you to `--no-verify`.
* **Co-check widening sheet** (`39872c4`): `--widen ARMOR_SET,MIXED_GEAR`. 321 projectable co-checks
  across 250 families (armor sets = 248). 🛑 42 DUP-ONLY families excluded — several lots on one flag
  awarding the SAME item, possibly the same pickup in two map versions, i.e. an unreachable co-check.
  Naive lot counting gives 363.

---

## 7. State

World `67d97c5`, client `9c4e3d9`. Full apworld suite green at last run (956 passed / 95 skipped / 0
failed) — **re-run it, do not trust this line.** Client CI:
https://github.com/4laric/from-software-archipelago-clients/actions?query=branch%3Amain

No regen is outstanding that I know of. `treasure_assets.tsv` (230 rows) and `lot_gates.tsv` (104
pairs) are committed and current.
