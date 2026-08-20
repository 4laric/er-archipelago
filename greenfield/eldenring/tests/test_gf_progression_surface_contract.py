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




def test_every_boss_check_is_reachable_by_a_class_narrower_than_Boss():
    """Alaric's ruling, 2026-08-16: the minidungeon bosses get a class of their own.

    Before it, 96 of the 267 `Boss` checks carried no sub-class at all -- catacomb, cave, tunnel,
    gaol and Divine Tower drops that a player could only reach by ticking `Boss`, which drags in
    every field and legacy boss with it. "Exclude the catacombs" was unexpressible, and the tree
    view makes the gap plain: a parent whose children do not add up.

    🛑 NOT asserted as "the residue is zero". 18 checks carry `Boss` and have no reward tile, so
    geography cannot place them and no honest class can claim them -- pretending otherwise would be
    a tag that means "we do not know". What IS asserted is that the residue is SMALL and that the
    named classes are disjoint from each other, so the tree's parent/child counts can be trusted.
    """
    from worlds.eldenring import contract
    from worlds.eldenring.location_tags import LOCATION_TAGS

    def tagged(t):
        return {ap for ap, tags in LOCATION_TAGS.items() if t in tags}

    boss = tagged("Boss")
    assert boss, "no Boss-tagged checks -- this test is measuring an empty world"
    # LegacyBoss absorbed into MajorBoss 2026-08-20. The law is about REACHABILITY BY A CLASS, so
    # membership is has_class (the surface predicate, alias included) -- raw-tag membership would
    # count the 22 legacy-only rows as unreachable residue when ticking MajorBoss reaches them.
    subs = {c: {ap for ap, tags in LOCATION_TAGS.items() if contract.has_class(tags, {c})}
            for c in ("MajorBoss", "FieldBoss", "MinorDungeonBoss")}
    for name, aps in subs.items():
        assert aps, f"{name} tags nothing"
        assert aps <= boss, f"{name} has {len(aps - boss)} check(s) outside Boss"
        assert name in contract.SURFACE_CLASSES, f"{name} is not selectable"

    covered = set().union(*subs.values())
    residue = boss - covered
    assert len(residue) < len(boss) * 0.10, (
        f"{len(residue)} of {len(boss)} Boss checks carry no sub-class ({len(residue)/len(boss):.0%}) "
        f"-- a player can only reach them by ticking Boss, which is what MinorDungeonBoss was added "
        f"to fix. Sample: {sorted(residue)[:5]}")

    # The four are WHERE the boss stands, so they cannot overlap -- the tree draws them as siblings
    # and a check in two of them would be counted twice under one parent.
    for a in subs:
        for b in subs:
            if a < b and a != "MajorBoss" and b != "MajorBoss":
                assert not (subs[a] & subs[b]), (
                    f"{a} and {b} share {len(subs[a] & subs[b])} check(s); geography classes must "
                    f"partition")


def test_the_minidungeon_class_is_not_named_after_a_region():
    """🛑 `MinorDungeonBoss`, never `Underground`. "Underground" is what a player calls Nokron,
    Nokstella, Siofra and the Ainsel river -- REGIONS, none of which this class contains. It holds
    catacombs, caves, tunnels, gaols and Divine Towers, which the sweep vocabulary already calls the
    minidungeons. One word for one thing, in both places a player meets it."""
    from worlds.eldenring import contract
    from worlds.eldenring.features.progression_surface import SURFACE_CLASS_LABELS

    assert "Underground" not in contract.SURFACE_CLASSES
    label, hint = SURFACE_CLASS_LABELS["MinorDungeonBoss"]
    assert "Minor dungeon" in label, label
    for region in ("Nokron", "Nokstella", "Siofra", "Ainsel"):
        assert region in hint, (
            f"the hint must say this class is NOT {region} -- that conflation is the reason it is "
            f"not called Underground")

def test_the_default_surface_admits_nothing_it_does_not_need():
    """#733. `Remembrance` and `GreatRune` sat in SURFACE_DEFAULT_CLASSES doing nothing at all.

    Both are STRICT SUBSETS of `MajorBoss`, so while that class is in the default set the two entries
    cannot admit a location of their own -- yet the wizard drew them as two live knobs beside the
    fifteen that are real, and a player has no way to tell a knob that does nothing from one that
    does.

    🛑 ASSERTED AS AN IDENTITY, NOT A MEMBERSHIP. `assert "Remembrance" not in DEFAULTS` would pass
    the day someone removes `MajorBoss` and makes the entry load-bearing again -- exactly backwards.
    What must stay true is that the shipped default and the default-plus-the-two select the SAME
    LOCATIONS; if that ever stops holding, the two belong back in the set and this test says so.
    """
    from worlds.eldenring import contract
    from worlds.eldenring.location_tags import LOCATION_TAGS

    defaults = set(contract.SURFACE_DEFAULT_CLASSES)
    with_both = defaults | {"Remembrance", "GreatRune"}

    def admitted(classes):
        return {ap for ap, tags in LOCATION_TAGS.items() if contract.has_class(tags, classes)}

    shipped, widened = admitted(defaults), admitted(with_both)
    assert shipped, "the default surface admits nothing -- this test is measuring an empty world"
    assert shipped == widened, (
        "adding Remembrance/GreatRune to the shipped default changes the surface by "
        f"{len(widened - shipped)} location(s): {sorted(widened - shipped)[:5]}. They are no longer "
        "redundant, so they belong back in SURFACE_DEFAULT_CLASSES (#733)."
    )


