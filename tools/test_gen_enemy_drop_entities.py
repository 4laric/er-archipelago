#!/usr/bin/env python3
"""The XML pairing contract of tools/gen_enemy_drop_entities.py (#1000).

WHY THIS EXISTS (review of PR #1004). The tool's only load-bearing assumption about its external,
local-only input is that WitchyBND unpacks `Part/Enemy` as ONE PART PER FILE -- it takes the FIRST
`<NPCParamID>` and the FIRST `<EntityID>` in each file and calls them one record. Two ways that can
be wrong, and before this both were INVISIBLE:

  * two parts in one file -> the first NPC id pairs with the first entity id and you get a wrong
    row that looks exactly like a right one;
  * a single-`Part.xml` (or un-unpacked) layout -> nothing resolves, and the tool reported that as
    "82/147 partial", indistinguishable from the 65 checks that genuinely need more datamining.

The MSBs themselves cannot be committed (copyright, and gen_inputs.db carries zero mapstudio files),
so the fixture under tools/testdata/enemy_drop_msb/ is a minimal hand-written excerpt of the shape:
the two joined fields plus enough surrounding structure to be recognisable. That is enough to pin
the pairing, which is the part that can silently rot.

Also pinned here: the read-only/missing-database refusal, the overworld flag-decode refusal, the
one-to-many check_maps contract, and the emitted row bytes.

Run: python -m unittest -v tools/test_gen_enemy_drop_entities.py
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_enemy_drop_entities as G  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testdata', 'enemy_drop_msb')


def enemy_dir(kind):
    return os.path.join(FIX, kind, 'm10_00_00_00-msb-dcx', 'Part', 'Enemy')


class TestXmlPairing(unittest.TestCase):
    def test_one_part_per_file_pairs_within_the_record(self):
        m = G.index_enemy_parts(enemy_dir('ok'))
        # c3330_9000 / c3330_9001 share an NPCParamID -> two placements; c4140_9001 has
        # EntityID 0 (unaddressable) and contributes nothing.
        self.assertEqual(m, {'33306000': [12010245, 12010246], '41400100': [12010300]})

    def test_two_parts_in_one_file_is_a_refusal_not_a_row(self):
        with self.assertRaises(G.Refusal) as cm:
            G.index_enemy_parts(enemy_dir('multipart'))
        msg = str(cm.exception)
        self.assertIn('Part.xml', msg)
        self.assertIn('more than one part per file', msg)

    def test_a_layout_that_resolves_nothing_is_a_refusal_not_a_partial(self):
        with self.assertRaises(G.Refusal) as cm:
            G.index_enemy_parts(enemy_dir('nopairs'))
        self.assertIn('not one yielded', str(cm.exception))

    def test_an_unpacked_but_empty_enemy_dir_is_a_refusal(self):
        with self.assertRaises(G.Refusal) as cm:
            G.index_enemy_parts(enemy_dir('emptydir'))
        self.assertIn('no *.xml', str(cm.exception))


class TestJoinOverTheFixture(unittest.TestCase):
    """The whole join, driven over the fixture instead of a real mapstudio tree."""

    def setUp(self):
        self.index = {'m10_00': G.index_enemy_parts(enemy_dir('ok'))}
        # flag -> (check lot, item id, name). 12017965's base lot is 333062020, the shipped pin.
        self.enemy = {'12017965': (333062021, '10100', 'Larval Tear'),
                      '12017966': (414001001, '20900', '')}
        self.ap = {'12017965': 7771237, '12017966': 7771238}
        self.npc_by_base = {'333062020': ['33306000'], '414001000': ['41400100']}
        self.flagmap = {'12017965': ['m10_00'], '12017966': ['m10_00']}

    def rows(self):
        table, unresolved = G.build(self.enemy, self.ap, self.npc_by_base, self.flagmap,
                                    lambda mp: self.index.get(mp, {}))
        buf = io.StringIO()
        G.render(table, buf)
        return buf.getvalue(), unresolved

    def test_rows_render_exactly(self):
        out, unresolved = self.rows()
        self.assertEqual(unresolved, [])
        self.assertEqual(out,
                         "    (12010245, 7771237), // Larval Tear\n"
                         "    (12010246, 7771237), // Larval Tear\n"
                         "    (12010300, 7771238), // 20900\n")

    def test_a_mispair_would_be_visible_here(self):
        # If the pairing ever crossed records, 41400100's entity would attach to the 333062020
        # check. Assert the entity->location binding, not just the count.
        out, _ = self.rows()
        self.assertIn("(12010300, 7771238)", out)
        self.assertNotIn("(12010300, 7771237)", out)

    def test_a_map_that_resolves_nothing_is_reported_unresolved_not_dropped(self):
        self.flagmap = {'12017965': ['m11_00'], '12017966': ['m11_00']}
        out, unresolved = self.rows()
        self.assertEqual(out, "")
        self.assertEqual(sorted(unresolved), ['12017965', '12017966'])

    def test_check_maps_is_one_to_many_every_map_is_tried(self):
        # The right map is SECOND. Last-wins/first-only both lose the row.
        self.flagmap = {'12017965': ['m11_00', 'm10_00'], '12017966': ['m10_00']}
        out, unresolved = self.rows()
        self.assertEqual(unresolved, [])
        self.assertIn("(12010245, 7771237)", out)


class TestCheckMapsParse(unittest.TestCase):
    """The parse itself, not a hand-built dict -- so `last wins` cannot pass this file."""

    def test_a_flag_on_two_maps_keeps_both_rows(self):
        import tempfile
        rows = ("# comment line, ignored\n"
                "flag\tmap\tsource\n"
                "12017965\tm10_00\tmsb\n"
                "12017965\tm11_00\tmsb\n"
                "12017965\tm10_00\tmerchant\n"   # duplicate position: one entry, not two
                "12017966\tm12_01\tmsb\n")
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 'check_maps.tsv')
            with open(p, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(rows)
            self.assertEqual(G.read_flagmap(p),
                             {'12017965': ['m10_00', 'm11_00'], '12017966': ['m12_01']})


class TestFlagDecode(unittest.TestCase):
    def test_legacy_dungeon_flags_decode(self):
        self.assertEqual(G.f2m('12017965'[:8]), 'm12_01')
        self.assertEqual(G.f2m('15001300'), 'm15_00')

    def test_overworld_prefixes_are_refused_by_the_decoder(self):
        # m60/m61 tiles are three-part (m60_35_50); `m60_XX` is not a map that exists.
        self.assertIsNone(G.f2m('60123456'))
        self.assertIsNone(G.f2m('61123456'))

    def test_an_overworld_flag_with_no_check_maps_row_is_a_named_refusal(self):
        with self.assertRaises(G.Refusal) as cm:
            G.maps_for('60123456', {})
        msg = str(cm.exception)
        self.assertIn('60123456', msg)           # the flag is NAMED
        self.assertIn('does not exist', msg)

    def test_an_overworld_flag_with_a_check_maps_row_resolves_normally(self):
        self.assertEqual(G.maps_for('1035507610', {'1035507610': ['m60_35_50']}), ['m60_35_50'])

    def test_a_legacy_flag_with_no_row_still_falls_back(self):
        self.assertEqual(G.maps_for('15001300', {}), ['m15_00'])


class TestDatabaseHandling(unittest.TestCase):
    def test_a_missing_db_is_refused_and_NOT_created(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            missing = os.path.join(td, 'greenfield', 'gen_inputs.db')
            os.makedirs(os.path.dirname(missing))
            with self.assertRaises(G.Refusal):
                G.open_db(missing)
            self.assertFalse(os.path.exists(missing),
                             "sqlite3.connect materialised a zero-byte db -- the exact shape "
                             "check_integrity.py reds on")

    def test_the_default_db_is_the_repo_root_one_and_it_exists(self):
        default = os.path.join(G.REPO, 'gen_inputs.db')
        self.assertTrue(os.path.isfile(default), default)
        con = G.open_db(default)
        self.assertEqual(con.execute("select count(*) from files").fetchone()[0] > 0, True)
        # read-only: a write must fail rather than touch a committed input.
        with self.assertRaises(Exception):
            con.execute("create table _t (x int)")


class TestRender(unittest.TestCase):
    def test_an_entity_reached_twice_emits_one_row(self):
        buf = io.StringIO()
        seen = G.render([(5, 2, 'b'), (5, 1, 'a')], buf)
        self.assertEqual(seen, {5})
        self.assertEqual(buf.getvalue(), "    (5, 1), // a\n")


if __name__ == '__main__':
    unittest.main(verbosity=2)
