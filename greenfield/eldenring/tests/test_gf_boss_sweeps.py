"""Boss-sweep SCOPING gate (tier A): the 2026-07-08 class-scoped sweep model must hold.

gen_data.py scopes each boss's dungeon-sweep by the boss's CLASS (from the authoritative
DisplayBossHealthBar set, tools/datamine_boss_healthbars.py -> BOSS_HEALTHBARS):
  * legacy / interior (region majors)   -> region filler PARTITIONED round-robin among the region's
                                           legacy bosses (each boss gets a disjoint ~1/N slice; a
                                           single-legacy-boss region still gets the whole pool)
  * catacomb / cave / tunnel (m30/31/32)-> MAP-LOCAL (only that dungeon map's own checks)
  * field / overworld (m60)             -> NEIGHBORHOOD + FILLER-ONLY (2026-07-15): each overworld
                                           filler check goes to the NEAREST same-region field boss
                                           within Chebyshev tile distance 2, ties split round-robin;
                                           groups are pairwise DISJOINT

These are the invariants a regen (or a member-loop / classifier change) must not break. Independent
of gen_data's derivation: we read the emitted modules + region_map.csv and re-derive each member's
map straight from its flag, so a bug in the generator can't hide behind shared code.

Run:  python greenfield/eldenring/tests/test_gf_boss_sweeps.py
"""
import csv
import importlib.util
from collections import defaultdict
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
MSB_FLAG_REGION_TSV = next((p for p in (os.path.join(GF_PKG, "msb_flag_region.tsv"),
                                        os.path.join(GREENFIELD, "msb_flag_region.tsv"))
                            if os.path.isfile(p)), os.path.join(GF_PKG, "msb_flag_region.tsv"))
UNPLACED_GLOBAL_TSV = next((p for p in (os.path.join(GF_PKG, "unplaced_global_tiles.tsv"),
                                        os.path.join(GREENFIELD, "unplaced_global_tiles.tsv"))
                            if os.path.isfile(p)), os.path.join(GF_PKG, "unplaced_global_tiles.tsv"))

# Minor-dungeon map prefixes, in the X0SS7000 flag convention (flag -> map mXX_SS). MUST match
# gen_data._is_dungeon: this oracle re-derives a member's true map from its flag, and a prefix
# missing here reads as "map unknown" and reports a FALSE map-local violation.
# 🛑 It drifted (found 2026-08-05, SPEC-broaden-sweeps piece B): the list was missing "34" and "39",
# so when Ruin-Strewn Precipice (m39_20, Magma Wyrm Makar) legitimately gained its 21 dungeon
# pickups, this oracle called all 21 non-local because it decoded their map as PENDING. Confirmed
# against a THIRD table before touching this list -- check_maps.tsv has 39207010 -> m39_20
# "decoded from the flag id" -- because widening a test's vocabulary to make a failure go away is
# how a carve-out gets written.
DUNGEON_LOT_PREFIXES = ("30", "31", "32", "34", "39", "40", "41", "42", "43")

# The PERMANENT sweep floor = gen_data._SWEEP_NEVER_TAGS. No sweep, in any seed, under any option,
# may contain one of these: another boss's reward is not this boss's area loot, a key item is a
# gate, and merchant stock is bought rather than picked up.
FIELD_EXCLUDE = frozenset({"Remembrance", "Boss", "GreatRune", "KeyItem", "Shop", "ShopNonSpell",
                           # "LegacyBoss" left with the class absorption (2026-08-20): every
                           # such row carries `Boss` (witnessed in test_gf_location_tags), so the
                           # never-sweep guarantee lost nothing.
                           "ShopSlot", "MajorBoss", "FieldBoss",
                           "MinorDungeonBoss"})
# ...and the half that IS admitted, cut per seed instead (gen_data._SWEEP_SURFACE_CUTTABLE /
# features/boss_locks._SWEEP_SURFACE_CUTTABLE). The collectathon and rarity lines hold loot unless
# the seed's Progression Surface claimed the class.
SURFACE_CUTTABLE = frozenset({"Seedtree", "Church", "Fragment", "Revered", "Basin", "Legendary"})
# LegacyBoss/FieldBoss (2026-08-02) and MinorDungeonBoss (2026-08-16) are SUBSETS of Boss, which is
# already in the floor, so adding them cuts nothing new -- every check they name was excluded
# already. They are listed because the
# UNION of the two sets above is a deliberate mirror of contract.SURFACE_CLASSES and
# test_field_exclude_matches_contract demands that PARTITION: the guard exists so a new premium
# class cannot be added to the vocabulary while quietly staying eligible for a sweep -- it has to be
# filed as never-sweepable or as surface-cuttable, and either way somebody decided.


# gen_data's sweep SCOPE for the multi-head-arena suppression. Legacy bosses are excluded on
# purpose: their members come from the round-robin DIVVY, which is a partition, so two legacy heads
# never shared a list in the first place.
DUNGEON_CLASSES = ("catacomb", "cave", "tunnel", "dungeon")

