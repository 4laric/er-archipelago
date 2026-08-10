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


def _load_pkg(name, data_mod):
    """Same, for a module that uses RELATIVE imports (`from .data import REGIONS`): fake the
    package so the import resolves. data.py and region_open_flags.py are standalone and do not
    need this; region_spine.py does, and the mirror needs DLC_REGIONS from it to answer the same
    "is the base game in play" question features/finale.py asks (SPEC-ashen-capital-lock)."""
    import importlib.util
    import types
    pkg = types.ModuleType("_gf_pkg")
    pkg.__path__ = [os.path.join(GF, "eldenring")]
    sys.modules["_gf_pkg"] = pkg
    sys.modules["_gf_pkg.data"] = data_mod
    path = os.path.join(GF, "eldenring", name + ".py")
    spec = importlib.util.spec_from_file_location("_gf_pkg." + name, path)
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
        cls.dlc_regions = frozenset(_load_pkg("region_spine", cls.data).DLC_REGIONS)

    def emit(self, kept, eligible=None):
        data, open_flags = self.data, self.open_flags
        # `eligible` is the seed's region POOL, which is what the finale's existence keys on since
        # SPEC-ashen-capital-lock -- not the draw. Default is the full pool, i.e. an ordinary seed
        # with the base game in play; pass a DLC-only pool to mirror `dlc_only`.
        eligible = list(data.REGIONS) if eligible is None else list(eligible)
        finale_built = bool(set(eligible) - self.dlc_regions)
        loc_regions, loc_flags = {}, {}
        for rn in [data.HUB] + list(kept):
            ids = [int(a) for (_n, a, _f) in data.LOCATIONS.get(rn, [])]
            if ids:
                loc_regions[rn] = sorted(ids)
            for (_n, a, f) in data.LOCATIONS.get(rn, []):
                loc_flags[str(a)] = f
        # THE FEATURE SEAM, and the reason this mirror grew it. features/finale.py publishes Ashen
        # Capital's checks through `gf_extra_location_flags`, which core merges into locationFlags --
        # and Ashen Capital is deliberately NOT in data.REGIONS, so the `[HUB] + kept` walk above
        # cannot see it. The FIRST version of this suite mirrored only that walk, so BOTH sides of
        # `test_every_location_flag_has_a_region_and_vice_versa` had the same 10-location hole and it
        # passed while the emit shipped 4869 regions against 4879 flags. A mirror that reproduces the
        # bug faithfully proves nothing; it has to mirror what core ACTUALLY emits.
        # ...and the seam is CONDITIONAL, but on a different question as of 2026-08-06
        # (SPEC-ashen-capital-lock). It used to read `set(data.FINALE_REQUIRES) <= set(kept)`:
        # features/finale.py armed only when Farum Azula and Leyndell were both kept. FINALE_REQUIRES
        # is `()` now, so that expression is VACUOUSLY TRUE and would arm the seam on every pool --
        # including a dlc_only one, where the real emit builds no finale at all. The live rule is
        # `finale_active` = "is any base-game region in play", computed above from the POOL, and
        # that is what is mirrored here.
        if finale_built:
            for (_n, a, f) in data.LOCATIONS.get(data.FINALE_REGION, ()):
                loc_flags[str(a)] = f
        ap_region = {int(a): rn for rn, rows in data.LOCATIONS.items() for (_n, a, _f) in rows}
        regioned = {i for ids in loc_regions.values() for i in ids}
        for ap in loc_flags:
            ap = int(ap)
            if ap not in regioned:
                loc_regions.setdefault(ap_region[ap], []).append(ap)
        # THE LOCKLESS-HOST BRANCH IS GONE (SPEC-ashen-capital-lock). It read
        # `lockless_host = {FINALE_REGION: FINALE_HOST_REGION}` and keyed the Ashen Capital's space
        # off LEYNDELL's lock, because the finale had checks and no lock of its own. It has one
        # now, plus a front-door open flag and its own kick buckets, so it takes the ordinary
        # `rn in open_flags` branch and the raise below is the ONLY fallback -- which is the point:
        # a region with checks and no gate of its own reads as permanently open to the client.
        coarse = {}
        for rn in loc_regions:
            if rn == data.HUB:
                coarse[rn] = ""
            elif rn in open_flags:
                coarse[rn] = rn
            else:
                self.fail("region %r has locations but no lock and no host mapping -- the client "
                          "would treat it as permanently accessible" % rn)
        region_open = {"%s Lock" % r: open_flags[r] for r in kept if r in open_flags}
        # ...plus the finale, which is never KEPT (never rolled) and so never appears in the walk
        # above, but is LOCKED. Without this its coarse key would name an item with no open flag.
        if finale_built and data.FINALE_REGION in open_flags:
            region_open["%s Lock" % data.FINALE_REGION] = open_flags[data.FINALE_REGION]
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
        allowed = set(kept) | {self.data.HUB, self.data.FINALE_REGION}
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

    def test_the_finale_region_is_regioned_and_not_just_flagged(self):
        """END TO END, BY NAME. The case that shipped wrong on 2026-07-28.

        Ashen Capital is conditional and never rollable, so it is NOT in `data.REGIONS`. Its checks
        reach slot_data through `features/finale.py` -> `gf_extra_location_flags` -> locationFlags.
        The first cut of `locationRegions` walked `[HUB] + kept` only, so those 10 got a flag and no
        region: the client's tracker could not group them, and `region_table.contains_key` is its
        "is this location ours?" test, so a hint for one of them from another player was DROPPED.
        Caught by reading a smoke-test log -- 4869 locations across 31 regions, against 4879 flags. (29 regions after the 2026-08-10 Cerulean merge; the location count is unchanged.)
        """
        # Full-region pool, so the base game is in play and the feature ARMS.
        loc_regions, coarse, loc_flags, region_open = self.emit(list(self.data.REGIONS))
        finale = self.data.FINALE_REGION
        expected = {int(a) for (_n, a, _f) in self.data.LOCATIONS[finale]}
        self.assertTrue(expected, "the finale region has no locations -- this fixture is vacuous")
        self.assertIn(finale, loc_regions,
                      "%r is absent from locationRegions; its checks would have a flag and no "
                      "region" % finale)
        self.assertEqual(set(loc_regions[finale]), expected)
        # WAS: `coarse.get(finale) == FINALE_HOST_REGION` -- "the finale is lockless, so its coarse
        # key must be its HOST". SPEC-ashen-capital-lock (2026-08-06) gave it a lock and an open
        # flag of its own, so it is its OWN coarse key now and the host is the hub (which has no
        # lock at all and could never have served as a key). The protection is identical and is the
        # sentence below it: whatever the key is, `<key> Lock` must be in regionOpenFlags, or the
        # client looks it up, finds nothing, and calls the finale permanently open.
        self.assertEqual(
            coarse.get(finale), finale,
            "the finale owns its lock now -- its coarse key must be itself, not a host")
        self.assertIn("%s Lock" % finale, region_open,
                      "the finale's own lock must be sent, or the client finds no lock item for "
                      "its coarse key and calls the finale permanently open")

    def test_a_dlc_only_pool_builds_no_finale_at_all(self):
        """The other side of the conditional seam, which FINALE_REQUIRES = () made unassertable.

        `set(FINALE_REQUIRES) <= set(kept)` was the arming test until 2026-08-06 and is now
        vacuously true for every pool, so a mirror that kept it would emit the finale's checks
        under dlc_only -- where the real feature builds nothing, because the Ashen Capital is
        base-game content. Nothing else in this file exercises an unarmed seam."""
        dlc = sorted(self.dlc_regions)
        self.assertTrue(dlc, "no DLC regions -- this fixture is vacuous")
        loc_regions, coarse, loc_flags, region_open = self.emit(dlc, eligible=dlc)
        finale = self.data.FINALE_REGION
        self.assertNotIn(finale, loc_regions)
        self.assertNotIn("%s Lock" % finale, region_open)
        for (_n, ap_id, _f) in self.data.LOCATIONS[finale]:
            self.assertNotIn(str(ap_id), loc_flags,
                             "a dlc_only seed flagged finale check %d it can never reach" % ap_id)

    def test_locationRegions_and_locationFlags_cover_the_same_ids_including_feature_seams(self):
        """The totality check, stated against data.LOCATIONS rather than against the mirror itself."""
        loc_regions, _c, loc_flags, _ro = self.emit(list(self.data.REGIONS))
        regioned = {i for ids in loc_regions.values() for i in ids}
        flagged = {int(k) for k in loc_flags}
        self.assertEqual(len(regioned), len(flagged),
                         "%d regioned vs %d flagged -- the shipped bug was exactly this gap"
                         % (len(regioned), len(flagged)))
        every = {int(a) for rows in self.data.LOCATIONS.values() for (_n, a, _f) in rows}
        self.assertEqual(regioned, every,
                         "a full-region seed must region EVERY location in data.LOCATIONS")

    # -- the mirror is the risk --------------------------------------------
    def test_the_mirror_matches_core_py(self):
        """This suite REBUILDS the emit (core.py needs AP). Pin the source it mirrors, so a change
        to core._base_slot_data that this file does not follow fails HERE rather than shipping."""
        src = open(os.path.join(GF, "eldenring", "core.py"), encoding="utf-8").read()
        for needle in ("contract.LOCATION_REGIONS: loc_regions",
                       "contract.REGION_COARSE_KEYS: coarse_keys",
                       "for rn in [HUB] + kept:",
                       "coarse_keys[rn] = \"\"",
                       "_ap_region = {int(ap): rn for rn, rows in LOCATIONS.items()",
                       # SPEC-ashen-capital-lock, 2026-08-06: the needle here WAS
                       # "_lockless_host = {FINALE_REGION: FINALE_HOST_REGION}". That branch is
                       # deleted -- the finale has its own open flag -- and these two lines are
                       # what replaced it: the finale's lock is added to regionOpenFlags so its
                       # ordinary `rn in REGION_OPEN_FLAGS` coarse key resolves.
                       "elif rn in REGION_OPEN_FLAGS:",
                       "region_open[ASHEN_LOCK] = REGION_OPEN_FLAGS[FINALE_REGION]"):
            self.assertIn(needle, src,
                          "core._base_slot_data no longer contains %r -- this mirror is stale and "
                          "is now testing something the world does not do." % needle)
        # ...and the deleted branch must STAY deleted: if a lockless host ever comes back, this
        # mirror's coarse-key walk (which now has only one fallback, `self.fail`) is wrong again.
        # (matched on the BRANCH, not the name: core's comment still explains the deletion, and a
        # bare-name check would trip on the explanation rather than on the code coming back)
        self.assertNotIn(
            "elif rn in _lockless_host:", src,
            "core._base_slot_data grew a lockless-host branch back -- the mirror above dropped it "
            "when the Ashen Capital got its own open flag, so it is stale again")


if __name__ == "__main__":
    unittest.main()
