"""The five graces a human ruled are NOT arena graces stay GRANTABLE (tier A, no artifacts).

2026-08-10. Unioning boss_healthbars into the arena-grace boss set took the derived table 41 -> 47.
Six were new; Alaric ruled five of them in game:

    76118 Warmaster's Shack          9.0m   Bell Bearing Hunter -- NIGHT-ONLY spawn
    76311 Hermit Merchant's Shack   21.6m   Bell Bearing Hunter -- NIGHT-ONLY spawn
    76451 Isolated Merchant's Shack 17.4m   Bell Bearing Hunter -- NIGHT-ONLY spawn
    76357 Primeval Sorcerer Azur    36.8m   Demi-Human Queen Maggie releases no grace; separate ledge
    76910 Behind the Fort of Reprimand 19.2m  not a boss grace

Three are MERCHANT SHACKS whose "arena" is an ordinary safe place with a conditional night invader.
Withholding them costs the player three shops and two travel nodes. The 47-row table shipped to main
before the exclusions existed and did exactly that -- and NOTHING went red, because the derived count
went UP and the floor only guards against a shrink.

That is what this pins: not the count, the five flags. A count ratchet cannot tell a real new arena
grace from a regression that adds five.

(76313 Windmill Heights was the sixth and is CORRECTLY withheld -- it is 4.0m from the Godskin
Apostle and already in _BOSS_GATED_GRACE_FLAGS. It is deliberately not in this list.)
"""
import os
import re
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

# 🛑 None-SAFE, and the class is SKIPPED rather than run. `find_repo_root` returns None when we are
# not under a repo checkout, and its docstring says "callers skip on None" -- this module did not.
# It joined the None at MODULE scope, so instead of skipping it raised `TypeError: expected str,
# bytes or os.PathLike object, not NoneType` during COLLECTION, which aborts the entire pytest run
# with an error and zero results. A test that cannot run should skip; one that takes the suite down
# with it is worse than absent. (Found 2026-08-16 running the suite with the AP checkout OUTSIDE the
# repo -- `gf_test.py --ap-dir` accepts any path, and every path but one reproduces this.)
ROOT = find_repo_root(os.path.abspath(__file__))
TSV = os.path.join(ROOT, "greenfield", "arena_graces.tsv") if ROOT else ""
GRACES = os.path.join(ROOT, "greenfield", "eldenring", "region_graces.py") if ROOT else ""

RULED_NOT_AN_ARENA = {
    76118: "Warmaster's Shack (Bell Bearing Hunter, night-only)",
    76311: "Hermit Merchant's Shack (Bell Bearing Hunter, night-only)",
    76451: "Isolated Merchant's Shack (Bell Bearing Hunter, night-only)",
    76357: "Primeval Sorcerer Azur (Maggie releases no grace)",
    76910: "Behind the Fort of Reprimand (not a boss grace)",
}
STILL_WITHHELD = 76313   # Windmill Heights, 4.0m from the Godskin Apostle -- the control


@unittest.skipUnless(ROOT is not None, REPO_ONLY_REASON)
class ArenaGraceExclusions(unittest.TestCase):

    def _derived(self):
        with open(TSV, encoding="utf-8") as f:
            return {int(l.split("\t")[0]) for l in f if l[:1].isdigit()}

    def test_the_five_are_not_in_the_derived_arena_set(self):
        derived = self._derived()
        self.assertTrue(derived, "arena_graces.tsv parsed EMPTY -- every assertion below would be "
                                 "vacuous, which is the 2026-08-10 zero-row emit.")
        back = sorted(f for f in RULED_NOT_AN_ARENA if f in derived)
        self.assertFalse(back, "%s are back in arena_graces.tsv, so gen will WITHHOLD them: %s. "
                               "Re-run tools/datamine_arena_graces.py -- its exclusion tables carry "
                               "the ruling, and a table generated before them reintroduces this."
                         % (back, [RULED_NOT_AN_ARENA[f] for f in back]))

    def test_the_control_is_still_withheld(self):
        """A test that only ever removes things would pass on an empty file."""
        self.assertIn(STILL_WITHHELD, self._derived(),
                      "76313 Windmill Heights is a REAL arena grace (4.0m from the Godskin Apostle) "
                      "and must stay in the derived set -- if it left, the exclusions over-reached.")

    def test_the_five_are_actually_emitted_to_players(self):
        """The point of the ruling: these graces reach the player."""
        src = open(GRACES, encoding="utf-8").read()
        # WITNESS FIRST (test_gf_vacuous_pass). "missing == []" is also what an empty or unparsed
        # region_graces.py says, and I made exactly this mistake in the sibling suite eight hours
        # ago. Prove the corpus is there before asserting nothing is absent from it.
        self.assertIn("REGION_GRACE_POINTS", src)
        self.assertGreater(len(re.findall(r"^\s+'[^']+': \[", src, re.M)), 20,
                           "region_graces.py holds fewer than 20 region bundles -- the assertion "
                           "below would pass vacuously.")
        self.assertTrue(RULED_NOT_AN_ARENA, "the ruled set is empty; nothing is being checked.")
        missing = sorted(f for f in RULED_NOT_AN_ARENA if not re.search(r"\b%d\b" % f, src))
        self.assertFalse(missing, "%s are not in region_graces.REGION_GRACE_POINTS, so no region "
                                  "lock lights them. Three of these are merchant shacks." % missing)


if __name__ == "__main__":
    unittest.main()
