"""The overworld tile frame is CENTRE-ORIGIN, and the committed grace grounds prove it.

WHAT BROKE (2026-08-26). `tools/datamine_item_play_regions.py --graces` -- the calibration gate the
item scan must pass before any of its answers may be believed -- REFUSED on Alaric's box with
bucket mismatches that pointed in OPPOSITE directions:

    grace 76416 (m60_49_39_00): committed [] (none)  vs here [64010] (tile-default)
    grace 76420 (m60_51_36_00): committed [64000] (tile-default) vs here [] (none)

Neither tool had touched a volume for those two. The disagreement was PURE TABLE LOOKUP: which
PlayRegionParam (gridXNo, gridZNo) row governs the point. `datamine_grace_ground` used the grace's
AUTHORED tile; `datamine_item_play_regions._fine_tile` recomputed one as `floor(world / 256)`.

`floor` is the bug, and the params say so out loud. The overworld tile's local coordinate frame is
centred on the tile, not cornered on it:

  * BonfireWarpParam's 225 overworld graces carry 450 local axis values. 438 (97.3%) lie in
    [-128, 128). Only 227 (50.4%) lie in [0, 256) -- and 222 are NEGATIVE, which a corner origin
    cannot produce.
  * greenfield/item_grace_coords.tsv's overworld placements: 4732 of 5010 (94.5%) in [-128, 128).

So tile t owns [t*256 - 128, t*256 + 128), `overworld_fold.fine_tile` rounds, and 2053 of 2768
overworld item placements had been reading the wrong tile's default.

THIS SUITE is the population-wide witness, and it needs NO MSB corpus: for every overworld grace
whose committed ground came from a tile default (or from nothing at all), the answer is a pure
function of BonfireWarpParam + PlayRegionParam, both of which ride in gen_inputs.db. Rows whose
committed source is a VOLUME are not judged here -- a volume outranks the default and the geometry
that decides it is not in the bundle. tests/test_gf_item_play_regions.py witnesses the volume half
on synthetic fixtures.

Repo-only (it reads gen_inputs.db and tools/), so it is ledgered under GENERATORS.
"""
import csv
import importlib.util
import io
import os
import sqlite3
import sys
import unittest
import zlib

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

# The two graces from the refusal, pinned by NAME so a regression names itself. (flag, tile the
# point stands on, expected buckets.) 76416 spills nowhere -- its own tile 49/38... is what `floor`
# claimed; centred, it stands on 49/39, which has NO PlayRegionParam row, so its ground is
# UNDERIVABLE. 76420 stands on 51/36, whose row is 6400002 -> bucket 64000.
PINNED = {76416: ((49, 39), ()),
          76420: ((51, 36), (64000,))}

# The five committed rows the fix MOVED, and the only rows in the table it moved. Each is a genuine
# SPILLER: its local coordinate runs past +-128, so the point physically stands on the neighbouring
# tile and the neighbour's default is the one the engine reads. Every one of them had `tile-default`
# or `none` as its committed source, i.e. no volume ruled on it, so the new value follows from the
# params alone -- which is what this suite re-derives.
# NOTE (2026-08-26, the shared-ladder change): `datamine_grace_ground` gained the OVERWORLD seam
# step, so a regenerated table will move 76214 -- and 76453 / 76500, which are not spillers -- off
# `none` and onto `seam:` with a real bucket. A seam answer comes from a VOLUME FACE and cannot be
# re-derived from the params alone, so every assertion below that reads the COMMITTED bucket is
# gated on the row still being params-derivable (see `_params_derivable`). The tile-frame half --
# which tile the point stands on, and what that tile's default is -- is unaffected by the seam
# step and stays asserted for all five.
SPILLERS = {76214: ((35, 49), ()),
            76236: ((36, 44), (62000,)),
            76304: ((40, 53), (63000,)),
            76905: ((51, 46), (69020,)),
            76936: ((52, 48), (69300,))}


