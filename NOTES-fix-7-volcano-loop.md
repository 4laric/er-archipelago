# Fix #7 — volcano_town requirement loop crash

**File changed:** `SoulsRandomizers/RandomizerCommon/KeyItemsPermutation.cs`, in `CollapseReqs()`
(the `findLoops` driver, ~line 794–819).

## Root cause
`volcano_town.Req = volcano_drawingroom OR (nodeathless AND academy AND altus)`
(annotations.txt:1072; `altus` added on purpose per the line-1071 comment; `nodeathless` is the
default of the deathless `Oneof`, annotations.txt:732). During the iterative key-item placement in
`CollapseReqs`, once a key item that `altus` needs (e.g. a Dectus medallion) is tentatively placed
behind `volcano_town`, a cycle forms: `volcano_town -> altus -> … -> volcano_town`.

`findLoops` is *not* an exhaustive DFS — it returns early right after cutting one edge and removes
cut edges mid-pass. A single pass can therefore leave a cycle uncut when it shares nodes with a
cycle already cut (the shared nodes get marked processed and are never revisited). With DLC nodes
present the residual graph gave the heuristic a good edge to cut; with DLC pruned (base-game) the
tighter residual cycle was missed, and the uncut cycle then surfaced downstream as
`Loop detection failed on volcano_town - internal error` in `simplifyReqs`. Hence seed- and
DLC-pruning-dependent.

## Fix (chosen angle: harden findLoops — self-contained, no apworld/annotation coupling)
Wrapped the `findLoops` scan in a do/while that resets `allDepsProcessed` and re-scans until a full
pass adds no new cut edge. A real remaining cycle is reachable only through not-yet-cut edges, so
cutting its first optional edge always grows the cut count → the loop keeps going; when the residual
graph is acyclic no new cut is added → it stops. `simplifyReqs` can then never reach an uncut cycle.
Genuinely unsolvable cycles (no optional edge) still throw the existing "Unsolvable seed" exception,
unchanged.

## Verification (Linux sandbox — faithful Python port of Expr + findLoops + simplifyReqs)
- 400,000 random small graphs: original single-pass threw "Loop detection failed" on **35,772**;
  the fixpoint version fixed **35,772 / 35,772** (0 still broken).
- No-regression: on every graph the original handled cleanly, the fixpoint version produced an
  **identical cut set** (8,820 / 8,820). So seeds that already bake are byte-for-byte unaffected.

## Players dir — prepped for the bake test (2026-06-13)
- `Archipelago\Players\EldenRing.yaml` = **DLC-OFF** test config (the validated sync config with
  only `enable_dlc: false`; slot `Alaric`). This is the base-game path that exercised #7.
- `EldenRing-DLCon-regression.yaml` (repo root, NOT in Players\) = verbatim DLC-ON sync config,
  staged to swap into `Players\` for the regression bake after the DLC-off test passes.
- `Players\` has no stray files (AP Generate reads *every* file there).

## Bake-test on Windows (Alaric — can't bake on Linux)
Build the randomizer once with the fix: `.\build.ps1 -Randomizer`

**DLC-off (the #7 fix) — automated multi-seed loop (preferred):**
1. Build once with both fixes: `.\build.ps1 -Randomizer`
2. Rip through several seeds unattended:
   - `.\build.ps1 -LoopTest -Seeds 1,2,3,4,5,61698419`  (deterministic/reproducible), or
   - `.\build.ps1 -LoopTest -Count 8`  (8 fresh random seeds), add `-Enemies` to mirror the yaml.
   Per seed it generates (`Generate.py --seed`), starts a FRESH server for that exact zip (so the
   bake can't hit a stale server), then does a HEADLESS bake (no dialogs, auto-close). It prints a
   pass/fail table; success = apconfig.json's seed matches the generated seed. ALL should be `OK`.
   Any `BAKE-FAIL` → check the `ap_error` diag; a `Loop detection failed` there means #7 isn't
   fully fixed for that seed.
3. `.\build.ps1 -Preflight` → PASS (slot=Alaric, baked seed == newest gen).

Manual single-seed alternative: `.\build.ps1 -Generate -Serve -Bake` (the GUI bake needs a manual
window close; `-LoopTest` headless avoids that).

**DLC-on regression:**
4. Swap configs: move `Players\EldenRing.yaml` aside, copy `EldenRing-DLCon-regression.yaml` →
   `Players\EldenRing.yaml`.
5. `.\build.ps1 -Generate -Bake` → still bakes clean (no regression from the findLoops change).
6. `ap_diag` clean.

If region gating (#13) deadlocks the apworld gen-test on volcano_town, it's this same cycle — link.

---

# Follow-on fix — `_read_slot_data_N` TimeoutException at bake (surfaced 2026-06-14)

With #7 fixed, the bake got *past* the volcano loop and then threw
`System.TimeoutException: Timed out retrieving data for key "_read_slot_data_3"` from
`ArchipelagoForm.RandomizeForArchipelago`. Cause: the bake connected with `requestSlotData: false`
and then read slot data via the **synchronous** `session.DataStorage.GetSlotData()`, which blocks on
a packet response — the AP MultiClient library explicitly warns this deadlocks/times out. It was a
latent fragility (same pattern in the committed code at two sites), exposed here by timing/latency.

**Fix (canonical AP pattern):** request slot data at login (`requestSlotData: true`) and read it
from the Connected packet via `((LoginSuccessful)result).SlotData` — no live DataStorage read at all.
Threaded that `slotData` into `RandomizeForArchipelago(session, slotData)` and
`ArchipelagoLocations(ann, locations, slotData)`; removed both `GetSlotData()` calls. Same
`Dictionary<string, object>` type and `JObject`-valued contents, so all downstream casts are
unchanged. File: `SoulsRandomizers/RandomizerCommon/ArchipelagoForm.cs`.

Needs a Windows rebuild (`.\build.ps1 -Randomizer`) + re-bake to confirm — can't compile WinForms here.

**Stale-server root cause (fixed):** the earlier failure's key was `_read_slot_data_3` (slot 3), but
a single-player DLC-off Generate makes Alaric slot **1** — the bake had autoconnected to a **stale
server** (the URL left in `apconfig.json` from the central-sync test). Cause: `OnShown` autoconnect
only set localhost when `url.Text` was *empty*, so the stale apconfig URL survived. Fixed in
`ArchipelagoForm.OnShown` — under autoconnect the URL now ALWAYS resets to `localhost:38281`
(overridable with a `url=` launch arg). `-LoopTest` also restarts a fresh local server per seed, so
both the URL and the served seed are guaranteed local/current. Still let `-Preflight` confirm baked
seed == newest gen.
