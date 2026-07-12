"""A grace INSIDE a boss arena must never be force-lit.

A region lock force-lights ("grants") every grace in its region so the player can warp in. That is
only safe if the grace's spawn point is somewhere safe to stand. A grace that sits inside a boss
arena is not: warping there drops you into a live boss fight.

Playtest 2026-07-11 (Alaric): the Redmane Castle grace sits in the Misbegotten Warrior + Crucible
Knight duo arena, so the Caelid lock warped him into the middle of the duo. That was the THIRD such
report (Maliketh 71300, ashen Leyndell, Redmane) against a HAND-MAINTAINED skip list -- i.e. we were
pinning symptoms. So the class is now DERIVED:

    distance(grace spawn, nearest boss ENEMY spawn) < 40m  =>  arena grace, never force-light

Sources (all ground truth, no hand lists):
  * boss set  -- EMEVD `DisplayBossHealthBar(Enabled, <entity>)`
  * boss pos  -- witchy'd MSB  <map>-msb-dcx/Part/Enemy/*.xml  -> <EntityID> + <Position>
  * grace pos -- grace_flags.tsv (BonfireWarpParam)
Both position sets are map-local, so they compare directly. See tools/datamine_arena_graces.py,
which writes greenfield/arena_graces.tsv.

The derivation independently re-derives 23 of the 48 hand-skipped flags (validating them) and caught
5 that were still being granted -- including 76419, a grace 13.3m from Starscourge Radahn.

NOTE the tsv is a LOWER BOUND: 52 of the 118 boss maps have no unpacked MSB yet, so gen_data UNIONS
the derived set with the hand lists rather than replacing them. Tile co-location is NOT a usable
fallback -- 172 granted graces share a tile with a boss (all 7 Stormveil graces sit on Godrick's).
"""
import unittest

from ..region_graces import REGION_GRACE_POINTS

# Derived arena graces that were being GRANTED before the oracle landed (2026-07-11).
# Each is within 40m of a boss spawn; granting them warps the player onto a live boss.
_DERIVED_REGRESSIONS = {
    73119: "31190850 (30.3m)",
    76419: "1051360801 -- STARSCOURGE RADAHN (13.3m)",
    76524: "1051570800 (13.6m)",
    76823: "2048440800 (7.6m)",
    76945: "2044450800 (1.6m)",
}

# The three playtest scars that motivated the derivation.
# The playtest scars are now DERIVED (the oracle measures them), so they are no longer "hand" entries --
# but they must still never be granted. 76414/76416 were REMOVED: they were my over-skip (46.6m / 119.8m
# from the duo), and 76415 at 9.4m is the actual Redmane arena grace.
_PLAYTEST_SCARS = {
    71300: "Maliketh the Black Blade -- now DERIVED (29.1m)",
    76415: "Redmane Castle duo arena -- now DERIVED (9.4m); NOT 76414/76416, which are 46.6m / 119.8m",
}

# Graces I once skipped by GUESSING conservatively, now measured SAFE. They must be GRANTED.
_OVER_SKIPPED_NOW_SAFE = {
    76414: "46.6m from the Redmane duo",
    76416: "119.8m from the Redmane duo",
}


class TestArenaGraces(unittest.TestCase):

    def _all_granted(self):
        return {f for flags in REGION_GRACE_POINTS.values() for f in flags}

    def test_no_derived_arena_grace_is_granted(self):
        """The oracle's finding: none of these may ride a region lock."""
        granted = self._all_granted()
        for flag, who in _DERIVED_REGRESSIONS.items():
            self.assertNotIn(
                flag, granted,
                f"grace {flag} is INSIDE a boss arena (nearest boss {who}) -- force-lighting it warps "
                f"the player onto a live boss")

    def test_playtest_scars_stay_skipped(self):
        """Regression guard on the ones we learned the hard way (now all DERIVED)."""
        granted = self._all_granted()
        for flag, who in _PLAYTEST_SCARS.items():
            self.assertNotIn(flag, granted,
                             f"grace {flag} ({who}) must never be force-lit")

    def test_over_skipped_graces_are_granted_again(self):
        """A conservative GUESS is still a guess. I skipped all three Redmane-tile graces because I could
        not tell which was in the arena -- silently costing the player two legitimate graces. The oracle
        measured them; these two are SAFE and must be granted."""
        granted = self._all_granted()
        for flag, why in _OVER_SKIPPED_NOW_SAFE.items():
            self.assertIn(flag, granted,
                          f"grace {flag} is SAFE ({why}) -- do not skip it. Measure, don't guess.")

    def test_derived_table_is_present_and_used(self):
        """If arena_graces.tsv goes missing, gen_data silently degrades to the hand lists -- and the
        5 derived-only flags come back. Fail loudly instead."""
        granted = self._all_granted()
        leaked = sorted(set(_DERIVED_REGRESSIONS) & granted)
        self.assertEqual([], leaked,
                         f"arena_graces.tsv appears to be missing at generation time -- {leaked} are "
                         f"granted again. Regenerate with tools/datamine_arena_graces.py.")


if __name__ == "__main__":
    unittest.main()