# A map-local check can deliberately stay outside its boss sweep when a key changes the map state
# and the sweep trigger is reachable before that key.  This mirrors gen_data's narrow carve-out;
# test_gf_dungeon_sweep_rungs proves every member here is actually key-gated, so this cannot become
# a generic escape hatch from the map-completeness invariant.
KEY_GATED_SWEEP_EXCLUDE_FLAGS = frozenset({
    34117100, 34117110, 34117120,
    34117400, 34117401, 34117402, 34117403,
    34117500, 34117710,
})


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
        # 2026-08-20 (#907): a boss's OWN drop is admitted into its own trigger's sweep (the
        # vanilla award waits on CharacterDead; a host enemy randomizer breaks it). The scoping
        # tests exempt exactly that RELATION -- flag's own trigger, from boss_drops.py -- never an
        # id list. Same shape as test_gf_dungeon_sweep_rungs' own_reward.
        _bd = _mod("boss_drops")
        cls.own_drop_of = dict(getattr(_bd, "BOSS_DROP_ENTITY", {}) or {}) if _bd else {}
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
        cls.flag_method = {}
        for r in csv.DictReader(open(REGION_MAP_CSV, encoding="utf-8")):
            if str(r["flag"]).lstrip("-").isdigit():
                cls.flag_map[int(r["flag"])] = r["map"] or ""
                cls.flag_method[int(r["flag"])] = r.get("method") or ""
        # #562: region_map is deliberately the raw scanner output, so rows recovered from an MSB
        # placement can remain PENDING there. Re-derive the generator's unambiguous placement from
        # the shipped source table instead of importing a generated effective-map answer.
        cls.msb_flag_map = {}
        if os.path.isfile(MSB_FLAG_REGION_TSV):
            maps = defaultdict(set)
            with open(MSB_FLAG_REGION_TSV, encoding="utf-8-sig") as fh:
                for r in csv.DictReader((line for line in fh if not line.startswith("#")),
                                        delimiter="\t"):
                    if str(r["flag"]).lstrip("-").isdigit() and r.get("map_id"):
                        maps[int(r["flag"])].add(r["map_id"])
            cls.msb_flag_map = {flag: next(iter(found)) for flag, found in maps.items()
                                if len(found) == 1}
        # #218: the unplaced-global audit publishes exact coordinate / AwardItemLot placement as a
        # committed source table. Read that evidence here just as we read msb_flag_region.tsv above;
        # otherwise the oracle calls every newly recovered dungeon pickup PENDING while gen_data
        # correctly puts it in that dungeon's map-local sweep.
        cls.unplaced_flag_map = {}
        if os.path.isfile(UNPLACED_GLOBAL_TSV):
            with open(UNPLACED_GLOBAL_TSV, encoding="utf-8-sig") as fh:
                for r in csv.DictReader((line for line in fh if not line.startswith("#")),
                                        delimiter="\t"):
                    if str(r["flag"]).lstrip("-").isdigit() and r.get("map_id"):
                        cls.unplaced_flag_map[int(r["flag"])] = r["map_id"]

    def _eff_map(self, ap):
        """A member's effective map: region_map's map, or -- for an unplaced dungeon check whose flag
        encodes the map (30.XX.. -> m30_XX) -- the flag-recovered map. Re-derived independently."""
        fs = str(self.ap_flag.get(ap, ""))
        # The X0SS7000 convention (flag -> map mXX_SS) is not base-only: the DLC minor dungeons use it
        # too (m40 catacombs, m41 gaols, m42 forges, m43 caves) -- e.g. 41017010 -> m41_01 (Curseblade
        # Labirith). An ItemLotParam_map flag's self-encoded map is AUTHORITATIVE over the `map` column:
        # 8 DLC dungeon lots (40007000/41027000/42007000/...) were column-tagged m18_00 (base-game
        # Stranded Graveyard), a mis-scan gen_data._swept_map_prefix now corrects by trusting the flag.
        # Mirror that here (flag wins for dungeon-lot flags) so this independent oracle re-derives the
        # SAME true map instead of trusting the stale column -- exactly what the docstring promises.
        if len(fs) >= 8 and fs[4] == "7" and fs[:2] in DUNGEON_LOT_PREFIXES:
            return f"m{fs[:2]}_{fs[2:4]}_00_00"
        raw = self.flag_map.get(self.ap_flag.get(ap, -1), "")
        if raw and raw != "PENDING":
            return raw
        # OVERWORLD self-encoding, same family as the dungeon rule above: a 10-digit lot flag
        # 10XXYYLLLL encodes tile m60_XX_YY. The late-recovered global/global_filler lots keep
        # map=PENDING in region_map.csv (they were never PLACED by the scan), so without this the
        # oracle cannot locate them at all -- and gen_data's field-sweep gate deliberately admits
        # ONLY rows whose tile is derivable exactly this way, so any member it admits MUST be
        # locatable here. Re-derived from the flag, never imported from gen_data: that is what keeps
        # this oracle independent. A member the oracle still cannot place is a genuine failure --
        # it means the generator claimed a tile from a private table (_BOSS_REWARD_TILE /
        # _ENTITY_SUFFIX) that nobody outside gen_data can check.
        if len(fs) == 10 and fs[:2] == "10":
            return "m60_" + fs[2:4] + "_" + fs[4:6] + "_00"
        msb = self.msb_flag_map.get(self.ap_flag.get(ap, -1), "")
        if msb:
            return msb + ("_00" if msb[:3] in ("m60", "m61") else "_00_00")
        unplaced = self.unplaced_flag_map.get(self.ap_flag.get(ap, -1), "")
        if unplaced:
            parts = unplaced.split("_")
            if unplaced[:3] in ("m60", "m61") and len(parts) == 3:
                return unplaced + "_00"
            if len(parts) == 2:
                return unplaced + "_00_00"
            return unplaced
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
        # BIG_TICKET_TYPES is RETIRED and the contract no longer carries it (a sibling test
        # asserts its absence), so the old `| getattr(ct, "BIG_TICKET_TYPES", [])` term was a
        # dead union with the empty set -- a phantom that made this gate LOOK wider than it is.
        # DIRECT, not getattr-with-default: a defaulted read makes this parity gate pass
        # VACUOUSLY (empty == empty) the moment the contract renames the constant, which is
        # exactly what it is here to prevent. Let it raise.
        # DERIVED classes (contract.SURFACE_DERIVED_CLASSES -- SweepSlot) are in NEITHER half on
        # purpose: they name no location TAG, so gen_data cannot bake them and the per-seed cut
        # cannot remove them without deleting the class. Read DIRECTLY, for the reason the comment
        # above gives: a getattr-with-default would let a renamed constant widen `want` silently and
        # pass this gate vacuously.
        want = set(ct.SURFACE_CLASSES) - set(ct.SURFACE_DERIVED_CLASSES)
        got = set(FIELD_EXCLUDE) | set(SURFACE_CUTTABLE)
        self.assertEqual(
            got, want,
            "the sweep cut no longer PARTITIONS contract.SURFACE_CLASSES; every class must be "
            "filed as never-sweepable (FIELD_EXCLUDE), surface-cuttable (SURFACE_CUTTABLE) or "
            "DERIVED (contract.SURFACE_DERIVED_CLASSES). got=%s want=%s"
            % (sorted(got), sorted(want)))
        self.assertEqual(
            set(ct.SURFACE_DERIVED_CLASSES) & got, set(),
            "a DERIVED surface class is also cut by the sweep. A derived class IS a sweep member by "
            "definition, so cutting it deletes the class it just nominated: %s"
            % sorted(set(ct.SURFACE_DERIVED_CLASSES) & got))
        self.assertEqual(
            set(FIELD_EXCLUDE) & set(SURFACE_CUTTABLE), set(),
            "a class is in BOTH halves of the sweep cut -- it would read as permanently excluded "
            "while its per-seed cut silently did nothing: %s"
            % sorted(set(FIELD_EXCLUDE) & set(SURFACE_CUTTABLE)))

    def test_the_feature_can_cut_everything_the_bake_admits(self):
        """The bake and the per-seed cut must name the SAME six classes.

        Only half the differential lives here. The other copy is in gen_data.py, which is NOT
        installed into an AP world -- a test that reads it from here can only skip, and a skip is a
        green tick over nothing. tools/check_sweep_cut_partition.py owns that half and runs in the
        generators job, where the whole repo is on disk. What IS readable here is the feature, and
        it is the one that has to cover the admission: a class admitted by the bake but absent from
        `_SWEEP_SURFACE_CUTTABLE` is baked into every sweep with no per-seed cut behind it.

        Read as TEXT rather than imported: features/boss_locks pulls in Options/BaseClasses, and
        this module is written to run without Archipelago."""
        import re as _re
        bl = os.path.join(GF_PKG, "features", "boss_locks.py")
        if not os.path.isfile(bl):
            self.skipTest("features/boss_locks.py not present")
        m = _re.search(r"_SWEEP_SURFACE_CUTTABLE\s*=\s*frozenset\(\{(.*?)\}\)",
                       open(bl, encoding="utf-8").read(), _re.S)
        self.assertIsNotNone(m, "features/boss_locks has no _SWEEP_SURFACE_CUTTABLE -- the "
                                "per-seed cut is gone and the bake is now unconditional")
        self.assertEqual(set(_re.findall(r'"([A-Za-z]+)"', m.group(1))), set(SURFACE_CUTTABLE),
                         "boss_locks._SWEEP_SURFACE_CUTTABLE disagrees with the sweep cut this "
                         "file asserts: the per-seed cut would not cover everything the bake "
                         "admitted")

    def test_field_sweeps_are_filler_only(self):
        bad = []
        for ent, info, members in self._members_by_class("field"):
            for ap in members:
                if self.own_drop_of.get(self.ap_flag.get(ap)) == ent:
                    continue  # #907: the boss's own drop, swept by its own trigger
                if FIELD_EXCLUDE & set(self.lt.get(ap, ())):
                    bad.append((ent, info[3], ap, sorted(FIELD_EXCLUDE & set(self.lt.get(ap, ())))))
        self.assertEqual(bad, [], str(len(bad)) + " field-boss sweep member(s) are important-tagged "
                         "-- field sweeps must be filler-only. Sample: " + repr(bad[:5]))

    _TILE_RE = re.compile(r"m60_(\d\d)_(\d\d)")

    def test_field_sweeps_are_local(self):
        """NEIGHBORHOOD scope (2026-07-15, was own-tile): every member must sit within Chebyshev
        distance 2 of the boss's own m60_XX_YY tile -- the nearest-boss assignment's cap. Farther
        means the assignment leaked (or a member's map decode regressed)."""
        bad = []
        for ent, info, members in self._members_by_class("field"):
            bt = self._TILE_RE.match(info[1] or "")
            if not bt:
                # WAS `continue  # undecodable boss tile (the m60_48_55 DLC pair)`. That carve-out
                # skipped the one boss the tile decode was actually LOSING (1248550800, and it is
                # Mountaintops, not DLC) -- a test that excuses the defect it would otherwise catch.
                # Fixed in datamine_boss_healthbars 2026-08-05; this is now a failure, not a skip.
                bad.append((ent, info[3], info[1], None, "boss tile does not decode"))
                continue
            bx, by = int(bt.group(1)), int(bt.group(2))
            for ap in members:
                if self.own_drop_of.get(self.ap_flag.get(ap)) == ent:
                    # #907: the boss's own drop. Global-lot drops (physick tears) carry no tile at
                    # all; region agreement was already enforced at admission (gen_data fails a
                    # region mismatch CLOSED), and "where does the boss's own reward sit" is by
                    # definition local to the boss.
                    continue
                mt = self._TILE_RE.match(self._eff_map(ap) or "")
                if not mt or max(abs(int(mt.group(1)) - bx), abs(int(mt.group(2)) - by)) > 2:
                    bad.append((ent, info[3], info[1], ap, self._eff_map(ap)))
        self.assertEqual(bad, [], str(len(bad)) + " field-boss sweep member(s) beyond Chebyshev "
                         "distance 2 of the boss's tile (or not on an m60 tile at all). Sample: "
                         + repr(bad[:5]))

    def test_every_field_boss_tile_decodes(self):
        r"""A field boss whose tile does not decode is invisible TWICE OVER: gen_data's field pass
        matches `^m60_(\d\d)_(\d\d)$`, so it gets no neighbourhood and no sweep, and it also drops
        out of SWEEP_REGION, which is what anything counting arenas per region reads.

        MOTIVATING CASE (2026-08-05, #363 follow-on). 1248550800 -- the Night's Cavalry duo by
        Yelough Anix Tunnel -- sat at tile 'm60_48'. datamine_boss_healthbars decoded a tile only
        for ids starting "10"; overworld ids also come in a 12-form, and Radahn / Fire Giant /
        Borealis survived only because for them the 12-form is the FLAG over a 10-form ENTITY. This
        one has no 10-form at all (game_areas.tsv flag_equals_id=yes), so it fell through to the
        bare map and granted nothing. The decode is now guarded by a second derivation instead of a
        prefix allowlist: the tile must be one an emevd exists for."""
        bad = [(ent, info[1], info[3]) for ent, info in self.BH.items()
               if info[2] == "field" and not re.fullmatch(r"m60_\d\d_\d\d", info[1] or "")]
        self.assertEqual(bad, [], str(len(bad)) + " field boss(es) have a tile that does not decode "
                         "to m60_XX_YY, so they can never sweep and never count as an arena: "
                         + repr(bad[:5]))

    def test_the_yelough_anix_cavalry_is_a_snowfield_arena(self):
        """The motivating case above, pinned end to end: tile, sweep, region.

        Its 29 members are a REDISTRIBUTION, not a widening -- the field pass is a disjoint
        nearest-boss partition, so neighbouring Snowfield bosses shed exactly what is now
        nearer this arena and the corpus total is unchanged. test_field_sweeps_are_local is the
        check that the tile is the RIGHT one: a wrong tile puts those 29 members outside Chebyshev
        distance 2 and reddens it."""
        ENT = 1248550800
        self.assertIn(ENT, self.BH, "the Yelough Anix Night's Cavalry left boss_healthbars")
        self.assertEqual(self.BH[ENT][1], "m60_48_55",
                         "tile regressed -- its emevd is event/m60_48_55_00.emevd.dcx.js")
        self.assertTrue(self.DS.get(ENT),
                        "1248550800 has no sweep members; the tile decode regressed and this boss "
                        "grants nothing again")
        self.assertEqual(self.sw.SWEEP_REGION.get(ENT), "Consecrated Snowfield",
                         "sweep region regressed -- the tile's own checks are 'near Yelough Anix "
                         "Tunnel' and one of them is the Night's Cavalry Helm (flag 1048557710)")

    _GRID_RE = re.compile(r"^(m6[01])_(\d\d)_(\d\d)")

    def test_overworld_sweeps_never_mix_GRIDS(self):
        r"""m60 and m61 are two coordinate systems, not one (SPEC-broaden-sweeps piece A, 2026-08-05).

        The DLC overworld pass reuses the base game's nearest-boss machinery, which was written when
        `_tile_xy` held a bare `(x, y)`. An m60 tile at (44,45) and an m61 tile at (44,45) are
        different places on different continents; comparing them yields a distance that means
        nothing, and a SMALL one -- so the failure mode is a DLC boss quietly claiming base-game
        checks, or the reverse. gen_data now carries the grid label and guards every comparison
        (`_near`); this states that independently.

        🛑 GRID ONLY, and the CAP is deliberately NOT asserted here -- I tried and it was wrong.
        A DLC overworld boss is `legacy`: it holds a NEIGHBOURHOOD slice (within Chebyshev 2) AND a
        region-divvy slice, and a divvy member is region-correct at ANY distance. Romina (m61_44_45)
        legitimately holds Ancient Ruins checks on m61_46_48, distance 3. Nothing in the output
        distinguishes the two pools, so an over-cap member is indistinguishable from a divvy member
        and a cap assertion here can only produce false failures. The cap is enforced by `_near` and
        covered for class-`field` bosses by test_field_sweeps_are_local; for m61 the reachable claim
        is the population one in test_the_dlc_overworld_has_neighbourhood_sweeps."""
        bad = []
        for ent, members in self.DS.items():
            info = self.BH.get(ent)
            if not info:
                continue
            bt = self._GRID_RE.match(info[1] or "")
            if not bt:
                continue
            for ap in members:
                mt = self._GRID_RE.match(self._eff_map(ap) or "")
                if mt and mt.group(1) != bt.group(1):
                    bad.append((ent, info[1], ap, mt.group(0)))
        self.assertEqual(bad, [], str(len(bad)) + " overworld sweep member(s) on the OTHER GRID -- "
                         "an m60 boss holding m61 checks or vice versa. Sample: " + repr(bad[:5]))

    def test_the_dlc_overworld_has_neighbourhood_sweeps(self):
        """MOTIVATING CASE for piece A: the DLC overworld granted nothing spatial at all.

        Its 28 bosses are classed `legacy` -- and must STAY that way, they are their regions' divvy
        hosts and five regions have no other one -- but `DisplayBossHealthBar` only carries the
        coarse `m61_XX` BAND, so gen_data's field pass could never place them. Their id encodes the
        real tile (20XXYYLLLL, the DLC sibling of 10/12), which gen_data already trusted for the
        divvy; now it reaches the boss table too.

        Pinned on Black Knight Edredd (m61_49_43, Scadu Altus), the largest gainer, plus the
        population-level claim so a single retuned boss cannot hide a dead pass."""
        EDREDD = 2049430850
        self.assertIn(EDREDD, self.DS, "Black Knight Edredd has no sweep -- the m61 tile decode or "
                                       "the DLC field pass regressed")
        self.assertGreaterEqual(len(self.DS[EDREDD]), 20,
                                "Edredd holds %d members; it gained 30 when the DLC field pass "
                                "landed, so this is a regression" % len(self.DS[EDREDD]))
        m61 = [ent for ent, info in self.BH.items()
               if (info[0] or "").startswith("m61") and ent in self.DS]
        self.assertGreaterEqual(len(m61), 20, "only %d DLC overworld bosses sweep anything" % len(m61))
        total = sum(len(self.DS[e]) for e in m61)
        self.assertGreaterEqual(total, 400, "DLC overworld bosses hold %d members between them; the "
                                            "field pass was worth ~225 on top of ~250 divvied" % total)

    def test_field_sweeps_are_disjoint(self):
        """Nearest-boss assignment gives each overworld check to exactly ONE field boss -- no two
        field sweeps may share a member (own-tile pairs used to double-sweep their shared tile)."""
        owner, overlaps = {}, []
        for ent, _info, members in self._members_by_class("field"):
            for ap in members:
                if ap in owner:
                    overlaps.append((ap, owner[ap], ent))
                owner.setdefault(ap, ent)
        self.assertEqual(overlaps, [], str(len(overlaps)) + " overworld check(s) swept by TWO field "
                         "bosses. Sample: " + repr(overlaps[:5]))

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

    def test_ruin_strewn_precipice_is_swept(self):
        """MOTIVATING CASE (SPEC-broaden-sweeps piece B, 2026-08-05).

        Ruin-Strewn Precipice (m39_20) is a real dungeon you fight your way DOWN, and Magma Wyrm
        Makar granted NONE of its 21 loot pickups. They were excluded because `_swept` keyed its
        dungeon branch on `method == "flag_prefix"`, and these rows are `global`/`global_filler` --
        a statement about an item's DISTRIBUTION ("scattered by design"), not about whether this
        particular pickup has a known place. It has one: the flag self-encodes m39_20.

        Pinned by FLAG, not ap id, so a location-table renumber does not silently retarget it."""
        FLAGS = (39207010, 39207020, 39207030)   # Smithing Stone [5] / Rune Arc / Somber [3]
        members = set(self.DS.get(39200800, ()))
        self.assertTrue(members, "Magma Wyrm Makar (39200800) has no sweep at all")
        missing = [f for f in FLAGS
                   if not any(self.ap_flag.get(ap) == f for ap in members)]
        self.assertEqual(missing, [], "Ruin-Strewn Precipice pickups not swept by its boss: "
                         + repr(missing))

    def test_a_legacy_map_is_swept_by_a_boss_STANDING_ON_IT(self):
        """The invariant piece C establishes (SPEC-broaden-sweeps, 2026-08-05).

        A legacy boss used to grant a round-robin slice of its whole REGION and nothing else, so the
        Shadow Keep's own pickups could be handed to you by a boss in a different building. Now a
        check on a legacy map that hosts a boss is granted by a boss ON THAT MAP.

        Directional on purpose: a legacy boss also keeps a region-divvy slice, and those members
        legitimately live elsewhere. What must not happen is the reverse -- someone else's boss
        paying out this building."""
        on_map = {}
        for ent, members in self.DS.items():
            info = self.BH.get(ent)
            if info:
                on_map[ent] = info[0]
        legacy_maps = {info[0] for ent, info in self.BH.items()
                       if info[2] == "legacy" and not info[0].startswith(("m60", "m61"))
                       and info[0] != "m10_01"}
        # A map is only "claimed" for a region if a boss of THAT region stands on it. m11_00's
        # Leyndell bosses legitimately hold Leyndell-regioned checks that sit on m11_05 (the Ashen
        # Capital map) via the region divvy -- the check is region-correct, it is just physically in
        # a building whose own bosses answer to a different region. Requiring a same-region host is
        # what makes this a map-locality claim rather than a map-adjacency one.
        host = defaultdict(set)
        for ent, mp in on_map.items():
            host[mp].add(self.sw.SWEEP_REGION.get(ent))
        # THE ONE DELIBERATE EXCEPTION: a clawback recipient. Astel's arena m12_04 holds no filler,
        # so once the map-local pass gave the Eternal Cities' loot to the bosses standing in m12_01
        # and m12_02, Astel was dealt nothing at all (33 -> 0). It claws back a share from the
        # largest holder in its region, which means it necessarily holds checks from someone else's
        # map -- see test_astel_still_grants_something and the pass in gen_data. Listed rather than
        # inferred: a SECOND boss appearing here is a new starvation, which is exactly what this
        # test should make you look at.
        CLAWBACK_RECIPIENTS = {12040800}          # Astel, Naturalborn of the Void
        bad = []
        for ent, members in self.DS.items():
            if ent in CLAWBACK_RECIPIENTS:
                continue
            reg = self.sw.SWEEP_REGION.get(ent)
            for ap in members:
                mp = _mp2(self._eff_map(ap))
                if mp in legacy_maps and mp != on_map.get(ent) and reg in host.get(mp, ()):
                    bad.append((ent, on_map.get(ent), ap, mp))
        # "An exclusion that matches nothing is a lie" -- if the clawback ever stops firing, this
        # carve-out must fail loudly rather than sit here reading like protection.
        self.assertTrue(all(self.DS.get(e) for e in CLAWBACK_RECIPIENTS),
                        "a CLAWBACK_RECIPIENT grants nothing -- the clawback stopped firing and "
                        "this exemption is now protecting a boss that no longer needs it")
        self.assertEqual(bad, [], str(len(bad)) + " legacy-map check(s) granted by a boss standing "
                         "somewhere else. Sample: " + repr(bad[:5]))

    def test_astel_still_grants_something(self):
        """THE CLAWBACK, and the case that forced it (piece C, 2026-08-05).

        Astel's arena (m12_04) is a bare boss room -- no chests, no pickups, nothing map-local can
        hold. Every check a player calls "the Eternal Cities" physically lives in m12_01 (Ancestral
        Woods) and m12_02 (Nokstella), which now belong to the bosses standing in them. So the
        map-local pass emptied Ainsel River's leftover pool and Astel, which used to take a
        consolation slice of it, was dealt 33 -> 0. Dealing the remainder to the emptiest bosses
        first cannot help: the remainder is genuinely EMPTY.

        A boss that granted 33 checks yesterday granting zero today is a regression however
        defensible the bookkeeping, so a starved region major claws back a share from the largest
        holder in its OWN region, re-dealt round-robin. Balanced within one, like every other
        partition here -- an unbalanced clawback would just move the starvation to the donor."""
        ASTEL, DONOR_REGION = 12040800, "Ainsel River"
        members = self.DS.get(ASTEL, [])
        self.assertTrue(members, "Astel (12040800) grants NOTHING. The clawback is gone or its "
                                 "region no longer has a donor -- see the pass in gen_data.")
        off = [ap for ap in members if self.ap_region.get(ap) != DONOR_REGION]
        self.assertEqual(off, [], "Astel's clawback pulled checks from outside %s: %r"
                         % (DONOR_REGION, off[:5]))
        donors = [len(m) for e, m in self.DS.items()
                  if e != ASTEL and self.sw.SWEEP_REGION.get(e) == DONOR_REGION and len(m) >= 2]
        self.assertTrue(donors, "no donor left in %s to compare against" % DONOR_REGION)
        # Balanced against its DONOR, not against every holder in the region: the re-deal splits one
        # boss's list, so the other holders are untouched and may legitimately be larger.
        self.assertTrue(any(abs(n - len(members)) <= 1 for n in donors),
                        "clawback is lopsided: Astel holds %d and no %s holder is within one of "
                        "that (%r). A round-robin re-deal leaves the donor and the starved boss "
                        "within one of each other." % (len(members), DONOR_REGION, sorted(donors)))

    def test_no_dungeon_mapped_filler_is_left_unswept(self):
        """The general invariant piece B establishes: on a minor-dungeon map whose boss ALREADY has
        a working sweep, no filler check may sit outside that sweep merely because of its `method`.

        Scoped to maps that host a sweeping boss -- a dungeon with no boss has nothing to attach to
        and is out of scope here (and out of reach of any boss-attached sweep; see the spec)."""
        swept = {ap for members in self.DS.values() for ap in members}
        bossmaps = {info[0] for ent, info in self.BH.items() if ent in self.DS}
        bad = []
        for region, locs in self.d.LOCATIONS.items():
            if region == "Roundtable Hold":
                continue
            for (_name, ap, flag) in locs:
                if ap in swept:
                    continue
                if int(flag) in KEY_GATED_SWEEP_EXCLUDE_FLAGS:
                    continue
                if FIELD_EXCLUDE & set(self.lt.get(ap, ())):
                    continue
                # _eff_map, NOT flag_map: the raw region_map column is "PENDING" for exactly
                # this population (global/global_filler rows), so reading it made this guard INERT
                # over the very checks it exists to protect. Caught by mutation -- deleting Makar's
                # 21 members left this test green until it was pointed at the flag decode.
                mp = _mp2(self._eff_map(ap))
                if mp and mp[1:3] in DUNGEON_LOT_PREFIXES and mp in bossmaps:
                    bad.append((ap, mp, _name[:60]))
        self.assertEqual(bad, [], str(len(bad)) + " filler check(s) on a minor-dungeon map whose "
                         "boss sweeps are left ungranted. Sample: " + repr(bad[:5]))

    def test_all_members_in_sweep_region(self):
        bad = []
        for ent, members in self.DS.items():
            reg = self.sw.SWEEP_REGION.get(ent)
            for ap in members:
                if self.ap_region.get(ap) != reg:
                    bad.append((ent, ap, "sweep=" + str(reg), "loc=" + str(self.ap_region.get(ap))))
        self.assertEqual(bad, [], str(len(bad)) + " sweep member(s) whose location region != the sweep's "
                         "region (cross-region leak). Sample: " + repr(bad[:5]))

    def test_summonwater_killsite_checks_are_swept(self):
        """The 2026-07-24 "killed the Tibia Mariner, no boss sweep" report. The checks physically AT
        a field boss's kill site are the late-recovered global/global_filler lots (map=PENDING); they
        were invisible to every sweep pass, so felling the boss granted only far-side treasure rows
        and read in-game as nothing happening. Summonwater Village is the reported case: the twelve
        m60_45_39 lots below (flags 1045397000-1045397140, self-encoded tile) must each belong to a
        field sweep. Absence is the bug -- and absence is invisible unless something goes looking.

        MEMBERSHIP IS ONLY HALF OF IT -- see test_summonwater_killsite_checks_are_limgrave below.
        This test stayed green for ten days while the same checks were unobtainable, because it never
        asked which REGION the sweep it found them in belonged to."""
        in_field = set()
        for _ent, _info, members in self._members_by_class("field"):
            in_field.update(members)
        # Candidates = locations on that tile that a FIELD sweep is allowed to grant (filler-only:
        # an important-tagged check is excluded by design, so it is not evidence of the bug).
        cands = [ap for ap, flag in self.ap_flag.items()
                 if 1045397000 <= flag <= 1045397140
                 and not (FIELD_EXCLUDE & set(self.lt.get(ap, ())))]
        self.assertTrue(cands, "no Summonwater m60_45_39 lots in data.py at all -- the recovery that "
                        "produced them regressed upstream of the sweep pass (empty is a FAILURE, "
                        "not a clean run)")
        missing = sorted(ap for ap in cands if ap not in in_field)
        self.assertEqual(missing, [], str(len(missing)) + " of " + str(len(cands)) + " Summonwater "
                         "kill-site check(s) belong to NO field sweep -- the recovered-global "
                         "admission gate regressed. Sample: " + repr(missing[:5]))

    def test_summonwater_killsite_checks_are_limgrave(self):
        """The OTHER half of the same report (boblerrr, v0.3.2, 2026-08-03: "killed the boss in
        Summonwater Village -- got no loot on a Limgrave seed"; Alaric hit it first in his own
        playtest). The twelve m60_45_39 lots WERE swept -- the test above proves that much -- by a
        sweep regioned CAELID. On any seed that does not keep Caelid the trigger, its members and the
        Tibia Mariner's own Deathroot (f530170) are never created, so felling the boss pays nothing.

        Tile m60_45_39 holds no grace of its own, so gen_data.tile_pr() nearest-neighboured it. The
        squared distance TIED between the Limgrave anchors to its west -- (44, 39) Summonwater
        Village Outskirts and (46, 38) Third Church of Marika, both play_region 61000 -- and the
        Caelid anchors to its east, and the tie was settled by the row order of grace_flags.tsv.
        gen_data.M60_TILE_CURATED pins the tile; this asserts the part a player can actually feel.

        Region, not membership: a check swept into the wrong region is exactly as unobtainable as a
        check swept into no sweep at all, and only one of those two had a test."""
        killsite = sorted(ap for ap, flag in self.ap_flag.items()
                          if 1045397000 <= flag <= 1045397140)
        self.assertTrue(killsite, "no Summonwater m60_45_39 lots in data.py at all")
        off = sorted((ap, self.ap_region.get(ap)) for ap in killsite
                     if self.ap_region.get(ap) != "Limgrave")
        self.assertEqual(off, [], str(len(off)) + " of " + str(len(killsite)) + " Summonwater "
                         "kill-site check(s) are not in Limgrave -- the m60_45_39 tile curation "
                         "regressed (gen_data.M60_TILE_CURATED). Sample: " + repr(off[:5]))
        # ... and the sweeps that grant them must be Limgrave sweeps, or a Limgrave-only seed still
        # drops the whole group: dungeonSweepFlags is emitted per sweep, keyed on SWEEP_REGION.
        owning = {ent for ent, members in self.DS.items() if set(members) & set(killsite)}
        self.assertTrue(owning, "the Summonwater kill-site checks belong to no sweep at all")
        wrong = sorted((ent, self.sw.SWEEP_REGION.get(ent)) for ent in owning
                       if self.sw.SWEEP_REGION.get(ent) != "Limgrave")
        self.assertEqual(wrong, [], "sweep(s) granting Summonwater kill-site checks are not regioned "
                         "Limgrave, so a Limgrave seed never emits them: " + repr(wrong))
        # The boss's OWN reward rides the same tile and the same mistake.
        deathroot = [ap for ap, flag in self.ap_flag.items() if flag == 530170]
        self.assertEqual([self.ap_region.get(ap) for ap in deathroot], ["Limgrave"] * len(deathroot),
                         "the Tibia Mariner's Deathroot (f530170) is not a Limgrave check")

    def test_fort_gael_checks_are_caelid(self):
        """The MIRROR of the Summonwater case, and the reason that one is not a one-off.

        Tile m60_47_38 is Fort Gael. Like m60_45_39 it holds no grace of its own, so tile_pr()
        nearest-neighboured it; like m60_45_39 the squared distance TIED at 1 -- (46, 38) Third
        Church of Marika [61000] west against (47, 39) Fort Gael North [64000] east -- and like
        m60_45_39 the tie was settled by table order. It fell the OTHER way, so 15 checks shipped as
        LIMGRAVE while twelve of them are named after Caelid graces (Fort Gael North, Caelid Highway
        South, Astray from Caelid Highway North).

        CONFIRMED IN GAME by Alaric 2026-08-03: "Fort Gael is in Caelid", naming
        [Incantation] Flame, Grant Me Strength (f1047387120) and Ash of War: Lion's Claw
        (f1047387700, "drops from killing the lion"). He first answered the two separately and they
        disagreed -- which is itself the finding: region is a TILE property, so two checks on one
        tile cannot have different answers, and a form that lets them is a form that hides this.

        🛑 Two tiles is not the class either. Both were found by a player noticing, not by a gate."""
        fg = sorted(ap for ap, flag in self.ap_flag.items()
                    if 1047387000 <= flag <= 1047387999)
        self.assertTrue(fg, "no m60_47_38 lots in data.py at all")
        off = sorted((ap, self.ap_region.get(ap)) for ap in fg
                     if self.ap_region.get(ap) != "Caelid")
        self.assertEqual(off, [], str(len(off)) + " of " + str(len(fg)) + " Fort Gael (m60_47_38) "
                         "check(s) are not in Caelid -- the tile curation regressed "
                         "(gen_data.M60_TILE_CURATED). Sample: " + repr(off[:5]))

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
        only the region's filler, never an important-tagged check (same cut as field). The
        member list is baked from location tags at gen time; boss_locks.slot_data emits it verbatim."""
        from worlds.eldenring.boss_sweeps import POST_BOSS_GIFTS
        bad = []
        for ent, info, members in self._members_by_class("legacy"):
            for ap in members:
                if self.own_drop_of.get(self.ap_flag.get(ap)) == ent:
                    continue  # #907: the boss's own drop, swept by its own trigger
                if ap in POST_BOSS_GIFTS.get(ent, ()):
                    continue  # #1100: the boss's own post-defeat vanilla gift
                hit = FIELD_EXCLUDE & set(self.lt.get(ap, ()))
                if hit:
                    bad.append((ent, info[3], ap, sorted(hit)))
        self.assertEqual(bad, [], str(len(bad)) + " legacy sweep member(s) are important-tagged -- "
                         "region-major sweeps must be filler-only. Sample: " + repr(bad[:5]))

    def test_legacy_filler_only_is_nontrivial(self):
        """Guard the cut actually bites: at least one important-tagged check must sit in a
        legacy sweep's own region yet be EXCLUDED from the sweep. Fails if legacy silently reverts to
        region-wide (or the tag data drops), which test_legacy_sweeps_are_filler_only alone would miss
        (an empty/degenerate sweep is vacuously filler-only)."""
        for ent, info, members in self._members_by_class("legacy"):
            reg = self.sw.SWEEP_REGION.get(ent)
            memset = set(members)
            for ap, r in self.ap_region.items():
                if r == reg and ap not in memset and (FIELD_EXCLUDE & set(self.lt.get(ap, ()))):
                    return  # found an excluded important check in a legacy sweep's region -> cut bites
        self.fail("no important-tagged check is excluded from any legacy sweep -- the filler-only "
                  "cut looks like a no-op (region-wide regression or missing location tags)")

    def test_legacy_sweeps_partition_their_region(self):
        """DIVVY (2026-07-11): a legacy region's filler is PARTITIONED among its legacy bosses -- no two
        legacy bosses in the SAME region may share a member. Guards against a revert to region-wide,
        where every boss dumped the whole region (Farum's 91 checks granted in full by each of Godskin
        Duo / Placidusax / Maliketh / Beast Clergyman). Single-legacy-boss regions are trivially fine."""
        by_region = {}
        for ent, info, members in self._members_by_class("legacy"):
            by_region.setdefault(self.sw.SWEEP_REGION.get(ent), []).append((ent, set(members)))
        overlaps = []
        for reg, lst in by_region.items():
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    if lst[i][1] & lst[j][1]:
                        overlaps.append((reg, lst[i][0], lst[j][0], len(lst[i][1] & lst[j][1])))
        self.assertEqual(overlaps, [], str(len(overlaps)) + " pair(s) of same-region legacy sweeps SHARE "
                         "members -- must be partitioned (disjoint), not region-wide. Sample: "
                         + repr(overlaps[:5]))

    # ---- MULTI-HEAD ARENAS (#363, bobler 2026-08-04) -------------------------------------------
    def _game_areas(self):
        """`area_id -> defeat_flag` straight from game_areas.tsv. Read here rather than imported
        from gen_data so this stays an INDEPENDENT oracle.

        Located the same way as REGION_MAP_CSV above: beside the package in the INSTALLED world,
        or in greenfield/ in the source tree. It is a gen INPUT, not emitted output, so the
        installed world only has it if the install step copied it -- skip loudly rather than
        pass blind, exactly as the region_map.csv gate does."""
        path = next((q for q in (os.path.join(GF_PKG, "game_areas.tsv"),
                                 os.path.join(GREENFIELD, "game_areas.tsv")) if os.path.isfile(q)),
                    None)
        if path is None:
            raise unittest.SkipTest(
                "game_areas.tsv not found beside the package or in greenfield/ -- it is a gen INPUT, "
                "so the installed world needs the install step to copy it. Skipping rather than "
                "reporting a multi-head arena clean on a table we could not read.")
        out = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line[:1] == "#" or line.startswith("area_id"):
                    continue
                p = line.rstrip("\n").split("\t")
                if len(p) > 2 and p[0].isdigit() and p[1].isdigit():
                    out[int(p[0])] = int(p[1])
        return out

    def _arena_pairs(self):
        """`secondary -> (primary, evidence)` straight from boss_arena_pairs.tsv.

        The second source #363 needed. GameAreaParam is "A PARTITION, not every boss" by its own
        header, so it has NO ROW for m34_14's second Fell Twin and the check below could not see it;
        the EMEVD defeat banner covers the rest. Read from the file, never imported from gen_data,
        so this stays an INDEPENDENT oracle. Located and skipped exactly like _game_areas."""
        path = next((q for q in (os.path.join(GF_PKG, "boss_arena_pairs.tsv"),
                                 os.path.join(GREENFIELD, "boss_arena_pairs.tsv"))
                     if os.path.isfile(q)), None)
        if path is None:
            raise unittest.SkipTest(
                "boss_arena_pairs.tsv not found beside the package or in greenfield/ -- it is a gen "
                "INPUT, so the installed world needs the install step to copy it. Skipping rather "
                "than reporting a multi-head arena clean on a table we could not read.")
        out = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line[:1] == "#" or line.startswith("secondary"):
                    continue
                q = line.rstrip("\n").split("\t")
                if len(q) > 4 and q[0].isdigit() and q[1].isdigit():
                    out[int(q[0])] = (int(q[1]), q[4])
        return out

    def _secondary(self, ent, bmap, areas, pairs):
        """Both sources, under the SAME same-map guard gen_data applies. -> primary id or None."""
        df = areas.get(ent)
        if df is not None and df != 0 and df != ent:
            primary = self.BH.get(df)
            if primary is not None and primary[0] == bmap:
                return df
        pair = pairs.get(ent)
        if pair is not None:
            primary = self.BH.get(pair[0])
            if primary is not None and primary[0] == bmap:
                return pair[0]
        return None

    def test_no_secondary_arena_head_carries_a_sweep(self):
        """THE MOTIVATING CASE (#363). A boss ARENA can hold several healthbar entities -- m32_05 is
        the Crystalian duo, 32050800 Ringblade + 32050801 Spear. Dungeon members are keyed on the
        MAP, so assigning them per ENTITY handed both heads the SAME seven checks, and the sweep paid
        out the whole dungeon when EITHER flipped.

        bobler, 2026-08-04: 7 Altus Tunnel checks granted on ENTERING the boss room, 69s before the
        fight ended, after which the Crystalian he killed dropped nothing. If the second head is not
        present in the arena its flag reads set at map load, so a secondary head's flag is not a
        statement about the fight at all.

        GameAreaParam says which head reports the fight: 32050801 -> defeat_flag 32050800,
        bonus_soul 0. A head whose defeat flag is ANOTHER entity on the SAME map must not trigger.

        SECOND SOURCE (the residual #364 could not reach). GameAreaParam covers 3 of the 15. It has
        NO ROW AT ALL for 34140851, the second Fell Twin -- and bobler confirmed that arena paying
        out on ENTRY the same day -- so the EMEVD defeat banner answers the rest:
        `HandleBossDefeatAndDisplayBanner(P)` names what reports a fight, and the condition guarding
        it names every head the fight waits on. Both sources are checked here under one guard,
        because a head suppressed by either must not carry a sweep.

        Applies to DUNGEON and LEGACY classes. A legacy round-robin divvy prevents two heads from
        holding the same member list, but it cannot turn a participant or activation flag into a
        terminal encounter flag. #877 is the counterexample that retired the old dungeon-only
        scope: Enir Ilim's 20010851/52 rows never report their own defeat."""
        areas, pairs = self._game_areas(), self._arena_pairs()
        offenders = []
        for ent in self.DS:
            info = self.BH.get(ent)
            if info is None or info[2] == "field":
                continue
            primary = self._secondary(ent, info[0], areas, pairs)
            if primary is not None:
                offenders.append((ent, primary, info[0], info[3]))
        self.assertEqual(offenders, [], str(len(offenders)) + " secondary arena head(s) still carry a "
                         "sweep -- their fight is reported by another flag on the same map, so they "
                         "pay the dungeon out early (#363). Offenders (entity, primary, map, "
                         "name): " + repr(offenders))

    def test_enir_ilim_npc_battle_uses_its_one_terminal_flag(self):
        """#877: Leda/Dane/Freyja are heads in one five-character encounter, not three fights.

        m20_01 event 20012850 waits for characters 20010850..854 to die, displays one banner keyed
        by 20010850, then sets event flag 20010850. The banner datamine captures the two additional
        displayed heads as conjuncts of that one terminal event. They must not survive as tracker
        rows or lend their names to generated ``may be sweep-granted by`` descriptions.
        """
        pairs = self._arena_pairs()
        for secondary in (20010851, 20010852):
            self.assertEqual(
                pairs.get(secondary),
                (20010850, "conjunct"),
                "%d must derive from the one 20010850 defeat banner" % secondary,
            )
            self.assertNotIn(
                secondary,
                self.DS,
                "%d is a participant/activation id, not an Enir Ilim terminal sweep flag"
                % secondary,
            )
        self.assertIn(20010850, self.DS, "the real Enir Ilim terminal sweep disappeared")

    def test_the_fell_twins_are_suppressed_by_the_banner_table(self):
        """THE GAP #364 SHIPPED WITH, pinned so it cannot reopen (bobler, 2026-08-04).

        `game_areas.tsv` has a row for 34140850 and NONE for 34140851, so `defeat_flag` returned no
        answer for the second Fell Twin and the Divine Tower of East Altus kept paying its whole
        7-check sweep on the first head. bobler got those checks on ENTERING the arena -- with
        Placidusax standing in it, because Matt's randomizer had swapped the occupant and SET one
        twin's kill flag, so the head read dead at map load.

        This asserts the fix comes from the EMEVD table specifically: a row must exist AND
        GameAreaParam must still not know the entity. If someone later adds a game_areas row for
        34140851 the assertion on `areas` fails loudly rather than letting the banner table quietly
        stop being exercised on the case it was built for."""
        pairs = self._arena_pairs()
        self.assertIn(34140851, pairs, "boss_arena_pairs.tsv has no row for the second Fell Twin "
                      "(34140851) -- the #363 residual is back and m34_14 pays out on entry again.")
        self.assertEqual(pairs[34140851][0], 34140850, "34140851's fight is reported by 34140850 "
                         "(one banner, over `Dead(34140850) && Dead(34140851)`).")
        self.assertNotIn(34140851, self._game_areas(), "GameAreaParam has gained a row for 34140851. "
                         "That is fine, but this test exists to prove the BANNER table carries the "
                         "case game_areas cannot -- re-point it at another uncovered head.")
        self.assertNotIn(34140851, self.DS, "the second Fell Twin still carries a sweep.")

    def test_sages_cave_retains_BOTH_triggers(self):
        """THE NEGATIVE CONTROL. m31_19 Sage's Cave is Black Knife Assassin (31190800) AND
        Necromancer Garris (31190850) -- two SEPARATE fights that happen to share a dungeon, and its
        EMEVD proves it by firing TWO defeat banners, one per head.

        Any discriminator that suppresses one of them is wrong however good it looks elsewhere: it
        would delete a real boss's reward rather than a duplicate. The 14 checks these two share are
        a PARTITIONING problem (still open on #363), and partitioning is not what suppression does.

        The rule that keeps this safe is that a head firing its OWN banner is never eligible to be a
        secondary. This test is what stops a future threshold quietly collapsing two real fights."""
        for ent in (31190800, 31190850):
            self.assertIn(ent, self.DS, "m31_19 head %d lost its sweep trigger -- Sage's Cave holds "
                          "TWO separate fights and must keep BOTH (#363 negative control)." % ent)
        pairs = self._arena_pairs()
        self.assertFalse({31190800, 31190850} & set(pairs), "a Sage's Cave head was classified as a "
                         "secondary arena head. Both fire their own defeat banner, so both are "
                         "fights in their own right: " + repr(pairs))

    def test_dungeon_sweeps_on_one_map_are_DISJOINT(self):
        """THE LAST FORM OF #363. A dungeon can hold two genuinely separate fights -- m31_19 Sage's
        Cave is Black Knife Assassin AND Necromancer Garris, and its EMEVD fires a banner for each.
        Members are keyed on the MAP, so both triggers held the SAME list and killing either paid
        out all 14 of the cave's checks, including the other boss's.

        Suppression cannot fix it: both are real fights, so removing a trigger deletes a real
        reward. Geometry cannot either -- measured 2026-08-04, all 14 checks are nearer Garris by
        20-30m, so nearest-boss gives him all 14 and the Assassin zero. And there is no owner to
        recover: none of the 32 residual checks carries an EMEVD arena association and every one is
        untagged filler.

        So they are PARTITIONED, exactly as the legacy region pools are. This asserts the property
        that matters and not the mechanism: no two triggers on one map may share a member."""
        by_map = defaultdict(list)
        for ent in self.DS:
            info = self.BH.get(ent)
            if info and info[2] in DUNGEON_CLASSES:
                by_map[info[0]].append(ent)
        overlaps = []
        for bmap, ents in sorted(by_map.items()):
            ents = sorted(ents)
            for i in range(len(ents)):
                for j in range(i + 1, len(ents)):
                    shared = set(self.DS[ents[i]]) & set(self.DS[ents[j]])
                    if shared:
                        overlaps.append((bmap, ents[i], ents[j], len(shared)))
        self.assertEqual(overlaps, [], str(len(overlaps)) + " pair(s) of triggers on ONE dungeon map "
                         "share members -- killing either boss pays out both their checks (#363). "
                         "They must be partitioned, never duplicated: " + repr(overlaps))

    def test_the_multi_fight_dungeons_still_PARTITION_their_whole_pool(self):
        """The other half of the invariant: disjoint is cheap if you drop checks.

        A partition must lose NOTHING -- the union over a map's triggers is still every check that
        map ever swept. Pinned on the four maps that have two defeat banners each, with the counts,
        so both a shrunken pool and a vanished trigger fail here rather than looking like a tidier
        sweep. 🛑 m31_19 in particular must stay 7/7: 14/0 is what nearest-boss geometry produced,
        and it reads as a working partition until you notice a boss drops nothing."""
        EXPECTED = {"m30_05": ((30050800, 30050850), 4),
                    # 10 -> 14 (2026-08-05, SPEC-broaden-sweeps piece B). WHY, as this test
                    # demands: Auriza Side Tomb's four Living Jar Shards (f30137960/70/80/90) are
                    # `global_filler` rows on m30_13. They were never excluded for an ownership or
                    # geometry reason -- only because `_swept` keyed its dungeon branch on
                    # method == flag_prefix. The pool GREW; nothing left it, and the split stays 7/7.
                    "m30_13": ((30130800, 30130810), 14),
                    # 4 -> 5 (2026-08-13, #191). WHY, as this gate demands: the map gained a
                    # real fifth check -- the Sage Robe/Trousers family (flag 31047060) projects a
                    # sibling co-check, and a sibling inherits its primary's sweep membership
                    # (gen_data mirrors it; a sibling is the same physical pickup, so a sweep that
                    # pays the primary has already paid this). The pool GREW; nothing was lost, which
                    # is what the partition invariant is actually protecting.
                    "m31_00": ((31000800, 31000850), 5),
                    "m31_19": ((31190800, 31190850), 14)}
        for bmap, (heads, total) in sorted(EXPECTED.items()):
            slices = [sorted(self.DS.get(h, [])) for h in heads]
            for h, sl in zip(heads, slices):
                self.assertTrue(sl, "%s head %d has NO sweep -- a partition may not delete a "
                                    "trigger that fires its own defeat banner (#363)." % (bmap, h))
            union = set().union(*(set(sl) for sl in slices))
            self.assertEqual(len(union), total, "%s partitions %d check(s), expected %d -- a "
                             "partition must lose nothing. If the map's pool legitimately moved, "
                             "say WHY here." % (bmap, len(union), total))
            # No head may be starved: with 2 heads and >=2 checks every slice is non-trivial, and a
            # lopsided split is the geometry failure mode this test exists to catch.
            self.assertLessEqual(max(len(sl) for sl in slices) - min(len(sl) for sl in slices), 1,
                                 "%s split is lopsided (%s) -- round-robin gives slices within 1 of "
                                 "each other; a skewed split means something ordered by position, "
                                 "which is the nearest-boss failure (%s)." % (
                                     bmap, [len(x) for x in slices], heads))

    def test_no_head_is_both_a_primary_and_a_secondary(self):
        """A head cannot both report a fight and be reported by one.

        If it could, suppression order would decide the outcome and two triggers could vanish
        together -- which is the m30_20 shape (a map losing its last reporter) reached by a different
        route. Cheap, and it fails on the exact table corruption that would be hardest to see."""
        pairs = self._arena_pairs()
        both = sorted(set(pairs) & {p for p, _e in pairs.values()})
        self.assertEqual(both, [], "head(s) appear as BOTH secondary and primary in "
                         "boss_arena_pairs.tsv: " + repr(both))

    def test_suppression_never_takes_a_maps_LAST_head(self):
        """THE REGRESSION THE FIRST DRAFT SHIPPED. `defeat_flag != area_id` is NOT "secondary":
        m30_20's Stray Mimic Tear (30200800) is that map's ONLY healthbar entity and its row points
        at 30200810, a flag no entity carries. Suppressing on the mismatch alone deleted m30_20's
        sweep outright and stranded aps 7772247/7772248.

        The invariant that catches it without over-reaching: a dungeon map may never have ALL of its
        heads classified secondary. A secondary head means "another head on THIS map reports the
        fight", so at least one head must always remain to be that reporter. (A map with a boss but
        no swept members legitimately has no trigger -- m34_15 -- which is why this asks about heads
        rather than about triggers.)"""
        areas, pairs = self._game_areas(), self._arena_pairs()

        def secondary(ent, bmap):
            # BOTH sources. A derived table is not exempt from the guard the hand path needed -- if
            # anything it needs it more, since a re-emit can add rows without anyone reading them.
            return self._secondary(ent, bmap, areas, pairs) is not None

        by_map = {}
        for ent, info in self.BH.items():
            bmap, _tile, cls, _name = info
            if cls in DUNGEON_CLASSES:
                by_map.setdefault(bmap, []).append(ent)
        eaten = [(bmap, ents) for bmap, ents in sorted(by_map.items())
                 if ents and all(secondary(e, bmap) for e in ents)]
        self.assertEqual(eaten, [], str(len(eaten)) + " dungeon map(s) would have EVERY head "
                         "suppressed as secondary, leaving nothing to report the fight -- the "
                         "#363 first-draft regression (m30_20 lost its whole sweep this way): "
                         + repr(eaten))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class SweepSlotIsInTheDefaultSurface(unittest.TestCase):
    """The 2026-08-13 default change (#631), pinned where it can be read.

    RULE 11 MOTIVATING CASE. `SweepSlot` joining SURFACE_DEFAULT_CLASSES changes every seed: a sweep
    can now pay out progression, which under a non-empty surface it never did. The failure this
    guards is not someone deleting the class -- that reddens loudly. It is the class staying in the
    VOCABULARY while quietly leaving the DEFAULT, or the shipped template's explicit
    `progression_surface:` list not carrying it. Either one silently restores the old behaviour for
    every player while `SweepSlot` still appears in the wizard, which is the exact shape of
    [[er-unfreezing-an-option-needs-the-class-default]]: a default that moved without anybody saying
    so.

    🛑 THE TEMPLATE IS HALF THE ASSERTION, and it is the half that would have been missed. The class
    default reaches only a yaml that does NOT name `progression_surface`. The shipped template names
    it explicitly, as a list, so a player generating from the shipped file gets the LIST, not the
    default -- and adding the class to `contract.py` alone would have shipped a default change that
    reached nobody who used the template.
    """

    def test_class_is_in_the_default_and_is_derived(self):
        ct = _mod("contract")
        if not ct:
            self.skipTest("contract.py not importable")
        self.assertIn("SweepSlot", ct.SURFACE_DEFAULT_CLASSES,
                      "SweepSlot left the DEFAULT progression surface. That silently reverts every "
                      "seed to ~30 surface checks and takes foreign-progression intake back to a "
                      "tenth of what it should be (er-archipelago#631). If it is deliberate, the "
                      "changelog entry has to move with it.")
        self.assertIn("SweepSlot", ct.SURFACE_DERIVED_CLASSES,
                      "SweepSlot is in the default but is no longer declared DERIVED, so every "
                      "reader of SURFACE_CLASSES will treat it as a location tag and find nothing.")

    def test_the_shipped_template_names_it(self):
        # Resolve from either layout, first existing wins -- same pattern as REGION_MAP_CSV above.
        # In an INSTALLED world the repo root is not reachable, so this SKIPS there rather than
        # asserting against a path that cannot exist; the repo-side CI job is where it bites.
        path = next((p for p in (os.path.join(os.path.dirname(GREENFIELD), "release", "EldenRing.yaml"),
                                 os.path.join(GF_PKG, "EldenRing.yaml"))
                     if os.path.isfile(p)), None)
        if path is None:
            self.skipTest("release/EldenRing.yaml not reachable from this layout")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        block = re.search(r"^  progression_surface:\s*\n((?:\s+- .*\n)+)", text, re.M)
        self.assertIsNotNone(
            block, "release/EldenRing.yaml no longer carries a list-form `progression_surface:`. If "
                   "it now omits the key entirely the class default applies and this test should be "
                   "deleted -- but say so, because it is the opposite of the assumption below.")
        listed = re.findall(r"-\s*(\S+)", block.group(1))
        self.assertIn("SweepSlot", listed,
                      "the shipped template lists progression_surface explicitly and does NOT list "
                      "SweepSlot, so every player generating from it gets the pre-#631 surface no "
                      "matter what contract.SURFACE_DEFAULT_CLASSES says. Listed: %s" % listed)
