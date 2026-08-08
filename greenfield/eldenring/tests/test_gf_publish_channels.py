#!/usr/bin/env python3
"""The publish surface: the apworld packer agrees with build.ps1, and the channel ledger is sound.

REPO-ONLY (tools/ + release/ + build.ps1 are not installed beside the world), so this is a
GENERATORS suite with a __main__ entry point.

WHY THE PACKER NEEDS A TEST AT ALL. `tools/build_apworld.py` is a SECOND builder of the same
artifact -- `build.ps1 -Apworld` is the first, and it is the one that cuts releases. Two builders is
two chances to disagree, and the disagreement would be silent: both produce a zip that installs, and
the difference would be a file that shipped to players or one that did not. So the exclusion lists
are asserted equal by reading them out of the PowerShell source. If either side changes, this reds
instead of drifting.
"""
import ast
import os
import re
import subprocess
import sys
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
# 🛑 NOT `dirname(dirname(dirname(HERE)))`. gf_test.py copies this package into an AP checkout with
# no tools/ beside it, where the positional walk lands on the AP root and every path below silently
# points at the wrong tree. `_util.find_repo_root` looks for a marker instead, and there is a gate
# (test_gf_data.py::RepoRootIsNeverDerivedPositionally) that reds on the idiom -- it caught this file.
sys.path.insert(0, HERE)
from _util import find_repo_root  # noqa: E402

REPO = find_repo_root(HERE)
TOOLS = os.path.join(REPO, "tools") if REPO else None
BUILD_PS1 = os.path.join(REPO, "build.ps1") if REPO else None
REPO_ONLY = "needs the repo tree (tools/, build.ps1, release/); not installed beside the world"
HAVE_REPO = bool(REPO) and os.path.isfile(BUILD_PS1) and os.path.isdir(TOOLS)


def _load(name):
    sys.path.insert(0, TOOLS)
    try:
        return __import__(name)
    finally:
        sys.path.pop(0)


def _ps1_list(var):
    """The @('a','b') array literal assigned to $var in build.ps1, as a python list."""
    src = open(BUILD_PS1, encoding="utf-8", errors="replace").read()
    m = re.search(r"\$" + var + r"\s*=\s*@\(([^)]*)\)", src)
    if not m:
        return None
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]


@unittest.skipUnless(HAVE_REPO, REPO_ONLY)
class ApworldPacker(unittest.TestCase):
    def test_exclusions_match_build_ps1(self):
        """🛑 THE ONE THAT MATTERS. build.ps1 is the release packer; this must pack the same set."""
        bp = _load("build_apworld")
        for var, ours in (("excludeName", bp.EXCLUDE_GLOB), ("excludeExact", bp.EXCLUDE_EXACT)):
            theirs = _ps1_list(var)
            self.assertIsNotNone(theirs, f"build.ps1 no longer defines ${var} -- the parity check "
                                         f"has gone blind; re-point it at whatever replaced it")
            self.assertTrue(theirs, f"${var} parsed empty from build.ps1")
            self.assertEqual(sorted(theirs), sorted(ours),
                             f"tools/build_apworld.py and build.ps1 ${var} disagree -- one of them "
                             f"would ship a file the other drops, and nothing else would say so")

    def test_pack_is_deterministic_and_rooted(self):
        bp = _load("build_apworld")
        rels = bp.members()
        self.assertTrue(rels, "nothing to pack")
        self.assertIn("archipelago.json", rels, "the manifest must be in the pack")
        self.assertIn("__init__.py", rels)
        self.assertEqual(rels, sorted(rels), "member order must be sorted (half of determinism)")
        for r in rels:
            self.assertFalse(r.endswith(".pyc"), r)
            self.assertNotIn("__pycache__", r, r)
            self.assertNotEqual(os.path.basename(r), "region_map.csv",
                                "region_map.csv is a gen INPUT copied in for the tests; shipping it "
                                "would put a test fixture in a player's download")

    def test_built_zip_has_the_ap_inner_root(self):
        """AP looks for worlds/<name>/__init__.py inside the archive; a flat zip installs to nothing."""
        import tempfile
        bp = _load("build_apworld")
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "eldenring.apworld")
            bp.build(out)
            with zipfile.ZipFile(out) as z:
                names = z.namelist()
                first = open(out, "rb").read()
            self.assertTrue(all(n.startswith("eldenring/") for n in names),
                            "every entry must sit under the eldenring/ inner root")
            self.assertIn("eldenring/archipelago.json", names)
            # rebuild and compare bytes -- a non-deterministic artifact makes "did it change?"
            # unanswerable, and a release job cannot verify what it cannot compare.
            bp.build(out)
            self.assertEqual(first, open(out, "rb").read(), "the pack is not byte-reproducible")


@unittest.skipUnless(HAVE_REPO, REPO_ONLY)
class ChannelLedger(unittest.TestCase):
    def test_ledger_passes_its_own_gate(self):
        # WITNESS: an empty ledger passes every rule vacuously, so assert it has rows before
        # asserting they are good. Both channels must be present or the pointer points nowhere.
        cc = _load("check_channels")
        channels = {r[1] for r in cc.rows() if not r[4]}
        self.assertEqual(channels, set(cc.CHANNELS),
                         "the ledger must carry a row for every channel")
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "check_channels.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_tag_independent_violation_is_caught_at_any_checkout_depth(self):
        """The one rule that must hold even in a shallow checkout: `stable` may not name a moving
        ref. Kept separate from the tag-existence case so at least one negative is depth-proof."""
        cc = _load("check_channels")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("stable\tmain\t2026-01-01\tbogus\nbeta\tmain\t2026-01-02\t\n")
            path = f.name
        try:
            bad = cc.check(path, tags=set())
            self.assertTrue(any("only `beta`" in b for b in bad), bad)
        finally:
            os.unlink(path)

    def test_the_gate_can_actually_fail(self):
        """⭐ A gate nobody has watched fail is a gate nobody knows the shape of. Feed it a ledger
        naming a tag that does not exist and require a finding -- the failure this file exists for
        is a typo'd pointer, which parses fine and looks right."""
        cc = _load("check_channels")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("stable\tv9.9.9-not-a-tag\t2026-01-01\tbogus\nbeta\tmain\t2026-01-02\t\n")
            path = f.name
        try:
            # 🛑 TAGS ARE INJECTED, NOT TAKEN FROM THE CHECKOUT. This test passed locally and went
            # RED IN CI on 2026-08-08 for the opposite reason to the obvious one: the `tests` job
            # checks out shallow, so `git tag -l` returned nothing, the gate took its
            # no-tags-so-skip branch, found no fault, and the NEGATIVE test failed. A negative case
            # that depends on checkout depth is testing the runner, not the gate.
            bad = cc.check(path, tags={"v0.3.7"})
            self.assertTrue(bad, "the gate accepted a ledger pointing at a nonexistent tag")
            # ...and the shallow branch must be a SKIP, not a pass-by-accident that looks the same.
            self.assertFalse([b for b in cc.check(path, tags=set()) if "not a tag" in b],
                             "with no tags available the existence check must stand down, not "
                             "invent a verdict")
        finally:
            os.unlink(path)

    def test_channels_are_named_in_the_spec(self):
        spec = os.path.join(REPO, "SPEC-publishing-pipeline.md")
        self.assertTrue(os.path.isfile(spec), "the spec that explains the ledger is missing")
        text = open(spec, encoding="utf-8").read()
        self.assertIn("CHANNELS.tsv", text,
                      "the ledger exists but nothing explains it -- CONTRIBUTING rule 14")


if __name__ == "__main__":
    unittest.main()
