"""CO-CHECK model tests (SPEC-flag-lot-item-model): N co-firing checks on one shared flag.

One getItemFlagId can drive several ItemLotParam lots (Messmer 510460 -> lot 10460 Remembrance of
the Impaler + lot 10461 Messmer's Kindling). The client's flag poll is keyed by AP LOCATION ID
(flagpoll.rs location_flags: HashMap<i64,u32>), so N locations sharing a flag all co-fire -- the
faithful projection is one check PER LOT (gen_data.CO_CHECK_FLAGS allowlist + the append-only
co_check_ids.tsv registry), each blanking its OWN lot.

What is testable WHERE (be explicit -- half this model only materializes at a Windows regen):
  * SANDBOX / any clone (this file, always-on half): registry + capture integrity
    (co_check_ids.tsv x flag_lots.tsv), the static check_lots_table.json overlay shape, and the
    coverage gate's co-check-group relaxation (synthetic groups -- accidental aliases must STILL
    raise; declared distinct-lot groups must pass).
  * POST-REGEN only (`build.ps1 -Greenfield`): the projected sibling LOCATIONS/LOCATION_ITEM
    entries and check_lots_data.LOCATION_LOT. Those tests self-skip while LOCATION_LOT is empty,
    and ARM AUTOMATICALLY on the first regen -- do not delete the skips, they are the arming pin.

Input tsvs resolve from the source tree (greenfield/) or beside the installed world (copied like
region_map.csv -- AGENTS.md §5); absent inputs skip loudly rather than vacuously pass.
"""
import csv
import importlib.util
import json
import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                       # .../eldenring (the world package)
_PKG = "co_check_test_pkg"

COCHECK_BASE = 7900000                               # must match gen_data.COCHECK_BASE
# The seeded allowlist (mechanism-first first cut -- gen_data.CO_CHECK_FLAGS). Pinned here so the
# registry-completeness half runs without importing gen_data (which executes the whole pipeline).
# Widening the allowlist updates BOTH (the pin is the reminder that the registry must grow with it).
SEEDED_FLAGS = {
    510460: {("map", 10461)},        # Messmer's Kindling beside the Remembrance primary
    510440: {("map", 10441)},        # Scadutree Fragment beside the Thorns primary
    520160: {("map", 20161)},        # Golden Seed beside the Ogha-ash primary
    400696: {("map", 106931)},       # Prayer Room Key beside the Flame-Skewer primary
}


def _find_input(fname):
    """greenfield/<fname> in a source tree, or <world>/<fname> when copied beside the install."""
    for cand in (os.path.join(os.path.dirname(GF_PKG), fname), os.path.join(GF_PKG, fname)):
        if os.path.isfile(cand):
            return cand
    return None


