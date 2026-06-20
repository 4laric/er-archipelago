# SPEC: Random Starting Region

Status: DRAFT (2026-06-19). Wacky-ideas batch, idea #1. Sibling: [SPEC-completion-scaling.md].

## One-liner

Instead of always spawning at The First Step in Limgrave, roll a random overworld region at
gen time, make THAT region the free sphere-1 hub (grant its grace bundle + open flag + a warp-in
at load), and let the rest of the world gate off it as usual. The bootstrap region rotates; the
fill, the locks, and the goal all reorient around wherever you woke up.

This is almost entirely a **re-pointing of machinery that already exists**. The dlc_only path
already does exactly this for Gravesite Plain: client latch sets a flag in the Chapel -> baked
`WarpPlayer` drops you in the DLC + grants the Roundtable + region grace at start (see the
`er-dlc-autoentry` and `er-region-fusion` memories). Random-start generalizes "the free hub is
Limgrave" / "the free hub is Gravesite" to "the free hub is whatever we rolled."

## Why this is coherent (not just chaos)

The world already has a notion of a single free starting region baked into the region-lock model:

- `map_region_data.START_REVEAL_FLAGS = [62010, 62011]` and `LIMGRAVE_START_GRACES` hard-code
  "Limgrave is the free sphere-1 hub, fully fast-travelable from the jump."
- `region_spine.py` SPINE step 1 (Limgrave) "owns no lock: it is the free starting region."
- `__init__._region_lock_warp_access()` already builds direct `Limgrave -> region` warp entrances
  gated on each region's lock item (`region_access = warp`).

So the codebase is already written around "there is exactly one free region and everything hangs
off it." Random-start swaps which region that is. The hard part is not the warp -- it is making the
**logic graph re-root** onto the new start without orphaning the goal or the lock chain.

## Option surface (apworld `options.py`)

```python
class RandomStartRegion(Choice):
    """Roll a random overworld region to start in instead of Limgrave / The First Step.
    The chosen region becomes the free sphere-1 hub: its lock (if any) is granted free, its
    grace bundle + map reveal + open flag fire at load, and you warp straight in. Requires a
    region-gating world_logic (region_lock / region_bosses / region_lock_bosses); inert under
    open_world (there is no hub to move). Forced off when dlc_only is on (Gravesite is already
    the fixed hub) and under ending_condition that seals the chosen region behind the wall.

    - off:          vanilla -- start at The First Step (Limgrave).
    - overworld:    roll among the 6 overworld majors (Limgrave, Weeping, Liurnia, Caelid,
                    Altus, Mt. Gelmir). Safest: each has a clean warp grace + map piece.
    - any_major:    overworld majors + legacy-dungeon entry regions (Stormveil, Leyndell...).
                    Spicier; some have no map pillar and need a hand-picked entry grace.
    """
    display_name = "Random Starting Region"
    option_off = 0
    option_overworld = 1
    option_any_major = 2
    default = 0

class StartRegionFreebie(Choice):
    """What the chosen start region's OWN lock chain costs. The start region must be reachable
    with zero items, so its lock is always free; this controls how much MORE comes free.
    - hub_only:   just the start region's graces + open flag (you still need its neighbours' locks
                  to leave -- it is an island until you find them).
    - to_limgrave: also grant a one-way warp back to The First Step, so Roundtable/Torrent/early
                  vendors are never stranded behind a lock you happened not to start near."""
    display_name = "Start Region Freebie"
    option_hub_only = 0
    option_to_limgrave = 1
    default = 1
```

Pin the seed: the roll must come from `self.multiworld.random` (per-slot, seeded) so a yaml +
seed reproduces, and so `TestEROptionMatrix` can pin a value. Store the result on `self` early
(in `generate_early`) because both `create_regions` (logic) and `fill_slot_data` (client payload)
need it.

## Candidate start regions

Source of truth = `grace_data.REGION_LOCK_ITEM` keys (the region list) intersected with
`map_region_data.REGIONS` (must have `area_ids` for detection and `reveal_flags` for the map).
A region is a **legal start** only if all of:

1. It has a non-boss-arena warp grace (reuse the grace-arena exclusion list from
   `patch_apworld_grace_arena_exclude.py` / `er-grace-bundle-boss-arena` -- never spawn the player
   inside a dormant no-AI boss arena).
2. It has at least one `reveal_flags` map pillar (so the map isn't black) -- this is why
   `overworld` is the safe default and `Mt. Gelmir` (`area_ids: []`, TBD) is excluded until its
   area id is captured (see `REGIONLOCK-areaid-capture.md`).
3. It is not sealed by the active `ending_condition` / `region_count` spine (a `capital` run that
   seals Caelid can't start you in Caelid).

Build this legal set in `generate_early`, then `random.choice` it. If the set is empty after
filters (over-constrained yaml), fall back to Limgrave and emit a generation warning.

## Mechanism, by layer

### 1. apworld -- logic re-root (`__init__.create_regions` / rules)

The whole region-lock logic assumes the `Menu`/start region connects to Limgrave. Re-rooting:

- Grant the chosen region's lock item as a **precollected start item** (so `state.has(lock)` is
  true from sphere 0). This is the same lever `region_count` uses to seal regions, run in reverse:
  instead of pulling a lock from the pool, we pre-place it.
- Connect `Menu -> <start region>` directly (the new bootstrap edge), replacing / in addition to
  `Menu -> Limgrave`.
- Under `region_access = warp`, the existing `_region_lock_warp_access` loop already makes every
  region reachable via its own lock from the hub. Re-point the hub variable from `limgrave` to the
  chosen region's AP region object; the `Warp To X` entrances then radiate from the new start.
- Under `region_access = geographic`, this is harder: you must physically path. Decision below
  (open question A) -- simplest is to **force `warp` access when random-start is on**, because a
  geographically-deep start (e.g. Altus) has no zero-item physical route back down to Limgrave.

### 2. apworld -- `fill_slot_data` payload

Mirror the dlc_only start block (around `__init__.py:4173`). Emit:

- `startRegion`: the chosen region name (client logs it, can show "You begin in: Caelid").
- `start_graces`: the chosen region's grace bundle (same source as `regionGraces` /
  `lockRevealFlags` for that lock), MINUS boss-arena graces. Plus `71190` (Roundtable) always, so
  bell bearings / remembrance exchange are never stranded. Plus the start region's primary warp
  grace as the literal spawn point.
