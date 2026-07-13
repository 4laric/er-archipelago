"""PLAY_REGION_GROUPS vs the game's REAL play_region bucket universe. Kills two silent failure modes.

The client enforces region locks by comparing the player's runtime play_region_id // 100 (a BUCKET)
against region_groups.PLAY_REGION_GROUPS. Both ways that table can rot are invisible in-game, because
the failure IS "nothing happens":

  * a PHANTOM bucket -- listed here, never produced by the game -- means that lock can never fire
    (Weeping's only listed bucket was one: the Weeping region lock never enforced anything);
  * a real bucket with NO entry is a PERMISSIVE HOLE -- the kick has no opinion there, so a sealed
    region leaks through its sub-areas, the Scadutree FLOOR never matches, and DLC scaling sits at
    its floor tier.

The universe comes from PlayRegionParam, which lives in the untracked game artifacts -- CI cannot
read it. So `python tools/datamine_play_regions.py --emit` (run on a box WITH the artifacts) writes
it to greenfield/play_region_buckets.tsv, which IS tracked; this suite asserts against that file.
If the artifact is absent the suite SKIPS, visibly: unverified is not the same thing as passing.

These are ground-truth-vs-table invariants over committed files; no Archipelago machinery is
needed, so everything is loaded by path (region_groups.py is installed beside the package by
tools/gf_test.py).
"""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)          # installed: <ap>/worlds/eldenring ; source: greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)    # source tree only: greenfield/


def _first(*cands):
    return next((p for p in cands if os.path.isfile(p)), None)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ARTIFACT = _first(os.path.join(GF_PKG, "play_region_buckets.tsv"),
                  os.path.join(GREENFIELD, "play_region_buckets.tsv"))
SPINE = _first(os.path.join(GF_PKG, "region_groups.py"),
               os.path.join(GREENFIELD, "region_groups.py"))
DATA = os.path.join(GF_PKG, "data.py")


