# SPEC: Sphere-Ordered Completion Scaling (start-relative, the "real" version)

Status: DRAFT 2026-06-19. v2 of completion scaling (SPEC-completion-scaling.md). The shipped v1
reshapes each enemy by its NATIVE GEOGRAPHIC tier -> it's start-UNAWARE (a random Altus start still
fights softened-but-mid-game Altus, not Limgrave-tier). Alaric wants tiers ordered by AP SPHERE so
the rolled start region = tier 1 and difficulty climbs with progression, not geography.

## What changes vs v1

v1: enemy tier = curve(nativeGeoTier). Fixed, geography-keyed, start-unaware.
v2: enemy tier = curve(sphere(enemy's region) / maxSphere). The region's AP fill SPHERE drives the
    tier. Random start in Altus -> Altus is sphere 1 -> its enemies are tier 1; regions unlocked later
    climb. Same curve/floor knobs (flat/gentle/steep) apply on top of the sphere fraction.

## Data flow (3 layers)

### apworld (post-fill)
1. After fill, compute per-region sphere: `for i, sphere in enumerate(self.multiworld.get_spheres()):
   for loc in sphere: region_sphere[loc.parent_region.name] = min(existing, i)`. A region's sphere =
   the earliest sphere any of its locations is reachable. Seed-specific, deterministic.
2. Normalize: depth = region_sphere / max_sphere; target = floor + curve(depth)*(1-floor)
   (curve = the existing flat/gentle/steep). Emit `regionSphereTargets` = {region_name: target_fraction}
   in slot_data. (This RESURRECTS the per-region target table v1 dropped -- but keyed by SPHERE now.)
3. ALSO emit the join key the baker needs: `apLocationRegion` = {ap_location_id: region_name} (the
   apworld trivially knows location.parent_region.name). Needed for the enemy->region bridge below.

### baker (the crux: enemy -> region bridge)
The baker reshapes per-ENEMY (ann.ScalingSections, keyed by enemy id) but tiers are now per-REGION.
Enemies are keyed by MSB MainMap; AP regions are an apworld concept. Bridge:
4. The baker already places each AP location into a specific MSB map (item-lot write). Join:
   for each AP location it places into map M -> region = apLocationRegion[loc] -> record M -> region.
   Build `mapRegion` = {MSB map name: region}. (Reuse any existing map->region table in the randomizer
   if one exists -- FogMod-style area maps -- else this location-join is the robust source.)
5. For each enemy: region = mapRegion[enemy.MainMap]; tier = clamp(round(regionSphereTargets[region]
   * MaxTier), 1, MaxTier). Fallback to the v1 native-tier reshape if the map has no AP location
   (some maps host enemies but no checks) -- OR nearest-mapped-region.

### option
6. Extend CompletionScaling: add `option_sphere` (or a sub-toggle `completion_scaling_basis:
   geographic|sphere`). geographic = v1 (current), sphere = v2. Keep v1 as the cheap default.

## Why this is the right metric

AP sphere IS the progression order. Under region locks, a region's sphere ~ when you get its lock, so
sphere-ordering = "difficulty by how deep you are," start-relative for free (random start precollects
its lock -> sphere 1). No special start-awareness code -- it falls out of the fill.

## Open questions / risks

- **Sphere granularity**: spheres can be lumpy (many regions in one sphere -> tier plateaus). Mitigate
  by ranking regions by sphere then spreading over tiers (dense-rank), or blend sphere with a tiebreak
  (region_order) so same-sphere regions still spread. Decide in playtest.
- **Bridge coverage**: maps with enemies but NO AP checks get no region from the location-join -> need
  the native-tier fallback or a hand map->region table for those. Enumerate during bake (log unmapped maps).
- **enemy_rando still required** (same v1 constraint -- reshape lives in the enemy pass). The TODO #21
  "decouple from enemy_rando" stacks under this too.
- **Bosses**: same great-rune carve-out question as v1.
- **Determinism**: sphere is fill-dependent but deterministic per seed; emit region->sphere into the
  spoiler/diag so it's inspectable.

## Build order

1. apworld: region_sphere compute (post-fill) + regionSphereTargets + apLocationRegion emission +
   the option. gen-test (assert table emitted, sane sphere ordering for a known seed).
2. baker: mapRegion join + per-enemy region lookup + reshape; fallback to v1. ap_bake log: per-region
   tier + count of unmapped maps. bake-test.
3. playtest: random Altus start with sphere basis -> Altus mobs should feel Limgrave-tier.

Supersedes the "start-relative" open item in SPEC-completion-scaling.md. v1 (geographic) stays as the
simpler default; sphere is the opt-in "true completion order" mode.
