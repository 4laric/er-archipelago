#!/usr/bin/env python3
"""test_datamine_enemy_drops.py -- the two rules in datamine_enemy_drops.py that data cannot state.

Everything else in that tool is a transcription of ItemLotParam_enemy and is gated by its own
`--check` against the committed params. These two are JUDGEMENTS, and a wrong one would be a
committed table asserting something false about the game:

  1. THE LOT GROUP STOPS AT THE NEXT NpcParam BASE. Groups are banded in tens, but 6 real bands are
     narrower than their band and butt straight against the next enemy's base. Walk `base+k` while
     the row merely exists and those 6 enemies inherit the following enemy's drops.
  2. chance_pct IS THE SLOT'S SHARE OF ITS OWN ROW, denominator = the sum of ALL EIGHT base points
     including the empty "nothing" slot -- so a row's emitted chances sum to less than 100.

AP-free and artifact-free: `lot_group` is pure, and the chance arithmetic is exercised on a
synthetic row. Run: python -m unittest -v tools/test_datamine_enemy_drops.py
"""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "_datamine_enemy_drops", os.path.join(HERE, "datamine_enemy_drops.py"))
ed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ed)


class LotGroup(unittest.TestCase):
    def test_forward_run_from_the_base(self):
        lots = {100: 1, 101: 1, 102: 1, 104: 1}
        self.assertEqual(ed.lot_group(100, lots, {100}), [100, 101, 102])

    def test_stops_at_the_next_npc_base(self):
        """The 6-band case. 103 exists AND is another enemy's base -- it is not ours."""
        lots = {100: 1, 101: 1, 102: 1, 103: 1, 104: 1}
        self.assertEqual(ed.lot_group(100, lots, {100, 103}), [100, 101, 102])
        self.assertEqual(ed.lot_group(103, lots, {100, 103}), [103, 104])

    def test_base_is_never_excluded_by_being_a_base(self):
        self.assertEqual(ed.lot_group(100, {100: 1}, {100}), [100])

    def test_missing_base_row_is_an_empty_group(self):
        self.assertEqual(ed.lot_group(100, {101: 1}, {100}), [])


class Chance(unittest.TestCase):
    def _row(self, points):
        row = {"ID": "1"}
        for i, p in enumerate(points, 1):
            row["lotItemBasePoint%02d" % i] = str(p)
        return row

    def test_denominator_includes_the_nothing_slot(self):
        # slot 1 = the "nothing" slot (weight 900), slot 2 = the drop (weight 100).
        row = self._row([900, 100, 0, 0, 0, 0, 0, 0])
        total = sum(ed._int(row, "lotItemBasePoint%02d" % i) for i in range(1, 9))
        self.assertEqual(total, 1000)
        self.assertEqual("%.4f" % (100.0 * ed._int(row, "lotItemBasePoint02") / total), "10.0000")

    def test_blank_and_junk_weights_read_as_zero(self):
        row = {"lotItemBasePoint01": "", "lotItemBasePoint02": "nope"}
        self.assertEqual(ed._int(row, "lotItemBasePoint01"), 0)
        self.assertEqual(ed._int(row, "lotItemBasePoint02"), 0)


class Emitted(unittest.TestCase):
    def test_header_matches_the_column_tuple(self):
        self.assertEqual(ed.HEADER.split("\t"), list(ed.COLUMNS))

    def test_preamble_states_the_polarity(self):
        """The tsv is read by people without the tool; the polarity has to be IN the file."""
        self.assertIn("flag>0 = ONE-TIME", ed.PREAMBLE)
        self.assertIn("FARMABLE", ed.PREAMBLE)
        self.assertIn("No row here is an AP location", ed.PREAMBLE)


class StaleDiff(unittest.TestCase):
    """`--check`'s report has to name the COLUMN: CI's tree is gone by the time anyone reads the log."""

    def _line(self, name):
        return "\t".join(["1", "", "0", "2", "3", "1", "9", "9", name, "1", "1.0000", "", "", ""])

    def test_names_the_column_that_moved(self):
        a = "\n".join([ed.HEADER, self._line("Grave Glovewort [2]")])
        b = "\n".join([ed.HEADER, self._line("")])
        out = ed.stale_diff(a, b)
        self.assertIn("columns that moved: item_name", out)
        self.assertIn("1 differing line(s)", out)
        self.assertIn("line 2:", out)
        self.assertIn("Grave Glovewort [2]", out)

    def test_reports_row_counts_and_missing_lines(self):
        a = "\n".join([ed.HEADER, self._line("x"), self._line("y")])
        b = "\n".join([ed.HEADER, self._line("x")])
        out = ed.stale_diff(a, b)
        self.assertIn("committed: 3 lines / fresh: 2 lines", out)
        self.assertIn("<missing>", out)

    def test_caps_how_much_it_prints(self):
        a = "\n".join([ed.HEADER] + [self._line("a%d" % i) for i in range(50)])
        b = "\n".join([ed.HEADER] + [self._line("b%d" % i) for i in range(50)])
        out = ed.stale_diff(a, b, limit=5)
        self.assertIn("50 differing line(s) (first 5 shown)", out)
        self.assertEqual(out.count("    committed: "), 5)


if __name__ == "__main__":
    unittest.main()
