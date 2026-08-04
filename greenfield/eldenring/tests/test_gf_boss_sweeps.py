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

# = contract.IMPORTANT_LOCATION_TYPES. A field sweep must contain
# none of these -- felling a field boss hands out filler only. Kept in sync with contract by
# test_field_exclude_matches_contract below (drift guard).
FIELD_EXCLUDE = frozenset({"Remembrance", "Seedtree", "Church", "Boss", "Fragment", "Revered",
                           "Basin", "GreatRune", "KeyItem", "Legendary", "Shop", "ShopNonSpell",
                           "ShopSlot", "MajorBoss", "LegacyBoss", "FieldBoss"})
# LegacyBoss/FieldBoss (2026-08-02) are SUBSETS of Boss, which is already here, so adding them cuts
# nothing new -- every check they name was excluded already. They are listed because this set is a
# deliberate mirror of contract.IMPORTANT_LOCATION_TYPES and test_field_exclude_matches_contract
# demands exact parity: the guard exists so a new premium class cannot be added to the vocabulary
# while quietly staying eligible for a filler sweep.


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
        fs = str(self.ap_flag.get(ap, ""))
        # The X0SS7000 convention (flag -> map mXX_SS) is not base-only: the DLC minor dungeons use it
        # too (m40 catacombs, m41 gaols, m42 forges, m43 caves) -- e.g. 41017010 -> m41_01 (Curseblade
        # Labirith). An ItemLotParam_map flag's self-encoded map is AUTHORITATIVE over the `map` column:
        # 8 DLC dungeon lots (40007000/41027000/42007000/...) were column-tagged m18_00 (base-game
        # Stranded Graveyard), a mis-scan gen_data._swept_map_prefix now corrects by trusting the flag.
        # Mirror that here (flag wins for dungeon-lot flags) so this independent oracle re-derives the
        # SAME true map instead of trusting the stale column -- exactly what the docstring promises.
        if len(fs) >= 8 and fs[4] == "7" and fs[:2] in ("30", "31", "32", "40", "41", "42", "43"):
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
        want = set(getattr(ct, "IMPORTANT_LOCATION_TYPES", []))
        self.assertEqual(
            set(FIELD_EXCLUDE), want,
            "FIELD_EXCLUDE drifted from contract.IMPORTANT_LOCATION_TYPES; "
            "sync the field filler-only cut. got=%s want=%s" % (sorted(FIELD_EXCLUDE), sorted(want)))

    def test_field_sweeps_are_filler_only(self):
        bad = []
        for ent, info, members in self._members_by_class("field"):
            for ap in members:
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
                continue   # undecodable boss tile (the m60_48_55 DLC pair) -> gets no sweep anyway
            bx, by = int(bt.group(1)), int(bt.group(2))
            for ap in members:
                mt = self._TILE_RE.match(self._eff_map(ap) or "")
                if not mt or max(abs(int(mt.group(1)) - bx), abs(int(mt.group(2)) - by)) > 2:
                    bad.append((ent, info[3], info[1], ap, self._eff_map(ap)))
        self.assertEqual(bad, [], str(len(bad)) + " field-boss sweep member(s) beyond Chebyshev "
                         "distance 2 of the boss's tile (or not on an m60 tile at all). Sample: "
                         + repr(bad[:5]))

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
        bad = []
        for ent, info, members in self._members_by_class("legacy"):
            for ap in members:
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
        bonus_soul 0. A head whose defeat flag is ANOTHER entity on the SAME map must not trigger."""
        areas = self._game_areas()
        offenders = []
        for ent in self.DS:
            df = areas.get(ent)
            if df is None or df == 0 or df == ent:
                continue
            primary = self.BH.get(df)
            if primary is not None and primary[0] == self.BH.get(ent, (None,))[0]:
                offenders.append((ent, df, primary[0], self.BH[ent][3]))
        self.assertEqual(offenders, [], str(len(offenders)) + " secondary arena head(s) still carry a "
                         "sweep -- their fight is reported by another flag on the same map, so they "
                         "pay the dungeon out early (#363). Offenders (entity, defeat_flag, map, "
                         "name): " + repr(offenders))

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
        areas = self._game_areas()

        def secondary(ent, bmap):
            df = areas.get(ent)
            if df is None or df == 0 or df == ent:
                return False
            primary = self.BH.get(df)
            return primary is not None and primary[0] == bmap

        by_map = {}
        for ent, info in self.BH.items():
            bmap, _tile, cls, _name = info
            if cls in ("catacomb", "cave", "tunnel", "dungeon"):
                by_map.setdefault(bmap, []).append(ent)
        eaten = [(bmap, ents) for bmap, ents in sorted(by_map.items())
                 if ents and all(secondary(e, bmap) for e in ents)]
        self.assertEqual(eaten, [], str(len(eaten)) + " dungeon map(s) would have EVERY head "
                         "suppressed as secondary, leaving nothing to report the fight -- the "
                         "#363 first-draft regression (m30_20 lost its whole sweep this way): "
                         + repr(eaten))


if __name__ == "__main__":
    unittest.main(verbosity=2)
