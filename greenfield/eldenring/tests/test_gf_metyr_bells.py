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
    bells_to_force, _BELL_RHIA, _BELL_DHEO, _BELL_RHIA_REGION,
)

_DERIVED_9440 = 9440
_FREE_CHECK_TRAP = 2051450180
_RAKSHASA_SWEEP = 2051440800
_RHIA_REWARD_FLAG = 2053467600
_RHIA_REWARD_AP = 7773806


def test_dheo_is_forced_always():
    """Dheo is the CROSS-REGION conjunct: Metyr's checks region to Scadu Altus, its tile is Jagged
    Peak. Forcing it unconditionally is what keeps Metyr independent of the Jagged Peak Lock, i.e.
    what preserves the logic shape the 9440 force used to provide."""
    for kept in ([], ["Scadu Altus"], ["Scadu Altus", "Jagged Peak"], ["Limgrave"]):
        assert _BELL_DHEO in bells_to_force(kept), kept


def test_rhia_is_forced_only_when_its_own_region_is_sealed():
    """Kept -> the player rings it with the Hole-Laden Necklace and 7773806 stays earnable.
    Sealed -> Metyr's checks are not in the pool either, so the award costs nothing."""
    assert _BELL_RHIA not in bells_to_force([_BELL_RHIA_REGION, "Limgrave"])
    assert _BELL_RHIA in bells_to_force(["Limgrave"])
    assert _BELL_RHIA in bells_to_force([])


def test_the_derived_flag_and_the_free_check_trap_are_never_forced():
    """9440 is derived from the pair -- setting it too is a redundant manual override. 2051450180
    awards lot 106720 and would hand every seed check 7773893 for free."""
    for kept in ([], ["Scadu Altus"], ["Scadu Altus", "Jagged Peak"]):
        forced = bells_to_force(kept)
        assert _DERIVED_9440 not in forced, kept
        assert _FREE_CHECK_TRAP not in forced, kept


def test_rakshasa_cannot_pay_the_necklace_gated_rhia_reward():
    """The #664 bypass: a broad regional sweep used to grant Rhia's reward for killing Rakshasa."""
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
    from worlds.eldenring.features.legacy_key_gates import _LEGACY_EXTRA

    assert _RHIA_REWARD_AP not in DUNGEON_SWEEPS[_RAKSHASA_SWEEP]
    assert _RHIA_REWARD_FLAG in _LEGACY_EXTRA["Hole-Laden Necklace"]


def test_the_forced_set_reaches_slot_data():
    """A pure predicate nobody calls is a spec, not a fix: the flags must actually be in the
    startGraces the world emits."""
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
    expected = bells_to_force(t.world._kept())
    assert set(expected) <= set(graces), (expected, graces)
    assert _DERIVED_9440 not in graces
    assert _FREE_CHECK_TRAP not in graces
