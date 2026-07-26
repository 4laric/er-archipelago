"""GESTURE PICKUPS: the detect-only checks that never existed (gen_data._gesture_derive).

TWO populations, 14 checks. Both are EMEVD awards, so the whole class is DETECT-ONLY: the flag poll
sees it, nothing can suppress the vanilla gesture, and the coverage gate classifies it
'event_award_unsuppressable' -- explicitly, never folded into "no ware".

(a) WORLD PICKUPS -- 7 checks (ground truth 2026-07-14). common_func $Event(90005570) /
    $Event(900005571) are the game's parameterized gesture-pickup events; the map EMEVDs call them
    at exactly 9 sites. 8 are standalone 90005570 pickups over 7 distinct flags (60824 "Fire Spur
    Me" has two physical pickups sharing ONE flag = one check); the single 900005571 site (60860)
    RIDES the Monk's Missive treasure f2048457510 -- already a live check -- so minting it would
    put two locations on one interaction, and the derivation skips it.

(b) NPC / QUEST AWARDS -- 7 checks, scoped IN 2026-07-26 (Alaric: questline content is randomised +
    MISSABLE now, not excluded). These are the literal AwardGesture sites in map EMEVDs that
    _gesture_derive used to COUNT and discard. 9 sites -> 7 with an acquisition flag of their own;
    m16_00's site is PARAMETERIZED and resolved at its $InitializeEvent CALL SITE.

🛑 The other 2 sites are REFUSED, and the refusal is pinned below. m10_00/10002691 (gesture 94) and
m18_00/18002690 (gesture 9) fire on flags 10007490 / 18007090 that are set by NOTHING -- absent from
all 589 decompiled EMEVD (only those two events READ them), from the complete 365-file talk ESD, from
ItemLotParam_map, flag_lots.tsv, region_map.csv and msb_flag_region.tsv. A check on a flag that can
never turn ON is a DEAD check. They were first misread as "riders on an existing treasure" and the
derivation's liveness guard is what caught that.
"""
import json
import os

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import HUB, LOCATIONS, REGIONS, GESTURE_AWARD_FLAGS  # noqa: E402
from worlds.eldenring import coverage as cov  # noqa: E402

GAME = "Elden Ring"
# (a) world pickups, via the two common events
EXPECTED_WORLD = {60809, 60822, 60824, 60833, 60836, 60861, 60864}
# (b) NPC/quest awards, literal AwardGesture in map EMEVDs (2026-07-26)
#   60843 m11_10 ev 11103706 g102 | 60802 m16_00 ev 16003762 g2 (call-site arg) |
#   60819 m31_00 ev 31003704 g41  | 60832 m31_00 ev 31003714 g90 |
#   60826 m60_42_36 ev 1042363703 g60 | 60801 m60_51_36 ev 1051360734 g1 |
#   60829 m60_51_56 ev 1051563701 g72
EXPECTED_NPC = {60801, 60802, 60819, 60826, 60829, 60832, 60843}
EXPECTED = EXPECTED_WORLD | EXPECTED_NPC
# flags the derivation must REFUSE: nothing in any corpus sets them (see the module docstring)
REFUSED_DEAD_FLAGS = {10007490, 18007090}


def _gesture_locs():
    return [(region, name, ap_id, flag)
            for region, locs in LOCATIONS.items()
            for (name, ap_id, flag) in locs if flag in GESTURE_AWARD_FLAGS]


