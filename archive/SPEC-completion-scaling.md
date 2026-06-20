# SPEC: Completion-Percent Scaling (override default region scaling)

Status: DRAFT (2026-06-19). Wacky-ideas batch, idea #2. Sibling: [SPEC-random-starting-region.md].

## One-liner

Replace Elden Ring's built-in geographic difficulty curve (Limgrave weak -> Mountaintops brutal)
with a curve keyed to **how much of the seed you've completed**, so difficulty tracks your actual
progress through the multiworld rather than where you happen to be standing.

## Precedent (Alaric, 2026-06-19): FogMod depth scaling

This is not a crazy idea -- thefifthmatt's Fog Gate randomizer already does exactly this kind of
re-basing. With randomized fog connections, geography stops predicting difficulty (you might walk
out of the tutorial into Farum Azula), so FogMod scales each area by its **fog-gate depth** -- the
graph distance from the start through the randomized gate network -- instead of its vanilla region.
Completion-scaling is the same move with a different distance metric: instead of "how many gates
deep," use "what fraction of the seed is done."

The key realization is that **ER scaling is already a re-mappable area -> tier function**, and both
FogMod and the enemy randomizer's own `scalerandom` option already overwrite that map. We are
adding one more way to compute the target tier.

## How ER scaling actually works (grounding)

From `SoulsRandomizers/RandomizerCommon/ScalingEffects.cs` and `EnemyRandomizer.cs`:

- `InitializeEldenScaling()` builds `ScalingSections`: a map of `enemyId -> tier`. Tiers come from
  `SpEffectParam` rows `7000 + 10*i` for base tiers 1..20, plus DLC families `20007000+10*i`
  extending to ~tier 35. `MaxTier = 20 + dlcTiers`.
- Scaling between two tiers is precomputed per stat (health, damage, xp, posture) as a matrix over
  `SectionPairs` `(sourceTier, targetTier)`, exposed as `AreaScalingValue` in `Areas[(i,j)]`.
- When an enemy is relocated by enemy rando, the writer applies the `(sourceSection, targetSection)`
  SpEffect so the enemy fights like the destination area expects.
- **Crucially, the target map is already overwritable.** `EnemyRandomizer.cs` (~L1041): when
  `opt["scale"]` and (`scalerandom` preset or `preset.RandomScaling`), it clones `ScalingSections`
  into `targetScalingSections` and overwrites entries with a `newScale`. That clone-and-overwrite
  is the exact injection point for a progress-ordered tier map.
- Default (no enemy rando, no scalerandom): enemies keep native tiers -> native geographic curve.
  THAT native curve is the "default region scaling" we are overriding.

