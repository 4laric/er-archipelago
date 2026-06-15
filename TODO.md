# ER Archipelago — TODO

Actionable backlog. Living doc; see HANDOFF.md for current state and SPEC-*.md for designs.

## 16. DLC-only mode (Shadow of the Erdtree) -- see BRIEF-dlc-only.md / SPEC-dlc-only.md

yaml-gated `dlc_only` toggle: check pool = Land of Shadow only (~1,171-1,207 checks), base kept for
traversal only (Option A). apworld-ONLY + independently gen-testable (forces enable_dlc; bake already
keeps DLC). Decisions locked in SPEC (Option A, 1,207 incl. Roundtable, PCR goal, Messmer-shard
spine, Scadu frags = normal checks). Buildable brief: BRIEF-dlc-only.md.
- [ ] options.py: `dlc_only` Toggle (default off), in the dataclass by enable_dlc/dlc_timing.
- [ ] __init__.py: invert the pool filters (:2480, :2525) via a `_content_in_scope` helper; force
      enable_dlc at generate_early; default messmer_kindle on; goal defaults to PCR.
- [ ] GEN-TEST solo (yaml in the brief): count ~1170-1207, completable to PCR, no base checks.
- [ ] Contract bump beta.3 -> beta.4 ONLY when shipping to a sync (no runtime consumer; bookkeeping).
- [ ] Follow-ups: Option B "DLC start" (re-root at Gravesite); ~500-check pruning (DLC-scoped lean).

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
- [x] apworld DONE 2026-06-14: under give, stopped precollecting map items; fill_slot_data emits
      "reveal_all_maps" (bool). Contract bumped beta.2 -> beta.3. py_compile clean.
- [x] client DONE 2026-06-14 (build on Windows): parse reveal_all_maps -> revealAllMapsPending;
      CGameHook::revealAllMaps sets kMapUnlockFlags (gates DLC, retries until holder ready) drained
      in Core.cpp loaded block. Also wired advisory version check (er_version_check.h, WARN not
      refuse). See BRIEF-contract-map-reveal "VERIFIED / DONE".
      NOTE lockstep gap: randomizer CheckVersionRange is dev-inert (Version==null) + DS3-numbered;
      not reconciled to beta.N -- separate cleanup. apworld's emitted versions is de-facto truth.

RECLAIM the 24 pillars AS checks (Alaric 2026-06-15): now that the client owns map reveals
(reveal_all_maps + lockRevealFlags) AND open-state is split from reveal (OPEN 76971+ vs reveal
62xxx, see [[er-map-grant-region-tracker]]), the ONLY reason a pillar can't be a check is that its
pickup guard flag == the 62xxx reveal flag, so setting reveal auto-fires it. If we manage reveals
entirely ourselves, re-key the pickups off 62xxx and they become 24 normal check locations (valuable
for lean/trimmed where checks are scarce; all are on-path landmark pickups).
- [ ] BAKE: re-key each map-pillar item lot's get-item/guard flag to a FRESH unique flag (not the
      62xxx reveal flag), so the pickup fires only on actual interaction.
- [ ] Keep map reveals 100% client/baker-managed (reveal_all under give; lockRevealFlags on unlock) --
      do NOT rely on the pickup to set 62xxx anymore.
- [ ] ITEM side: the Map fragment items (8600-8618, DLC 2008600-2008604) become inert/redundant under
      give -- drop them from the pool, or keep as pure filler (if left functional they'd reveal a tile
      early; harmless but messy). Decide.
- [ ] CONTRACT: location keys currently encode the 62xxx flag (e.g. key "...0000062010::"); re-keying
      = locations.py + scraper + client must agree -> contract bump. Coordinate with the map-tracker.
- [ ] Drop the `map_option.value == 1 and data.map` exclusion in _is_location_available once re-keyed.
- [ ] Gate: only relevant under map_option=give (1); under place-mode (2) pillars already hold the
      locked map item.

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

