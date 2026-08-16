"""Ending-condition (Great-Rune goal) tests -- WorldTestBase.

Covers the greenfield EndingCondition / GreatRunesRequired goal wired into core.py:
  * region_locks (default): goal unchanged -- completion needs every kept lock, no runes.
  * great_runes + item_shuffle on: seed still fills/beatable AND the goal actually requires the
    Great Runes (dropping a required rune breaks completion; the required runes are progression).
  * heavily-sealed seed (num_regions=1) + great_runes: the requirement auto-drops to what's
    reachable (here 0 -- only Limgrave survives, which has no Great Rune), so the seed collapses to
    the region_locks goal and stays beatable. This is the winnability guard: under-require, never
    over-require.

Each subclass runs AP's base suite for free (test_fill etc.), so "beatable" is asserted by the
harness; the extra methods assert the goal shape. importorskips when AP isn't importable
(source-tree sandbox), so it's a no-op there and only runs once installed under Archipelago/worlds/.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring/tests/test_gf_ending.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.core import GREAT_RUNES  # noqa: E402
from ._util import world_items  # noqa: E402
from BaseClasses import ItemClassification  # noqa: E402

GAME = "Elden Ring"


def _held_runes(world, itempool):
    return [i for i in itempool if i.name in set(GREAT_RUNES)]


class RegionLocksGoalDefault(WorldTestBase):
    """Default ending goal is unchanged: all kept locks, zero Great Runes required."""
    game = GAME
    options = {"num_regions": 0, }  # ending_condition defaults to region_locks

    def test_no_runes_required_by_default(self):
        world = self.multiworld.worlds[self.player]
        self.assertEqual(world._required_runes(), [],
                         "region_locks (default) goal must require no Great Runes")

    def test_all_state_beats_without_runes(self):
        # get_all_state grants every item; goal must be reachable and must be lock-only.
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))

    def test_slot_data_reports_region_locks(self):
        sd = self.multiworld.worlds[self.player].fill_slot_data()
        self.assertEqual(sd["ending_condition"], "region_locks")
        self.assertEqual(sd["great_runes_required"], 0)


class GreatRunesGoalShuffleOn(WorldTestBase):
    """great_runes goal with item_shuffle on: beatable (base test_fill) AND the runes gate it."""
    game = GAME
    options = {"num_regions": 0, 
        "item_shuffle": True,
        "ending_condition": "great_runes",
        "goal_great_runes": 2,
    }

    def test_required_runes_resolved_and_progression(self):
        world = self.multiworld.worlds[self.player]
        req = world._required_runes()
        # full-region seed with shuffle on: at least the requested 2 runes must be reachable.
        self.assertEqual(len(req), 2, "full seed should honor great_runes_required=2")
        for name in req:
            self.assertIn(name, GREAT_RUNES)
        # the required runes are placed as progression items (so fill guarantees reachability).
        placed = [i for i in world_items(self)
                  if i.name in set(req)]
        self.assertTrue(placed, "required Great Runes must actually be in the pool")
        for i in placed:
            self.assertEqual(i.classification, ItemClassification.progression,
                             f"required Great Rune {i.name} must be progression")

    def test_goal_actually_needs_the_runes(self):
        world = self.multiworld.worlds[self.player]
        req = world._required_runes()
        cond = self.multiworld.completion_condition[self.player]
        # full state beats it.
        full = self.multiworld.get_all_state(False)
        self.assertTrue(cond(full))
        # removing a required rune from an otherwise-complete state breaks completion.
        # remove ALL copies of a required rune (Land of Shadow duplicates the runes, so state.has
        # stays true until every copy is gone) -> completion must then break.
        one = req[0]
        for victim in [i for i in world_items(self) if i.name == one]:
            full.remove(victim)
        self.assertFalse(cond(full),
                         "dropping every copy of a required Great Rune must break the great_runes goal")

    def test_slot_data_reports_great_runes(self):
        sd = self.multiworld.worlds[self.player].fill_slot_data()
        self.assertEqual(sd["ending_condition"], "great_runes")
        self.assertEqual(sd["great_runes_required"], 2)
        self.assertEqual(len(sd["great_rune_items"]), 2)


class GreatRunesGoalHeavilySealed(WorldTestBase):
    """num_regions=1 keeps a single drawn region (+ the always-kept goal region). Most single
    regions carry no Great Rune, so the requirement auto-drops and the seed reverts to
    region_locks -- and either way it must stay beatable. The assertions below are premise-free:
    they compare the requirement against whatever _available_runes() the draw actually produced,
    so they hold for a draw that DOES land a rune region as well as one that does not."""
    game = GAME
    options = {
        "item_shuffle": True,
        "num_regions": 1,
        "ending_condition": "great_runes",
        "goal_great_runes": len(GREAT_RUNES),   # the MAXIMUM, whatever it currently is
    }

    def test_requirement_auto_drops(self):
        world = self.multiworld.worlds[self.player]
        avail = world._available_runes()
        req = world._required_runes()
        self.assertEqual(len(req), len(avail),
                         "requirement must clamp to reachable Great Runes")
        self.assertLessEqual(len(req), 7)
        # if no Great Rune region survived, the goal must collapse to locks-only (req == []).
        if not avail:
            self.assertEqual(req, [],
                             "no reachable Great Rune -> goal falls back to region_locks")

    def test_still_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state),
                        "heavily-sealed great_runes seed must remain winnable")

    def test_slot_data_matches_effective_requirement(self):
        world = self.multiworld.worlds[self.player]
        sd = world.fill_slot_data()
        self.assertEqual(sd["great_runes_required"], len(world._required_runes()))
        expected = "great_runes" if world._required_runes() else "region_locks"
        self.assertEqual(sd["ending_condition"], expected)



def _rune_sets():
    """The Great Rune set as each consumer sees it. One entry per module that used to carry its own
    `endswith("Great Rune")` copy."""
    from worlds.eldenring import item_categories
    from worlds.eldenring.core import GREAT_RUNES as core_runes
    from worlds.eldenring.features.leyndell_gate import GREAT_RUNES as gate_runes
    from worlds.eldenring.features.natural_progression import GREAT_RUNES as np_runes
    from worlds.eldenring.features.legacy_key_gates import _GREAT_RUNES as key_runes
    return {
        "item_categories": frozenset(item_categories.GREAT_RUNES),
        "core": frozenset(core_runes),
        "features/leyndell_gate": frozenset(gate_runes),
        "features/natural_progression": frozenset(np_runes),
        "features/legacy_key_gates": frozenset(key_runes),
    }


def test_there_are_seven_great_runes_and_every_goods_id_resolves():
    """Alaric's ruling, 2026-08-16: seven everywhere, the Unborn rune is a full citizen.

    Asserted through `GREAT_RUNES_MISSING` as well as the count, because those fail differently: a
    count of six tells you the set is wrong, the missing list tells you WHICH goods row stopped
    resolving. The old bug had no such signal -- the set just quietly answered a smaller question.
    """
    from worlds.eldenring import item_categories

    assert item_categories.GREAT_RUNES_MISSING == (), (
        f"goods rows {item_categories.GREAT_RUNES_MISSING} are declared Great Runes but resolve to "
        f"no catalog name. Either gen_data dropped them or their ids moved -- do NOT shrink the set "
        f"to match, that is exactly how it went from seven to six unnoticed.")
    assert len(item_categories.GREAT_RUNES) == 7, (
        f"expected seven Great Runes, found {len(item_categories.GREAT_RUNES)}: "
        f"{item_categories.GREAT_RUNES}")
    assert "Great Rune of the Unborn" in item_categories.GREAT_RUNES, (
        "the Unborn rune is a full citizen (Alaric, 2026-08-16) -- Rennala drops it on flag 197 and "
        "the game counts it toward the Leyndell wall")


def test_every_consumer_sees_the_same_seven():
    """THE ANTI-DRIFT GUARD, and the one this bug actually needed.

    Four modules each carried their own `endswith("Great Rune")` over ITEM_CATALOG. They AGREED, so
    no drift gate could see anything wrong -- they were four copies of one predicate that was wrong
    in one place. Pinning them to each other is not enough on its own; pinning them to
    item_categories, which is now the only definition, is what makes a fifth copy impossible to add
    quietly.
    """
    sets = _rune_sets()
    canonical = sets["item_categories"]
    assert len(canonical) == 7, f"canonical set is not seven: {sorted(canonical)}"
    for who, got in sets.items():
        assert got == canonical, (
            f"{who} sees a different Great Rune set than item_categories.\n"
            f"  only in {who}: {sorted(got - canonical)}\n"
            f"  missing from {who}: {sorted(canonical - got)}")


def test_every_great_rune_is_reachable_as_a_check():
    """The #405 failure mode from the other side: a cap of seven is only honest if seven runes can
    actually be in the pool. Each rune must sit on exactly one location, or `great_runes_required:
    7` advertises a goal no seed can satisfy -- which is the reporter's original complaint."""
    from worlds.eldenring import item_categories
    from worlds.eldenring.item_ids import LOCATION_ITEM

    placed = {}
    for ap_id, name in LOCATION_ITEM.items():
        if name in set(item_categories.GREAT_RUNES):
            placed.setdefault(name, []).append(ap_id)
    assert len(placed) == 7, (
        f"only {len(placed)} of 7 Great Runes are on a location; "
        f"unplaced: {sorted(set(item_categories.GREAT_RUNES) - set(placed))}")
    multi = {n: aps for n, aps in placed.items() if len(aps) != 1}
    assert not multi, f"a Great Rune on more than one location double-counts in the pool: {multi}"


