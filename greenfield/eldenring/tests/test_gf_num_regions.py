"""num_regions (marquee) tests -- WorldTestBase, needs AP. Gen a sealed seed and assert the kept
set, goal, and slot_data region_count. Base suite (test_fill etc.) proves it stays winnable.

REWRITTEN 2026-08-05 with the removal of the `spine` order. These two fixtures used to name the
regions they expected -- first-N of SPINE plus the goal -- which only worked because the draw was
deterministic. A random draw cannot be asserted by identity, and re-pinning to a fixed seed would
just hide the same problem behind a magic number.

What they are actually about, and what they still assert, is AGREEMENT between the four views of the
kept set that a mis-scoped seed would desynchronise: the Lock ITEMS, the instantiated REGIONS, the
slot-data COUNT, and the parent closure. None of that needs to know which regions were drawn. The
draw itself (size, closure, goal presence, reachability of every region) is covered as properties
over a 400-seed sweep in test_gf_region_selection.py.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.region_spine import GOAL_REGION, REGIONS, parent_chain  # noqa: E402
from ._util import world_item_names  # noqa: E402

GAME = "Elden Ring"


def _assert_views_agree(tc, n):
    """The kept set seen four ways must be ONE set. Shared by both scopes below."""
    kept = list(tc.world._kept())
    tc.assertEqual(len(kept), len(set(kept)), "duplicate region in the kept set")
    tc.assertGreaterEqual(len(kept), n, f"kept {len(kept)} regions, num_regions asked for {n}")
    tc.assertIn(GOAL_REGION, kept, "an `auto`-goal seed must keep the goal region (winnability)")

    # (1) the ITEM side: one Lock per kept region, and no Lock for anything else.
    locks = sorted(name for name in world_item_names(tc) if name.endswith(" Lock"))
    tc.assertEqual(locks, sorted(f"{r} Lock" for r in kept),
                   "the Lock items and the kept set must be the same list -- a Lock for a sealed "
                   "region is unobtainable, a kept region with no Lock is an unlockable gate")

    # (2) the parent closure: a gated child is never kept without its ancestors.
    for r in kept:
        for anc in parent_chain(r):
            tc.assertIn(anc, kept, f"kept child {r} without ancestor {anc}")

    # (3) the REGION side: sealed regions are never instantiated. DERIVED from the draw -- the old
    # version hardcoded "Caelid", which a random draw can legitimately keep.
    names = {r.name for r in tc.multiworld.get_regions() if r.player == tc.player}
    sealed = set(REGIONS) - set(kept)
    tc.assertTrue(sealed, f"test basis broken: num_regions={n} must seal something")
    tc.assertEqual(names & sealed, set(), "a sealed region must not be instantiated")
    tc.assertIn(GOAL_REGION, names)

    # (4) the SLOT-DATA side: region_count is the kept count, and checks actually reached it.
    sd = tc.world.fill_slot_data()
    tc.assertEqual(sd["region_count"], len(kept),
                   "slot_data.region_count must equal the kept count")
    tc.assertGreater(len(sd["locationFlags"]), 0, "no locationFlags reached the client")


class NumRegions3(WorldTestBase):
    """A mid-sized sealed seed: 3 drawn + the goal region + the parent closure."""
    game = GAME
    options = {"num_regions": 3}

    def test_every_view_of_the_kept_set_agrees(self):
        _assert_views_agree(self, 3)


class NumRegions1(WorldTestBase):
    """The MINIMUM draw. Worth its own fixture: N=1 is where a seed that mis-scopes progression has
    the least room to hide it, and it is the corner the closure has to carry on its own."""
    game = GAME
    options = {"num_regions": 1}

    def test_every_view_of_the_kept_set_agrees(self):
        _assert_views_agree(self, 1)
