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
import re
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


def _load_location_tags():
    lt = os.path.join(GF_PKG, "location_tags.py")
    if not os.path.isfile(lt):
        return {}
    spec = importlib.util.spec_from_file_location("gf_loctags_check", lt)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "LOCATION_TAGS", {})


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
        cls.tags = _load_location_tags()

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

    # ------------------------------------------------------------------ FLAG_REGION_OVERRIDE pins
    # In-game tracker report 2026-07-08: three overworld pickups showed under Liurnia because their
    # source tile was a contested Liurnia/Altus boundary tile (nearest-neighbour tie) or a wrong emevd
    # scan tile. gen_data.FLAG_REGION_OVERRIDE (+ a GLOBAL_RECOVER entry for the Right medallion)
    # correct them. Pinned so a regen can't silently regress them. Independent of the override
    # MECHANISM: this asserts the emitted data.py region per flag against the hand-verified vanilla
    # location, not against the override table.
    FLAG_REGION_PINS = {
        1039507100: "Altus Plateau",               # Godfrey Icon = Godefroy the Grafted (Golden Lineage
                                                   #   Evergaol, NW Altus). Was Liurnia (tile 39,50 NN tie).
        1051587800: "Mountaintops of the Giants",  # Haligtree Secret Medallion (Left), physically Castle
                                                   #   Sol. Was Liurnia (emevd mis-tiled to m60_36_41).
        400130:     "Liurnia of the Lakes",        # Haligtree Secret Medallion (Right), Village of the
                                                   #   Albinaurics. Was global/unplaced (SKIPPED) -> vanilla
                                                   #   leak; recovered as a Liurnia check.
    }

    def test_flag_region_overrides_pinned(self):
        """Boundary/bad-tile pickups land in their hand-verified region (in-game report 2026-07-08)."""
        for flag, want in self.FLAG_REGION_PINS.items():
            regions = self.assigned.get(flag)
            self.assertIsNotNone(
                regions, f"flag {flag} not emitted as any location (expected in {want!r})")
            self.assertIn(
                want, regions,
                f"flag {flag} should be assigned to {want!r} (boundary mis-region regression, "
                f"2026-07-08); got {sorted(regions)}")
        # The Haligtree Left obtained-flag twin (f400280, flag_prefix -> phantom Leyndell) is dropped
        # via gen_data EXCLUDE_FLAGS so the placed Left half (f1051587800, Mountaintops) is the sole
        # check -- not a double. Rold (400001, granted) and Right (400130, physical undetected) stay.
        self.assertIsNone(
            self.assigned.get(400280),
            "Haligtree Left obtained-flag twin f400280 should be EXCLUDED (redundant with the placed "
            f"f1051587800); got region(s) {self.assigned.get(400280)}")

    # ------------------------------------------------------------------- unique KeyItem singletons
    # KeyItem = gen_data's curated set of UNIQUE progression keys (medallions, lift/glintstone keys).
    # Each is 1-of-1 in vanilla, so it must resolve to exactly ONE check -- UNLESS it is a key with
    # genuinely multiple vanilla copies, allowlisted here with its count (cite the copies). This guards
    # the OBTAINED-FLAG TWIN class (in-game 2026-07-08): Haligtree Secret Medallion (Left) had both a
    # placed Castle Sol pickup AND a 4000xx flag_prefix obtained-flag heuristic twin -> two checks for
    # one medallion (the twin phantom-bucketed to Leyndell). Great Runes / Remembrances do NOT carry
    # the KeyItem tag (they are GreatRune/Remembrance-tagged and legitimately DUAL-check: rune
    # drop+restore, boss-drop + Enia duplicate purchase), so they never trip this gate.
    KEYITEM_MULTI_COPY = {
        "Academy Glintstone Key": 2,   # Meeting Place ruins corpse + Schoolhouse Classroom (Thops)
        "Imbued Sword Key": 3,         # three illusory-wall keys: Raya Lucaria, Caelid, Land of Shadow
    }

    def test_unique_key_items_are_singletons(self):
        """A curated unique KeyItem must resolve to exactly one location (except documented multi-copy
        keys). A re-introduced obtained-flag twin of a placed medallion re-doubles its count here."""
        counts = {}
        for region, locs in self.d.LOCATIONS.items():
            for (name, apid, _flag) in locs:
                if "KeyItem" not in self.tags.get(apid, ()):
                    continue
                m = re.match(r".*:: (.+) \[f\d+\]$", name)
                counts.setdefault(m.group(1) if m else name, []).append(region)
        bad = []
        for item, regs in sorted(counts.items()):
            if len(regs) > self.KEYITEM_MULTI_COPY.get(item, 1):
                bad.append((item, len(regs), self.KEYITEM_MULTI_COPY.get(item, 1), sorted(regs)))
        self.assertEqual(
            bad, [],
            str(len(bad)) + " unique KeyItem(s) exceed their allowed location count -- an obtained-flag "
            "TWIN regression (2026-07-08 Haligtree Left) or a new multi-copy key needing an allowlist "
            "entry. (item, found, allowed, regions): " + repr(bad))

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
