"""The wizard's seed-size census must be CURRENT, CONSISTENT, and TRUE OF REAL SEEDS.

`tools/build_region_census.py` emits `wizard/region-census.json`: per region, how many checks it
contributes and -- keyed by class COMBINATION -- how many of those may host progression. The options
wizard evaluates it live so a player can size a seed BEFORE generating one.

MOTIVATING CASE (CONTRIBUTING rule 11). On 2026-08-07 a Nexus commenter asked what fraction of
"2000 checks for 6 areas" is filler before committing five friends to a multiworld, and the day
before, bobler asked why `num_regions: 1` kept four regions. Neither answer existed until after
generation. #409 added the gen-log line that explains the kept set -- but a log line is read AFTER
the decision it would have informed. The census puts the number in front of the choice, and this
file is what stops it being a confidently wrong number.

Four claims, each a different way the artifact could rot:

1. THE COMMITTED COPIES AGREE (`test_inlined_blob_equals_the_json_file`). The census is stored twice
   -- the JSON file and the blob inlined into `wizard/wizard.html`. Same split, same failure mode,
   as `test_gf_wizard_blob_sync`: four commits in 2026-07-28/29 moved the options JSON without
   re-injecting and the wizard page silently lost three options.

2. NEITHER COPY IS STALE (`test_artifact_is_current`). A regen that moves a region's check count or
   re-anchors a Golden Seed must not land silently.

3. 🛑 THE SPLIT SUMS BACK TO THE GATED TOTAL (`test_default_union_matches_surface_confidence`).
   This is the load-bearing one. The census adds a REGION axis to numbers `build_surface_confidence`
   already owns; if the split drifts, the wizard prints confident per-seed surface sizes that no
   longer describe the surface. So the union of this table over the default classes is pinned to
   that tool's own `default_hosting` total. It is a UNION, never a sum of per-class counts: surface
   classes overlap (a check is routinely GreatRune + MajorBoss + Boss), so summing double-counts
   exactly the checks carrying two selected classes -- which is why the artifact is keyed by
   combination in the first place.

4. 🛑 THE IDENTITY IS TRUE OF WORLDS ARCHIPELAGO ACTUALLY BUILDS
   (`test_check_count_identity_against_real_worlds`). Everything above is internal consistency --
   the census could be perfectly self-consistent and still describe a seed shape that does not
   exist. So this builds real worlds and asserts

       len(real locations) == hub + sum(kept regions) + finale

   where `finale` is the Ashen Capital's checks and exists iff a base-game region is in play
   (features/finale.finale_active). The Ashen Capital is NEVER rollable, is not in REGIONS and is
   not counted by num_regions, so a census that treated it as an ordinary region would be off by 12
   on every base-game seed and off by -12 on every dlc_only one. The matrix below covers both.

REPO-ONLY (`find_repo_root`): `tools/` and `wizard/` are not copied into the pinned AP checkout by
`tools/gf_test.py`, so under that harness there is nothing to test. Claims 1-3 are AP-free; claim 4
additionally needs AP, so it runs where an AP checkout sits inside the repo (`.ap-test`, which is
what `run_ci.ps1` / `greenfield/ci-linux.sh` provision) -- the same arrangement
`test_gf_surface_confidence`'s second suite relies on.
"""

import importlib.util
import io
import json
import os
import re
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

# Character-for-character the tag tools/build_region_census.py:inject() substitutes on. If the
# injector's tag ever changes this must FAIL rather than quietly match nothing and report "in sync".
BLOB_RE = re.compile(
    r'<script id="er-region-census" type="application/json">\n(.*?)</script>', re.S)

FIX = "fix: python tools/build_region_census.py"


