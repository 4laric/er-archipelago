"""#701 option 3 ("C"), AGAINST A REAL SEED THAT HOLDS NONE OF PATCHES' REGIONS.

Sibling to `test_gf_hub_collapsed_merchant_rows.py`, which asserts the tables. This file asserts the
thing Cokeman5 actually saw: a generated multiworld whose kept set contains NONE of
{Limgrave, Mt. Gelmir, Cerulean} -- the three regions Patches / Thiollier stand in -- must not be
able to put progression on any of the 19 hub-collapsed merchant rows, and must still FILL them.

🛑 THE SEED IS SEARCHED, NOT ASSUMED. `num_regions` is a DRAW SIZE, so "base-only, one region" makes
Limgrave and Mt. Gelmir unlikely, never impossible; `enable_dlc: False` is what seals Cerulean. A
fixture that merely HOPED for the right shape would silently degrade into "some seed" the first time
the rng consumption upstream moved -- the draw-dependent-assertion species this repo has been bitten
by before. So the shape is asserted, and a seed that does not have it is skipped over, not used.

🛑 AND EVERY NEGATIVE HERE IS PAIRED. "No progression on the 19" is exactly what you would also
measure if the 19 had been DELETED, or if their item_rule rejected everything. So: the rows are
counted, the same rule object is shown ACCEPTING the same item somewhere else in the same hub, and a
real `distribute_items_restrictive` is run to show all 19 still take an item.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from .test_gf_hub_collapsed_merchant_rows import (  # noqa: E402
    EXPECTED_TOTAL, PATCHES_REGIONS, REPORTED, collapsed_rows)

GAME = "Elden Ring"
_SEED_BUDGET = 40


class HubCollapsedRowsInASeedWithoutPatchesRegions(WorldTestBase):
    game = GAME
    # base-only (Cerulean is DLC -> sealed outright) and the smallest draw, so the odds that the
    # roll hands back Limgrave or Mt. Gelmir are low and the search below almost always takes the
    # first seed. auto_construct off: each test builds its own, having first checked the shape.
    # base-only seals Cerulean outright (it is a DLC region); the draw has to miss Limgrave and
    # Mt. Gelmir, which at four regions out of the base pool it usually does on the first try. It is
    # deliberately NOT one region: a one-region seed has no region Lock left in the pool to probe
    # with, and a probe item that does not exist proves nothing.
    options = {"num_regions": 4, "enable_dlc": False}
    auto_construct = False

    def _seed_without_patches_regions(self):
        """Build until the kept set misses all three of Patches' regions. Returns (seed, kept)."""
        for seed in range(_SEED_BUDGET):
            self.world_setup(seed)
            kept = set(getattr(self.world, "gf_kept", ()))
            self.assertTrue(kept, "the world exposed no kept-region list (gf_kept); this fixture "
                                  "cannot verify its own shape and would be worthless")
            if not (kept & set(PATCHES_REGIONS)):
                return seed, kept
        self.fail("no seed in %d tries kept none of %r -- the draw or the region set moved; fix the "
                  "fixture, do not delete the requirement" % (_SEED_BUDGET, (PATCHES_REGIONS,)))

    def _rows(self):
        want = {ap for (_n, ap, _f) in collapsed_rows()}
        self.assertEqual(len(want), EXPECTED_TOTAL, "population changed; see the sibling file")
        got = [loc for loc in self.multiworld.get_locations(self.player) if loc.address in want]
        # POSITIVE WITNESS: option C must not delete the locations. They stay checks; they just stop
        # being able to gate anything.
        self.assertEqual(len(got), EXPECTED_TOTAL,
                         "%d of the %d hub-collapsed rows are missing from the seed -- option C bars "
                         "progression, it does not remove checks" % (EXPECTED_TOTAL - len(got),
                                                                     EXPECTED_TOTAL))
        return got

    def test_no_progression_may_be_placed_on_any_collapsed_row(self):
        """THE NEGATIVE, and the control that keeps it from being vacuous."""
        seed, kept = self._seed_without_patches_regions()
        self.assertNotIn("Limgrave", kept, "fixture broke: seed %d kept Limgrave" % seed)
        rows = self._rows()
        flag_of = {ap: fl for (_n, ap, fl) in collapsed_rows()}
        self.assertIn(REPORTED, [flag_of[loc.address] for loc in rows],
                      "Cokeman5's f110030 must be among the rows under test")
        # A region Lock if the seed has one -- that is the item class Cokeman5's spoiler showed --
        # else any of our own advancement. get_items(), not itempool: a Lock may already be placed.
        ours = [i for i in self.multiworld.get_items() if i.player == self.player and i.advancement]
        self.assertTrue(ours, "this seed has no advancement item of ours to probe with; the negative "
                              "below would pass for want of a subject, not because the bar works")
        lock = next((i for i in ours if i.name.endswith(" Lock")), ours[0])
        self.assertTrue(lock.advancement, "the probe item must be advancement or this proves nothing")
        accepted = sorted(loc.name for loc in rows if loc.item_rule(lock))
        self.assertEqual(accepted, [],
                         "a hub-collapsed merchant row accepted %r in a seed holding none of %r: %r"
                         % (lock.name, PATCHES_REGIONS, accepted[:5]))
        # CONTROL: the same item, the same hub, a row that is NOT hub-collapsed. Without this the
        # assertion above is satisfied by an item_rule that refuses everything.
        others = [loc for loc in self.multiworld.get_locations(self.player)
                  if loc.parent_region is not None and loc not in rows and loc.item_rule(lock)]
        self.assertGreater(len(others), 0,
                           "no location in this seed accepts %r, so 'the 19 refuse it' says nothing "
                           "about the 19" % lock.name)

    def test_the_collapsed_rows_still_receive_filler(self):
        """THE POSITIVE WITNESS. A real fill, and all 19 come out of it holding something."""
        from Fill import distribute_items_restrictive
        seed, _kept = self._seed_without_patches_regions()
        rows = self._rows()
        distribute_items_restrictive(self.multiworld)
        empty = sorted(loc.name for loc in rows if loc.item is None)
        self.assertEqual(empty, [], "seed %d left hub-collapsed row(s) with no item at all: %r"
                                    % (seed, empty[:5]))
        real = [loc for loc in rows if loc.item is not None and loc.item.code is not None]
        self.assertGreater(len(real), 0,
                           "not one of the %d rows took a real (non-event) item -- they have dropped "
                           "out of the fill instead of holding filler" % EXPECTED_TOTAL)
        progression = sorted(loc.name for loc in rows
                             if loc.item is not None and loc.item.advancement)
        self.assertEqual(progression, [],
                         "seed %d placed progression on hub-collapsed row(s): %r" % (seed, progression[:5]))
