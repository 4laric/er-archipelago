# WIRING — Region capstone model implementation plan (2026-07-08)

Build plan for SPEC-region-capstone-model-20260708.md. Ordered, parallelized, with the
serial bottleneck, the sandbox-vs-Windows split, and the Fable-handoff boundaries called
out. Scope here = **DLC re-carve + the capstone primitive generalization**. The base-game
re-carve (fold Raya Lucaria -> Liurnia, Leyndell -> Altus + capstone keys) is the larger
region-spine surgery tracked in er-region-spine-surgery-spec; it runs as a parallel track on
the same primitive and is NOT gated by this plan.

## 0. Ground truth (what the code is today)

- **Region set** lives in three co-located places that must move together:
  `data.REGIONS`, `region_spine.SPINE`, `region_spine.DLC_REGIONS`. Current DLC set is a
  coarse 6: `Land of Shadow, Belurat, Scadu Altus, Shadow Keep, Jagged Peak, Abyssal Woods`.
- **Tile -> region** is assigned in `gen_data.py` via `REGION_MAP` (name remap) + grace
  anchors + per-map-id overrides. Today's carve is wrong for the spec: `Land of Shadow` is a
  catch-all (Gravesite Plain, Cerulean Coast, Enir-Ilim, Stone Coffin Fissure all map to it);
  Castle Ensis -> Belurat; Church of the Bud (Romina) -> Scadu Altus; Enir-Ilim -> Land of
  Shadow. There is **no** `Ancient Ruins of Rauh` or `Enir-Ilim` region yet.
- **Bosses** are generated into `boss_data.py` (`REGION_BOSSES {region: [(ap_id, flag,
  reward)]}`) by joining `method=boss_arena` rows to remembrance flags. Consequence of the
  coarse carve: Rellana (Twin Moon Knight) sits under **Belurat**, Radahn (God and a Lord)
  under **Land of Shadow**, Romina under **Scadu Altus**. **Golden Hippopotamus has no
  remembrance**, so it is absent from `REGION_BOSSES` entirely — Scadu Altus's capstone must
  be added by hand.
- **The lock/release machinery** already exists in `features/boss_locks.py` (mode B):
  `Boss Key: <Boss>` progression item, `DUNGEON_SWEEP_FLAGS` (boss-defeat flag -> members),
  `sweepLockGates` (flag -> Boss Key, defers release until key arrives). The **location-keyed
  `DUNGEON_SWEEPS`** variant that would let a boss release its *whole region's* checks is
  emitted **empty** — it needs an ItemLotParam boss-reward-location join. That join is the
  main missing mechanism.
- **`boss_data.py` / `boss_sweeps.py` are generated from artifacts that are filter-repo'd
  out of the public repo.** So any step that re-runs `gen_data.py` is **Windows-side / needs
  the artifacts staged** — it cannot run in the sandbox. Pure-Python feature/test code CAN
  run in the sandbox via `greenfield/provision-linux-env.sh` + `git archive`.

## 1. The dependency DAG (maps to tasks #3-#10)

```
        #3 SERIAL spine/region registration (Opus-owned; shared files)
        (data.REGIONS + region_spine.SPINE/DLC_REGIONS + gen_data.REGION_MAP)
              |
     +--------+-----------------+---------------------+
     v                          v                     v
 #4 regen boss_data +       #5 DLC region-         (base-game re-carve track,
    assign capstones           correctness tests      er-region-spine-surgery,
    (Windows/artifacts)        (sandbox)               parallel, own primitive)
     |         |
     v         v
 #7 boss_locks   #6 region-wide sweep member join
    DLC un-scope    (ItemLotParam location-keyed DUNGEON_SWEEPS)
    + per-boss flag  (Windows/artifacts)
     |
     v
 #9 client Rust P3b sweep-on-kill + sweepLockGates defer (WINDOWS/cargo)

 #8 legible-key map (parallel, only needs the Boss Key names from #4)

        all -> #10 verification (provision sandbox; gen-fuzz + region gates + boss-lock tests)
```

