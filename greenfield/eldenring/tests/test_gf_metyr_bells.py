"""Metyr's bells -- WHICH flags the run forces at spawn, and which it must never force.

MOTIVATING CASE (CONTRIBUTING rule 11). Until 2026-08-14 this feature forced 9440, the flag
common.emevd DERIVES from the two Finger Ruins bells. It opened the throne and nothing else:
Count Ymir's talk ESD reads the BELL flags, not 9440, so with the bells unrung he stayed seated,
his dialogue never exhausted, and the questline did not move (Alaric, playtest 2026-08-14).
Forcing a derived flag is the redundant manual override CONTRIBUTING warns about, and here the
override hid the fact that the real prerequisite was never met.

THE OTHER HALF of the case is why we do not simply force both bells. A preset bell flag makes its
tile's event award the lot on load:
    Rhia  2053460600 -> lot 2053460600 -> check flag 2053467600  (Cerulean Seed Talisman +1, 7773654)
    Dheo  2050400600 -> lot 2050400000 -> check flag 2050407000  (Crimson Seed Talisman +1,  7773579)
so a forced bell SPENDS its check -- the same trap as 2051450180, whose forcing awards lot 106720
and popped check 7773757 (f400672) on the spot when it was set by hand in a playtest save (2026-08-13).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.start_grace import (  # noqa: E402
    _METYR_BELL_FLAGS, _BELL_DHEO, _BELL_DHEO_REGION, metyr_bells_to_force,
)

_DERIVED_9440 = 9440
_FREE_CHECK_TRAP = 2051450180
_RAKSHASA_SWEEP = 2051440800
_RHIA_REWARD_FLAG = 2053467600
# Every ap id in this file is a POSITIONAL id and was re-derived by FLAG IDENTITY from the
# regenerated tables/data.py when this branch merged main's #1515/#1518/#1526 renumber
# (2026-09-09): f2053467600 7773804 -> 7773654, f2050407000 7773728 -> 7773579, f400672
# 7773891 -> 7773757, f400661 7773753 -> 7773751, f400664 7773755 -> 7773753.
_RHIA_REWARD_AP = 7773654


def test_only_a_sealed_regions_bell_is_forced():
    """Dheo is real logic when its own region exists, and a cost-free bypass only when it does not.

    The region NAME is read off the shipped table (start_grace._BELL_DHEO_REGION), not typed here:
    m61_50_40 shipped as Jagged Peak until 2026-09-07 and is Shadow Keep (= Scaduview, folded into
    the Keep 2026-07-19) since, and a typed name would have made this test the thing that has to
    move every time the tile derivation is corrected.
    """
    assert _BELL_DHEO_REGION not in ("Roundtable Hold",), "Dheo's check must have a real region"
    assert metyr_bells_to_force(["Scadu Altus", _BELL_DHEO_REGION]) == []
    assert metyr_bells_to_force(["Scadu Altus"]) == [_BELL_DHEO]


def test_rakshasa_cannot_pay_the_necklace_gated_rhia_reward():
    """The #664 bypass: a broad regional sweep used to grant Rhia's reward for killing Rakshasa."""
    from worlds.eldenring.tables.boss_sweeps import DUNGEON_SWEEPS
    from worlds.eldenring.features.legacy_key_gates import _LEGACY_EXTRA

    assert _RHIA_REWARD_AP not in DUNGEON_SWEEPS[_RAKSHASA_SWEEP]
    assert _RHIA_REWARD_FLAG in _LEGACY_EXTRA["Hole-Laden Necklace"]


def test_bell_checks_are_named_and_tagged_as_the_actions():
    from worlds.eldenring.tables.data import LOCATIONS
    from worlds.eldenring.tables.location_tags import LOCATION_TAGS

    by_flag = {int(flag): (name, ap) for locations in LOCATIONS.values()
               for (name, ap, flag) in locations}
    expected = {2053467600: "Finger Ruins of Rhia", 2050407000: "Finger Ruins of Dheo"}
    for flag, ruins in expected.items():
        name, ap = by_flag[flag]
        assert f"Ring the {ruins} bell" in name
        assert "Seed Talisman" not in name
        assert "KeyItem" in LOCATION_TAGS[ap]


