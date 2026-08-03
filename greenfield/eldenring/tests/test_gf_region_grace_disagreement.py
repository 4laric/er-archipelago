"""REGION-vs-GRACE screen: rank the overworld tiles whose checks are named after another region.

A site of grace sits in ONE region, and `grace_flags.tsv` reads that region straight off
BonfireWarpParam. So when a check's own NEAREST grace belongs to region A and the check is filed
under region B, one of the two derivations is wrong. This ranks the m60 tiles by how many of their
checks say that, and pins the total as a ratchet.

WHY THIS IS NOT test_gf_grace_straddle.py, which already exists and which I checked first.
That screen compares a grace's checks TO EACH OTHER: if they split across regions, the minority is
suspect. It is deliberately built to need no play_region -> region table. Two consequences:

  * a UNANIMOUS miss is structurally invisible to it -- no minority, no signal. MEASURED: of the
    graces this screen flags, six are unanimous, e.g. grace 73020 whose eight checks all sit in one
    region that is not the grace's.
  * where it does fire, its minority-vote framing can point the WRONG WAY. Fort Gael North split
    9 Limgrave / 1 Caelid, so the minority was the single check that was RIGHT. The screen said
    "straddle" and the ratchet said "51 graces"; nothing said "look at this one".

This screen reads the grace's own region instead of voting, so it catches both cases and names the
direction. The two are complementary; neither replaces the other.

DOES IT WORK? Re-measured on e076cee -- main immediately BEFORE the two tile curations, with both
mistakes still in the data. Eleven tiles disagreed, and the two that a human had to find by standing
on them ranked FIRST and SECOND:

    m60_45_39   12/12   Caelid   -> Limgrave      (Summonwater; #339)
    m60_47_38   12/15   Limgrave -> Caelid        (Fort Gael;   #340)

Both were reported by players -- boblerrr got no loot from the Tibia Mariner, and Alaric answered a
confirmation form with two different regions for one tile. Neither needed to be. The signal was
derivable from committed data the whole time.

🛑 THIS IS A SCREEN, NOT A SOURCE. `GRACE_PLAY_REGION` is deliberately NOT wired into regioning
(gen_data: "that would make the straddle screen circular"), and nothing here changes that. A row on
this list is a QUESTION -- "which of these two derivations is wrong?" -- not a verdict.

🛑 A DISAGREEMENT CAN BE THE GRACE'S FAULT. `nearest_grace` is itself a nearest-neighbour join, so a
check can anchor to a grace that is not really its landmark. That is not hypothetical: the straddle
screen's largest entry was once twelve checks 8.7-10.4 km from the grace they had anchored to. When
a row here looks geographically impossible, suspect the GRACE first.

🛑 A ROW IS NOT AUTOMATICALLY A BUG. The Altus/Mt. Gelmir seam at the top of the current list is a
grace-join fold `region_groups.py` has already looked at and declined to "correct". Driving this
number down means adjudicating rows, not silencing them -- and an exemption list would be exactly
the quarantine-to-go-green move the straddle screen's docstring warns about.

Run:  python greenfield/eldenring/tests/test_gf_region_grace_disagreement.py
"""
import csv
import importlib.util
import os
import unittest
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)
GREENFIELD = os.path.dirname(GF_PKG)

# MEASURED on the branch that curated both tiles. A RATCHET: it may only ever go DOWN. Raising it
# means a region derivation moved and someone must say WHY, in this docstring, before re-pinning.
PIN_TILES = 7
PIN_CHECKS = 24
# A SHARE as well as a count, for the reason test_gf_grace_straddle.py gives: locating MORE checks
# must not be able to move a gate that is supposed to measure a DERIVATION. Only a derivation can.
PIN_SHARE = 0.024


