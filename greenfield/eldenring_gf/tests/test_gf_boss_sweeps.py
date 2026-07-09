"""Boss-sweep SCOPING gate (tier A): the 2026-07-08 class-scoped sweep model must hold.

gen_data.py scopes each boss's dungeon-sweep by the boss's CLASS (from the authoritative
DisplayBossHealthBar set, tools/datamine_boss_healthbars.py -> BOSS_HEALTHBARS):
  * legacy / interior (region majors)   -> REGION-WIDE
  * catacomb / cave / tunnel (m30/31/32)-> MAP-LOCAL (only that dungeon map's own checks)
  * field / overworld (m60)             -> OWN-TILE + FILLER-ONLY

These are the invariants a regen (or a member-loop / classifier change) must not break. Independent
of gen_data's derivation: we read the emitted modules + region_map.csv and re-derive each member's
map straight from its flag, so a bug in the generator can't hide behind shared code.

Run:  python greenfield/eldenring_gf/tests/test_gf_boss_sweeps.py
"""
import csv
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)
GREENFIELD = os.path.dirname(GF_PKG)
# region_map.csv is gen_data's INPUT; in the SOURCE tree it sits beside the package (GREENFIELD/), and
# the world-install step copies it INTO the installed package (GF_PKG/) so the sweep-scoping oracle runs
# in the installed-world pytest too. Resolve from either -- first existing wins.
REGION_MAP_CSV = next((p for p in (os.path.join(GF_PKG, "region_map.csv"),
                                   os.path.join(GREENFIELD, "region_map.csv")) if os.path.isfile(p)),
                      os.path.join(GF_PKG, "region_map.csv"))

# = contract.IMPORTANT_LOCATION_TYPES (a superset of BIG_TICKET_TYPES). A field sweep must contain
# none of these -- felling a field boss hands out filler only. Kept in sync with contract by
# test_field_exclude_matches_contract below (drift guard).
FIELD_EXCLUDE = frozenset({"Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered",
                           "Basin", "GreatRune", "KeyItem", "Legendary", "Shop"})