def _read(*parts):
    with open(os.path.join(REPO, *parts), "r", encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def _tool(name):
    spec = importlib.util.spec_from_file_location("_t_" + name,
                                                  os.path.join(REPO, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(REPO, REPO_ONLY_REASON)
class TestRegionCensusArtifact(unittest.TestCase):
    """Claims 1-3. AP-free."""

    def test_inlined_blob_equals_the_json_file(self):
        raw = _read("wizard", "region-census.json")
        html = _read("wizard", "wizard.html")
        m = BLOB_RE.search(html)
        self.assertIsNotNone(
            m, "wizard.html has no <script id='er-region-census'> block -- the injector's anchor "
               "is gone, so nothing is being kept in sync. " + FIX)
        self.assertEqual(m.group(1), raw,
                         "wizard.html's inlined census differs from wizard/region-census.json. " + FIX)

    def test_artifact_is_current(self):
        census = _tool("build_region_census")
        # WITNESS (test_gf_vacuous_pass): the ratchet reads `assertEqual(rc, 0)` as an
        # assert-this-is-empty and wants proof the test saw a subject. It is a false positive on an
        # exit code -- but the cheap honest answer is to show the tool measured a real tree rather
        # than to argue with the lint, so assert the census is non-trivial before trusting its rc.
        self.assertGreater(len(census.measure()["regions"]), 1,
                           "the census describes fewer than two regions -- --check would be "
                           "asserting about an empty tree")
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            rc = census.main(["--check"])
        self.assertEqual(rc, 0, "wizard/region-census.json is STALE.\n" + buf.getvalue() + FIX)

    def test_default_union_matches_surface_confidence(self):
        census_tool = _tool("build_region_census")
        sc = _tool("build_surface_confidence")
        census = census_tool.measure(sc)
        _rows, totals = sc.measure(sc._load())
        union = census_tool.surface_union(
            census, census["default_classes"], list(census["regions"]))
        self.assertEqual(
            union, totals["default_hosting"],
            "the per-region census unioned over the default surface (%d) disagrees with "
            "build_surface_confidence's default_hosting (%d). One of the two changed its bar stack; "
            "they must stay one definition of 'can host'." % (union, totals["default_hosting"]))

    def test_combination_keys_are_vocabulary_classes(self):
        """A combo key naming a class outside the vocabulary would silently never match a player's
        selection -- those checks would vanish from every surface count instead of erroring."""
        census = _tool("build_region_census").measure()
        vocab = set(census["classes"])
        # WITNESS (test_gf_vacuous_pass): without this the loop below asserts nothing the day the
        # census emits no combos at all -- it would pass for exactly the reason it passes when the
        # keys are correct. The ratchet caught this file at 155/154 on its first full-suite run.
        seen = sum(len(b["combos"]) for b in census["regions"].values())
        self.assertGreater(seen, 0, "the census carries no class combinations at all")
        self.assertTrue(vocab, "the surface vocabulary is empty")
        for region, body in census["regions"].items():
            for combo in body["combos"]:
                for cls in combo.split("|"):
                    self.assertIn(cls, vocab,
                                  "%s: combo %r names %r, which is not in the surface vocabulary"
                                  % (region, combo, cls))

    def test_emit_is_deterministic(self):
        """Two measures in one process must be byte-identical. SURFACE_DEFAULT_CLASSES is a
        frozenset and a set of strings has no stable iteration order ACROSS processes; the first
        cut of the tool emitted `list(...)` of it and two runs disagreed. Ordering now comes from
        the vocabulary (same fix as progression_surface.selected_surface). This catches the
        in-process half; `--check` in test_artifact_is_current catches the cross-process half,
        because the committed file was written by a different process."""
        tool = _tool("build_region_census")
        self.assertEqual(tool.dumps(tool.measure()), tool.dumps(tool.measure()))


@unittest.skipUnless(REPO, REPO_ONLY_REASON)
class TestRegionCensusAgainstRealWorlds(unittest.TestCase):
    """Claim 4. Needs AP: it builds real worlds."""

    # (options, why this row is here) -- every branch of the identity, not a spread of samples.
    CASES = [
        ({"num_regions": 6}, "the default draw"),
        # the rune goal is what makes the smallest draw LEGAL since #768 withheld the Ashen
        # Lock -- a 1-region `region_locks` seed mints nothing the goal can want and is refused
        # at gen. The case is still the smallest draw, which is what it is here to measure.
        ({"num_regions": 1, "ending_condition": "great_runes"},
         "the smallest draw -- goal force-keeps and parent closure dominate"),
        ({"num_regions": 0}, "the whole-map branch (no draw at all)"),
        ({"num_regions": 3, "enable_dlc": False}, "base game only"),
        ({"num_regions": 4, "dlc_only": True}, "no base region in play -> the finale must DROP OUT"),
    ]

    @classmethod
    def setUpClass(cls):
        try:
            from test.bases import WorldTestBase  # noqa: F401
        except Exception as exc:  # no AP checkout around this repo
            raise unittest.SkipTest("needs an Archipelago checkout (test.bases): %s" % exc)

    def _build(self, options):
        from test.bases import WorldTestBase

        class _T(WorldTestBase):
            game = "Elden Ring"
            def runTest(self):  # noqa: D102
                pass
        _T.options = dict(options)
        t = _T("runTest")
        t.setUp()
        return t.multiworld, t.multiworld.worlds[1]

    def test_check_count_identity_against_real_worlds(self):
        census = _tool("build_region_census").measure()
        regions = census["regions"]
        hub = census["hub_region"]
        finale = census["finale"]["region"]

        for options, why in self.CASES:
            with self.subTest(options=options, why=why):
                mw, world = self._build(options)
                actual = len([l for l in mw.get_locations(1) if not l.is_event])
                kept = list(world._kept())
                self.assertTrue(kept, "no region was kept -- the identity would be vacuous")

                predicted = regions[hub]["checks"] + sum(regions[r]["checks"] for r in kept)
                # 🛑 THE FINALE RULE IS OVER THE ELIGIBLE POOL, NOT THE KEPT SET. The first cut of
                # this test read `any(not dlc for r in kept)` and went red on num_regions=1 when the
                # single drawn region happened to be a DLC one: the built world still had the Ashen
                # Capital's 12 checks, because the base game was in play (dlc_only was off) even
                # though the draw kept none of it. features/finale.finale_active takes the seed's
                # ELIGIBLE pool; census["finale"]["present_when"] says the same thing. Only dlc_only
                # removes the base game from the pool.
                base_in_play = not options.get("dlc_only", False)
                if base_in_play:
                    predicted += regions[finale]["checks"]

                self.assertEqual(
                    predicted, actual,
                    "census says %d checks, the built world has %d (%s; kept %d region(s), "
                    "base game in play: %s). The identity 'hub + kept + finale' has drifted -- "
                    "either a region's check count moved or the finale rule changed."
                    % (predicted, actual, why, len(kept), base_in_play))

    def test_surface_is_never_larger_than_the_seed(self):
        """A per-seed surface bigger than the seed's own check count would be nonsense the wizard
        would happily print. Cheap, but it is the one bound that catches a region-axis mix-up."""
        census_tool = _tool("build_region_census")
        census = census_tool.measure()
        for options, why in self.CASES:
            with self.subTest(options=options, why=why):
                mw, world = self._build(options)
                actual = len([l for l in mw.get_locations(1) if not l.is_event])
                present = [census["hub_region"]] + list(world._kept())
                if not options.get("dlc_only", False):  # eligible pool, not kept -- see above
                    present.append(census["finale"]["region"])
                surface = census_tool.surface_union(census, census["default_classes"], present)
                self.assertGreater(surface, 0)
                self.assertLessEqual(surface, actual)


if __name__ == "__main__":
    unittest.main()
