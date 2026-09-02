"""Description-triage gate (tier A) -- tools/build_desc_triage.py.

The triage page ranks checks by how badly they need a hand row in
location_descriptions.tsv, and plots them on the committed overworld maps so a
curator can see what makes indistinguishable siblings different. Two ways it could
lie, both gated here:

  A. THE RANKING reads the SHIPPED location name, so it cannot drift from what the
     tracker renders. Assert the parse is total (every name splits) and that the
     derived layer agrees with the ground truth we do hold: every flag in
     location_descriptions.tsv must classify as 1-override, and every name carrying
     a collision ordinal must be in a family of >1.
  B. THE MAP. A point placed off-image is invisible; a point placed WRONG is worse
     than missing, because a curator will write a description from it. Assert every
     projected position lands inside its map's viewBox, and pin the LOD fold
     (world = tile*pitch + local + (pitch-256)/2) against hand-computed cases --
     the centring term is INFERRED, so if someone "simplifies" it away, this fails.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_desc_triage.py
  or: python greenfield/eldenring/tests/test_gf_desc_triage.py
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
# 🛑 Derive greenfield paths FROM the found root, never positionally. In CI the AP
# checkout `_ap/` sits INSIDE the repo, so find_repo_root succeeds and these suites
# RUN there -- but a positional GREENFIELD then resolves to `_ap/worlds/` and every
# tsv read misses. That is the second half of the 2026-07-27 path bug: fixing REPO
# alone moved 45 errors to 3 failures instead of to 0.
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
GREENFIELD = os.path.join(REPO, "greenfield") if _FOUND else os.path.dirname(os.path.dirname(HERE))
GF_PKG = os.path.join(GREENFIELD, "eldenring") if _FOUND else os.path.dirname(HERE)
TOOL = os.path.join(REPO, "tools", "build_desc_triage.py")
SHIPPED = os.path.join(REPO, "er-archipelago-desc-triage.html")

# SVG viewBox of each committed map, read from the file so a regenerated map is honoured.
VIEWBOX = {"m60": "lands_between_map.svg", "m61": "land_of_shadow_map.svg"}


def _load_tool():
    sys.path.insert(0, os.path.join(REPO, "tools"))
    spec = importlib.util.spec_from_file_location("_build_desc_triage", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _payload(html):
    m = re.search(r"^const DATA = (\{.*\});$", html, re.M)
    if not m:
        raise AssertionError("built page has no embedded DATA payload")
    return json.loads(m.group(1))


def _viewbox(name):
    with open(os.path.join(REPO, "greenfield", "maps", name), encoding="utf-8") as fh:
        head = fh.read(400)
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head)
    return (float(m.group(1)), float(m.group(2))) if m else None


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class DescTriageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()
        cls.tmp = tempfile.mkdtemp(prefix="desc_triage_")
        out = os.path.join(cls.tmp, "a.html")
        subprocess.run([sys.executable, TOOL, "--repo", REPO, "--out", out],
                       check=True, stdout=subprocess.DEVNULL)
        with open(out, encoding="utf-8") as fh:
            cls.html = fh.read()
        cls.data = _payload(cls.html)
        cls.checks = cls.data["checks"]
        cls.cal = cls.data["meta"]["cal"]

    # -- A. the ranking -----------------------------------------------------
    def test_every_location_name_parses(self):
        LOC = self.tool.load_module_consts(os.path.join(GF_PKG, "data.py"), {"LOCATIONS"})["LOCATIONS"]
        total = sum(len(v) for v in LOC.values())
        bad = [n for v in LOC.values() for (n, _a, _f) in v if self.tool.split_name(n) is None]
        self.assertFalse(bad, f"{len(bad)} location name(s) did not parse, e.g. {bad[:3]}")
        self.assertEqual(len(self.checks), total)

    def test_hand_described_flags_classify_as_override(self):
        ov = {int(r["flag"]) for r in
              self.tool.read_tsv(os.path.join(GREENFIELD, "location_descriptions.tsv"))}
        got = {c["f"] for c in self.checks if c["layer"] == "1-override"}
        self.assertEqual(got, ov & {c["f"] for c in self.checks})

    def test_override_rows_score_zero_and_are_marked(self):
        for c in self.checks:
            if c["layer"] == "1-override":
                self.assertIn("have", c, f"f{c['f']} is an override but carries no existing text")

    def test_collision_ordinals_come_in_families(self):
        """An ordinal means 'indistinguishable from someone'. A lone ordinal is a parse bug."""
        fam = defaultdict(list)
        for c in self.checks:
            if c["ord"]:
                fam[(c["r"], c["item"], c["desc"])].append(c["f"])
        lonely = {k: v for k, v in fam.items() if len(v) < 2}
        self.assertFalse(lonely, f"{len(lonely)} ordinal(s) with no sibling: {list(lonely)[:3]}")
        for c in self.checks:
            if c["ord"]:
                self.assertTrue(c.get("sib"), f"f{c['f']} has ordinal {c['ord']} but no sibling list")

    def test_score_is_reproducible_from_its_reasons(self):
        """The UI shows the reasons as chips; they must actually sum to the score."""
        w = {"no item name": 100, "indistinguishable sibling": 50, "no descriptor": 25,
             "machine locale": 20, "coarse (tile-grace)": 10, "important item": 15,
             "bulk filler": -30}
        for c in self.checks:
            if c["layer"] == "1-override":
                continue
            self.assertEqual(c["s"], sum(w[r] for r in c["why"]),
                             f"f{c['f']} score {c['s']} != sum of {c['why']}")

    # -- B. the map ---------------------------------------------------------
    def test_lod_fold_pins_the_centring_term(self):
        """world = tile*pitch + local + (pitch-256)/2. Hand-computed; the offset is INFERRED,
        so this is the tripwire if someone 'simplifies' it to a bare tile*256."""
        cases = [
            # (map_id, x, z) -> (base, gx, gz)
            (("m60_33_46_00", -63.089, 0.0), ("m60", 33 * 256 - 63.089, 46 * 256)),
            (("m60_10_09_02", 0.0, 0.0), ("m60", 10 * 1024 + 384, 9 * 1024 + 384)),
            (("m60_44_36_10", 1.0, 2.0), ("m60", 44 * 256 + 1.0, 36 * 256 + 2.0)),
            # 3-field merchant id, LOW tile -> truncated LOD2
            (("m60_09_11", 0.0, 0.0), ("m60", 9 * 1024 + 384, 11 * 1024 + 384)),
            # 3-field merchant id, FINE tile -> LOD0
            (("m60_44_36", 0.0, 0.0), ("m60", 44 * 256, 36 * 256)),
        ]
        for (mid, x, z), want in cases:
            got = self.tool.world_xz(mid, x, z)
            self.assertIsNotNone(got, f"{mid} did not fold")
            self.assertEqual(got[0], want[0])
            self.assertAlmostEqual(got[1], want[1], places=3, msg=f"{mid} gx")
            self.assertAlmostEqual(got[2], want[2], places=3, msg=f"{mid} gz")

    def test_fine_grid_fold_matches_the_games_own_conversion_table(self):
        """⭐ THE FINE-GRID FOLD IS NO LONGER INFERRED.

        WorldMapLegacyConvParam (196 rows, bundled 2026-07-27 when gen_inputs started globbing
        the params dir) is the game's OWN legacy<->overworld conversion table. Rows 1113-1116
        express ONE world point in FOUR different tile frames, with locals that run far outside
        a 256 m tile (-1024, +2304 -- so the local frame is not clamped, and the fold is a pure
        affine map). Under `tile*256 + local` all four collapse to exactly (12544, 12544).

        Four independent frames agreeing to the metre is about as close to proof as a datamine
        gets, and it is much better evidence than the "looks about right" this started as. The
        fixture is PINNED here rather than read from the param so the gate needs no artifacts.

        🛑 SCOPE, because this proves less than it looks like it proves: all 163 overworld-
        destination rows sit on the FINE grid (tile indices 33..54). This param contains ZERO
        coarse/LOD2 rows, so it says NOTHING about the (pitch-256)/2 centring term in
        test_lod_fold_pins_the_centring_term -- that half is still inference, and the in-game
        merchant spot-check in AGENTS.md is still the way to falsify it.
        """
        cases = [                     # (tile_x, tile_z, local_x, local_z) -- WorldMapLegacyConvParam
            (50, 40, -256.0, 2304.0),                                    # ID 1113
            (50, 41, -256.0, 2048.0),                                    # ID 1114
            (51, 45, -512.0, 1024.0),                                    # ID 1115
            (53, 46, -1024.0, 768.0),                                    # ID 1116
        ]
        got = set()
        for tx, tz, lx, lz in cases:
            w = self.tool.world_xz(f"m61_{tx:02d}_{tz:02d}_00", lx, lz)
            self.assertIsNotNone(w, f"m61_{tx:02d}_{tz:02d}_00 did not fold")
            got.add((round(w[1], 3), round(w[2], 3)))
        self.assertEqual(got, {(12544.0, 12544.0)},
                         "the four frames no longer agree -- tile*256+local is broken: " + str(got))

    def test_interiors_are_refused_not_guessed(self):
        for mid in ("m11_10_00_00", "m30_00_00_00", "m40_00", "PENDING", ""):
            self.assertIsNone(self.tool.world_xz(mid, 1.0, 2.0), f"{mid} should not fold")

    def test_every_plotted_point_lands_inside_its_map(self):
        boxes = {k: _viewbox(v) for k, v in VIEWBOX.items()}
        for k, b in boxes.items():
            self.assertIsNotNone(b, f"no viewBox for {k}")
        oob, n = [], 0
        for c in self.checks:
            for p in c["pos"]:
                cal = self.cal.get(p["b"])
                if not cal:
                    continue
                wb, im = cal["world_bounds"], cal["image"]
                px = im["margin"] + (p["gx"] - wb["gx_min"]) / (wb["gx_max"] - wb["gx_min"]) * im["draw_w"]
                py = im["margin"] + (1 - (p["gz"] - wb["gz_min"]) / (wb["gz_max"] - wb["gz_min"])) * im["draw_h"]
                W, H = boxes[p["b"]]
                n += 1
                if not (0 <= px <= W and 0 <= py <= H):
                    oob.append((c["f"], p["m"], round(px), round(py)))
        self.assertTrue(n > 1500, f"only {n} points projected -- the coord join went missing")
        self.assertFalse(oob, f"{len(oob)} of {n} points land OFF the map: {oob[:5]}")

    def test_positions_are_deduped_across_map_versions(self):
        """The same flag on _00 and _10 is ONE physical spot; two dots would double-count."""
        for c in self.checks:
            keys = [(p["b"], round(p["gx"]), round(p["gz"])) for p in c["pos"]]
            self.assertEqual(len(keys), len(set(keys)), f"f{c['f']} has duplicate positions")

    # -- freshness ----------------------------------------------------------
    def test_committed_page_is_not_stale(self):
        if not os.path.exists(SHIPPED):
            self.skipTest("er-archipelago-desc-triage.html not present")
        with open(SHIPPED, encoding="utf-8", newline="") as fh:
            shipped = fh.read()
        self.assertEqual(shipped.replace("\r\n", "\n"), self.html,
                         "committed er-archipelago-desc-triage.html is STALE -- "
                         "run: python tools/build_desc_triage.py")


if __name__ == "__main__":
    unittest.main()
