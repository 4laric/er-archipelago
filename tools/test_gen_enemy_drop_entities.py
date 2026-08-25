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

AND (2026-08-24) the THREE unresolved classes. A vanilla `<EntityID>0` placement -- e.g. the Siofra
larval-tear dropper, `m12_02_00_00-msb-dcx/Part/Enemy/c3330_9000.xml`, `<NPCParamID>33300665` with
`<EntityID>0` -- can never be resolved by any amount of further datamining, because there is no id
for an EntityID-keyed `CharacterDead` watch to key on. Reporting it in the same flat list as maps
that simply were not on disk turned a structural limit into a coverage number.

Run: python -m unittest -v tools/test_gen_enemy_drop_entities.py
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_enemy_drop_entities as G  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testdata', 'enemy_drop_msb')


def enemy_dir(kind, mp='m10_00'):
    return os.path.join(FIX, kind, mp + '_00_00-msb-dcx', 'Part', 'Enemy')


class TestXmlPairing(unittest.TestCase):
    def test_one_part_per_file_pairs_within_the_record(self):
        m = G.index_enemy_parts(enemy_dir('ok'))
        # c3330_9000 / c3330_9001 share an NPCParamID -> two placements; c4140_9001 has
        # EntityID 0 (unaddressable) so it stays out of the addressable side.
        self.assertEqual(m.by_npc, {'33306000': [12010245, 12010246], '41400100': [12010300]})
        self.assertTrue(m.present)

    def test_entity_zero_parts_are_counted_not_discarded(self):
        # c4140_9001 is NPCParamID 41400100 with <EntityID>0. Dropping it outright made an
        # unaddressable placement look identical to an un-datamined one.
        m = G.index_enemy_parts(enemy_dir('ok'))
        self.assertEqual(m.zero_by_npc, {'41400100': 1})

    def test_an_npc_whose_every_part_is_entity_zero_resolves_nothing_but_is_recorded(self):
        # The real vanilla Siofra row: NPCParamID 33300665 exists in m12_02 and its only part
        # carries <EntityID>0.
        m = G.index_enemy_parts(enemy_dir('entityzero', 'm12_02'))
        self.assertNotIn('33300665', m.by_npc)
        self.assertEqual(m.zero_by_npc['33300665'], 1)
        self.assertEqual(m.by_npc, {'42000050': [12020400]})

    def test_a_dir_of_only_entity_zero_parts_is_still_the_nothing_resolved_refusal(self):
        # The refusal keys on the NON-ZERO side deliberately: an un-unpacked layout must stay
        # loud, and no real map is made entirely of unaddressable parts.
        with self.assertRaises(G.Refusal):
            G.index_enemy_parts(enemy_dir('nopairs'))

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
        self.index = {'m10_00': G.index_enemy_parts(enemy_dir('ok')),
                      'm12_02': G.index_enemy_parts(enemy_dir('entityzero', 'm12_02'))}
        # flag -> (check lot, item id, name). 12017965's base lot is 333062020, the shipped pin.
        self.enemy = {'12017965': (333062021, '10100', 'Larval Tear'),
                      '12017966': (414001001, '20900', '')}
        self.ap = {'12017965': 7771237, '12017966': 7771238}
        self.npc_by_base = {'333062020': ['33306000'], '414001000': ['41400100']}
        self.flagmap = {'12017965': ['m10_00'], '12017966': ['m10_00']}

    def rows(self):
        table, unresolved = G.build(self.enemy, self.ap, self.npc_by_base, self.flagmap,
                                    lambda mp: self.index.get(mp, G.EMPTY_INDEX))
        buf = io.StringIO()
        G.render(table, buf)
        return buf.getvalue(), unresolved

    def test_rows_render_exactly(self):
        out, unresolved = self.rows()
        self.assertEqual(unresolved, G.Unresolved([], [], []))
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
        # m11_00 is not on disk at all -> the class a fuller MSB tree fixes, and ONLY that class.
        self.assertEqual(unresolved, G.Unresolved([], [], ['12017965', '12017966']))

    def test_an_npc_placed_only_at_entity_zero_is_its_own_class_not_a_datamining_gap(self):
        # 33300665 is placed in m12_02 and every part of it is <EntityID>0. No regen can fix it;
        # calling it "unresolved" alongside the un-unpacked maps is what hid the class.
        self.enemy = {'12027985': (333065001, '8185', 'Larval Tear')}
        self.ap = {'12027985': 7771343}
        self.npc_by_base = {'333065000': ['33300665']}
        self.flagmap = {'12027985': ['m12_02']}
        out, unresolved = self.rows()
        self.assertEqual(out, "")
        self.assertEqual(unresolved, G.Unresolved(['12027985'], [], []))

    def test_a_map_that_was_read_but_holds_no_such_npc_is_the_absent_class(self):
        # m12_02 IS on disk and parsed; nothing in it runs NPC 33306000.
        self.enemy = {'12017965': (333062021, '10100', 'Larval Tear')}
        self.ap = {'12017965': 7771237}
        self.flagmap = {'12017965': ['m12_02']}
        out, unresolved = self.rows()
        self.assertEqual(out, "")
        self.assertEqual(unresolved, G.Unresolved([], ['12017965'], []))

    def test_an_addressable_part_still_wins_over_a_zero_sibling(self):
        # 41400100 has BOTH a zero part and an addressable one -- it must resolve, and must not
        # leak into any unresolved class.
        out, unresolved = self.rows()
        self.assertIn("(12010300, 7771238)", out)
        self.assertEqual(unresolved, G.Unresolved([], [], []))

    def test_check_maps_is_one_to_many_every_map_is_tried(self):
        # The right map is SECOND. Last-wins/first-only both lose the row.
        self.flagmap = {'12017965': ['m11_00', 'm10_00'], '12017966': ['m10_00']}
        out, unresolved = self.rows()
        self.assertEqual(unresolved, G.Unresolved([], [], []))
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
