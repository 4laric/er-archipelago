"""255's notebook, 2026-09-08: the ten region movers and the eleven rows that did NOT move.

THE RULING THIS FILE MAKES INTO STATE (#1514, #1509, #1511).

255 reported twenty-one checks as "should be region X, not Y". Each was re-derived through the
ladder in docs/MATT-ORACLE-ROADMAP.md item 4 -- the PlayArea point-in-volume scan first
(greenfield/item_play_regions.tsv, docs/PLAYAREA-ITEM-SCAN.md), then the nearest-grace join
(greenfield/nearest_grace.tsv, #1074), and only where NEITHER can speak, whatever first-hand
corpus evidence exists for that flag. Ten moved. Eleven did not, and eleven is the number that
matters: for five of them the instrument answered and CONTRADICTED the reporter, three have no
instrument at all, and three are governed by a standing human ruling the instrument does not
outrank. A queue that moved every reported row would be agreeing with the reporter rather than
measuring, which is the failure #1054 named when two of its Rauh rows moved the other way.

🛑 EVIDENCE CLASSES ARE NOT INTERCHANGEABLE and this file pins which one each mover used:

  scan-exact       the pickup stands INSIDE a named PlayArea volume. Outranks everything below.
                   2051477500, 2051477510 (volume 69300 = Shadow Keep).
  grace-calibrated the scan is silent, and the nearest-grace join is corroborated by scan-exact
                   rows sharing that grace ON THE SAME TILE. 1051557310/320, 580330 (grace 76503,
                   calibrated 5/5 against volume 65010); 2048417800 (76811, four same-tile rows);
                   2052417000 (76864, its on-tile twin 2052417010 scans volume 68600).
  grace-only       the nearest-grace join with no same-tile scan corroboration. 2049427010 alone.
  esd              no coordinates exist; the award SITE in the ESD corpus is the evidence. 400221.
  lot-decode       no coordinates and no ESD; the flag's own map lot id decodes to a tile. 1049557700.

THE SWEEP CONSEQUENCE, pinned here because it is part of the same ruling. Moving three checks off
the Ancient Snow Valley Ruins tiles tipped Great Wyrm Theodorix's neighbourhood vote to
Mountaintops, which the #1059 containment invariant correctly refused. Two independent
measurements say the boss is on the Snowfield side -- boss_arena_rulings.tsv and its own drop
f530550 -- so gen_data._FIELD_SWEEP_REGION_CURATED pins the BOSS, not the tile, exactly as it
already does for the Snowfield Putrid Avatar one seam over.
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

# flag -> (region it must present as, evidence class, the instrument's answer in words)
MOVERS = {
    2051477500: ("Shadow Keep", "scan-exact", "volume 69300 on m61_51_47"),
    2051477510: ("Shadow Keep", "scan-exact", "volume 69300 on m61_51_47"),
    1051557310: ("Mountaintops of the Giants", "grace-calibrated", "nearest grace 76503 -> 65000"),
    1051557320: ("Mountaintops of the Giants", "grace-calibrated", "nearest grace 76503 -> 65000"),
    580330: ("Mountaintops of the Giants", "grace-calibrated", "nearest grace 76503 -> 65000"),
    2048417800: ("Gravesite", "grace-calibrated", "nearest grace 76811 -> 6800"),
    2052417000: ("Abyssal", "grace-calibrated", "nearest grace 76864 -> 6860"),
    2049427010: ("Abyssal", "grace-only", "nearest grace 76861 -> 6860"),
    400221: ("Limgrave", "esd", "t321006000_x3 awards lot 102200 in the m60_00 container"),
    1049557700: ("Consecrated Snowfield", "lot-decode", "map lot 1049550700 -> tile m60_49_55"),
}

# The rows 255 reported that did NOT move, and why. Under-moving is the safe direction: a future
# bulk apply of the notebook trips here rather than shipping the reporter's opinion as data.
STAYERS = {
    # The instrument answered and DISAGREED with the reporter.
    2047457000: ("Scadu Altus", "nearest grace 76907 -> 6900, calibrated 7/7 on m61_47_45"),
    2047457010: ("Scadu Altus", "nearest grace 76907 -> 6900, calibrated 7/7 on m61_47_45"),
    2051467020: ("Scadu Altus", "scan-exact volume 69020, NOT the 69300 of its two neighbours"),
    1050567700: ("Consecrated Snowfield", "nearest grace 73019 -> 65002, calibrated by 1050567600"),
    400220: ("Stormveil", "of three MSB placements only m10_00 resolves, to 10000 = Stormveil"),
    # No instrument can speak at all.
    2047407980: ("Cerulean", "no scan row, no coordinates, no nearest grace"),
    65460: ("Gravesite", "furnace-golem drop; no c4900 placements exist in the bundle"),
    # A standing human ruling the instrument does not outrank.
    21007670: ("Scadu Altus", "#885 Hippo: m21_00 is curated Scadu Altus at MAP scope"),
    2048417980: ("Jagged Peak", "no coordinates; only boss_verdict_tiles.tsv m61_48_41 speaks"),
    2049427700: ("Jagged Peak", "no coordinates; only boss_verdict_tiles.tsv m61_49_42 speaks"),
    2049427720: ("Jagged Peak", "no coordinates; only boss_verdict_tiles.tsv m61_49_42 speaks"),
}

# A region move re-sorts NAMES; it must never renumber an id (#952, #249). Read back from the
# regenerated data.py by flag, never derived by arithmetic.
PINNED_AP_IDS = {
    # Re-read by FLAG from the regenerated data.py after #1526 removed 10 rows, which shifted
    # every positional id from 7770795 on. Nothing here moved region as a result.
    2051477500: 7773641, 2051477510: 7773642, 1051557310: 7773137, 1051557320: 7773138,
    580330: 7770803, 2048417800: 7773474, 2049427010: 7774549, 2052417000: 7773644,
    400221: 7773715, 1049557700: 7774470,
}

THEODORIX_TRIGGER = 1050560800
THEODORIX_REGION = "Consecrated Snowfield"


def _by_flag():
    from ..tables import data
    out = {}
    for region, rows in data.LOCATIONS.items():
        for (name, ap, flag) in rows:
            out.setdefault(int(flag), []).append((region, name, ap))
    return out


class TheMoversLanded(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.by_flag = _by_flag()

    def test_every_mover_presents_as_its_derived_region(self):
        for flag, (want, klass, answer) in MOVERS.items():
            rows = self.by_flag.get(flag) or []
            self.assertTrue(rows, "f%d is no longer a check" % flag)
            for region, name, _ap in rows:
                self.assertEqual(
                    region, want,
                    "255's notebook: f%d was moved on %s evidence (%s) and must present as %s; "
                    "got %s (%s)" % (flag, klass, answer, want, region, name))
                self.assertTrue(
                    name.startswith(want + " ::"),
                    "the location NAME prefix must move with the region: %r" % name)

    def test_no_ap_id_renumbered(self):
        for flag, ap in PINNED_AP_IDS.items():
            rows = self.by_flag.get(flag) or []
            self.assertIn(ap, [r[2] for r in rows],
                          "f%d lost ap id %d -- the moves renumbered, which they must not"
                          % (flag, ap))

    def test_400221_no_longer_names_a_stormveil_landmark(self):
        """A region move that leaves the old region's landmark in the name is worse than neither
        half alone. f400221 went Stormveil -> Limgrave, so 'Castleward Tunnel' had to go with it
        (greenfield/location_descriptions.tsv, layer 1)."""
        rows = self.by_flag.get(400221) or []
        self.assertTrue(rows, "f400221 is no longer a check")
        for _region, name, _ap in rows:
            self.assertNotIn("Castleward Tunnel", name,
                             "f400221 is a Limgrave row and must not name a Stormveil grace: %r"
                             % name)
            self.assertIn("Kenneth Haight", name)

    def test_the_larval_tear_keeps_its_progression_bar(self):
        """f1049557700 left the HUB on the weakest rung of the ladder -- a lot-id decode, with no
        coordinates for either instrument to read and nobody having stood in front of it. In the
        HUB it was already barred; the re-pin must settle where it is FILED and nothing else, so
        gen_data._REGION_OVERRIDE_UNCONFIRMED_FLAGS carries it and the hedge survives the move.
        Same shape as f400220 (#445, 2026-08-26)."""
        rows = self.by_flag.get(1049557700) or []
        self.assertTrue(rows, "f1049557700 is no longer a check")
        for _region, name, _ap in rows:
            self.assertIn(
                "(region unconfirmed)", name,
                "f1049557700 must keep its DEFAULTED bar across the HUB -> Consecrated Snowfield "
                "re-pin; a region move must not silently promote an unwitnessed progression host: "
                "%r" % name)


class TheStayersDidNotMove(unittest.TestCase):
    """Eleven reported rows the evidence did not support. This is the half that proves the batch
    measured rather than agreed."""

    @classmethod
    def setUpClass(cls):
        cls.by_flag = _by_flag()

    def test_each_stayer_keeps_its_region(self):
        for flag, (want, why) in STAYERS.items():
            rows = self.by_flag.get(flag) or []
            self.assertTrue(rows, "f%d is no longer a check" % flag)
            for region, name, _ap in rows:
                self.assertEqual(region, want,
                                 "f%d must stay %s (%s); got %s (%s)"
                                 % (flag, want, why, region, name))


class TheTheodorixContainmentPin(unittest.TestCase):
    """#1059: a sweep's members must live in the region the boss is fought in."""

    def test_theodorix_sweeps_the_snowfield_and_only_the_snowfield(self):
        from ..tables import boss_sweeps, data
        self.assertIn(THEODORIX_TRIGGER, boss_sweeps.SWEEP_REGION,
                      "trigger %d is no longer a live sweep" % THEODORIX_TRIGGER)
        self.assertEqual(
            boss_sweeps.SWEEP_REGION[THEODORIX_TRIGGER], THEODORIX_REGION,
            "Great Wyrm Theodorix's arena is %s in boss_arena_rulings.tsv and its own drop f530550 "
            "is a %s check; the sweep region must agree with both."
            % (THEODORIX_REGION, THEODORIX_REGION))
        region_of = {}
        for region, rows in data.LOCATIONS.items():
            for (_name, _ap, flag) in rows:
                region_of[int(flag)] = region
        for member in boss_sweeps.DUNGEON_SWEEPS.get(THEODORIX_TRIGGER, ()):
            got = region_of.get(int(member))
            if got is None:
                continue
            self.assertEqual(got, THEODORIX_REGION,
                             "#1059 containment: f%s is swept by Theodorix but ships %s"
                             % (member, got))

    def test_the_moved_snowfield_rows_left_the_theodorix_sweep(self):
        """The three movers are the reason the pin exists; they must be out of its member list."""
        from ..tables import boss_sweeps
        members = {int(m) for m in boss_sweeps.DUNGEON_SWEEPS.get(THEODORIX_TRIGGER, ())}
        for flag in (1051557310, 1051557320, 580330):
            self.assertNotIn(flag, members,
                             "f%d is Mountaintops now and must not be swept by a Snowfield boss"
                             % flag)


@unittest.skipUnless(IN_REPO, REPO_ONLY_REASON)
class TheRulingIsRecordedForTheIndependentOracle(unittest.TestCase):
    """region_overrides.tsv is the file the matt oracle reads. A move with no reasoned row there
    is the failure mode that file exists for -- and so is a NO-OP with no written decision, which
    is why the stayers are recorded too."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(REPO, "greenfield", "region_overrides.tsv")
        rows = [ln.rstrip("\n").split("\t") for ln in open(path, encoding="utf-8")
                if ln.strip() and not ln.startswith("#")]
        cls.by_key = {}
        for r in rows:
            if len(r) >= 4 and r[0] == "flag":
                cls.by_key.setdefault(r[1], []).append(r)

    def test_one_row_per_flag(self):
        # The witness, tied to the scan (test_gf_vacuous_pass): an empty `dupes` means nothing
        # unless by_key actually holds the rows this batch wrote.
        self.assertGreaterEqual(
            len(self.by_key), len(MOVERS) + len(STAYERS),
            "region_overrides.tsv parsed only %d flag rows -- fewer than this batch alone wrote, "
            "so the duplicate scan below is looking at nothing" % len(self.by_key))
        dupes = sorted(k for k, v in self.by_key.items() if len(v) > 1)
        self.assertEqual(dupes, [],
                         "region_overrides.tsv must carry at most one active ruling per flag; "
                         "tools/build_v060_current_evidence.py hard-fails on a duplicate: %r"
                         % dupes)

    def test_every_mover_is_excused_with_its_issue(self):
        for flag, (want, _klass, _answer) in MOVERS.items():
            rows = self.by_key.get(str(flag))
            self.assertIsNotNone(rows, "f%d moved with no reasoned region_overrides row" % flag)
            self.assertEqual(rows[0][2], want)
            self.assertTrue(
                any(n in rows[0][3] for n in ("1514", "1509", "1511")),
                "f%d's row must cite the issue that made it" % flag)

    def test_every_stayer_records_why_it_did_not_move(self):
        for flag, (want, _why) in STAYERS.items():
            rows = self.by_key.get(str(flag))
            self.assertIsNotNone(rows, "f%d was reported and left; that decision must be written "
                                       "down, or the next reader re-litigates it" % flag)
            self.assertEqual(rows[0][2], want)
            self.assertTrue(
                any(n in rows[0][3] for n in ("1514", "1509", "1511")),
                "f%d's row must cite the report it answers" % flag)

    def test_the_movers_name_their_evidence_class(self):
        """'scan-exact' and 'the nearest-grace heuristic agreed' are different claims, and #1054's
        rows already carry the distinction. Keep it legible."""
        for flag, (_want, klass, _answer) in MOVERS.items():
            reason = self.by_key[str(flag)][0][3].upper()
            self.assertIn("EVIDENCE CLASS", reason,
                          "f%d's row must name its evidence class explicitly" % flag)
            if klass == "scan-exact":
                self.assertIn("SCAN-EXACT", reason)
            elif klass in ("grace-calibrated", "grace-only"):
                self.assertIn("NEAREST-GRACE", reason)
                self.assertNotIn("SCAN-EXACT, GROUND-PLACED", reason,
                                 "f%d is not scan-exact and must not be labelled as if it were"
                                 % flag)


if __name__ == "__main__":
    unittest.main()
