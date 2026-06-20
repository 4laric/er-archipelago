# HANDOFF: Random overworld start under num_regions Capital chain

Status: SCOPED + BLOCKED on a working-tree repair. 2026-06-19.
Supersedes the over-scoped plan in SPEC-random-start-roundtable-hub.md (see "Correction" below).

## ⛔ BLOCKER 0 — `__init__.py` is truncated; restore before anything

`Archipelago/worlds/eldenring/__init__.py` in the WORKING TREE is cut off mid-statement inside
`fill_slot_data` (it ends at `# received AND ALL flags`). It will not import.

- working tree = 4687 lines; HEAD (`02864706` "spine seal bell relief") = 4934 lines.
- `git diff --stat` = **25 insertions, 271 deletions** — the slot_data tail (start emission,
  `versions`, `return slot_data`) is gone. Same truncation failure as 2026-06-19; see
  [[er-mount-write-truncation]] / [[mount-error-hand-off-patch]].

**Do this first, on Windows (do NOT let the sandbox "fix" it — that is what truncated it):**

```
cd <repo>\Archipelago
git restore worlds/eldenring/__init__.py
git status   # expect clean
python -c "import ast,io; ast.parse(io.open('worlds/eldenring/__init__.py',encoding='utf-8').read())"  # must be silent
```

Everything below assumes a clean HEAD tree. Line numbers are HEAD line numbers.

## Correction to SPEC-random-start-roundtable-hub.md

That SPEC assumed Bucket A (Roundtable re-root) and Bucket B (spine surgery) were unbuilt. They
are essentially DONE in HEAD:

- `Limgrave Lock` item exists (items.py:2153); `_random_start_region` truthy re-roots New Game →
  Roundtable (HEAD:863), the warp hub → Roundtable (HEAD:2437), adds a lock-gated `Warp To Limgrave`,
  emits Limgrave `areaLockFlags` + `lockOpenFlags["Limgrave Lock"]`, and the baker retargets the KICK
  off `regionOpenFlags`. No new work.
- num_regions + `num_regions_chain` + `num_regions_rune_source=pool` already make Limgrave a normal
  rollable/sealable region (Roundtable is the hub) and build a linear chain whose **link 0 is a
  randomly-rolled overworld region** (steps 2–8; Altus forced to the tail). `pre_fill` already
  **precollects link-0's lock** (HEAD:2099-2101) → that region is logically sphere-1 free.

So the original Bucket B (teach the spine to demote Limgrave) is **not needed** — the chain already
rolls the start region. The only reason the player physically begins at Roundtable is that the
pool-reroot hardcodes the spawn and the physical-warp keys were never committed.

## What's actually missing (three small changes)

### Patch A — emit the physical-spawn keys (REQUIRED; missing even from HEAD)
HEAD has NO `startRegion` / `startWarpGrace` / `_rsr_warp_grace`. The baker's `ApplyRandomStartEntry`
reads `slotData["startRegion"]` + `slotData["startWarpGrace"]` (patch_baker_random_start_warp*.py),
so without these the forced spawn is dead — even for the shipped non-spine Caelid case.

`patch_apworld_random_start.py` already contains the exact code (its `SG_BLOCK` computes
`_rsr_warp_grace` = centroid grace of `_random_start_region`; its `SD_BLOCK` emits the two keys),
BUT that script self-skips when `self._random_start_region = None` is already present (it is, in HEAD)
→ re-running it will NOT add the emission. **Write a fresh standalone patch** lifting just SG_BLOCK +
SD_BLOCK:
- SG_BLOCK anchor: insert before `        start_items: List[int] = []`
- SD_BLOCK anchor: insert after `            "startGraces": start_graces,\n` (HEAD:4900)
Keep the `_RS_SKIP` boss/border grace exclusion set verbatim.

### Patch B — latch flags (EXISTS, run after A)
`patch_apworld_random_start_warpflags.py` adds `randomStartWarpFlag/AreaId/DoneFlag`. Its anchor is
`            "startWarpGrace": getattr(self, "_rsr_warp_grace", 0),\r\n` — created by Patch A, so A→B.

### Patch C — point the chain spawn at link 0 instead of fixed Roundtable (THE feature)
At HEAD:782-783:
```python
if getattr(self, "_num_regions_pool_reroot", False):
    self._random_start_region = "Roundtable Hold"
    ...
```
When `self._num_regions_chain` is on and `self._num_regions_chain_order` is non-empty, set
`_random_start_region` to **link-0's region name** instead of `"Roundtable Hold"`:
1. `step0 = self._num_regions_chain_order[0]`
2. `lock0 = region_spine.NUM_REGIONS_CHAIN_STEP_LOCK[step0]`
3. `region0 = next((r for r, l in REGION_LOCK_ITEM.items() if l == lock0 and r in REGION_GRACE_POINTS), None)`
   (invert REGION_LOCK_ITEM; require a grace-mapped region so the spawn/grace bundle resolves —
   note `Caelid Lock` maps to BOTH `Caelid` and `Sellia Crystal Tunnel`, so the `in REGION_GRACE_POINTS`
   filter picks the real overworld region.)
4. If `region0` found → `self._random_start_region = region0`; else keep `"Roundtable Hold"` (safe
   fallback, never breaks gen).