def test_both_retired_defaults_are_still_selectable():
    """The other half of #733's ruling, and the one that would break players.

    `OptionSet` raises on an unknown key, so a yaml naming `Remembrance` must still validate --
    every seed shared before today names it. `Options.Removed` is per-OPTION, not per-KEY, so there
    is no migration available: the keys have to stay.
    """
    from worlds.eldenring import contract

    for name in ("Remembrance", "GreatRune"):
        assert name in contract.SURFACE_CLASSES, (
            f"{name} left SURFACE_CLASSES -- every existing yaml that names it now fails to load, "
            "and OptionSet gives no migration path (#733)"
        )


def test_a_class_that_contains_another_is_the_reason_this_can_happen():
    """The general shape, so the next redundant default is caught by the rule.

    Containment among surface classes is what makes a default entry inert, and it is not visible
    from the class list -- only from the tags. Every strict subset of another DEFAULT class is dead
    weight in the default set by construction.
    """
    from worlds.eldenring import contract
    from worlds.eldenring.location_tags import LOCATION_TAGS

    sets = {c: {ap for ap, t in LOCATION_TAGS.items() if c in t}
            for c in contract.SURFACE_DEFAULT_CLASSES}
    sets = {c: v for c, v in sets.items() if v}
    # WITNESS: with an empty LOCATION_TAGS every class maps to an empty set, they are filtered out
    # above, and `inert` is empty for the wrong reason.
    assert len(sets) >= 5, (
        f"only {len(sets)} default surface class(es) match any location -- LOCATION_TAGS is empty or "
        "the class names moved, and the containment check below is measuring nothing")
    inert = [(a, b) for a, av in sets.items() for b, bv in sets.items()
             if a != b and av <= bv]
    assert not inert, (
        "these default surface classes are subsets of another default class, so they admit nothing "
        f"and read as live knobs: {inert}. Drop them from SURFACE_DEFAULT_CLASSES (keep them in "
        "SURFACE_CLASSES) the way #733 did for Remembrance/GreatRune."
    )

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

        🛑 NARROWED 2026-08-09 for `progression_bias` (er-archipelago#491), which defaults to
        0 and therefore RELEASES every Lock into the normal multiworld fill. A released Lock can
        land anywhere -- that is the entire point of the option -- so asserting it sits on the
        surface would be asserting the feature does not work.

        The exemption is deliberately keyed on `world.gf_locks_released`, the list `apply()` actually
        drew, NOT on "is it a Lock". A Lock that was CONFINED must still obey the invariant, so a
        bug that released an item the option said to keep is still a failure here.

        Run at a PARTIAL bias (50) on purpose. At the shipped default of 0 this seed confines
        nothing of its own at all -- every restricted item in it is a Lock -- so the invariant would
        pass while examining zero items, and the witness below would (correctly) fail. 50 is the
        setting where both halves of the option are live at once: some Locks exempt, some still
        owed to the surface."""
        from Fill import distribute_items_restrictive

        self.options = dict(self.options, progression_bias=50)
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
        `progression_bias: 100` and EVERY restricted item -- Locks included -- is back on the
        surface. Without this, narrowing the invariant above would have quietly retired it."""
        from Fill import distribute_items_restrictive

        self.options = dict(self.options, progression_bias=100)
        self.world_setup(seed=22222)
        distribute_items_restrictive(self.multiworld)
        world = self.world
        surface = set(world.fill_slot_data()[KEY])
        self.assertEqual(getattr(world, "gf_locks_released", []), [],
                         "progression_bias=100 must release nothing")
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
        # 🛑 THROUGH THE CHOKEPOINT, not allowed_ap_ids. `surface_ap_ids` is the tagged half PLUS
        # the derived half (SweepSlot), and calling the tag half alone here is precisely the
        # second-list drift this test forbids -- it caught exactly that when the derived half was
        # added, reporting ~50 ids the wire had and this recomputation did not.
        placement_surface = ps.surface_ap_ids(world, classes)
        own = {loc.address for loc in self.multiworld.get_locations(world.player)
               if loc.address is not None}
        expected = {i for i in placement_surface if i in own}
        self.assertEqual(set(world.fill_slot_data()[KEY]), expected,
                         "the wire and the placement surface disagree -- two lists again")
