# -*- coding: utf-8 -*-
"""Issue #249 -- the unplaced common-event rows that were never checks, so their item stayed vanilla.

Reported in game: Thops still drops the vanilla Academy Glintstone Staff while his Bell Bearing from
the same corpse is randomized. A `region_map.csv` row filed `Global / Common-event (unplaced)` gets
no location, `check_lots` never blanks the vanilla lot, and nothing errors -- the item is simply not
a check.

🛑 READ THIS BEFORE CLOSING #249. The derivation added here does NOT reach f400361. Its lots
103601/113601 are named by no talk ESD and no map EMEVD, so it sits in the 45-strong "no evidence in
any corpus" bucket. CONTRIBUTING rule 11 says the case that motivated the work is the acceptance
test; where that case CANNOT be fixed, the test says so by name, so nobody reads a green suite as
"the reported bug is gone". That is what test_the_motivating_case_is_still_unreached does.

Run: python3 eldenring/tests/test_gf_unplaced_globals.py
"""
import ast
import collections
import csv
import os
import re
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)
PKG = os.path.dirname(HERE)
TABLE = os.path.join(PKG, "unplaced_global_tiles.tsv")
if not os.path.isfile(TABLE) and _ROOT:
    TABLE = os.path.join(_ROOT, "greenfield", "unplaced_global_tiles.tsv")
DATA = os.path.join(PKG, "data.py")

# MEASURED 2026-08-04 on the emit that shipped with this file. A floor, not a target: the table may
# grow when a corpus improves, and must not silently SHRINK (an oracle that quietly stops protecting
# you is the arena-grace lesson, one table over).
MIN_ROWS = 36


def _rows():
    out = []
    for ln in open(TABLE, encoding="utf-8"):
        if ln.startswith("#") or not ln.strip() or ln.startswith("flag\t"):
            continue
        c = ln.rstrip("\n").split("\t")
        if c and c[0].isdigit():
            out.append(c)
    return out


_TOOL = os.path.join(_ROOT, "tools", "datamine_unplaced_globals.py") if _ROOT else None


