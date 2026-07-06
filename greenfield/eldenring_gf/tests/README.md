# Greenfield ER tests

Two suites, mirroring the existing `worlds/eldenring/tests` split of "pure structural" +
"AP-framework" tests. Everything here is derived from the greenfield world's own `data.py`
and AP's (MIT) `WorldTestBase` harness -- no test or data is copied from any other apworld.

| file | needs AP? | what it guards |
|------|-----------|----------------|
| `test_gf_data.py`  | no (runs anywhere, ms) | data.py structural invariants: HUB/region split, unique + contiguous ap-ids from 7770000, unique location names, positive flags, LOCATIONS keys == HUB+regions, every region non-empty |
| `test_gf_world.py` | yes (Windows/Py3.11, installed) | `WorldTestBase` base suite (fill, beatable, reachability) + one-lock-per-region pool, goal-needs-all-locks, hub-free, slot_data contract (`world_logic`/`locationFlags`), seed-independent slot_data |

Run:

```
python greenfield/eldenring_gf/tests/test_gf_data.py                  # source tree, no AP (direct unittest; NOT pytest)
python -m pytest worlds/eldenring_gf/tests/test_gf_world.py           # after install (build.ps1 -Greenfield)
.\run_ci.ps1 -OnlyGreenfield                                          # both, via CI, nothing else
```


## Phase 0 (boot contract) — landed

`patch_phase0_boot_contract.py` added `apIdsToItemIds` (filler → Golden Rune [1], GOODS-packed
FullID `0x40000B54`) and `regionOpenFlags` (scalar warp flag per region, grace-derived) to
`fill_slot_data`. Covered by:
- `test_gf_data.py::GreenfieldRegionOpenFlags` — `region_open_flags.py` shape (19 resolved + 3 DLC
  pending partition the region set; unique positive flags). Skips if not yet generated.
- `test_gf_world.py::test_boot_contract_ap_ids_and_open_flags` — filler FullID + open-flag scalars.

3 DLC sub-areas (Abyssal Woods, Jagged Peak, Scadu Altus) are all boss-arena (`map=PENDING`) and stay
`REGION_OPEN_PENDING` until the DLC region audit (SPEC-PARITY.md 14.4); the client treats an absent
open flag as "unlocked", so this is safe.

## Map of the eldenring test suite -> greenfield

The eldenring folder has ~20 test files. Most gate features greenfield does not have yet, so
they are NOT copied verbatim (they would import missing modules and fail). They come online as
their feature is ported onto this clean base (see HANDOFF.md "Next work").

**Ported (greenfield analog exists now):**
- `test_data_tables.py`         -> `test_gf_data.py`
- `TestER.py` (locations unique / default items) -> `test_gf_world.py`
- `test_slot_data_determinism.py` -> `test_gf_world.py::test_slot_data_is_seed_independent`

**Deferred until the feature is ported (no greenfield surface yet):**
- `test_multiworld_gen.py`      -- two-player greenfield gen (portable now; add when useful)
- `test_slot_data_fixture.py`   -- Rust-side slot_data fixture (add with the client contract)
- `test_options_descriptions.py`, `TestEROptionMatrix.py` -- greenfield has no options yet
- `test_boss_locks.py`          -- boss locks
- `test_curated_fill.py`, `test_pool_builder_filler.py`, `test_capped_uniques_pool.py` -- pool builder / curated fill
- `test_grace_pool_leak.py`     -- grace_rando
- `test_key_gates_gen.py`       -- KeyGatesMissable
- `test_local_items_gen.py`     -- local_item_option
- `test_merchant_bells.py`, `test_shop_checks_gen.py`, `test_shop_lock_legibility.py`, `test_shop_slot_map_gen.py` -- shops
- `test_check_item_suppression.py` -- runtime grant/suppress
- `test/test_predicate_equivalence.py` -- predicate-contract migration
