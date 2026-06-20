# HANDOFF: Sphere-Ordered Completion Scaling — BAKER track

Status: DESIGN 2026-06-19. Pairs with SPEC-sphere-ordered-scaling.md. apworld track in flight by
another agent — DO NOT edit the apworld here (per-track files, reconcile serially). This doc is the
baker (SoulsRandomizers / C#) plan, grounded in the actual v1 code. Two pieces:

1. **Sphere bridge (v2)** — reshape enemies by AP-fill sphere of their region instead of native geo tier.
2. **enemy_rando:false** — Alaric's new ask: make completion-scaling work with the enemy pass OFF.
   Not in the SPEC; scoped here as a separate sub-track (stacks with TODO #21).

All C# patches are written here, applied + built by Alaric on Windows (ER patches run on Windows).
File line endings: EnemyRandomizer.cs = CRLF, ArchipelagoForm.cs = LF — patches handle per-file.

---

## How v1 works today (ground truth, verified in source)

- Native tier: `ScalingEffects.InitializeEldenScaling(...)` reads each enemy's actual scaling SpEffect
  and returns `ann.ScalingSections` = `{enemyId: tier}`, tier 1..MaxTier (MaxTier = 20 base, up to 35
  with DLC). EnemyRandomizer.cs L1037.
- v1 reshape block: EnemyRandomizer.cs ~L1071-1101. When `CompletionScaleMode > 0`, clones
  `ann.ScalingSections` into `targetScalingSections` and overwrites each value with
  `floor + curve(d)*(1-floor)` where `d = (section-1)/(MaxTier-1)`. flat=identity, gentle=d^1.6,
  steep=d^0.55. Forces `opt["scale"]=true`.
- Apply path: `getScalingSections(source,target,...)` (L1105) returns `sourceSection` from
  `ann.ScalingSections` and `targetSection` from `targetScalingSections`. The actual SpEffect is
  stamped in the transplant loop **L7636+** (`foreach transfer in revMapping`): for each placed
  enemy it calls `getScalingSections(enemySource, baseTarget, ...)`, looks up
  `scalingSpEffects.Areas[(sourceSection,targetSection)]`, and emits an EMEVD common-func init
  (`addCommonFuncInit("scale"/"scale2", target, {target, scaleSp})`). **This loop only runs inside
  the enemy randomization pass** — hence v1's enemy_rando constraint.
- Threading: ArchipelagoForm.cs L725-730 sets `erRando.CompletionScaleMode/FloorPct` from
  `slotData["options"]` right before `erRando.Run(...)`, gated by `randomize_enemies` (L674).

Key consequence: v1 reshapes by **native section = geography** (ER geography ≈ vanilla progression),
so a random Altus start fights softened-but-mid Altus, not tier-1. v2 fixes the *key*, not the curve.

---

## Piece 1 — Sphere bridge (v2)

### The contract with the apworld (confirm with the other agent)

apworld must emit, post-fill, into slot_data:
- `regionSphereTargets` = `{region_name: target_fraction}` — fraction in [0,1], curve+floor already
  applied in Python (keep the baker trivial, same division of labor as v1).
- `apLocationRegion` = `{ap_location_id: region_name}` — the join key. **Essential**: the baker's only
  bridge from a physical MSB map to an AP region.

`region_name` MUST be the apworld's `region_order` names (e.g. "Limgrave", "Stormveil Castle",
"Liurnia of The Lakes") — NOT the FogMod fog-area names (lowercase "limgrave"). They differ, so the
baker cannot reuse the C# fog-area table; the location-join is the robust source the SPEC mandates.

Note: `map_region_data.py` in the apworld is **runtime FieldArea ids** (region→client area id ranges),
NOT MSB map ids — it is NOT the enemy.MainMap bridge. Don't try to reuse it for this.

### Baker bridge: build mapRegion via the location-placement join

The baker already resolves every AP location to a `LocationScope`, and a scope resolves to physical
MSB map(s) through its slot keys. Verified accessor chain (LocationData.cs):

```
apLocationsToScopes[apLocId]  -> LocationScope scope          // ArchipelagoForm L450
data.Location(scope)          -> List<SlotKey>                // LocationData L71
data.Location(slotKey)        -> ItemLocation (has .Keys)     // LocationData L67
ItemLocation.Keys             -> List<LocationKey>            // each has .Entities
LocationKey.Entities          -> List<EntityId>              // EntityId.MapName = MSB map id
```

So in `RandomizeForArchipelago`, AFTER `apLocationsToScopes` is built (~L450) and BEFORE the enemy
pass (~L709), build the table:

```csharp
// v2 sphere bridge (SPEC-sphere-ordered-scaling.md). Join AP location -> physical MSB map -> AP
// region, so the enemy pass can tier by region sphere instead of native geography.
Dictionary<string, string> mapRegion = null;          // MSB map id -> region (majority vote)
Dictionary<string, double> regionSphereTargets = null;
if (((JObject)slotData["options"])?["completion_scaling_basis"]?.Value<int>() == 1
    && slotData.TryGetValue("regionSphereTargets", out var rst) && rst is JObject rstObj
    && slotData.TryGetValue("apLocationRegion", out var alr) && alr is JObject alrObj)
{
    regionSphereTargets = rstObj.ToObject<Dictionary<string, double>>();
    var apLocRegion = alrObj.ToObject<Dictionary<long, string>>();  // ap id -> region
    var mapVotes = new Dictionary<string, Dictionary<string, int>>();
    foreach (var kv in apLocRegion)
    {
        if (!apLocationsToScopes.TryGetValue(kv.Key, out var scope)) continue;
        foreach (var sk in data.Location(scope))
            foreach (var lk in data.Location(sk).Keys)
                foreach (var ent in lk.Entities ?? Enumerable.Empty<EntityId>())
                {
                    if (string.IsNullOrEmpty(ent.MapName)) continue;
                    if (!mapVotes.TryGetValue(ent.MapName, out var v))
                        mapVotes[ent.MapName] = v = new Dictionary<string,int>();
                    v[kv.Value] = v.GetValueOrDefault(kv.Value) + 1;
                }
    }
    mapRegion = mapVotes.ToDictionary(e => e.Key, e => e.Value.MaxBy(x => x.Value).Key);
}
```

Thread `mapRegion` + `regionSphereTargets` onto `erRando` next to the existing
`CompletionScaleMode/FloorPct` lines (ArchipelagoForm L728), e.g.
`erRando.MapRegion = mapRegion; erRando.RegionSphereTargets = regionSphereTargets;`.

### Baker reshape change (EnemyRandomizer.cs)

Add fields (next to `CompletionScaleMode`): `public Dictionary<string,string> MapRegion;` and
`public Dictionary<string,double> RegionSphereTargets;`.

In the v1 reshape block (~L1071), branch on basis. When sphere data is present, compute the target
**per enemy from its region** instead of from its native section:

```csharp
// v2: per-enemy region -> sphere target. defaultData[enemyId].MainMap is the MSB map.
int compMaxTier = scalingSpEffects.MaxTier;
bool sphere = MapRegion != null && RegionSphereTargets != null;
foreach (KeyValuePair<int,int> compEntry in ann.ScalingSections)
{
    int compTarget = compEntry.Key, compSection = compEntry.Value;
    if (compSection <= 0) continue;
    int compNew;
    if (sphere
        && defaultData.TryGetValue(compTarget, out var ed) && ed.MainMap != null
        && MapRegion.TryGetValue(ed.MainMap, out var rgn)
        && RegionSphereTargets.TryGetValue(rgn, out double frac))
    {
        compNew = (int)Math.Round(frac * compMaxTier);   // floor+curve already in 'frac'
    }
    else
    {
        // FALLBACK: v1 native-tier reshape (map had no AP check, or unmapped enemy).
        double compD = compMaxTier > 1 ? (compSection - 1.0)/(compMaxTier - 1.0) : 0.0;
        double compT = compFloor + compCurve(compD)*(1.0 - compFloor);
        compNew = (int)Math.Round(compT * compMaxTier);
    }
    if (compNew < 1) compNew = 1; if (compNew > compMaxTier) compNew = compMaxTier;
    targetScalingSections[compTarget] = compNew;
}
```

`defaultData` is already in scope at the reshape site (it's the arg to InitializeEldenScaling, L1037).

### Diag (extend the existing CompletionScaling diag line)

The diag patch (patch_baker_completion_scaling_diag.py) already logs up/down/same. Add, for sphere
basis: per-region resolved tier, and **count of enemy maps with no region (fallback count)** + a list
of the first ~20 unmapped maps. This is the bridge-coverage check the SPEC asks for. Emit to the
ap_bake_<stamp>.log tee.

### Option (apworld side, but baker reads it)

`completion_scaling_basis`: 0 = geographic (v1, default), 1 = sphere (v2). Baker reads it from
`slotData["options"]` (int, like the others). When basis=1 but the sphere tables are missing/empty,
the reshape silently falls back to v1 native — safe degrade.

### Risks / open

- **Map-name format**: `EntityId.MapName` vs `defaultData[].MainMap` must be the same string form.
  Overworld tiles (m60/m61) are shared and fine-grained; legacy dungeons (m10_..) are clean. Verify
  with the diag's unmapped-map dump on first bake; if overworld tiles mismatch, normalize both sides.
- **Sphere lumpiness**: handled apworld-side (dense-rank / region_order tiebreak). Baker just consumes
  the fraction.
- **Bosses / great runes**: same carve-out question as v1 — defer to playtest.
- **Determinism**: sphere is fill-dependent but deterministic; apworld should dump region→sphere to
  the spoiler/gendiag for inspection.

---

## Piece 2 — enemy_rando:false (Alaric's ask, NOT in SPEC)

### Why it's blocked today

The scaling SpEffect is stamped only inside the transplant loop (EnemyRandomizer.cs L7636+,
`foreach transfer in revMapping`). With `randomize_enemies` off, `EnemyRandomizer.Run` is never even
called (ArchipelagoForm L674 gates the whole block), so nothing scales. This is the same root as
TODO #21 "decouple from enemy_rando".

### Recommended: Option A — a standalone "scale-only" pass

Add `EnemyRandomizer.RunScaleOnly(opt)` (or a flag on Run) that does the minimum:

1. Load the ER maps + build `defaultData`/`infos` (reuse the early part of `RunGame` that reads MSBs
   — factor it into a shared helper so both paths use it).
2. `ann.ScalingSections = scaling.InitializeEldenScaling(defaultData, ...)`.
3. Run the v1/v2 reshape block to fill `targetScalingSections` (identical code — factor it into a
   private method `BuildTargetScalingSections()` reused by both Run and RunScaleOnly).
4. Build an **identity self-map**: for every scalable enemy entity, source = target = itself.
5. Factor the scaling-apply body (the `opt["scale"]` chunk at L7727-7775: pick scale/scale2, lookup
   `scalingSpEffects.Areas[(src,tgt)]`, `addCommonFuncInit`) into a method
   `ApplyScaling(int source, int target, ...)` and call it per enemy with src==tgt. Since
   reshaped tier != native tier for non-flat curves, the `(native, reshaped)` SpEffect gets applied;
   when equal, the existing `sourceSection==targetSection` branch no-ops cleanly.
6. Write the touched EMEVDs (reuse RunGame's EMEVD/MSB write tail).

Then in ArchipelagoForm, add an else-branch to the L674 gate:

```csharp
if (options.GetValueOrDefault("randomize_enemies", false)) { /* existing */ }
else if (type == FromGame.ER
         && (((JObject)slotData["options"])?["completion_scaling"]?.Value<int>() ?? 0) > 0)
{
    // build erRando exactly like the randomize branch (events.txt, enemyEvents, fields,
    // mapRegion/regionSphereTargets), then:
    erRando.RunScaleOnly(opt);
}
```

Effort: medium. The reshape + apply logic already exists; the work is **factoring** the MSB-load,
reshape, and apply chunks out of the monolithic `RunGame`/transplant loop so a scale-only path can
call them without doing a shuffle. Touches the hot enemy-write code, so guard with the existing
sandbox-copy compile + idempotent-anchor checks, and bake-test both enemy_rando on AND off.

### Rejected: Option B — identity shuffle

Running the full enemy randomizer with a "map everything to itself" preset would scale in place but
drags in the entire (slow) enemy-write + MSB rewrite, risks the deploy-hygiene stale-MSB leak
(tools\deploy_hygiene.ps1), and "identity" isn't truly a no-op in that pass. Not worth it vs Option A.

### Caveat

Scaling DOWN with enemy_rando off changes vanilla encounters the player may expect unmodified — fine
for steep (down=0 by construction) but gentle can soften early bosses. Call it out in the option help.

---

## Build order

1. apworld (other agent): region_sphere compute + `regionSphereTargets` + `apLocationRegion` +
   `completion_scaling_basis` option + spoiler dump. gen-test.
2. baker Piece 1: mapRegion join (ArchipelagoForm) + per-enemy region reshape + fallback + diag.
   `patch_baker_sphere_scaling.py`. Sandbox-compile, then Alaric applies + builds on Windows. bake-test
   with enemy_rando ON + basis=sphere; check unmapped-map count in ap_bake log.
3. baker Piece 2 (separate patch, optional/independent): factor scale-only pass + ArchipelagoForm
   else-branch. `patch_baker_scaleonly_pass.py`. bake-test enemy_rando OFF + completion_scaling on.
4. playtest: random Altus start, basis=sphere → Altus mobs should feel Limgrave-tier.

Patches to be written next (not yet authored): `patch_baker_sphere_scaling.py`,
`patch_baker_scaleonly_pass.py`. v1 (geographic) stays the cheap default.
