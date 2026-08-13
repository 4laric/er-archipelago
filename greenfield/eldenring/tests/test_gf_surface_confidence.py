"""The surface-confidence table must be CURRENT, and its bar stack must be the REAL one.

`tools/build_surface_confidence.py` prices every progression-surface class: how many checks carry the
tag, and how many of those may actually HOST progression once the bars are applied. It is the
instrument the surface vocabulary is opened up against -- *before we add something to the possible
progression surface we have to be absolutely sure where it is* -- so it is only worth having if two
things hold, and this file is both of them.

1. THE COMMITTED TABLE IS NOT STALE (`test_artifact_is_current`). A regen that shifts a class's
   confidence must not land silently; `--check` diffs a fresh emit against `greenfield/
   surface_confidence.tsv`.

2. 🛑 THE TOOL'S BARS ARE THE FEATURE'S BARS (`test_eligible_matches_allowed_ap_ids`). This is the
   load-bearing test. The tool is AP-FREE on purpose -- it loads the generated modules by path,
   because importing `eldenring` pulls `BaseClasses`, and being AP-free is what lets it run in the
   coverage half of CI. The price is that it RE-IMPLEMENTS the bar stack instead of calling
   `features/progression_surface.allowed_ap_ids` (which needs `Options`). A re-implementation drifts.
   When it drifts, the table keeps printing confident numbers about a surface that no longer exists
   -- which is the exact failure the table was built to end, wearing a lab coat. So the two are
   pinned here, per class, on the AP side.

   The relation is exact rather than approximate:

       tool.eligible(cls)  ==  allowed_ap_ids(LOCATION_TAGS, {cls})  -  MISSABLE_LOCATIONS

   `allowed_ap_ids` bars guessed-region / erdtree-burn / surface-excluded / hub-merchant itself; the
   missable bar lives in `_world_barred_aps` because it is world-conditional
   (`protect_missable_locations`), and the tool applies it unconditionally because that option is
   frozen ON. If it is ever unfrozen, THIS ASSERTION is the thing that should be made conditional --
   not the tool's column, which must keep reporting the cost either way.

Both suites are REPO-ONLY (`find_repo_root`): `tools/` is not copied into the pinned AP checkout by
`tools/gf_test.py`, so under that harness there is nothing to test. They run in the `generators` CI
job, which checks out the repo proper. Suite 2 additionally needs AP for the feature import.
"""

import importlib.util
import io
import os
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # run as a script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
# Derive paths FROM the found root, never positionally -- in CI the AP checkout sits INSIDE the
# repo, so a positional walk lands in `_ap/worlds/` and every read misses (see _util.find_repo_root).
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
TOOL = os.path.join(REPO, "tools", "build_surface_confidence.py")
ARTIFACT = os.path.join(REPO, "greenfield", "surface_confidence.tsv")


