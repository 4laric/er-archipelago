"""num_regions (marquee) tests -- WorldTestBase, needs AP. Gen a sealed seed and assert the kept
set, goal, and slot_data region_count. Base suite (test_fill etc.) proves it stays winnable."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.region_spine import GOAL_REGION, SPINE  # noqa: E402
from ._util import world_item_names  # noqa: E402

GAME = "Elden Ring (Greenfield)"


class NumRegions3Spine(WorldTestBase):
    game = GAME
    options = {"num_regions": 3, "num_regions_order": "spine"}

    def test_kept_is_spine_prefix_plus_goal(self):
        locks = sorted(n for n in world_item_names(self) if n.endswith(" Lock"))
        expected = sorted(f"{r} Lock" for r in list(SPINE[:3]) + [GOAL_REGION])
        self.assertEqual(locks, expected, "kept locks must be spine first-3 + goal region")

    def test_region_count_and_scope_in_slot_data(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["region_count"], 4)
        # every locationFlags entry belongs to a kept (or hub) region -- no sealed leakage
        self.assertGreater(len(sd["locationFlags"]), 0)

    def test_sealed_region_not_created(self):
        names = {r.name for r in self.multiworld.get_regions() if r.player == self.player}
        self.assertNotIn("Caelid", names, "a sealed region must not be instantiated")
        self.assertIn(GOAL_REGION, names)


class NumRegions1Spine(WorldTestBase):
    game = GAME
    options = {"num_regions": 1, "num_regions_order": "spine"}

    def test_min_scope_keeps_first_plus_goal(self):
        locks = sorted(n for n in world_item_names(self) if n.endswith(" Lock"))
        self.assertEqual(locks, sorted([f"{SPINE[0]} Lock", f"{GOAL_REGION} Lock"]))
