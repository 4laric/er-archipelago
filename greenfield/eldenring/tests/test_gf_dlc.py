"""DLC region-scope tests -- EnableDLC / DLCOnly toggles (WorldTestBase, needs AP).

Covers the DLC filter wired into core.py + region_spine.py:
  * default (Enable DLC on, DLC Only off): every region eligible -- kept set unchanged, beatable.
  * Enable DLC off: DLC regions are sealed -- none appear in kept; base-game goal (Leyndell) still
    kept; seed beatable.
  * DLC Only on: ONLY DLC regions eligible -- every kept region is a DLC region, the base-game goal
    region is NOT kept, yet the seed is still beatable (goal = hold every kept lock).
  * combined with num_regions=3: each mode keeps N-from-its-pool + the parent closure and stays
    beatable and filter-respecting. WHICH regions is a per-seed draw since 2026-08-05, so these
    assert the pool boundary, never the membership. The "+goal" term this bullet used to name is
    gone as of SPEC-ashen-capital-lock (2026-08-06): nothing is force-kept for the goal any more.
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
    GOAL_REGION, DLC_REGIONS, base_regions, dlc_regions,
)
from worlds.eldenring.features.goal_locations import DLC_TERMINUS_REGION  # noqa: E402
from worlds.eldenring.core import GREAT_RUNES  # noqa: E402
from worlds.eldenring.data import FINALE_REGION  # noqa: E402
from ._util import assert_goal_reachable  # noqa: E402

GAME = "Elden Ring"
DLC = set(DLC_REGIONS)

# ⭐ "<R> Lock exists" STOPPED meaning "R was kept" on 2026-08-06 (SPEC-ashen-capital-lock), and
# STARTED MEANING IT AGAIN on 2026-08-16 (#768). For those ten days the Erdtree burn was a
# synthetic progression item, `Ashen Capital Lock`, minted on every seed with the base game in
# play, so the lock-side view of a seed was `kept | {FINALE_REGION}` and these tests subtracted
# that ONE name by hand before asserting their equalities.
#
# #768 withholds that Lock from the pool entirely -- the client grants the goal region once every
# other goal item is held (client#245) -- so the lock-side view is plain `kept` again and the
# hand-subtraction is gone. The equalities below stay EXACT rather than becoming subset tests: a
# stray lock, in either direction, still has to be noticed. What the subtraction used to protect
# ("this seed has a goal it can finish") is now `assert_goal_reachable`, which checks the goal
# region's entrance requirement is satisfiable instead of checking one item exists.


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
    options = {"num_regions": 0}

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
    options = {"num_regions": 0, "enable_dlc": False}

    def test_no_dlc_region_kept(self):
        locks = _lock_region_names(self.multiworld, self.player)
        kept = locks   # see the FINALE_REGION note at the top of this file
        self.assertEqual(kept & DLC, set(), "Enable DLC off must seal every DLC region")
        self.assertEqual(kept, set(base_regions()),
                         "Enable DLC off, full seed -> exactly the base-game regions")
        assert_goal_reachable(self, label="enable_dlc off, full seed")
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
    options = {"num_regions": 0, "dlc_only": True}

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
    options = {"num_regions": 0, "dlc_only": True, "enable_dlc": False}

    def test_dlc_only_overrides_disable(self):
        kept = _lock_region_names(self.multiworld, self.player)
        self.assertTrue(kept, "DLC Only must force the DLC in even if Enable DLC is off")
        self.assertEqual(kept, set(dlc_regions()))

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))


class DLCDisabledNumRegions3(WorldTestBase):
    """Enable DLC off + num_regions 3 -> 3 base-game regions + goal + closure, no DLC, beatable."""
    game = GAME
    options = {"enable_dlc": False, "num_regions": 3}

    def test_kept_is_base_only_and_counts(self):
        from worlds.eldenring.region_spine import parent_chain
        locks = _lock_region_names(self.multiworld, self.player)
        kept = locks   # see the FINALE_REGION note at the top of this file
        # SCOPING is this test's claim, and scoping is unaffected by the draw becoming random
        # (2026-08-05). It used to also assert WHICH three regions -- first-3 of SPINE -- which was
        # never what "Enable DLC off" is about, and is now unassertable.
        self.assertEqual(kept & DLC, set(), "no DLC region under Enable DLC off")
        self.assertTrue(kept <= set(base_regions()),
                        "draw escaped the base pool: %s" % sorted(kept - set(base_regions())))
        # WAS `assertIn(GOAL_REGION, kept)` -- "goal region always kept". That held only because
        # compute_kept force-kept GOAL_REGION under `auto`, so the goal DERIVATION (which reads the
        # kept set) was guaranteed a terminus. SPEC-ashen-capital-lock deleted that force-keep:
        # `auto` now resolves to the Elden Beast on every base-game seed and the Ashen Capital is
        # reached from the HUB behind its own lock, not by being kept. The protection is the same
        # one -- "this seed has a goal it can actually finish" -- restated at its new carrier.
        assert_goal_reachable(self, label="enable_dlc off, num_regions 3")
        # The COUNT survives identity removal: 3 drawn, plus the parent closure of whatever was
        # drawn. (It used to read "+ the goal" too; that term went with the force-keep above, and
        # the floor is unchanged because the draw itself was never the term that moved.)
        self.assertGreaterEqual(len(kept), 3, "kept fewer regions than num_regions asked for")
        for r in kept:
            for anc in parent_chain(r):
                self.assertIn(anc, kept, "kept child %s without ancestor %s" % (r, anc))

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))


class DLCOnlyNumRegions3(WorldTestBase):
    """DLC Only + num_regions 3 -> 3 DRAWN DLC regions plus the terminus, no base, beatable.

    ⭐ RE-PREMISED 2026-08-09, and it is a premise change, not a number change. This asserted
    "exactly 3 kept (no goal appended)" and that was right while `dlc_only` force-kept nothing: the
    DLC had no guaranteed ending, so a draw of 3 was a seed of 3. features/goal_locations tier 0b
    force-keeps Enir Ilim on every dlc_only seed -- the mirror of the guarantee the Ashen Capital
    gives the base game by not being rollable -- so the shape is now 3 drawn + 1 forced.

    The thing worth asserting did not change: `num_regions` is a DRAW SIZE (#409), the draw is 3,
    and nothing BASE creeps in. So the count is checked as "3 drawn, and the only addition is the
    terminus", which fails if a second region ever appears from somewhere unexplained.
    """
    game = GAME
    options = {"dlc_only": True, "num_regions": 3}

    def test_three_drawn_dlc_regions_plus_the_terminus(self):
        kept = _lock_region_names(self.multiworld, self.player)
        self.assertIn(DLC_TERMINUS_REGION, kept,
                      "dlc_only must force-keep the terminus, or the run has no guaranteed ending")
        drawn = kept - {DLC_TERMINUS_REGION}
        self.assertEqual(len(drawn), 3,
                         "num_regions=3 is a DRAW SIZE: 3 drawn + the forced terminus, nothing else")
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
    options = {"num_regions": 0, 
        "dlc_only": True,
        "item_shuffle": True,
        "ending_condition": "great_runes",
        "goal_great_runes": 2,
    }

    def test_great_runes_goal_survives_dlc_only(self):
        """REPLACES test_runes_collapse_to_region_locks_under_dlc_only (2026-08-16, #764).

        The old test asserted the collapse: no Great Rune boss stands in the Land of Shadow, so
        `_available_runes()` was empty under DLC Only and the requirement clamped to 0, turning a
        great_runes goal into a region_locks one. That was the honest behaviour while the pool held
        only the runes the draw kept.

        All seven are now injected into every seed (`features/great_runes`), so the supply no longer
        depends on which demigods are in the draw and a DLC-only seed can have a real rune goal --
        the runes arrive from the multiworld and from DLC checks. Alaric ruled to let it change
        rather than exempt DLC Only, because an invariant with one exception is the kind that rots.

        Kept as a NAMED test rather than deleted: the collapse was documented behaviour in the
        DLCOnly docstring and in the wizard's warning panel, so a future reader needs to find out
        here that it went away on purpose."""
        world = self.multiworld.worlds[self.player]
        self.assertEqual(len(world._available_runes()), 7,
                         "all seven Great Runes are in the pool, DLC Only included (#764)")
        want = int(world.options.goal_great_runes.value)
        self.assertEqual(len(world._required_runes()), want,
                         "the requirement is the number the player asked for -- no clamp, because "
                         "the supply no longer depends on the draw")

    def test_beatable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state),
                        "DLC Only great_runes seed must remain winnable")