So baked completion-scaling = compute a deterministic, progress-ordered `targetScalingSections`
(instead of `scalerandom`'s random one) and force the scale pass to apply it even when enemies
aren't relocated ("scale in place").

## Two variants (this is the real design fork)

### Variant A -- BAKED "progress tier" (recommended; the true FogMod analog)

At gen time, assign every area a tier from its **expected completion order**, then bake that as the
target scaling map. "Expected completion order" with AP region locks is well-defined:

- Order regions by lock-chain depth (sphere position): the start region is progress 0%; each region
  reachable only after N locks sits deeper. We already compute this ordering for `region_spine.py`
  and the region-lock graph -- reuse it.
- Map each region's depth fraction onto tiers `1..MaxTier` (linear, or a tunable curve). Every
  enemy in that region gets that target tier.
- Force the scale pass on (set `opt["scale"]`, inject our `targetScalingSections`) so the rewrite
  applies even on a no-enemy-rando seed -- scale in place, source tier = native, target tier =
  progress tier.

Pros: deterministic, reproducible from seed, zero runtime risk, reuses the proven SpEffect path,
exactly mirrors FogMod. Cons: difficulty is fixed at gen -- it reflects *expected* progress order,
not your *actual* live %. If you skip ahead via a lucky warp, the area is still tuned to its baked
depth (which is arguably correct -- that's what FogMod does).

### Variant B -- RUNTIME live completion% (the literal reading)

Client applies a single global difficulty SpEffect to the player, swapped by bucket as your live
`checked_locations / total_locations` climbs. ER already ships uniform global scaling SpEffects
(the NG+/difficulty family with `damage taken` / `damage dealt` rate fields); the client picks a
bucket each poll and applies the matching SpEffect.

Pros: actually tracks live %, dynamic, no gen/bake changes, pure client. Cons: **uniform** -- it
shifts your whole relationship to every enemy at once; it cannot make Limgrave easy and Caelid hard
simultaneously, because it's a player buff/debuff, not a per-area tier. Also a blunt instrument
(health+damage rates only, no posture/xp curve nuance) and visible as a status effect.

### Recommendation

Ship **Variant A** as `completion_scaling` proper -- it is the honest "override region scaling" and
the FogMod-faithful design, and it lands almost entirely in code paths that already exist. Treat
Variant B as a separate optional `live_difficulty_drift` toggle for people who literally want the
world to harden as their check count climbs; it's independent and can stack.

## Option surface (apworld `options.py`)

```python
class CompletionScaling(Choice):
    """Override Elden Ring's geographic difficulty curve with one keyed to seed progress.
    Each region is re-tiered by its lock-chain depth (how deep in the completion order it sits)
    and enemies are scaled in place to that tier -- so difficulty tracks progress, not geography.
    Inspired by FogMod's fog-gate-depth scaling.

    - off:    vanilla geographic scaling (native enemy tiers).
    - flat:   linear depth -> tier mapping across MaxTier tiers.
    - gentle: compressed curve (early regions stay close together, ramp late) -- friendlier.
    - steep:  expanded late curve -- deep regions punish hard.
    Requires a region-gating world_logic (needs a lock-chain depth to order by); inert under
    open_world. Composes with enemy_rando (relocation scaling still applies on top)."""
    display_name = "Completion Scaling"
    option_off = 0
    option_flat = 1
    option_gentle = 2
    option_steep = 3
    default = 0

class CompletionScalingFloor(Range):
    """Lowest tier any region can be re-mapped to (1..MaxTier). Raising it means even the start
    region isn't trivial. Default 1 = preserve a true easy start."""
    display_name = "Completion Scaling Floor"
    range_start = 1
    range_end = 10
    default = 1
```

The depth-ordering must be derived from the SAME region-lock graph the fill uses, and pinned to the
seed, so the curve is reproducible. Emit the resulting region -> tier table into slot_data (for the
baker) and into the spoiler (so you can eyeball "Caelid = tier 12" when debugging).

## Mechanism, by layer

### Variant A
1. **apworld**: compute `region_depth[region]` from the lock-chain graph in `generate_early` /
   after `create_regions`. Map depth -> tier via the chosen curve + floor. Emit
   `regionScalingTiers` into `fill_slot_data`.
2. **baker (C#)**: read `regionScalingTiers` from slot_data. In the scaling pass, build
   `targetScalingSections` from it (region -> its enemies -> target tier) instead of / in addition
   to `scalerandom`'s random remap, and force `opt["scale"]` so the rewrite applies even without
   enemy relocation. Reuse `Areas[(source,target)]` SpEffect application verbatim.
3. **client**: nothing -- it's all baked into regulation.bin SpEffect assignments.

### Variant B
1. **apworld**: just the toggle + total-location count into slot_data.
2. **client**: each poll, compute `% = checked / total`, pick a bucket, apply the matching global
   difficulty SpEffect to the player; remove the previous one. Persist nothing (recompute on load).
   Reuse the SpEffect-apply path the auto_upgrade / consumable grants already use.
3. **baker**: none.

## Interactions / risks

- **Enemy rando on top.** Variant A composes: relocation scaling maps source->dest tier; our
  re-tiering changes what "dest tier" means per region. Net effect = enemies scaled to the region's
  PROGRESS tier. Verify the matrix doesn't double-apply (the rewrite replaces `targetScalingSections`,
  it shouldn't stack with a second pass).
- **DLC tiers.** `MaxTier` includes the DLC families (up to ~35) only when the DLC regulation is
  loaded (`InitializeEldenScaling` breaks the loop when the rows are absent). The depth->tier map
  must clamp to the live `MaxTier`, not assume 35. Under `dlc_only` the whole tier budget is DLC.
- **Bosses are hand-tuned.** `ScalingEffects` already dampens scaling (the `target = 1.275` / 19-iter
  dampening) because "later game bosses are often manually tuned differently." Re-tiering a boss
  region down could trivialize a boss, or up could make an early boss absurd. Consider excluding
  remembrance/great-rune bosses from the re-tier (keep native), or apply a softer curve to them.
- **No-lock regions.** A region with no lock (the free start) is depth 0 -> floor tier. Good.
- **Variant B uniform caveat** (above) -- document loudly so expectations are right.

## Open questions

A. Depth metric: raw lock-chain hop count, or fill-sphere index (when each region's checks first
   become reachable)? Sphere index tracks "completion" more faithfully but is fill-dependent
   (varies per seed even at same settings). Hop count is more stable. Recommend hop count for v1.

B. Do we scale items/upgrade availability too, or only enemies? ER scaling is enemy-stat only;
   item placement is the AP fill's job. Keep this enemy-only; pool shaping lives in
   [SPEC-pool-builder.md] / curation.

C. Should Variant A force `opt["scale"]` globally, or require the player to also enable enemy
   rando? Forcing it is the point (so it works on vanilla-enemy seeds) but means owning the
   in-place scale pass on its own -- confirm that path is safe without a relocation map.

## Test plan

1. Dry-run the depth->tier table for a standard region_lock seed; sanity-check (start region low,
   Mountaintops/Farum high only if they're deep, NOT by geography). Dump to spoiler.
2. Bake + playtest `flat`: confirm an early-but-deep region actually fights harder than vanilla,
   and a geographically-late-but-early-in-chain region fights easier.
3. Compose with enemy_rando: confirm no double-scaling, no tier-out-of-range crash, DLC clamp.
4. Variant B: confirm bucket SpEffect applies/removes cleanly, survives save/load
   (`er-client-load-crash-poll-gate` regression), no stacking.
5. Boss check: a great-rune boss in a re-tiered region is still beatable and not trivial.

## Effort estimate

Variant A: ~1-1.5 days. The SpEffect application + tier matrix + `targetScalingSections` rewrite
ALL already exist (the `scalerandom` path); the new code is the depth->tier computation + slot_data
wiring + forcing the in-place scale pass. Variant B: ~half day, pure client, but spend the time on
picking/authoring sane global difficulty SpEffect buckets. Both gated behind real bake + playtest.
