"""features/catacomb_doors -- the boss-door opener.

The table is 18 datamined integers, so the tests that matter are the ones a typo would survive:
that the ids are in the STATE-flag band and not the ObjAct or asset band next door, that the four
non-lever doors stay excluded, and that the flags actually reach the wire on the TAIL of
startGraces rather than displacing its sentinel head.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.features import catacomb_doors as cd  # noqa: E402
from worlds.eldenring import contract  # noqa: E402

GAME = "Elden Ring"


# ---- the table, checked without a world ------------------------------------------------------

def test_the_table_is_the_state_flag_band_not_the_objact_band():
    """🛑 THE TYPO THIS FILE EXISTS FOR. Three id bands are live at once and differ by one digit:
    asset 30001540, state flag 30000540, ObjAct flag 30003541. Writing the ObjAct flag would be
    silently wrong -- it is the ObjAct subsystem's own space, only readable via ObjActEventFlag().
    Every entry must have 0 as its 5th digit."""
    assert cd.LEVER_DOORS, "the door table is empty -- every assertion below would pass vacuously"
    # Scoped to LEVER_DOORS on purpose. The m30/m35 5th-digit rule is a catacombs convention and
    # says nothing about the m12 altars, which have their own aggregate/per-urn split -- asserting
    # it over both tables would be a coincidence dressed as an invariant.
    for tile, flag in cd.LEVER_DOORS:
        digit = (flag // 1000) % 10
        assert digit == 0, (
            f"{tile}: {flag} has 5th digit {digit}. 0 = the door STATE flag (what we must set), "
            f"1 = the door/lever ASSET entity, 3 = the ObjAct event flag. Only 0 is writable here.")


def test_the_table_covers_eighteen_distinct_lever_tiles():
    tiles = [t for t, _ in cd.LEVER_DOORS]
    flags = [f for _, f in cd.LEVER_DOORS]
    assert len(cd.LEVER_DOORS) == 18, (
        f"expected the 18 lever dungeons, got {len(cd.LEVER_DOORS)}. If FromSoft added a minor "
        f"dungeon the module docstring has the one-liner that re-derives the table.")
    assert len(set(tiles)) == len(tiles), "a tile appears twice"
    assert len(set(flags)) == len(flags), "a flag appears twice"


def test_the_four_non_lever_doors_are_excluded():
    """Two open on a mini-boss's DEATH and two have no lever at all. The option promises to pull
    levers; forcing the first pair would skip a fight, which is a different feature and a different
    conversation. NOT_LEVERS carries the reason per id so this stays a fact rather than a comment."""
    forced = {f for _, f in cd.LEVER_DOORS}
    assert forced, "the forced set is empty -- every exclusion below would hold vacuously"
    assert len(cd.NOT_LEVERS) == 4
    for flag, why in cd.NOT_LEVERS.items():
        assert flag not in forced, f"{flag} must stay excluded: {why}"


def test_doors_to_force_fails_closed_and_can_open():
    """Both arms, in one test, because the OFF arm alone is a witnessless empty assertion -- it
    would pass just as happily if `doors_to_force` were `return []`.

    The absent-option arm matters on its own account: `getattr(world.options, ..., None)` reading as
    OFF is the shape that made progression_surface_mode's retirement dangerous, where absent silently
    meant "disarmed". Here fail-closed is the CORRECT reading, and this pins it."""
    def _world(**opts):
        return type("W", (), {"options": type("O", (), {
            k: type("V", (), {"value": v})() for k, v in opts.items()})()})()

    # the witness: the ON arm returns the whole table, so the OFF arm below is a real zero
    on = cd.doors_to_force(_world(open_boss_doors=1))
    expected = [f for _, f in cd.LEVER_DOORS] + [f for _, f in cd.ANCESTOR_ALTARS]
    assert on == expected, "the ON arm must force every lever door and both ancestor altars"
    assert len(on) == 20

    assert cd.doors_to_force(_world(open_boss_doors=0)) == [], "the toggle must gate it"
    assert cd.doors_to_force(_world()) == [], "an ABSENT option must read as OFF -- fail closed"


# ---- the wire --------------------------------------------------------------------------------

class DoorsOff(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "open_boss_doors": False}

    def test_no_door_flags_on_the_wire(self):
        graces = self.world.fill_slot_data()[contract.START_GRACES]
        doors = {f for _, f in cd.LEVER_DOORS}
        # WITNESS BOTH SIDES. An empty intersection is what a working option looks like AND what a
        # dead wire looks like; without these two the assertion below would survive startGraces
        # going missing or the table emptying.
        assert graces, "startGraces is empty -- the assertion below would pass for the wrong reason"
        assert doors, "the door table is empty -- likewise"
        assert not (set(graces) & doors), "off must put no door flag in startGraces"


class DoorsOn(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "open_boss_doors": True}

    def test_every_door_and_altar_reaches_the_wire(self):
        graces = self.world.fill_slot_data()[contract.START_GRACES]
        # WITNESS: an empty `missing` is also what an empty TABLE produces, so say how many were
        # looked for. Both counts are pinned independently by the table tests.
        assert len(cd.LEVER_DOORS) == 18, "the table emptied -- `missing` would be empty for free"
        assert len(cd.ANCESTOR_ALTARS) == 2, "likewise the altars"
        want = [f for _, f in cd.LEVER_DOORS] + [f for _, f in cd.ANCESTOR_ALTARS]
        missing = [f for f in want if f not in graces]
        assert not missing, f"{len(missing)} flag(s) never reached startGraces: {missing[:3]}"

    def test_the_individual_urn_flags_are_NOT_set(self):
        """🛑 We set the two aggregates and nothing else. The counter's own already-done branch
        lights the altar from the aggregate at map load, so the eight-per-altar urn flags are
        redundant -- and they are a plausible future check family, which is exactly what a QoL
        toggle must not quietly pre-satisfy."""
        graces = set(self.world.fill_slot_data()[contract.START_GRACES])
        urns = list(range(12020600, 12020608)) + list(range(12020620, 12020628))
        assert len(urns) == 16, "the urn range is wrong -- the assertion below would be vacuous"
        assert 12020609 in graces and 12020629 in graces, (
            "the aggregates are not on the wire, so 'no urns' below would be true for free")
        leaked = sorted(set(urns) & graces)
        assert not leaked, f"individual urn flag(s) reached startGraces: {leaked}"

    def test_the_doors_are_on_the_TAIL_and_never_the_head(self):
        """🛑 start_graces.first() is read twice for something else entirely: it is the clobber
        read-back sentinel in core.rs, and fast_travel::prime_known_good takes the first positive
        element. Riding this key is only safe while the doors stay off the head -- so pin it."""
        graces = self.world.fill_slot_data()[contract.START_GRACES]
        doors = {f for _, f in cd.LEVER_DOORS}
        assert graces, "startGraces is empty -- the assertion below would pass vacuously"
        assert graces[0] not in doors, (
            f"a door flag ({graces[0]}) is the HEAD of startGraces. Append, never prepend: the "
            f"head is the clobber sentinel and the fast-travel prime target.")

    def test_the_boss_and_its_sweep_are_still_earned(self):
        """The door is a prerequisite to REACHING the boss, so opening it must not hand over the
        boss's own defeat flag or any sweep payload. The 30XX0800 band is the boss-defeat flag the
        sweeps key on; none of it may ride along."""
        graces = self.world.fill_slot_data()[contract.START_GRACES]
        def _boss_defeat(seq):
            return [g for g in seq if 30000800 <= g <= 30209999 and (g // 100) % 10 == 8]
        # WITNESS THE FILTER, not just the input. "no boss flags found" is also what a filter that
        # matches nothing says, so plant one and require it to be caught. 30000800 is Tombsward's
        # boss-defeat flag, the id its dungeon sweep keys on.
        assert _boss_defeat([30000800]) == [30000800], (
            "the boss-defeat filter does not match a known boss-defeat flag -- it is dead, and the "
            "assertion below would pass whatever startGraces contained")
        assert graces, "startGraces is empty -- likewise"
        boss_flags = _boss_defeat(graces)
        assert not boss_flags, (
            f"a boss-defeat flag reached startGraces: {boss_flags}. Opening the door must not win "
            f"the fight -- that would grant the check AND the whole dungeon sweep.")