def test_no_live_bell_or_lot_trap_reaches_slot_data():
    """With both regions live, startGraces contains neither bell nor either unsafe helper flag."""
    WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
    from worlds.eldenring import contract

    class _T(WorldTestBase):
        game = "Elden Ring"
        run_default_tests = False
        options = {"num_regions": 0}

    t = _T()
    t.setUp()
    sd = t.world.fill_slot_data()
    graces = list(sd[contract.START_GRACES])
    assert {"Scadu Altus", "Jagged Peak"} <= set(t.world._kept())
    forbidden = set(_METYR_BELL_FLAGS) | {_DERIVED_9440, _FREE_CHECK_TRAP}
    assert not (forbidden & set(graces)), forbidden & set(graces)


def test_fill_with_both_bell_regions_and_with_jagged_peak_sealed():
    """Acceptance fixtures: the extra conjunct must not turn either region draw into a FillError."""
    WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
    from Fill import distribute_items_restrictive

    class _T(WorldTestBase):
        game = "Elden Ring"
        run_default_tests = False
        options = {"num_regions": 12, "enable_dlc": True, "item_shuffle": True,
                   "legacy_dungeon_keys": True, "accessibility": "minimal",
                   "leyndell_runes_required": 0}

    for seed, jagged_expected in ((63, True), (67, False)):
        t = _T("runTest")
        t.options = dict(_T.options)
        t.world_setup(seed)
        kept = set(t.world.gf_kept)
        assert "Scadu Altus" in kept and ("Jagged Peak" in kept) is jagged_expected, (seed, kept)
        distribute_items_restrictive(t.multiworld)
        assert t.multiworld.can_beat_game(), (seed, kept)


# ---------------------------------------------------------------------------------------------
# #1513 -- the rest of the Ymir/Metyr questline rewards, and the two flag-sharing reports.
# ---------------------------------------------------------------------------------------------
_ONE_BELL_FLAGS = {400661}
_BOTH_BELL_FLAGS = {400662, 330030, 400664, 400666}
_DEFERRED_FLAGS = {400672, 68580}


def test_every_ymir_reward_flag_is_necklace_gated():
    """#1513: each reward's vanilla award state is downstream of a bell, and both bell ObjActs are
    held closed until PlayerHasItem(Goods, 2008008). So all of them owe the necklace."""
    from worlds.eldenring.features.legacy_key_gates import _LEGACY_EXTRA

    gated = _LEGACY_EXTRA["Hole-Laden Necklace"]
    assert (_ONE_BELL_FLAGS | _BOTH_BELL_FLAGS) <= gated


def test_both_bell_rewards_also_owe_dheos_region_lock():
    """common.emevd $Event(9440) is `2053460600 && 2050400600`. Anything gated on 9440 -- or on a
    state 9440 gates -- needs the far bell's region Lock, exactly as Metyr's remembrance does.

    The region NAME is never typed: _EXTRA_CHECK_LOCKS derives it from the shipped table.
    """
    from worlds.eldenring.features.legacy_key_gates import _EXTRA_CHECK_LOCKS, _DHEO_REGION

    if _DHEO_REGION is None:  # Dheo check absent -> start_grace forces the bell, no conjunct owed
        assert _EXTRA_CHECK_LOCKS == {}
        return
    expected = ("%s Lock" % _DHEO_REGION,)
    for flag in _BOTH_BELL_FLAGS | {510550}:
        assert _EXTRA_CHECK_LOCKS.get(flag) == expected, flag
    for flag in _ONE_BELL_FLAGS | _DEFERRED_FLAGS:
        assert flag not in _EXTRA_CHECK_LOCKS, flag


def test_the_deferred_rows_stay_ungated_until_their_evidence_exists():
    """A plausible gate is still a guess (CONTRIBUTING). f400672's award flag 2051450180 has one
    setter, m61_51_45 $Event(2051450722), whose antecedent f2051459721 is SET NOWHERE in the v1.17
    EMEVD/talk corpus -- it is only read, in Jolan's ESD (#1505). f68580 is a plain treasure corpse
    with no row in any of the four gate corpora. Neither may acquire a gate by association."""
    from worlds.eldenring.features.legacy_key_gates import _LEGACY_EXTRA, _YMIR_DEFERRED

    assert _YMIR_DEFERRED == _DEFERRED_FLAGS
    for flag in _DEFERRED_FLAGS:
        assert flag not in _LEGACY_EXTRA["Hole-Laden Necklace"], flag


