"""`--path <artifacts-root>` -- every corpus-reading tool takes the SAME flag, and it MOVES the root.

WHY THIS SUITE EXISTS. The extracted `elden_ring_artifacts/` corpus is licensing-restricted and
.gitignore'd, so it lives wherever its owner keeps it -- and when it moved, nine tools that had
hardcoded `<repo>/elden_ring_artifacts` all had to be edited. `--path` is the one flag that
relocates it; `tools/artifacts_root.py` is the one implementation.

Two things can rot, and each has its own test here:

  * a tool grows/keeps a private spelling (or none at all), so the runbook's commands stop being
    uniform -- the CENSUS test pins the list of tools that must expose `--path`, and pins the three
    that must ALSO still accept `--artifacts`, because docs/PLAYAREA-ITEM-SCAN.md's commands and
    test_gf_item_play_regions.py both spell it that way;
  * a tool PARSES the flag and keeps reading the old root. That is the dangerous half: a scan
    pointed at a moved corpus that silently reads nothing still writes a plausible table. So every
    tool's `_set_artifacts_root` seam is CALLED here and its module globals are asserted to live
    under the new root -- a flag that parses is not a root that moved.

Repo-only by construction (it loads tools/ scripts by path), so it is ledgered in
tools/gf_suite_ledger.py under GENERATORS.
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

# tool -> (globals that must move under the new root, does it ALSO accept --artifacts?)
# The globals are named, not discovered: "some global moved" is not the claim -- THESE inputs move.
CENSUS = {
    "datamine_grace_ground":       (("AR", "BWP", "PRP", "MAPDIR"), True),
    "datamine_item_grace_coords":  (("AR", "VV"), True),
    "datamine_msb_item_regions":   (("ART", "VV", "EVT"), True),
    "datamine_arena_graces":       (("AR", "EVENT"), False),
    "datamine_merchant_shops":     (("ART", "VV", "TALK"), False),
    "datamine_dungeon_regions":    (("ART",), False),
}
# These two take --path but own no `_set_artifacts_root` seam: the root is one argparse default
# away from the directory they walk, so the flag is asserted through --help + the resolved default
# only. `datamine_item_play_regions` re-roots through datamine_grace_ground's seam, tested above
# and end-to-end in test_gf_item_play_regions.
FLAG_ONLY = {
    "datamine_msb_gated_treasures": False,  # value: does --artifacts work too?
    "probe_msb_mapversions": False,
    "datamine_item_play_regions": True,
}


def _load(name):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location("_apath_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _help(name):
    out = subprocess.run([sys.executable, os.path.join(TOOLS, name + ".py"), "--help"],
                         capture_output=True, text=True, timeout=180)
    return out.returncode, (out.stdout or "") + (out.stderr or "")


class ArtifactsPathFlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TOOLS is None or not os.path.isdir(TOOLS):
            raise unittest.SkipTest(REPO_ONLY_REASON)
        sys.path.insert(0, TOOLS)
        cls.ar = _load("artifacts_root")

    # ---- the shared helper --------------------------------------------------------------------
    def test_default_root_is_unchanged(self):
        self.assertEqual(os.path.join("/repo", "elden_ring_artifacts"),
                         self.ar.default_root("/repo"))

    def test_resolve_keeps_the_default_when_the_flag_is_absent(self):
        self.assertIsNone(self.ar.resolve(None))
        self.assertIsNone(self.ar.resolve(""))

    def test_resolve_refuses_a_root_that_is_not_a_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(os.path.abspath(tmp), self.ar.resolve(tmp))
            with self.assertRaises(SystemExit):
                self.ar.resolve(os.path.join(tmp, "no-such-corpus"))

    def test_there_is_no_env_var_fallback(self):
        # Deliberate: an invisible input is how a scan reads a STALE corpus and writes a plausible
        # table. If this ever becomes wanted, it is a decision, not a silent addition.
        with open(os.path.join(TOOLS, "artifacts_root.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("os.environ", src)

    # ---- the census ---------------------------------------------------------------------------
    def test_every_corpus_tool_exposes_path(self):
        for name in list(CENSUS) + list(FLAG_ONLY):
            with self.subTest(tool=name):
                rc, txt = _help(name)
                self.assertEqual(0, rc, txt[-400:])
                self.assertIn("--path", txt, "%s must take --path" % name)

    def test_the_older_artifacts_spelling_still_parses_where_it_shipped(self):
        # docs/PLAYAREA-ITEM-SCAN.md and test_gf_item_play_regions.py both spell it --artifacts.
        for name, alias in list(CENSUS.items()) + [(k, (None, v)) for k, v in FLAG_ONLY.items()]:
            want = alias[1]
            with self.subTest(tool=name):
                rc, txt = _help(name)
                self.assertEqual(want, "--artifacts" in txt,
                                 "%s: --artifacts alias presence should be %s" % (name, want))

    # ---- the half that matters: the root actually MOVES ---------------------------------------
    def test_set_artifacts_root_moves_every_named_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            moved = os.path.join(tmp, "elsewhere")
            os.makedirs(os.path.join(moved, "map"))
            os.makedirs(os.path.join(moved, "mapstudio"))
            for name, (globs, _alias) in CENSUS.items():
                with self.subTest(tool=name):
                    mod = _load(name)
                    before = {g: getattr(mod, g) for g in globs}
                    # The DEFAULT has not moved: a freshly imported tool still reads
                    # <repo>/elden_ring_artifacts. CI has no corpus, so nothing else can say this.
                    default = self.ar.default_root(REPO)
                    for g in globs:
                        self.assertTrue(os.path.abspath(before[g]).startswith(default),
                                        "%s.%s no longer defaults under %s" % (name, g, default))
                    mod._set_artifacts_root(moved)
                    for g in globs:
                        now = getattr(mod, g)
                        self.assertNotEqual(before[g], now, "%s.%s did not move" % (name, g))
                        self.assertTrue(os.path.abspath(now).startswith(os.path.abspath(moved)),
                                        "%s.%s is still outside the new root: %s" % (name, g, now))

    def test_gated_treasures_path_means_mapstudio_under_it(self):
        mod = _load("datamine_msb_gated_treasures")
        self.assertTrue(mod.ROOT_DEFAULT.endswith(os.path.join("elden_ring_artifacts", "mapstudio")))


if __name__ == "__main__":
    unittest.main()
