# SPEC: `num_regions` — random short Capital run

## Goal
A short (~3–4 hour) Elden Ring AP run made of a **random** subset of overworld majors, instead of
the deterministic first‑N spine that `region_count` keeps. The region holding the end‑goal boss is
always included; everything else is sealed. Reachability is by **warp** (region‑lock grace bundles),
so the random set does **not** need to form a geographically contiguous chain.

This is the randomized sibling of `region_count` (`SPEC-region-count-morgott.md`) and reuses the
exact same `_spine_*` seal machinery.

## Decisions (per Alaric, 2026‑06‑19)
- **The generator picks the count, not the player.** `num_regions` is exposed as a tunable Range for
  flexibility, but the recommended/intended value for a 3–4 hr run is **4** — that is the number I
  picked. Set higher (5–6) if runs feel short. The *selection* of which majors are kept is random
  per seed.
- **Warp reachability only.** The kept majors are reached by warping in on each region's own lock
  (region fusion / grace bundles), so a non‑contiguous random set is fine. `num_regions` therefore
  **forces `region_access = warp`**.
- **Goal region always kept.** For v1 the supported goal is the **Capital** ending (Morgott in
  Leyndell), whose capstone (`GOAL_CAPSTONE_REGIONS`) is always kept, exactly like `region_count`.

## What counts toward `num_regions`
`num_regions` = total live overworld majors **including** the two always‑kept anchors:
1. **Limgrave** — the free sphere‑1 hub (Torrent / leveling / Roundtable services connect here; the
   warp graph is Limgrave‑rooted).
2. **Leyndell / Morgott capstone** — the goal region.

So `num_regions = 4` ⇒ Limgrave + Leyndell + **2 randomly rolled** middle majors.

The middle‑major universe is the `region_count` SPINE steps 2–8:
Weeping Peninsula, Stormveil Castle, Liurnia, Caelid, Dragonbarrow, Altus, Mt. Gelmir.
(Legacy dungeons fold into their overworld region as in the SPINE: Raya Lucaria→Liurnia,
Volcano Manor→Mt. Gelmir, Redmane→Caelid.)

## Great‑rune floor
Leyndell is gated by `great_runes_required` great runes (default 2). The four great‑rune bosses live
in SPINE steps {Stormveil/Godrick, Liurnia/Rennala, Caelid/Radahn, Mt. Gelmir/Rykard}. The roller
therefore **guarantees `great_runes_required` rune‑boss majors** are in the kept set, and raises the
effective count if `num_regions` is set too low to fit them:

```
effective = clamp( max(num_regions, 2 + great_runes_required), 2, 2 + 7 )
```

Because access is **warp**, there is *no* Altus‑route requirement (unlike the geographic
`region_count` floor, which forces Altus = step 7 as the only walk into Leyndell). A warning fires if
the count was raised. `great_runes_required > 4` is rejected (only 4 pre‑Leyndell rune bosses exist).

Worked floor examples (verified):

| num_regions | great_runes_required | effective | middle majors rolled | rune majors guaranteed |
|---|---|---|---|---|
| 4 | 2 | 4 | 2 | 2 |
| 3 | 2 | 4 | 2 | 2 |
| 5 | 2 | 5 | 3 | ≥2 |
| 4 | 3 | 5 | 3 | 3 |
| 2 | 4 | 6 | 4 | 4 |

## Seal mechanism (unchanged — reused from `region_count`)
Identical to the Capital spine / Godrick / Messmer mini‑campaigns:
1. `compute_num_regions_scope()` returns `(kept_regions, sealed_regions, kept_locks, sealed_locks,
   effective)`.
2. `_spine_active = True`; sealed locks have `item_table[lock].inject = False` (pulled from the pool,
   so their gated entrance can never open).
3. Sealed‑region checks become locked‑vanilla **events** in `create_region()` (downgraded to
   `filler` since they're unreachable).
4. `_is_location_available()` excludes the sealed location names from the randomized pool.

## Compatibility / guards
- **Capital goal only** (`ending_condition = capital`, value 4). Other goals ⇒ warn + ignore (the
  goal boss would sit past the sealed wall). `godrick` / `messmer` already give fixed short runs.
- **Lock‑based world logic** (`region_lock` / `region_lock_bosses`). Otherwise ⇒ warn + ignore
  (nothing to seal without locks).
- **Mutually exclusive** with `region_count` / the messmer / godrick seal goals — if one of those is
  already active, `num_regions` warns and yields.
- **`random_start_region`** already defers to any active spine seal, so it yields to `num_regions`
  too (they'd both want to reshape the kept set / the hub).
- DLC: if `enable_dlc` is on, all DLC regions are sealed wholesale (same as Godrick) — the Capital
  goal ignores the DLC.

## Files touched
- `region_spine.py` — `NUM_REGIONS_MIDDLE_STEPS`, `num_regions_floor()`, `compute_num_regions_scope()`.
- `options.py` — `class NumRegions(Range)` (0–9, default 0) + `num_regions: NumRegions` dataclass field.
- `__init__.py` — resolution block in `generate_early()` (after the Godrick block, before the
  lock‑injection block), forces `region_access = warp`.

Applied by `patch_apworld_num_regions.py` (CRLF‑safe, idempotent).

## Status
WRITTEN 2026‑06‑19. `region_spine.py` + `__init__.py` patched copies compile clean in the sandbox;
`compute_num_regions_scope()` unit‑tested across the floor matrix (Limgrave+Leyndell always kept,
rune floor always met, sealed = disjoint complement). **`options.py` not sandbox‑verifiable** (mount
truncates the read of that file) — apply + build + gen‑test on Windows. See `HANDOFF-num-regions.md`.

## Future work
- Extend beyond the Capital goal: a goal‑region resolver for `final_boss` / `elden_beast` (the
  endgame chain Leyndell‑Ashen → Farum Azula is a multi‑region mandatory tail) and for a DLC variant.
- Optional "generator rolls the count" mode (a Toggle that rolls `num_regions` in a 4–6 band) if
  Alaric wants the count itself randomized rather than fixed at the recommended value.