Roundtable stays the hub/logic-root/KICK-fallback regardless (the re-root keys on `_random_start_region`
being *truthy*, not on its value). Link-0's lock is already precollected, so the region is reachable
sphere-1 by warp; Patch A then lights its graces and emits `startRegion`/`startWarpGrace`; the baker
warps the player in. **CONFIRM at implementation time:** the exact `REGION_GRACE_POINTS` keys for the
candidate link-0 regions (Caelid / Liurnia of The Lakes / Weeping Peninsula / Stormveil* / Mt. Gelmir)
— grace_data.py uses an unusual `REGION_GRACE_POINTS = REGION_GRACE_POINTS = ...` assignment; verify
the key strings match REGION_LOCK_ITEM's region names (Stormveil may key as "Stormveil Start", not
"Stormveil Castle"). The `in REGION_GRACE_POINTS` guard makes a mismatch fail safe (→ Roundtable), not
crash, but you want the match so the feature actually fires.

### Baker — already wired, just verify
`ApplyRandomStartEntry` (SoulsRandomizers, patch_baker_random_start_warp_regionpoint.py is the latest
robust spawn-point fix) reads startRegion/startWarpGrace and the KICK retarget reads regionOpenFlags.
Confirm these are present in the built SoulsRandomizers; no new baker code.

## Run order (Windows)
1. `git restore` __init__.py (Blocker 0); confirm it imports.
2. Apply Patch A (new), then `patch_apworld_random_start_warpflags.py` (B), then Patch C (new).
   Verify each via Read on disk (CRLF-safe, binary I/O, idempotent, assert anchors).
3. `.\build.ps1 -Randomizer -Generate` with a num_regions + num_regions_chain + rune_source=pool +
   random/overworld start yaml.

## Gen-test matrix
- num_regions ∈ {2,4,6}, chain ON, rune_source=pool: assert solvable; spoiler `Menu → New Game`
  root = Roundtable Hold; `startRegion` in slot_data = the chain link-0 region (NOT Limgrave/Roundtable);
  link-0 lock precollected; Limgrave Lock in pool; no orphaned Limgrave checks.
- chain ON but link-0 resolves unmapped → must fall back to Roundtable spawn, still solvable.
- Normal region_lock seed (no num_regions): unchanged — startRegion="" , spawn = Limgrave/First Step.
- dlc_only: unaffected (Gravesite is the fixed hub).
## Playtest
Start a pool+chain seed → confirm physical spawn in the rolled region (e.g. Caelid), Roundtable
reachable by fast-travel, kick from a still-locked region lands in Roundtable (no loop), receive
Limgrave Lock → Limgrave opens.

---

## STATUS 2026-06-20 — patches WRITTEN + dry-run verified against HEAD

The three changes are now concrete patch scripts in the repo root, anchored to HEAD (`02864706`),
idempotent, binary/CRLF-safe, anchor-asserting (no write on mismatch):

1. `patch_apworld_start_emission.py`  (NEW) — start-grace bundle + `_rsr_warp_grace` + slot_data
   `startRegion`/`startWarpGrace`. Drops First Step 76101 (Limgrave is locked under the re-root).
2. `patch_apworld_random_start_warpflags.py`  (EXISTS) — latch flags; anchors on #1's `"startWarpGrace"` line.
3. `patch_apworld_numregions_chain_rolled_start.py`  (NEW) — retargets HEAD:783 so chain spawns in the
   link-0 region (resolved via `region_spine.SPINE[step-1]["name"]`, grace-mapped, else Roundtable).

Verified in a throwaway sandbox over a CRLF copy of HEAD: all three apply in order, the result
`ast.parse`s (4934 -> 4983 lines), each key appears exactly once, and re-running is a clean no-op.
NOTE: the sandbox MOUNT is stale/truncated, so these MUST be run on the Windows tree after the
`git restore`. The anchor asserts will FAIL-SAFE (no write) if the restore didn't fully land.

### Run order (Windows, repo root)
```
git restore Archipelago/worlds/eldenring/__init__.py   # if not already
python patch_apworld_start_emission.py
python patch_apworld_random_start_warpflags.py
python patch_apworld_numregions_chain_rolled_start.py
python -c "import ast,io; ast.parse(io.open('Archipelago/worlds/eldenring/__init__.py',encoding='utf-8').read()); print('OK')"
.\build.ps1 -Randomizer -Generate   # yaml: num_regions>0 + num_regions_chain + num_regions_rune_source=pool + random/overworld start
```
Then the gen-test matrix above. Confirm spoiler `startRegion` = the link-0 region (Caelid/Liurnia/etc),
New Game root = Roundtable Hold, link-0 lock precollected, Limgrave Lock in pool.

---

## FIX 2026-06-20 — chain breadcrumb host collided with derandomize_gurranq

First gen (231831) failed in pre_fill: `place_locked_item ... "DB/(BS): Ancient Dragon Smithing
Stone - Gurranq ..." already filled`. The num_regions_chain breadcrumb host-picker reused a Gurranq
deathroot location that `derandomize_gurranq: true` had already locked. Independent of the random-start
work (host selection keys on chain ORDER, not the link-0 region). Fixed by
`patch_apworld_chain_host_skip_filled.py`: `_num_regions_chain_host` now excludes already-filled
candidates, and the placement treats a filled host as no-host (-> precollect fallback).

APPLY ORDER NOW (apworld-only; no client rebuild needed for this fix):
```
python patch_apworld_start_emission.py
python patch_apworld_random_start_warpflags.py
python patch_apworld_numregions_chain_rolled_start.py
python patch_apworld_chain_host_skip_filled.py
.\build.ps1 -Randomizer -Generate
```
