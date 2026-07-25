"""The completion condition must name a region THIS SEED ACTUALLY HAS.

The bug (found by the fuzz gate 2026-07-24, GF-fuzz-573519869-0021; latent since the mode's birth
commit 28d0540): natural_progression hardcoded `GOAL_REGION` ("Leyndell") into
`completion_condition`. Under `dlc_only` every BASE region is dropped, so Leyndell is never created
and `state.can_reach("Leyndell", "Region", p)` raised `KeyError: 'Leyndell'` straight out of AP's
region cache. It surfaced in pre_fill because BaseClasses evaluates the completion lambda on EVERY
fill_restrictive batch, unconditionally -- accessibility does not gate it.

The rule this locks down is goal_locations.py's own: the goal is NEVER a hardcoded region. For any
kept set the derived goal must be a MEMBER of that set -- otherwise the seed cannot be completed and,
worse, cannot even be generated.
"""
import random
import unittest

from ..data import FINALE_REGION, HUB, REGIONS
from ..features.finale import finale_active
from ..features.goal_locations import terminal_goal_ids
from ..region_spine import GOAL_REGION, DLC_REGIONS, compute_kept


def _created(kept):
    """Regions the world actually builds: the hub, the kept set, and -- only when its requirements
    are kept -- the conditional finale region (features/finale.py). `Ashen Capital` is NOT in
    data.REGIONS and is never rolled, so asserting `goal in kept` is too strict; asserting the goal
    is REACHABLE-BY-NAME is the real invariant, because that is what can_reach looks up."""
    out = set(kept) | {HUB}
    if finale_active(kept):
        out.add(FINALE_REGION)
    return out


class GoalRegionIsAlwaysKept(unittest.TestCase):
    def test_dlc_only_derives_a_kept_goal(self):
        """THE REPRODUCER: a DLC-only kept set has no Leyndell, so the goal must come from the set."""
        kept = [r for r in REGIONS if r in set(DLC_REGIONS)]
        self.assertTrue(kept, "no DLC regions in REGIONS -- the fixture is wrong, not the code")
        self.assertNotIn(GOAL_REGION, kept, "fixture must not contain the hardcoded goal")
        goal, _ids = terminal_goal_ids(kept)
        self.assertIsNotNone(goal, "no goal derived for a DLC-only seed")
        self.assertIn(goal, _created(kept),
                      "derived goal %r is not a created region -- can_reach would KeyError" % goal)

    def test_base_only_derives_a_kept_goal(self):
        kept = [r for r in REGIONS if r not in set(DLC_REGIONS)]
        goal, _ids = terminal_goal_ids(kept)
        self.assertIn(goal, _created(kept), "derived goal %r is not a created region" % goal)

    def test_every_num_regions_slice_derives_a_kept_goal(self):
        """Walk the whole num_regions range: no N may produce a goal outside its own kept set."""
        bad = []
        for n in range(1, len(REGIONS) + 1):
            for order in ("spine", "rolled"):
                kept = compute_kept(n, order, random.Random(n), list(REGIONS))
                goal, _ids = terminal_goal_ids(kept)
                if goal is not None and goal not in _created(kept):
                    bad.append((n, order, goal))
        self.assertEqual(bad, [], "kept sets whose derived goal is not a created region: %r"
                                  % (bad[:5],))


if __name__ == "__main__":
    unittest.main()
