"""num_regions region-diversity gate -- WorldTestBase (the marquee mode).

ONE contract, since the fixed spine draw was removed 2026-08-05: the kept set is randomised per
seed. Across a handful of fixed seeds the selections must actually DIFFER (real diversity, not a
stuck RNG) while ALWAYS keeping the goal region so the seed stays winnable. Deterministic (fixed
seeds) and fast (no extra generation beyond world_setup).

The SpineScope1/3/5 classes that used to sit here asserted the kept set by IDENTITY -- first-N of
SPINE plus the goal -- which was only ever possible because the draw was not random. They are gone;
the invariants they were standing in for (draw size, parent closure, goal presence, every region
reachable) are properties over a 400-seed sweep in test_gf_region_selection.py. The slot-data half
they also covered (region_count == the kept count) survives here in
RolledDiversity.test_rolled_slot_data_region_count_tracks_kept.

importorskips when AP isn't importable (source-tree sandbox) -> no-op there; runs once installed.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring/tests/test_gf_region_diversity.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.region_spine import GOAL_REGION, parent_chain  # noqa: E402

GAME = "Elden Ring"


class RolledDiversity(WorldTestBase):
    game = GAME
    options = {"num_regions": 4}

    # A spread of fixed seeds keeps this deterministic while giving the RNG room to diverge.
    SEEDS = (1, 2, 7, 13, 101, 5551212)

    def test_rolled_kept_sets_diverge_and_keep_goal(self):
        n = 4
        kept_sets = []
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = frozenset(self.world._kept())
            self.assertIn(GOAL_REGION, kept,
                          f"rolled seed {seed}: goal region must always be kept (winnability)")
            # rolled keeps N random regions; the goal is appended if the sample missed it, and
            # the REGION_PARENT closure can add up to len(parent_chain(GOAL_REGION)) + the other
            # children's ancestors -- so the count is a bounded range now, and every kept child
            # must have its ancestors kept (the invariant that replaces the exact count).
            self.assertGreaterEqual(len(kept), n,
                                    f"rolled seed {seed}: kept fewer than N regions")
            self.assertLessEqual(len(kept), n + 1 + sum(len(parent_chain(r)) for r in kept),
                                 f"rolled seed {seed}: kept count {len(kept)} exceeds closure bound")
            for r in kept:
                for anc in parent_chain(r):
                    self.assertIn(anc, kept,
                                  f"rolled seed {seed}: kept child {r} without ancestor {anc}")
            kept_sets.append(kept)
        distinct = set(kept_sets)
        self.assertGreater(len(distinct), 1,
                           "rolled order must produce DIFFERENT kept sets across seeds (diversity); "
                           f"got a single set for all {len(self.SEEDS)} seeds")

    def test_rolled_slot_data_region_count_tracks_kept(self):
        self.world_setup(seed=7)
        kept = set(self.world._kept())
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["region_count"], len(kept),
                         "rolled slot_data.region_count must equal the kept count")
