"""Check-browser gate (tier A) -- tools/build_check_browser.py.

The browser is a READING tool for the check corpus, so its only real failure mode is
LYING: showing a set of checks, tags or counts that the world does not actually define.
A reader that silently drops rows is worse than no reader, because it is then used to
reason about coverage. This gate asserts the join is total and the shipped page is fresh:

  A. TOTALITY -- every (name, ap_id, flag) in data.LOCATIONS appears exactly once in the
     page payload, and the payload contains nothing else. A join that drops or duplicates
     rows fails here rather than being discovered by eye.
  B. AGREEMENT -- the tag histogram recomputed from the payload equals location_tags.
     TAG_COUNTS, and every missable ap_id is carried. This is the same cross-check that
     caught nothing when written, and is exactly what a future tag rename would break.
  C. DETERMINISM -- two builds from the same inputs are byte-identical. Required, because
     the CI `generators` job gates on a git diff of the committed output; a nondeterministic
     build (dict order, a git hash, CRLF) would make that gate permanently red.
  D. FRESHNESS -- the committed er-archipelago-check-browser.html equals a fresh build.
     Catches "changed the data, never regenerated the page".

AP-FREE: the tool reads the generated modules with ast, never imports them, so this test
needs no Archipelago on sys.path and runs in the bare sandbox.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_check_browser.py
  or: python greenfield/eldenring/tests/test_gf_check_browser.py
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
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                       # .../greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)                 # .../greenfield
# Resolve the checkout by MARKER, never positionally: under tools/gf_test.py this file
# lives at _ap/worlds/eldenring/tests and a positional walk-up yields `_ap`, which has no
# tools/. See _util.find_repo_root -- this is the bug that errored 45 tests in CI.
REPO = find_repo_root(HERE) or os.path.dirname(GREENFIELD)
RUNNING_FROM_REPO = find_repo_root(HERE) is not None                   # .../er-archipelago
TOOL = os.path.join(REPO, "tools", "build_check_browser.py")
SHIPPED = os.path.join(REPO, "er-archipelago-check-browser.html")


def _load_tool():
    spec = importlib.util.spec_from_file_location("_build_check_browser", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _payload(html):
    """Pull the embedded JSON back out of a built page."""
    m = re.search(r"^const DATA = (\{.*\});$", html, re.M)
    if not m:
        raise AssertionError("built page has no embedded DATA payload")
    return json.loads(m.group(1))


def _build(out_path):
    subprocess.run([sys.executable, TOOL, "--repo", REPO, "--out", out_path],
                   check=True, stdout=subprocess.DEVNULL)
    with open(out_path, encoding="utf-8") as fh:
        return fh.read()


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class CheckBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()
        cls.tmp = tempfile.mkdtemp(prefix="check_browser_")
        cls.html = _build(os.path.join(cls.tmp, "a.html"))
        cls.data = _payload(cls.html)
        cls.checks = cls.data["checks"]
        consts = cls.tool.load_module_consts(
            os.path.join(GF_PKG, "data.py"), {"LOCATIONS"})
        cls.LOCATIONS = consts["LOCATIONS"]

    # -- A. totality ------------------------------------------------------
    def test_every_location_present_exactly_once(self):
        want = {(a, f, r) for r, v in self.LOCATIONS.items() for (_n, a, f) in v}
        got = Counter((c["id"], c["f"], c["r"]) for c in self.checks)
        dupes = {k: n for k, n in got.items() if n > 1}
        self.assertFalse(dupes, f"payload duplicates {len(dupes)} check(s): {list(dupes)[:5]}")
        missing = want - set(got)
        extra = set(got) - want
        self.assertFalse(missing, f"{len(missing)} location(s) dropped by the join: {sorted(missing)[:5]}")
        self.assertFalse(extra, f"{len(extra)} check(s) invented by the join: {sorted(extra)[:5]}")

    def test_meta_total_matches(self):
        self.assertEqual(self.data["meta"]["total"], len(self.checks))
        self.assertEqual(len(self.checks), sum(len(v) for v in self.LOCATIONS.values()))

    # -- B. agreement with the generated modules ---------------------------
    def test_tag_histogram_matches_TAG_COUNTS(self):
        declared = self.tool.load_module_consts(
            os.path.join(GF_PKG, "location_tags.py"), {"TAG_COUNTS"})["TAG_COUNTS"]
        got = Counter(t for c in self.checks for t in c["t"])
        self.assertEqual(dict(sorted(got.items())), dict(sorted(declared.items())))

    def test_every_missable_is_carried(self):
        declared = self.tool.load_module_consts(
            os.path.join(GF_PKG, "missable_locations.py"), {"MISSABLE_LOCATIONS"})["MISSABLE_LOCATIONS"]
        got = {c["id"]: c["miss"] for c in self.checks if "miss" in c}
        self.assertEqual(got, dict(declared))

    def test_stamp_is_the_data_inputs_hash_not_a_commit(self):
        stamp = self.data["meta"]["stamp"]
        self.assertTrue(stamp.startswith("sha256:"), f"stamp is not a content hash: {stamp!r}")
        self.assertEqual(stamp, self.tool.data_stamp(os.path.join(GF_PKG, "data.py")))

    # -- C. determinism ----------------------------------------------------
    def test_two_builds_are_byte_identical(self):
        again = _build(os.path.join(self.tmp, "b.html"))
        self.assertEqual(len(again), len(self.html), "build length is nondeterministic")
        self.assertEqual(again, self.html, "build is nondeterministic -- the CI diff gate cannot hold")

    def test_output_has_no_crlf(self):
        self.assertNotIn("\r\n", self.html, "build wrote CRLF; CI regen on Linux would diff")

    # -- E. gate evidence is PLURAL ----------------------------------------
    # The page previously showed only lot_gates, teaching the reader "110 of 4879 checks
    # are gated". Four corpora document gating and their union is 684. These gates keep
    # the other three joined AND keep their caveats in the payload, because a UI that
    # flattens NO_ENTITY_HANDLE ("proof of no gating") into "gated: unknown" inverts it.
    def test_all_four_gate_corpora_reach_the_payload(self):
        for key, tsv in (("gates", "lot_gates.tsv"), ("enab", "treasure_enablers.tsv"),
                         ("gift", "esd_gifts.tsv"), ("eshop", "esd_gates.tsv")):
            n = sum(1 for c in self.checks if c.get(key))
            self.assertTrue(n > 0, f"no check carries {key} -- the {tsv} join is broken")

    def test_enabler_join_matches_the_tsv(self):
        """treasure_enablers.tsv states its own distinct-check count in its header."""
        rows = self.tool.read_tsv(os.path.join(GREENFIELD, "treasure_enablers.tsv"))
        want = {int(r["flag"]) for r in rows if r.get("flag", "").isdigit()}
        got = {c["f"] for c in self.checks if c.get("enab")}
        self.assertEqual(got, want & {c["f"] for c in self.checks})

    def test_enabler_verdicts_are_carried_verbatim(self):
        """Never normalise a verdict string: the UI facets on it and the caveat text
        explains it by that exact name."""
        rows = self.tool.read_tsv(os.path.join(GREENFIELD, "treasure_enablers.tsv"))
        want = {r["verdict"] for r in rows if r.get("verdict")}
        got = {e["verdict"] for c in self.checks for e in c.get("enab", []) if e["verdict"]}
        self.assertEqual(got, want)
        self.assertIn("NO_ENTITY_HANDLE", got, "the 'proof of no gating' verdict vanished")

    def test_caveat_headers_are_present_and_not_paraphrased(self):
        cav = self.data["meta"]["caveats"]
        for k in ("treasure_enablers", "esd_gates", "esd_gifts", "msb_gated_treasures", "lot_gates"):
            self.assertTrue(cav.get(k, "").strip(), f"no caveat text carried for {k}")
        # the specific warnings that stop a misread -- if the header is reworded, re-check the UI
        self.assertIn("NO_ENTITY_HANDLE", cav["treasure_enablers"])
        self.assertIn("POLARITY IS NOT ENCODED", cav["treasure_enablers"])
        self.assertIn("NOT A RISK LIST", cav["msb_gated_treasures"].upper())

    def test_gate_union_is_not_a_sum(self):
        """The corpora overlap; the footer shows a union. If this ever equals the sum,
        someone has double-counted."""
        m = self.data["meta"]
        parts = m["gate_lot"] + m["gate_enabler"] + m["gate_gift"] + m["gate_eshop"]
        self.assertLessEqual(m["gate_any"], parts)
        self.assertGreater(m["gate_any"], m["gate_lot"],
                           "union is no bigger than lot_gates alone -- the new joins are inert")

    # -- F. negative space --------------------------------------------------
    def test_residuals_are_present_and_disjoint_from_checks(self):
        res = self.data["residuals"]
        self.assertTrue(len(res) > 0)
        check_flags = {c["f"] for c in self.checks}
        bad = [r for r in res if r["k"].startswith("itemlot") and r["f"] in check_flags]
        self.assertFalse(bad, f"{len(bad)} residual(s) are actually checks: {bad[:3]}")

    def test_residual_reasons_are_recorded_or_honestly_blank(self):
        """A fabricated reason is the disease this view exists to cure. Blank is allowed;
        a non-string is not."""
        for r in self.data["residuals"]:
            self.assertIsInstance(r["reason"], str)

    # -- G. the map tab ----------------------------------------------------
    # A point placed off-image is invisible; a point placed WRONG is worse, because the
    # map is used to eyeball misregioned checks and a wrong dot invents an outlier.
    def test_every_plotted_point_lands_inside_its_map(self):
        cal = self.data["meta"]["cal"]
        self.assertTrue(cal, "no calibration carried -- the map tab has nothing to project with")
        boxes = {}
        for key, svg in (("m60", "lands_between_map.svg"), ("m61", "land_of_shadow_map.svg")):
            with open(os.path.join(REPO, "poptracker", "maps", svg), encoding="utf-8") as fh:
                m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', fh.read(400))
            boxes[key] = (float(m.group(1)), float(m.group(2)))
        oob, n = [], 0
        for c in self.checks:
            for p in c.get("pos", []):
                k = cal.get(p["b"])
                if not k:
                    continue
                wb, im = k["world_bounds"], k["image"]
                px = im["margin"] + (p["gx"] - wb["gx_min"]) / (wb["gx_max"] - wb["gx_min"]) * im["draw_w"]
                py = im["margin"] + (1 - (p["gz"] - wb["gz_min"]) / (wb["gz_max"] - wb["gz_min"])) * im["draw_h"]
                W, H = boxes[p["b"]]
                n += 1
                if not (0 <= px <= W and 0 <= py <= H):
                    oob.append((c["f"], p["b"], round(px), round(py)))
        self.assertTrue(n > 1500, f"only {n} points -- the coord join went missing")
        self.assertFalse(oob, f"{len(oob)} of {n} points land OFF the map: {oob[:5]}")

    def test_dlc_calibration_is_not_the_base_one(self):
        """m61 has its own bounds and draw_h. Projecting DLC through the base transform
        would put every Shadow-Realm check in the sea, plausibly enough to be believed."""
        cal = self.data["meta"]["cal"]
        self.assertIn("m61", cal)
        self.assertNotEqual(cal["m60"]["world_bounds"], cal["m61"]["world_bounds"])

    def test_map_positions_are_deduped_across_map_versions(self):
        for c in self.checks:
            keys = [(p["b"], round(p["gx"]), round(p["gz"])) for p in c.get("pos", [])]
            self.assertEqual(len(keys), len(set(keys)), f"f{c['f']} has duplicate positions")

    def test_plottable_count_matches_the_payload(self):
        self.assertEqual(self.data["meta"]["plottable"],
                         sum(1 for c in self.checks if c.get("pos")))
        # the map must NOT silently imply full spatial coverage
        self.assertLess(self.data["meta"]["plottable"], self.data["meta"]["total"],
                        "every check claims a position -- interiors should have none")

    def test_both_maps_are_inlined(self):
        """The page is offline; an <img src> or a CDN would make the map tab blank."""
        for token in ("lands_between", "land_of_shadow"):
            self.assertIn(token, self.html, f"{token} map not inlined")
        self.assertNotIn("cdnjs", self.html)
        self.assertNotIn("<img", self.html)

    # -- H. diff mode is a REVIEW AID, not a gate --------------------------
    def test_payload_is_reparseable_by_the_diff_loader(self):
        """Diff mode re-extracts a payload from another build with this exact regex; if
        the emitted shape ever stops matching it, diff silently loads nothing."""
        m = re.search(r"^const DATA = (\{.*\});$", self.html, re.M)
        self.assertIsNotNone(m, "diff mode's loader regex no longer matches our own output")
        again = json.loads(m.group(1))
        self.assertEqual(len(again["checks"]), len(self.checks))
        for k in ("id", "r", "n", "t", "f", "g"):
            self.assertIn(k, again["checks"][0], f"diff keys on {k}; it left the payload")

    def test_diff_mode_is_labelled_as_not_a_gate(self):
        self.assertIn("review aid", self.html)
        self.assertIn("not a gate", self.html)

    # -- D. freshness ------------------------------------------------------
    def test_committed_page_is_not_stale(self):
        if not os.path.exists(SHIPPED):
            self.skipTest("er-archipelago-check-browser.html not present")
        with open(SHIPPED, encoding="utf-8", newline="") as fh:
            shipped = fh.read()
        self.assertEqual(
            shipped.replace("\r\n", "\n"), self.html,
            "committed er-archipelago-check-browser.html is STALE -- "
            "run: python tools/build_check_browser.py")


if __name__ == "__main__":
    unittest.main()
