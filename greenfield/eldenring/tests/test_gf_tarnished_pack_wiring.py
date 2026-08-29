"""#1096 -- `core` publishes the Patch 1.17 pool exclusion into `gf_dlc_excluded`.

The decision logic (unconditional exclusion by verified FullID) is proved AP-free in
test_gf_tarnished_pack_exclude.py. This asserts the WIRING that makes it reach the pool: the world's
`gf_dlc_excluded` -- the single set every pool-augmentation feature reads (filler_budget,
pool_builder, presence_floor, progressive, finale, scadu_supply, ...) -- must be exactly what
`tarnished_pack.pool_excluded_names` returns. If that ever drifts, the names pasted in on 2026-08-28
would be dropped from the decision but never reach a single placement path, and every pre-patch seed
would look identical -- so this is the guard that keeps patch day a one-line edit.

Needs the installed world, so it is `importorskip`-guarded and runs in the `tests` job.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import tarnished_pack as tp  # noqa: E402
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from worlds.eldenring.item_ids import DLC_ITEM_NAMES, ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring"


class TarnishedExclusionIsPublished(WorldTestBase):
    game = GAME
    # DLC OFF so gf_dlc_excluded is non-empty today (the DLC names) -- the comparison then witnesses
    # a real set, not two empty ones, and would catch a helper that silently returned nothing.
    options = {"num_regions": 6, "enable_dlc": False}

    def test_gf_dlc_excluded_is_exactly_the_helper_output(self):
        want = tp.pool_excluded_names(
            self.world.gf_dlc_on, DLC_ITEM_NAMES, ITEM_CATALOG,
            self.world.gf_tarnished_pack_on)
        self.assertEqual(
            self.world.gf_dlc_excluded, want,
            "gf_dlc_excluded must equal tarnished_pack.pool_excluded_names(gf_dlc_on, "
            "DLC_ITEM_NAMES, ITEM_CATALOG)"
            " -- the resolved set every pool path reads. If core stops routing through the helper, "
            "the patch-day Tarnished names never reach the pool.")

    def test_the_dlc_names_are_actually_present_so_the_comparison_is_not_vacuous(self):
        # The witness: DLC-off must exclude a non-empty set, else the equality above is two empties.
        self.assertGreater(
            len(self.world.gf_dlc_excluded), 0,
            "DLC-off seed excluded nothing -- gf_dlc_excluded is empty, so the wiring test compares "
            "two empty sets. DLC_ITEM_NAMES should be non-empty on a real catalog.")

    def test_disabled_pack_removes_every_pack_location_at_the_seed_chokepoint(self):
        seen = {int(row[2]) for region in LOCATIONS for row in self.world._seed_locations(region)}
        self.assertTrue(tp.TARNISHED_PACK_LOCATION_FLAGS, "the exclusion test has no pack flags")
        self.assertFalse(tp.TARNISHED_PACK_LOCATION_FLAGS & seen)


class TarnishedOwnershipEnablesEquipment(WorldTestBase):
    game = GAME
    options = {"num_regions": 6, "enable_dlc": True, "enable_tarnished_pack": True}

    def test_enabled_equipment_is_not_excluded(self):
        names = frozenset(tp.TARNISHED_PACK_EQUIPMENT)
        self.assertTrue(names <= set(ITEM_CATALOG))
        self.assertFalse(names & self.world.gf_dlc_excluded)

    def test_enabled_pack_publishes_every_verified_location_flag(self):
        seen = {int(row[2]) for region in LOCATIONS for row in self.world._seed_locations(region)}
        self.assertTrue(tp.TARNISHED_PACK_LOCATION_FLAGS <= seen)