def _dug():
    """The PRODUCTION tool module, loaded by path.

    🛑 Deliberately NOT a local re-implementation of `_flag_lots`. A test that builds its own copy
    of the mechanism it is checking cannot catch a change to the real one -- re-key the de-dup back
    onto item names and a private helper here would sail straight through."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_dug_under_test", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _locations():
    txt = open(DATA, encoding="utf-8").read()
    m = re.search(r"^LOCATIONS\s*=\s*(\{.*?\n\})", txt, re.S | re.M)
    return ast.literal_eval(m.group(1))


@unittest.skipIf(not os.path.isfile(TABLE), "unplaced_global_tiles.tsv not beside the package")
class UnplacedGlobals(unittest.TestCase):

    def test_the_table_is_populated(self):
        """Rule 2: an empty table is a failure, not a clean run. If the emit ever produces nothing,
        every one of these checks silently reverts to dropping its vanilla item."""
        rows = _rows()
        self.assertGreaterEqual(len(rows), MIN_ROWS,
                                "unplaced_global_tiles.tsv has %d rows, below the %d measured on "
                                "2026-08-04. A SHRINKING derivation must be explained, not "
                                "rebaselined -- did a corpus go missing?" % (len(rows), MIN_ROWS))

    def test_no_common_bucket_is_treated_as_a_place(self):
        """`m60_00_00_00` / `m61_00_00_00` / `m00_00_00_00` are where the talk ESD files an award
        that fires anywhere in that world. They exist in NO other corpus -- zero rows in
        check_maps.tsv, zero in msb_flag_region.tsv, absent from map_names.tsv. Tile (00,00) is not
        a tile.

        Before this filter the emit placed EIGHT checks at "m60_00_00_00", which reads exactly like
        a map id and is not one, and the row count looked like a bigger win (43 vs 37)."""
        bad = [c for c in _rows() if c[1] in ("m60_00_00_00", "m61_00_00_00", "m00_00_00_00")]
        self.assertEqual([], bad, "common ESD buckets placed as if they were locations: %s" % bad[:5])

    @unittest.skipIf(not (_TOOL and os.path.isfile(_TOOL)), REPO_ONLY_REASON)
    def test_no_placed_flag_re_awards_an_existing_check_s_LOT(self):
        """The DOUBLE-COUNT filter, keyed structurally. Two flags are the same in-game pickup iff
        they share an ItemLotParam row; two flags on different lots are separately collectable.

        This replaced a filter keyed on the ITEM NAME (2026-08-07). That rule dropped 62 rows on the
        grounds that placing them "would double-count a single in-game pickup" -- but 61 of the 62
        were on lots DISTINCT from every name-twin and none shared one, so it was discarding real
        checks wherever two sites award the same common item."""
        loc = _locations()
        lot_of = _dug()._flag_lots()
        placed = {c[0] for c in _rows()}
        claimed = {}
        for _r, v in loc.items():
            for (_nm, _a, fl) in v:
                if str(fl) in placed:
                    continue
                for key in lot_of.get(str(fl), ()):
                    claimed[key] = fl
        dupes = []
        for c in _rows():
            for key in lot_of.get(c[0], ()):
                if key in claimed:
                    dupes.append((c[0], key, claimed[key]))
        self.assertEqual([], dupes,
                         "these placed flags re-award an ItemLotParam row that ALREADY backs a "
                         "check, so the world now has two locations for ONE pickup: %s" % dupes[:5])

    @unittest.skipIf(not (_TOOL and os.path.isfile(_TOOL)), REPO_ONLY_REASON)
    def test_the_marika_pair_is_two_pickups_not_one(self):
        """MOTIVATING CASE (rule 11) for the key change -- boblerrr, 2026-08-07, client 0.3.7.

        `Blessing of Marika` is awarded by lot 30935 (flag 530935) and lot 30950 (flag 530950). The
        old name-keyed filter called them one pickup and dropped 530935. In game he collected BOTH
        on one character (`!flag` reads true for each): 530950 sent a check, 530935 handed over the
        vanilla item and sent nothing.

        The assertion is on the DATA, not on the tool's output, so it keeps holding after 530935 is
        placed: these two flags must never be judged the same award."""
        lot_of = _dug()._flag_lots()
        a, b = lot_of.get("530935", set()), lot_of.get("530950", set())
        self.assertTrue(a and b, "flag_lots.tsv lost the Blessing of Marika rows (530935/530950)")
        self.assertEqual(set(), a & b,
                         "530935 and 530950 now share a lot -- if that is real, the name rule was "
                         "right about this pair and the motivating case needs re-deriving; got "
                         "%s vs %s" % (sorted(a), sorted(b)))

    def test_every_placed_flag_became_a_real_check(self):
        """Producer coverage and consumer coverage are different numbers (rule 11). The table having
        a row proves nothing about the world having a location."""
        loc = _locations()
        in_world = {f for _r, v in loc.items() for (_n, _a, f) in v}
        missing = sorted(int(c[0]) for c in _rows() if int(c[0]) not in in_world)
        self.assertEqual([], missing,
                         "%d flag(s) carry a derived tile but produced NO location -- the table is "
                         "being written and dropped by its own consumer: %s"
                         % (len(missing), missing[:8]))

    @unittest.skipIf(not (_TOOL and os.path.isfile(_TOOL)), REPO_ONLY_REASON)
    def test_the_name_twin_survives_the_dedup(self):
        """THE ACCEPTANCE TEST for the 2026-08-07 key change -- it asks PRODUCTION for its verdict.

        The two tests above check DATA (lots differ) and OUTPUT (nothing placed re-awards a claimed
        lot); neither would notice the de-dup being re-keyed onto `item_name`, because the committed
        table would not move until the next emit. This one calls `candidates()` and fails the moment
        530935 is judged a duplicate of its name-twin again."""
        out, _tally = _dug().candidates()
        flags = {r["flag"] for r in out}
        self.assertIn("530935", flags,
                      "f530935 (Blessing of Marika) is being dropped as a duplicate again -- the "
                      "de-dup has been re-keyed onto the item name. It shares NO lot with f530950 "
                      "and boblerrr collected both in one session (2026-08-07).")

    def test_the_motivating_case_is_still_unreached(self):
        """🛑 THE HONEST ONE. f400361 (Thops's Academy Glintstone Staff) is what #249 is about, and
        this derivation does NOT fix it -- no corpus we have names its lots. Rule 11's corollary: if
        the exemplar cannot be a fixture, say in the test how you would know it was still covered.

        This assertion is INVERTED on purpose. It fails the day f400361 finally gets placed -- and
        that failure is the signal to close #249 and delete this test, not to widen anything."""
        placed = {int(c[0]) for c in _rows()}
        self.assertNotIn(400361, placed,
                         "f400361 (Thops) is now placed -- #249's reported bug is FIXED. Verify in "
                         "game that the staff is randomized, close #249, and remove this test.")
        loc = _locations()
        in_world = {f for _r, v in loc.items() for (_n, _a, f) in v}
        self.assertNotIn(400361, in_world,
                         "f400361 became a check by some OTHER route -- good, but this test is now "
                         "lying about the state of #249. Re-verify and retire it.")



    def test_the_emit_is_idempotent_against_a_placed_world(self):
        """🛑 THE ONE THAT NEARLY SHIPPED A SELF-ERASING GENERATOR.

        This tool reads data.py to decide which rows are "not a check yet". After an emit + regen,
        the flags it placed ARE checks -- so on the second run they look like "already a check" by
        flag AND like "that item is already a check under another flag" by name (their own). The
        second --emit resolved `0 of 64` and tried to write a 0-row table, which would have reverted
        every one of these checks to dropping its vanilla item, silently, on the next routine regen.

        The tool now subtracts its own previous output from both filters. This asserts the property
        rather than the fix: re-running the emit against a world that already contains its
        placements must reproduce the same table."""
        import subprocess
        if not _ROOT:
            self.skipTest(REPO_ONLY_REASON)
        tool = os.path.join(_ROOT, "tools", "datamine_unplaced_globals.py")
        if not os.path.isfile(tool):
            self.skipTest("tools/ not beside the package")
        before = open(TABLE, encoding="utf-8").read()
        r = subprocess.run(["python3", tool], cwd=_ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(0, r.returncode, r.stdout[-800:] + r.stderr[-400:])
        # report-only run must not have touched it, and must still SEE the same population
        self.assertEqual(before, open(TABLE, encoding="utf-8").read(),
                         "a report-only run modified the table")
        m = re.search(r"resolved (\d+) of (\d+) candidate", r.stdout)
        self.assertIsNotNone(m, "the tool stopped reporting its resolve counts:\n" + r.stdout[-600:])
        self.assertEqual(len(_rows()), int(m.group(1)),
                         "re-running against the CURRENT (already placed) world resolves %s rows but "
                         "the committed table has %d -- the emit is not idempotent and the next "
                         "routine regen would rewrite it:\n%s"
                         % (m.group(1), len(_rows()), r.stdout[-800:]))

if __name__ == "__main__":
    unittest.main(verbosity=2)