## 2. The one serial bottleneck (#3)

Per the parallel-clobber rule, `data.REGIONS`, `region_spine.py`, and `gen_data.REGION_MAP`
are shared-registration files — **Opus edits them serially, no parallel co-edit.** This is
the single gate everything else waits on. The edit:

- Add `Ancient Ruins of Rauh` and `Enir-Ilim` to `REGIONS`, `SPINE`, `DLC_REGIONS`.
- Rename the `Land of Shadow` catch-all -> `Gravesite Plain` (DLC root).
- Remap `REGION_MAP`: `Church of the Bud (DLC)` -> `Ancient Ruins of Rauh`;
  `Enir-Ilim (DLC)` -> `Enir-Ilim`; `Castle Ensis (DLC)` -> `Gravesite Plain` (was Belurat);
  `Gravesite Plain / Cerulean Coast / Stone Coffin Fissure (DLC)` -> `Gravesite Plain`;
  Rauh ruins tiles -> `Ancient Ruins of Rauh`.
- `GOAL_REGION` stays `Leyndell` for now (base-game re-carve owns folding it into Altus).

Because `SPINE` order defines the num_regions sphere gradient, place the six DLC regions in
spine order: Gravesite Plain, Belurat, Scadu Altus, Shadow Keep, Ancient Ruins of Rauh,
Enir-Ilim, (Jagged Peak, Abyssal Woods ride-alongs last).

## 3. What parallelizes, and to whom

Once #3 lands, three tracks run concurrently as Fable subagents, **each owning its own
file** (no shared-file co-edit):

