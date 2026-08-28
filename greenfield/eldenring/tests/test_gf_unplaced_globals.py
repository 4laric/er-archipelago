# -*- coding: utf-8 -*-
"""Issue #249 -- the unplaced common-event rows that were never checks, so their item stayed vanilla.

Reported in game: Thops still dropped the vanilla Academy Glintstone Staff while his Bell Bearing
from the same corpse was randomized. A `region_map.csv` row filed `Global / Common-event
(unplaced)` got no location, `check_lots` never blanked the vanilla lot, and nothing errored.

The general derivation still refuses flags with no single-map evidence.  The first-hand #249 report
is the evidence for the narrow f400361 GLOBAL_RECOVER pin, and the acceptance test below now requires
that motivating case to remain a real Raya Lucaria Academy check.

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
AUDIT = os.path.join(PKG, "unplaced_unique_audit.tsv")
if not os.path.isfile(AUDIT) and _ROOT:
    AUDIT = os.path.join(_ROOT, "greenfield", "unplaced_unique_audit.tsv")

# MEASURED 2026-08-04 on the emit that shipped with this file. A floor, not a target: the table may
# grow when a corpus improves, and must not silently SHRINK (an oracle that quietly stops protecting
# you is the arena-grace lesson, one table over).
# 36 -> 52 (2026-08-07): the de-dup re-key (see test_coverage_gate BASELINE_TOTAL_LOCATIONS)
# unblocked 62 rows the name rule had been discarding; 16 of them had derivable tiles.
# 52 -> 51 (2026-08-07, #451): the ONE sanctioned way this floor may drop -- a row was RETIRED as
# cut content, not lost to a corpus going quiet. FromSoft writes the marker BOTH ways, bare
# '[ERROR]' and '[ERROR]<real name>', and the guard tested only the bare form; goods 8130
# ("[ERROR]Rya's Necklace", sortId 0) therefore read as a NAMED item and f400081 shipped as a live
# check holding a thing that does not exist. It was never a duplicate of f400300 (goods 8136, the
# real necklace, sortId 204050) -- it was never an item at all. Every corpus this emit reads is
# intact and every other row is unchanged: 51 of 51 survive, and the only delta is
#     -400081  m35_00_00_00  talk_esd  Rya's Necklace
# 🛑 This is the shape the docstring above warns about, so the burden is discharged by SAYING WHICH
# ROW and WHY it is not a real placement -- never by moving the number to whatever the emit printed.
# 51 -> 74 (2026-08-19, #218): 22 exact item entities plus the Sacred Tower painting's map-event
# flag+lot call became available as placement evidence. A stricter ESD join also retired three
# false talk-number matches and admitted three actual AwardItemLot sites; the table's net is +23.
MIN_ROWS = 74


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

    def test_issue_218_audit_covers_exactly_the_corrected_30(self):
        expected = {
            400079, 400104, 400105, 400159, 400162, 400173, 400189, 400293,
            400294, 400295, 400361, 400395, 400421, 400451, 400452, 540514,
            580110, 580400, 30207900, 59930000, 1033477020, 1038417100,
            400902, 400903, 400907, 400908, 400909, 400910, 400914, 400915,
        }
        with open(AUDIT, encoding="utf-8") as fh:
            rows = list(csv.DictReader((ln for ln in fh if not ln.startswith("#")), delimiter="\t"))
        self.assertEqual(30, len(rows))
        self.assertEqual(expected, {int(row["flag"]) for row in rows})

    def test_every_audit_acceptance_names_a_generated_check(self):
        locations = _locations()
        by_flag = {f: (region, name) for region, rows in locations.items() for name, _ap, f in rows}
        with open(AUDIT, encoding="utf-8") as fh:
            rows = list(csv.DictReader((ln for ln in fh if not ln.startswith("#")), delimiter="\t"))
        accepted = [row for row in rows if row["verdict"] in ("generated", "duplicate")]
        self.assertTrue(accepted)
        for row in accepted:
            canonical = int(row["canonical_flag"])
            self.assertIn(canonical, by_flag, "%s has no generated canonical check" % row["item"])
            if row["verdict"] == "generated":
                self.assertEqual(int(row["flag"]), canonical)
                self.assertEqual(row["region"], by_flag[canonical][0])

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
        rows = list(_rows())
        # WITNESS (vacuous-pass ratchet): an empty emit greens the bucket check for free.
        self.assertTrue(rows, "the emit produced no rows -- the bucket filter below sees nothing")
        bad = [c for c in rows if c[1] in ("m60_00_00_00", "m61_00_00_00", "m00_00_00_00")]
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
    def test_fixed_coordinate_pickups_are_resolved_without_hand_pins(self):
        """Issue #218's concrete blind spot: these flags have exact item entities, but neither
        their short common flag nor a talk script supplies a map. The production resolver must use
        the coordinate corpus rather than leave them vanilla or grow GLOBAL_RECOVER by hand."""
        out, _refused, _n_talk = _dug().resolve(_dug().candidates()[0])
        by_flag = {int(flag): (map_id, source) for flag, map_id, source, _name in out}
        expected = {
            400902: "m60_45_36", 400903: "m60_41_36",
            400907: "m60_35_45", 400908: "m60_36_49",
            400909: "m60_43_53", 400910: "m60_40_52",
            400915: "m60_48_41", 580400: "m61_45_43",
        }
        for flag, map_id in expected.items():
            got = by_flag.get(flag)
            self.assertIsNotNone(got, "f%d has an exact item coordinate but was not derived" % flag)
            self.assertEqual(map_id, got[0],
                             "f%d derived to the WRONG map: %r" % (flag, got))
            # 2026-08-19 (the full-MSB census): the resolver may now see these rows in the census
            # ("observed") before falling through to the coordinate corpus -- same map either way,
            # and the issue #218 claim under test is "resolved without hand pins", not which
            # sufficient corpus answered first. A THIRD label would still be a surprise.
            self.assertIn(got[1], ("item_coords", "observed"),
                          "f%d derived from an unexpected corpus: %r" % (flag, got))

    @unittest.skipIf(not (_TOOL and os.path.isfile(_TOOL)), REPO_ONLY_REASON)
    def test_map_event_flag_and_lot_pair_resolves_the_sacred_tower_painting(self):
        """The painting has no item entity, but m61_47_42 initializes its award event with BOTH
        f580110 and lot 80110. That pair is placement evidence; either literal alone is not."""
        out, _refused, _n_talk = _dug().resolve(_dug().candidates()[0])
        by_flag = {int(flag): (map_id, source) for flag, map_id, source, _name in out}
        self.assertEqual(("m61_47_42_00", "event_call"), by_flag.get(580110))

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

    def test_the_motivating_thops_staff_is_a_real_check(self):
        """The exact first-hand #249 failure must never return under a green suite."""
        loc = _locations()
        by_flag = {f: (region, name) for region, rows in loc.items() for name, _ap, f in rows}
        self.assertEqual("Raya Lucaria Academy", by_flag.get(400361, (None, None))[0])
        self.assertIn("Academy Glintstone Staff", by_flag[400361][1])

    def test_hand_pinned_unique_quest_awards_are_real_checks(self):
        loc = _locations()
        by_flag = {f: region for region, rows in loc.items() for _name, _ap, f in rows}
        self.assertEqual("Ainsel River", by_flag.get(400159))
        self.assertEqual("Mt. Gelmir", by_flag.get(400440))

    @unittest.skipIf(not (_TOOL and os.path.isfile(_TOOL)), REPO_ONLY_REASON)
    def test_talk_index_uses_awards_not_incidental_flag_reads(self):
        """Lusat awards Stars in m31_11; Sellen merely reads its flag in other talk files."""
        out, _refused, _n_talk = _dug().resolve(_dug().candidates()[0])
        by_flag = {int(flag): (map_id, source) for flag, map_id, source, _name in out}
        self.assertEqual(("m31_11_00_00", "talk_esd"), by_flag.get(400430))
        self.assertNotIn(400440, by_flag, "common overworld talk bucket is not a placement")

    @unittest.skipIf(not (_TOOL and os.path.isfile(_TOOL)), REPO_ONLY_REASON)
    def test_incomplete_117_talk_extract_retains_corroborated_awards(self):
        mod = _dug()
        self.assertEqual(8, len(mod._CORROBORATED_TALK_AWARD_MAP))
        self.assertEqual("m31_11_00_00", mod._CORROBORATED_TALK_AWARD_MAP["400430"])



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
