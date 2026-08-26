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
    "datamine_dungeon_regions":    (("ART", "MSBDIR"), False),
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

    # ---- MSB discovery: the corpus root does not say WHERE the witchy'd MSBs sit ---------------
    # Alaric's WitchyBND export (2026-08-26) put every map FLAT under `<root>/mapstudio/`, beside
    # unrelated siblings. Three tools read it; three said `FATAL: no witchy'd m60/m61 MSBs under
    # <root>/map`. One candidate list, one predicate, and every tool resolves the same tree.
    LAYOUTS = ("map", "mapstudio", "")          # "" == the witchy dirs sit in the root itself

    def _tree(self, tmp, layout, noise=()):
        root = os.path.join(tmp, "corpus")
        d = os.path.join(root, layout) if layout else root
        for m in ("m60_44_45_00-msb-dcx", "m10_00_00_00-msb-dcx"):
            os.makedirs(os.path.join(d, m, "Region", "PlayArea"))
        for n in noise:
            os.makedirs(os.path.join(root, n), exist_ok=True)
        return root

    def test_all_three_layouts_resolve(self):
        for layout in self.LAYOUTS:
            with tempfile.TemporaryDirectory() as tmp:
                root = self._tree(tmp, layout)
                want = os.path.join(root, layout) if layout else root
                with self.subTest(layout=layout or "<root>"):
                    self.assertEqual(want, self.ar.msb_dir(root))
                    self.assertIn(want, self.ar.msb_dirs(root))

    def test_map_wins_over_mapstudio_when_both_hold_msbs(self):
        """Order is not cosmetic: the committed grace tables were derived from `map/`, and 2026-07
        measured `mapstudio/` holding only 66 of the 118 boss maps. First hit must stay `map/`."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(tmp, "map")
            os.makedirs(os.path.join(root, "mapstudio", "m60_44_45_00-msb-dcx"))
            self.assertEqual(os.path.join(root, "map"), self.ar.msb_dir(root))
            self.assertEqual([os.path.join(root, "map"), os.path.join(root, "mapstudio")],
                             self.ar.msb_dirs(root))

    def test_noise_siblings_do_not_fake_a_flat_root(self):
        """The bare root is only a hit when it DIRECTLY holds `m*-msb-dcx` children. Alaric's root
        also holds `_pilot`, `breakgeom`, `m00`..`m61` -- none of which is a witchy MSB dir, and an
        `isdir` test would have accepted every one of them."""
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "corpus")
            for n in ("_pilot", "breakgeom", "m00", "m60", "m61", "mapstudio-notreally"):
                os.makedirs(os.path.join(root, n))
            self.assertIsNone(self.ar.msb_dir(root))
            self.assertEqual([], self.ar.msb_dirs(root))
            self.assertFalse(self.ar.holds_msb_dirs(root))
            # ...and the same root WITH one real witchy dir added does resolve.
            os.makedirs(os.path.join(root, "m60_44_45_00-msb-dcx"))
            self.assertEqual(root, self.ar.msb_dir(root))

    def test_an_empty_map_dir_does_not_shadow_a_populated_mapstudio(self):
        """The motivating shape's evil twin: `map/` exists but is empty. Existence is not a hit."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(tmp, "mapstudio", noise=("map", "_pilot"))
            self.assertEqual(os.path.join(root, "mapstudio"), self.ar.msb_dir(root))

    def test_the_fatal_names_every_location_tried(self):
        report = self.ar.msb_search_report("/corpus")
        for c in self.ar.msb_candidates("/corpus"):
            self.assertIn(c, report, "the FATAL must name %s" % c)

    def test_every_msb_reading_tool_resolves_the_flat_mapstudio_layout(self):
        """THE MOTIVATING CASE (rule 11): a tree shaped exactly like Alaric's -- witchy dirs FLAT
        under `<root>/mapstudio/`, with `_pilot`/`m60` sibling noise -- must resolve for every tool
        through plain `--path <root>`, with no per-tool flag and no `map/` anywhere."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(tmp, "mapstudio", noise=("_pilot", "breakgeom", "m00", "m60", "m61"))
            ms = os.path.join(root, "mapstudio")
            for name, attr in (("datamine_grace_ground", "MAPDIR"),
                               ("datamine_dungeon_regions", "MSBDIR")):
                with self.subTest(tool=name):
                    mod = _load(name)
                    mod._set_artifacts_root(root)
                    self.assertEqual(ms, getattr(mod, attr),
                                     "%s.%s did not find the flat mapstudio export" % (name, attr))
            for name, attr in (("datamine_arena_graces", "MSB_DIRS"),
                               ("datamine_merchant_shops", "MAPSTUDIO_ROOTS")):
                with self.subTest(tool=name):
                    mod = _load(name)
                    mod._set_artifacts_root(root)
                    self.assertEqual([ms], list(getattr(mod, attr)))
            with self.subTest(tool="datamine_msb_item_regions"):
                mod = _load("datamine_msb_item_regions")
                mod._set_artifacts_root(root)
                self.assertEqual([ms], mod._msb_roots())
                self.assertEqual(["m10_00", "m60_44_45"],
                                 sorted(m for m, _d in mod._iter_msb_dirs(mod._msb_roots())))
            with self.subTest(tool="datamine_item_grace_coords"):
                mod = _load("datamine_item_grace_coords")
                self.assertEqual([ms], mod._msb_dirs(root))
            with self.subTest(tool="datamine_msb_gated_treasures"):
                out = subprocess.run(
                    [sys.executable, os.path.join(TOOLS, "datamine_msb_gated_treasures.py"),
                     "--path", root, "--probe"], capture_output=True, text=True, timeout=180)
                txt = (out.stdout or "") + (out.stderr or "")
                # DISCOVERY is what is under test: the tool must have WALKED both fixture dirs.
                # It still refuses the fixture on its row floor, and rightly so -- two empty MSB
                # dirs are not a corpus -- so assert the discovery FATAL specifically is absent.
                self.assertNotIn("Point --root at", txt, txt[-600:])
                self.assertIn("msb dirs 2", txt, txt[-600:])
            with self.subTest(tool="probe_msb_mapversions"):
                out = subprocess.run(
                    [sys.executable, os.path.join(TOOLS, "probe_msb_mapversions.py"),
                     "--path", root, "--out", os.path.join(tmp, "probe.txt")],
                    capture_output=True, text=True, timeout=180)
                with open(os.path.join(tmp, "probe.txt"), encoding="utf-8") as fh:
                    txt = fh.read()
                # The auto-detection must both FIND the flat export and RANK it first -- this probe
                # reports on an unknown tree, so what it names first is what a reader will trust.
                self.assertIn(ms, txt)
                self.assertNotIn("No candidate root found", txt)
                self.assertIn("=== ROOT DETECTION ===", txt)
                self.assertEqual(ms, [ln.split()[0] for ln in txt.splitlines()
                                      if ln.strip().endswith("EXISTS")][0].strip())

    def test_the_grace_ground_fatal_lists_the_paths_it_tried(self):
        """The failure that started this: the message named ONE path and taught the wrong layout."""
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "corpus")
            os.makedirs(os.path.join(root, "_pilot"))
            gg = _load("datamine_grace_ground")
            gg._set_artifacts_root(root)
            with self.assertRaises(SystemExit) as cm:
                gg.load_volumes()
            msg = str(cm.exception)
            for c in self.ar.msb_candidates(root):
                self.assertIn(c, msg, "the FATAL must name %s" % c)

    def test_gated_treasures_path_means_mapstudio_under_it(self):
        mod = _load("datamine_msb_gated_treasures")
        self.assertTrue(mod.ROOT_DEFAULT.endswith(os.path.join("elden_ring_artifacts", "mapstudio")))


if __name__ == "__main__":
    unittest.main()
