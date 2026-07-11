"""Phase 7 tests -- Local Items convenience toggle (WorldTestBase).

local_item_only ON + item_shuffle ON  -> every real vanilla item name (ITEM_CATALOG) is in
                                          world.options.local_items.value.
local_item_only OFF                   -> those names are NOT force-added.
item_shuffle OFF                      -> no-op even with the toggle on (no real items exist).
exclude_local_item_only               -> a released category is left free to travel.
Base WorldTestBase.test_fill runs for each subclass and proves winnability either way (Region Locks
stay the sole progression; local_items only restricts WHERE non-progression items may land).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring"


def _local_set(tb):
    """The player's local_items name set as fill will see it: the world options set."""
    return set(tb.world.options.local_items.value)


class LocalItemsOn(WorldTestBase):
    game = GAME
    options = {"local_item_only": True, "item_shuffle": True}

    def test_catalog_items_forced_local(self):
        self.assertTrue(ITEM_CATALOG, "item_ids.py must be generated for this test to be meaningful")
        local = _local_set(self)
        # every real vanilla item name is forced into local_items
        missing = [n for n in ITEM_CATALOG if n not in local]
        self.assertFalse(missing, f"{len(missing)} catalog items were not forced local (e.g. {missing[:3]})")

    def test_locks_and_rune_not_localized(self):
        # progression Locks + generic Rune filler are exactly what SHOULD stay free to travel;
        # the feature must not have swept them into local_items.
        local = _local_set(self)
        self.assertNotIn("Rune", local)
        lock_names = [n for n in self.world.item_name_to_id if n.endswith(" Lock")]
        self.assertTrue(lock_names)
        for lk in lock_names:
            self.assertNotIn(lk, local, "Region Locks must stay foreign-eligible (progression)")


class LocalItemsOff(WorldTestBase):
    game = GAME
    options = {"local_item_only": False, "item_shuffle": True}

    def test_catalog_items_not_force_added(self):
        # toggle off -> feature leaves local_items alone. With no hand-authored local_items in the
        # test yaml, the catalog names must NOT appear.
        local = _local_set(self)
        present = [n for n in ITEM_CATALOG if n in local]
        self.assertFalse(present, f"toggle off must not force items local (found {present[:3]})")


class LocalItemsWithExclusion(WorldTestBase):
    game = GAME
    options = {
        "local_item_only": True,
        "item_shuffle": True,
        "exclude_local_item_only": {"goods"},
    }

    def test_excluded_category_left_foreign(self):
        # goods (FullID high nibble 0x40000000) are released -> must NOT be forced local, while a
        # non-excluded category (e.g. weapons, nibble 0x0) still is.
        local = _local_set(self)
        goods = [n for n, full in ITEM_CATALOG.items() if (full & 0xF0000000) == 0x40000000]
        weapons = [n for n, full in ITEM_CATALOG.items() if (full & 0xF0000000) == 0x00000000]
        self.assertTrue(goods and weapons, "catalog should contain both goods and weapons")
        self.assertTrue(all(n not in local for n in goods),
                        "excluded 'goods' category must stay foreign-eligible")
        self.assertTrue(all(n in local for n in weapons),
                        "non-excluded 'weapons' category must still be forced local")
