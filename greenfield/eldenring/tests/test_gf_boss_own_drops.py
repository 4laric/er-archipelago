"""#907: a boss's OWN drop rides its own trigger's sweep.

THE ORIGINAL MOTIVATING CASE (CptFabulous, Discord 2026-08-20): an in-game hint placed his Liurnia
Lock at the Lansseax's Glaive check [f530300]. He killed Lansseax's REPLACEMENT (host enemy
randomizer) at the Abandoned Coffin; the swept member checks paid, the glaive did not. The vanilla award
(common event 90005860) is gated on CharacterDead(vanilla chr) -- the replacement's death sets the
site FLAG (the rando's compat layer), which our sweep watches, but the vanilla character never
dies, so AwardItemsIncludingClients never runs. A FLAG IS NOT AN AWARD.

The fix is gen_data's own-drop admission pass: every boss_drops.py row whose flag is a live check,
whose trigger holds a sweep, and whose PRESENTED region equals the sweep's region joins that
sweep's members. These tests re-derive that rule from the committed tables every run, so the pass
cannot silently stop matching (a consumer is not a capture -- this is the capture).
"""
import unittest

from ..boss_drops import BOSS_DROP_ENTITY
from ..boss_sweeps import DUNGEON_SWEEPS, SWEEP_REGION
from ..data import LOCATIONS

GLAIVE_FLAG = 530300
GLAIVE_TRIGGER = 1041520800   # m60_41_52, the terminal Rampartside fight
COFFIN_TRIGGER = 1037510800   # m60_37_51, the non-terminal apparition
SENESSAX_FLAG = 530805
SENESSAX_TRIGGER = 2054390850


def _flag_to_ap_and_region():
    f2a, f2r = {}, {}
    for region, locs in LOCATIONS.items():
        for _name, ap, flag in locs:
            f2a[int(flag)] = ap
            f2r[int(flag)] = region
    return f2a, f2r


class OwnDropSweeps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f2a, cls.f2r = _flag_to_ap_and_region()

    def test_the_motivating_case_lansseax(self):
        """The Glaive rides the terminal fight; the Coffin retreat cannot pay the final sweep."""
        ap = self.f2a.get(GLAIVE_FLAG)
        self.assertIsNotNone(ap, "f530300 is no longer a check?!")
        self.assertIn(GLAIVE_TRIGGER, DUNGEON_SWEEPS, "the Rampartside trigger lost its sweep")
        self.assertIn(ap, DUNGEON_SWEEPS[GLAIVE_TRIGGER],
                      "f530300 is not swept by its own trigger -- the #907 admission pass "
                      "regressed, and CptFabulous's bug is back")
        self.assertEqual(SWEEP_REGION[GLAIVE_TRIGGER], self.f2r[GLAIVE_FLAG],
                         "the glaive and its sweep disagree on region")
        self.assertNotIn(COFFIN_TRIGGER, DUNGEON_SWEEPS,
                         "the non-terminal Coffin encounter must not pay the final Lansseax sweep")

    def test_senessax_pays_both_co_firing_stone_checks(self):
        """One boss-drop flag drives two reward lots; both AP locations must ride the kill."""
        aps = [ap for region, locs in LOCATIONS.items() for _name, ap, flag in locs
               if flag == SENESSAX_FLAG]
        self.assertEqual(len(aps), 2, "Senessax must expose one check per reward lot")
        self.assertTrue(set(aps) <= set(DUNGEON_SWEEPS[SENESSAX_TRIGGER]),
                        "the own-drop admission must not overwrite one co-check with the other")

    def test_the_rule_not_the_list(self):
        """Every admissible boss_drops row IS swept; every inadmissible one is OUT for a named
        reason. Re-derived, so gen_data's pass and this test cannot drift apart silently."""
        # WITNESS first: an empty table would green everything below for the wrong reason.
        self.assertGreater(len(BOSS_DROP_ENTITY), 50, "boss_drops.py shrank -- rerun the datamine")
        swept_pairs = {(t, ap) for t, mem in DUNGEON_SWEEPS.items() for ap in mem}
        admitted, nosweep, notcheck, mismatch = [], [], [], []
        for flag, trig in sorted(BOSS_DROP_ENTITY.items()):
            ap = self.f2a.get(flag)
            if ap is None:
                notcheck.append(flag); continue
            if trig not in DUNGEON_SWEEPS:
                nosweep.append(flag); continue
            if self.f2r[flag] != SWEEP_REGION.get(trig):
                mismatch.append(flag); continue
            admitted.append((flag, trig))
            self.assertIn((trig, ap), swept_pairs,
                          "f%d passes every admission gate but is NOT in trigger %d's sweep"
                          % (flag, trig))
        # The fail-closed remainder, pinned. A shrink here is the loop working (a suppressed
        # trigger gained a sweep, or a dead row became a check) -- name it. A growth means the
        # sweep builder dropped a trigger and its drop fell out with it: that is a regression.
        self.assertEqual(len(admitted), 74, "the admitted set moved (was 74 after #1296)")
        self.assertEqual(sorted(notcheck), [530861],
                         "the not-a-check remainder moved -- if one became a check it must now "
                         "be swept (the rule above already asserts it); update this pin with why")
        self.assertEqual(len(nosweep), 13,
                         "the trigger-without-sweep remainder moved (was 13: suppressed phase "
                         "pairs and memberless tiles, x340-family heads). If it shrank, a trigger "
                         "gained a sweep and its drop is now covered; if it grew, a sweep VANISHED "
                         "and took a boss's own drop with it -- that is #907 again, look")
        self.assertEqual(mismatch, [],
                         "a drop's presented region no longer matches its sweep's -- gen_data "
                         "fails these CLOSED, so this row is silently unswept: rule on it")

    def test_double_grant_is_impossible_by_flag(self):
        """One drop flag, one owning trigger: no drop may be swept by TWO triggers (the #363
        duplication shape, one table over)."""
        drop_aps = {self.f2a[f]: f for f in BOSS_DROP_ENTITY if f in self.f2a}
        owners = {}
        for trig, mem in DUNGEON_SWEEPS.items():
            for ap in mem:
                if ap in drop_aps:
                    owners.setdefault(ap, []).append(trig)
        self.assertTrue(owners, "WITNESS: no swept drop found at all")
        multi = {drop_aps[ap]: ts for ap, ts in owners.items() if len(ts) > 1}
        self.assertEqual(multi, {}, "a boss drop is swept by more than one trigger")