def _mod(name):
    path = os.path.join(GF_PKG, name + ".py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("gf_" + name + "_sweepcheck", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _mp2(m):
    return None if (not m or m == "PENDING") else "_".join(m.split("_")[:2])


class BossSweepScoping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sw = _mod("boss_sweeps")
        cls.bh = _mod("boss_healthbars")
        cls.d = _mod("data")
        cls.lt = getattr(_mod("location_tags"), "LOCATION_TAGS", {}) if _mod("location_tags") else {}
        if not (cls.sw and cls.bh and cls.d):
            raise unittest.SkipTest("boss_sweeps/boss_healthbars/data not generated")
        cls.BH = cls.bh.BOSS_HEALTHBARS
        cls.DS = cls.sw.DUNGEON_SWEEPS
        # ap-id -> (flag, region) from data.py
        cls.ap_flag, cls.ap_region = {}, {}
        for region, locs in cls.d.LOCATIONS.items():
            for (_name, ap, flag) in locs:
                cls.ap_flag[ap] = int(flag); cls.ap_region[ap] = region
        # flag -> raw map from region_map.csv (may be PENDING for unplaced dungeon checks). Without it
        # _eff_map would silently degrade to flag-only decode and report FALSE map-local/own-tile
        # mismatches, so skip loudly instead of running blind. The world-install step copies region_map.csv
        # into the package (GF_PKG) so this normally RUNS in the installed-world pytest; the skip is only a
        # safety net for a fresh clone where the copy was missed.
        if not os.path.isfile(REGION_MAP_CSV):
            raise unittest.SkipTest(
                "region_map.csv not found beside the package or installed into it -- copy "
                "greenfield/region_map.csv into the world (the install step does this) to run the "
                "sweep-scoping oracle")
        cls.flag_map = {}
        for r in csv.DictReader(open(REGION_MAP_CSV, encoding="utf-8")):
            if str(r["flag"]).lstrip("-").isdigit():
                cls.flag_map[int(r["flag"])] = r["map"] or ""

    def _eff_map(self, ap):
        """A member's effective map: region_map's map, or -- for an unplaced dungeon check whose flag
        encodes the map (30.XX.. -> m30_XX) -- the flag-recovered map. Re-derived independently."""
        raw = self.flag_map.get(self.ap_flag.get(ap, -1), "")
        if raw and raw != "PENDING":
            return raw
        fs = str(self.ap_flag.get(ap, ""))
        if len(fs) >= 8 and fs[:2] in ("30", "31", "32"):
            return f"m{fs[:2]}_{fs[2:4]}_00_00"
        return raw

    def _members_by_class(self, cls_name):
        for ent, members in self.DS.items():
            info = self.BH.get(ent)
            if info and info[2] == cls_name:
                yield ent, info, members

    def test_field_exclude_matches_contract(self):
        ct = _mod("contract")
        if not ct:
            self.skipTest("contract.py not importable")
        want = set(getattr(ct, "IMPORTANT_LOCATION_TYPES", [])) | set(getattr(ct, "BIG_TICKET_TYPES", []))
        self.assertEqual(
            set(FIELD_EXCLUDE), want,
            "FIELD_EXCLUDE drifted from contract.IMPORTANT_LOCATION_TYPES u BIG_TICKET_TYPES; "
            "sync the field filler-only cut. got=%s want=%s" % (sorted(FIELD_EXCLUDE), sorted(want)))

    def test_field_sweeps_are_filler_only(self):
        bad = []
        for ent, info, members in self._members_by_class("field"):
            for ap in members:
                if FIELD_EXCLUDE & set(self.lt.get(ap, ())):
                    bad.append((ent, info[3], ap, sorted(FIELD_EXCLUDE & set(self.lt.get(ap, ())))))
        self.assertEqual(bad, [], str(len(bad)) + " field-boss sweep member(s) are important/big-ticket "
                         "-- field sweeps must be filler-only. Sample: " + repr(bad[:5]))

    def test_field_sweeps_are_own_tile(self):
        bad = []
        for ent, info, members in self._members_by_class("field"):
            tile = info[1]  # m60_XX_YY
            for ap in members:
                if not (self._eff_map(ap) or "").startswith(tile):
                    bad.append((ent, info[3], tile, ap, self._eff_map(ap)))
        self.assertEqual(bad, [], str(len(bad)) + " field-boss sweep member(s) are NOT on the boss's own "
                         "m60 tile. Sample: " + repr(bad[:5]))

    def test_dungeon_sweeps_are_map_local(self):
        bad = []
        for cls_name in ("catacomb", "cave", "tunnel", "dungeon"):
            for ent, info, members in self._members_by_class(cls_name):
                bmap = info[0]  # mAA_BB
                for ap in members:
                    if _mp2(self._eff_map(ap)) != bmap:
                        bad.append((cls_name, ent, info[3], bmap, ap, self._eff_map(ap)))
        self.assertEqual(bad, [], str(len(bad)) + " catacomb/cave/tunnel sweep member(s) are outside the "
                         "boss's own dungeon map (should be map-local). Sample: " + repr(bad[:5]))

    def test_all_members_in_sweep_region(self):
        bad = []
        for ent, members in self.DS.items():
            reg = self.sw.SWEEP_REGION.get(ent)
            for ap in members:
                if self.ap_region.get(ap) != reg:
                    bad.append((ent, ap, "sweep=" + str(reg), "loc=" + str(self.ap_region.get(ap))))
        self.assertEqual(bad, [], str(len(bad)) + " sweep member(s) whose location region != the sweep's "
                         "region (cross-region leak). Sample: " + repr(bad[:5]))

    def test_recovered_catacombs_have_members(self):
        """The 9 catacombs whose checks were unplaced (flag_prefix/PENDING) must sweep them after the
        grace-derived map recovery -- guards the 'catacomb boss sweeps its whole catacomb' fix."""
        recovered = {30010800: "Impaler's", 30020800: "Stormfoot", 30040800: "Murkwater",
                     30060800: "Cliffbottom", 30080800: "Sainted Hero's Grave", 30120800: "Unsightly",
                     30140800: "Minor Erdtree", 30150800: "Caelid Catacombs", 30160800: "War-Dead"}
        empty = [f"{name} ({ent})" for ent, name in recovered.items() if not self.DS.get(ent)]
        self.assertEqual(empty, [], "recovered catacomb boss(es) have EMPTY sweeps (flag_prefix map "
                         "recovery regressed): " + repr(empty))

    def test_legacy_sweeps_are_filler_only(self):
        """Legacy (region-major) sweeps must be FILLER-ONLY now -- felling a region boss auto-grants
        only the region's filler, never an important/big-ticket-tagged check (same cut as field). The
        member list is baked from location tags at gen time; boss_locks.slot_data emits it verbatim."""
        bad = []
        for ent, info, members in self._members_by_class("legacy"):
            for ap in members:
                hit = FIELD_EXCLUDE & set(self.lt.get(ap, ()))
                if hit:
                    bad.append((ent, info[3], ap, sorted(hit)))
        self.assertEqual(bad, [], str(len(bad)) + " legacy sweep member(s) are important/big-ticket -- "
                         "region-major sweeps must be filler-only. Sample: " + repr(bad[:5]))

    def test_legacy_filler_only_is_nontrivial(self):
        """Guard the cut actually bites: at least one important/big-ticket-tagged check must sit in a
        legacy sweep's own region yet be EXCLUDED from the sweep. Fails if legacy silently reverts to
        region-wide (or the tag data drops), which test_legacy_sweeps_are_filler_only alone would miss
        (an empty/degenerate sweep is vacuously filler-only)."""
        for ent, info, members in self._members_by_class("legacy"):
            reg = self.sw.SWEEP_REGION.get(ent)
            memset = set(members)
            for ap, r in self.ap_region.items():
                if r == reg and ap not in memset and (FIELD_EXCLUDE & set(self.lt.get(ap, ()))):
                    return  # found an excluded important check in a legacy sweep's region -> cut bites
        self.fail("no important/big-ticket check is excluded from any legacy sweep -- the filler-only "
                  "cut looks like a no-op (region-wide regression or missing location tags)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
