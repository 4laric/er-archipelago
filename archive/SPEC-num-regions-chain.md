# SPEC — num_regions Chain Mode + Sphere-Ordered Scaling

Status: DRAFT (2026-06-19). Owner: Alaric. Frozen contract in §4 — do not edit without bumping all tracks.

## 1. Problem
`num_regions` (random short Capital run) is FLAT in fill-sphere terms. `region_access: warp` + the free Limgrave hub + `graces_per_region: 0` mean every kept region is reachable the instant you hold its lock, and the locks themselves land in sphere-1 spots (hub / Roundtable Twin Maiden shop — especially under `important_locations: Shop`). Result: all N kept regions resolve to sphere ~1, `get_spheres()` is flat, and `completion_scaling_basis: sphere` has no gradient to tier across. The run plays "go-mode from sphere 1" (e.g. seed 21761386509934715396: every lock + 2 great runes in the opening shop).

## 2. Goal
Force the N kept regions into a linear CHAIN so the fill spheres become 1..N, then let sphere-ordered completion scaling tier each region by chain depth. Keep `region_access: warp` (a random non-contiguous subset has no zero-item geographic route).

## 3. Core mechanism — lock breadcrumb
New opt-in toggle `num_regions_chain` (default off; only meaningful with `num_regions > 0` + `ending_condition: capital` + region_lock). When active:

1. Order the kept regions: Limgrave is link 0 (free hub, sphere 1). The rolled middle majors form links 1..N-2 in a random order. Altus is pinned as the LAST middle link (capstone tail, see §5). Leyndell is the terminus.
2. Breadcrumb each link's lock into its PREDECESSOR: place `lock_{k+1}` inside region k, hosted on region k's mainboss drop (already tagged by `dungeon_sweep: bosses`). `lock_1` is precollected or placed in the hub.
3. Breadcrumbed locks LEAVE the random pool (fixed placement). Keep the pool count-neutral (the freed slot takes filler).

Resulting spheres: hub=1, region1=1, region1.boss→lock2→region2=2, … regionN-1.boss→lockN→regionN=N, then Leyndell. A clean 1..N ladder. Random order is intentional — sphere basis is start-relative, so each seed's difficulty curve follows the rolled order.

## 4. FROZEN WIRE CONTRACT (slot_data) — the seam between tracks
Already defined by `patch_apworld_completion_scaling.py` + `patch_apworld_sphere_scaling.py`. All tracks build against this; changing it = bump A+B+C together.

| Key | Location | Type | Meaning |
|-----|----------|------|---------|
| `completion_scaling` | `slot_data["options"]` | int | 0 off, 1 gentle, 2 steep… |
| `completion_scaling_floor` | `slot_data["options"]` | int | min tier as % of MaxTier (0..50) |
| `completionScalingBasis` | `slot_data` (top level) | int | 0 geographic, 1 sphere |
| `regionSphereTargets` | `slot_data` (top level) | `{ "<AP region name>": float }` | per-region target, [0.0,1.0], 4dp |

`target = floor + curve(region_sphere / maxSphere) * (1 - floor)`, where `region_sphere` = earliest AP fill sphere among that region's locations (0 ≈ easiest, 1 ≈ MaxTier). Diag artifact: `Archipelago/worlds/eldenring/ER_SPHERE_TIERS.txt` (`region\tsphere\ttarget`, sorted by sphere). Region names are the apworld AP region names — C must map MSB→AP-region.

## 5. Capstone tail
Leyndell has no lock (great-rune gated, `__init__.py` L2072) and is reached only geographically Altus → Capital Outskirts → Leyndell. So the chain TERMINATES Altus → Leyndell: pin Altus last among middles. ≥2 great runes must be collectable before Leyndell — the rune-floor already keeps ≥2 rune regions, all of which precede Leyndell; leave great runes in the randomized pool (the chain forces them into the unlocked prefix) or breadcrumb them too. (Optional cleaner alt: add `Warp To Leyndell` gated on the final lock + 2 runes, decoupling from Altus geography — more work, defer.)

## 6. Tracks (parallel)

