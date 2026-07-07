"""curated_fill + big-ticket tags tests.

Pure-data: the new LOCATION_TAGS types (Legendary/GreatRune/KeyItem) are generated and selectable in
important_locations. WorldTestBase: curated_fill marks every big-ticket check PRIORITY (advancement
gets first crack; the excess fall through to filler), and the base test_fill on each subclass proves
generation stays beatable (no FillError) with it on.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.location_tags import LOCATION_TAGS, TAG_COUNTS  # noqa: E402
from worlds.eldenring_gf.features.curated_fill import BIG_TICKET_TYPES, select_priority  # noqa: E402
from worlds.eldenring_gf.features.important_locations import _VALID  # noqa: E402

GAME = "Elden Ring (Greenfield)"


# ---- pure-data guards -------------------------------------------------------------------------
def test_new_big_ticket_tags_generated():
    """gen_data derives Legendary (rarity==3), GreatRune, KeyItem into LOCATION_TAGS."""
    for t in ("Legendary", "GreatRune", "KeyItem"):
        assert TAG_COUNTS.get(t, 0) > 0, f"{t} should tag some locations"
    assert TAG_COUNTS["Legendary"] > TAG_COUNTS["GreatRune"], "many legendaries, few great runes"


def test_new_tags_selectable_in_important_locations():
    for t in ("Legendary", "GreatRune", "KeyItem"):
        assert t in _VALID, f"{t} must be a valid important_locations type"


def test_big_ticket_set():
    assert BIG_TICKET_TYPES == {"Boss", "Remembrance", "Legendary", "GreatRune", "KeyItem"}


# ---- WorldTestBase: routing + fill-safety -----------------------------------------------------
class CuratedFillOn(WorldTestBase):
    game = GAME
    # the inherited test_fill proves this generates + is beatable (no FillError) with curated_fill on.
    options = {"item_shuffle": True, "enable_dlc": True, "curated_fill": True, "num_regions": 8}

    def test_all_big_ticket_marked_priority(self):
        # select_priority is the pure selection (no get_all_state) -> no MultiWorld leak in teardown.
        prio = select_priority(self.world)
        n_adv = sum(1 for it in self.multiworld.itempool
                    if it.player == self.world.player and it.advancement)
        # EVERY selected slot is a big-ticket check.
        for L in prio:
            self.assertTrue(BIG_TICKET_TYPES.intersection(LOCATION_TAGS.get(L.address, [])),
                            f"priority slot {L.name} must be big-ticket")
        # There are far MORE big-ticket priority slots than advancement items -- that's the point:
        # advancement gets first crack, the leftover big-ticket fall through to useful/filler. (No
        # cap; a tight priority==advancement set is the only thing that would FillError.)
        self.assertGreater(len(prio), n_adv,
                           "curated_fill marks all big-ticket -> more priority slots than locks")


class CuratedFillOff(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "curated_fill": False, "num_regions": 6}

    def test_off_marks_nothing(self):
        self.assertEqual(select_priority(self.world), [], "curated_fill off -> no priority marking")
