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
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                       # .../greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)                 # .../greenfield
REPO = os.path.dirname(GREENFIELD)                   # .../er-archipelago
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
