"""The armed Leyndell rune wall is never WEAKER than the vanilla capital gate.

MOTIVATING CASE (2026-08-01, from a player report on 0.2.18 -- "I had 2 great runes, but couldn't
enter leyndell itself to make progress"). Triaging that turned up a soundness hole one step away
from it: `features/leyndell_gate.generate_early` used to do

    want = min(want, len(world._available_runes()))

on the theory that lowering the requirement is always safe. It is not. Our N is data-driven; the
game's capital main gate is a FIXED two-Great-Rune possession wall that does not clamp with us. And
while our wall is ARMED, `features/graces.WALL_ARMED["Leyndell"]` withholds the capital grace
bundle, so the physical gate is the ONLY way in. At N=1:

    logic says   "one Great Rune opens Leyndell"   ->  fill may put a region Lock in the capital
    the game says "two, or the gate stays shut"    ->  the player cannot open it. Stranded.

Two ways to land on N=1 with no warning: `num_regions` (default 6) keeping exactly one Great-Rune
region, or the player simply writing `leyndell_runes_required: 1` in their yaml -- it is a
Range(0, 6) and 1 is selectable.

THE RULE THIS FILE GUARDS. `gf_leyndell_runes` is either EMPTY (wall disarmed; the bundle is granted
on the Leyndell Lock and the player warps in past the physical gate -- the already-sound N=0 path)
or holds AT LEAST `VANILLA_CAPITAL_GATE_RUNES`. Never one. There is no third state, and the
disarmed state is the only safe response to a pool that cannot supply two runes.

NB the guard is deliberately stated over the ARMED SET, not over the option value: it is the set
`set_rules` and `graces.WALL_ARMED` both read, so it holds however a future caller arrives at it.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.features.leyndell_gate import (  # noqa: E402
    VANILLA_CAPITAL_GATE_RUNES, GREAT_RUNES)
from worlds.eldenring.features.graces import WALL_ARMED  # noqa: E402

GAME = "Elden Ring"


def _assert_never_armed_below_vanilla(world):
    """The invariant, in one place: empty, or >= the vanilla constant."""
    runes = list(getattr(world, "gf_leyndell_runes", []))
    assert len(runes) != 1 or VANILLA_CAPITAL_GATE_RUNES <= 1, (
        f"Leyndell wall ARMED at {len(runes)} rune(s) ({runes}) but the vanilla capital gate is a "
        f"fixed {VANILLA_CAPITAL_GATE_RUNES}-rune wall and the capital graces are withheld while "
        f"armed -- logic would believe a door open that the game keeps shut")
    assert not runes or len(runes) >= VANILLA_CAPITAL_GATE_RUNES, (
        f"armed rune wall {runes} is below the vanilla floor {VANILLA_CAPITAL_GATE_RUNES}")
    # And the arming predicate graces.py reads must agree with what we just checked.
    assert WALL_ARMED["Leyndell"](world) == bool(runes)


class TestFlooredAtVanilla(WorldTestBase):
    """A yaml asking for ONE rune must not produce a one-rune wall."""
    game = GAME
    options = {"num_regions": 0, "leyndell_runes_required": 1}

    def test_asking_for_one_arms_at_vanilla_or_not_at_all(self):
        _assert_never_armed_below_vanilla(self.world)

    def test_all_base_regions_kept_means_it_arms_rather_than_disarms(self):
        # num_regions 0 keeps everything, so the pool has all six Great Runes and there is no
        # excuse to disarm -- the floor must ARM at 2, not silently drop the gate.
        assert len(GREAT_RUNES) >= VANILLA_CAPITAL_GATE_RUNES, "fixture assumes runes exist"
        assert len(self.world.gf_leyndell_runes) == VANILLA_CAPITAL_GATE_RUNES


class TestDefaultIsUnchanged(WorldTestBase):
    """The floor is a no-op on the shipped default -- this is a fix, not a difficulty change."""
    game = GAME
    options = {"num_regions": 0}

    def test_default_still_arms_at_two(self):
        _assert_never_armed_below_vanilla(self.world)
        assert len(self.world.gf_leyndell_runes) == VANILLA_CAPITAL_GATE_RUNES


class TestDisarmedStaysDisarmed(WorldTestBase):
    """0 still means 0 -- the floor must not resurrect a gate the player turned off."""
    game = GAME
    options = {"num_regions": 0, "leyndell_runes_required": 0}

    def test_zero_is_not_floored_up(self):
        assert self.world.gf_leyndell_runes == []
        assert WALL_ARMED["Leyndell"](self.world) is False


class TestAboveTheFloorIsUntouched(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "leyndell_runes_required": 4}

    def test_four_stays_four(self):
        _assert_never_armed_below_vanilla(self.world)
        assert len(self.world.gf_leyndell_runes) == 4


class TestScarceRunePoolDisarmsRatherThanArmsLow(WorldTestBase):
    """num_regions sealing rune regions must DISARM, never arm below vanilla.

    This is the case the old clamp got wrong. We do not pin which regions a given num_regions keeps
    (that is the seed's business and would make this a change-detector), so the assertion is the
    invariant itself across a spread of seeds: whatever the pool turns out to hold, the wall is
    empty or >= 2.
    """
    game = GAME
    options = {"num_regions": 2}
    auto_construct = False

    def test_invariant_holds_across_seeds(self):
        for seed in range(12):
            self.world_setup(seed)
            _assert_never_armed_below_vanilla(self.world)
            avail = self.world._available_runes()
            if len(avail) < VANILLA_CAPITAL_GATE_RUNES:
                assert self.world.gf_leyndell_runes == [], (
                    f"seed {seed}: only {len(avail)} Great Rune(s) in the pool, so the wall cannot "
                    f"be armed soundly -- it must disarm and let the capital bundle grant")