class TestPlayRegionBuckets(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if ARTIFACT is None:
            raise unittest.SkipTest(
                "greenfield/play_region_buckets.tsv is not emitted yet: run "
                "`python tools/datamine_play_regions.py --emit` on a box with the game artifacts "
                "and commit the result. Until then the phantom / permissive-hole invariants are "
                "UNVERIFIED -- this skip is that fact, made visible.")
        if SPINE is None:
            raise AssertionError(
                "region_groups.py not found beside the package. tools/gf_test.py installs it; "
                "without it this suite would assert nothing.")

        cls.universe = {}   # bucket -> (kind, geometry)
        with open(ARTIFACT, encoding="utf-8") as fh:
            lines = [ln.rstrip("\n") for ln in fh if ln.strip() and not ln.startswith("#")]
        if not lines or not lines[0].startswith("bucket\tkind"):
            raise AssertionError("%s: unexpected header %r -- the artifact format drifted; "
                                 "re-emit it." % (ARTIFACT, lines[:1]))
        for ln in lines[1:]:
            b, kind, geo = ln.split("\t")
            cls.universe[int(b)] = (kind, geo)
        # A present-but-degenerate artifact must FAIL, not quietly weaken every assertion below.
        if len(cls.universe) < 100:
            raise AssertionError("%s parsed to only %d buckets; the game defines ~134. Truncated "
                                 "emit -- regenerate it." % (ARTIFACT, len(cls.universe)))

        cls.rg = _load(SPINE, "gf_region_groups_under_test")
        cls.data = _load(DATA, "gf_data_under_test")
        cls.claimed = {int(b) for pids in cls.rg.PLAY_REGION_GROUPS.values() for b in pids}

    def test_no_phantom_buckets(self):
        """Every bucket REGION_GROUPS claims must exist in the game (kills 6800/61002/63001-class
        phantoms: a lock on a phantom bucket can never fire)."""
        phantoms = sorted(self.claimed - set(self.universe))
        self.assertFalse(
            phantoms,
            "PLAY_REGION_GROUPS lists buckets the game never produces -- these locks can NEVER fire: "
            "%r. Re-run tools/datamine_play_regions.py and reassign them." % (phantoms,))

    def test_every_region_has_enforceable_geometry(self):
        """Every apworld region must own at least one REAL bucket of kick geometry (kills the
        Weeping failure mode: a region whose every bucket is phantom is silently unenforceable)."""
        geo = self.rg.region_play_ids()
        pending = set(getattr(self.rg, "REGIONS_PENDING_BUCKET", ()))
        bad = []
        for region in self.data.REGIONS:
            if region == self.rg.HUB or region in pending:
                continue    # HUB is never kicked; PENDING is a NAMED, reasoned hole (see below)
            real = [b for b in geo.get(region, ()) if int(b) in self.universe]
            if not real:
                bad.append((region, tuple(geo.get(region, ()))))
        self.assertFalse(
            bad,
            "Regions with NO real kick geometry -- their locks are silently unenforceable "
            "(region, buckets claimed): %r" % (bad,))

    def test_pending_regions_are_declared_not_discovered(self):
        """REGIONS_PENDING_BUCKET is the ONLY sanctioned way to have a region without kick geometry,
        and it is a debt marker, not a parking space.

        A region listed here genuinely does NOT enforce its lock -- you can walk into it while it is
        sealed. That is the same defect as the Weeping bug; the difference, and the only one that
        matters, is that it is NAMED. So: every entry must be a real region, and must actually lack
        geometry. Once you measure its bucket, move it into PLAY_REGION_GROUPS and delete it here.
        Do not add a region to this set to silence a failure -- that is the old bug with a lid on it.
        """
        pending = set(getattr(self.rg, "REGIONS_PENDING_BUCKET", ()))
        unknown = sorted(pending - set(self.data.REGIONS))
        self.assertFalse(unknown, "REGIONS_PENDING_BUCKET names things that are not regions: %r" % unknown)

        geo = self.rg.region_play_ids()
        stale = sorted(r for r in pending if [b for b in geo.get(r, ()) if int(b) in self.universe])
        self.assertFalse(
            stale,
            "these regions DO have real kick geometry now -- remove them from REGIONS_PENDING_BUCKET "
            "(a stale debt marker suppresses the very check that would catch a regression): %r" % stale)

    def test_hub_bucket_is_real(self):
        hub_pids = self.rg.PLAY_REGION_GROUPS.get(self.rg.HUB, ())
        self.assertTrue([b for b in hub_pids if int(b) in self.universe],
                        "the HUB (%r) has no real bucket: %r" % (self.rg.HUB, hub_pids))

    def test_no_unreviewed_permissive_holes(self):
        """Every real bucket is either assigned to a region or sits on the explicit, reasoned
        UNASSIGNED_BUCKETS list. Anything else is ground where the kick silently has no opinion."""
        unassigned = getattr(self.rg, "UNASSIGNED_BUCKETS", None)
        self.assertIsNotNone(unassigned, "region_groups.UNASSIGNED_BUCKETS is gone -- the "
                                         "explicit exclusion list is part of this invariant.")
        holes = sorted(set(self.universe) - self.claimed - set(unassigned))
        detail = ["%d (%s %s)" % (b, *self.universe[b]) for b in holes]
        self.assertFalse(
            holes,
            "Real buckets with no region and no reasoned exclusion -- the kick is silently "
            "PERMISSIVE on this ground: %s. Assign each in PLAY_REGION_GROUPS or add it to "
            "UNASSIGNED_BUCKETS with a reason." % ", ".join(detail))

    def test_unassigned_list_is_honest(self):
        """UNASSIGNED_BUCKETS entries must be real (else stale) and must not ALSO be assigned
        (else contradictory), and each needs a non-empty reason."""
        unassigned = getattr(self.rg, "UNASSIGNED_BUCKETS", {}) or {}
        stale = sorted(b for b in unassigned if int(b) not in self.universe)
        double = sorted(b for b in unassigned if int(b) in self.claimed)
        reasonless = sorted(b for b, why in unassigned.items()
                            if not (isinstance(why, str) and why.strip()))
        self.assertFalse(stale, "UNASSIGNED_BUCKETS entries the game does not define: %r" % stale)
        self.assertFalse(double, "buckets both assigned in PLAY_REGION_GROUPS and excluded in "
                                 "UNASSIGNED_BUCKETS: %r" % double)
        self.assertFalse(reasonless, "UNASSIGNED_BUCKETS entries without a reason: %r" % reasonless)


if __name__ == "__main__":
    unittest.main()
