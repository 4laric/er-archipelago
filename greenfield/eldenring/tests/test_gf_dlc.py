"""DLC region-scope tests -- EnableDLC / DLCOnly toggles (WorldTestBase, needs AP).

Covers the DLC filter wired into core.py + region_spine.py:
  * default (Enable DLC on, DLC Only off): every region eligible -- kept set unchanged, beatable.
  * Enable DLC off: DLC regions are sealed -- none appear in kept; base-game goal (Leyndell) still
    kept; seed beatable.
  * DLC Only on: ONLY DLC regions eligible -- every kept region is a DLC region, the base-game goal
    region is NOT kept, yet the seed is still beatable (goal = hold every kept lock).
  * combined with num_regions=3: each mode keeps exactly N-from-its-pool (+goal when the goal region
    is eligible) and stays beatable and filter-respecting.
  * DLC Only + great_runes: no Great Rune sits in a DLC region, so a great_runes goal collapses to region_locks
  (requirement shrinks to 0) and the seed stays winnable (v0.2; runes-in-Land-of-Shadow deferred)

Each subclass runs AP's base suite for free (test_fill etc.), so "beatable" is asserted by the
harness; the extra methods assert the filtered scope. importorskips when AP isn't importable
(source-tree sandbox), so it's a no-op there and only runs once installed under Archipelago/worlds/.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring/tests/test_gf_dlc.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.region_spine import (  # noqa: E402
    GOAL_REGION, DLC_REGIONS, SPINE, base_regions, dlc_regions,
)
from worlds.eldenring.core import GREAT_RUNES  # noqa: E402

GAME = "Elden Ring"
DLC = set(DLC_REGIONS)


def _kept_region_names(mw, player):
    """Regions actually instantiated for this player (sealed regions are never created), minus the
    always-present Menu + Roundtable Hold hub."""
    names = {r.name for r in mw.get_regions() if r.player == player}
    names.discard("Menu")
    names.discard("Roundtable Hold")
    return names


def _lock_region_names(mw, player):
    """Regions whose Lock item this world created (== the kept set from the item side). Looks across
    itempool + precollected + placed, since progression_surface pre-places Locks during pre_fill."""
    items = [i for i in mw.itempool if i.player == player]
    items += list(mw.precollected_items[player])
    items += [loc.item for loc in mw.get_locations(player)
              if loc.item is not None and loc.item.player == player]
    return {i.name[:-len(" Lock")] for i in items if i.name.endswith(" Lock")}


class DLCDefaultOn(WorldTestBase):
    """Default: Enable DLC on, DLC Only off, num_regions 0 -> full Shattering, all regions kept."""
    game = GAME
    options = {}

    def test_all_regions_kept_including_dlc(self):
        kept = _lock_region_names(self.multiworld, self.player)
        # full seed keeps every region, DLC included
        self.assertTrue(DLC <= kept, "default (DLC on) full seed must keep every DLC region")
        self.assertIn(GOAL_REGION, kept)

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))


class DLCDisabled(WorldTestBase):
    """Enable DLC off -> DLC regions sealed; base-game goal still kept; beatable."""
    game = GAME
    options = {"enable_dlc": False}

    def test_no_dlc_region_kept(self):
        kept = _lock_region_names(self.multiworld, self.player)
        self.assertEqual(kept & DLC, set(), "Enable DLC off must seal every DLC region")
        self.assertEqual(kept, set(base_regions()),
                         "Enable DLC off, full seed -> exactly the base-game regions")
        self.assertIn(GOAL_REGION, kept, "base-game goal region must remain kept")

    def test_no_dlc_region_instantiated(self):
        names = _kept_region_names(self.multiworld, self.player)
        self.assertEqual(names & DLC, set(), "no DLC region may be instantiated when DLC is off")

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))


class DLCOnlyMode(WorldTestBase):
    """DLC Only on -> only DLC regions eligible; base goal sealed; still beatable."""
    game = GAME
    options = {"dlc_only": True}

    def test_only_dlc_regions_kept(self):
        kept = _lock_region_names(self.multiworld, self.player)
        self.assertTrue(kept, "DLC Only full seed must keep at least one region")
        self.assertTrue(kept <= DLC, "DLC Only must keep ONLY DLC regions")
        self.assertEqual(kept, set(dlc_regions()),
                         "DLC Only full seed -> exactly the DLC regions")

    def test_base_goal_region_sealed(self):
        names = _kept_region_names(self.multiworld, self.player)
        self.assertNotIn(GOAL_REGION, names,
                         "base-game goal region must be sealed under DLC Only")
        # base-game regions are all sealed
        self.assertEqual(names & set(base_regions()), set())

    def test_beatable_without_base_goal(self):
        # goal collapses to "hold every kept (DLC) lock" -- get_all_state must satisfy it.
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state),
                        "DLC Only seed must be winnable with the base goal region sealed")


class DLCOnlyImpliesEnabled(WorldTestBase):
    """DLC Only on WITH Enable DLC off: DLC Only wins (implies enabled) -- DLC regions still kept."""
    game = GAME
    options = {"dlc_only": True, "enable_dlc": False}

    def test_dlc_only_overrides_disable(self):
        kept = _lock_region_names(self.multiworld, self.player)
        self.assertTrue(kept, "DLC Only must force the DLC in even if Enable DLC is off")
        self.assertEqual(kept, set(dlc_regions()))

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))


class DLCDisabledNumRegions3(WorldTestBase):
    """Enable DLC off + num_regions 3 spine -> 3 base-game spine regions + goal, no DLC, beatable."""
    game = GAME
    options = {"enable_dlc": False,
               "num_regions": 3, "num_regions_order": "spine"}

    def test_kept_is_base_only_and_counts(self):
        kept = _lock_region_names(self.multiworld, self.player)
        self.assertEqual(kept & DLC, set(), "no DLC region under Enable DLC off")
        self.assertIn(GOAL_REGION, kept, "goal region always kept")
        # first 3 base spine regions are Limgrave/Weeping/Stormveil (all base), + Leyndell + the
        # REGION_PARENT closure (the capital pulls Altus in -- it has no other way in).
        from worlds.eldenring.region_spine import parent_chain
        expected = {r for r in list(SPINE[:3]) + [GOAL_REGION]}
        for r in list(expected):
            expected.update(parent_chain(r))
        self.assertEqual(kept, expected)
        self.assertTrue(kept <= set(base_regions()))

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))


class DLCOnlyNumRegions3(WorldTestBase):
    """DLC Only + num_regions 3 spine -> exactly 3 DLC regions, no base, no goal forced, beatable."""
    game = GAME
    options = {"dlc_only": True,
               "num_regions": 3, "num_regions_order": "spine"}

    def test_exactly_three_dlc_regions(self):
        kept = _lock_region_names(self.multiworld, self.player)
        self.assertEqual(len(kept), 3, "num_regions=3 DLC Only -> exactly 3 kept (no goal appended)")
        self.assertTrue(kept <= DLC, "every kept region must be DLC")
        self.assertNotIn(GOAL_REGION, kept, "base goal not forced in under DLC Only")

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))


class DLCOnlyGreatRunesGoal(WorldTestBase):
    """DLC Only + great_runes goal: no Great Rune sits in a DLC region (they are base-game shardbearer
    drops), so the goal COLLAPSES to region_locks -- _resolve_required_runes shrinks the requirement
    to 0 rather than making the seed unbeatable. Winnability is guarded by test_beatable. (A standalone
    Great Runes goal under DLC Only -- placing runes in Land of Shadow -- is scoped out of v0.2.)"""
    game = GAME
    options = {
        "dlc_only": True,
        "item_shuffle": True,
        "ending_condition": "great_runes",
        "goal_great_runes": 2,
    }

    def test_runes_collapse_to_region_locks_under_dlc_only(self):
        # v0.2: no Great Rune region survives DLC Only, so the great_runes goal collapses -- the
        # requirement shrinks to 0 (region_locks-only) instead of becoming unwinnable. Winnability
        # itself is asserted by test_beatable below.
        world = self.multiworld.worlds[self.player]
        self.assertEqual(world._available_runes(), [],
                         "no Great Rune sits in a DLC region -> none available under DLC Only")
        self.assertEqual(len(world._required_runes()), 0,
                         "DLC Only collapses great_runes to region_locks (required shrinks to 0)")

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state),
                        "DLC Only great_runes seed must remain winnable")