- `startOpenFlags`: the chosen region's open flag (`OPEN_FLAG_BASE`+, the lock's `lockOpenFlags`
  value) so the physical fog-wall enforcement (RegionFogGates) treats it as open.
- `startRevealFlags`: the chosen region's `reveal_flags` so its map tile is lit.
- If `StartRegionFreebie = to_limgrave`: also append Limgrave's `START_REVEAL_FLAGS` +
  `LIMGRAVE_START_GRACES` + a warp to `76101` (The First Step), so the early-game services hub is
  always available.

### 3. baker (SoulsRandomizers / C#) -- physical spawn + warp

The dlc_only auto-entry already bakes a `WarpPlayer` keyed off a flag the client latches in the
Chapel (`er-dlc-autoentry`: flag 76999 -> WarpPlayer to Gravesite). Generalize:

- The chosen region's spawn-grace `BonfireWarpParam` id becomes the `WarpPlayer` target.
- Keep the latch in the Chapel of Anticipation tutorial (the player still does the falling
  intro), then warp. OR skip the Chapel entirely if a clean post-intro warp flag exists --
  open question B.
- The grace `obtained` flags must be set so the target grace is "activated" (you can warp back to
  it after death), same as the key-item obtained-flag handling in `er-keyitem-obtained-flags`.

The baker needs to know WHICH region was rolled. Cleanest: pass it through slot_data (the baker
already reads slot_data; `er-bake-slotdata-timeout` is resolved) rather than a new bake arg.

### 4. client (runtime)

Reuse the dlc_only latch + start-grant path almost verbatim:

- On first load with `startRegion` set: queue `start_graces` / `startOpenFlags` / `startRevealFlags`
  into the existing `pendingStartItems` queue, set obtained flags, set the warp latch flag.
- Honour the once-per-save gate (`er-startitems-grant-loop`: `startItemsGranted` persisted) so the
  warp + grants don't re-fire on every reconnect and yank the player out of wherever they are.
- Gate the flush on `InventoryInstance() != 0` (`er-grace-flag-flush-too-early`) so new-game init
  doesn't clobber the granted graces.

## Goal / fill interactions (the actually-tricky part)

- **Goal reachability.** If `ending_condition = capital` (Morgott) but you start in Mountaintops,
  the goal is now "behind" you. Logic must still prove a path from the start region to the goal
  boss through the lock chain. Pre-placing the start lock changes which spheres are reachable;
  `region_access = warp` makes this tractable (everything radiates from the hub via its own lock).
  Validate with a full gen-test matrix (each legal start x each ending_condition).
- **Region-count spine.** `region_count` (capital runs) keeps a FIXED first-N spine from Limgrave.
  Random-start + region_count conflict: the spine assumes Limgrave is step 1. v1 decision: **forbid
  the combo** (force random-start off when region_count > 0), warn, revisit later.
- **Bootstrap softlock.** If the start region is an island (hub_only) and none of its neighbour
  locks are in early spheres, the fill could place the only progression behind a lock you can't
  reach. `region_access = warp` + the rune-skip injectable-room trick (`er-rune-skip-injectable-room`)
  should keep the fill solvable, but this is the #1 thing to stress-test.

## Open questions

A. **Force warp access?** Recommend yes for v1 -- geographic access from a deep start is a
   softlock minefield. Document that random-start implies `region_access = warp`.

B. **Chapel intro or skip it?** Keeping the Chapel falling-intro is lowest-risk (proven path) but
   it always warps you to Limgrave-adjacent first. Skipping needs a clean post-character-creation
   warp flag. Start with "keep Chapel, then warp."

C. **`any_major` legal set.** Stormveil/Leyndell as starts are fun but several have `reveal_flags:
   []` (no map pillar) and boss-gated graces. Ship `overworld` first; treat `any_major` as a
   follow-up once each candidate's spawn grace is hand-verified.

D. **Torrent / Spirit Calling Bell / flasks.** A non-Limgrave start skips the vanilla pickups for
   these. Grant them as start items (Torrent is already a start grant under some modes --
   `er-torrent-start-grant`; flasks via the start-items queue).

## Test plan

1. Gen-test each `overworld` start x {region_lock, region_bosses} x {capital, default goal};
   assert solvable, assert start lock pre-collected, assert no boss-arena spawn grace.
2. `TestEROptionMatrix`: pin `random_start_region` to each value; assert legal-set filter, assert
   forced-off interactions (dlc_only, region_count, open_world) emit warnings not crashes.
3. Bake + playtest the safest start (Caelid or Liurnia): confirm you spawn at the right grace, map
   tile lit, can warp the region's bundled graces, Roundtable reachable, goal still beatable.
4. Adversarial: start in the region the goal boss lives in; start in a region adjacent to nothing
   with a low `graces_per_region`.

## Effort estimate

Logic re-root + slot_data: ~1 day (mostly re-pointing existing functions). Baker warp generalize:
~half day (dlc_only path is the template). Client: minimal (reuse latch/queue). The cost is in the
**gen-test matrix + playtest**, not the code -- this touches the load-bearing region-lock graph.
