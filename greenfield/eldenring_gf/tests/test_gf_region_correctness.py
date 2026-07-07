"""Region-of CORRECTNESS gate (tier A: semantic-value, independent oracle).

The existing `test_gf_data.py` proves the region tables are well-FORMED (unique ids, HUB not a
spoke, every region non-empty). It never proves a region assignment is RIGHT. That blind spot is
where three green-while-broken bugs lived (TRIAGE-test-upgrades-20260706.md):
  - gf-maplot-region-quarantine: 52 placed overworld pickups mislabelled to the HUB
    (region_of quarantined them because it keyed on `method` and ignored `flag_source=='map_lot'`).
  - gf-dungeon-grace-misbundle: cave/tower graces bucketed into Limgrave.
  - er-boss-border-grace-skip-list: graces granted that should be skipped.

This gate closes the marquee (map_lot) case with an INDEPENDENT oracle. The ground truth is
`greenfield/region_map.csv` -- gen_data's INPUT, whose `map` / `region` / `flag_source` columns come
straight from the Smithbox `ItemLotParam_map` dump (the item's real placement tile). The bug lived
in `region_of` (the TRANSFORM applied to that input), so checking the emitted assignment against the
CSV's declared placement never re-runs the buggy derivation -- the independence Fable's review
requires (a checker that shares derivation code with the thing it checks is not an oracle).

A placed item (`flag_source=='map_lot'`) physically sits on its tile, so if that tile is a real
emitted spoke its region is ground truth and `region_of` must preserve it -- never quarantine it to
the HUB. That single invariant is the map_lot regression guard.

Deeper layer (follow-up, artifact-gated like ci-linux.sh's DRIFT step): re-derive the tile region
straight from the raw Smithbox param dump / Witchy'ed MSBs / decompiled EMEVD in
`elden_ring_artifacts/` (independent of even region_map.csv), and extend the oracle to graces
(region_graces.py vs grace-anchor map) to cover the dungeon-misbundle + boss-grace-skip cases.

Run:  python -m pytest greenfield/eldenring_gf/tests/test_gf_region_correctness.py
  or: python greenfield/eldenring_gf/tests/test_gf_region_correctness.py   (unittest fallback)
"""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                 # .../greenfield/eldenring_gf
GREENFIELD = os.path.dirname(GF_PKG)           # .../greenfield
DATA_PY = os.path.join(GF_PKG, "data.py")
REGION_MAP_CSV = os.path.join(GREENFIELD, "region_map.csv")

# Placed-item flag_sources: the item sits on a real ItemLotParam_map tile, so its declared region is
# ground truth and region_of must preserve it (never quarantine to HUB). `shop`/`global` sources are
# legitimately allowed to resolve to HUB (shop_multi, unreliable scattered globals) and are excluded.
PLACED_SOURCES = {"map_lot"}

# HUB-quarantine tripwire. The map_lot fix moved HUB to 336 locations; a regression that re-quarantines
# placed items balloons this back up (it was ~388 with the bug). Budget = observed + margin.
HUB_BUDGET = 360


def _load_data():
    spec = importlib.util.spec_from_file_location("gf_data_region_check", DATA_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_region_map():
    with open(REGION_MAP_CSV, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class RegionCorrectness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(REGION_MAP_CSV):
            raise unittest.SkipTest(
                "region_map.csv absent (installed-world copy / fresh clone) -- this oracle runs from "
                "the greenfield source tree where the CSV lives; gated in ci-linux.sh step (b)."
            )
        cls.d = _load_data()
        cls.rows = _load_region_map()
        # flag(int) -> set of regions it is assigned to in the emitted tables (a flag can be shared).
        assigned = {}
        for region, locs in cls.d.LOCATIONS.items():
            for (_name, _apid, flag) in locs:
                assigned.setdefault(int(flag), set()).add(region)
        cls.assigned = assigned

    def test_region_map_parsed_nonempty(self):
        self.assertTrue(self.rows, "region_map.csv parsed to zero rows")

    def test_placed_items_on_a_real_spoke_are_never_quarantined_to_hub(self):
        """A placed (map_lot) item physically sits on its tile, so if that tile is a real emitted
        spoke, region_of MUST leave it in a spoke -- never quarantine it to the HUB. Independent of
        region_of: the declared tile region is read from the CSV input, the assignment from data.py.

        Rows whose declared region is NOT a spoke are excluded on purpose -- a map_lot on the tutorial
        Chapel of Anticipation, or a scattered shared-flag global ('Global / Common-event (unplaced)',
        e.g. the Larval Tears), legitimately routes to the always-reachable HUB via REGION_MAP /
        GLOBAL_RECOVER. The bug this guards is a REAL-region item losing its region, not those."""
        hub = self.d.HUB
        spokes = set(self.d.REGIONS)
        quarantined = []
        for r in self.rows:
            if r.get("flag_source") not in PLACED_SOURCES:
                continue
            declared = r.get("region") or ""
            if declared not in spokes:
                continue  # tutorial / global / unplaced -> HUB is legitimate, not this gate's concern
            try:
                flag = int(r["flag"])
            except (KeyError, ValueError):
                continue
            regions = self.assigned.get(flag)
            if not regions:
                continue  # excluded from the emitted pool (DLC filtered, etc.)
            if regions == {hub}:  # a placed item on a real spoke, sole-assigned to HUB = the bug
                quarantined.append((flag, r.get("item_name"), declared))
        self.assertEqual(
            quarantined, [],
            str(len(quarantined)) + " placed (map_lot) item(s) whose tile is a real spoke were "
            "quarantined to the HUB -- the gf-maplot-region-quarantine regression. "
            "Sample: " + repr(quarantined[:5]),
        )

    def test_hub_quarantine_budget(self):
        """Tripwire for the quarantine class: the HUB bucket must not balloon. A regression that
        re-routes placed items to HUB pushes this over budget even if the per-row check is loosened."""
        hub_locs = len(self.d.LOCATIONS.get(self.d.HUB, []))
        self.assertLessEqual(
            hub_locs, HUB_BUDGET,
            "HUB has " + str(hub_locs) + " locations (budget " + str(HUB_BUDGET) + "); a quarantine "
            "regression likely re-routed placed items to the HUB. If intentional, rebaseline HUB_BUDGET.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