def test_the_great_rune_cap_is_derived_not_typed():
    """CONTRIBUTING rule 11: the reporter's case is the acceptance test.

    > *"I cant goal my game. this is because Elden Ring has 7 great runes. And I set my goal
    > condition to be having all 7 great runes. However, the archipelago mod. Doesn't count 'Great
    > rune of the Unborn' as a great rune."*

    He set the option to its own advertised maximum and it was unreachable. `range_end` was the
    literal 7 while `GREAT_RUNES` yielded six, so #405 lowered the cap to `len(GREAT_RUNES)` --
    which made the option HONEST but conceded his point rather than answering it.

    🛑 2026-08-16: he was right and the cap is SEVEN again. Rennala's flag-197 co-check put goods
    10080 in the catalog and on a location on 2026-08-06; the derivation could not see it because
    it was a name-suffix match and "Great Rune of the Unborn" does not carry the suffix. It is now
    keyed on the goods row. Still an EQUALITY against the collection, never `== 7`, so the cap keeps
    moving with the data instead of re-opening this bug from either side.
    """
    from worlds.eldenring.core import GreatRunesRequired

    assert GreatRunesRequired.range_end == len(GREAT_RUNES), (
        f"great-rune goal cap is {GreatRunesRequired.range_end} but only {len(GREAT_RUNES)} Great "
        f"Rune items exist ({sorted(GREAT_RUNES)}). A player who sets the advertised maximum gets a "
        f"goal no seed can satisfy.")
    assert GreatRunesRequired.range_start <= GreatRunesRequired.default <= GreatRunesRequired.range_end
