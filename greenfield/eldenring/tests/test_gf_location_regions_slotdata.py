"""The tracker's region model is SENT, and it agrees with the locations it describes.

WHAT CHANGED (2026-07-28). `er-logic/src/tracker_regions.rs` -- a generated 279 KB table of every
location's region, committed to the CLIENT repo -- is deleted. `locationRegions` and
`regionCoarseKeys` carry it in slot_data instead.

THE REASON IS CORRECTNESS, NOT CONVENIENCE, and this suite exists to keep the correctness half
honest. `_base_slot_data` scopes `locationFlags` and `regionOpenFlags` to `[HUB] + kept`, and under
`num_regions` the kept set is a per-seed SUBSET. The baked table was generated from the full
`data.LOCATIONS` once, so on a reduced seed it grouped locations into regions the seed does not
contain and marked them in-logic. A CORPUS fact standing in for a SEED fact -- the same shape as the
num_regions bug that voided "the item exists" claims.

So the assertions here are all about AGREEMENT WITH THE SEED, not with the corpus:

  A. every location in `locationFlags` has a region, and vice versa -- they are built from one walk,
     and this is what stops them drifting apart.
  B. every region named has a coarse key, and every non-empty coarse key has a lock item in
     `regionOpenFlags` -- otherwise the client looks one up, finds nothing, and calls the region
     permanently OPEN. That failure is silent and permissive, which is the bad direction.
  C. the hub is `""` (always accessible), not merely lockless.
  D. a REDUCED seed emits only its kept regions. This is the whole point, so it is tested with an
     actual reduced kept-set rather than asserted about the default one.
"""
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
GF = os.path.join(REPO, "greenfield") if _FOUND else os.path.dirname(os.path.dirname(HERE))