def _bundle_csv(db, name):
    """One params CSV out of gen_inputs.db (files(path, ..., blob) of zlib'd bytes)."""
    con = sqlite3.connect(db)
    try:
        row = con.execute("SELECT blob FROM files WHERE path LIKE ?", ("%" + name,)).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    return zlib.decompress(row[0]).decode("utf-8-sig")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class GraceTileFrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if REPO is None:
            raise unittest.SkipTest(REPO_ONLY_REASON)
        db = os.path.join(REPO, "gen_inputs.db")
        ground = os.path.join(REPO, "greenfield", "grace_ground.tsv")
        if not os.path.isfile(db) or not os.path.isfile(ground):
            raise unittest.SkipTest("gen_inputs.db / grace_ground.tsv absent")
        bwp = _bundle_csv(db, "BonfireWarpParam.csv")
        prp = _bundle_csv(db, "PlayRegionParam.csv")
        if not bwp or not prp:
            raise unittest.SkipTest("the params are not in this gen_inputs.db")
        cls.fold = _load(os.path.join(REPO, "tools", "overworld_fold.py"), "_otf_frame")

        cls.tile_ids = {60: {}, 61: {}}
        for r in csv.DictReader(io.StringIO(prp)):
            a = int(r["areaNo"] or 0)
            if a in (60, 61):
                key = (int(r["gridXNo"]), int(r["gridZNo"]))
                cls.tile_ids[a].setdefault(key, set()).add(int(r["ID"]) // 100)

        cls.graces = {}                    # flag -> (area, authored tile, local x/z)
        for r in csv.DictReader(io.StringIO(bwp)):
            try:
                f = int(r["eventflagId"] or 0)
            except ValueError:
                continue
            a = int(r["areaNo"] or 0)
            if not (71000 <= f <= 76999) or a not in (60, 61):
                continue
            cls.graces[f] = (a, (int(r["gridXNo"]), int(r["gridZNo"])),
                             (float(r["posX"]), float(r["posZ"])))

        cls.committed = {}                 # flag -> (buckets, source)
        with open(ground, encoding="utf-8-sig") as fh:
            body = [ln for ln in fh if not ln.startswith("#") and ln.strip()]
        for r in csv.DictReader(body, delimiter="\t"):
            bks = tuple(int(b) for b in r["ground_buckets"].split(";") if b.strip() and b != "-")
            cls.committed[int(r["grace_flag"])] = (bks, r["source"])

    def _standing_tile(self, flag):
        a, (tx, tz), (x, z) = self.graces[flag]
        return a, self.fold.fine_tile(tx * 256 + x, tz * 256 + z)

    @staticmethod
    def _params_derivable(src):
        """Is this committed row re-derivable from PlayRegionParam ALONE?

        No, if a VOLUME decided it (`volume:`), a volume FACE decided it (`seam:` -- the overworld
        seam step, 2026-08-26), or the ENGINE decided it (`measured:`). This suite is the
        corpus-FREE half of the `--graces` gate: it must never start demanding rows whose answer
        lives in the MSBs, and it must not go red when a regen legitimately moves a row from
        `none`/`tile-default` INTO the seam population -- leaving this population is not drift.
        """
        return not src.startswith(("volume:", "seam:", "measured:"))

    def _default(self, area, tile):
        return tuple(sorted(self.tile_ids[area].get(tile, ())))

    def test_the_local_frame_is_centred_not_cornered(self):
        """THE PREMISE, measured rather than asserted. If the local origin were the tile CORNER,
        every local would be in [0, 256) and none would be negative."""
        vals = [v for f in self.graces for v in self.graces[f][2]]
        centred = sum(1 for v in vals if -128 <= v < 128)
        cornered = sum(1 for v in vals if 0 <= v < 256)
        negative = sum(1 for v in vals if v < 0)
        self.assertGreater(centred, 0.95 * len(vals),
                           "%d/%d locals in [-128,128) -- the centred frame stopped holding"
                           % (centred, len(vals)))
        self.assertGreater(centred, cornered + 100,
                           "centred %d vs cornered %d: the two framings stopped being separable"
                           % (centred, cornered))
        self.assertGreater(negative, 100,
                           "only %d negative locals -- a corner origin would explain that, and this"
                           " whole ruling would need re-deriving" % negative)

    def test_folding_a_grace_returns_its_own_tile_far_more_often_than_floor_does(self):
        """The round-trip, both ways, as ONE comparison: fold the grace, re-derive its tile. Under
        the centred rule 214 of 225 come back to their own authored tile; under `floor` 53 do."""
        import math
        rounded = floored = 0
        for f, (a, auth, (x, z)) in self.graces.items():
            gx, gz = auth[0] * 256 + x, auth[1] * 256 + z
            rounded += self.fold.fine_tile(gx, gz) == auth
            floored += (int(math.floor(gx / 256.0)), int(math.floor(gz / 256.0))) == auth
        self.assertGreater(rounded, 200, "only %d/%d graces round back onto their own tile"
                           % (rounded, len(self.graces)))
        self.assertLess(floored, rounded // 2,
                        "floor came back %d/%d and round %d/%d -- they are no longer telling the "
                        "two framings apart" % (floored, len(self.graces), rounded, len(self.graces)))

    def test_the_two_graces_that_refused_the_calibration_gate(self):
        """⭐ THE MOTIVATING CASE (rule 11): 76416 and 76420, the pair in Alaric's refusal, in
        OPPOSITE directions. Both must now answer the same thing in both tools, which means: the
        tile they stand on is their AUTHORED tile, and its default is what the committed table
        says."""
        for f, (want_tile, want_bks) in PINNED.items():
            with self.subTest(grace=f):
                a, tile = self._standing_tile(f)
                self.assertEqual(tile, want_tile, "grace %d stands on the wrong tile" % f)
                self.assertEqual(self._default(a, tile), want_bks)
                if self._params_derivable(self.committed[f][1]):
                    self.assertEqual(self.committed[f][0], want_bks,
                                     "grace_ground.tsv disagrees with the params for %d" % f)

    def test_the_five_spillers_the_fix_moved(self):
        """The rows the centred rule genuinely CHANGES: local past +-128, so the grace stands on a
        neighbour. Pinned so a future regen that quietly reverts them is loud."""
        for f, (want_tile, want_bks) in SPILLERS.items():
            with self.subTest(grace=f):
                a, tile = self._standing_tile(f)
                self.assertEqual(tile, want_tile)
                self.assertNotEqual(tile, self.graces[f][1],
                                    "grace %d stopped being a spiller" % f)
                self.assertEqual(self._default(a, tile), want_bks)
                if self._params_derivable(self.committed[f][1]):
                    self.assertEqual(self.committed[f][0], want_bks)

    def test_every_committed_tile_default_row_re_derives_from_the_params(self):
        """THE POPULATION, not a sample. Every overworld grace whose committed source is a tile
        default or nothing must equal the default of the tile it STANDS on. This is the gate
        `--graces` runs on Alaric's box, minus the half it needs the MSB corpus for -- so a table
        that drifts from the transform reds in CI instead of on his box."""
        bad = []
        judged = 0
        for f, (bks, src) in sorted(self.committed.items()):
            if f not in self.graces or not self._params_derivable(src):
                continue
            judged += 1
            a, tile = self._standing_tile(f)
            want = self._default(a, tile)
            if want != bks:
                bad.append("  grace %d: committed %s, tile %s default %s"
                           % (f, list(bks) or "-", tile, list(want) or "-"))
        self.assertGreater(judged, 150, "only %d rows judged -- the population moved" % judged)
        self.assertFalse(bad, "%d committed grace ground(s) do not follow from the tile frame; "
                              "re-run tools/datamine_grace_ground.py --emit:\n%s"
                              % (len(bad), "\n".join(bad[:40])))


if __name__ == "__main__":
    unittest.main()
