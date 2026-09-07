# SPEC -- Move the foreign placement passes from `stage_pre_fill` to `stage_fill_hook`

Status: **DRAFT.** 2026-09-07. Author: Fable (draft), Alaric (commission). Parent:
[SPEC-core-fill-hooks-upstream-20260907](SPEC-core-fill-hooks-upstream-20260907.md) section 4,
issue #1459. Does not wait for anything upstream.

---

## 0. Why

Our `GreenfieldEldenRingWorld.stage_pre_fill` (`core.py:1714`) places items onto other worlds'
locations. AP runs stage pre-fills in class-name order and reserves `pre_fill` for a world's own
locations, so we have been paying for that with workarounds: `players_still_prefilling` (#1457),
the declared-early skips in `incoming_progression` (#1456) and `keep_out_of_shops` (seed 1044,
2026-09-06), and a sort-order dependence nobody documents.

Core already has the hook we want. `stage_fill_hook` is called from
`distribute_items_restrictive` (`Fill.py:517`) **after** every world's `pre_fill` and
`stage_pre_fill`, **after** `distribute_early_items`, and **before** the priority and
progression fills. Four shipped worlds use it; core tests the contract
(`test/general/test_fill.py:628`). At that moment:

- every partner has placed its own confined items, so we cannot take a slot it still needs;
- every declared early item is already on a sphere-1 location, so we cannot steal one;
- nothing else has placed anything yet, so the open grid is exactly what our passes assume.

## 1. What the hook hands us, and the one contract difference

```python
@classmethod
def stage_fill_hook(cls, multiworld, progitempool, usefulitempool, filleritempool, fill_locations)
```

- The three pools are the unplaced items, already split by classification, in core's shuffled
  order. They hold the **same Item objects** that were in `multiworld.itempool`
  (`Fill.py:500`, `sorted` then `shuffle`, no copies).
- `fill_locations` is the shuffled open-location list, minus what early items took.
- **`multiworld.itempool` is dead from here on.** Nothing in `distribute_items_restrictive`,
  `Main.py` after line 196, or `post_fill` reads it in the `balanced` algorithm. But
  `multiworld.get_all_state(False)` still *collects* it (`BaseClasses.py:434`), and every one of
  our passes builds its reachability state that way. A pass that runs with an empty
  `multiworld.itempool` would see a world with no items and refuse every placement.
- After the hook returns, core reads only the three pools and `fill_locations`. Anything we
  placed must be gone from those lists or it is placed twice / handed to fill as an empty slot.

Every pass we have does two things with the pool: pops its batch from `multiworld.itempool`, and
returns leftovers to it. And every pass reads open locations via `get_unfilled_locations()`,
which is driven by `location.item` and stays correct throughout.

## 2. Design: one shim, seven passes untouched

Do **not** rewrite seven passes to speak the three-pool dialect. Wrap them:

```python
@classmethod
def stage_fill_hook(cls, multiworld, progitempool, usefulitempool, filleritempool, fill_locations):
    from .features import fill_hook_shim as _shim
    with _shim.pool_view(multiworld, progitempool, usefulitempool, filleritempool, fill_locations):
        _worlds = list(multiworld.get_game_worlds(GAME))
        ... the seven calls, in today's order, unchanged ...
```

`features/fill_hook_shim.py`, ~40 lines, one context manager:

- **enter**: `multiworld.itempool[:] = progitempool + usefulitempool + filleritempool`. The
  passes now see exactly the unplaced pool they always saw, `get_all_state` builds a correct
  state, and pops/extends work as before.
- **exit** (in `finally`): rebuild the three pools **by filtering the originals**, so core's
  order is preserved and no item can change class:
  `progitempool[:] = [i for i in progitempool if i.location is None]`, same for the other two;
  then `fill_locations[:] = [l for l in fill_locations if l.item is None]`; then
  `multiworld.itempool[:] = []` so the dead list stays dead and a later reader fails loudly.
- **assert** on exit, `__debug__` only: every item still in the three pools is in
  `multiworld.itempool` as we left it and vice versa (catches a pass that created a new item
  instead of returning one, which none does today; `progression_surface.apply:1785` creates
  filler but it runs in `pre_fill`, not here).

Why a shim over the honest rewrite: the seven passes are ~600 lines with measured behaviour and
tests keyed on `multiworld.itempool`. The shim is the whole contract difference in one place.
If a pass is ever rewritten it can take the pools directly and stop needing the shim; until
then there is one adapter, not seven.

## 3. Per-file changes

| File | Change |
|---|---|
| `core.py` | `stage_pre_fill` body becomes `stage_fill_hook` under the shim, same seven calls, same order. Docstring rewritten: why `fill_hook` (section 0), the shim contract, the `flood` caveat. `pre_fill` logs one WARNING if `multiworld.algorithm != "balanced"` naming every pass that will not run. |
| `features/fill_hook_shim.py` | new, section 2 |
| `progression_surface.py` | delete `players_still_prefilling`; `_foreign_open_locations` drops the `prefilling` filter and its docstring bullet. Rewrite the "Why `stage_pre_fill` and not `pre_fill`" block in `place_released_locks` to two lines citing the parent spec. The `TUNIC raises` warning stays; it is still true of any world that objects on principle. |
| `incoming_progression.py` | delete `_declared_early`; `_eligible_by_game` no longer skips copies. Module docstring: early copies are already placed when this runs. |
| `export_reservation.py` | drop the `players_still_prefilling` import, the `prefilling` loop and its log line. Docstring "ORDERING in stage_pre_fill" becomes "ORDERING in stage_fill_hook". |
| `keep_out_of_shops.py` | `reserve_forbidden_items`: delete the `early_left` guard (the declared copies are placed before we run). `finalize_rules` is unchanged: it reads `multiworld.itempool`, which the shim keeps truthful, and the remaining grid, which is truer here than before. Docstrings at `:104`, `:311`, `:518`: `stage_pre_fill` -> `stage_fill_hook`. |
| `preferred_placement.py` | no code change; it reads and writes `multiworld.itempool` and the shim covers it. |

What stays in `pre_fill`, deliberately: `missable.reserve_filler` and `progression_surface.apply`
(own items onto own locations, which is what `pre_fill` is for) and the `_declared_early`-shaped
guard in `missable` if it has one. `test_gf_missable:131` keeps its meaning.

## 4. Behaviour that changes, and that does not

**Changes, all intended.**

- A partner's confined items are already placed. The #1457 seeds get their full share offered
  again instead of falling back to the ER surfaces; the "still holds N pre-fill item(s)" log
  line disappears.
- Early items are already placed. The reservation passes see fewer partner advancement copies
  and fewer of our own forbidden-category copies; the #1456 and seed-1044 guards are deleted
  rather than made redundant.
- `fill_restrictive` inside the hook starts from a state that includes early placements. That
  is strictly more reachable than before, so no placement that was legal becomes illegal.
- The share arithmetic in `export_reservation.reservation_size` and
  `preferred_placement.foreign_unit_target` divides by open-location counts. Those counts are
  now taken after early items, so the derived N moves by a few items on a seed with many early
  declarations. That is the truer number; note it in the changelog, do not compensate.

**Does not change.**

- Pass order, quotas, refusal handling, `lock=True`, the accessibility override in
  `place_released_locks`, and every log line except the two deleted ones.
- Any `stage_pre_fill` of another world: we no longer have one.
- The `flood` algorithm never ran our stage hook well either (it ran, then flood ignored the
  locked placements' curation intent); now it does not run it at all. `flood` is not a shipped
  option in our yaml template. The `pre_fill` warning covers it.

## 5. Tests

**Unit, `greenfield/eldenring/tests/`.**

- `test_gf_fill_hook_shim.py`, new: (1) enter/exit round-trip on three fake pools leaves core's
  order intact; (2) an item placed inside the view is absent from its pool and its location
  is absent from `fill_locations` on exit; (3) an item popped and returned is still present;
  (4) `multiworld.itempool` is empty on exit; (5) exit runs on exception.
- `test_gf_progression_bias.py`: delete the `players_still_prefilling` import and the
  Oracle-of-Seasons test at `:408`; replace with a test that `_foreign_open_locations` offers a
  partner's locations even when its `get_pre_fill_items()` is non-empty (the inverse assertion,
  because at hook time that list is stale and must be ignored).
- `test_gf_incoming_progression.py:64`: delete `test_owner_declared_early_copies_are_left_for_aps_early_pass`.
- `test_gf_keep_out_of_shops.py:391`: rewrite as "copies already placed by the early pass are
  not in the pool the reservation samples", which is what the shim guarantees.
- `test_gf_capital_reconciler.py:148` and `test_gf_keep_out_of_shops.py:50` docstrings: rename.

**Generation, recorded in the PR the way #1458 did.**

| Seed set | Before (#1457 / #1456 tables) | Expect |
|---|---|---|
| 2xER (`num_regions: 2`) + Oracle of Seasons 20.1.13, seeds 1-4, `auto` and `never` | 8/8 generate, with the "still holds" fallback line | 8/8 generate, no fallback line, Oracle receives its quota |
| ER defaults + APQuest, `Key` in `early_items`, six seeds | 6/6 Key in start region | 6/6, with `_declared_early` gone |
| `tools/gf_export_profile.py` at confine 100, 2xER + 2xHK, 2 seeds | useful% per the reservation | within noise of today |
| `tools/gf_multiworld_smoke.py`, the CI matrix | passes | passes, per-lever metrics within noise |
| 1-region seed 1044, `keep_out_of_shops` armed | both Somber [2] in sphere 1 | same |

**CI.** `test/general` in `.ap-test` still passes; our world exposes no `stage_pre_fill`, and
`test_can_remove_locations_in_fill_hook` is the contract we now rely on.

## 6. Rollout

One PR, one changelog entry under the next open window ("Fixed: our cross-world placements now
run in Archipelago's fill hook, after every partner has placed its own items and after early
items; the two v0.6.0.2 workarounds are removed"). New seeds only; no contract change. The
`0.6.0.3` window is open.

## 7. Open question

`cross_game_progression: aggregate` (the legacy one-batch path in `place_released_locks`) moves
with everything else and keeps working. Dropping it is a separate decision; this PR does not
touch it.
