"""The PlayArea ITEM scan (tools/datamine_item_play_regions.py), on synthetic MSB fixtures.

WHY THIS SUITE IS UNUSUAL. The datamine tools are normally witnessed only by their COMMITTED
OUTPUT: CI has no `elden_ring_artifacts/`, so the geometry inside them -- the point-in-volume
test, the tile fold, the seam snap -- has never been executed by anything except a run on Alaric's
box, where a wrong answer looks exactly like a right one (a tsv full of plausible rows). This
scan's answers are about to REPLACE a 91.4% heuristic as rulings on check regions, so the geometry
gets a real witness first: a tiny hand-built witchy-style MSB tree, one fixture per shape and per
fallback, with the expected `source` asserted per case. `--artifacts` (added to
datamine_grace_ground for exactly this) is what lets the machinery be pointed at it.

THE FOLD-FIRST TRAP is the case that matters most, and it is a RED/GREEN PAIR: an item authored on
a LOD2 tile is inside its volume only when folded through `overworld_fold.world_xz` (pitch
256<<lod plus the centring term). The same point folded the way the MSB loader positions volumes
(`tile*256`) lands hundreds of metres away, inside nothing, and would have answered
`tile-default` -- a plausible row, silently wrong, issue #338 all over again.

Repo-only by construction (it drives a tools/ script over a temp artifacts tree), so it is
ledgered in tools/gf_suite_ledger.py under GENERATORS.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
# Never positional: under tools/gf_test.py the same walk lands in the AP checkout (2026-07-27).
REPO = find_repo_root(HERE)
TOOL = os.path.join(REPO, "tools", "datamine_item_play_regions.py") if REPO else None

TILE = 40                       # fine-grid tile the fixture volumes live on (tx = tz = 40)
BASE = TILE * 256               # 10240 -- the world origin of that tile


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- fixture builders ---------------------------------------------------------------------------
def _region_xml(name, pr, pos, shape, yaw=0.0):
    """One witchy'd MSB region file. `shape` is the <Shape> body, already xsi:typed."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Region xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        "  <Name>%s</Name>\n"
        "  <PlayRegionID>%d</PlayRegionID>\n"
        "  <Position><X>%s</X><Y>%s</Y><Z>%s</Z></Position>\n"
        "  <Rotation><X>0</X><Y>%s</Y><Z>0</Z></Rotation>\n"
        "%s"
        "</Region>\n" % (name, pr, pos[0], pos[1], pos[2], yaw, shape))


def _box(w, d, h):
    return ('  <Shape xsi:type="Box"><Width>%s</Width><Depth>%s</Depth><Height>%s</Height></Shape>\n'
            % (w, d, h))


def _cyl(r, h):
    return '  <Shape xsi:type="Cylinder"><Radius>%s</Radius><Height>%s</Height></Shape>\n' % (r, h)


def _sphere(r):
    return '  <Shape xsi:type="Sphere"><Radius>%s</Radius></Shape>\n' % r


