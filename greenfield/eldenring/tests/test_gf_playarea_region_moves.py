"""#1054's acceptance test: the PlayArea scan's ten ground-placed movers, and the Yelough NO-OP.

THE MOTIVATING CASES.

1. YELOUGH ANIX TUNNEL IS CONSECRATED SNOWFIELD (Alaric's WIKI ruling, 2026-08-26). The #1054
   queue carried 19 Yelough-anchored rows as Mountaintops-vs-Consecrated-Snowfield candidates.
   The PlayArea scan answers `none` for every one of them -- no volume, no seam, no
   PlayRegionParam tile default -- so the instrument CANNOT settle them in either direction, and
   Alaric ruled them from the wiki instead.

   🛑 EVIDENCE CLASS: WIKI RULING. Not scan evidence. Never cite it as scan evidence.

   🛑 AND THE RULING WAS ALREADY SATISFIED IN THE SHIPPED DATA. Grace 73211 files under
   play_region 65002 (grace_region_map.tsv); 65002 is Consecrated Snowfield in
   region_groups.REGION_GROUPS; its measured ground bucket is 32110 (grace_ground.tsv,
   `tile-default`, m60_47_55), which PLAY_REGION_GROUPS also owns for Consecrated Snowfield; 73211
   already sits in the Consecrated Snowfield grace bundle; and every Yelough-labelled check in
   data.py already ships Consecrated Snowfield. The Mountaintops premise came from the STALE
   `our_region` column in check_region_second_opinion.tsv, built before the regen that moved them
   (#1054 records the same staleness for check_region_triage.tsv). A NOTE IS NOT STATE -- so this
   file is where the ruling becomes state, and a regression that flips 73211 back to Mountaintops
   fails a written decision instead of passing silently.

2. THE ELEVEN MOVERS. 679 checks carry an EXACT (`volume:`/`interior-vol:`/`seam:`/`interior-seam:`)
   answer in item_play_regions.tsv; 114 disagree with the region they shipped. Only these eleven are
   BOTH scan-exact AND ground-placed pickups -- the population the instrument rules on. The
   NPC-relocation families in #1054 are deliberately excluded (a shop/grant flag's scanned point
   is where the NPC ENDED UP, not where the check is), and this file pins two of them as NOT
   moved so a future bulk apply trips here.

   Two of the five Rauh movers go the OTHER way from 255's report (#1046). That asymmetry is the
   point: a queue that only ever moved rows in the reported direction would be the instrument
   agreeing with the reporter instead of measuring.
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
IN_REPO = REPO is not None

# flag -> (region it must present as, its item_play_regions.tsv answer)
MOVERS = {
    68630: ("Gravesite", "volume: 6810000"),
    1050567500: ("Mountaintops of the Giants", "volume: 6501000"),
    1050567510: ("Mountaintops of the Giants", "volume: 6501000"),
    1050567520: ("Mountaintops of the Giants", "volume: 6501000"),
    1050567620: ("Mountaintops of the Giants", "volume: 6501000"),
    1051557330: ("Mountaintops of the Giants", "volume: 6501000"),
    2045467050: ("Ancient Ruins", "volume: 69410"),
    2045477020: ("Ancient Ruins", "seam:@2.7m 69400"),
    2046457000: ("Gravesite", "volume: 68100"),
    2045457010: ("Rauh Base", "volume: 69010 (REVERSE)"),
    2046467800: ("Rauh Base", "volume: 69010 (REVERSE)"),
}

# The carve-outs. Each is a row the scan touched that must NOT have moved, and the reason.
STAYERS = {
    # The sixth Ancient Snow Valley Ruins row: answers 65030, which IS Consecrated Snowfield. The
    # tile straddles the Grand Lift of Rold boundary -- that is why the five above are per-flag
    # pins and not a tile pin (#1054 calls this out explicitly as ruled-DISAGREE-confirmed).
    1050567600: "Consecrated Snowfield",
    # Ancient Ruins keeps its own: 2045477010 is the East (2) Shadow Realm Rune, unmoved.
    2045477010: "Rauh Base",
}

YELOUGH_GRACE = 73211
YELOUGH_REGION = "Consecrated Snowfield"
# Every check whose data.py label names Yelough Anix Tunnel and that the #1054 queue listed. All
# already Consecrated Snowfield; pinned so the NO-OP ruling cannot silently become a flip.
YELOUGH_QUEUE_FLAGS = (
    1046577300, 1046577800, 1047567310, 1047567320, 1047567330, 1047577300, 1047577310,
    1048547800, 1048547810, 1048547820, 1048547830, 1048547840, 1048557300, 1048557600,
    1048557900, 1048587300, 1049567350,
)


def _by_flag():
    from .. import data
    out = {}
    for region, rows in data.LOCATIONS.items():
        for (name, ap, flag) in rows:
            out.setdefault(int(flag), []).append((region, name, ap))
    return out


class TheScanMoversLanded(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.by_flag = _by_flag()

    def test_every_mover_presents_as_its_scanned_region(self):
        for flag, (want, answer) in MOVERS.items():
            rows = self.by_flag.get(flag) or []
            self.assertTrue(rows, "f%d is no longer a check" % flag)
            for region, name, ap in rows:
                self.assertEqual(
                    region, want,
                    "#1054: f%d answers %s in item_play_regions.tsv and must present as %s; "
                    "got %s (%s)" % (flag, answer, want, region, name))
                self.assertTrue(
                    name.startswith(want + " ::"),
                    "the location NAME prefix must move with the region: %r" % name)

    def test_the_carve_outs_did_not_move(self):
        """Under-moving is the safe direction; a bulk apply of the #1054 queue trips here."""
        for flag, want in STAYERS.items():
            rows = self.by_flag.get(flag) or []
            self.assertTrue(rows, "f%d is no longer a check" % flag)
            for region, name, ap in rows:
                self.assertEqual(region, want,
                                 "f%d must stay %s; got %s (%s)" % (flag, want, region, name))

    def test_no_ap_id_renumbered(self):
        """A region move re-sorts NAMES; it must never renumber an id (#952, #249)."""
        pinned = {
            68630: 7770146,
            # 2026-08-26 (#1013, Enia vanilla): these ids moved. NOT because the region moves
            # renumbered -- which is exactly what this test forbids and which still holds -- but
            # because Enia's hundred hub rows left the corpus in the SAME window, and removing a
            # check renumbers every later ap id. Each value below was RE-READ from the regenerated
            # data.py by flag; none was derived by subtracting 100 (1050567620 does not follow that
            # arithmetic at all, which is the reason the rule exists).
            1050567500: 7773101, 1050567510: 7773102, 1050567520: 7773103,
            1050567620: 7900270, 1051557330: 7773141, 1050567600: 7773104,
            2045467050: 7773253, 2045477020: 7773263, 2046457000: 7773327,
            2045457010: 7773248, 2046467800: 7773340, 2045477010: 7773262,
        }
        for flag, ap in pinned.items():
            rows = self.by_flag.get(flag) or []
            self.assertIn(ap, [r[2] for r in rows],
                          "f%d lost ap id %d -- the moves renumbered, which they must not"
                          % (flag, ap))


