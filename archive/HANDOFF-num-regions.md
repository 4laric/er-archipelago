# HANDOFF: `num_regions` — apply, build, gen-test (Windows)

Feature: random short Capital run. Full design in `SPEC-num-regions.md`.
Patch: `patch_apworld_num_regions.py` (CRLF-safe, idempotent).

## Why this needs you on Windows
The sandbox sees a **truncated** copy of `options.py` (mount read cuts off mid-dataclass at
`region_access: Regi`), so I could not apply/compile the `options.py` half there. The patch anchors
are confirmed against the real file via the editor, and the `region_spine.py` + `__init__.py` halves
were applied to sandbox copies and compile clean + pass a unit test. Apply on Windows where the file
is whole.

## 1. Apply
```powershell
cd <repo>\Archipelago\worlds\eldenring
python ..\..\..\..\patch_apworld_num_regions.py
```
Expect four `[ok]` lines and `DONE`:
```
  [ok]   region_spine.py: inserted compute_num_regions_scope
  [ok]   options.py: inserted class NumRegions
  [ok]   options.py: inserted num_regions: NumRegions
  [ok]   __init__.py: inserted SPEC-num-regions.md
DONE
```
If any line says `[FAIL] ... anchor not found`, stop — the source moved; ping me with the file and
I'll re-anchor. Re-running is safe (already-patched files report `[skip]`).

Sanity compile:
```powershell
python -c "import ast; [ast.parse(open(f,encoding='utf-8').read()) for f in ('options.py','__init__.py','region_spine.py')]; print('parse OK')"
```

## 2. yaml
Add to the ER section of your test yaml:
```yaml
  ending_condition: capital
  world_logic: region_lock        # or region_lock_bosses
  num_regions: 4                   # recommended for ~3-4 hr; 5-6 = a bit longer
  great_runes_required: 2          # the rune floor; >4 is rejected for the capital goal
  # region_access is forced to warp by num_regions (no need to set it)
```

## 3. Build + gen-test
Full clean build (kill any stale :38281 server first), then a generate:
```powershell
.\build.ps1 -Clean -All
# generate a test seed with the yaml above
```

## 4. Expected gen output
- A warning line: `num_regions forces region_access=warp ...`.
- If `num_regions` was below the floor: `num_regions N raised to M so the capital (Morgott) stays
  reachable.` (e.g. `num_regions: 2` with `great_runes_required: 2` → raised to 4.)
- Generation **succeeds** (no fill error).

## 5. Verify in the spoiler
- Kept overworld majors = **Limgrave + Leyndell/Morgott capstone + (effective−2) random middles**,
  and at least `great_runes_required` of the kept middles are great-rune regions
  (Stormveil/Godrick, Liurnia/Rennala, Caelid/Radahn, Mt. Gelmir/Rykard).
- The random middles **change with the seed** (re-roll with a different seed → different majors).
- Sealed regions' checks are **locked-vanilla events**, not AP checks; sealed region **locks are
  absent** from the item pool.
- The Morgott goal location (`LRC/QB: Remembrance of the Omen King - mainboss drop`) is reachable.
- Use a `gendiag_*.txt` / generated spoiler as ground truth (not the yaml).

## 6. Negative checks (should warn + ignore, still generate)
- `num_regions: 4` with `ending_condition: final_boss` → "needs ending_condition 'capital'".
- `num_regions: 4` with `world_logic: open_world` → "needs world_logic region_lock / region_lock_bosses".
- `num_regions: 4` **and** `region_count: 4` together → num_regions warns "overlaps another
  region-seal goal" and yields to region_count.
- `num_regions: 4` with `great_runes_required: 5` → `OptionError` (only 4 pre-Leyndell rune bosses).

## 7. Report back
Spoiler kept/sealed region lists for a couple of seeds + the gen warnings. If warp routing
softlocks in-game (a kept region's lock never becomes reachable), capture the seed — that's a
fill/warp-graph issue, not the seal logic.
