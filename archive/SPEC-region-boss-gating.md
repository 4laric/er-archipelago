# SPEC: Finish region_bosses / region_lock_bosses world logic

Status: FUTURE PROJECT, not started. (Alaric, 2026-06-11)
Context: world_logic modes 1 (region_bosses) and 2 (region_lock_bosses) are advertised in
options.py but the boss-gating half is dead code (`and False # unfinished always skip` in
`_region_lock()`, __init__.py ~1007). Mode 1 currently degenerates to OPEN WORLD (lock
rules explicitly skip it, boss rules never run); mode 2 silently behaves as plain
region_lock. `region_boss_percent` is decorative — referenced only in slot_data.

## Intended design (from the option text)

- **region_bosses (1):** entering region N+1 requires defeating X% of the bosses in
  region N (no lock items in the pool).
- **region_lock_bosses (2):** requires the region's Lock item AND the boss percentage.
- `region_boss_percent` (1-100, default 50): the X.
- `region_boss_type` (toggle): only "overworld" bosses count vs all bosses in region.

## What exists to build on

- Location tags: per-region boss flags on ERLocationData (`limgrave_boss`,
  `stormveil_boss`, ... 40+ incl. DLC) plus class tags (`overworldboss`, etc.), and
  `location_name_groups` exposing them as groups (the dead code already consumes
  "Limgrave Bosses"-style groups — VERIFY these group names actually exist; if not,
  they're built from the tags).
- The dead block already sketches both variants (intersect with Overworld Bosses when
  region_boss_type is set) and the region progression chain (Limgrave -> Weeping ->
  Stormveil -> Liurnia -> ...). Treat it as a draft, not gospel — the chain hardcodes a
  linear order that should be reviewed against the actual region graph.

## Why it was hard (the actual problems to solve)

1. **Percent thresholds need counting, not _can_get_all.** The draft gates on "can get
   ALL bosses in the group" (= 100%, ignoring the option). AP logic has no native
   "N% of these locations reachable" primitive over LOCATIONS. Two viable approaches:
   a. **Event items per boss (recommended):** place an event item ("Limgrave Boss
      Token") at each boss location at generation; gate entrances on
      `state.has("Limgrave Boss Token", player, ceil(pct * count))`. This is the
      standard AP pattern (cf. Great Runes counting, which this apworld already does).
   b. CollectionState location-counting lambda — works but is slow (called constantly
      during fill) and easy to get subtly wrong with sweep/stale caches.

2. **Client-side detection — what does "defeated" mean at runtime?** Logic-only gating
   (like region_lock) needs NOTHING in-game: the tokens are events, the server tracks
   reachability, done. BUT the boss locations' CHECKS (drops) already detect via flag
   polling, so the player's progress is visible to logic automatically. No client work.

3. **Self-referential gating hazard:** boss DROP locations live inside regions that the
   boss gating itself locks. The chain must only count region-N bosses for the
   region-N+1 gate (the draft does this), and bosses inside gated subregions (Stormveil
   bosses behind Stormveil Lock in mode 2) must not deadlock the count — fill needs at
   least `ceil(pct*count)` bosses reachable without the gate they feed. Needs a
   generation-time sanity assert + a few targeted unit seeds.

4. **region_boss_type definition:** decide what "overworld" excludes (evergaols?
   minidungeon bosses? night bosses?) and tag accordingly — `overworldboss` exists but
   audit its coverage before trusting it.

5. **DLC chain:** the draft block predates the DLC port; the DLC region chain
   (Gravesite -> Scadu Altus -> ...) has no boss-gate draft at all. Extend the chain
   using the dlc `*_boss` tags (gravesite_boss, scadualtus_boss, ...).

## Work items

1. Audit/build `location_name_groups` for per-region boss groups + Overworld subset;
   audit `overworldboss` tag coverage (incl. DLC).
2. Implement boss-token events: at generation, place "<Region> Boss Token" event items
   on boss locations (skip missables/excluded).
3. Rewrite the dead block: entrance rules use token counts with
   `ceil(region_boss_percent/100 * tokens_in_region)`; honor region_boss_type subset;
   add the DLC chain; delete `and False`.
4. Fix mode interactions: mode 1 = boss gates only; mode 2 = boss gates AND lock items
   (the `!= "region_bosses"` guard in _region_lock already aims at this — verify enum
   string comparison actually works there; comparing a Choice to a string is fragile,
   prefer `.value` against the option constants).
5. slot_data already ships region_boss_percent/type — no contract change. UT picks up
   the new logic for free. Dungeon sweep unaffected (triggers are drop locations).
6. Tests: unit seeds for pct=1, 50, 100 in modes 1 and 2, DLC on/off; assert beatable
   and no boss-count deadlock (problem 3).

## Effort guess

Small-medium apworld-only change (no randomizer/client work): the token-event pattern
is well-trodden; the real time goes into boss-group auditing and deadlock test seeds.

## Open questions

- Should boss gates respect `missable_location_behavior`? (A missable boss in the count
  with pct=100 = potential brick; suggest: missable bosses never count toward gates.)
- Great Runes interaction: great_runes_required already gates Leyndell — boss gates
  stack on top; decide if that's intended difficulty or double-gating to simplify.
- Does region_bosses (no locks) want soft_logic's Caelid/Snowfield expectations kept?
  (Suggest yes — they're orthogonal.)
