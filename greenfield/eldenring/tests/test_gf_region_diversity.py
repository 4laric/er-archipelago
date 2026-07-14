"""num_regions region-diversity gate -- WorldTestBase (the marquee mode).

Two contracts, both derived from the greenfield region spine:

  * order='spine': the kept set is deterministic -- the first N of SPINE, plus the always-kept
    goal region -- and slot_data.region_count matches. The base WorldTestBase suite (test_fill)
    already proves the sealed seed stays beatable; here we pin the exact scope for a few N.

  * order='rolled': the kept set is randomised per seed. Across a handful of fixed seeds the rolled
    selections must actually DIFFER (real diversity, not a stuck RNG) while ALWAYS keeping the goal
    region so the seed stays winnable. Deterministic (fixed seeds) and fast (no extra generation
    beyond world_setup).

importorskips when AP isn't importable (source-tree sandbox) -> no-op there; runs once installed.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring/tests/test_gf_region_diversity.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.region_spine import GOAL_REGION, SPINE, parent_chain  # noqa: E402

GAME = "Elden Ring"


def _expected_spine(n):
    """Deterministic spine kept set for num_regions=n: first-N of SPINE + goal + REGION_PARENT
    closure (a gated child pulls its ancestors in -- the always-kept capital pulls Altus; derived
    from parent_chain, never re-pinned)."""
    base = list(SPINE[:n])
    if GOAL_REGION not in base:
        base.append(GOAL_REGION)
    for r in list(base):
        for anc in parent_chain(r):
            if anc not in base:
                base.append(anc)
    return set(base)


def _assert_spine_scope(tc, n):
    """Shared assertions for a spine-ordered num_regions=n world already built by setUp."""
    kept = set(tc.world._kept())
    tc.assertEqual(kept, _expected_spine(n),
                   f"spine num_regions={n} must keep first-{n} of SPINE + goal")
    tc.assertIn(GOAL_REGION, kept, "goal region must always be kept")
    tc.assertEqual(len(kept), len(_expected_spine(n)),
                   "kept count must be N + goal + parent-closure additions (all derived)")
    sd = tc.world.fill_slot_data()
    tc.assertEqual(sd["region_count"], len(kept),
                   "slot_data.region_count must equal the kept count")


class SpineScope1(WorldTestBase):
    game = GAME
    options = {"num_regions": 1, "num_regions_order": "spine"}

    def test_spine_scope(self):
        _assert_spine_scope(self, 1)


class SpineScope3(WorldTestBase):
    game = GAME
    options = {"num_regions": 3, "num_regions_order": "spine"}

    def test_spine_scope(self):
        _assert_spine_scope(self, 3)


class SpineScope5(WorldTestBase):
    game = GAME
    options = {"num_regions": 5, "num_regions_order": "spine"}

    def test_spine_scope(self):
        _assert_spine_scope(self, 5)


class RolledDiversity(WorldTestBase):
    game = GAME
    options = {"num_regions": 4, "num_regions_order": "rolled"}

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
