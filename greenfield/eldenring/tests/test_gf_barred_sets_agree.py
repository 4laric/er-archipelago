"""The SURFACE's bar set and the ITEM_RULE's bar set must differ only where we decided they should.

Two sets answer "may this check hold progression?", and they are computed in different places:

    core._NO_PROGRESSION_APS                    -- what the item_rule fill actually obeys
    features/progression_surface._world_barred_aps(world)
                                                -- what the surface math believes

`_world_barred_aps`' docstring already promises they agree ("Mirrors core._add_locations' item_rule
carve-out; the two must agree or the surface would star checks the item_rule forbids"). Nothing
enforced it, and the promise has been broken three times:

  * 2026-07-28  MISSABLE -- missable_locations enforced its bar with an item_rule the surface never
                knew about. Mostly cosmetic, until Deeproot Depths' ONE surface member turned out to
                be the Fortissax reward: the surface said the region could host a Lock, the true
                count was zero, and regions_with_major_boss said the same thing off the same tags.
  * #724        SHOP_RELEASE_GATED -- 185 checks the surface counted as hostable that fill refused.
  * (this file) the absence of any gate at all, which is why both of the above were found by hand.

# 🛑 THE POINT IS NOT "THE TWO SETS MUST BE EQUAL". SOME DIVERGENCE IS DELIBERATE.

An earlier draft of this gate was specified as "a bar joining one set and not the other is a red".
That is too strong, and had it shipped it would have failed on SURFACE_EXCLUDE_APS and invited
someone to "fix" an asymmetry `gen_data.py` rules on in three separate places:

    🛑 AND DO NOT "FIX" IT BY MOVING IT TO _SURFACE_EXCLUDE_FLAGS. That looks equivalent and is
    not: SURFACE_EXCLUDE_APS is consumed by allowed_ap_ids (the surface SELECTION) but is absent
    from core._NO_PROGRESSION_APS, which is the item_rule fill actually obeys.

SURFACE_EXCLUDE is a DISPLAY lever, kept distinct from a FILL lever on purpose. #252's stranding
happened because 16 isolated-merchant checks were put in it as though it were a fill bar; the fix
was FLAG_REGION_OVERRIDE, so the REGION gates them. Binding it into _NO_PROGRESSION_APS would
collapse the distinction those rulings protect.

So this file pins WHICH asymmetries are intentional rather than forbidding all of them:

  1. `_world_barred_aps` == `_NO_PROGRESSION_APS`, minus `collapsed_lift_aps`, plus
     `missable_barred_aps` -- both world-conditional, both documented, and nothing else;
  2. `SURFACE_EXCLUDE_APS` is in NEITHER set, deliberately, and IS applied by the selection
     chokepoint -- asserted, so the next reader does not re-derive it as a bug;
  3. a spy, because an equality between two sets that happen to be identical proves nothing.

A fifth bar joining one set and not the other now has to come here and say which kind it is.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract as _contract          # noqa: E402
from worlds.eldenring import core as _core                  # noqa: E402
from worlds.eldenring.features.progression_surface import (  # noqa: E402
    _world_barred_aps, allowed_ap_ids, collapsed_lift_aps, missable_barred_aps)
from worlds.eldenring.location_tags import (                # noqa: E402
    DEFAULTED_REGION_APS, ERDTREE_BURN_APS, LOCATION_TAGS, SHOP_RELEASE_GATED_APS,
    SURFACE_EXCLUDE_APS)
from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS  # noqa: E402

GAME = "Elden Ring"


class BarredSetsAgree(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "num_regions": 4}

    # ---- 1. the relation -------------------------------------------------------------------------

    def _expected(self, world, no_progression):
        """`_NO_PROGRESSION_APS` re-expressed as the surface should see it.

        Subtracting the lift from the WHOLE union (rather than from DEFAULTED alone, as the
        production code does) is safe *and* is the assertion: `collapsed_lift_aps` returns
        `ids - ERDTREE_BURN - SHOP_RELEASE_GATED`, so it cannot reach a row another cause still
        bars. If someone widens the lift to include one, these two stop being equal and this test
        is what says so."""
        return (frozenset(no_progression) - collapsed_lift_aps(world)) | missable_barred_aps(world)

    def _assert_relation(self, armed):
        world = self.world
        prior = getattr(world, "gf_capital_reconciler", False)
        try:
            world.gf_capital_reconciler = armed
            base = frozenset(_core._NO_PROGRESSION_APS)
            if armed:
                # Armed, the client restores m11_00, so core drops the burn strand from the
                # item_rule and `_world_barred_aps` takes its early return. Both sides move, and
                # this is the one conditional they already share -- the easiest place to drift.
                base = base - frozenset(ERDTREE_BURN_APS)
            got = frozenset(_world_barred_aps(world))
            self.assertEqual(self._expected(world, base), got,
                             self._diff_message(self._expected(world, base), got))
            if armed:
                # ⚠️ BURN-MEMBERSHIP ALONE, not the whole set -- the same shape as the
                # SURFACE_EXCLUDE assertion below, and it caught me the same way. 9 of the burn
                # rows stay barred when armed because they are independently DEFAULTED / MISSABLE /
                # SHOP_RELEASE_GATED, which are different causes with their own levers. "The burn
                # set is disjoint from the bar set" is false and says something wrong about why;
                # "the burn cause stops binding" is the claim that holds.
                burn_only = (frozenset(ERDTREE_BURN_APS) - frozenset(DEFAULTED_REGION_APS)
                             - frozenset(SHOP_RELEASE_GATED_APS) - frozenset(MISSABLE_LOCATIONS))
                self.assertTrue(burn_only,
                                "every ERDTREE_BURN_APS row is barred for some other reason too, "
                                "so this assertion proves nothing about the reconciler")
                self.assertFalse(got & burn_only,
                                 "armed, the client restores m11_00 -- the burn strand must stop "
                                 "binding on the surface side, as it does in core.")
        finally:
            world.gf_capital_reconciler = prior

    def test_reconciler_off__differs_only_by_the_documented_carveouts(self):
        """🛑 SETS the flag rather than assuming it. This class's seed arms the reconciler by
        DEFAULT, so an earlier draft that asserted `gf_capital_reconciler is False` as a
        precondition failed immediately -- and would have silently tested only one branch had the
        default gone the other way."""
        self._assert_relation(armed=False)

    def test_reconciler_armed__erdtree_burn_lifts_on_BOTH_sides(self):
        self._assert_relation(armed=True)

    # ---- 2. the asymmetry that is SUPPOSED to be there -------------------------------------------

    def test_surface_exclude_alone_never_bars_and_that_is_deliberate(self):
        """🛑 NOT A BUG. Read the module docstring before "fixing" this.

        SURFACE_EXCLUDE_APS trims the ADVERTISED surface and does not, BY ITSELF, bar a check from
        carrying progression -- fill stays free. That is the documented design (gen_data.py, three
        rulings, #252).

        ⚠️ ASSERTED ON THE SURFACE-EXCLUDE-ONLY MEMBERS, not on the whole set. Of the 18, two
        (7773913, 7900113) ARE in the surface's bar set -- because they are independently MISSABLE,
        which is a different cause with its own lever. Asserting the whole set is disjoint fails on
        those two and says something false about why. The claim that actually holds, and the one
        worth pinning, is: surface-exclusion ALONE never bars."""
        sx = frozenset(SURFACE_EXCLUDE_APS)
        self.assertTrue(sx, "SURFACE_EXCLUDE_APS is empty -- this test has lost its subject")
        others = (frozenset(DEFAULTED_REGION_APS) | frozenset(ERDTREE_BURN_APS)
                  | frozenset(SHOP_RELEASE_GATED_APS) | frozenset(MISSABLE_LOCATIONS))
        only_sx = sx - others
        self.assertTrue(only_sx,
                        "every SURFACE_EXCLUDE_APS member is also barred for some other reason, so "
                        "this test proves nothing about surface-exclusion itself")
        self.assertFalse(only_sx & frozenset(_core._NO_PROGRESSION_APS),
                         "SURFACE_EXCLUDE_APS has been bound into the item_rule. If that is "
                         "deliberate, gen_data.py's three rulings against it need retiring FIRST "
                         "(and #252's stranding re-reasoned); if not, revert it.")
        self.assertFalse(only_sx & frozenset(_world_barred_aps(self.world)),
                         "surface-exclusion alone has started barring progression; it belongs in "
                         "allowed_ap_ids/sweep_slot_aps, which are unconditional and selection-only.")
        # ...and it IS applied where it belongs. Non-vacuous: assert it had something to remove.
        on_surface = {ap for ap, tags in LOCATION_TAGS.items()
                      if _contract.has_class(tags, set(_contract.SURFACE_CLASSES))}
        self.assertTrue(sx & on_surface,
                        "no SURFACE_EXCLUDE_APS member carries a surface class, so the selection "
                        "assertion below would pass vacuously")
        selected = allowed_ap_ids(LOCATION_TAGS, set(_contract.SURFACE_CLASSES),
                                  defaulted=frozenset())
        self.assertFalse(set(selected) & sx,
                         "allowed_ap_ids stopped applying SURFACE_EXCLUDE_APS -- the display lever "
                         "is now doing nothing, and nothing else applies it.")

    # ---- 3. the spy --------------------------------------------------------------------------

    def test_the_carveouts_actually_move_something(self):
        """An equality between two sets that are already identical proves nothing.

        If both carve-outs are empty in this seed, the relation above degenerates to
        `_world_barred_aps == _NO_PROGRESSION_APS` and would keep passing after someone deleted
        them. So require the pair to be load-bearing HERE, in the seed this class generates."""
        world = self.world
        lift, missable = collapsed_lift_aps(world), missable_barred_aps(world)
        self.assertTrue(lift or missable,
                        "both carve-outs are empty in this seed -- the relation is vacuous. Change "
                        "the options until one bites rather than deleting this test.")
        self.assertNotEqual(frozenset(_core._NO_PROGRESSION_APS), frozenset(_world_barred_aps(world)),
                            "the two sets are IDENTICAL, so the carve-outs in the relation are "
                            "untested. See above.")

    # ---- helper ------------------------------------------------------------------------------

    @staticmethod
    def _diff_message(want, got):
        only_rule, only_surface = sorted(want - got)[:8], sorted(got - want)[:8]
        return (
            "the surface's bar set and the item_rule's have diverged beyond the documented "
            "carve-outs (collapsed_lift_aps subtracted, missable_barred_aps added).\n"
            f"  barred by the item_rule, NOT by the surface ({len(want - got)}): {only_rule}\n"
            "    -> the surface will advertise/star checks fill refuses; surface_confidence.tsv "
            "and regions_with_major_boss both over-count.\n"
            f"  barred by the surface, NOT by the item_rule ({len(got - want)}): {only_surface}\n"
            "    -> fill may place progression somewhere the surface promised it would not.\n"
            "If you added a bar: put UNCONDITIONAL ones in allowed_ap_ids (the SURFACE_EXCLUDE_APS "
            "pattern) and WORLD-CONDITIONAL ones in both _world_barred_aps and "
            "core._NO_PROGRESSION_APS, then say which here.")
