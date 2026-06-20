# HANDOFF — num_regions pool rune-source + Roundtable hub (Track A)

**Patch:** `patch_apworld_num_regions_pool_runes.py` (repo root)
**Run on:** Windows only. The sandbox must NOT edit apworld files (truncation hazard).
**Status:** authored + dry-run-proven against committed HEAD copies; NOT yet applied to the live tree.

---

## ⚠️ PRECONDITION — the mount working tree is truncated; verify Windows is intact first

When I read the mount, several apworld files were **truncated** (smaller/broken than `git HEAD`):

| file | HEAD bytes | mount working-tree bytes | state |
|---|---|---|---|
| `region_spine.py` | 24680 | 20552 | **truncated mid-comment at line ~391**; `compute_num_regions_scope` / `NUM_REGIONS_MIDDLE_STEPS` / `num_regions_floor` are GONE |
| `options.py` | 51416 | 51438 | truncated tail at line ~1020 (`OptionGroup("`), unterminated string — won't import |
| `__init__.py` | 310809 | 306324 | smaller than HEAD |

These are almost certainly a stale/corrupt mount reflection, not your real Windows tree — but **confirm on Windows** before running. The num_regions feature must be intact:

```
cd Archipelago\worlds\eldenring
python -c "import ast; ast.parse(open('region_spine.py',encoding='utf-8').read()); print('parses')"
findstr /C:"def compute_num_regions_scope" region_spine.py
findstr /C:"class NumRegions" options.py
```

If any are missing/broken, restore + re-stack the num_regions patches first:
```
git restore worlds/eldenring/region_spine.py worlds/eldenring/options.py worlds/eldenring/__init__.py
# then re-apply patch_apworld_num_regions.py (+ any later num_regions patches you keep) before this one
```
The patch is defensive: it prints `[FAIL]` and writes nothing for any file whose anchor is missing or ambiguous, so a half-restored tree can't be silently corrupted.

---

## What it changes

Adds **`num_regions_rune_source`** (Choice: `regions`=0 default, `pool`=1). Only meaningful when `num_regions > 0`.

- **regions (default):** untouched — today's behaviour exactly (great-rune floor + Altus force in region selection, Limgrave forced hub).
- **pool:** decouples the great-rune floor from region selection.
  1. **region_spine.py** — new sibling `compute_num_regions_scope_pool()` + `NUM_REGIONS_POOL_STEPS` (= `[1]+NUM_REGIONS_MIDDLE_STEPS`, i.e. all 8 majors rollable, **including Limgrave**) + `NUM_REGIONS_STEP_GREAT_RUNE` map. No rune floor, no Altus force; content floor = always-kept set only (Roundtable hub + Leyndell), so **a 1-middle-region run is legal**. Limgrave is NOT force-prepended.
  2. **__init__.py (num_regions block)** — in pool mode, re-runs the scope with the pool function, overwrites the `_spine_*` seal fields, sets `self._num_regions_pool_reroot = True`, and **injects the deficit great runes** into the pool: `deficit = great_runes_required − (rune bosses still in a kept region)`; candidates = the 4 base-spine runes (`Godrick's`, `Great Rune of the Unborn`, `Radahn's`, `Rykard's`) whose step is **sealed**, **excluding `Morgott's Great Rune`** (goal-side Leyndell drop). Each chosen rune gets `item_table[name].inject = True` — the existing create_items demand-drop frees one filler slot per injectable, so the pool is **count-neutral** (no manual filler bookkeeping).
  3. **__init__.py (after the `_random_start_region = None` reset)** — when `_num_regions_pool_reroot`, sets `self._random_start_region = "Roundtable Hold"` and `Limgrave Lock.inject = True`, arming the **already-built Roundtable-hub re-root** (`_region_lock_warp_access`, `create_regions` New-Game root, start-grace block all key on truthy `_random_start_region`). Limgrave becomes a normal locked region reached by `Warp To Limgrave`.

Leyndell's gate is a pure item count (`_has_enough_great_runes`, no region/tower dependency), so injecting the runes as items satisfies it with **no rule changes**.

---

## Exact anchors used (all verified unique against committed HEAD)

1. `options.py` — after the NumRegions class body:
   ```
       display_name = "Num Regions (random Capital run)"
       range_start = 0
       range_end = 9
       default = 0
   ```
   inserts `class NumRegionsRuneSource(Choice)`. Marker: `class NumRegionsRuneSource`.
2. `options.py` — after `    num_regions: NumRegions\n` (dataclass field). Inserts `num_regions_rune_source: NumRegionsRuneSource`. Marker: `num_regions_rune_source: NumRegionsRuneSource`.
3. `region_spine.py` — after the unique tail of `compute_num_regions_scope` (the `kept_steps = [SPINE[0]] + [SPINE[s - 1] for s in picked] … return …, effective` block). Inserts `compute_num_regions_scope_pool` + maps. Marker: `compute_num_regions_scope_pool`.
4. `__init__.py` — after the num_regions `_eff raised` warning:
   ```
                   if _eff != self.options.num_regions.value:
                       warning(f"{self.player_name}: num_regions {self.options.num_regions.value} "
                               f"raised to {_eff} so the capital (Morgott) stays reachable.")
   ```
   inserts the pool-mode re-scope + deficit-rune injection. Marker: `SPEC-num-regions-pool-runes.md`.
