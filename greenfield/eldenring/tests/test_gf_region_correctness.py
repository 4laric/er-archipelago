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

Run:  python -m pytest greenfield/eldenring/tests/test_gf_region_correctness.py
  or: python greenfield/eldenring/tests/test_gf_region_correctness.py   (unittest fallback)
"""
import csv
import importlib.util
import re
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)                 # .../greenfield/eldenring
GREENFIELD = os.path.dirname(GF_PKG)           # .../greenfield
DATA_PY = os.path.join(GF_PKG, "data.py")
# region_map.csv is gen_data's INPUT; in the SOURCE tree it sits beside the package (GREENFIELD/), and
# the world-install step copies it INTO the installed package (GF_PKG/) so this oracle RUNS in the
# installed-world pytest too. Resolve from either -- first existing wins.
REGION_MAP_CSV = next((p for p in (os.path.join(GF_PKG, "region_map.csv"),
                                   os.path.join(GREENFIELD, "region_map.csv")) if os.path.isfile(p)),
                      os.path.join(GREENFIELD, "region_map.csv"))

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


def _load_module(name):
    """Load a generated eldenring/<name>.py module by path (None if absent)."""
    path = os.path.join(GF_PKG, name + ".py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("gf_" + name + "_check", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- Authoritative re-pins ------------------------------------------------------------------
# These two tests assume the CSV region-string / map-prefix is authoritative for its whole group.
# It is NOT, and that assumption WAS the bug: 'Leyndell / Roundtable / Shunning-Grounds' is ONE
# string covering THREE regions (m11_00/05 Leyndell, m11_10 Roundtable, m11_71 Shunning), and every
# m35 row is mislabelled 'Divine Tower'. gen_data now regions these from the MAP (DUNGEON_REGION_
# OVERRIDE / FLAG_REGION_OVERRIDE / the MSB+EMEVD ground truth in msb_flag_region.tsv), which is
# strictly more authoritative than the coarse string -- and the provenance oracle
# (test_gf_region_provenance_oracle) proves it against the grace join.
#
# So the group expectation holds for every flag EXCEPT these, each of which is authoritatively pinned
# elsewhere. The tests keep their real value (boundary-bleed / stale-carve on the rest) instead of
# asserting the model we disproved.
AUTHORITATIVE_REPIN = {
    # m11_10 IS Roundtable Hold -- its own loot, not Leyndell/Altus.
    9800: "Roundtable Hold",             # Ensha reward
    60120: "Roundtable Hold",            # Crafting Kit
    60300: "Roundtable Hold",            # Taunter's Tongue
    68210: "Roundtable Hold",            # Fevor's Cookbook [3]
    400282: "Roundtable Hold",           # [Incantation] Black Flame's Protection
    400283: "Roundtable Hold",           # [Incantation] Lord's Divine Fortification
    400285: "Roundtable Hold",           # [Incantation] Law of Causality
    400349: "Roundtable Hold",           # D's Bell Bearing
    400356: "Roundtable Hold",           # Rogier's Letter
    400358: "Roundtable Hold",           # [Sorcery] Explosive Ghostflame
    400359: "Roundtable Hold",           # Rogier's Bell Bearing
    400490: "Roundtable Hold",           # Royal Remains Helm (Ensha)
    10007452: "Roundtable Hold",         # Crimson Hood
    11107000: "Roundtable Hold",         # Cipher Pata
    11107710: "Roundtable Hold",         # Crepus's Black-Key Crossbow
    11107900: "Roundtable Hold",         # Clinging Bone (Ensha)
    11107700: "Roundtable Hold",         # Assassin's Prayerbook -- an m11_10 flag_prefix row; the
                                         #   "11" map recovery (region-spine v2) now derives it to
                                         #   the hub with the rest of the m11_10 loot.
    # EMEVD ground truth: the award site is elsewhere entirely.
    400106: "Raya Lucaria Academy",      # Sellen's Bell Bearing -- awarded in m14 (its own region now)
    520020: "Limgrave",                  # Noble Sorcerer Ashes -- m30_02
    530120: "Limgrave",                  # [Incantation] Aspects of the Crucible: Thorns
    530130: "Limgrave",                  # Bloodhound's Fang -- Darriwil evergaol
    # Boss remembrances the map scan mis-tiled onto m35 (Divine Tower): they belong to their boss.
    510100: "Siofra River",              # Gargoyle's Greatsword -- Valiant Gargoyles (Siofra Aqueduct)
    510200: "Haligtree",                 # Remembrance of the Rot Goddess -- Malenia
    510300: "Caelid",                    # Remembrance of the Starscourge -- Radahn
}
# THE FINALE: the m11_05 lots + the Ashen boss rewards belong to the conditional finale region
# (gen_data.region_of routes them there before any label/map path). DERIVED from data.py itself --
# never a second hand list -- so the oracle and the emission cannot drift; test_gf_finale.py pins
# the membership to the ground-truth flag set.
_d_fin = _load_data()
AUTHORITATIVE_REPIN.update({int(_f): _d_fin.FINALE_REGION
                            for (_n, _a, _f) in _d_fin.LOCATIONS.get(_d_fin.FINALE_REGION, ())})
del _d_fin


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
        1039507100: "Altus",                       # Godfrey Icon = Godefroy the Grafted (Golden Lineage
                                                   #   Evergaol, NW Altus). Was Liurnia (tile 39,50 NN tie).
        1051587800: "Mountaintops of the Giants",  # Haligtree Secret Medallion (Left), physically Castle
                                                   #   Sol. Was Liurnia (emevd mis-tiled to m60_36_41).
        400130:     "Liurnia",                     # Haligtree Secret Medallion (Right), Village of the
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
# Tags whose items are 1-of-1 in vanilla, so each must be a SINGLE check. GreatRune (boss drop,
    # tower dupe excluded) and Remembrance (boss drop, Walking-Mausoleum dupe excluded) join KeyItem
    # here -- all three were duplicate-check classes found in-game 2026-07-08. (Remembrance/GreatRune
    # carry no multi-copy exceptions; only the two keys below do.)
    UNIQUE_SINGLETON_TAGS = frozenset({"KeyItem", "GreatRune", "Remembrance"})
    KEYITEM_MULTI_COPY = {
        "Academy Glintstone Key": 2,   # Meeting Place ruins corpse + Schoolhouse Classroom (Thops)
        "Imbued Sword Key": 3,         # three illusory-wall keys: Raya Lucaria, Caelid, Land of Shadow
    }

    def test_unique_key_items_are_singletons(self):
        """A curated unique KeyItem must resolve to exactly one location (except documented multi-copy
        keys). A re-introduced obtained-flag twin of a placed medallion re-doubles its count here."""
        # Count ALL locations per item NAME, and flag which names are unique-category (tagged on ANY
        # location). Counting by name -- not by tagged-location -- is what gives this teeth against an
        # UNTAGGED duplicate check (the Walking-Mausoleum remembrance copies carry no Remembrance tag;
        # only the boss drop does, so a tag-only count would miss the dupe entirely).
        regions_by_item, unique_named = {}, set()
        for region, locs in self.d.LOCATIONS.items():
            for (name, apid, _flag) in locs:
                m = re.match(r".*:: (.+) \[f\d+\]$", name)
                item = m.group(1) if m else name
                regions_by_item.setdefault(item, []).append(region)
                if self.UNIQUE_SINGLETON_TAGS & set(self.tags.get(apid, ())):
                    unique_named.add(item)
        bad = []
        for item in sorted(unique_named):
            regs = regions_by_item[item]
            if len(regs) > self.KEYITEM_MULTI_COPY.get(item, 1):
                bad.append((item, len(regs), self.KEYITEM_MULTI_COPY.get(item, 1), sorted(regs)))
        self.assertEqual(
            bad, [],
            str(len(bad)) + " unique KeyItem(s) exceed their allowed location count -- an obtained-flag "
            "TWIN regression (2026-07-08 Haligtree Left) or a new multi-copy key needing an allowlist "
            "entry. (item, found, allowed, regions): " + repr(bad))

    # ------------------------------------------------------------------ region capstone re-carve
    # SPEC-region-capstone-model-20260708 (sections 3, 3a) + WIRING-region-capstone-v0.2 (section 7)
    # re-carved the overworld. Boundary mis-bucketing is the RECURRING bug class this gate exists for
    # (Liurnia/Altus 2026-07-08; DLC risk 6a "Boundary mis-bucketing will recur"), so pin every
    # re-carved boundary and refuse any leftover old region name.
    #
    # ACCEPTANCE-GATE NOTE: these assertions encode the TARGET carve. `data.py` (and boss_data.py,
    # region_graces.py, ...) are GENERATED by greenfield/gen_data.py from artifacts that are
    # filter-repo'd out of the public repo, so they are regenerated ONLY on Windows (task #4). The
    # committed data.py at time of writing has the new REGION *names* but LOCATIONS still keyed by the
    # OLD carve (Land of Shadow / Leyndell / Raya Lucaria Academy) -- so this test is RED until that
    # Windows regen and is precisely the gate that confirms the regen landed correctly. It is written
    # to encode the target regardless of the current stale generated state.
    #
    # Independence: the map is the hand-authored SPEC target; the FLAGS are pulled out of region_map.csv
    # by CSV region-string / map-prefix (never hardcoded flag ids), and checked against the emitted
    # data.py assignment -- so this never re-runs gen_data's region_of / REGION_MAP transform.

    # CSV `region` string -> expected emitted region after the re-carve (region-spine v2: the
    # fine places are their OWN regions now -- SPEC-region-spine-v2.md).
    RECARVE_REGION_STRING_EXPECT = {
        # DLC fine splits.
        "Church of the Bud (DLC)":     "Ancient Ruins",   # Romina slice
        "Enir-Ilim (DLC)":             "Enir Ilim",       # Kindling-gated finale (bedrock spelling)
        "Castle Ensis (DLC)":          "Ensis",
        # Cerulean's single CSV row (flag 68540, Forager Brood Cookbook [3]) is deliberately vanilla
        # (gen_data._UNPLACEABLE_DLC_COOKBOOKS, 236bf3d) -> the string may legitimately emit ZERO
        # checks, PROVIDED the flag is ledgered in data.NOT_RANDOMIZED. Keep the expectation: if the
        # exclusion is ever lifted, the region target is still pinned.
        "Cerulean Coast (DLC)":        "Cerulean",
        "Stone Coffin Fissure (DLC)":  "Stone Coffin",
        # Base-game first-class regions.
        "Raya Lucaria Academy":                     "Raya Lucaria Academy",
        "Leyndell / Roundtable / Shunning-Grounds": "Leyndell",   # (m11_10 rows are Roundtable -- AUTHORITATIVE_REPIN)
        "Leyndell, Royal Capital":                  "Leyndell",
        # "Leyndell (Ashen Capital)" checks stay EXCLUDED as dead (post-Erdtree-burn;
        # gen_data._is_ashen_dead) -- zero emitted checks by design, never a re-carve target.
    }

    # `map` prefix -> expected region, for tiles the CSV `region` string mislabels. Subterranean
    # Shunning-Grounds (m35_00) is labelled 'Divine Tower' in region_map.csv (would route to
    # Liurnia); it is the SEWER region since region-spine v2 (bucket 35000).
    RECARVE_MAP_PREFIX_EXPECT = {
        "m35_00": "Sewer",
    }

    # Region names deleted by the re-carve(s). No emitted location may resolve to any of these --
    # v2 renamed/split the coarse names on the right of every old fold.
    REMOVED_REGION_NAMES = frozenset({
        "Land of Shadow",
        # v2 renames (bedrock interop) -- the long forms are gone:
        "Weeping Peninsula", "Stormveil Castle", "Liurnia of the Lakes", "Altus Plateau",
        "Miquella's Haligtree", "Mohgwyn Palace", "Gravesite Plain", "Abyssal Woods",
        "Ancient Ruins of Rauh", "Enir-Ilim",
        # v2 splits -- the coarse bucket is gone entirely:
        "Eternal Cities",
    })


    def _placed_flags_where(self, pred):
        """map_lot flags in region_map.csv matching pred(row), as ints (skips non-numeric flags)."""
        out = []
        for r in self.rows:
            if r.get("flag_source") not in PLACED_SOURCES:
                continue
            if not pred(r):
                continue
            try:
                out.append(int(r["flag"]))
            except (KeyError, ValueError):
                continue
        return out

    # The regen command for the generated-data-can-lag gotcha: keep every failure message actionable.
    REGEN_CMD = ("python greenfield/gen_data.py  (Windows box with elden_ring_artifacts/ present; "
                 "then commit the regenerated greenfield/eldenring/*.py + _gen_stamp.json)")

    def _not_randomized(self):
        """data.NOT_RANDOMIZED (flag -> reason ledger of deliberate exclusions), or a LOUD failure
        when the generated data lags gen_data.py. Never a skip: without the ledger this gate cannot
        tell a deliberate exclusion from silent data loss -- the exact blind spot it exists to
        close (Cerulean Coast dead-air false alarm, 2026-07-14)."""
        nr = getattr(self.d, "NOT_RANDOMIZED", None)
        if nr is None:
            self.fail("data.py has no NOT_RANDOMIZED ledger -- the generated data LAGS gen_data.py. "
                      "REGENERATE, do not skip: " + self.REGEN_CMD)
        return nr

    def test_recarved_regions_by_csv_region_string(self):
        """Every placed pickup whose CSV region-string was re-carved must resolve SOLELY to its new
        region -- catches boundary bleed (a re-carved tile leaking into a neighbour) and stale carve.

        A region-string may produce ZERO emitted checks ONLY when every flag it carries is in
        data.NOT_RANDOMIZED (deliberately excluded, rule recorded) -- e.g. 'Cerulean Coast (DLC)',
        whose single row 68540 is an unplaceable DLC cookbook. A flag absent from BOTH the emitted
        LOCATIONS and NOT_RANDOMIZED is REAL data loss and fails, empty group or not."""
        nr = self._not_randomized()
        bad, lost, no_rows = [], [], []
        for region_string, target in sorted(self.RECARVE_REGION_STRING_EXPECT.items()):
            flags = self._placed_flags_where(lambda r, rs=region_string: (r.get("region") or "") == rs)
            emitted = [(f, self.assigned[f]) for f in flags if f in self.assigned]
            lost.extend((region_string, f) for f in flags
                        if f not in self.assigned and f not in nr)
            if not flags:
                no_rows.append(region_string)  # the CSV carries no row with this string at all
                continue
            if not emitted:
                # Every flag this string carries is deliberately excluded (ledgered above, or it
                # would be in `lost`) -> the string is LEGITIMATELY empty. PASS for that reason.
                continue
            for f, regions in emitted:
                want = AUTHORITATIVE_REPIN.get(f, target)
                if regions != {want}:
                    bad.append((region_string, f, want, sorted(regions)))
        self.assertEqual(
            lost, [],
            str(len(lost)) + " placed flag(s) absent from BOTH data.LOCATIONS and "
            "data.NOT_RANDOMIZED -- REAL data loss, not a deliberate exclusion (an exclusion would "
            "be ledgered with its rule; if gen_data.py changed, regen: " + self.REGEN_CMD + "). "
            "(csv_region, flag): " + repr(lost))
        self.assertEqual(
            no_rows, [],
            "re-carved CSV region-string(s) with NO region_map.csv rows at all (stale expectation "
            "or CSV regression): " + repr(no_rows))
        self.assertEqual(
            bad, [],
            str(len(bad)) + " placed pickup(s) did not resolve solely to their re-carved region "
            "(SPEC-region-capstone-model-20260708 sec 3/3a; boundary mis-bucketing regression, or the "
            "Windows regen of data.py has not run yet). (csv_region, flag, expected, got): "
            + repr(bad[:8]))

    def test_not_randomized_ledger_disjoint_from_emitted(self):
        """A flag cannot be BOTH an emitted location and ledgered NOT_RANDOMIZED -- a ledger entry
        for a live check lies about why the world works (the redundant-manual-override failure
        mode: nobody can tell which entries are load-bearing)."""
        nr = self._not_randomized()
        overlap = sorted(set(nr) & set(self.assigned))
        self.assertEqual(
            overlap, [],
            str(len(overlap)) + " flag(s) present in BOTH data.LOCATIONS and data.NOT_RANDOMIZED "
            "(ledger lies about a live check; regen: " + self.REGEN_CMD + "): " + repr(overlap[:10]))

    def test_shunning_grounds_is_the_sewer(self):
        """Subterranean Shunning-Grounds (m35_00) is the SEWER region (bucket 35000; region-spine
        v2). Keyed on the `map` tile prefix because region_map.csv mislabels every m35 row
        'Divine Tower'."""
        bad, empty = [], []
        for prefix, target in sorted(self.RECARVE_MAP_PREFIX_EXPECT.items()):
            flags = self._placed_flags_where(lambda r, p=prefix: (r.get("map") or "").startswith(p))
            emitted = [(f, self.assigned[f]) for f in flags if f in self.assigned]
            if not emitted:
                empty.append(prefix)
                continue
            for f, regions in emitted:
                want = AUTHORITATIVE_REPIN.get(f, target)
                if regions != {want}:
                    bad.append((prefix, f, want, sorted(regions)))
        self.assertEqual(empty, [], "map-prefix group(s) produced no emitted checks: " + repr(empty))
        self.assertEqual(
            bad, [],
            str(len(bad)) + " Shunning-Grounds (m35_00) pickup(s) not in the Sewer "
            "(region-spine v2 regression, or pre-regen stale data). (map_prefix, flag, expected, got): "
            + repr(bad[:8]))

    def test_no_location_resolves_to_removed_region(self):
        """No emitted location -- and no region table entry -- may name a region a re-carve deleted
        (the old coarse/long names: 'Liurnia of the Lakes', 'Eternal Cities', 'Gravesite Plain', ...).
        Guards against a half-applied regen that keeps LOCATIONS keyed by an old carve while REGIONS
        moves on."""
        leaked_regions = sorted(self.REMOVED_REGION_NAMES & set(self.d.REGIONS))
        self.assertEqual(
            leaked_regions, [],
            "removed region name(s) still present in data.REGIONS: " + repr(leaked_regions))
        leaked_locations = sorted(self.REMOVED_REGION_NAMES & set(self.d.LOCATIONS))
        self.assertEqual(
            leaked_locations, [],
            "removed region name(s) still keying data.LOCATIONS (LOCATIONS not regenerated to the "
            "re-carve while REGIONS was -- half-applied regen): " + repr(leaked_locations)
            + " (counts: "
            + repr({r: len(self.d.LOCATIONS.get(r, [])) for r in leaked_locations}) + ")")
        leaked_assigned = sorted(
            r for regs in self.assigned.values() for r in regs if r in self.REMOVED_REGION_NAMES)
        self.assertEqual(
            leaked_assigned, [],
            "flags still assigned to removed region name(s): " + repr(sorted(set(leaked_assigned))))

    def test_hub_quarantine_budget(self):
        """Tripwire for the quarantine class: the HUB bucket must not balloon. A regression that
        re-routes placed items to HUB pushes this over budget even if the per-row check is loosened.

        Counted against the budget: only hub locations we CLAIM to know belong in the hub, i.e. those
        NOT in DEFAULTED_REGION_APS. A defaulted location is one whose region is admittedly unknown --
        it is hub-quarantined for detection AND barred from carrying progression, so it cannot become
        the false gate this tripwire exists to catch. Counting them would make the budget fire on
        honest "we don't know" rows while staying blind to the thing that actually hurts: a PLACED item
        silently landing in the hub while we still assert it is reachable.
        (Rebaselined 2026-07-11 when the derived shop rows added ~41 unresolved-merchant-block checks.)"""
        hub_all = self.d.LOCATIONS.get(self.d.HUB, [])
        try:
            from ..location_tags import DEFAULTED_REGION_APS as _defaulted
        except ImportError:
            _defaulted = frozenset()
        claimed = [l for l in hub_all if l[1] not in _defaulted]
        hub_locs = len(claimed)
        self.assertLessEqual(
            hub_locs, HUB_BUDGET,
            "HUB has " + str(hub_locs) + " CLAIMED locations (budget " + str(HUB_BUDGET) + "; "
            + str(len(hub_all) - hub_locs) + " more are DEFAULTED and therefore progression-barred); "
            "a quarantine regression likely re-routed placed items to the HUB. "
            "If intentional, rebaseline HUB_BUDGET.",
        )

    # ---------------------------------------------------- cross-file region agreement (independent)
    # Found in-game 2026-07-08: Rennala's Remembrance of the Full Moon Queen (ap 7770008) showed under
    # Stormveil Castle in data.py but Liurnia of the Lakes in boss_data.py / boss_sweeps.py -- the
    # location row (flag 197) was map_lot-scanned onto Godrick's map (m10_00) while the boss join keys
    # off Rennala's m14 defeat flag (14000800). data.py's region and the sweep membership both read the
    # row's `map`/`region` columns, so a mis-scan double-faults: wrong region label AND the reward gets
    # swept by the WRONG boss. This oracle is independent of the region_of TRANSFORM -- boss_data joins
    # by boss event flag (a different derivation), so agreement between the two emitted tables is a real
    # cross-check, not a tautology. gen_data.ROW_MAP_REGION_FIX corrects the row; this pins it.
    def test_boss_reward_region_agrees_with_location_region(self):
        bd = _load_module("boss_data")
        if bd is None or not hasattr(bd, "REGION_BOSSES"):
            self.skipTest("boss_data.py absent")
        loc_region = {}
        for region, locs in self.d.LOCATIONS.items():
            for (_name, apid, _flag) in locs:
                loc_region[apid] = region
        mismatch = []
        for region, entries in bd.REGION_BOSSES.items():
            for (apid, _flag, name) in entries:
                lr = loc_region.get(apid)
                if lr is not None and lr != region:
                    mismatch.append((apid, name, "boss_data=" + region, "data.py=" + lr))
        self.assertEqual(
            mismatch, [],
            str(len(mismatch)) + " boss reward(s) whose data.py location region disagrees with "
            "boss_data.py's region -- a map-scan mis-region (2026-07-08 Full Moon Queen class). "
            "Add a gen_data.ROW_MAP_REGION_FIX entry for the offending flag. " + repr(mismatch[:5]))

    def test_boss_reward_not_swept_by_wrong_boss(self):
        """A boss reward must NEVER be a member of a DIFFERENT boss's sweep (the Full Moon Queen bug:
        Rennala's reward was swept by Godrick's 10000800, not her own 14000800). Legacy/field sweeps
        are filler-only so they exclude boss rewards (Boss/Remembrance-tagged) entirely; a map-local
        dungeon sweep may still contain its own catacomb boss's reward. Either way a reward may only
        ever appear in ITS OWN boss's sweep -- misattribution to another boss is the defect."""
        bd = _load_module("boss_data")
        sw = _load_module("boss_sweeps")
        if bd is None or sw is None or not hasattr(sw, "DUNGEON_SWEEPS"):
            self.skipTest("boss_data.py / boss_sweeps.py absent")
        ds = sw.DUNGEON_SWEEPS
        wrong = []
        for region, entries in bd.REGION_BOSSES.items():
            for (apid, flag, name) in entries:
                for trig, members in ds.items():
                    if trig != flag and apid in members:
                        wrong.append((apid, name, "own_flag=" + str(flag), "swept_by=" + str(trig)))
        self.assertEqual(
            wrong, [],
            str(len(wrong)) + " boss reward(s) swept by the WRONG boss (Full Moon Queen class). "
            "(ap, name, own_flag, swept_by): " + repr(wrong[:5]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
