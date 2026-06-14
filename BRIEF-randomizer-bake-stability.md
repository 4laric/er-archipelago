# BRIEF: randomizer bake stability — volcano_town loop (#7) + Raya Lucaria crash (#10)

Repo: **static randomizer** `SoulsRandomizers` (C#). Contract-FREE. SAME repo as
`BRIEF-randomizer-bake-polish.md` → run in a SEPARATE git worktree or sequence them; never two
concurrent sessions on one working tree. See BRIEF-PARALLEL-INDEX.md. TODO #7 and #10.

> LICENSING: fork is PRIVATE; reimplement in our own C#. Build/bake on Windows (`build.ps1
> -Randomizer -Bake`). Both tasks need a Windows repro / in-game log — the Linux sandbox can read
> source and reason, but the actual repro is Alaric's.

---

## Task A — volcano_town requirement loop crashes some bakes (#7)

One sentence: certain seeds throw `System.Exception: Loop detection failed on volcano_town` in
`KeyItemsPermutation.CollapseReqs`; find and break the cycle so base-game (DLC-off) bakes stop
randomly failing.

**Anchors:** `KeyItemsPermutation.cs` — `CollapseReqs()` at ~756, the recursive `simplifyReqs`
lambda ~799–828, throw at ~806 (`Loop detection failed on {name}`). Called from ~446 and ~498.
The cycle: `volcano_town` Req = `volcano_drawingroom OR (nodeathless AND academy AND altus)`
(annotations data ~line 1072 in the annotations file); the abduction branch pulls in `altus`, which
chains back to `volcano_town`. `findLoops` breaks this when DLC nodes are present but NOT in the
pruned base-game graph — so it's **seed- and DLC-pruning-dependent**, not strictly DLC-off (base seed
61698419 baked fine; a later base seed crashed). DLC-on has been robust/lucky.

**Steps:**
1. **Repro in isolation:** DLC-off + a crashing seed; confirm it's the DLC-pruning interaction and
   NOT one of the apworld changes (map-exclusion / reclassification altering the scrape/scopes).
   Find a deterministic crashing seed to iterate on.
2. **Fix angle (pick one):**
   - Preferred: make the `nodeathless` abduction branch drop out. Wiring the apworld
     `deathless_routing` to ALSO set the bake's deathless (so `nodeathless` is false) removes that
     branch and breaks the cycle — but `nodeathless`'s source isn't in KeyItemsPermutation /
     AnnotationData; FIND where it's set first. (This angle touches the apworld too — coordinate, but
     it's logic not wire-contract.)
   - Local-only fallback (licensing-aware, our edit): drop the `altus` term from volcano_town's
     abduction branch in the annotation so the cycle can't form.
   - Or: harden `findLoops` so it collapses this cycle in the pruned base graph the same way it does
     with DLC nodes present.
3. Until fixed, DLC-ON sync is the validated path (HANDOFF). Goal of this task = unblock DLC-off.

**Test:** bake the previously-crashing base-game seed → completes; bake several more base seeds →
no loop throw. DLC-on bakes still fine (no regression). ap_diag clean.

**Coordination note:** region gating (#13) changes the logic graph and may surface this same loop in
the apworld gen-test (`BRIEF-apworld-content.md`). If that test deadlocks on volcano_town, it's THIS
bug — link findings.

---

## Task B — Raya Lucaria entry crash → won't reload → softlock (#10)

One sentence: the game crashes after entering Raya Lucaria and won't load on retry (effective
softlock); diagnose, reproduce, and isolate the cause.

**This is diagnosis-first — do not guess a fix.** Likely an enemy-rando placement/scaling issue in
RLA (Raya Lucaria Academy), or a map/asset problem. Needed inputs (ask Alaric to capture in-game):
- `%LOCALAPPDATA%\archipelago_client.log` around the crash, and the console er::Init BUILD stamp.
- Whether it persists with **enemy_rando OFF** (the single biggest isolator).
- Whether it's DLC-on vs DLC-off, and whether it's RLA-specific or any legacy-dungeon entry.

**Steps:**
1. From the log + repro, isolate the variable: enemy rando? DLC? a specific RLA entity/scaling?
   (If enemy_rando-off fixes it, focus on `EnemyRandomizer.cs` RLA placements/scaling — note the
   known v0.8 scaling IndexOutOfRange at `EnemyRandomizer.cs:8202` is a DIFFERENT, swap-toggle bug;
   don't conflate.)
2. Reproduce deterministically (seed + entry path).
3. Propose the minimal fix once the cause is pinned; if it's a placement/scaling guard, mirror the
   existing guard patterns. If it's an asset/map issue, it may not be a randomizer fix at all —
   report that clearly rather than forcing a code change.

**Test:** re-enter RLA on the repro seed → no crash, reloads cleanly. Confirm with enemy_rando on
(the intended config).

**Contract:** none.
