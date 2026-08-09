"""TIER-A: the client stars EXACTLY the locations progression can occupy. One set, not two lists.

WHY THIS FILE EXISTS
--------------------
There used to be two definitions of "an important check", and they disagreed:

    progression surface                       : Remembrance, Seedtree, Church, Boss, Fragment, Revered
    big-ticket          (bigTicketLocations)  : MajorBoss, Remembrance, GreatRune

Intersection: **Remembrance alone.** So the client's tracker starred MajorBoss and GreatRune checks --
locations `progression_surface` (frozen `strict`) FORBIDS this world's progression from ever reaching.
The tracker was pointing at the wrong checks by construction, and nothing caught it, because the two
lists had no contract with each other. It surfaced only when a human read a spoiler and asked why
killing Malenia paid out a Smithing Stone [4].

That is the same disease as the three-pass filler tail (see features/filler_budget): several
locally-correct mechanisms, no single owner, silently composing into nonsense.

Big-ticket is retired. There is ONE definition now -- the surface -- and the client is fed it directly
(`progressionSurfaceLocations`). This file makes the drift UNREPRESENTABLE rather than merely fixed:
the wire and the placement are asserted to be the same set, on real generated seeds.

Note what is deliberately NOT asserted: that locks land on major bosses. They do not, and that is
correct -- Alaric 2026-07-12: "the progression surface is correct, those are all valid." A lock on a
Golden Seed check is a fine lock. The bug was never where the locks went; it was the client claiming
they went somewhere else.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features import progression_surface as ps  # noqa: E402

GAME = "Elden Ring"
KEY = contract.PROGRESSION_SURFACE_LOCATIONS


def test_big_ticket_is_gone():
    """The retired concept must not creep back as a third list. If someone re-adds a second selection
    over the same tags, it will drift from the surface again -- that is not a hypothetical, it is what
    happened."""
    assert not hasattr(contract, "is_big_ticket"), (
        "is_big_ticket was renamed to has_class: it was never a concept, just 'tags intersect a "
        "selection' -- and the name let a SECOND selection masquerade as a second mechanism")
    assert not hasattr(contract, "BIG_TICKET_TYPES")
    assert "bigTicketLocations" not in contract.BY_NAME, (
        "the client must be fed the progression surface, not a separate 'important' list")


class SurfaceContract(WorldTestBase):
    game = GAME
    options = {"num_regions": 4}

    def test_wire_is_nonempty_and_is_this_world(self):
        sd = self.world.fill_slot_data()
        surface = sd[KEY]
        self.assertTrue(surface, "the client got an EMPTY star set -- the tracker would show nothing")
        own = {loc.address for loc in self.multiworld.get_locations(self.world.player)
               if loc.address is not None}
        stray = [i for i in surface if i not in own]
        self.assertFalse(stray[:5], f"the wire names locations that are not in this seed: {stray[:5]}")

    def test_every_confined_progression_sits_on_a_starred_location(self):
        """THE INVARIANT. Every restricted progression item this world CONFINED must be on a location
        the client was told to star. If this ever fails, the tracker is lying again -- which is
        precisely the failure that shipped, undetected, until a human read a spoiler.

        🛑 NARROWED 2026-08-09 for `region_locks_anywhere` (er-archipelago#491), which defaults to
        100 and therefore RELEASES every Lock into the normal multiworld fill. A released Lock can
        land anywhere -- that is the entire point of the option -- so asserting it sits on the
        surface would be asserting the feature does not work.

        The exemption is deliberately keyed on `world.gf_locks_released`, the list `apply()` actually
        drew, NOT on "is it a Lock". A Lock that was CONFINED must still obey the invariant, so a
        bug that released an item the option said to keep is still a failure here.

        Run at a PARTIAL release (50) on purpose. At the shipped default of 100 this seed confines
        nothing of its own at all -- every restricted item in it is a Lock -- so the invariant would
        pass while examining zero items, and the witness below would (correctly) fail. 50 is the
        setting where both halves of the option are live at once: some Locks exempt, some still
        owed to the surface."""
        from Fill import distribute_items_restrictive

        self.options = dict(self.options, region_locks_anywhere=50)
        self.world_setup(seed=22222)
        distribute_items_restrictive(self.multiworld)
        world = self.world
        surface = set(world.fill_slot_data()[KEY])
        self.assertTrue(surface)
        released = set(getattr(world, "gf_locks_released", []))

        offenders = []
        examined = 0
        for loc in self.multiworld.get_locations(world.player):
            it = loc.item
            if it is None or loc.address is None:
                continue
            if not ps.is_restricted_progression(it, world.player):
                continue
            if it.name in released:
                continue  # deliberately in the general pool; the surface never claimed it
            examined += 1
            if loc.address not in surface:
                offenders.append(f"{it.name} @ {loc.name} (ap {loc.address})")
        # WITNESS: at least one CONFINED item was actually looked at. Without this the invariant
        # passes for free the moment the release option starts exempting everything -- which is
        # exactly the state the default now puts it in.
        self.assertTrue(examined, "no confined progression to check -- this invariant proved nothing")
        self.assertFalse(
            offenders,
            "this world's own CONFINED progression landed on locations the client was NOT told to "
            "star -- the tracker and the fill disagree about where progression lives:\n  "
            + "\n  ".join(offenders[:8]))

    def test_with_the_locks_confined_the_original_invariant_still_holds_in_full(self):
        """The guarantee the test above was written for, preserved rather than weakened: set
        `region_locks_anywhere: 0` and EVERY restricted item -- Locks included -- is back on the
        surface. Without this, narrowing the invariant above would have quietly retired it."""
        from Fill import distribute_items_restrictive

        self.options = dict(self.options, region_locks_anywhere=0)
        self.world_setup(seed=22222)
        distribute_items_restrictive(self.multiworld)
        world = self.world
        surface = set(world.fill_slot_data()[KEY])
        self.assertEqual(getattr(world, "gf_locks_released", []), [],
                         "region_locks_anywhere=0 must release nothing")
        restricted = [loc for loc in self.multiworld.get_locations(world.player)
                      if loc.item is not None and loc.address is not None
                      and ps.is_restricted_progression(loc.item, world.player)]
        # WITNESS: this seed placed restricted progression at all.
        self.assertTrue(restricted, "no restricted progression placed -- nothing was proved")
        offenders = [f"{loc.item.name} @ {loc.name}"
                     for loc in restricted if loc.address not in surface]
        self.assertFalse(offenders, "with locks confined, nothing may sit off the surface:\n  "
                         + "\n  ".join(offenders[:8]))

    def test_the_surface_the_client_gets_is_the_surface_the_fill_used(self):
        """apply() (where locks go) and slot_data() (what the client stars) must resolve the SAME
        selection. They read it through one helper for exactly this reason; assert it, so a future
        refactor cannot quietly give them different answers."""
        from worlds.eldenring.location_tags import LOCATION_TAGS

        world = self.world
        classes = ps.selected_surface(ps._selection(world))
        # _world_barred_aps is the SAME per-world no-progression set both apply() and slot_data()
        # read (capital reconciler ON lifts the ERDTREE_BURN bar -- SPEC-capital-reconciler.md);
        # recomputing the surface here must go through it too, or this test would re-create the
        # very second-list drift it exists to forbid.
        placement_surface = ps.allowed_ap_ids(LOCATION_TAGS, classes,
                                              defaulted=ps._world_barred_aps(world))
        own = {loc.address for loc in self.multiworld.get_locations(world.player)
               if loc.address is not None}
        expected = {i for i in placement_surface if i in own}
        self.assertEqual(set(world.fill_slot_data()[KEY]), expected,
                         "the wire and the placement surface disagree -- two lists again")
