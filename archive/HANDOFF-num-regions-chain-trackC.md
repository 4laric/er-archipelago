# HANDOFF — Track C: Baker sphere→region→enemy bridge (TODO #22)

Spec: SPEC-num-regions-chain.md (contract §4 is frozen). Track owner edits ONLY this file + the patch below.
Deliverable: `patch_baker_sphere_scaling_bridge.py` (+ scale-only path).

## Scope (files this track may touch)
- `SoulsRandomizers/RandomizerCommon/ArchipelagoForm.cs` — read `completionScalingBasis` + `regionSphereTargets`.
- `SoulsRandomizers/RandomizerCommon/EnemyRandomizer.cs` — scale-only pass (enemy_rando OFF) per-region reshape.
- MSB→AP-region map (reuse the boss-attribution map if available).
DO NOT touch any apworld `.py` (Tracks A/B). Can MOCK `regionSphereTargets` to develop independently.

## Steps
- [x] ArchipelagoForm: read `slotData["completionScalingBasis"]` + `slotData["regionSphereTargets"]` (top-level keys; threaded onto BOTH enemy-rando-ON and scale-only callsites).
- [~] Build MSB-map → AP region — **STUBBED** (no ready-made reuse; see "MSB→region approach" below).
- [x] When basis=sphere: override each enemy's `compT` with `regionSphereTargets[region]`. Fallback to v1 geographic / floor for unmapped regions.
- [x] Routes through the scale-only pass (the reshape loop fills `targetScalingSections`, which the scale-only apply block already consumes — no separate scale-only edit needed).

## Contract consumed (§4)
`completionScalingBasis` (int), `regionSphereTargets` ({AP region name: float [0,1]}). Region names are AP region names — C owns the MSB→AP-region mapping. NOTE: the float is the **already curved+floored** target tier fraction; the baker only does `round(target * MaxTier)` for sphere basis (geographic basis still applies curve+floor in-baker as v1).

## Status / notes — APPLIED to /tmp dry-run 2026-06-19; needs Windows build + bake

`patch_baker_sphere_scaling_bridge.py` (repo root) — CRLF-safe byte splice, idempotent, per-file line endings preserved (ER=CRLF, AF=LF). **PREREQ:** apply `patch_baker_completion_scaling.py` + `patch_baker_completion_scaling_diag.py` + `patch_baker_scaleonly_pass.py` FIRST (already applied in current source; the bridge FAILs loudly if their anchors are missing).

### .cs anchors used
**EnemyRandomizer.cs (CRLF, +88 lines, 0 removed):**
- E1 fields — after `public int CompletionScaleFloorPct = 0;` → adds `CompletionScaleBasis` (int) + `RegionSphereTargets` (`Dictionary<string,double>`).
- `compSphereHits` decl — before `double compFloor = Math.Max(0, Math.Min(50, CompletionScaleFloorPct)) / 100.0;` (opens the reshape body).
- E2 override — REPLACES the single `double compT = compFloor + compCurve(compD) * (1.0 - compFloor);` line, keeping it and appending the sphere override (computes geographic `compT` first, then overrides with the region target when basis=1 + region resolves + present in table; clamps to [0,1]).
- E3 diag — after the existing `CompletionScaling: mode=... retiered enemies` `Console.WriteLine`, prints `CompletionScaling sphere basis: reshaped {N} enemies by region target (targets=...)`.
- Resolver — before `bool getScalingSections(int source, int target, ...)` → inserts local fn `string CompApRegionForMap(string msbMap)` (sibling scope, visible to the reshape loop).

**ArchipelagoForm.cs (LF, +20 lines, 0 removed):** both `*.CompletionScaleFloorPct = (slotData["options"] as JObject)?...` assignments (the enemy-rando-ON `erRando` callsite ~L729 and the scale-only `scaleRando` callsite ~L767) get a sphere block appended that reads the two top-level keys via `slotData.TryGetValue(...)` (absent on pre-contract seeds ⇒ basis 0 = v1) and builds `RegionSphereTargets` from the `regionSphereTargets` JObject.

### MSB→region approach: **STUBBED** (not reused)
No ready-made reuse exists for what this needs:
- **BossAttribution.cs** builds region membership at runtime from per-check positions + AP `Area` strings threaded in from ArchipelagoForm (`CheckPt`/`NearestRegion`), and only for the boss roster. Those checks/positions are NOT in scope inside `EnemyRandomizer.Run`, and we need ALL enemies, keyed by entity ID. Also gated on `dungeon_sweep == bosses`.
- **map_region_data.REGIONS** (apworld) is keyed on runtime **FieldArea ids** (61000…) read by the client @0xE4 — NOT MSB ids, so not directly usable to resolve `EnemyInfo.Map`.
- **annotations.txt `AreaAnnotation.Maps/MainMaps`** give MSB→internal-area-name, but `Archipelago` (the AP abbrev) is null for most areas, and those names are not the apworld region_order names anyway.

So the resolver `CompApRegionForMap(string msbMap)` is a hand-written stub keyed on `EnemyInfo.Map`: an exact switch for legacy-dungeon / interior MSBs (`m10_00_00_00`→Stormveil, m11/m13/m14/m15/m16/m18/m19, m12 underground quadrants) plus a coarse `m60_XX_YY_00` overworld-tile band classifier. Unmapped maps return null ⇒ v1 geographic fallback (safe, just not sphere-shaped).

### Remaining for Windows
1. **Finish `CompApRegionForMap`** — this is the load-bearing TODO. The region NAMES must match the apworld's `region_order` (the keys of `regionSphereTargets`) EXACTLY, else every lookup misses and you stay on geographic. To get an authoritative MSB→AP-region table:
   - Dump `regionSphereTargets` keys from a real seed's slot_data (or read `region_order` in `Archipelago/worlds/eldenring/__init__.py` / `region_spine.py`), then map each MSB tile/dungeon to one of those names. Cross-check against `map_region_data.WORLD_MAP_PIECE_FLAGS` and the FogMod tile grid for the `m60_XX_YY` bands (the current `>=51/47/43` thresholds + the `compTx>=47`→Caelid split are GUESSES).
   - Replace the m60 band heuristic with the apworld's actual tile→region grouping if one exists; otherwise tighten the thresholds from the world grid.
2. **Build** SoulsRandomizers (Release), then an **enemy_rando-OFF** bake with `completionScalingBasis=1`.
3. **Confirm** the bake log shows `CompletionScaling sphere basis: reshaped N enemies by region target (targets=M)` with N>0 and M = number of regions in the table. If N=0, the resolver names don't match the apworld region names (step 1).
4. In-game: an early chain link should be easier than a late link.

### Dry-run result (sandbox)
Applied to copies in `/tmp/trackC/`: applies cleanly, idempotent on re-run (`[skip] … already has sphere bridge`), ER stays pure-CRLF, AF stays pure-LF, both whole files brace/paren/bracket-balanced after patch. CANNOT compile C# here — splice landed at the right anchors and inserted C# verified balanced by eye + count. Do NOT trust until it compiles on Windows.
