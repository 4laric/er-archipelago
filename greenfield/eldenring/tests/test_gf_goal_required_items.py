"""goalRequiredItems -- the client must hold every kept Region Lock before Goal fires.

MOTIVATING CASE (CONTRIBUTING rule 11). Measured 2026-07-30 over generated seeds: on 25% of rolled
`num_regions` draws, fill placed the goal region's Lock in sphere 0, so the goal region was the
SECOND region opened. `core.set_rules` tells Archipelago the slot completes on
`has_all(kept Region Locks)` -- that is what fill balances around -- but the client's `goal.rs`
`is_met()` checked the goal BOSS FLAGS ALONE, and the client's Goal-send is what actually ends the
run. Two terminal conditions, one silently ignored: the player killed the boss on region two and the
run ended while the world still claimed every lock was required.

This file pins the WORLD half: the emitted list is exactly the list `set_rules` closes over, minus
the precollected start anchor. The CLIENT half (an unheld lock blocks the send) is pinned in
`goal.rs`'s own unit tests -- `killing_the_goal_boss_on_region_two_is_not_finishing_the_seed`.

🛑 Why there is no "the goal must be N locks deep" assertion here: the fix does NOT move fill. The
goal region's Lock is still placed wherever fill wants it, including sphere 0 -- the client simply
waits. A depth-floor assertion would be asserting something this change never promised, and would
fail forever. The measurement was the diagnosis; it is not the instrument.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features import natural_progression as _np  # noqa: E402

GAME = "Elden Ring"
KEY = "goalRequiredItems"


class TestContractShape:
    def test_the_key_is_declared_optional_and_greenfield_only(self):
        k = contract.BY_NAME[KEY]
        assert k.shape == "STR_LIST"
        assert k.required is False, (
            "REQUIRED would reject every pre-existing seed and every foreign apworld; the client "
            "treats an absent key as 'no added requirement' on purpose")
        assert contract.GREENFIELD in k.profiles and contract.BOTH not in k.profiles

    def test_the_name_constant_exists(self):
        # Emitters must never hard-code the wire string (contract.py's module-level constants).
        assert contract.GOAL_REQUIRED_ITEMS == KEY


class GoalRequiredItemsFullSeed(WorldTestBase):
    """num_regions 0: every region kept."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    def _free(self):
        return {i.name for i in self.multiworld.precollected_items[self.player]}

    def test_it_is_exactly_the_locks_set_rules_closes_over_minus_the_anchor(self):
        # THE anti-drift pin. Both sides read core.kept_lock_names(); if a future change rebuilds
        # either list independently, this fails.
        sd = self.world.fill_slot_data()
        expected = sorted(n for n in self.world.kept_lock_names() if n not in self._free())
        assert sd[KEY] == expected
        assert sd[KEY] == sorted(self.world.goal_required_lock_names())

    def test_every_kept_region_is_represented(self):
        sd = self.world.fill_slot_data()
        kept = set(self.world._kept())
        named = {n[: -len(" Lock")] for n in sd[KEY]}
        missing = kept - named - {r for r in kept if f"{r} Lock" in self._free()}
        assert not missing, f"kept regions absent from the goal requirement: {sorted(missing)}"

    def test_the_precollected_anchor_is_excluded(self):
        # The anchor lock leaves the pool (push_precollected), so requiring the player to HOLD it
        # would be requiring an item that is never sent -- an unwinnable seed.
        sd = self.world.fill_slot_data()
        anchors = self._free() & {f"{r} Lock" for r in self.world._kept()}
        assert anchors, "test basis broken: the shipping config precollects one region Lock"
        assert not (anchors & set(sd[KEY])), \
            f"the precollected anchor {sorted(anchors)} can never be RECEIVED -- Goal could never fire"

    def test_it_does_not_collide_with_great_rune_items(self):
        # Two independent keys; a great_runes seed needs the runes AND the locks. merge_slot_data
        # raises on duplicate top-level keys, so this also proves the emitters stayed separate.
        sd = self.world.fill_slot_data()
        assert KEY in sd
        assert set(sd[KEY]) & set(sd.get("great_rune_items", ())) == set()


class GoalRequiredItemsRolledSeed(WorldTestBase):
    """A rolled sub-draw -- the shape the measurement was taken on."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 6, "num_regions_order": "rolled"}

    def test_emitted_and_consistent_on_a_rolled_draw(self):
        sd = self.world.fill_slot_data()
        free = {i.name for i in self.multiworld.precollected_items[self.player]}
        assert sd[KEY] == sorted(n for n in self.world.kept_lock_names() if n not in free)
        assert sd[KEY], "a rolled seed keeps regions, so it must require their locks"


class GoalRequiredItemsUnderNaturalProgression(WorldTestBase):
    """🛑 THE DEADLOCK LEG. natural_progression mints ZERO Lock items -- its regionOpenFlags keys are
    '<Region> Lock' NAMES with no item behind them. Requiring them would make the seed unwinnable,
    which is exactly why the client must NOT derive this list from regionOpenFlags."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "natural_progression": True}

    def test_the_key_is_omitted_entirely(self):
        assert _np.is_on(self.world), "test basis broken: natural_progression is not on"
        sd = self.world.fill_slot_data()
        assert KEY not in sd, (
            "natural_progression mints no Lock items; emitting them as held-item goals would "
            "deadlock the seed")

    def test_no_lock_items_exist_to_require(self):
        assert self.world.kept_lock_names() == []
        assert self.world.goal_required_lock_names() == []
        names = {i.name for i in self.multiworld.itempool if i.player == self.player}
        assert not any(n.endswith(" Lock") for n in names)


class GoalRequiredItemsWithAnExplicitGoal(WorldTestBase):
    """The force-kept region of an explicit `goal` choice must also be required, or the choice would
    hand the player a shorter run than `auto`."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 6, "num_regions_order": "rolled", "goal": "promised_consort"}

    def test_the_forced_region_lock_is_required(self):
        sd = self.world.fill_slot_data()
        free = {i.name for i in self.multiworld.precollected_items[self.player]}
        assert "Enir Ilim" in self.world._kept()
        if "Enir Ilim Lock" not in free:
            assert "Enir Ilim Lock" in sd[KEY]
        assert sd[KEY] == sorted(n for n in self.world.kept_lock_names() if n not in free)
