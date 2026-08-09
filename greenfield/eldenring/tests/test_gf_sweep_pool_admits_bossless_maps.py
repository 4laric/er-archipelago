"""A check on a BOSSLESS interior map must still reach its region's sweep pool -- issue #444.

THE MOTIVATING CASE (CONTRIBUTING rule 11), and it is a fixture below, by name.

    bobler, 2026-08-09, apworld 0.3.9, `num_regions: 3` + `dlc_only: true`:

        [APC] Boss sweep (Shadow Keep) [trigger flag 2049480800] -- 1 check(s) granted.

    Commander Gaius owns a whole m61 tile and no building, so the map-local pass gave him the one
    filler check on it. The REGION REMAINDER pass exists to top up exactly that boss -- its own
    comment names Astel going 33 -> 0 as the reason it deals to the emptiest first. It topped up
    nobody, because Shadow Keep's remainder was 5 when it should have been 41.

    Instrumented at the divvy: `mem=216 filler=213 remainder=5 ents=8`, against 271 locations in the
    region. The missing 36 all live on m21_02 (West Rampart), and their provenance is identical to
    the members that DID sweep -- `msrc=flag_tile`, same as 93 of Messmer's own 100.

THE DEFECT IS ONE SET ASKED TWO QUESTIONS. `_LEGACY_SWEEP_MAPS` was derived from BOSS_HEALTHBARS --
the maps that HOST a legacy boss -- and the membership gate reused it to decide which checks MAY BE
SWEPT. m21_02 hosts no healthbar boss, so it was excluded from the pool *because* it has no owner,
when having no owner is the qualification for the remainder pool in the first place.

WHAT THIS IS NOT. Not a rebalance, and the numbers say so. The remainder deals EQUAL slices
(`_ents[_j % len(_ents)]`); dealing to the emptiest first fixes the ORDER, not the size, and only
bites when the pool is smaller than the host count. So Messmer and the Hippo gain 5 each alongside
Gaius. This stops 49 checks being discarded; moving share between hosts is a share cap, and a
separate argument.

MEASURED, the whole blast radius: 59 checks over 6 (region, map) pairs -- Shadow Keep/m21_02 36,
Siofra River/m12_07 13, Roundtable Hold 8 (HUB, dropped downstream anyway), Limgrave/m11_10 2.
Triggers 219 -> 219, member links 3677 -> 3726.

Run:  python3 greenfield/eldenring/tests/test_gf_sweep_pool_admits_bossless_maps.py
"""
import csv
import importlib.util
import os
import re
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF = os.path.dirname(HERE)                      # .../eldenring
GREENFIELD = os.path.dirname(GF)                # .../greenfield


def _load(modname, relpath):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(GF, relpath))
    m = importlib.util.module_from_spec(spec)
    sys.modules[modname] = m
    spec.loader.exec_module(m)
    return m


if "eldenring" not in sys.modules:
    _pkg = types.ModuleType("eldenring")
    _pkg.__path__ = [GF]
    sys.modules["eldenring"] = _pkg

contract = _load("eldenring.contract", "contract.py")
_load("eldenring.registry", "registry.py")
data = _load("eldenring.data", "data.py")
sw = _load("eldenring.boss_sweeps", "boss_sweeps.py")
tags_mod = _load("eldenring.location_tags", "location_tags.py")

DS = sw.DUNGEON_SWEEPS
SR = sw.SWEEP_REGION
LOCATION_TAGS = getattr(tags_mod, "LOCATION_TAGS", {})

# The premium classes a filler sweep may never pay out. Taken from the contract rather than
# re-listed, for the same reason test_gf_boss_sweeps.test_field_exclude_matches_contract exists: a
# new class must not be able to appear in the vocabulary and stay quietly sweep-eligible.
EXCLUDE = frozenset(contract.SURFACE_CLASSES)

# Mirrors gen_data._is_interior_member_map. Kept as a literal here ON PURPOSE: this suite is the
# consumer-side statement of the rule, and importing the producer's own predicate would let the two
# drift together and still agree. gen_data is not importable from a test anyway (it regenerates).
_INTERIOR = re.compile(r"^m\d\d_\d\d$")
_DUNGEON_PREFIXES = ("m30", "m31", "m32", "m34", "m39", "m40", "m41", "m42", "m43")
_SWEEP_EXCLUDED_BMAPS = {"m10_01"}          # the Chapel of Anticipation -- see gen_data


