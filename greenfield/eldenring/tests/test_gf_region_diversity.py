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
from worlds.eldenring.data import FINALE_REGION  # noqa: E402
from ._util import world_item_names  # noqa: E402

GAME = "Elden Ring"
# The synthetic Erdtree burn (SPEC-ashen-capital-lock): minted on every base-game seed, for a
# region that is never kept and never rolled. It is what carries winnability now.
_FINALE_LOCK = f"{FINALE_REGION} Lock"


class RolledDiversity(WorldTestBase):
    game = GAME
    options = {"num_regions": 4}

    # A spread of fixed seeds keeps this deterministic while giving the RNG room to diverge.
    SEEDS = (1, 2, 7, 13, 101, 5551212)

    def test_rolled_kept_sets_diverge_and_stay_winnable(self):
        n = 4
        kept_sets = []
        without_goal = 0
        for seed in self.SEEDS:
            self.world_setup(seed=seed)
            kept = frozenset(self.world._kept())
            # WAS `assertIn(GOAL_REGION, kept)` with the reason "(winnability)". The capital was
            # force-kept under `auto` so the goal derivation had a terminus; SPEC-ashen-capital-lock
            # (2026-08-06) deleted that force-keep and moved the terminus to the Ashen Capital,
            # which exists on every base-game seed and is entered from the HUB with its own lock.
            # Winnability is the same claim at its new carrier: the item that opens the goal is in
            # this seed's pool.
            self.assertIn(_FINALE_LOCK, world_item_names(self),
                          f"rolled seed {seed}: the finale's lock is the only way into the goal "
                          f"region -- without it the seed is unwinnable")
            without_goal += GOAL_REGION not in kept
            # rolled keeps N random regions plus the REGION_PARENT closure, and every kept child
            # must have its ancestors kept (the invariant that replaces the exact count). The
            # `+ 1` this bound used to carry was the goal append; it is gone with the force-keep,
            # so the bound is one region TIGHTER than it was.
            self.assertGreaterEqual(len(kept), n,
                                    f"rolled seed {seed}: kept fewer than N regions")
            self.assertLessEqual(len(kept), n + sum(len(parent_chain(r)) for r in kept),
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
        # The other half of the deleted force-keep, stated so it cannot come back unnoticed: on a
        # 4-wide draw over 31 regions, some of these seeds must MISS the capital entirely.
        self.assertGreater(without_goal, 0,
                           "every one of these seeds kept the goal region on a 4-wide draw -- the "
                           "`auto` GOAL_REGION force-keep is back")

    def test_rolled_slot_data_region_count_tracks_kept(self):
        self.world_setup(seed=7)
        kept = set(self.world._kept())
        sd = self.world.fill_slot_data()
        self.assertEqual(sd["region_count"], len(kept),
                         "rolled slot_data.region_count must equal the kept count")
