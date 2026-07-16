# Greenfield ER tests

The apworld's test suite. Everything here is derived from the greenfield world's
own generated data and AP's (MIT) `WorldTestBase` harness — no test or data is
copied from any other apworld. A handful of pure-data tests run without
Archipelago, but the suite as a whole needs an installed world inside an AP
checkout, so:

**The canonical way to run it is the harness:**

```
python tools/gf_test.py             # bootstrap .ap-test/, install the world, run everything
python tools/gf_test.py -k shops    # extra args pass through to pytest
```

`gf_test.py` bootstraps its own **pinned upstream** Archipelago checkout (version
from `.ap-version`) into `.ap-test/`, installs (copies) the world into it, and
runs pytest there. It refuses to run against a fork of Archipelago and never
touches your working `.\Archipelago` — see the docstring for why.
`run_ci.ps1` runs this suite plus every other automated gate.

## Map of the suite

Helpers (not tests): `_util.py` (progression-surface-aware fill helpers),
`pool_builder_sweep.py` (a standalone scaling harness for the pool builder).

**Data invariants & generated-data gates** (the committed data must be
well-formed, fresh, and true to the game):
`test_gf_data.py` (structural invariants for the data tables, no AP needed),
`test_gf_gen_stamp.py` (gen-input hash gate), `test_coverage_gate.py`
(coverage baseline over an option matrix), `test_gf_no_phantom_flags.py`
(every check's acquisition flag exists in the game), `test_gf_item_exists.py`
(every check's item exists), `test_gf_defaulted_region_guard.py` (a guessed
region may not carry progression), `test_gf_lod_tile_regions.py` (coarse LOD
tiles are not fine tiles), `test_gf_play_region_buckets.py` (lock-enforcement
buckets vs the game's real play_region universe), `test_gf_missable.py` and
`test_gf_important_locations.py` (location tagging), `test_gf_gestures.py`
(gesture-pickup derivation).

**Region & grace oracles** (independent, artifact-derived ground truth for the
region assignment and grace model):
`test_gf_region_correctness.py`, `test_gf_region_artifact_oracle.py`,
`test_gf_region_provenance_oracle.py`, `test_gf_grace_region_correctness.py`,
`test_gf_grace_ground.py`, `test_gf_grace_skip_oracle.py`,
`test_gf_grace_skip_classes.py`, `test_gf_arena_graces.py`,
`test_gf_grace_gates.py`, `test_gf_gated_children.py`.

**Fill, region scope & reachability** (WorldTestBase — real generated
multiworlds):
`test_gf_world.py` (the base suite: fill, beatable, reachability, slot_data),
`test_gf_num_regions.py` (the marquee sealing mode), `test_gf_region_diversity.py`,
`test_gf_dlc.py` and `test_gf_dlc_pool_leak.py` (EnableDLC / DLCOnly scope),
`test_gf_start_anchor.py` (the precollected opening Region Lock),
`test_gf_scaling_sphere.py` (completion-scaling over true fill spheres),
`test_gf_progression_surface.py` and `test_gf_progression_surface_option.py`
(which locations may hold progression), `test_gf_foreign_apworld_degrade.py`
(a foreign apworld degrades to a playable vanilla seed).

**Features:**
- bosses: `test_gf_boss_locks.py`, `test_gf_boss_lock_items.py`,
  `test_gf_boss_keys.py`, `test_gf_boss_sweeps.py`
- shops: `test_gf_shops.py`, `test_gf_shop_release_gate.py`,
  `test_gf_shop_slot_pins.py`, `test_gf_weapon_shop_slots.py`
- pool builder & filler economy: `test_gf_pool_builder.py`,
  `test_gf_pool_builder_all_filler.py`, `test_gf_pool_builder_categories.py`,
  `test_gf_pool_builder_intensity.py`, `test_gf_pool_builder_juice_protected.py`,
  `test_gf_pool_builder_reserved.py`, `test_gf_filler_curation.py`,
  `test_gf_filler_economy_floor.py`, `test_gf_collectathon_protected.py`
- goal & finale: `test_gf_ending.py`, `test_gf_goal_terminal.py`,
  `test_gf_finale.py`, `test_gf_capital_reconciler.py`
- items & progression: `test_gf_item_shuffle.py`, `test_gf_progressive.py`,
  `test_gf_progressive_flasks.py`, `test_gf_local_items.py`,
  `test_gf_legacy_key_gate.py`, `test_gf_legible_keys.py`,
  `test_gf_area_locks.py`, `test_gf_auto_upgrade_echo.py`, `test_gf_p7.py`
  (deathlink + start items), `test_gf_features_smoke.py` (feature registry),
  `test_gf_options.py` (every option carries a real description)

**Contract & packaging** (the apworld <-> client seam):
`test_gf_client_contract_paths.py` (every slot_data path the client reads has a
gen-side producer), `test_gf_slot_data_fixture.py` (contract-drift snapshot),
`test_gf_progression_surface_contract.py`, `test_gf_version_handshake.py`
(apworld/DLL hash-matched pair), `test_gf_apworld_manifest.py`
(`archipelago.json` names the game the world registers),
`test_gf_shipping_yaml.py` (the shipped yaml names the game we ship).
