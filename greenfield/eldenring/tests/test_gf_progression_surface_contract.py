"""TIER-A: the client stars EXACTLY the locations progression can occupy. One set, not two lists.

WHY THIS FILE EXISTS
--------------------
There used to be two definitions of "an important check", and they disagreed:

    progression surface (important_locations) : Remembrance, Seedtree, Church, Boss, Fragment, Revered
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
    options = {"num_regions": 4, "num_regions_order": "rolled"}

    def test_wire_is_nonempty_and_is_this_world(self):
        sd = self.world.fill_slot_data()
        surface = sd[KEY]
        self.assertTrue(surface, "the client got an EMPTY star set -- the tracker would show nothing")
        own = {loc.address for loc in self.multiworld.get_locations(self.world.player)
               if loc.address is not None}
        stray = [i for i in surface if i not in own]
        self.assertFalse(stray[:5], f"the wire names locations that are not in this seed: {stray[:5]}")

    def test_every_placed_progression_sits_on_a_starred_location(self):
        """THE INVARIANT. Every region Lock / required rune this world placed must be on a location the
        client was told to star. If this ever fails, the tracker is lying again -- which is precisely
        the failure that shipped, undetected, until a human read a spoiler."""
        from Fill import distribute_items_restrictive

        self.world_setup(seed=22222)
        distribute_items_restrictive(self.multiworld)
        world = self.world
        surface = set(world.fill_slot_data()[KEY])
        self.assertTrue(surface)

        offenders = []
        for loc in self.multiworld.get_locations(world.player):
            it = loc.item
            if it is None or loc.address is None:
                continue
            if not ps.is_restricted_progression(it, world.player):
                continue
            if loc.address not in surface:
                offenders.append(f"{it.name} @ {loc.name} (ap {loc.address})")
        self.assertFalse(
            offenders,
            "this world's own progression landed on locations the client was NOT told to star -- the "
            "tracker and the fill disagree about where progression lives:\n  "
            + "\n  ".join(offenders[:8]))

    def test_the_surface_the_client_gets_is_the_surface_the_fill_used(self):
        """apply() (where locks go) and slot_data() (what the client stars) must resolve the SAME
        selection. They read it through one helper for exactly this reason; assert it, so a future
        refactor cannot quietly give them different answers."""
        from worlds.eldenring.location_tags import LOCATION_TAGS

        world = self.world
        classes = ps.selected_surface(ps._selection(world))
        placement_surface = ps.allowed_ap_ids(LOCATION_TAGS, classes)
        own = {loc.address for loc in self.multiworld.get_locations(world.player)
               if loc.address is not None}
        expected = {i for i in placement_surface if i in own}
        self.assertEqual(set(world.fill_slot_data()[KEY]), expected,
                         "the wire and the placement surface disagree -- two lists again")
