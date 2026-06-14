# ER Archipelago — TODO

Actionable backlog. Living doc; see HANDOFF.md for current state and SPEC-*.md for designs.

## 1. DLC enemy randomization — engine port (the v0.8 → v0.11.4 enemy delta)

Ref: SPEC-reverse-engineer-rando (this session's RE notes). Our fork is v0.8; DLC enemy
handling lives in the shipped v0.11.4 `.exe` + plaintext config, not in public source.
Flag-collision check is DONE and CLEAR (2026-06-13): fork synthetic bands are 11.30M–11.70M
(writable/temp) + 1.4M–1.5M (helper entities); DLC DefeatFlags are 20M+ (low) and ~2.05B
(field bosses) — no overlap. Safe to wire DLC flags to AP locations.

CORRECTION (2026-06-13): enemy_rando + enable_dlc by itself WORKS -- playtest 2 shuffled DLC
bosses/gear fine (Messmer wearing Rellana's armor). The IndexOutOfRange at
EnemyRandomizer.cs:8202 (scaling: `EldenSoulScaling[section-1]`) is triggered by the NEW Tier A
swap toggles -- `swap_multiboss` and/or `boss_runes_match` (swaprewards) -- against DLC enemies,
a combo v0.8 never saw (it predates DLC; the crash log shows the swaprewards "no runes to move
... Grafted Scion" line right before). So base+DLC enemy rando is FINE; the swap/rune
sub-toggles are NOT DLC-safe yet -- keep them OFF for DLC bakes until guarded. `impolite` is
probably innocent (aggression only). The `Unknown event map target m61_*` lines are benign
warnings (scripting won't apply there), not the crash.

Steps (prereq order):
- [ ] Extend `ScalingEffects.EldenSoulScaling` + `getScalingSections` to cover DLC tiers
      (Scadu Altus / m61 etc.) so scaling doesn't index past the table.
- [ ] Pull the mandatory DLC param/FMG constants from `elden_ring_artifacts/vanilla_er/`:
      `dlcGameClearSpEffectID` (engine forces it to -1 when anything randomizes) and the DLC
      NPC-name FMGs (`NPC名_dlc1` / `NPC名_dlc2`) for swapped-enemy healthbar names. Mandatory
      bake steps once DLC enemies are in the pool, or healthbars/clear-gate misbehave.
- [ ] Port DLC enemy handling into the v0.8 engine (the ~21 extra `dlc` code sites: DLC map
      enable list, placement guards). Reimplement in our own C# — do NOT vendor his decompiled
      source. Validate roster against his `enemy.txt` locally only.
- [ ] Add the area-silo system (`AreaSilo`/`AreaSiloType{None,DLC,Region}`, `IsDlc()`); key the
      enemy permutation bucket on `(class, silo.Type, silo.Index)`. Stamp areas DLC-vs-base by
      map prefix (DLC = m20,21,22,25,28,40,41,42,43,45,61; base = m10–19,30–39,60).
- [ ] Wire `dlc_enemy_silo` slot option (options.py → slot_data → `opt["dlcsilo"]` + set
      `opt["dlc"]`). Default `separate`. Plumbing is trivial (Tier-A pattern) but INERT until
      the engine port above — ship together so the toggle isn't a lie.
- [ ] Confirm DLC boss `DefeatFlag`s are in the client's polled flag set (apworld is
      DLC-complete, so locations likely exist; verify the poll covers the new ranges).
- [ ] me3/ModEngine profile: add `RandomizerCrashFix.dll` load entry (reference download, do
      NOT rebundle) — recommended once base+DLC enemies mix.

## 1b. DLC map fragments — RESOLVED 2026-06-13

Confirmed working in the preflight-PASS playtest: DLC map items `2008600-2008604` were
granted and their reveal flags `62080-62084 SET` (alongside the base maps), and the DLC
maps appear in the Key Items inventory. Earlier doubt was unfounded. No action needed.

## 2. Fix starting class randomization (CharacterWriter)

Ref: HANDOFF.md "Randomizer AP-path specifics" — CharacterWriter is WIRED BUT DISABLED; it
corrupts regulation.bin → boot crash, because the fork's ER code predates the DLC-era
`CharaInitParam` definition. Low personal interest but expected to be a demanded feature.

Steps:
- [ ] Diff the fork's `CharaInitParam` def/usage against `vanilla_er/vanilla_er/CharaInitParam.csv`
      (the gold param dump) to find the field/layout drift that corrupts the write.
- [ ] Fix the def/write in the randomizer (likely SoulsFormats/SoulsIds param layout or
      CharacterWriter field set), so the written regulation boots.
- [ ] Re-enable the `random_start` path in ArchipelagoForm (currently `erRandomStart=false`).
- [ ] Test: boot a seed with `random_start` on; confirm no crash and loadouts actually vary.
      Verify the GUI sub-options (two-handing / one-handable / stat-tweak) if exposing them.

## 3. Bake: read the connect slot name from the Players yaml -- DONE 2026-06-13

build.ps1 -Bake now reads `name:` from the (first) Players yaml and passes `slot=<name>` to the
bake; Program.cs parses `slot=` -> `apForm.AutoConnectSlot`; ArchipelagoForm.cs uses it (falls
back to "Player1" if absent). So the yaml `name:` drives the bake slot. Player is now `Alaric`.
- [ ] Remaining: multi-yaml case picks the FIRST yaml (fine for solo dev loop; for a real
      multi-player local bake, would need to specify which slot is "yours").

## 4. Crafting Kit: "start with" option -- DONE 2026-06-13

`crafting_kit_option` now has `option_start_with = 3` (options.py): precollects the Crafting
Kit at spawn (a copy also stays in the pool, like bell/physick/maps). Needs a regen to take
effect. Not yet in-game tested, but same proven precollect path as bell/physick.

## 5. map_option=give auto-completes every map-pillar check at start (decide if intended)

A map-pillar location's guarding flag IS its reveal flag (e.g. Gravesite Plain =
`62080`). With `map_option: give`, the client sets the reveal flag when granting the map, so
flag-polling immediately fires that pillar's check and dumps its (randomized) item to the
player at spawn -- that's where the free Academy Glintstone Key / Stonesword Keys /
Remembrance of the Fire Giant came from in the 2026-06-13 playtest. Coherent but a free
item dump + a multiworld check leak.
LEAK FIXED apworld-side 2026-06-13: `_is_location_available` now returns False for `map=True`
locations when `map_option.value == 1` (give), so map-pillar pickups are no longer AP checks --
the reveal flag fires at spawn but there's no bound location, so nothing leaks. Maps are still
precollected (given + revealed). Needs a regen. (Note: this drops ~24 checks and makes the
"Map" important_locations class a no-op under give -- both expected.)

OPTIONAL POLISH (the original "flip flags without granting items" idea -- removes the map
FRAGMENT items from inventory clutter; needs a client change, untested-compilable here):
- [ ] apworld: under give, also stop precollecting the map items; emit "reveal_all_maps" in
      slot_data instead.
- [ ] client: on connect, if reveal_all_maps, set the reveal flags directly (reuse
      kMapUnlockFlags in GameHook.cpp) -- no item grant. Net: revealed, zero map items in bag.

## 6. Double-grant: own-world GOODS bought from a shop

ROOT CAUSE (traced 2026-06-13). Affects every own-world GOOD sold in a shop (runes are just the
visible case -- they stack). Chain:
1. ArchipelagoForm.cs:515-545 (the ELSE branch) places ER own-world GOODS in shops via
   `writer.AddSyntheticCopy(original, replaceWithInArchipelago: original, ...)` -- a FUNCTIONAL
   copy of the real item, on purpose: shops can't suppress-on-pickup (see the comment at
   ArchipelagoForm.cs:499-503), so they sell a realistic item to avoid a lingering placeholder.
2. Buying it: the AddItemFunc detour does NOT intercept shop purchases, so the functional copy
   lands in inventory (= grant #1).
3. The purchase sets the slot's guarding flag -> FLAG POLLING sends the check
   (ArchipelagoForm.cs:699: "detects checks that bypass the AddItemFunc detour (shop
   purchases...)") -> items_handling=7 echoes the own-world item -> client gibs it (= grant #2).
   (Non-GOOD shop items use the placeholder branch at ~497, so they don't double; foreign-player
   shop items sell a junk token, so they don't double. It's specifically own-world GOODS.)

FIX OPTIONS (a real trade -- the shop-can't-suppress constraint is the crux):
- [ ] Proper: un-stub removeFromInventory (HANDOFF "unfixed" list), then sell a non-functional
      PLACEHOLDER for own-world shop goods too (route the ELSE through AddSyntheticItem like the
      non-GOOD branch). Purchase -> placeholder (client removes it) + echo -> real item = single.
- [ ] OR client-side: when flag-polling fires a SHOP check whose item is own-world, suppress the
      echo gib for it (the purchase already granted it). Needs the client to know the check came
      from a shop purchase (tag shop locations in apconfig?).
- [ ] Interim (cheap, accept a junk token): drop the GOODS exception so own-world shop goods use
      the placeholder branch now -- single grant + a lingering placeholder token until
      removeFromInventory is fixed. Better than a double-grant.

## 7. Base-game (DLC off) bake crashes: volcano_town requirement loop

Symptom (2026-06-13): a bake throws `System.Exception: Loop detection failed on
volcano_town` in `KeyItemsPermutation.CollapseReqs` (KeyItemsPermutation.cs:806/819/821,
infinite simplifyReqs recursion). EVERY successful bake this session was DLC-ON; this is the
first FAILURE seen. NOTE: it's SEED-DEPENDENT, not strictly DLC-off -- base-game seed
61698419 baked fine (preflight 18:25) but a later base-game seed crashed (18:27). So some
seeds trigger an uncollapsible volcano_town cycle; DLC-on has been lucky/robust so far.
Workaround: regenerate for a new seed if a bake hits the loop.
Cause: `volcano_town` (annotations.txt:1072) Req = `volcano_drawingroom OR (nodeathless AND
academy AND altus)`; the abduction branch pulls in `altus`, and the chain cycles back to
`volcano_town`. The static randomizer's `findLoops` breaks this when DLC nodes are present but
not in the pruned base-game graph (DLC vs base is the only changed variable vs the working
99692103 bake; annotations + KeyItemsPermutation.cs are unchanged).
- [ ] Repro in isolation: DLC-off + same options; confirm it's DLC-pruning, not one of my
      apworld changes (map-exclusion / reclassification altering the scrape/scopes).
- [ ] Likely fix angle: the cycle is the `nodeathless` abduction branch. Wiring the apworld
      `deathless_routing` to ALSO set the bake's deathless (so `nodeathless` is false) would
      drop that branch and break the cycle -- but `nodeathless` source isn't in
      KeyItemsPermutation/AnnotationData; find where it's set. OR (local-only, licensing-aware)
      edit the volcano_town annotation to drop the `altus` term from the abduction branch.
- [ ] Until fixed: sync with DLC ON (validated). DLC-off base-game runs are blocked.

## Playtest 3 (live sync) findings -- 2026-06-13

Wins: dungeon sweep worked, full plumbing worked (checks/items/maps), bell+physick+kit at spawn.

## 8. Check count too high -- DONE 2026-06-13 (location_pool option)

At ~4000 locations Alaric was a huge fraction of the multiworld pool, blocking several players
on items behind far-flung checks (minutes of Torrent riding away). Need to VASTLY cut the
randomized-location count.
- Plan: add a `location_pool` Choice (e.g. all / no_filler / lean). Drop low-value pickups from
  the check pool via `_is_location_available` (same mechanism as the map-give exclusion). Easiest
  signal: the location's vanilla item CLASSIFICATION (post-reclassification, filler = golden
  runes / consumables / materials / cookbooks). no_filler ~= drop ~1800 filler-item locations
  (3945 -> ~2150). lean = progression + bosses + curated uniques (~few hundred).
DONE: `location_pool` Choice (all / trimmed / lean) in options.py; `_in_location_pool`
in __init__.py gates `_is_location_available`. all=~3900, trimmed=~2150 (drop filler-item
locations), lean=668 (boss/key/remembrance/flask/blessing tags OR progression item).
Sync uses `lean`. Needs a regen.

## 9. Everything is sphere 1 (ER open-world) -- structural

From start you can reach almost everywhere (Altus included) except Leyndell, so logic floods
sphere 1 -> hints point at far places you've never been. Real fix is region gating.
- [ ] Enable/finish region gating: world_logic `region_lock` works (each region needs a Special
      item); `region_bosses` is the nicer version but dead code (SPEC-region-boss-gating.md).
      Pairs with the great-rune thresholds already added.

## 10. Crash entering Raya Lucaria -> won't reload -> softlock

Game-side crash after entering Raya Lucaria; wouldn't load on retry (effective softlock).
Likely an enemy-rando placement / scaling in RLA, or a map/asset issue. NEED the crash repro +
client log (archipelago_client.log) + whether it persists with enemy_rando off.
- [ ] Diagnose from log; reproduce; isolate (enemy rando? DLC? RLA-specific entity).

## 11. Incoming-item notifications hog screen real estate -- client UI

The in-game incoming-item toasts are too large / badly placed (cover important HUD). Client-side
(archipelago.dll render). 
- [ ] Shrink / reposition / throttle the notification overlay in the client.

## 12. Visual marker on randomized pickups (reuse legendary aura)

With `lean`, most world pickups are NOT checks -- so a visible glow on the ones that ARE checks
would tell players what's worth grabbing (and cut aimless searching). Idea: reuse the legendary-
item golden aura VFX on randomized-check world drops.
- [ ] Find how the world-pickup glow is driven (item rarity field -> VFX, or a SpEffect/VFX on
      the EnvObj/treasure asset, or ItemLotParam). The bake already rewrites these spots.
- [ ] At bake, tag each AP-check pickup with the legendary/notable VFX (or a custom one). Verify
      it shows on shop/gift/enemy-drop checks too, not just world treasure.
- [ ] Pairs great with `location_pool: lean` -- the glow becomes "this is a check."

## 13. Region fusion: region keys + bundled grace unlock -- see SPEC-region-chain.md

Sphere shaping for the open world. Each region has a key that unlocks BOTH region access AND
that region's Sites of Grace (fast travel) -- bundled, so graces can't bypass the lock. Order
shuffles per seed; graces make non-linear travel painless. Supersedes the standalone
"graces at start" idea and the strict 7-tier chain (kept as fallback in the SPEC).
- [x] apworld: per-region key gating -- REUSED existing `_region_lock` (it already does per-region
      lock items with emergent/shuffled order). No new world_logic value needed; region_lock IS the
      logic half. Made it explicit in the sync yaml (was already the default; the playtest-3 sphere
      bloat was the TEST yaml's open_world, not the sync).
- [x] grace bundle DATA + contract (2026-06-13, apworld): grace->region mapping PROVEN clean
      (413/422 graces via map-tile -> region; 9 edge tiles unmapped). Built
      `worlds/eldenring/grace_data.py` (REGION_LOCK_ITEM + REGION_GRACE_FLAGS, 25 lock items / 210
      graces). slot_data now ships `regionGraces` = {lock_item_name: [grace warp flags]} when
      world_logic < 3. Compiles + JSON-serializable. Regen grace_data.py if regions/graces change.
- [x] graces_per_region DIAL (2026-06-13): "important" is NOT in the data (placeNameTextId is an
      unreliable proxy -- biased to overworld). Use SPATIAL SPREAD (hub + farthest-point coverage)
      from grace coords instead. New `graces_per_region` option: 0=all(210), 1=hub(29), 3=hub+
      coverage(75, default). grace_data.py stores [flag,x,z]; spread runs at gen time (no regen to
      retune). Sync yaml set to 3. Full FMG-name curation possible later if a pick is bad.
- [ ] CLIENT (next session, C++): on granting an item whose name is a key in `regionGraces`, SET
      those grace warp-unlock flags (same flag-setting path as map-reveal). This is the remaining
      half -- the data/contract is done and waiting.
- [ ] light soft-ordering so difficulty doesn't swing; GEN-TEST region_lock for deadlocks
      (undergrounds; also watch the volcano_town loop #7 -- region gating changes the logic graph).
- [ ] (optional) sub-region graces (caves/catacombs) are NOT bundled -- only the 25 locked hub
      regions. Player walks to sub-graces normally. Coarsen to ~7 region groups later if desired.

## 14. Check-name readability ("reading a barcode")

Playtest 3: lean check NAMES are cryptic abbreviations (e.g. `LL/SeI: Glass Shard - to S on
isle`) -- players couldn't parse them on the sync. Renaming the location strings is RISKY:
__init__.py logic references many location names verbatim (entrance/location rules, _fill_local),
so a rename breaks those refs. Safer paths:
- [ ] Build a region/area ABBREVIATION LEGEND (decode all ~30 region prefixes + common subarea
      codes) as a reference doc -- lets players/Alaric parse any name. Cheapest win.
- [ ] OR populate `location_descriptions` (already imported) with readable text per lean check
      (additive, non-breaking; surfaced in trackers/hints depending on client).
- [ ] Decide whether a full readable-rename (with ref updates) is worth it later.

## 15. PopTracker pack (map-based auto-tracker) -- see SPEC-poptracker-pack.md

FUTURE PROJECT, not started. Map-based auto-tracking pack: connect to the AP slot, show reachable
checks under apworld logic, pinned on Lands Between / underground / Land of Shadow maps, live as
items arrive. Interim: Universal Tracker already works with this apworld. Guiding decision:
GENERATE from apworld source (`tools/gen_poptracker.py`), don't hand-author -- ~3,700+ locations
(4,300+ DLC) and churning logic would rot a hand-built pack. Pack version == apworld `versions`
lockstep (logic must match). Decide pack home: suggest `poptracker/` in this monorepo, zipped by
build.ps1.
- [ ] Settle BLOCKER: map-art licensing (hand-traced/stylized vs CC renders vs screenshot stitches)
      -- needed for the MAP-based variant (M1 pins / M3 maps). M0 sidestepped it by shipping
      COMPACT/list-only; settle this before adding region pins.
- [x] M0 skeleton DONE 2026-06-13 (see `poptracker/` + BRIEF-poptracker-pipeline.md): built
      `tools/gen_poptracker.py` (import-free `ast` parse of items.py/locations.py → items.json
      [86 tracked: 31 locks + 55 key items], locations.json [161 region nodes, 4943 checks as
      sections], layouts/item_grid.json; `--check` mode for CI). Stable manifest (`game_name`
      "EldenRing") + autotracking/logic/init Lua + placeholder icon. Shipped COMPACT/list-only
      (no map) to sidestep the map-art blocker. Generates + validates; NOT yet loaded in PopTracker.
      Also did most of M1's id work: generator runs in RUNTIME mode (imports items.py/locations.py
      with a stubbed BaseClasses) so it emits AUTHORITATIVE id maps with no datapackage --
      scripts/ap_map.lua (90 item ids) + scripts/loc_map.lua (4906 location ids); autotracking.lua
      is id-keyed for on_item + on_location. ALSO DONE: per-section clearing (loc_map.lua emits
      sanitized "@Region/Section" codes) and region-graph reachability (region_graph.lua from
      create_connection + _add_entrance_rule; logic.lua BFS, gates split _region_lock vs set_rules;
      sanity-checked 13 reachable@sphere1 / 160 all-locks / 27 open). Remaining M1: LOAD in PopTracker
      + fix schema nits (no Lua interpreter in the dev sandbox), make on_clear's slot_data toggles
      ACT (DLC show/hide), wire --check into build.ps1. M2 = apworld declarative-rules (per-location).
- [ ] M1 full regions: all 161 region pins + generated per-region location lists; coarse
      region-graph logic for `region_lock` mode (region pin green if region reachable). Coordinate
      cost = 161 x/y pairs per map (use a click-to-record helper). Already a useful tracker.
- [ ] M2 rules (PREREQ = apworld refactor): migrate `__init__.py` `_add_location_rule` lambdas to a
      DECLARATIVE data table (`location -> requirement expr` strings) that __init__ compiles AND the
      generator translates to PopTracker access rules. Then generate per-location rules (quest gates,
      key items, Bell, medallions). Refactor also makes apworld logic testable. (HANDOFF roadmap
      flags this as the M2 blocker.)
- [ ] M3 DLC variant + polish: Land of Shadow map, Messmer kindling / Scadutree counts, item icons
      (32x32 originals or license-checked crops -- packs repo rejects some ripped assets), settings
      popout (hide missables / shop checks).
- [ ] CI guard: `gen_poptracker.py --check` in build.ps1 (-Pack?) to fail loudly when locations.py
      adds/renames regions without regenerated pack data.
- [ ] items.json scope = logic-relevant only (~60-100): region locks (99999 sentinels under
      region_lock), Great Runes (+count vs threshold), medallion halves, Glintstone/Rusty/Imbued/
      Stonesword keys (counts), Bell, quest gates, DLC kindling/gaol keys. Not the whole pool.

