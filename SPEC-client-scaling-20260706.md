# SPEC — client scaling vs greenfield emission (I2, 2026-07-06)

**Verdict: NO er-logic/scaling.rs change is required.** Greenfield now emits the exact shape the
client already parses; completion scaling should arm on the next greenfield connect once Alaric
rebuilds the client for the other Wave-2 pieces (no scaling-specific rebuild needed beyond that).

## What greenfield now emits (producer: `greenfield/eldenring/features/scaling.py`)

- `regionSphereTargetRanges = [[lo, hi, target], ...]` — TOP-LEVEL, i32 triples, **emitted every
  seed** (completion_scaling is always on in greenfield, curve id 4).
  - `lo == hi ==` the region's 5-digit play_region bucket (`runtime play_region_id / 100`), reused
    verbatim from `features/area_locks.REGION_PLAY_IDS` — the SAME bucket space `areaLockFlags`
    speaks. One triple per bucket of each KEPT region.
  - `target` = the region's progression depth: position along `region_spine.SPINE` **within the
    kept set**, normalized to `0..10000` (deepest kept region == 10000; single-region seed == 0 ==
    floor everywhere, by design). Deterministic, independent of `num_regions_order` roll order.
  - Example (gen-verified, num_regions=4 rolled + Leyndell): Limgrave buckets → 0, Caelid → 2500,
    Dragonbarrow → 5000, Mt. Gelmir (63001/16000/39200) → 7500, Leyndell (11000/11050/35000/19000)
    → 10000.
- `regionSphereTargets` stays `{}` (core.py transitional emission; contract-declared
  `{str(i32): i32}`). The client's `i32_i32_map` parses `{}` to empty and falls through to ranges —
  exactly the `parse_scaling_config` path (scaling.rs:148-165). No dup-key: features/scaling.py
  deliberately does NOT emit the flat key.
- Gate/floor already land under `sd["options"]` via core's options echo (I1):
  `options.completion_scaling = 4` (truthy → `parse_bool_option` passes),
  `options.completion_scaling_floor` (f64 → `floor_tier_from_multiplier`). Verified present in the
  generated seed.

## Client match, point by point (er-logic/src/scaling.rs `parse_scaling_config`, L144-188)

| client read | greenfield emission | status |
|---|---|---|
| `options.completion_scaling` (parse_bool_option) | int 4 (truthy) | ✅ arms |
| `regionSphereTargets` via `i32_i32_map` | `{}` | ✅ empty, falls to ranges |
| `regionSphereTargetRanges` rows of exactly 3 i64s | `[[i32,i32,i32], ...]`, non-empty | ✅ `region_ranges` non-empty → does NOT refuse-to-arm (H4 guard passes) |
| `max_target` (normalization) | max emitted target == 10000 (kept-set normalized) | ✅ full 0..1 curve over the seed |
| `completionScalingBasis` | int 1 (core.py) | ✅ Sphere |
| `options.completion_scaling_floor` as f64 HP multiplier | option value (0..50) | ✅ (unchanged semantics) |
| lookup space: `player.play_region_id / 100` (client scaling.rs:75) | 5-digit REGION_PLAY_IDS buckets | ✅ for all 7-digit runtime prs (overworld + interiors ≥ 1,000,000) — see observation below |

## One open OBSERVATION (client-side, NOT a required change, NOT scaling-blocking)

`eldenring-archipelago/src/scaling.rs:75` normalizes the live id **unconditionally** (`pr / 100`),
while the region-lock kick (region.rs:231/321) normalizes **conditionally** (`/100` only when
`pr >= 1_000_000`). The two agree for every base-game bucket (overworld 61000-65002 and interiors
10000+ both come out as the 5-digit bucket). They can only diverge for runtime prs `< 1_000_000`
that are NOT already 5-digit buckets — i.e. the DLC buckets 6800-6950 IF the live DLC
play_region_id turns out to be `bucket*100 + sub` (6-digit, e.g. 680012): scaling would resolve
6800 ✅ while the kick compares 680012 vs [6800,6800] ❌ (an area_locks concern, pre-existing, not
introduced here). If instead live DLC prs are literally 6800, the kick matches ✅ and scaling
resolves 68 ❌ (DLC regions would silently sit at floor tier). One in-game kick-watch log line in a
DLC region settles which; the contingent one-line fix is to make the two normalizations identical.
Base game is unaffected either way.

## Validation done (sandbox, GF_CI_HOME=~/.gfci-i1 env)

- Isolated GEN (ci-linux step c): PASS — AP zip produced; the strict contract validator (runs
  inside fill_slot_data) accepted the shapes.
- Seed slot_data inspected: `regionSphereTargetRanges` present, 12 triples (pasted above),
  `regionSphereTargets == {}`, options echo intact.
- World suite: full `worlds/eldenring/tests/` (minus test_gf_data.py, run separately: 21 OK)
  green — 369 tests incl. the updated `test_gf_slot_data_fixture.py` (regionSphereTargetRanges
  removed from `_CONTRACT_NOT_EMITTED`).
- Fuzz sample: 8/8 clean (100%).
- NOT run here: cargo (per plan — Alaric's step). No Rust file was touched by I2.
