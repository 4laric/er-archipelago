"""curated_fill + configurable big-ticket tests.

Big-ticket is defined by contract.is_big_ticket(tags, selected): a SELECTED class tag AND no
BIG_TICKET_EXCLUDE_TAGS tag. The selection is the `big_ticket_locations` OptionList (same vocabulary
as important_locations); default = Boss/Remembrance/Legendary/GreatRune/KeyItem. Enia's remembrance
store carries the internal `EniaShop` tag and is a permanent hard-exclude, so selecting Shop turns on
the OTHER shops but never Enia. features/big_ticket_locations ships the per-seed id list to the client
as `bigTicketLocations`, and curated_fill routes region Locks onto the same set -- one source, no drift.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.location_tags import LOCATION_TAGS, TAG_COUNTS  # noqa: E402
from worlds.eldenring_gf.contract import (  # noqa: E402
    BIG_TICKET_TYPES, BIG_TICKET_EXCLUDE_TAGS, IMPORTANT_LOCATION_TYPES, is_big_ticket,
    BIG_TICKET_LOCATIONS,
)
from worlds.eldenring_gf.features.curated_fill import select_priority  # noqa: E402
from worlds.eldenring_gf.features.important_locations import _VALID  # noqa: E402
from worlds.eldenring_gf.features.big_ticket_locations import BigTicketLocations  # noqa: E402

GAME = "Elden Ring (Greenfield)"


# ---- pure-data guards -------------------------------------------------------------------------
def test_new_big_ticket_tags_generated():
    for t in ("Legendary", "GreatRune", "KeyItem"):
        assert TAG_COUNTS.get(t, 0) > 0, f"{t} should tag some locations"
    assert TAG_COUNTS["Legendary"] > TAG_COUNTS["GreatRune"], "many legendaries, few great runes"


def test_vocabulary_shared_with_important_locations():
    assert list(_VALID) == list(IMPORTANT_LOCATION_TYPES)
    assert BigTicketLocations.valid_keys == frozenset(IMPORTANT_LOCATION_TYPES)
    assert set(BigTicketLocations.default) == set(BIG_TICKET_TYPES)


def test_big_ticket_default_set():
    assert BIG_TICKET_TYPES == {"Boss", "Remembrance", "Legendary", "GreatRune", "KeyItem"}
    assert BIG_TICKET_EXCLUDE_TAGS == {"EniaShop"}


def test_is_big_ticket_semantics():
    # default selection
    assert is_big_ticket(["Legendary"]) and is_big_ticket(["Boss"])
    assert not is_big_ticket([]) and not is_big_ticket(None)
    assert not is_big_ticket(["Shop"])                    # Shop not in default
    # Shop is selectable -> turns on
    assert is_big_ticket(["Shop"], {"Shop"})
    # Enia (EniaShop) is a permanent hard-exclude under ANY selection
    enia = ["Shop", "Legendary", "EniaShop"]
    assert not is_big_ticket(enia)
    assert not is_big_ticket(enia, {"Shop", "Legendary", "Boss"})
    assert not is_big_ticket(enia, set(IMPORTANT_LOCATION_TYPES))


def test_enia_hard_excluded_in_real_table():
    """After gen_data, Enia's remembrance store carries EniaShop; it is never big-ticket."""
    enia = [i for i, t in LOCATION_TAGS.items() if "EniaShop" in t]
    assert enia, "expected EniaShop-tagged rows (regenerate location_tags.py)"
    everything = set(IMPORTANT_LOCATION_TYPES)
    for i in enia:
        assert not is_big_ticket(LOCATION_TAGS[i]), f"{i} big-ticket under default"
        assert not is_big_ticket(LOCATION_TAGS[i], everything), f"{i} big-ticket under full selection"


def test_shop_selection_turns_on_nonenia_shops():
    base = [i for i, t in LOCATION_TAGS.items() if is_big_ticket(t)]
    withshop = [i for i, t in LOCATION_TAGS.items() if is_big_ticket(t, set(BIG_TICKET_TYPES) | {"Shop"})]
    assert len(withshop) > len(base), "selecting Shop should light up non-Enia shops"
    assert not any("EniaShop" in LOCATION_TAGS[i] for i in withshop), "Enia must stay excluded"


# ---- WorldTestBase: routing + slot_data + fill-safety -----------------------------------------
class CuratedFillOn(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "enable_dlc": True, "curated_fill": True, "num_regions": 8}

    def test_all_big_ticket_marked_priority(self):
        prio = select_priority(self.world)
        n_adv = sum(1 for it in self.multiworld.itempool
                    if it.player == self.world.player and it.advancement)
        sel = set(self.world.options.big_ticket_locations.value)
        for L in prio:
            tags = LOCATION_TAGS.get(L.address, [])
            self.assertTrue(is_big_ticket(tags, sel), f"priority slot {L.name} must be big-ticket")
            self.assertNotIn("EniaShop", tags, f"Enia slot {L.name} must never be priority")
        self.assertGreater(len(prio), n_adv,
                           "curated_fill marks all big-ticket -> more priority slots than locks")

    def test_bigticket_locations_emitted_and_consistent(self):
        # the feature ships the per-seed id list; it must equal curated_fill's placement set (no drift)
        sd = self.world.fill_slot_data()
        self.assertIn(BIG_TICKET_LOCATIONS, sd)
        emitted = set(sd[BIG_TICKET_LOCATIONS])
        self.assertTrue(emitted, "bigTicketLocations should be non-empty for a normal seed")
        for i in emitted:
            self.assertTrue(is_big_ticket(LOCATION_TAGS.get(i), set(self.world.options.big_ticket_locations.value)))
            self.assertNotIn("EniaShop", LOCATION_TAGS.get(i, []))
        placed = {L.address for L in select_priority(self.world)}
        self.assertEqual(emitted, placed, "tracker set (slot_data) must equal curated_fill placement set")


class CuratedFillOff(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True, "curated_fill": False, "num_regions": 6}

    def test_off_marks_nothing(self):
        self.assertEqual(select_priority(self.world), [], "curated_fill off -> no priority marking")