5. `__init__.py` — after the `_random_start_region = None` reset's Limgrave-Lock line:
   ```
           if "Limgrave Lock" in item_table:
               item_table["Limgrave Lock"].inject = False
   ```
   inserts the pool-mode Roundtable re-root. Marker: `num_regions pool-mode Roundtable re-root`.

Every insertion is idempotent (marker check) and CRLF-safe (per-file newline detected, inserted text normalised). The splice helper also **aborts if the anchor matches >1 place** (ambiguity guard added vs the original num_regions patch).

---

## How to run (Windows)

```
cd Archipelago\worlds\eldenring
python ..\..\..\..\patch_apworld_num_regions_pool_runes.py
```
Expect five `[ok]` lines + `DONE`. Re-running prints five `[skip]` lines.

Then build the apworld and gen-test (your usual recipe).

## Gen-test

YAML knobs:
```
ending_condition: capital          # option value 4 — REQUIRED
world_logic: region_lock           # (or region_lock_bosses) — REQUIRED
num_regions: 1                      # any 1..9
num_regions_rune_source: pool
great_runes_required: <whatever, e.g. 2>
```

**Expect:**
- Seed generates (no fill failure).
- Hub is **Roundtable Hold**; First Step (76101) NOT lit, Roundtable (71190) lit at load.
- Exactly **one rolled middle major** kept (could be a sealed Limgrave — reached via `Warp To Limgrave` if Limgrave is rolled, otherwise Limgrave is sealed and that's fine).
- The deficit **great runes appear as pool items** (placeable anywhere), reachable before Leyndell; pool size unchanged (each injected rune ↔ one freed filler).
- `gendiag_*.txt` should show the kept region set + the injected runes (the patch emits a `num_regions rune-source=pool …` warning naming them).
- Sweep up `num_regions` (4, 8) and `great_runes_required` (1–4) to confirm the floor/cap and that `total runes (kept + injected) >= great_runes_required` always holds.

I verified the rune-deficit math standalone for every (num_regions 1–4 × great_runes_required 1–4): **total runes ≥ requirement in all 16 cases, Morgott never injected, no double-inject.**

---

## Risks / edge cases

1. **`great_runes_final_boss` / `great_runes_mountaintops`** also call `_has_enough_great_runes`. Under the Capital goal those gates (Erdtree / Mountaintops) are past the sealed wall and not goal-required, but if a future combo makes them logic-relevant, the injected runes count toward them too (generally harmless — more runes available, not fewer). Worth a glance if you ever stack pool mode with a non-Capital sub-goal.
2. **DLC runes (`Mohg's` / `Malenia's`) are intentionally NOT injection candidates** — their bosses aren't base-spine steps, so they're never the deficit source. `great_runes_required` is capped at 4 base runes anyway (`MAX_PRE_LEYNDELL_RUNES`).
3. **Dragonbarrow-without-Caelid** warp reachability caveat from the chain feature does NOT apply here (no chain), but Dragonbarrow still has no own hub warp — in pool mode a kept Dragonbarrow relies on the bundle/grace path the base warp-access code already handles. If a kept-Dragonbarrow-without-Caelid seed gen-tests as unreachable, that's the same known gap, not new.
4. **`_random_start_region = "Roundtable Hold"`** is a slight overload of that field (it's normally a real start region name). Every consumer treats it as a truthy re-root flag; the only value-lookup (`REGION_GRACE_POINTS.get(self._random_start_region, [])` in the start-grace block) safely returns `[]`. Verified all 7 read-sites. If you'd rather not overload it, a dedicated `_num_regions_pool_reroot`-keyed branch in `_region_lock_warp_access`/`create_regions` is the alternative — but that's 3 more splices for no behavioural gain.
5. **pool + num_regions_chain together:** the chain block runs AFTER the pool re-scope and consumes `_kept_l` (now the pool-scope kept locks), so it chains the pool-kept middles. Untested combo — gen-test before relying on it. If undesired, gate the chain off when `num_regions_rune_source == pool`.

---

## Dry-run evidence

Applied cleanly to committed-HEAD copies (5× `[ok]`, `DONE`); all three patched files `py_compile` OK; re-run idempotent (5× `[skip]`); `compute_num_regions_scope_pool` exercised standalone (floor=1 honoured, cap=8, Limgrave rollable); deficit-injection math verified for all 16 (num_regions × great_runes_required) combos. The live mount was left untouched (region_spine.py/options.py/__init__.py NOT modified by me).
