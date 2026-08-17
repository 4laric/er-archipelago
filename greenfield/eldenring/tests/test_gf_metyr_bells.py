"""Metyr's bells -- WHICH flags the run forces at spawn, and which it must never force.

MOTIVATING CASE (CONTRIBUTING rule 11). Until 2026-08-14 this feature forced 9440, the flag
common.emevd DERIVES from the two Finger Ruins bells. It opened the throne and nothing else:
Count Ymir's talk ESD reads the BELL flags, not 9440, so with the bells unrung he stayed seated,
his dialogue never exhausted, and the questline did not move (Alaric, playtest 2026-08-14).
Forcing a derived flag is the redundant manual override CONTRIBUTING warns about, and here the
override hid the fact that the real prerequisite was never met.

THE OTHER HALF of the case is why we do not simply force both bells. A preset bell flag makes its
tile's event award the lot on load:
    Rhia  2053460600 -> lot 2053460600 -> check flag 2053467600  (Cerulean Seed Talisman +1, 7773806)
    Dheo  2050400600 -> lot 2050400000 -> check flag 2050407000  (Crimson Seed Talisman +1,  7773730)
so a forced bell SPENDS its check -- the same trap as 2051450180, whose forcing awards lot 106720
and popped check 7773893 on the spot when it was set by hand in a playtest save (2026-08-13).
"""
import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.start_grace import (  # noqa: E402
    _METYR_BELL_FLAGS, _BELL_DHEO, metyr_bells_to_force,
)

_DERIVED_9440 = 9440
_FREE_CHECK_TRAP = 2051450180
_RAKSHASA_SWEEP = 2051440800
_RHIA_REWARD_FLAG = 2053467600
_RHIA_REWARD_AP = 7773806


def test_only_a_sealed_regions_bell_is_forced():
    """Dheo is real logic when Jagged Peak exists, and a cost-free bypass only when it does not."""
    assert metyr_bells_to_force(["Scadu Altus", "Jagged Peak"]) == []
    assert metyr_bells_to_force(["Scadu Altus"]) == [_BELL_DHEO]


def test_rakshasa_cannot_pay_the_necklace_gated_rhia_reward():
    """The #664 bypass: a broad regional sweep used to grant Rhia's reward for killing Rakshasa."""
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
    from worlds.eldenring.features.legacy_key_gates import _LEGACY_EXTRA

    assert _RHIA_REWARD_AP not in DUNGEON_SWEEPS[_RAKSHASA_SWEEP]
    assert _RHIA_REWARD_FLAG in _LEGACY_EXTRA["Hole-Laden Necklace"]


def test_bell_checks_are_named_and_tagged_as_the_actions():
    from worlds.eldenring.data import LOCATIONS
    from worlds.eldenring.location_tags import LOCATION_TAGS

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
