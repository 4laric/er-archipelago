"""The door-side witness (tools/datamine_msb_door_sides.py), on synthetic witchy-style MSB fixtures.

WHY THIS SUITE EXISTS. The extracted MSB corpus is licensing-restricted and lives on ONE box; CI
has none. So every line of parsing and geometry in that tool would otherwise be executed for the
first time on the day someone needs an answer about the Belurat well door (#1512) or the Sewer-Gaol
door (#1511) -- and a wrong signed distance looks exactly like a right one in a tsv. This suite
builds a tiny artifacts tree by hand (Part/Asset, Part/DummyAsset, Event/Treasure, Part/Enemy,
Region/PlayArea, and the three params), points the tool at it with `--path`, and asserts the
numbers.

WHAT IS PINNED, and why each case is here:

  * the door is found BY ENTITY ID and BY NAME, and the record's own <Name> wins over the filename;
  * the SIGNED NORMAL separates the two sides. The door is yawed 90 degrees, so its local +Z axis
    is world +X and a pickup at +X is positive while one at -X is negative. A tool that ignored the
    rotation and used world +Z would give BOTH of them ~0 -- that is the red half of the pair;
  * a door with NO <Rotation> yields '-' in normal_dist_m, never a zero-yaw number;
  * the PlayArea column answers `interior-vol:` for a pickup inside an interior volume, through
    datamine_grace_ground.derive_ground (interior maps have sub-volumes too);
  * `--flags` resolves through a fixture greenfield/flag_lots.tsv, and an unresolvable flag is
    DROPPED with a note rather than guessed at;
  * THE REFUSALS: an absent corpus, an absent map, an unknown door and a zero-placement scan each
    exit non-zero and write NOTHING. That is the failure mode this project has already paid for
    twice, and it is the one thing about this tool that must never regress quietly;
  * `--enemy-drops` emits item_grace_coords.tsv's exact column shape for an NpcParam-only drop.

Repo-only by construction (it drives a tools/ script over a temp artifacts tree), so it is
ledgered in tools/gf_suite_ledger.py under GENERATORS.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)
TOOLS = os.path.join(REPO, "tools") if REPO else None
TOOL = os.path.join(TOOLS, "datamine_msb_door_sides.py") if TOOLS else None

MAP = "m20_00_00_00"
DOOR_ENTITY = 20001562
DOOR_POS = (100.0, 10.0, 200.0)
DOOR_YAW = 90.0            # local +Z becomes world +X: the axis the two sides are separated on

# (lot, flag, item name, treasure part, position). NEAR sits at door +X (the "inside" of the yawed
# plane), FAR at door -X. Their straight-line distances are IDENTICAL (both 30 m) -- which is the
# whole point of the normal column: distance alone cannot separate them, sign can.
NEAR = (20000210, 20007210, "Well Depths Key", "TreasureNear", (130.0, 10.0, 200.0))
FAR = (20000220, 20007220, "Somber Smithing Stone", "TreasureFar", (70.0, 10.0, 200.0))
# A third, placed on a DummyAsset instead of an Asset, and 5 m off the plane on the FAR side.
DUMMY = (20000230, 20007230, "Golden Rune", "TreasureDummy", (95.0, 10.0, 260.0))

ENEMY_FLAG = 1049557700
ENEMY_LOT = 104955770
ENEMY_NPC = 55770
ENEMY_POS = (11.5, 22.25, -33.75)


def _load(name):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location("_doors_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ---- fixture builders (witchy MSBE XML, the field names the existing tools actually read) --------
def _part_xml(name, entity, pos, yaw=None, extra=""):
    rot = ("  <Rotation><X>0</X><Y>%s</Y><Z>0</Z></Rotation>\n" % yaw) if yaw is not None else ""
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<Part xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
            "  <Name>%s</Name>\n"
            "  <EntityID>%d</EntityID>\n"
            "  <Position><X>%s</X><Y>%s</Y><Z>%s</Z></Position>\n"
            "%s%s"
            "</Part>\n" % (name, entity, pos[0], pos[1], pos[2], rot, extra))


def _treasure_xml(name, lot, part):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            "<Event>\n"
            "  <Name>%s</Name>\n"
            "  <ItemLotID>%d</ItemLotID>\n"
            "  <TreasurePartName>%s</TreasurePartName>\n"
            "  <InChest>0</InChest>\n"
            "  <StartDisabled>0</StartDisabled>\n"
            "</Event>\n" % (name, lot, part))


def _region_xml(name, pr, pos, w, d, h):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<Region xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
            "  <Name>%s</Name>\n"
            "  <PlayRegionID>%d</PlayRegionID>\n"
            "  <Position><X>%s</X><Y>%s</Y><Z>%s</Z></Position>\n"
            "  <Rotation><X>0</X><Y>0</Y><Z>0</Z></Rotation>\n"
            '  <Shape xsi:type="Box"><Width>%s</Width><Depth>%s</Depth><Height>%s</Height></Shape>\n'
            "</Region>\n" % (name, pr, pos[0], pos[1], pos[2], w, d, h))


def build_artifacts(root, door_yaw=DOOR_YAW):
    """A minimal witchy-style tree holding one interior map with a door, three treasures, one
    rotation-less door, one enemy drop, one PlayArea volume, and the three params."""
    md = os.path.join(root, "mapstudio", MAP + "-msb-dcx")
    asset = os.path.join(md, "Part", "Asset")
    dummy = os.path.join(md, "Part", "DummyAsset")
    _write(os.path.join(asset, "door.xml"),
           _part_xml("AEG099_001_9000", DOOR_ENTITY, DOOR_POS, yaw=door_yaw))
    # The record's <Name> is what joins, not the filename -- so the filename is deliberately wrong.
    _write(os.path.join(asset, "not_the_name.xml"),
           _part_xml("AEG099_002_9000", 20001999, (0, 0, 0)))
    # A second door with NO <Rotation> at all: the explicit missing-field case.
    _write(os.path.join(asset, "norot.xml"), _part_xml("DoorNoRotation", 20001563, DOOR_POS))
    for lot, _flag, _nm, part, pos in (NEAR, FAR):
        _write(os.path.join(asset, part + ".xml"), _part_xml(part, 0, pos))
    _write(os.path.join(dummy, DUMMY[3] + ".xml"), _part_xml(DUMMY[3], 0, DUMMY[4]))

    tre = os.path.join(md, "Event", "Treasure")
    for lot, _flag, _nm, part, _pos in (NEAR, FAR, DUMMY):
        _write(os.path.join(tre, "t%d.xml" % lot), _treasure_xml("宝箱%d" % lot, lot, part))
    # A treasure for a lot nobody asked about: it must not appear in the table.
    _write(os.path.join(tre, "tnoise.xml"), _treasure_xml("noise", 20009999, NEAR[3]))

    _write(os.path.join(md, "Part", "Enemy", "e1.xml"),
           _part_xml("c1000_9000", 20005000, ENEMY_POS,
                     extra="  <NPCParamID>%d</NPCParamID>\n" % ENEMY_NPC))

    # An interior PlayArea volume that contains NEAR and not FAR (centred on the door, 40 wide in
    # X starting at +10): the point-in-volume column, through datamine_grace_ground.
    _write(os.path.join(md, "Region", "PlayArea", "pa.xml"),
           _region_xml("PlayVol", 2000010, (130, 0, 200), 40, 40, 60))

    vv = os.path.join(root, "vanilla_er", "vanilla_er")
    lot_rows = ["ID,getItemFlagId"]
    for lot, flag, _nm, _p, _pos in (NEAR, FAR, DUMMY):
        lot_rows.append("%d,%d" % (lot, flag))
    lot_rows.append("20009999,20009999")
    _write(os.path.join(vv, "ItemLotParam_map.csv"), "\n".join(lot_rows) + "\n")
    _write(os.path.join(vv, "ItemLotParam_enemy.csv"),
           "ID,getItemFlagId\n%d,%d\n" % (ENEMY_LOT, ENEMY_FLAG))
    _write(os.path.join(vv, "NpcParam.csv"),
           "ID,itemLotId_enemy,itemLotId_map\n%d,%d,0\n" % (ENEMY_NPC, ENEMY_LOT))
    _write(os.path.join(vv, "PlayRegionParam.csv"),
           "ID,areaNo,gridXNo,gridZNo\n2000000,20,0,0\n2000010,20,0,0\n")
    return root


def build_gf(gf):
    """A fixture greenfield/ holding just the two committed tables `--flags` resolves through."""
    rows = ["flag\ttable\tlot\tslot\tcategory\titem_id\tnum\tgoods_type\tname"]
    for lot, flag, nm, _p, _pos in (NEAR, FAR, DUMMY):
        rows.append("%d\tmap\t%d\t1\t1\t0\t1\t1\t%s" % (flag, lot, nm))
    _write(os.path.join(gf, "flag_lots.tsv"), "\n".join(rows) + "\n")
    _write(os.path.join(gf, "msb_flag_region.tsv"),
           "flag\tmap_id\titem_lot_id\ttreasure_name\tsource\n"
           "%d\tm20_00\t%d\t%s\ttreasure\n" % (DUMMY[1], DUMMY[0], DUMMY[3]))
    return gf


def _run(root, *args):
    out = subprocess.run([sys.executable, TOOL, "--path", root] + list(args),
                         capture_output=True, text=True, timeout=300)
    return out.returncode, out.stdout, out.stderr


def _table(stdout):
    lines = [ln for ln in stdout.splitlines() if ln.strip() and not ln.startswith("#")]
    head = lines[0].split("\t")
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:]]


class DoorSidesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TOOLS is None or not os.path.isfile(TOOL or ""):
            raise unittest.SkipTest(REPO_ONLY_REASON)
        sys.path.insert(0, TOOLS)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = build_artifacts(os.path.join(cls.tmp.name, "corpus"))
        cls.mod = _load("datamine_msb_door_sides")
        cls.gf = build_gf(os.path.join(cls.tmp.name, "repo", "greenfield"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # ---- unit level: the pieces, against the fixture ------------------------------------------
    def _rooted(self):
        mod = _load("datamine_msb_door_sides")
        mod._set_artifacts_root(self.root)
        mod.GF = self.gf
        return mod

    def test_full_map_id_accepts_both_spellings(self):
        self.assertEqual(MAP, self.mod.full_map_id("m20_00"))
        self.assertEqual(MAP, self.mod.full_map_id(MAP))
        with self.assertRaises(SystemExit):
            self.mod.full_map_id("Belurat")

    def test_the_door_is_found_by_entity_and_by_name(self):
        mod = self._rooted()
        msb = mod.msb_dir_or_die("m20_00")
        by_ent = mod.find_door(msb, str(DOOR_ENTITY))
        by_name = mod.find_door(msb, "AEG099_001_9000")
        for d in (by_ent, by_name):
            self.assertEqual("AEG099_001_9000", d.name)
            self.assertEqual(DOOR_ENTITY, d.entity)
            self.assertEqual(DOOR_POS, (d.x, d.y, d.z))
            self.assertAlmostEqual(DOOR_YAW, d.yaw)

    def test_the_normal_follows_the_yaw_not_world_z(self):
        """THE RED/GREEN PAIR. Yaw 90 sends local +Z to world +X. A tool that ignored <Rotation>
        would return (0, 0, 1) here and score both sides of the door at ~0."""
        mod = self._rooted()
        n = mod.find_door(mod.msb_dir_or_die("m20_00"), str(DOOR_ENTITY)).normal()
        self.assertAlmostEqual(1.0, n[0], places=6)
        self.assertAlmostEqual(0.0, n[2], places=6)

    def test_a_door_without_rotation_has_no_normal(self):
        mod = self._rooted()
        d = mod.find_door(mod.msb_dir_or_die("m20_00"), "20001563")
        self.assertIsNone(d.yaw)
        self.assertIsNone(d.normal())

    def test_flags_resolve_through_the_committed_tables_only(self):
        mod = self._rooted()
        cands, unresolved = mod.resolve_candidates([NEAR[1], FAR[1], 999999], [], gf=self.gf)
        self.assertEqual([999999], unresolved)
        self.assertEqual({NEAR[0], FAR[0]}, set(cands))
        self.assertEqual(NEAR[2], cands[NEAR[0]][1])

    def test_msb_flag_region_is_the_fallback_join(self):
        """DUMMY's flag is in BOTH tables; a flag present only in msb_flag_region must still
        resolve, because flag_lots does not cover every acquisition flag."""
        mod = self._rooted()
        cands, unresolved = mod.resolve_candidates([DUMMY[1]], [], gf=self.gf)
        self.assertEqual([], unresolved)
        self.assertIn(DUMMY[0], cands)

    # ---- end to end ---------------------------------------------------------------------------
    def test_the_two_sides_separate_by_sign_at_equal_distance(self):
        rc, out, err = self._cli("--map", "m20_00", "--door", str(DOOR_ENTITY),
                                 "--lots", "%d,%d" % (NEAR[0], FAR[0]))
        self.assertEqual(0, rc, err[-800:])
        rows = {r["lot_id"]: r for r in _table(out)}
        self.assertEqual({str(NEAR[0]), str(FAR[0])}, set(rows))
        near, far = rows[str(NEAR[0])], rows[str(FAR[0])]
        self.assertEqual(near["distance_m"], far["distance_m"])       # 30.00 both
        self.assertAlmostEqual(30.0, float(near["normal_dist_m"]), places=2)
        self.assertAlmostEqual(-30.0, float(far["normal_dist_m"]), places=2)
        self.assertEqual(NEAR[3], near["treasure_part"])

    def test_a_dummyasset_placement_is_found_and_the_noise_lot_is_not(self):
        rc, out, err = self._cli("--map", "m20_00", "--door", str(DOOR_ENTITY),
                                 "--flags", ",".join(str(c[1]) for c in (NEAR, FAR, DUMMY)))
        self.assertEqual(0, rc, err[-800:])
        rows = {r["lot_id"]: r for r in _table(out)}
        self.assertIn(str(DUMMY[0]), rows)
        self.assertNotIn("20009999", rows)
        self.assertEqual(DUMMY[2], rows[str(DUMMY[0])]["item_name"])

    def test_the_playarea_column_answers_from_the_interior_volume(self):
        rc, out, err = self._cli("--map", "m20_00", "--door", str(DOOR_ENTITY),
                                 "--lots", "%d,%d" % (NEAR[0], FAR[0]))
        self.assertEqual(0, rc, err[-800:])
        rows = {r["lot_id"]: r for r in _table(out)}
        self.assertEqual("interior-vol:PlayVol", rows[str(NEAR[0])]["play_region_source"])
        self.assertEqual("2000010", rows[str(NEAR[0])]["play_region_ids"])
        # FAR is 60 m outside the volume face, well past SEAM_SLACK: the map default, not a volume.
        self.assertEqual("interior-map", rows[str(FAR[0])]["play_region_source"])

    def test_a_rotationless_door_emits_a_dash_and_says_so(self):
        rc, out, err = self._cli("--map", "m20_00", "--door", "20001563",
                                 "--lots", str(NEAR[0]))
        self.assertEqual(0, rc, err[-800:])
        self.assertEqual("-", _table(out)[0]["normal_dist_m"])
        self.assertIn("no <Rotation>", err)

    def test_emit_writes_a_deterministic_tsv_with_the_witness_caveat(self):
        with tempfile.TemporaryDirectory() as out_dir:
            p = os.path.join(out_dir, "doors.tsv")
            rc, _out, err = self._cli("--map", "m20_00", "--door", str(DOOR_ENTITY),
                                      "--lots", "%d,%d" % (FAR[0], NEAR[0]), "--emit", p)
            self.assertEqual(0, rc, err[-800:])
            with open(p, encoding="utf-8") as fh:
                first = fh.read()
            rc2, _o2, _e2 = self._cli("--map", "m20_00", "--door", str(DOOR_ENTITY),
                                      "--lots", "%d,%d" % (NEAR[0], FAR[0]), "--emit", p)
            self.assertEqual(0, rc2)
            with open(p, encoding="utf-8") as fh:
                self.assertEqual(first, fh.read())
            self.assertIn("it RANKS, a human RULES", first)
            self.assertIn("\t".join(self.mod.COLUMNS), first)

    def test_enemy_drops_emit_the_item_grace_coords_shape(self):
        rc, out, err = self._cli("--enemy-drops", str(ENEMY_FLAG))
        self.assertEqual(0, rc, err[-800:])
        lines = [ln for ln in out.splitlines() if ln.strip() and not ln.startswith("#")]
        self.assertEqual(list(self.mod.ENEMY_COLUMNS), lines[0].split("\t"))
        cells = lines[1].split("\t")
        self.assertEqual(["item", str(ENEMY_FLAG), MAP], cells[:3])
        self.assertEqual([str(v) for v in ENEMY_POS], cells[3:6])
        self.assertEqual("", cells[6])

    # ---- THE REFUSALS -------------------------------------------------------------------------
    def test_an_absent_corpus_is_fatal_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as empty:
            p = os.path.join(empty, "never.tsv")
            out = subprocess.run([sys.executable, TOOL, "--path", empty, "--map", "m20_00",
                                  "--door", str(DOOR_ENTITY), "--lots", str(NEAR[0]),
                                  "--emit", p],
                                 capture_output=True, text=True, timeout=300)
            self.assertNotEqual(0, out.returncode)
            self.assertIn("FATAL", out.stderr)
            self.assertFalse(os.path.exists(p), "a refused run must not leave a table behind")

    def test_an_absent_map_is_fatal(self):
        rc, _out, err = self._cli("--map", "m99_00", "--door", str(DOOR_ENTITY),
                                  "--lots", str(NEAR[0]))
        self.assertNotEqual(0, rc)
        self.assertIn("FATAL", err)

    def test_an_unknown_door_is_fatal_and_names_where_it_looked(self):
        rc, _out, err = self._cli("--map", "m20_00", "--door", "20009998",
                                  "--lots", str(NEAR[0]))
        self.assertNotEqual(0, rc)
        self.assertIn("Part/Asset", err)

    def test_zero_placements_is_fatal_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as out_dir:
            p = os.path.join(out_dir, "never.tsv")
            rc, _out, err = self._cli("--map", "m20_00", "--door", str(DOOR_ENTITY),
                                      "--lots", "20001234", "--emit", p)
            self.assertNotEqual(0, rc)
            self.assertIn("ZERO placements", err)
            self.assertFalse(os.path.exists(p))

    def test_no_candidates_at_all_is_refused(self):
        rc, _out, err = self._cli("--map", "m20_00", "--door", str(DOOR_ENTITY))
        self.assertNotEqual(0, rc)
        self.assertIn("--flags or --lots", err)

    # ---- helper -------------------------------------------------------------------------------
    def _cli(self, *args):
        """Run the tool with the fixture greenfield/ in place of the repo's, via ER_REPO."""
        env = dict(os.environ, ER_REPO=os.path.dirname(self.gf))
        out = subprocess.run([sys.executable, TOOL, "--path", self.root] + list(args),
                             capture_output=True, text=True, timeout=300, env=env)
        return out.returncode, out.stdout, out.stderr


if __name__ == "__main__":
    unittest.main()
