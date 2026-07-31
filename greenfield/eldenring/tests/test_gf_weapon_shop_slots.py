"""WEAPON shop slots are UNCONSTRAINED -- the fill may put anything on them.

This file used to assert the opposite. `features/weapon_shop_slots.py` forced every weapon shop slot
to hold an own-world ER weapon, so the client's rewrite was always weapon -> weapon. It was deleted
2026-07-25 (Alaric: "full random"), and these tests are its headstone: they now pin the ABSENCE of
that constraint, so nobody restores it by reflex.

Why it existed, and why it doesn't:

  * The client's SHOP_CTD_GUARD refused to natively rewrite a WEAPON row whose reward was a
    non-weapon, on a 3x CTD repro from 2026-07-03. A guarded row stayed on the vanilla-sell path,
    which leaked the vanilla good AND previewed vanilla. Forcing own-world weapons dodged that.
  * SHOP_CTD_GUARD was REMOVED 2026-07-11: its repro is believed confounded by the bag-add nulling
    that was live then (`should_suppress_sold`) and is dead code now. So a weapon row rewrites to
    any reward, and the constraint bought nothing.

⚠️ The CTD theory is NOT proven -- "armor -> goods" also produces a non-weapon bag-add and never
crashed, so the exoneration has a hole. Deleting this constraint is the deliberate experiment that
settles it (buy out every shop). If a weapon-slot purchase CTDs in playtest, the fix is to restore
the two-line guard in the CLIENT's shop_sell::run -- not to re-add a fill constraint here. A fill
rule that hides a crash is a worse answer than the crash: it makes the bug unreproducible while
leaving it live for every seed the rule happens not to cover.

The slot is not a special case any more, so most of what used to be tested here is now covered by
the general shop suites (test_gf_shops.py, test_gf_shop_preview_repoint.py). What remains is the
regression guard.
"""
import unittest
import pytest

from worlds.eldenring.shop_data import SHOP_PREVIEW_GOODS
from worlds.eldenring.item_ids import ITEM_CATALOG

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
GAME = "Elden Ring"

_NIBBLE_MASK = 0xF0000000
_WEAPON_NIBBLE = 0x00000000


def _is_weapon_full(full):
    return full is not None and (full & _NIBBLE_MASK) == _WEAPON_NIBBLE


def _is_weapon_slot(address):
    return _is_weapon_full(SHOP_PREVIEW_GOODS.get(str(address)))


class TheFeatureIsGone(unittest.TestCase):
    def test_weapon_shop_slots_feature_no_longer_exists(self):
        """Named so the failure explains itself: if someone re-adds the module, this says why not."""
        with self.assertRaises(
                ImportError,
                msg="features/weapon_shop_slots.py is back. It forced weapon shop slots to hold "
                    "own-world weapons to dodge a client CTD that was exonerated 2026-07-11. If a "
                    "weapon-slot purchase is crashing again, restore the guard in the CLIENT "
                    "(shop_sell::run) where the crash actually is -- do not re-constrain the fill."):
            import worlds.eldenring.features.weapon_shop_slots  # noqa: F401

    def test_the_data_still_distinguishes_weapon_slots(self):
        # Not a constraint any more, but the derivation is still load-bearing for shop_sell's
        # cross-type rewrite and for the tests below. If it went empty, they would pass vacuously.
        weapon_slots = [a for a, f in SHOP_PREVIEW_GOODS.items() if _is_weapon_full(f)]
        self.assertGreater(len(weapon_slots), 0, "no weapon shop slots derived from the data")


class WeaponSlotsAcceptAnything(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": True}  # the pool that USED to trigger enforcement

    def _weapon_slots_in_play(self):
        return [l for l in self.multiworld.get_locations(self.world.player)
                if getattr(l, "address", None) is not None and _is_weapon_slot(l.address)]

    def test_a_weapon_slot_accepts_a_non_weapon(self):
        """The exact inverse of the old test_weapon_slots_reject_non_weapon. This is the assertion
        that goes red the moment the constraint comes back."""
        slots = self._weapon_slots_in_play()
        self.assertGreater(len(slots), 0, "expected weapon shop slots in play with the real-item pool")
        filler = self.world.create_item(self.world.get_filler_item_name())
        self.assertFalse(_is_weapon_full(ITEM_CATALOG.get(filler.name)),
                         "the filler item must be a non-weapon for this test to mean anything")
        rejecting = [l for l in slots if not l.item_rule(filler)]
        self.assertFalse(
            rejecting,
            "%d weapon shop slot(s) still reject a non-weapon item -- something is re-imposing the "
            "deleted weapon_shop_slots constraint" % len(rejecting))

    def test_a_weapon_slot_accepts_a_foreign_item(self):
        # Foreign rewards were never blocked, but they are the population the repoint now flowers,
        # so pin that nothing on the weapon-slot path filters them either.
        slots = self._weapon_slots_in_play()
        foreign = self.world.create_item(self.world.get_filler_item_name())
        foreign.player = self.world.player + 1
        rejecting = [l for l in slots if not l.item_rule(foreign)]
        self.assertFalse(rejecting, "%d weapon shop slot(s) reject a foreign item" % len(rejecting))


class DegeneratePoolStillGenerates(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "item_shuffle": False}  # the pool whose fill-safety gate used to matter

    def test_generates_without_overconstraint(self):
        # Kept from the old file: the degenerate pool was the case the deleted feature had to skip
        # for. With no constraint there is nothing to skip, but a regression here would still be the
        # first sign that something re-narrowed the shop slots.
        self.assertTrue(self.multiworld.get_locations(self.world.player))
