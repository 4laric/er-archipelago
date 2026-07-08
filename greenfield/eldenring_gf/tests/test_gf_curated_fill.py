"""curated_fill + big-ticket tags tests.

Pure-data: the new LOCATION_TAGS types (Legendary/GreatRune/KeyItem) are generated and selectable in
important_locations. WorldTestBase: curated_fill marks every big-ticket check PRIORITY (advancement
gets first crack; the excess fall through to filler), and the base test_fill on each subclass proves
generation stays beatable (no FillError) with it on.

Big-ticket is defined by contract.is_big_ticket: a BIG_TICKET_TYPES tag AND no BIG_TICKET_EXCLUDE_TAGS
tag. Shop is excluded, so Enia's remembrance store (Shop+Legendary) never gets a region Lock nor a
tracker star, even though those items keep their Legendary tag for important_locations / display.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.location_tags import LOCATION_TAGS, TAG_COUNTS  # noqa: E402
from worlds.eldenring_gf.contract import (  # noqa: E402
    BIG_TICKET_TYPES, BIG_TICKET_EXCLUDE_TAGS, is_big_ticket,
)
from worlds.eldenring_gf.features.curated_fill import select_priority  # noqa: E402
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


def test_shop_excluded_from_big_ticket():
    """Enia's remembrance store (Shop+Legendary) is buy-only -> excluded from big-ticket, but the
    Legendary TAG itself is untouched. World-drop legendaries (no Shop) stay big-ticket."""
    assert BIG_TICKET_EXCLUDE_TAGS == {"Shop"}
    assert not is_big_ticket(["Shop", "Legendary"])   # Enia gear: legendary, but buy-only
    assert is_big_ticket(["Legendary"])               # world-drop legendary
    assert is_big_ticket(["Boss"])
    assert not is_big_ticket([]) and not is_big_ticket(None)
    # real table: EVERY Shop+Legendary row (Enia) is excluded; there is at least one.
    shop_leg = [i for i, t in LOCATION_TAGS.items() if "Shop" in t and "Legendary" in t]
    assert shop_leg, "expected Enia shop-legendary rows in the table"
    assert all(not is_big_ticket(LOCATION_TAGS[i]) for i in shop_leg), "no Enia slot may be big-ticket"
    # world-drop legendaries remain big-ticket
    wd = [i for i, t in LOCATION_TAGS.items() if "Legendary" in t and "Shop" not in t]
    assert wd and all(is_big_ticket(LOCATION_TAGS[i]) for i in wd), "world-drop legendaries stay big-ticket"
    # no Shop-tagged location is big-ticket at all
    assert not any(is_big_ticket(t) for t in LOCATION_TAGS.values() if "Shop" in t)


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
        # EVERY selected slot is a big-ticket check, and NONE is a shop slot (Enia excluded).
        for L in prio:
            tags = LOCATION_TAGS.get(L.address, [])
            self.assertTrue(is_big_ticket(tags), f"priority slot {L.name} must be big-ticket")
            self.assertNotIn("Shop", tags, f"shop slot {L.name} must not be priority (Enia excluded)")
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