def _load_tool():
    spec = importlib.util.spec_from_file_location("_build_surface_confidence", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class SurfaceConfidenceArtifact(unittest.TestCase):
    def test_tool_and_artifact_exist(self):
        self.assertTrue(os.path.isfile(TOOL), "missing %s" % TOOL)
        self.assertTrue(os.path.isfile(ARTIFACT),
                        "missing greenfield/surface_confidence.tsv -- run "
                        "`python tools/build_surface_confidence.py`")

    def test_artifact_is_current(self):
        mod = _load_tool()
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            rc = mod.main(["--check"])
        self.assertEqual(rc, 0,
                         "greenfield/surface_confidence.tsv is STALE. Re-emit with "
                         "`python tools/build_surface_confidence.py`.\n%s" % buf.getvalue())

    def test_every_vocabulary_class_is_priced(self):
        """No class may be offered without its confidence cost -- that is the whole rule.

        `contract` comes from the tool's own path loader, not `from ..contract import`: this suite
        must stay AP-free AND runnable as a bare script, and a relative import satisfies neither
        (`python tests/test_gf_surface_confidence.py` has no parent package). It reads the same
        contract.py the world does. The stronger check -- that the tool's SELECTION matches
        contract.has_class -- lives in the AP-side suite below, where the real module is importable."""
        mod = _load_tool()
        mods = mod._load()
        rows, _totals = mod.measure(mods)
        ct = mods["contract"]
        derived = set(ct.SURFACE_DERIVED_CLASSES)
        vocab = [c for c in ct.SURFACE_CLASSES if c not in derived]
        self.assertEqual([r["class"] for r in rows], vocab,
                         "the table must price the TAGGED vocabulary exactly, in vocabulary order")
        # A derived class must be ABSENT, not zero. A 0/0 row is indistinguishable from "no location
        # can carry this", and the whole point of the artifact is that a class's cost is legible.
        self.assertEqual(sorted(set(r["class"] for r in rows) & derived), [],
                         "a DERIVED surface class was priced by tag count; it has no tags, so the "
                         "row can only read 0 and would be read as 'unhostable'")
        self.assertTrue(derived <= set(ct.SURFACE_CLASSES),
                        "SURFACE_DERIVED_CLASSES names something outside the vocabulary")
        self.assertTrue(set(ct.SURFACE_DEFAULT_CLASSES) - derived <= set(vocab),
                        "a TAGGED default class outside the vocabulary would never be priced")
        # A DERIVED class in the default is the interesting case: it is unpriceable here, so the
        # artifact has to SAY it is part of the default rather than leave the reader to add the
        # hosting number to nothing. Pin the disclosure, not just the omission.
        self.assertTrue(set(ct.SURFACE_DEFAULT_CLASSES) & derived <= set(ct.SURFACE_CLASSES),
                        "a derived default class outside the vocabulary")
        if set(ct.SURFACE_DEFAULT_CLASSES) & derived:
            self.assertEqual(sorted(_totals["default_derived"]),
                             sorted(set(ct.SURFACE_DEFAULT_CLASSES) & derived),
                             "the emit must name the derived classes the DEFAULT surface includes, "
                             "or its 'DEFAULT SURFACE hosting' line reads as the whole surface "
                             "when it is only the tagged half")

    def test_total_plus_tag_excluded_is_the_raw_tag_count(self):
        """`total` is has_class-FILTERED; the header's "carry any tag" line is RAW. Pin the bridge.

        MOTIVATING CASE (rule 11), 2026-08-08: `Shop 500` in the committed table was compared
        against 527 raw `Shop` tags in location_tags.py and the table was reported STALE in a
        design review. It was not stale -- `test_artifact_is_current` above diffs a fresh emit on
        every CI run and was green. The two numbers are different measures wearing one label:
        `total` subtracts SURFACE_EXCLUDE_TAGS (EniaShop), the header line does not. That cost a
        wrong claim about a green gate, which is worse than a red one.

        So the filter is now a COLUMN, and this is the identity that keeps it honest. It cannot be
        satisfied by re-typing a number: both sides are derived from LOCATION_TAGS here, the same
        way the tool derives them, so a class whose exclusion count moves must move the column."""
        mod = _load_tool()
        mods = mod._load()
        rows, _ = mod.measure(mods)
        lt = mods["location_tags"].LOCATION_TAGS
        for r in rows:
            raw = sum(1 for ts in lt.values() if r["class"] in (ts or ()))
            self.assertEqual(
                r["total"] + r["tag_excluded"], raw,
                "%s: total %d + tag_excluded %d != %d raw tags -- the table's filtered and raw "
                "counts have come apart, which is exactly the confusion the column exists to end"
                % (r["class"], r["total"], r["tag_excluded"], raw))

    def test_surface_excluded_tags_are_what_tag_excluded_counts(self):
        """The column must count the TAG exclusion, not the hand-excluded FLAG list.

        `surface_excluded` (a bar column) and `tag_excluded` (this one) are different mechanisms
        with confusingly similar names: the first is gen_data's `_SURFACE_EXCLUDE_FLAGS`, the
        second is `contract.SURFACE_EXCLUDE_TAGS`. A class with no exclude-tagged member must
        price zero here even when its bar column is large -- Fragment is the live witness (7
        hand-excluded flags, 0 exclude-tagged)."""
        mod = _load_tool()
        mods = mod._load()
        rows, _ = mod.measure(mods)
        lt = mods["location_tags"].LOCATION_TAGS
        xtags = set(getattr(mods["contract"], "SURFACE_EXCLUDE_TAGS", ()) or ())
        self.assertTrue(xtags, "SURFACE_EXCLUDE_TAGS is empty -- this test would be vacuous")
        for r in rows:
            want = sum(1 for ts in lt.values()
                       if r["class"] in (ts or ()) and (xtags & set(ts or ())))
            self.assertEqual(r["tag_excluded"], want,
                             "%s: tag_excluded %d != %d checks carrying both the class and a "
                             "SURFACE_EXCLUDE_TAG" % (r["class"], r["tag_excluded"], want))

    def test_eligible_is_never_computed_by_subtracting_columns(self):
        """The bar columns OVERLAP, so `total - sum(bars)` is wrong and can even go negative.
        Guard the invariant the header claims: eligible >= total - sum(bars), with equality only
        when no check is barred twice."""
        mod = _load_tool()
        rows, _ = mod.measure()
        for r in rows:
            naive = r["total"] - sum(r[b] for b in mod.BAR_ORDER)
            self.assertGreaterEqual(
                r["eligible"], naive,
                "%s: eligible %d < naive column subtraction %d -- eligible must come from the "
                "UNION of the bars" % (r["class"], r["eligible"], naive))
            self.assertLessEqual(r["eligible"], r["total"])


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class SurfaceConfidencePinsTheRealBarStack(unittest.TestCase):
    """🛑 The reason the table can be trusted. See the module docstring."""

    @classmethod
    def setUpClass(cls):
        try:
            from ..features.progression_surface import allowed_ap_ids
            from ..location_tags import LOCATION_TAGS
            from ..missable_locations import MISSABLE_LOCATIONS
            from ..contract import SURFACE_CLASSES, SURFACE_DERIVED_CLASSES, has_class
        except Exception as e:  # AP absent -> the feature module cannot import Options
            raise unittest.SkipTest("progression_surface needs Archipelago (%r)" % (e,))
        cls.allowed_ap_ids = staticmethod(allowed_ap_ids)
        cls.LT = LOCATION_TAGS
        cls.MISS = frozenset(MISSABLE_LOCATIONS)
        # The TAGGED vocabulary. A derived class (SweepSlot) is not priced by the tool and has no
        # row to compare against; test_derived_classes_carry_no_tags below pins the reason instead.
        cls.DERIVED = frozenset(SURFACE_DERIVED_CLASSES)
        cls.VOCAB = [c for c in SURFACE_CLASSES if c not in cls.DERIVED]
        cls.has_class = staticmethod(has_class)
        cls.mod = _load_tool()

    def test_tagged_selection_matches_has_class(self):
        """The tool re-expresses contract.has_class (tag intersection minus SURFACE_EXCLUDE_TAGS).
        If that drifts, every count in the table is off before a single bar is applied."""
        mods = self.mod._load()
        rows, _ = self.mod.measure(mods)
        by_class = {r["class"]: r["total"] for r in rows}
        for cls in self.VOCAB:
            expected = {ap for ap, ts in self.LT.items() if self.has_class(ts, {cls})}
            self.assertEqual(by_class[cls], len(expected),
                             "%s: tool counted %d tagged, contract.has_class says %d"
                             % (cls, by_class[cls], len(expected)))

    def test_derived_classes_carry_no_tags_so_the_tag_path_cannot_serve_them(self):
        """A DERIVED class must contribute NOTHING through allowed_ap_ids -- the witness that its
        whole contribution comes from progression_surface.sweep_slot_aps and not from a stray tag.

        Rule 11 motivating case: SweepSlot was added to contract.SURFACE_CLASSES, and every reader
        that iterates that list -- this suite twice, the confidence tool, the wizard's family/label
        maps, both halves of the sweep-cut partition gate -- assumed a member was a TAG. Four of them
        went red or silent. This is the assertion that says what the class actually is, so the next
        derived class is added with its contract rather than discovered by a KeyError."""
        self.assertTrue(self.DERIVED, "no derived class declared -- this test is vacuous")
        for cls in sorted(self.DERIVED):
            self.assertEqual(
                set(self.allowed_ap_ids(self.LT, {cls})), set(),
                "%s is DERIVED but some location carries it as a tag. Either it is not derived "
                "after all, or gen_data has started baking a tag it must not." % cls)
            self.assertEqual(
                {ap for ap, ts in self.LT.items() if cls in (ts or ())}, set(),
                "%s appears in LOCATION_TAGS" % cls)

    def test_eligible_matches_allowed_ap_ids(self):
        """tool.eligible(cls) == allowed_ap_ids({cls}) - MISSABLE, exactly, for every class."""
        mods = self.mod._load()
        rows, _ = self.mod.measure(mods)
        by_class = {r["class"]: r["eligible"] for r in rows}
        for cls in self.VOCAB:
            real = set(self.allowed_ap_ids(self.LT, {cls})) - self.MISS
            self.assertEqual(
                by_class[cls], len(real),
                "%s: build_surface_confidence says %d eligible, the REAL "
                "progression_surface.allowed_ap_ids says %d. The tool's bar stack has drifted from "
                "the feature's -- fix the tool, not this test." % (cls, by_class[cls], len(real)))

    def test_default_surface_hosting_number_matches(self):
        """The headline number people quote. `default_hosting` must equal what the feature would
        actually offer with the missable guard armed (its frozen state)."""
        from ..contract import SURFACE_DEFAULT_CLASSES
        _rows, totals = self.mod.measure()
        real = set(self.allowed_ap_ids(self.LT, set(SURFACE_DEFAULT_CLASSES))) - self.MISS
        self.assertEqual(totals["default_hosting"], len(real))
        self.assertGreater(totals["default_tag_union"], totals["default_hosting"],
                           "a tag union that equals the hosting count means the bars stopped being "
                           "applied -- the exact confusion this table exists to prevent")


if __name__ == "__main__":
    unittest.main()