def test_400661_is_two_lots_on_one_flag_and_both_are_checks():
    """#1513 defect 1, ADJUDICATED NOT A DEFECT. 255 never saw Beloved Stardust randomized and
    suspected the shared flag. ItemLotParam_map says 400661 is FOUR lots, not one lot with two
    items: 106610/106630 grant goods 2008017 (Ruins Map (2nd)) and 106611/106631 grant ACCESSORY
    8190, which AccessoryName_dlc01 names Beloved Stardust. The talisman has no flag of its own
    anywhere in the table, so 'find the stardust's own flag' has no answer -- the co-check model
    (SPEC-flag-lot-item-model 2.2) is already the right shape and both members are live checks that
    fire together. This pins that, so a future co-check regression cannot silently drop the sibling
    again.
    """
    from worlds.eldenring.tables.data import LOCATIONS

    rows = {ap: name for locations in LOCATIONS.values()
            for (name, ap, flag) in locations if int(flag) == 400661}
    assert set(rows) == {7773751, 7900096}, rows
    assert "Ruins Map (2nd)" in rows[7773751]
    assert "Beloved Stardust" in rows[7900096]


def test_400664_is_one_lot_family_presented_as_a_bundle():
    """#1513 defect 2, ADJUDICATED NOT A DEFECT. The six ap ids on 400664 are one getItemFlagId
    family of six ItemLotParam_map lots (106640 goods 2008901 + 106641 weapon 33520000 + 106642-45
    protectors 5060000/100/200/300), all awarded together by common.emevd $Event(4857). Six checks
    is what the co-check model owes them; the BUNDLE presentation lives on the ITEM side, where
    armor_bundles already folds the four protector pieces into one 'High Priest Set'.
    """
    from worlds.eldenring.tables.data import LOCATIONS
    from worlds.eldenring.tables.item_ids import ARMOR_BUNDLES

    aps = {ap for locations in LOCATIONS.values()
           for (_n, ap, flag) in locations if int(flag) == 400664}
    assert aps == {7773753, 7900097, 7900098, 7900099, 7900100, 7900101}
    assert len(ARMOR_BUNDLES["High Priest Set"]) == 4


class YmirRewardGateBinds(WorldTestBase):
    """The rules actually BIND, not just the tables. Mirrors the harness
    test_gf_legacy_key_gate.LegacyKeyGateOn already uses for the Metyr chain."""
    game = "Elden Ring"
    run_default_tests = False
    options = {"item_shuffle": True, "num_regions": 0, "legacy_dungeon_keys": True,
               "leyndell_runes_required": 0, "accessibility": "minimal"}

    def test_no_ymir_reward_is_reachable_without_the_necklace(self):
        from BaseClasses import ItemClassification as IC, CollectionState
        from worlds.eldenring.tables.data import LOCATIONS
        from ._util import world_items

        world = self.multiworld
        items = world_items(self)
        dheo_region = next(reg for reg, locations in LOCATIONS.items()
                           for (_n, _ap, flag) in locations if int(flag) == 2050407000)
        lock_name = "%s Lock" % dheo_region
        necklace = next(it for it in items if it.name == "Hole-Laden Necklace")
        lock = next(it for it in items if it.name == lock_name)
        withheld = {necklace.name, lock.name}

        def _state(*extras):
            st = CollectionState(world)
            for item in items:
                if item.name in withheld:
                    continue
                if item.classification & IC.progression:
                    st.collect(item, prevent_sweep=True)
            for item in extras:
                st.collect(item, prevent_sweep=True)
            return st

        bare, with_necklace, with_both = _state(), _state(necklace), _state(necklace, lock)
        by_flag = {}
        for locations in LOCATIONS.values():
            for (name, _ap, flag) in locations:
                by_flag.setdefault(int(flag), []).append(name)

        for flag in _ONE_BELL_FLAGS | _BOTH_BELL_FLAGS:
            for name in by_flag[flag]:
                loc = world.get_location(name, self.player)
                assert not loc.can_reach(bare), "%s reachable with no necklace" % name
                assert loc.can_reach(with_both),                     "%s unreachable with necklace + %s" % (name, lock_name)
                if flag in _BOTH_BELL_FLAGS:
                    assert not loc.can_reach(with_necklace),                         "%s must also need %s" % (name, lock_name)