- **Track B (#4, #6):** the generation/data track — `boss_data.py`, `boss_sweeps.py`, the
  ItemLotParam join in `gen_data.py`. Windows/artifacts. One owner.
- **Track T (#5):** tests — `tests/test_gf_region_correctness.py` (+ a Rule-B foothold
  assertion). Sandbox. Separate owner, separate file.
- **Track K (#8):** legible-key map — its own module + a contract note. Needs only the Boss
  Key name set from #4. Separate owner.

`#7` (boss_locks un-scope + per-boss flag) edits `features/boss_locks.py` and must land
after #4's data exists; it is Opus-or-single-owner because it also touches `contract.py`
(shared registration) for any new/changed key. `#9` is Windows/cargo -> Alaric.

## 4. Sandbox vs Windows (hard split)

- **Sandbox-runnable:** #5 tests, #8 legible-key map (pure Python), and #10's pytest /
  gen-fuzz over already-committed generated data. Provision via
  `bash greenfield/provision-linux-env.sh`; populate with `git archive HEAD:... | tar -x`
  (never mount cp).
- **Windows / needs artifacts:** #4 and #6 (re-run `gen_data.py` against the filter-repo'd
  EMEVD + ItemLotParam), and #9 (cargo). These are Alaric-executed; agents prepare the
  patch, Alaric runs the regen/build and reports back.

## 5. Open confirms before dispatch

1. **Belurat cut** — this plan carries it (own region, Dancing Lion capstone) per the 2a
   recommendation. Say the word to fold it back into Gravesite (one REGION_MAP line + drop it
   from SPINE/DLC_REGIONS).
2. **Golden Hippopotamus capstone** — has no remembrance flag; confirm we add a manual
   boss-defeat-flag capstone entry for Scadu Altus (vs. picking a remembrance boss there).
3. **Base-game re-carve scope** — is that track in-scope for this push, or does this push
   ship DLC-carve + primitive first and base-game folds follow?

## 6. Test gates (acceptance)

- `test_gf_region_correctness` green on all six DLC regions (boundary mis-bucketing is the
  recurring bug class; this is the tier-A gate).
- Capstone release semantics: hold Boss Key AND kill boss -> region members release; neither
  alone does.
- Rule B: fill may place a capstone key in another world (no local-only constraint); no
  within-world cycle (only the boss's own check is has(key)-gated); a start region exposes a
  non-empty sphere-0 foothold.
- Unique-key singleton + big-ticket curation gates still green after the DLC bosses enter the
  pool.

## 7. Progress log — serial foundation DONE + verified (2026-07-08)

Task #3 source edits landed and verified in-sandbox against the in-repo `region_map.csv`
(the artifacts are only needed for the *generated outputs*, not the region assignment):

- **region_spine.py** (hand-authored source): `GOAL_REGION = "Altus Plateau"` (Leyndell
  folded in); `SPINE` and `DLC_REGIONS` rebuilt to the 21-region set (13 base + 8 DLC).
- **gen_data.py** (generator source): `REGION_MAP` remapped — verified **all 271 distinct
  `region` strings in region_map.csv resolve to a valid new region, zero broken**. Added the
  missing bare `'Gravesite Plain'` mapping. Fixed 5 double-quoted stragglers the first grep
  missed (single-quote only): the per-map-id override table `m34_14`/`m35_00` `"Leyndell"` ->
  `"Altus Plateau"`, `GLOBAL_RECOVER` 65400/65470 `"Land of Shadow"` -> `"Gravesite Plain"`,
  and the special-boss entry (Rennala / Full Moon Queen) `"Raya Lucaria Academy"` ->
  `"Liurnia of the Lakes"`.
- **REGIONS auto-derives** from `spokes = sorted(buckets != HUB)`, so REGION_MAP + regen
  produces `data.py` REGIONS. The hand-edit to generated `data.py` could not be reverted (git
  index.lock unremovable — mount blocks unlink), but it matches the verified regen output, so
  it is harmless and will be overwritten on regen.
- **PLAY2AP is base-overworld only** (61xxx-65xxx); needs NO change for these folds — Raya
  Lucaria, Leyndell, and all DLC areas resolve via REGION_MAP strings, not PLAY2AP.
- **The duplicate `eldenring_gf/gen_data.py` (852 lines) has zero importers** — dead/stale;
  the live generator is `greenfield/gen_data.py` (970 lines). Delete the duplicate in cleanup.

Deferred base folds (in scope, next serial pass): Weeping->Limgrave, Consecrated Snowfield +
Miquella's Haligtree merge, Mt. Gelmir -> Volcano Manor rename. Kept separate this pass to
bound blast radius; each removes a `<Region> Lock` the client must stop expecting.

### Windows regen recipe (task #4 — needs the filter-repo'd artifacts)

1. Run the live generator `greenfield/gen_data.py`. It regenerates `data.py` (REGIONS +
   LOCATIONS), `boss_data.py`, `boss_sweeps.py`, `region_graces.py`, `region_open_flags.py`,
   `item_ids.py` from region_map.csv + the artifacts (grace TSVs, EMEVD, ItemLotParam).
2. **Golden Hippopotamus** has no remembrance flag, so the boss_arena join skips it — add a
   manual special-boss entry (like the Rennala line) keyed on its boss-defeat flag so Scadu
   Altus gets a capstone. Confirm Rellana->Gravesite, Romina->Ancient Ruins of Rauh,
   Radahn->Enir-Ilim, Dancing Lion->Belurat, Messmer->Shadow Keep in the regenerated
   `boss_data.py`.
3. **Verify the two new regions resolve their overworld graces.** Rauh / Enir-Ilim get their
   *named* checks via REGION_MAP, but overworld graces flow through
   `PLAY2AP.get(greg.get(flag))`; DLC play_region ids are absent from PLAY2AP, so confirm the
   grace_region_map path buckets Rauh/Enir-Ilim graces correctly (else add PLAY2AP entries or
   a `_DLC_OPEN_FALLBACK` for them — they may otherwise land in `REGION_OPEN_PENDING`).
4. Run `test_gf_region_correctness` (tier-A gate) — the safety net for every tile mis-bucket,
   especially Shunning-Grounds (m35 -> Altus now) and the Rauh boundary.
