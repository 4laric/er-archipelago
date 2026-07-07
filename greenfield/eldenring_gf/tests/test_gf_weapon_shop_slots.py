"""weapon_shop_slots tests -- WEAPON shop slots must hold an own-world ER weapon.

WHY: the client SHOP_CTD_GUARD leaves a weapon row whose reward is non-weapon on the vanilla-sell
path -> the slot hands over the vanilla good (leak) + previews vanilla. Forcing own-world weapons
keeps every weapon->weapon rewrite native + safe. Fill-safety gate skips a degenerate pool.
"""
import unittest
import pytest

from worlds.eldenring_gf.features.weapon_shop_slots import (
    _is_weapon_full, _is_weapon_slot, _is_own_weapon, _WEAPON_NIBBLE, _NIBBLE_MASK,
)
from worlds.eldenring_gf.shop_data import SHOP_PREVIEW_GOODS
from worlds.eldenring_gf.item_ids import ITEM_CATALOG

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
GAME = "Elden Ring (Greenfield)"


class NibbleDataTests(unittest.TestCase):
    def test_weapon_nibble_is_zero(self):
        self.assertEqual(_WEAPON_NIBBLE, 0x0)
        self.assertTrue(_is_weapon_full(0x00003A98))          # a weapon FullID (nibble 0x0)
        self.assertFalse(_is_weapon_full(0x40000B54))         # a GOODS FullID (Golden Rune)
        self.assertFalse(_is_weapon_full(0x10000000 | 100))   # a PROTECTOR FullID
        self.assertFalse(_is_weapon_full(None))

    def test_some_weapon_slots_exist(self):
        # Twin Maiden Husks resell many weapons; the data must expose weapon-nibble preview goods,
        # else the guard is a silent no-op (the exact failure mode it fixes).
        weapon_slots = [a for a, f in SHOP_PREVIEW_GOODS.items() if _is_weapon_full(f)]
        self.assertGreater(len(weapon_slots), 0, "no weapon shop slots derived from the data")

    def test_catalog_has_weapons(self):
        weapons = [n for n, f in ITEM_CATALOG.items() if _is_weapon_full(f)]
        self.assertGreater(len(weapons), 50, "catalog should hold ample ER weapons for the fill")


class WeaponSlotsEnforced(WorldTestBase):
    game = GAME
    options = {"item_shuffle": True}  # real-item pool -> enough own-world weapons to enforce

    def _weapon_slots_in_play(self):
        return [l for l in self.multiworld.get_locations(self.world.player)
                if getattr(l, "address", None) is not None and _is_weapon_slot(l.address)]

    def test_weapon_slots_reject_non_weapon(self):
        slots = self._weapon_slots_in_play()
        self.assertGreater(len(slots), 0, "expected weapon shop slots in play with the real-item pool")
        # a filler good (non-weapon) must be rejected by every weapon slot
        filler = self.world.create_item(self.world.get_filler_item_name())
        self.assertFalse(_is_own_weapon(filler, self.world.player))
        bad = [l for l in slots if l.item_rule(filler)]
        self.assertFalse(bad, f"{len(bad)} weapon slots accept a non-weapon item")

    def test_placed_own_items_are_weapons(self):
        # post-fill: any OWN-world item on a weapon slot is a weapon (foreign items are fine -- the
        # client leaves foreign shop slots on the preview path regardless).
        for l in self._weapon_slots_in_play():
            if l.item is not None and l.item.player == self.world.player:
                self.assertTrue(_is_own_weapon(l.item, self.world.player),
                                f"non-weapon own item landed on weapon slot {l.name}: {l.item.name}")


class WeaponSlotsDegenerateSafe(WorldTestBase):
    game = GAME
    options = {"item_shuffle": False}  # degenerate pool -> gate must SKIP, gen must not FillError

    def test_generates_without_overconstraint(self):
        self.assertTrue(self.multiworld.get_locations(self.world.player))