class YeloughAnixIsConsecratedSnowfield(unittest.TestCase):
    """The NO-OP ruling, made into state. See this module's docstring for the evidence class."""

    @classmethod
    def setUpClass(cls):
        cls.by_flag = _by_flag()

    def test_the_queue_rows_all_present_as_consecrated_snowfield(self):
        for flag in YELOUGH_QUEUE_FLAGS:
            rows = self.by_flag.get(flag) or []
            self.assertTrue(rows, "f%d is no longer a check" % flag)
            for region, name, ap in rows:
                self.assertEqual(
                    region, YELOUGH_REGION,
                    "Alaric's 2026-08-26 wiki ruling: Yelough Anix Tunnel is %s. f%d (%s) "
                    "presents as %s." % (YELOUGH_REGION, flag, name, region))

    def test_the_grace_itself_rides_the_snowfield_bundle(self):
        """The checks follow the grace, so the grace is the thing to pin."""
        from .. import region_graces
        self.assertIn(
            YELOUGH_GRACE, region_graces.REGION_GRACE_POINTS[YELOUGH_REGION],
            "grace %d (Yelough Anix Tunnel) must ride the %s bundle"
            % (YELOUGH_GRACE, YELOUGH_REGION))
        for other, pts in region_graces.REGION_GRACE_POINTS.items():
            if other != YELOUGH_REGION:
                self.assertNotIn(YELOUGH_GRACE, pts,
                                 "grace %d must not also ride %s" % (YELOUGH_GRACE, other))

    @unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
    def test_the_ruling_is_recorded_and_labelled_as_a_wiki_ruling(self):
        """region_overrides.tsv is where a ruling that is NOT scan evidence has to say so."""
        path = os.path.join(REPO, "greenfield", "region_overrides.tsv")
        rows = [ln.rstrip("\n").split("\t") for ln in open(path, encoding="utf-8")
                if ln.strip() and not ln.startswith("#")]
        hits = [r for r in rows if len(r) >= 4 and r[1] == str(YELOUGH_GRACE)]
        self.assertEqual(len(hits), 1,
                         "expected exactly one region_overrides row recording the Yelough ruling")
        self.assertEqual(hits[0][2], YELOUGH_REGION)
        self.assertIn("WIKI RULING", hits[0][3].upper(),
                      "the row must name its evidence class -- it is NOT scan evidence")

    @unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
    def test_the_movers_are_excused_to_the_independent_oracle(self):
        path = os.path.join(REPO, "greenfield", "region_overrides.tsv")
        rows = [ln.rstrip("\n").split("\t") for ln in open(path, encoding="utf-8")
                if ln.strip() and not ln.startswith("#")]
        by_key = {r[1]: r for r in rows if len(r) >= 4 and r[0] == "flag"}
        for flag, (want, _answer) in MOVERS.items():
            row = by_key.get(str(flag))
            self.assertIsNotNone(row, "f%d moved with no reasoned region_overrides row" % flag)
            self.assertEqual(row[2], want)
            self.assertIn("1054", row[3], "the row must cite the ruling that made it")


if __name__ == "__main__":
    unittest.main()
