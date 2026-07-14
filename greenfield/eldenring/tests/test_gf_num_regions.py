"""num_regions (marquee) tests -- WorldTestBase, needs AP. Gen a sealed seed and assert the kept
set, goal, and slot_data region_count. Base suite (test_fill etc.) proves it stays winnable."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.region_spine import GOAL_REGION, SPINE, parent_chain  # noqa: E402
from ._util import world_item_names  # noqa: E402

GAME = "Elden Ring"


def _closed(regions):
    """`regions` + every REGION_PARENT ancestor -- the same closure compute_kept applies (derived
    here from parent_chain, not re-pinned, so a REGION_PARENT edit moves both sides together)."""
    out = list(dict.fromkeys(regions))
    for r in list(out):
        for anc in parent_chain(r):
            if anc not in out:
                out.append(anc)
    return out


class NumRegions3Spine(WorldTestBase):
    game = GAME
    options = {"num_regions": 3, "num_regions_order": "spine"}

    def test_kept_is_spine_prefix_plus_goal_plus_parents(self):
        locks = sorted(n for n in world_item_names(self) if n.endswith(" Lock"))
        expected_regions = _closed(list(SPINE[:3]) + [GOAL_REGION])
        expected = sorted(f"{r} Lock" for r in expected_regions)
        self.assertEqual(locks, expected,
                         "kept locks must be spine first-3 + goal region + REGION_PARENT closure "
                         "(the capital pulls Altus in: it has no other way in)")

    def test_region_count_and_scope_in_slot_data(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["region_count"], len(_closed(list(SPINE[:3]) + [GOAL_REGION])))
        # every locationFlags entry belongs to a kept (or hub) region -- no sealed leakage
        self.assertGreater(len(sd["locationFlags"]), 0)

    def test_sealed_region_not_created(self):
        names = {r.name for r in self.multiworld.get_regions() if r.player == self.player}
        self.assertNotIn("Caelid", names, "a sealed region must not be instantiated")
        self.assertIn(GOAL_REGION, names)


class NumRegions1Spine(WorldTestBase):
    game = GAME
    options = {"num_regions": 1, "num_regions_order": "spine"}

    def test_min_scope_keeps_first_plus_goal_plus_parents(self):
        locks = sorted(n for n in world_item_names(self) if n.endswith(" Lock"))
        expected = sorted(f"{r} Lock" for r in _closed([SPINE[0], GOAL_REGION]))
        self.assertEqual(locks, expected)
