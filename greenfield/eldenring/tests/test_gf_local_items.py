"""Local Items -- the `keep_local` category control (WorldTestBase).

`local_item_only` and `exclude_local_item_only` were RETIRED 2026-08-14 and are `Options.Removed`,
so naming either one here would raise rather than skip. `keep_local: [everything]` is their
replacement and these tests are the proof it is a true replacement, not a near one:

keep_local [everything] + item_shuffle ON -> every real vanilla item name (ITEM_CATALOG) is in
                                             world.options.local_items.value -- the exact assertion
                                             the retired toggle used to satisfy.
keep_local empty                          -> those names are NOT force-added.
keep_local a SUBSET                       -> only that category is held; the rest travel. This is
                                             what replaces exclude_local_item_only, inverted: name
                                             what you keep instead of what you release.

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
    """`keep_local: [everything]` must localize exactly what `local_item_only: true` did. This class
    is the retirement's acceptance test -- it is the OLD assertion against the NEW spelling."""
    game = GAME
    options = {"num_regions": 0, "keep_local": {"everything"}, "item_shuffle": True}

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
    # 🛑 BOTH knobs have to be turned off to reach "off". `keep_local: set()` alone stopped being
    # enough at #703, which gave `keep_local_rune_cap` a default of 12,500 (this comment said 6,250
    # until 2026-08-16 -- the same stale number the option's own docstring carried) -- the runes it holds are
    # catalog names, so this class would fail reporting Golden Runes as "force added" when nothing
    # had forced anything. Naming both is the isolation the test always meant.
    # ⚠️ THREE knobs now. `filler_foreign_pct` began shipping at 70 on 2026-08-16 and writes into
    # the same set, so "off" needs it pinned to its 100 no-op too -- the same lesson this comment
    # already records for the rune cap, arriving a third time.
    options = {"num_regions": 0, "keep_local": set(), "keep_local_rune_cap": 0,
               "item_shuffle": True, "filler_foreign_pct": 100}

    def test_catalog_items_not_force_added(self):
        # nothing named -> feature leaves local_items alone. With no hand-authored local_items in
        # the test yaml, the catalog names must NOT appear.
        local = _local_set(self)
        present = [n for n in ITEM_CATALOG if n in local]
        self.assertFalse(present, f"toggle off must not force items local (found {present[:3]})")


class LocalItemsPartial(WorldTestBase):
    """What replaces `exclude_local_item_only`, inverted. The retired pair said "everything MINUS
    goods"; `keep_local` says "goods" -- so this asserts the mirror image of the old test, and that
    is the whole ergonomic difference the retirement costs."""
    game = GAME
    options = {"num_regions": 0,
        "item_shuffle": True,
        "keep_local": {"goods"},
    }

    def test_named_category_held_and_the_rest_travel(self):
        # goods (FullID high nibble 0x40000000) are NAMED -> forced local. Weapons (nibble 0x0) are
        # not named -> must stay foreign-eligible. Both directions, because a keep_local that held
        # everything would satisfy the first assertion alone.
        local = _local_set(self)
        goods = [n for n, full in ITEM_CATALOG.items() if (full & 0xF0000000) == 0x40000000]
        weapons = [n for n, full in ITEM_CATALOG.items() if (full & 0xF0000000) == 0x00000000]
        self.assertTrue(goods and weapons, "catalog should contain both goods and weapons")
        self.assertTrue(all(n in local for n in goods),
                        "the named 'goods' category must be held local")
        self.assertTrue(all(n not in local for n in weapons),
                        "an unnamed category must stay foreign-eligible")