def _path_load(modname):
    if _PKG not in sys.modules:
        pkg = types.ModuleType(_PKG)
        pkg.__path__ = [GF_PKG]
        sys.modules[_PKG] = pkg
    fq = _PKG + "." + modname
    if fq in sys.modules:
        return sys.modules[fq]
    spec = importlib.util.spec_from_file_location(fq, os.path.join(GF_PKG, modname + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fq] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        del sys.modules[fq]
        raise
    return mod


def _load_registry(path):
    out = {}
    with open(path, encoding="utf-8-sig") as fh:
        for ln in fh:
            if not ln.strip() or ln.lstrip().startswith("#") or ln.startswith("flag\t"):
                continue
            p = ln.rstrip("\n").split("\t")
            out[(int(p[0]), p[1].strip(), int(p[2]))] = int(p[3])
    return out


def _load_families(path):
    fam = {}
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            try:
                fam.setdefault(int(r["flag"]), set()).add((r["table"], int(r["lot"])))
            except (KeyError, TypeError, ValueError):
                continue
    return fam


def _primary(family_lots):
    """The family's PRIMARY lot: lowest, map-table first -- the lot the region_map scan named the
    original row after (gen_data's projection uses the same ordering)."""
    return sorted(family_lots, key=lambda t: (0 if t[0] == "map" else 1, t[1]))[0]


class CoCheckRegistry(unittest.TestCase):
    """Sandbox half: registry x capture integrity. No AP, no regen needed."""

    @classmethod
    def setUpClass(cls):
        reg_p = _find_input("co_check_ids.tsv")
        fam_p = _find_input("flag_lots.tsv")
        if reg_p is None or fam_p is None:
            raise unittest.SkipTest("co_check_ids.tsv / flag_lots.tsv not beside the world or in "
                                    "the source tree (copy them like region_map.csv -- AGENTS.md 5)")
        cls.registry = _load_registry(reg_p)
        cls.families = _load_families(fam_p)

    def test_registry_band_and_uniqueness(self):
        ids = list(self.registry.values())
        self.assertEqual(len(ids), len(set(ids)), "registry ap_ids must be unique -- ids are "
                         "allocated once and never reused")
        for (fl, tb, lot), ap in self.registry.items():
            self.assertGreaterEqual(ap, COCHECK_BASE,
                                    f"registry ap {ap} (flag {fl}) below the COCHECK band -- the "
                                    f"band is what keeps registry ids disjoint from positional ids")
            self.assertIn(tb, ("map", "enemy"))

    def test_registry_keys_exist_in_capture(self):
        for (fl, tb, lot) in self.registry:
            fam = self.families.get(fl)
            self.assertTrue(fam, f"registry flag {fl} has no flag_lots.tsv family")
            self.assertIn((tb, lot), fam,
                          f"registry ({fl}, {tb}, {lot}) not in the captured family {sorted(fam)} "
                          f"-- registry and capture disagree; reconcile, never delete the row")

    def test_registry_never_holds_a_primary(self):
        """The primary keeps its positional region_map ap_id; only SIBLINGS get registry ids."""
        for (fl, tb, lot) in self.registry:
            prim = _primary(self.families[fl])
            self.assertNotEqual((tb, lot), prim,
                                f"registry row ({fl}, {tb}, {lot}) is the family PRIMARY -- the "
                                f"primary's ap_id is its region_map row's, never a registry id")

    def test_seeded_allowlist_fully_registered(self):
        """Every seeded CO_CHECK_FLAGS sibling has its registry row (gen would FATAL without it --
        this catches the drift in-sandbox, before anyone burns a regen on it)."""
        for fl, sibs in SEEDED_FLAGS.items():
            fam = self.families.get(fl, set())
            self.assertGreaterEqual(len(fam), 2, f"seeded flag {fl} is not a shared flag?")
            expect = fam - {_primary(fam)}
            self.assertEqual(expect, sibs,
                             f"seeded flag {fl}: pinned sibling set {sorted(sibs)} != captured "
                             f"{sorted(expect)} -- capture changed; update SEEDED_FLAGS + registry")
            for (tb, lot) in sibs:
                self.assertIn((fl, tb, lot), self.registry,
                              f"seeded sibling (flag {fl}, {tb} lot {lot}) missing from "
                              f"co_check_ids.tsv -- APPEND it (next free id)")


class StaticTableOverlay(unittest.TestCase):
    """check_lots_table.json: the shared-flag overlay shape (replaces last-write-wins)."""

    @classmethod
    def setUpClass(cls):
        p = os.path.join(GF_PKG, "check_lots_table.json")
        if not os.path.isfile(p):
            raise unittest.SkipTest("check_lots_table.json absent")
        cls.tbl = json.load(open(p, encoding="utf-8"))

    def test_overlay_present_and_consistent(self):
        for key in ("map", "enemy"):
            self.assertIn(key + "_v2", self.tbl, "overlay key missing -- regenerate "
                          "tools/gen_check_lots_table.py")
            for k, ents in self.tbl[key + "_v2"].items():
                self.assertIsInstance(ents, list)
                self.assertGreaterEqual(len(ents), 2,
                                        f"{key}_v2[{k}] has <2 entries -- overlay is multi-lot only")
                lots = [e["lot"] for e in ents]
                self.assertEqual(lots, sorted(lots), f"{key}_v2[{k}] not lot-sorted")
                self.assertEqual(len(lots), len(set(lots)), f"{key}_v2[{k}] duplicate lots")
                # legacy entry must be the overlay's FIRST (lowest lot) -- deterministic, and a
                # legacy-only consumer (shipped static_lots.rs) blanks the primary's lot.
                self.assertEqual(self.tbl[key][k], ents[0],
                                 f"legacy {key}[{k}] != {key}_v2[{k}][0] -- legacy must be the "
                                 f"lowest lot, never scan-order luck")

    def test_known_families_in_overlay(self):
        v2 = self.tbl["map_v2"]
        self.assertEqual([e["lot"] for e in v2["510460"]], [10460, 10461])
        self.assertEqual([e["lot"] for e in v2["520160"]], [20160, 20161])
        self.assertEqual([e["lot"] for e in v2["510440"]], [10440, 10441])
        # 400696: sibling 106930 is an Ash of War (GEM, non-goods) -> no goods slots -> only lot
        # 106931 carries a goods blank: single-entry, so NO overlay, and legacy points at 106931.
        self.assertNotIn("400696", v2)
        self.assertEqual(self.tbl["map"]["400696"]["lot"], 106931)

    def test_coverage_loader_normalizes_to_lists(self):
        cov = _path_load("coverage")
        sm, se, si = cov._load_static_table()
        self.assertTrue(sm, "static table empty")
        for fl, ents in list(sm.items())[:50]:
            self.assertIsInstance(ents, list, "normalized map table must be flag -> [entry, ...]")
        self.assertEqual([e["lot"] for e in sm[510460]], [10460, 10461],
                         "overlay must win over the single legacy entry in the normalized view")
        # _entries tolerates a legacy-shaped injected dict (the tripwire tests build those)
        self.assertEqual(cov._entries({1: {"lot": 5, "slots": [1]}}, 1), [{"lot": 5, "slots": [1]}])


class CoverageCoCheckRelaxation(unittest.TestCase):
    """The no-alias rule is now the co-check-group invariant. Synthetic proof both ways:
    accidental aliases (no bindings / colliding lots) still raise; declared groups pass."""

    @classmethod
    def setUpClass(cls):
        cls.cov = _path_load("coverage")
        cls.records, cls.ctx = cls.cov.build_coverage()

    def _two_nonshop(self):
        it = (r for r in self.records.values()
              if r.detect_kind == "event_flag" and r.ap_id not in self.ctx["shop_flag_by_ap"])
        return next(it), next(it)

    def test_accidental_alias_still_raises(self):
        a, b = self._two_nonshop()
        old = b.detect_flag
        try:
            b.detect_flag = a.detect_flag
            det = self.cov.check_detection(self.records, self.ctx)
            hit = [v for v in det if v.ap_id in (a.ap_id, b.ap_id)]
            self.assertGreaterEqual(len(hit), 2,
                                    "an undeclared shared flag must violate for BOTH sharers")
            self.assertIn("co-check", hit[0].detail)
        finally:
            b.detect_flag = old

    def test_declared_distinct_lot_group_passes(self):
        a, b = self._two_nonshop()
        old_flag, old_ll = b.detect_flag, dict(self.ctx["location_lot"])
        try:
            b.detect_flag = a.detect_flag
            self.ctx["location_lot"] = dict(old_ll)
            self.ctx["location_lot"][a.ap_id] = ("map", 111)
            self.ctx["location_lot"][b.ap_id] = ("map", 222)
            det = self.cov.check_detection(self.records, self.ctx)
            self.assertEqual([v for v in det if v.ap_id in (a.ap_id, b.ap_id)], [],
                             "a declared distinct-lot co-check group must be detection-legal")
        finally:
            b.detect_flag = old_flag
            self.ctx["location_lot"] = old_ll

    def test_same_lot_bindings_still_raise(self):
        a, b = self._two_nonshop()
        old_flag, old_ll = b.detect_flag, dict(self.ctx["location_lot"])
        try:
            b.detect_flag = a.detect_flag
            self.ctx["location_lot"] = dict(old_ll)
            self.ctx["location_lot"][a.ap_id] = ("map", 111)
            self.ctx["location_lot"][b.ap_id] = ("map", 111)   # two checks, ONE lot: not a group
            det = self.cov.check_detection(self.records, self.ctx)
            self.assertGreaterEqual(len([v for v in det if v.ap_id in (a.ap_id, b.ap_id)]), 2,
                                    "two sharers bound to the SAME lot must still be an alias "
                                    "violation (distinctness is what makes it a group)")
        finally:
            b.detect_flag = old_flag
            self.ctx["location_lot"] = old_ll

    def test_committed_data_has_no_undeclared_aliases(self):
        det = self.cov.check_detection(self.records, self.ctx)
        self.assertEqual([v.detail for v in det], [],
                         "committed data must be alias-clean (declared groups excepted)")


class PostRegenProjection(unittest.TestCase):
    """ARMED BY THE FIRST `-Greenfield` REGEN (LOCATION_LOT lands in check_lots_data.py). Until
    then these skip -- explicitly, so the pre-regen state is visible, never silently green."""

    @classmethod
    def setUpClass(cls):
        cls.cld = _path_load("check_lots_data")
        cls.location_lot = {int(k): (v[0], int(v[1]))
                            for k, v in getattr(cls.cld, "LOCATION_LOT", {}).items()}
        if not cls.location_lot:
            raise unittest.SkipTest("pre-regen: check_lots_data.LOCATION_LOT empty -- the co-check "
                                    "projection bakes at the next `build.ps1 -Greenfield`")
        cls.data = _path_load("data")
        cls.item_ids = _path_load("item_ids")

    def _groups(self):
        by_flag = {}
        for region, locs in self.data.LOCATIONS.items():
            for (_n, ap, fl) in locs:
                by_flag.setdefault(int(fl), []).append((ap, region))
        return {fl: v for fl, v in by_flag.items() if len(v) > 1}

    def test_groups_bound_distinct_and_coherent(self):
        for fl, members in self._groups().items():
            binds = [self.location_lot.get(ap) for (ap, _r) in members]
            self.assertTrue(all(b is not None for b in binds),
                            f"shared flag {fl}: every member needs a LOCATION_LOT binding")
            self.assertEqual(len(set(binds)), len(binds),
                             f"shared flag {fl}: member lots must be pairwise distinct")
            regions = {r for (_ap, r) in members}
            self.assertEqual(len(regions), 1,
                             f"shared flag {fl}: co-checks are one physical acquisition and must "
                             f"share a region, got {sorted(regions)}")

    def test_count_neutrality_items_follow_locations(self):
        LOCATION_ITEM = self.item_ids.LOCATION_ITEM
        for fl, members in self._groups().items():
            for (ap, _r) in members:
                if ap >= COCHECK_BASE:
                    self.assertIn(ap, LOCATION_ITEM,
                                  f"co-check ap {ap} (flag {fl}) has no pooled vanilla item -- "
                                  f"items==locations count-neutrality broken")

    def test_missable_uniform_across_groups(self):
        miss = _path_load("missable_locations").MISSABLE_LOCATIONS
        for fl, members in self._groups().items():
            kinds = {miss.get(ap) for (ap, _r) in members}
            self.assertEqual(len(kinds), 1,
                             f"shared flag {fl}: group mixes missability {kinds} -- one physical "
                             f"acquisition cannot be both missable and not")


if __name__ == "__main__":
    unittest.main()