def _composite(children):
    return ('  <Shape xsi:type="Composite">%s</Shape>\n'
            % "".join("<Child><RegionName>%s</RegionName></Child>" % c for c in children))


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def build_artifacts(root):
    """A minimal witchy-style artifacts tree: two overworld tiles, one interior map, the two params.

    Volume geometry (LOCAL coords; the loader world-positions overworld tiles at tile*256):
      BoxVol   6800000  (100, 0, 100) yaw 45, 40 x 10 x 20   -- the yaw is load-bearing, see below
      CylVol   6810000  (200, 0,  50) r 20, h 20
      SphVol   6820000  ( 50, 0, 200) r 15
      CompVol  6830000  Composite -> CompChildA, a 20 x 20 x 20 box at (150, 0, 150)
      CrossVol 6850000  on the NEIGHBOURING tile m60_41_40 -- the cross-tile case
      InnerVol 1000010  in interior map m10_00 (world == local, no tile offset)
    """
    m = os.path.join(root, "map")
    d = os.path.join(m, "m60_%02d_%02d_00-msb-dcx" % (TILE, TILE), "Region", "PlayArea")
    _write(os.path.join(d, "box.xml"), _region_xml("BoxVol", 6800000, (100, 0, 100), _box(40, 10, 20), 45.0))
    _write(os.path.join(d, "cyl.xml"), _region_xml("CylVol", 6810000, (200, 0, 50), _cyl(20, 20)))
    _write(os.path.join(d, "sph.xml"), _region_xml("SphVol", 6820000, (50, 0, 200), _sphere(15)))
    _write(os.path.join(d, "comp.xml"),
           _region_xml("CompVol", 6830000, (0, 0, 0), _composite(["CompChildA"])))
    _write(os.path.join(m, "m60_%02d_%02d_00-msb-dcx" % (TILE, TILE), "Region", "Other", "childa.xml"),
           _region_xml("CompChildA", 0, (150, 0, 150), _box(20, 20, 20)))
    d2 = os.path.join(m, "m60_%02d_%02d_00-msb-dcx" % (TILE + 1, TILE), "Region", "PlayArea")
    _write(os.path.join(d2, "cross.xml"), _region_xml("CrossVol", 6850000, (30, 0, 30), _box(40, 40, 20)))
    d3 = os.path.join(m, "m10_00_00_00-msb-dcx", "Region", "PlayArea")
    _write(os.path.join(d3, "inner.xml"), _region_xml("InnerVol", 1000010, (0, 0, 0), _box(40, 40, 20)))

    vv = os.path.join(root, "vanilla_er", "vanilla_er")
    _write(os.path.join(vv, "PlayRegionParam.csv"),
           "ID,areaNo,gridXNo,gridZNo\n"
           "6800000,60,%d,%d\n"        # a volume id also present as a tile row -- harmless
           "6899900,60,%d,%d\n"        # THE tile default for our fixture tile
           "6859900,60,%d,%d\n"        # the neighbouring tile's default
           "1000000,10,0,0\n"          # interior map m10_00's default (bucket 10000)
           % (TILE, TILE, TILE, TILE, TILE + 1, TILE))
    return root


# item flags, and where each one is authored. (flag, map_id, x, y, z, expected source prefix)
BOX_PT = (110, 1, 90)          # dx=+10 dz=-10 from the box centre: INSIDE only because of yaw 45
CASES = [
    ("1000000001", "m60_40_40", BOX_PT, "volume:BoxVol", [6800000]),
    ("1000000002", "m60_40_40", (205, 1, 55), "volume:CylVol", [6810000]),
    ("1000000003", "m60_40_40", (55, 5, 205), "volume:SphVol", [6820000]),
    ("1000000004", "m60_40_40", (152, 1, 148), "volume:CompChildA", [6830000]),
    ("1000000005", "m60_40_40", (224, 1, 50), "seam:CylVol", [6810000]),     # 4 m off the face
    ("1000000006", "m60_40_40", (250, 1, 250), "tile-default", [6899900, 6800000]),
    # LOD2: authored on m60_10_10_02, pitch 1024 + centring 384. Folded it lands in BoxVol at
    # world (10350, 10330); folded the loader's way (tile*256) it lands ~8 km away, inside nothing.
    ("1000000007", "m60_10_10_02", (10350 - 10 * 1024 - 384, 1, 10330 - 10 * 1024 - 384),
     "volume:BoxVol", [6800000]),
    # cross-tile: its CHECK is labelled m60_40_40, its coords are authored on m60_41_40.
    ("1000000008", "m60_41_40", (30, 1, 30), "volume:CrossVol", [6850000]),
    ("1000000009", "m10_00", (0, 1, 0), "interior-vol:InnerVol", [1000010]),
    ("1000000010", "m10_00", (500, 1, 500), "interior-map", [1000000]),
]


def build_coords_repo(root):
    lines = ["# fixture item_grace_coords.tsv", "kind\tkey\tmap_id\tx\ty\tz\tname"]
    for flag, mid, (x, y, z), _src, _ids in CASES:
        lines.append("item\t%s\t%s\t%s\t%s\t%s\t" % (flag, mid, x, y, z))
    _write(os.path.join(root, "greenfield", "item_grace_coords.tsv"), "\n".join(lines) + "\n")
    return root


# graces, for the --graces calibration mode: (flag, areaNo, gridX, gridZ, pos, entity, buckets)
GRACES = [
    (76001, 60, TILE, TILE, BOX_PT, "", "68000"),
    (76002, 60, TILE, TILE, (250, 1, 250), "", "68000;68999"),
    (76003, 10, 0, 0, (0, 1, 0), "10000950", "10000"),
]