def _is_interior_member_map(mp):
    return (bool(mp) and _INTERIOR.match(mp) is not None
            and not mp.startswith(("m60", "m61"))
            and mp[:3] not in _DUNGEON_PREFIXES
            and mp not in _SWEEP_EXCLUDED_BMAPS)


def _check_maps():
    """flag -> {map prefix, ...}. One-to-many by design (build_check_maps.py's own header)."""
    out = {}
    with open(os.path.join(GREENFIELD, "check_maps.tsv"), encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if not row or row[0].startswith("#") or not row[0].isdigit():
                continue
            mp = "_".join((row[1] or "").split("_")[:2])
            if mp:
                out.setdefault(int(row[0]), set()).add(mp)
    return out


CHECK_MAPS = _check_maps()
SWEPT = set().union(*[set(v) for v in DS.values()]) if DS else set()
# region -> [(name, ap, flag), ...] for every region that has at least one sweep host. A region with
# no host has nowhere to deal a remainder to, so it is out of scope for this rule, not a violation.
HOSTED_REGIONS = {SR[t] for t in DS if SR.get(t) and SR[t] != data.HUB}

# The motivating case, as named constants so rule 11's exemplar survives a regen that renumbers
# everything around it.
GAIUS = 2049480800
WEST_RAMPART = "m21_02"
WEST_RAMPART_REGION = "Shadow Keep"


def _orphans():
    """Untagged filler on a bossless interior map, in a hosted region, in NO sweep group."""
    out = []
    for region in sorted(HOSTED_REGIONS):
        for (name, ap, flag) in data.LOCATIONS.get(region, ()):
            if ap in SWEPT:
                continue
            if EXCLUDE & set(LOCATION_TAGS.get(ap, ())):
                continue
            maps = CHECK_MAPS.get(flag, set())
            if any(_is_interior_member_map(mp) for mp in maps):
                out.append((region, sorted(maps), name, ap))
    return out


class TheWestRampartIsSwept(unittest.TestCase):
    """bobler's case, asserted rather than asserted-in-prose."""

    def test_the_bossless_map_contributes_members(self):
        rampart = [ap for (_n, ap, f) in data.LOCATIONS[WEST_RAMPART_REGION]
                   if WEST_RAMPART in CHECK_MAPS.get(f, set())
                   and not (EXCLUDE & set(LOCATION_TAGS.get(ap, ())))]
        self.assertTrue(rampart, "WITNESS: no untagged filler found on %s -- the fixture moved, so "
                                 "this suite is asserting nothing" % WEST_RAMPART)
        missing = [ap for ap in rampart if ap not in SWEPT]
        self.assertEqual(missing, [],
                         "%d of %d %s filler check(s) are in no sweep group. %s hosts no healthbar "
                         "boss, and that is exactly why its checks belong to the region REMAINDER -- "
                         "if the membership gate is keyed on boss-hosting maps again, this is the "
                         "first thing to go." % (len(missing), len(rampart), WEST_RAMPART,
                                                 WEST_RAMPART))

    def test_gaius_is_not_a_one_check_sweep(self):
        """The symptom the player actually reported. A FLOOR, not a pin: the exact size moves with
        every regen that touches Shadow Keep's filler, but 1 is the number that made the sweep read
        as broken in game, and any regression to a near-empty group lands back there."""
        self.assertIn(GAIUS, DS, "Commander Gaius lost his sweep group entirely")
        self.assertGreater(len(DS[GAIUS]), 1,
                           "Gaius is back to a %d-check sweep -- the region remainder is not "
                           "reaching the tile bosses again (bobler 2026-08-09)" % len(DS[GAIUS]))


class NoBosslessInteriorMapIsOrphaned(unittest.TestCase):
    """The general rule the fixture above is one instance of, plus the remainder it does NOT reach."""

    # WHAT IS LEFT, and WHY -- measured 2026-08-09, not guessed. Every one of these rows reaches the
    # membership gate with `map == 'PENDING'`: the row's own map column never resolved, so `_mp2`
    # returns None and every map-keyed branch fails, even though check_maps.tsv (a DIFFERENT
    # datamine, physical-position granular) does know where they are.
    #
    #     WHYNOT: flag=28007070  method=flag_prefix    map='PENDING'  region=Abyssal
    #     WHYNOT: flag=400918    method=global         map='PENDING'  region=Ainsel River
    #     WHYNOT: flag=11057030  method=global_filler  map='PENDING'  region=Ashen Capital
    #
    # 🛑 So this is NOT the bug this suite is about, and widening the gate to consult check_maps.tsv
    # is not the fix: `_recovered_m60_tile`'s own docstring already ruled on the identical situation
    # for m60 -- "PUBLISH the recovered tile (write it into the `map` column) so the oracle can see
    # it -- do not widen this gate". The same answer applies here.
    #
    # 🛑🛑 KEYED ON (region, map), NOT on ap ids: a regen renumbers ap ids (#249 did), and a ratchet
    # that churns every regen teaches people to rebaseline it without looking. If this dict MOVES,
    # that is a finding -- say which pairs entered, which left, and whether an input got better or a
    # predicate got looser.
    PENDING_MAP_REMAINDER = {
        ("Abyssal", "m28_00"): 3,
        ("Ainsel River", "m12_01"): 1,
        ("Ashen Capital", "m11_05"): 1,
        ("Mohgwyn", "m12_05"): 1,
        ("Siofra River", "m12_02"): 1,
        ("Stone Coffin", "m22_00"): 9,
    }

    def test_the_only_orphans_left_are_the_pending_map_rows(self):
        self.assertTrue(HOSTED_REGIONS, "WITNESS: no hosted regions -- nothing was examined")
        seen = {}
        for region, maps, _name, _ap in _orphans():
            for mp in maps:
                if _is_interior_member_map(mp):
                    seen[(region, mp)] = seen.get((region, mp), 0) + 1
        self.assertEqual(
            seen, self.PENDING_MAP_REMAINDER,
            "the orphan set MOVED. Anything NEW here is untagged filler on an interior map that a "
            "region with a host failed to sweep -- check whether its row carries a real `map` or "
            "'PENDING' before rebaselining this dict.")

    def test_the_west_rampart_is_not_in_the_remainder(self):
        """The regression guard proper: m21_02 was the largest single entry in that dict before this
        change (36 of 59), and it is gone because its rows DO carry a map."""
        self.assertNotIn((WEST_RAMPART_REGION, WEST_RAMPART), self.PENDING_MAP_REMAINDER)
        rampart_orphans = [o for o in _orphans() if WEST_RAMPART in o[1]]
        self.assertEqual(rampart_orphans, [],
                         "%s is orphaned again: %r" % (WEST_RAMPART, rampart_orphans[:3]))


class TheChapelOfAnticipationFoldIsStillHalfApplied(unittest.TestCase):
    """A ratchet on a leak this change does NOT fix, so it cannot widen unnoticed.

    `_SWEEP_EXCLUDED_BMAPS` stops the Grafted Scion GRANTING Stormveil's filler (dafranky67, Nexus
    2026-07-29). It does not stop the reverse: one m10_01 check is a member of Godrick's group on
    main, and still is here. It arrives via the `method in ("treasure", "emevd")` branch, which has
    never consulted a map -- so the fold has three consumers and the exception reaches two.

    🛑 Pinned by NAME, not by ap id, for the #249 renumbering reason. Growing this list means the
    Chapel is being paid out more, which is the reported bug pointing the other way.
    """

    KNOWN_LEAK = ("Stormveil :: Stormhawk Deenh - m10_01 [f10017900]",)

    def test_exactly_the_known_chapel_member_leaks(self):
        leaked = tuple(sorted(
            name for region in HOSTED_REGIONS
            for (name, ap, f) in data.LOCATIONS.get(region, ())
            if "m10_01" in CHECK_MAPS.get(f, set()) and ap in SWEPT))
        self.assertEqual(leaked, self.KNOWN_LEAK,
                         "the Chapel of Anticipation leak MOVED -- it was one check via the "
                         "treasure/emevd branch. New entries mean a sweep now pays out the intro "
                         "area more widely than main does.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
