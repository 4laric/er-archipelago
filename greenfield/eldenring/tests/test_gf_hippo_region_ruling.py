"""#885's acceptance test: the Golden Hippopotamus presents as Scadu Altus EVERYWHERE.

THE MOTIVATING CASE (cokeman5 on #330, 2026-08-18, the third player-facing surfacing): *"the tracker
says I am missing the golden hippopotamus sweep, but the golden hippopotamus' boss room counts as
part of Scadu Altus, not Shadow Keep."* Worse than the label: a player holding the Shadow Keep Lock
without Scadu Altus, shown 100+ `Shadow Keep ::` rows "also granted by Golden Hippopotamus",
reasonably goes to kill the Hippo -- and the kick guard ejects them from the arena's play_region
(bucket 69000), which their seed never opened. Scadu Altus alone, by contrast, always suffices for
every one of those rows: the fight is fought standing in Scadu Altus and the kill sweeps them all.

THE RULING (Alaric 2026-08-19, #885): reward, sweep trigger, sweep grouping, AND every granted
member present as Scadu Altus. Implemented as gen_data.DUNGEON_REGION_CURATED["m21_00_00_00"];
this file asserts each surface so no regen or branch reorder can silently split them apart again
(#53/#146/#445 are the history of exactly that).

The one deliberate carve-out is asserted too: f68800, the m21_00 cookbook the Hippo does NOT grant,
stays Shadow Keep -- Scadu-Altus-labelled with no sweep route it would be a created-but-kick-locked
check in a Scadu-Altus-only seed (see FLAG_REGION_OVERRIDE[68800]).
"""
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

HIPPO_DEFEAT = 21000850
HIPPO_REWARD_FLAG = 510440
COOKBOOK_FLAG = 68800
ARENA = "Scadu Altus"


class HippoPresentsAsScaduAltusEverywhere(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from .. import boss_sweeps, data
        cls.boss_sweeps = boss_sweeps
        cls.data = data
        cls.by_ap = {}
        cls.by_flag = {}
        for region, rows in data.LOCATIONS.items():
            for (name, ap, flag) in rows:
                cls.by_ap[ap] = (region, name)
                cls.by_flag.setdefault(int(flag), []).append((region, name))

    def test_sweep_grouping_region_is_the_arena(self):
        """SWEEP_REGION is what groups the sweep for presentation/keeping; it must not disagree
        with SWEEP_ARENA_REGION (the #445 reachability key) for the Hippo ever again."""
        self.assertEqual(self.boss_sweeps.SWEEP_REGION.get(HIPPO_DEFEAT), ARENA)
        self.assertEqual(self.boss_sweeps.SWEEP_ARENA_REGION.get(HIPPO_DEFEAT), ARENA)

    def test_every_granted_member_presents_as_the_arena_region(self):
        members = self.boss_sweeps.DUNGEON_SWEEPS.get(HIPPO_DEFEAT) or []
        self.assertGreater(len(members), 80, "WITNESS: the Hippo's membership collapsed -- an empty "
                                             "list would make the assertion below vacuously green")
        wrong = [(ap,) + self.by_ap[ap] for ap in members if self.by_ap[ap][0] != ARENA]
        self.assertEqual(wrong, [], "Hippo-granted member(s) present as a region other than the "
                                    "arena -- the split #885 removed is back: %r" % wrong[:10])

    def test_the_reward_presents_as_the_arena_region(self):
        rows = self.by_flag.get(HIPPO_REWARD_FLAG) or []
        self.assertTrue(rows, "WITNESS: the Hippo reward flag has no locations at all")
        self.assertEqual({r for (r, _n) in rows}, {ARENA},
                         "the Hippo's reward left Scadu Altus: %r" % rows)

    def test_the_ungranted_cookbook_stays_on_its_ground(self):
        rows = self.by_flag.get(COOKBOOK_FLAG) or []
        self.assertTrue(rows, "WITNESS: the m21_00 cookbook vanished from the corpus")
        self.assertEqual({r for (r, _n) in rows}, {"Shadow Keep"},
                         "f68800 has no Hippo grant; off Shadow Keep it is a created-but-kick-locked "
                         "check in any Scadu-Altus-only seed: %r" % rows)
        for (_r, name) in rows:
            self.assertNotIn("also granted by", name,
                             "f68800 grew a sweep clause -- if it IS granted now, the pin in "
                             "gen_data.FLAG_REGION_OVERRIDE should be re-examined, not this test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