def build_grace_fixtures(artifacts, ground_path, mutate=False):
    rows = ["eventflagId,areaNo,gridXNo,gridZNo,posX,posY,posZ,bonfireEntityId"]
    for f, a, gx, gz, (x, y, z), ent, _b in GRACES:
        rows.append("%d,%d,%d,%d,%s,%s,%s,%s" % (f, a, gx, gz, x, y, z, ent))
    _write(os.path.join(artifacts, "vanilla_er", "vanilla_er", "BonfireWarpParam.csv"),
           "\n".join(rows) + "\n")
    out = ["# fixture grace_ground.tsv", "grace_flag\tground_buckets\tsource\ttile"]
    for f, a, gx, gz, _p, _e, b in GRACES:
        if mutate and f == 76001:
            b = "68123"
        out.append("%d\t%s\t%s\tm%d_%02d_%02d" % (f, b, "fixture", a, gx, gz))
    _write(ground_path, "\n".join(out) + "\n")


class ItemPlayRegionScanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TOOL is None or not os.path.isfile(TOOL):
            raise unittest.SkipTest(REPO_ONLY_REASON)
        cls.tmp = tempfile.mkdtemp(prefix="ipr_fixture_")
        cls.artifacts = build_artifacts(os.path.join(cls.tmp, "artifacts"))
        cls.coords = build_coords_repo(os.path.join(cls.tmp, "coordsrepo"))
        cls.mod = _load(TOOL, "_ipr_tool")
        # The fixture corpus is four volumes, not four thousand: the degenerate-scan floor and the
        # table floor are asserted in their OWN tests and stood down for the geometry ones.
        cls.mod.VOL_FLOOR = 1
        cls.mod.MIN_DERIVED_ABS = 1

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _run(self, extra=(), flag="--artifacts"):
        out = os.path.join(self.tmp, "item_play_regions.tsv")
        rc = self.mod.main(["--emit", flag, self.artifacts, "--coords-repo", self.coords,
                            "--out", out] + list(extra))
        self.assertEqual(rc, 0)
        rows = {}
        with open(out, encoding="utf-8") as fh:
            for ln in fh:
                if ln.startswith("#") or ln.startswith("flag\t") or not ln.strip():
                    continue
                flag, mid, ids, buckets, src = ln.rstrip("\n").split("\t")
                rows[flag] = (mid, ids, buckets, src)
        return rows

    # -- the flag that points all of this at a corpus that MOVED ---------------------------------
    def test_path_and_artifacts_are_the_same_flag(self):
        """`--path` is the spelling every corpus-reading tool now shares (tools/artifacts_root.py);
        `--artifacts` is kept as an alias so the runbook's commands keep working verbatim. Same
        fixture tree, at a NON-DEFAULT location, must give byte-identical rows through either."""
        self.assertEqual(self._run(flag="--path"), self._run(flag="--artifacts"))

    def test_the_same_corpus_resolves_from_map_mapstudio_or_the_bare_root(self):
        """WitchyBND does not promise a subdirectory. Alaric's 2026-08-26 export put every map FLAT
        under `<root>/mapstudio/`, beside `_pilot`/`breakgeom`/`m00`..`m61` noise dirs, and this
        scan's loader said `FATAL: no witchy'd m60/m61 MSBs under <root>/map`. All three layouts
        are the SAME corpus, so all three must give BYTE-IDENTICAL rows off plain `--path <root>`:
        discovery may move where the tool looks, never what it answers."""
        want = self._run()                                   # the map/ layout, built in setUpClass
        for layout in ("mapstudio", ""):
            with self.subTest(layout=layout or "<root>"):
                alt = os.path.join(self.tmp, "alt_" + (layout or "root"))
                shutil.copytree(self.artifacts, alt)
                src = os.path.join(alt, "map")
                dst = os.path.join(alt, layout) if layout else alt
                if layout:
                    os.rename(src, dst)
                else:
                    for name in os.listdir(src):
                        os.rename(os.path.join(src, name), os.path.join(dst, name))
                    os.rmdir(src)
                for noise in ("_pilot", "breakgeom", "m00", "m60", "m61"):
                    os.makedirs(os.path.join(alt, noise), exist_ok=True)
                out = os.path.join(self.tmp, "alt_%s.tsv" % (layout or "root"))
                self.assertEqual(0, self.mod.main(["--emit", "--path", alt,
                                                   "--coords-repo", self.coords, "--out", out]))
                rows = {}
                with open(out, encoding="utf-8") as fh:
                    for ln in fh:
                        if ln.startswith("#") or ln.startswith("flag\t") or not ln.strip():
                            continue
                        f, mid, ids, buckets, src_col = ln.rstrip("\n").split("\t")
                        rows[f] = (mid, ids, buckets, src_col)
                self.assertEqual(want, rows,
                                 "the %s layout answered differently from map/" % (layout or "root"))

    def test_a_moved_root_that_is_not_there_stops_the_run(self):
        """A typo'd root must FAIL, not scan an empty tree and write a plausible table."""
        with self.assertRaises(SystemExit):
            self.mod.main(["--path", os.path.join(self.tmp, "no-such-corpus")])

    # -- the fixture matrix, one assertion set per shape and per fallback ------------------------
    def test_every_case_answers_from_the_expected_source(self):
        rows = self._run()
        self.assertEqual(len(rows), len(CASES), "one row per PLACEMENT, no more and no fewer")
        for flag, mid, _pt, want_src, want_ids in CASES:
            self.assertIn(flag, rows, "%s produced no row" % flag)
            got_mid, got_ids, got_buckets, got_src = rows[flag]
            self.assertEqual(got_mid, mid, "the row must carry the coords tsv's OWN map_id")
            self.assertTrue(got_src.startswith(want_src),
                            "%s: source %r is not %r -- the answer came from the wrong instrument, "
                            "which is exactly the failure a source column exists to expose"
                            % (flag, got_src, want_src))
            self.assertEqual(sorted(int(i) for i in got_ids.split(";")), sorted(want_ids), flag)
            self.assertEqual(sorted(int(b) for b in got_buckets.split(";")),
                             sorted({i // 100 for i in want_ids}),
                             "buckets are ids // 100 -- the kick-watch id space")

    def test_box_containment_needs_the_yaw(self):
        """The box case is only inside because `contains` rotates the delta by +yaw. Its mirror:
        the same offset against an UNROTATED box of the same size is outside. Without this, a
        passing box test proves nothing about the rotation."""
        gg = _load(os.path.join(REPO, "tools", "datamine_grace_ground.py"), "_ipr_gg")
        rot = gg.Vol(6800000, 60, "B", "Box", 0, 0, 0, 45.0, 40, 10, 20)
        flat = gg.Vol(6800000, 60, "B", "Box", 0, 0, 0, 0.0, 40, 10, 20)
        self.assertTrue(rot.contains(10, 1, -10))
        self.assertFalse(flat.contains(10, 1, -10))

    def test_seam_is_inside_the_slack_and_its_mirror_is_not(self):
        """The seam case sits 4 m off the cylinder face -- inside SEAM_SLACK. A point past the
        slack must fall through to the tile default instead, or 'seam' would mean nothing."""
        gg = _load(os.path.join(REPO, "tools", "datamine_grace_ground.py"), "_ipr_gg2")
        self.assertEqual(gg.SEAM_SLACK, 8.0)
        vols = self.mod.load_volumes_or_die(force=True)
        tile_ids, interior_ids = gg.load_play_region_defaults(
            os.path.join(self.artifacts, "vanilla_er", "vanilla_er", "PlayRegionParam.csv"))
        ids, src = self.mod.derive("m60_40_40", 224, 1, 50, vols, tile_ids, interior_ids)
        self.assertTrue(src.startswith("seam:CylVol"), src)
        ids, src = self.mod.derive("m60_40_40", 240, 1, 50, vols, tile_ids, interior_ids)
        self.assertEqual(src, "tile-default", "20 m off the face is not a seam")

    def test_lod2_item_resolves_ONLY_through_the_shared_fold(self):
        """The red/green pair. Folded with `world_xz` the LOD2 item is inside BoxVol; folded the
        way the volume loader positions tiles (tile*256, no LOD pitch, no centring term) the same
        authored point is inside NOTHING and would have answered tile-default."""
        rows = self._run()
        self.assertTrue(rows["1000000007"][3].startswith("volume:BoxVol"))
        _f, mid, (x, _y, z), _s, _i = CASES[6]
        self.assertEqual(mid, "m60_10_10_02")
        vols = self.mod.load_volumes_or_die(force=True)
        naive_x, naive_z = 10 * 256 + x, 10 * 256 + z          # the WRONG fold, on purpose
        self.assertFalse([v for v in vols if v.contains(naive_x, 1, naive_z)],
                         "the unfolded LOD2 point must be inside nothing -- if it is not, this "
                         "test has stopped witnessing the fold")

    def test_cross_tile_row_answers_from_its_map_id_not_its_label(self):
        """Three real Bestial Sanctum checks are labelled m60_51_41 with coords in m60_51_43. The
        scan is driven off the coords row's map_id, so the neighbouring tile's volume answers."""
        rows = self._run()
        mid, ids, buckets, src = rows["1000000008"]
        self.assertEqual(mid, "m60_41_40")
        self.assertEqual(src, "volume:CrossVol")
        self.assertEqual(buckets, "68500")
        self.assertNotEqual(buckets, "68999", "it must not have taken the LABEL tile's default")

    # -- the refusals ---------------------------------------------------------------------------
    def test_degenerate_scan_is_refused_without_force(self):
        """A partial witchy export answers `tile-default` everywhere, which LOOKS like a result."""
        self.mod.VOL_FLOOR = 10 ** 6
        try:
            with self.assertRaises(SystemExit) as cm:
                self.mod.main(["--artifacts", self.artifacts, "--coords-repo", self.coords,
                               "--out", os.path.join(self.tmp, "never.tsv")])
            self.assertIn("PARTIAL witchy export", str(cm.exception))
            self.assertFalse(os.path.exists(os.path.join(self.tmp, "never.tsv")))
            self.assertEqual(0, self.mod.main(["--artifacts", self.artifacts, "--coords-repo",
                                               self.coords, "--force", "--out",
                                               os.path.join(self.tmp, "forced.tsv")]))
        finally:
            self.mod.VOL_FLOOR = 1

    def test_floor_refuses_a_shrinking_table(self):
        """A ground-truth table that shrinks and writes anyway is how a gate goes blind."""
        self.mod.MIN_DERIVED_ABS = 10 ** 6
        try:
            out = os.path.join(self.tmp, "floored.tsv")
            with self.assertRaises(SystemExit) as cm:
                self.mod.main(["--emit", "--artifacts", self.artifacts, "--coords-repo",
                               self.coords, "--out", out])
            self.assertIn("floor", str(cm.exception))
            self.assertFalse(os.path.exists(out), "the refusal must happen BEFORE the write")
        finally:
            self.mod.MIN_DERIVED_ABS = 1

    def test_floor_ratchets_against_the_committed_table(self):
        """With a committed table present the floor is ITS derived count, not the absolute one."""
        out = os.path.join(self.tmp, "ratchet.tsv")
        self.mod.emit(out, [(1, "m60_40_40", [6800000], "volume:BoxVol")] * 1 +
                      [(i, "m60_40_40", [6800000], "volume:BoxVol") for i in range(2, 60)])
        with self.assertRaises(SystemExit) as cm:
            self.mod.main(["--emit", "--artifacts", self.artifacts, "--coords-repo", self.coords,
                           "--out", out])
        self.assertIn("floor 59", str(cm.exception))

    def test_help_warns_against_force(self):
        """--force exists to say a shrink is deliberate. The help text must say so, because the
        next reader under time pressure reads only the help text."""
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            self.mod.main(["--help"])
        text = " ".join(buf.getvalue().split())
        self.assertIn("deliberate", text)
        self.assertIn("red run green", text)

    # -- step 3: the calibration gate -----------------------------------------------------------
    def test_graces_mode_diffs_clean_against_a_fixture_ground(self):
        ground = os.path.join(self.tmp, "grace_ground.tsv")
        build_grace_fixtures(self.artifacts, ground)
        # The witness: a --graces that compared NOTHING would also return 0. Assert first that
        # there are graces on both sides and that every one of them derived a bucket.
        vols = self.mod.load_volumes_or_die(force=True)
        gg = _load(os.path.join(REPO, "tools", "datamine_grace_ground.py"), "_ipr_gg3")
        tile_ids, interior_ids = gg.load_play_region_defaults(
            os.path.join(self.artifacts, "vanilla_er", "vanilla_er", "PlayRegionParam.csv"))
        rows = self.mod.grace_rows(vols, tile_ids, interior_ids)
        self.assertEqual(len(rows), len(GRACES))
        self.assertEqual(len(self.mod.read_ground(ground)), len(GRACES))
        self.assertTrue(all(ids for _f, _m, ids, _s in rows), "a grace with no bucket to compare")
        self.assertEqual(0, self.mod.main(["--artifacts", self.artifacts, "--graces",
                                           "--ground", ground]),
                         "the same pipeline must reproduce the graces' committed buckets")

    def test_graces_mode_fails_on_a_bucket_mismatch(self):
        """The gate's own falsifier: a ground table that disagrees must exit NON-ZERO. Without
        this, a --graces that always returned 0 would read identically."""
        ground = os.path.join(self.tmp, "grace_ground_bad.tsv")
        build_grace_fixtures(self.artifacts, ground, mutate=True)
        self.assertEqual(1, self.mod.main(["--artifacts", self.artifacts, "--graces",
                                           "--ground", ground]))


if __name__ == "__main__":
    unittest.main()