def _load(name):
    import importlib.util
    path = os.path.join(GF, "eldenring", name + ".py")
    spec = importlib.util.spec_from_file_location("_gf_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
class LocationRegionsSlotData(unittest.TestCase):
    """Rebuilds the emit from data.py, AP-free -- core.py imports BaseClasses, which is not here.

    The logic under test is small and stated in one place in core._base_slot_data; this mirrors it
    over an arbitrary kept-set so a REDUCED seed can actually be exercised. The mirror is the risk,
    so `test_the_mirror_matches_core_py` pins the source text it mirrors.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = _load("data")
        cls.open_flags = _load("region_open_flags").REGION_OPEN_FLAGS

    def emit(self, kept):
        data, open_flags = self.data, self.open_flags
        loc_regions, loc_flags = {}, {}
        for rn in [data.HUB] + list(kept):
            ids = [int(a) for (_n, a, _f) in data.LOCATIONS.get(rn, [])]
            if ids:
                loc_regions[rn] = sorted(ids)
            for (_n, a, f) in data.LOCATIONS.get(rn, []):
                loc_flags[str(a)] = f
        lockless_host = {}
        finale = getattr(data, "FINALE_REGION", None)
        if finale is not None and getattr(data, "FINALE_HOST_REGION", None) is not None:
            lockless_host[finale] = data.FINALE_HOST_REGION
        coarse = {}
        for rn in loc_regions:
            if rn == data.HUB:
                coarse[rn] = ""
            elif rn in open_flags:
                coarse[rn] = rn
            elif rn in lockless_host:
                coarse[rn] = lockless_host[rn]
            else:
                self.fail("region %r has locations but no lock and no host mapping -- the client "
                          "would treat it as permanently accessible" % rn)
        region_open = {"%s Lock" % r: open_flags[r] for r in kept if r in open_flags}
        return loc_regions, coarse, loc_flags, region_open

    # -- A ------------------------------------------------------------------
    def test_every_location_flag_has_a_region_and_vice_versa(self):
        kept = list(self.data.REGIONS)
        loc_regions, _coarse, loc_flags, _ro = self.emit(kept)
        regioned = {i for ids in loc_regions.values() for i in ids}
        flagged = {int(k) for k in loc_flags}
        self.assertEqual(
            regioned, flagged,
            "locationRegions and locationFlags disagree about which locations this seed has "
            "(%d only-regioned, %d only-flagged). They are built from ONE walk in "
            "core._base_slot_data precisely so this cannot happen."
            % (len(regioned - flagged), len(flagged - regioned)))

    def test_no_location_appears_in_two_regions(self):
        loc_regions, _c, _lf, _ro = self.emit(list(self.data.REGIONS))
        seen = {}
        for region, ids in loc_regions.items():
            for i in ids:
                self.assertNotIn(i, seen,
                                 "location %d is in both %r and %r; the client's id->region map "
                                 "would keep whichever landed last" % (i, seen.get(i), region))
                seen[i] = region

    # -- B ------------------------------------------------------------------
    def test_every_coarse_key_resolves_to_a_lock_the_seed_actually_sent(self):
        kept = list(self.data.REGIONS)
        loc_regions, coarse, _lf, region_open = self.emit(kept)
        self.assertEqual(set(coarse), set(loc_regions),
                         "every region with locations needs a coarse key")
        for region, key in sorted(coarse.items()):
            if not key:
                continue
            self.assertIn(
                "%s Lock" % key, region_open,
                "region %r keys in-logic off coarse %r, but '%s Lock' is not in regionOpenFlags. "
                "The client would look it up, find nothing, and treat the region as permanently "
                "OPEN -- a silent, permissive failure." % (region, key, key))

    # -- C ------------------------------------------------------------------
    def test_the_hub_is_always_accessible(self):
        _lr, coarse, _lf, _ro = self.emit(list(self.data.REGIONS))
        self.assertEqual(coarse.get(self.data.HUB), "",
                         "the hub must be '' (always accessible), not its own lock key")

    # -- D: THE POINT -------------------------------------------------------
    def test_a_reduced_seed_emits_only_its_kept_regions(self):
        """num_regions is why this moved to slot_data at all."""
        full = list(self.data.REGIONS)
        kept = full[:3]
        loc_regions, coarse, loc_flags, region_open = self.emit(kept)
        allowed = set(kept) | {self.data.HUB}
        self.assertTrue(set(loc_regions) <= allowed,
                        "a reduced seed emitted regions it did not keep: %s"
                        % sorted(set(loc_regions) - allowed))
        dropped = [r for r in full[3:] if self.data.LOCATIONS.get(r)]
        self.assertTrue(dropped, "no dropped region had locations -- this test proved nothing")
        for region in dropped:
            self.assertNotIn(region, loc_regions)
            for (_n, ap_id, _f) in self.data.LOCATIONS[region]:
                self.assertNotIn(str(ap_id), loc_flags)
        # ...and every coarse key still resolves, which is the thing a subset most easily breaks.
        for region, key in coarse.items():
            if key:
                self.assertIn("%s Lock" % key, region_open,
                              "on a REDUCED seed, region %r keys off coarse %r whose lock was not "
                              "sent -- the client would call it permanently open" % (region, key))

    # -- the mirror is the risk --------------------------------------------
    def test_the_mirror_matches_core_py(self):
        """This suite REBUILDS the emit (core.py needs AP). Pin the source it mirrors, so a change
        to core._base_slot_data that this file does not follow fails HERE rather than shipping."""
        src = open(os.path.join(GF, "eldenring", "core.py"), encoding="utf-8").read()
        for needle in ("contract.LOCATION_REGIONS: loc_regions",
                       "contract.REGION_COARSE_KEYS: coarse_keys",
                       "for rn in [HUB] + kept:",
                       "coarse_keys[rn] = \"\""):
            self.assertIn(needle, src,
                          "core._base_slot_data no longer contains %r -- this mirror is stale and "
                          "is now testing something the world does not do." % needle)


if __name__ == "__main__":
    unittest.main()