def _mod(name):
    path = os.path.join(GF_PKG, name + ".py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("_gf_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find(fname):
    for base in (GF_PKG, GREENFIELD):
        p = os.path.join(base, fname)
        if os.path.isfile(p):
            return p
    return None


class RegionGraceDisagreement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data, graces = _mod("data"), _mod("region_graces")
        if not (data and graces):
            raise unittest.SkipTest("data/region_graces not generated")
        ng = _find("nearest_grace.tsv")
        if not ng:
            raise unittest.SkipTest(
                "nearest_grace.tsv not found beside the package or in greenfield/ -- this screen "
                "cannot run blind, so it skips loudly rather than reporting zero disagreements")
        # grace flag -> region, straight off grace_flags.tsv via the generated table.
        cls.grace_region = {int(g): r for r, gs in graces.REGION_GRACE_POINTS.items() for g in gs}
        cls.flag_region = {int(f): r for r, ls in data.LOCATIONS.items() for (_n, _ap, f) in ls}
        cls.check_grace = {}
        with open(ng, encoding="utf-8-sig") as fh:
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 3 and p[0].strip().lstrip("-").isdigit() and p[2].strip():
                    cls.check_grace[int(p[0])] = int(p[2].strip())

    @staticmethod
    def _tile(flag):
        s = str(flag)
        return "m60_%s_%s" % (s[2:4], s[4:6]) if len(s) == 10 and s.startswith("10") else None

    def _rows(self):
        bad, total = defaultdict(list), Counter()
        for flag, region in self.flag_region.items():
            tile = self._tile(flag)
            if tile:
                total[tile] += 1
            g = self.check_grace.get(flag)
            gr = self.grace_region.get(g) if g else None
            if tile and gr and gr != region:
                bad[tile].append((flag, region, gr))
        return bad, total

    def test_worklist_is_a_ratchet(self):
        bad, total = self._rows()
        checks = sum(len(v) for v in bad.values())
        report = []
        for tile, rows in sorted(bad.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            (a, b), _ = Counter((r, gr) for _f, r, gr in rows).most_common(1)[0]
            report.append("  %-12s %2d/%-3d  %s -> %s" % (tile, len(rows), total[tile], a, b))
        msg = ("region/grace disagreement is %d tile(s) / %d check(s), pinned at %d/%d.\n"
               "A RATCHET -- it may only go DOWN. If it GREW, a region derivation moved and the "
               "reason belongs in this file's docstring before the pin changes. If it SHRANK, "
               "lower the pin in the same commit that earned it -- this asserts <= only, "
               "so an improvement passes silently and it is on you to tighten it.\nCurrent worklist:\n%s"
               % (len(bad), checks, PIN_TILES, PIN_CHECKS, "\n".join(report)))
        self.assertLessEqual(len(bad), PIN_TILES, msg)
        self.assertLessEqual(checks, PIN_CHECKS, msg)
        graced = sum(1 for f in self.flag_region if self._tile(f) and f in self.check_grace)
        share = checks / graced if graced else 0.0
        self.assertLessEqual(share, PIN_SHARE,
                             "disagreement SHARE is %.4f of %d graced overworld check(s), pinned at "
                             "%.4f. The share is the assertion that means something: locating more "
                             "checks cannot move it, only a derivation can.\n%s"
                             % (share, graced, PIN_SHARE, msg))

    def test_the_two_curated_tiles_are_clean(self):
        """The motivating cases. Both were #1 and #2 on this list before they were curated; if
        either comes back the curation regressed and this screen must say so by name."""
        bad, _ = self._rows()
        for tile in ("m60_45_39", "m60_47_38"):
            self.assertNotIn(tile, bad, tile + " disagrees with its own graces again -- the "
                             "M60_TILE_CURATED entry for it regressed (#339 / #340)")

    def test_screen_can_see_a_unanimous_miss(self):
        """The property that makes this complementary to the straddle screen rather than a copy.

        A grace whose checks ALL sit in one wrong region has no minority, so a vote among them
        cannot flag it. Assert this screen can, by constructing that exact shape directly --
        the corpus may not contain one on any given day, and a guard the corpus never fires is
        untested (CONTRIBUTING)."""
        self.grace_region = {900: "Caelid"}
        self.flag_region = {1047387000 + i: "Limgrave" for i in range(4)}
        self.check_grace = {f: 900 for f in self.flag_region}
        bad, _ = self._rows()
        self.assertEqual(sorted(bad), ["m60_47_38"])
        self.assertEqual(len(bad["m60_47_38"]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