class TestGestureData:
    def test_the_fourteen_pickups_exist_once_each(self):
        # The SET is the pin; the count follows from it. 7 world + 7 NPC/quest, disjoint.
        assert EXPECTED_WORLD & EXPECTED_NPC == set(), "the two populations must not overlap"
        assert set(GESTURE_AWARD_FLAGS) == EXPECTED
        locs = _gesture_locs()
        assert len(locs) == len(EXPECTED) == 14, \
            f"each gesture flag must be exactly one location, got {locs}"
        assert {f for (_r, _n, _a, f) in locs} == EXPECTED

    def test_the_dead_flag_awards_stay_refused(self):
        # A gesture award whose flag nothing can set would be a check that can never fire. If one of
        # these ever becomes a location, something started setting the flag -- find out WHAT before
        # accepting it (the derivation FATALs on exactly that transition).
        all_flags = {f for locs in LOCATIONS.values() for (_n, _a, f) in locs}
        assert not (REFUSED_DEAD_FLAGS & all_flags), \
            "a gesture award on an unsettable flag was minted as a check"

    def test_alarics_find_is_a_check_in_leyndell(self):
        # "By My Sword" paying vanilla in Leyndell (in-game 2026-07-14) is what exposed the class.
        by_my_sword = [(r, n) for (r, n, _a, f) in _gesture_locs() if f == 60822]
        assert len(by_my_sword) == 1, by_my_sword
        region, name = by_my_sword[0]
        assert region == "Leyndell", region
        # The tracker-description pass may append "- around <grace>" to the check NAME, so match the
        # stable parts (the item + its flag), not the exact string.
        assert "By My Sword" in name and "[f60822]" in name, name

    def test_regions_are_real(self):
        for (region, name, _a, _f) in _gesture_locs():
            assert region in REGIONS or region == HUB, f"{name} in unknown region {region!r}"

    def test_rider_flag_is_not_a_location_but_its_treasure_is(self):
        # 60860 (gesture 111) rides treasure f2048457510; the treasure must be the (only) check.
        all_flags = {f for locs in LOCATIONS.values() for (_n, _a, f) in locs}
        assert 60860 not in all_flags, "the 900005571 rider must not mint a second location"
        assert 2048457510 in all_flags, "the ridden treasure must remain a live check"

    def test_detect_only_premise_flags_absent_from_award_table(self):
        # a gesture flag appearing in check_lots_table.json would mean an ItemLotParam row awards
        # it -- the detect-only premise would be dead and the derivation must be redesigned.
        path = os.path.join(os.path.dirname(os.path.abspath(cov.__file__)), "check_lots_table.json")
        with open(path, encoding="utf-8") as fh:
            t = json.load(fh)
        for f in EXPECTED:
            for part in ("map", "enemy", "items"):
                assert str(f) not in t.get(part, {}), f"gesture flag {f} in check_lots_table[{part}]"

    def test_coverage_classifies_event_award_unsuppressable(self):
        records, ctx, byname = cov.report_coverage(world=None, printer=None)
        recs = {r.detect_flag: r for r in records.values() if r.detect_flag in EXPECTED}
        assert set(recs) == EXPECTED, "gesture locations missing from coverage scope"
        for f, rec in recs.items():
            assert rec.suppress_kind == "event_award_unsuppressable", \
                f"flag {f}: {rec.suppress_kind} (must be the explicit detect-only kind)"
            assert rec.vanilla_item, "the ware must stay visible (never folded into 'no ware')"
        assert sum(len(v) for v in byname.values()) == 0, "gate must be green with the class sanctioned"

    def test_wares_stay_out_of_the_pool_tables(self):
        # no verified client grant path for a gesture-linked goods id -> not in LOCATION_ITEM (the
        # shuffle pool source) and not armed by checkItemFlags.
        from worlds.eldenring.item_ids import LOCATION_ITEM
        for (_r, _n, ap_id, _f) in _gesture_locs():
            assert ap_id not in LOCATION_ITEM


class GestureSeed(WorldTestBase):
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "item_shuffle": True}

    def test_gesture_checks_reach_the_client_and_arm_nothing(self):
        sd = self.world.fill_slot_data()
        lf = sd["locationFlags"]
        by_flag = {int(v): k for k, v in lf.items()}
        for f in EXPECTED:
            assert f in by_flag, f"gesture flag {f} absent from locationFlags (flag poll blind)"
        armed = {int(f) for flags in sd.get("checkItemFlags", {}).values() for f in flags}
        assert not (armed & EXPECTED), "checkItemFlags armed a detect-only gesture flag"