### Track A — Apworld chain placement
- Deliverable: `patch_apworld_num_regions_chain.py` (+ a `region_spine.py` chain-order helper).
- Files: `region_spine.py` (order helper), `__init__.py` (num_regions resolution block ~L221-258 region; `_region_lock_warp_access` ~L2234), `options.py` (new `num_regions_chain` toggle).
- Depends on: nothing (contract frozen).
- Produces: linear `get_spheres()` (1..N). NO new slot_data keys.
- Anchor region: the num_regions block + warp helper — DISJOINT from B's `fill_slot_data` anchors.

### Track B — Apworld sphere emission
- Deliverable: apply `patch_apworld_completion_scaling.py` THEN `patch_apworld_sphere_scaling.py`; extend ONLY if emission is gated on `enemy_rando` (it must emit with `enemy_rando` OFF — these runs are enemy-OFF).
- Files: `__init__.py` (`fill_slot_data` ~L4540), `options.py`.
- Depends on: nothing for the code; MEANINGFUL only after A lands (until then targets ~flat — that's expected, not a bug).
- Produces/owns: the four contract keys in §4.
- Anchor region: `fill_slot_data` — DISJOINT from A.

### Track C — Baker sphere→region→enemy bridge (TODO #22)
- Deliverable: `patch_baker_sphere_scaling_bridge.py` (+ scale-only path for enemy-OFF).
- Files: `SoulsRandomizers/RandomizerCommon/ArchipelagoForm.cs`, `EnemyRandomizer.cs` (scale-only pass), MSB→region map.
- Depends on: contract §4 only — can mock `regionSphereTargets` and build independently.
- Consumes: `completionScalingBasis` + `regionSphereTargets`.
- Notes: baker today reads `completion_scaling` + `_floor` only (`ArchipelagoForm.cs` L728/729/756/757), NOT `basis`, NOT `regionSphereTargets`; and `enemy_rando` is OFF, so it runs the scale-only pass (`patch_baker_scaleonly_pass.py`). Build MSB→AP-region (reuse the boss-attribution map), reshape each enemy to `regionSphereTargets[region]` using the same curve as v1; fallback to v1 geographic / floor for unmapped regions.

## 7. Application order (Windows)
Apply A → B → C patch files, then `.\build.ps1 -Randomizer -Generate` to gen-test A+B, then a full enemy-OFF bake to exercise C. Anchors are disjoint, so order within A/B is not strict; apply A then B then C for clarity.

## 8. Parallelization hygiene
- Each track edits its OWN new patch file + its OWN `HANDOFF-num-regions-chain-track{A,B,C}.md`. NEVER co-edit this SPEC or a shared TODO (clobber rule — see memory).
- `__init__.py` is touched by A and B but in DISJOINT anchor regions; patches byte-splice serially on Windows, so there is no live co-edit. If an anchor moves, the second patch reports `[FAIL] anchor not found` rather than corrupting the file — safe to reorder/retry.
- Reconcile serially: once all three patch files exist, apply A,B,C in order and gen/bake once.

## 9. Interactions / risks
- `soft_progression` × `smithing_bell` bug: a chain Capital run still routes through Capital Outskirts' bell gate. Keep `patch_apworld_softprog_bellgate_fix.py` applied or run `smithing_bell` off, else "unbeatable".
- The num_regions floor raises effective N (e.g. 4→5) and force-keeps Altus; chain length = effective N; Altus pinned last.
- Breadcrumb host needs a guaranteed reachable check per region; if a region's mainboss drop is sealed/missing, fall back to any always-present region check.
- Region naming must match across A/B emit and C consume (AP region names).

## 10. Verification
- A: gen-test; spoiler Playthrough shows N ascending spheres (≈one region per sphere), each region's lock found in the PRIOR region's boss; goal reachable.
- B: `ER_SPHERE_TIERS.txt` present with a 1..N gradient; slot_data carries `completionScalingBasis: 1` + non-empty `regionSphereTargets`.
- C: bake log reports "sphere basis: reshaped X enemies by region target"; in-game an early link is easier than a late link.
- Integrated: one seed end-to-end; difficulty visibly ramps along the chain.