Sphere shaping for the open world. Each region has a key that unlocks BOTH region access AND that
region's Sites of Grace (fast travel), bundled so graces can't bypass the lock. Full design +
status in SPEC-region-chain.md and memory [[er-region-fusion]].
- [x] apworld: region gating via existing `region_lock` (per-region .lock items, shuffled order).
- [x] grace bundle DATA + contract: grace_data.py (REGION_LOCK_ITEM + REGION_GRACE_POINTS); slot_data
      ships `regionGraces` {lock-item: [warp flags]} when world_logic < 3; `graces_per_region` dial.
- [x] CLIENT (2026-06-13): regionGraces parsed; FlushPendingGraceFlags sets grace warp flags on
      lock-item receipt (Core.cpp/.h, ArchipelagoInterface.cpp, GameHook.cpp). Build on Windows.
- [ ] INTEGRATION GATE (human): build client, bake region_lock seed (graces_per_region:1), playtest
      -- receive lock -> "Region grace flag .. SET" -> map -> grace selectable. Then 3 and 0.
- [ ] gen-test region_lock for deadlocks (undergrounds); watch volcano_town loop (#7).

## 14. Check-name readability ("reading a barcode") -- DONE 2026-06-14

Lean check names were cryptic (e.g. `LL/SeI: Glass Shard - to S on isle`). Done by the apworld-content
session (NON-breaking, additive -- no location renames, so no logic refs broke):
- [x] Abbreviation LEGEND: `worlds/eldenring/docs/check-name-legend.md` -- 57 region prefixes + 264
      subarea codes across 443 lean checks, auto-derived from locations.py (not invented).
- [x] `location_descriptions` populated: `_er_describe_lean_checks()` (locations.py:6304) decodes each
      lean check's prefix -> full region name + check-type tag + original hint; 464 entries total
      (454 auto per-check). Keyed by verbatim name via setdefault; runs clean at import. Surfaces in
      trackers/hints (incl. the PopTracker pack, TODO #15-poptracker).
- [ ] (optional, deferred) full readable-RENAME with ref updates -- still risky; legend+descriptions
      were the safe win, rename not needed.

## 15. Retarget the .NET stack net6.0-windows -> net8.0-windows (EOL)

net6.0-windows is out of support (SDK warns NETSDK1138; currently silenced via the root
`Directory.Build.props` `<CheckEolTargetFramework>false>` -- that's a NAG MUTE, not a fix). net8 is
the current LTS. All C# projects share the TFM, so retarget together. Low-to-moderate risk: WinForms
+ the deps (Archipelago.MultiClient.Net, Newtonsoft, BouncyCastle.Cryptography 2.5.0, YamlDotNet,
Tomlyn, ZstdSharp) all support net8; the bake/-LoopTest and RandomizerCommon.Tests give a quick
regression signal.
- [ ] Bump `<TargetFramework>`/`<TargetFrameworks>` net6.0-windows -> net8.0-windows in: SoulsFormats,
      SoulsIds, GrayIris.Utilities, RandomizerCommon, RandomizerCommon.Tests, EldenRingRandomizer
      (and DS3/Sekiro projects if kept). Update the `win-x64` self-contained settings if needed.
- [ ] Update build.ps1 / dotnet invocations and any `net6.0-windows` path literals (e.g. the
      RandoExe path in build.ps1, deploy copies).
- [ ] Rebuild `build.ps1 -Randomizer -Client`, run `build.ps1 -Test` (xUnit) + a `-LoopTest` batch;
      eyeball a bake. Watch for new analyzer/CA warnings under net8 (esp. CA1416 surfaces -- the
      GrayIris NoWarn already covers it).
- [ ] Once green, remove `<CheckEolTargetFramework>false>` from Directory.Build.props (no longer
      needed) and re-confirm no NETSDK1138.
- [ ] Confirm the runtime client DLL (C++, pinned eldenring.exe 2.6.2.0) is unaffected -- it's a
      separate MSBuild/vcxproj toolchain, not .NET-TFM-bound.

## Mount-truncation instrumentation (dev-infra) — 2026-06-14
Working out of the repo keeps getting bitten by a file-view split: the Edit tool's
writes to an EXISTING file do NOT refresh the bash sandbox mount (bash serves a stale /
truncated view, while real disk is correct), and bash large-file READs can themselves
truncate. Observed this session: __init__.py + trim_report.py both showed phantom
truncation in bash while correct on disk. Characterized mount behavior:
  - bash write -> real disk: WORKS
  - file-tools NEW file -> bash: WORKS
  - file-tools EDIT to existing file -> bash: STALE (does not refresh)  <-- the trap
Action items:
- [ ] Standardize a "verify on disk after edit" step: after any source edit, re-Read the
      file via file-tools (real-disk truth) AND, when a compile is needed, force convergence
      by rewriting through bash (cat > heredoc) since bash->disk syncs reliably.
- [ ] Add a tiny `tools/verify_edit.py` (or build.ps1 hook) that compiles + checks line
      count / brace balance on the REAL file after edits, so phantom-truncation is caught.
- [ ] Prefer Python read-modify-write (or Write tool) over the Edit tool for CRLF apworld
      files; the Edit tool has historically truncated CRLF tails (see memory).
- [ ] Consider normalizing the apworld __init__.py to LF (or a .gitattributes guard) to
      remove the CRLF edit-truncation hazard entirely.
- [ ] Document the mount asymmetry in HANDOFF.md so future sessions don't re-derive it.

## 17. Curation pass: keep "free" filler checks (on main road / near important checks) — 2026-06-15

In-game discoverability companion: SPEC-ingame-check-indicators.md (enemy ghost-glow marker + scarab audio cue).

Alaric: do a sweep for checks whose vanilla item is filler/junk material BUT that sit on the
starter/main road or right next to an already-kept important check — those are "pretty free to
get" and fun, so force-keep them under lean/trimmed (same treatment as the Kukri / Stormgate
Lump of Flesh already wired into `_in_location_pool`).

Precedent already in code (`__init__.py` `_in_location_pool`, pool==1 curated keep list):
- "LG/GC: Kukri x4 - E of GC" (Limgrave road, Church of Elleh <-> Gatefront)
- "LG/(SG): Lump of Flesh - lower area" (Stormgate, main road N of Gatefront -> Stormveil) [2026-06-15]

Candidates raised so far (verify keys, then add to the curated keep / a new tag):
- [x] Spiked Cracked Tear — DONE 2026-06-15: added to the curated keep in _in_location_pool (basin tear; was kept in lean, now also kept in trimmed). key 604537,0:0000065140::.
- [ ] Fire Grease near South of Agheel Lake (Agheel-adjacent, on the early loop).
- [ ] Arteria Leaf at Agheel Lake North — "LG/ALN: Arteria Leaf - to SE", key `604337,0:1043377020::`.
- [ ] "Golden Vow guy" ash + other enemy-drop ashes — see enemy-drop tagging note below.

Method to make this systematic (not hand-curated forever):
- [ ] Add an `enemydrop` tag derived in `location script/script.js` from the itemslots DebugText.
      Signal = the source string matches `/ enemy c\d{4}_\d{4}/` (covers BOTH "enemy lot
      NNN[enemy cXXXX_YYYY ...]" pure death-drops AND "lot NNN[event enemy cXXXX_YYYY ...,
      event EEEE ...]" event-awarded drops). Add `enemydrop: bool = False` to ERLocationData,
      regen `location output.txt`, merge into locations.py.
      - Golden Vow = pure enemy lot (Godrick Knight c4351_9000); Gravitas = enemy lot (Onyx Lord
        c3600_9000); Lion's Claw / Bloody Slash / Flame Spear = event-enemy drops.
      - ENEMY-RANDO caveat: event-enemy drops are keyed on the placed ENTITY id, not the model,
        so they survive a model swap but break if enemy rando deletes/relocates that entity —
        protect those entities. Pure enemy-lot drops follow the carrier.
- [ ] Consider a grace-proximity sweep (reuse LOC_GRACE_DIST from location_remoteness.py): a
      filler check within X metres of a kept check / grace is a "free" keep candidate.
- [ ] Decide the mechanism: extend the curated name list vs. a real tag (e.g. `freecheck` /
      `enemydrop`) added to the `_lean` tuple so they survive lean too, not just trimmed.

## 18. Grant Cathedral of Dragon Communion grace on Dragon Heart receipt — 2026-06-15

Idea (Alaric): when the player RECEIVES a Dragon Heart (item id 10060, progression) as an AP item,
unlock the Site of Grace at the **Cathedral of Dragon Communion** (Caelid — the `CL/(CDC)` altar
where Dragon Hearts buy dragon incantations; shop flag 101950, region "Church of Dragon Communion").
Rationale: a Dragon Heart is useless until you can reach a communion altar (deep in Caelid), so
granting that grace on receipt makes the reward actually spendable + thematic.

- [ ] Reuse the grace-bundle plumbing from §13 (client `FlushPendingGraceFlags` sets grace warp
      flags; `regionGraces` slot_data). Here the trigger is item-receipt (Dragon Heart 10060), not a
      region-lock item — so it's a small item->grace mapping, not a region bundle.
- [ ] Find the Cathedral of Dragon Communion grace warp flag to set.
- [ ] Decide: grant on the FIRST Dragon Heart only (idempotent), and whether to gate behind
      world_logic / region_lock settings like §13 does.
- [ ] NB: distinct from the Limgrave **Church** of Dragon Communion (Isolated Merchant area) — this
      is the Caelid **Cathedral**.

## 19. QoL patches (bake/client) — 2026-06-15

Misc quality-of-life polish. Bake-side unless noted; contract-free.

### 19a. Patches' Murkwater shop without the leave/re-enter dance  (PRIORITY — Alaric)
Annoyance: after beating/sparing Patches in Murkwater Cave (m31_00) you must exit and re-enter
before his shop is browsable. Cause is the ambush->merchant ENTITY swap + shop ESD, not param
caching: Murkwater has hostile Patches `c0000_9000` (id 31000800, group 31005100,31005800) and
seated-merchant Patches `c0000_9002` (id 31000850); the merchant entity + shop ESD 309003100 only
come up on the next map load. Shop lineups 100100-100122, flags 110000-110220 (+67600).
- [ ] FIX (preferred): patch the m31_00 Patches EMEVD so his surrender/low-HP trigger immediately
      sets the spared-merchant flag and enables the merchant entity in place (no reload). RE the
      exact event id first.
- [ ] Verify his later relocations (Liurnia Scenic Isle 1037420720 -> Mt. Gelmir 1037540700/701 ->
      Volcano Manor 16000710) still read the right flags after the patch — don't break the quest.
- [ ] Preserve the ambush "kill Patches" death-drops (Spear/Leather set, key ...0000400189,
      death=True) — if we ever go the "merchant from start" route instead, relocate those checks.
- [ ] Alternative (heavier): Patches-as-merchant from bake init, ambush disabled. Simplest shop
      access but changes questline + loses the kill drops. Not preferred.

### 19b. General shop-refresh-on-unlock (lower priority)
Other shops (bell-bearing merchants, Dragon Communion altar, AP shop unlocks) also need a reload to
reflect a flag flipped mid-area. ShopLineupParam is already a Dynamic (runtime-reloadable) param per
RuntimeParamChecker, so the blocker is the open menu/ESD cache, not the data.
- [ ] Investigate a client-side "invalidate/refresh open shop menu" poke after a grant that sets a
      shop flag (reuse the grant/grace-flush surface). RE the shop-menu refresh call.
- [ ] Candidates that benefit: Dragon Communion incantation lineup (ties to §18), bell-bearing
      turn-ins, any AP-unlocked shop row.

### 19c. Other QoL candidates (parking lot)
- [ ] Show real AP item names in shop/lineup rows (instead of vanilla placeholder) where feasible.
- [ ] Skip/shorten the Dragon Communion commune animation on repeat use.
