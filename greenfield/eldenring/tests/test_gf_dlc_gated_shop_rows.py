"""AzoTax's no-DLC goal-lock (Discord 2026-08-20): DLC-gated hub shop rows leave a no-DLC seed.

Enia stands in Roundtable Hold -- kept in EVERY seed -- and 36 of her shop rows are gated on DLC
content: the remembrance trades consume a DLC remembrance as their EquipMtrlSetParam material
(the 2,000,000 goods block), and the DLC boss armor sets release on DLC ceremony flags while
selling >=3,000,000 protectors. With `enable_dlc: false` those checks could never open; a
two-player seed on a pre-#860 apworld had a goal-required item parked on one.

THE RULE, not the list: gen_data derives `shop_data.DLC_GATED_SHOP_CHECK_FLAGS` from the vanilla
params; core.py skips those locations at creation when the seed has no DLC. These tests hold the
two worlds against each other (the motivating case) and re-derive the set from the committed
inputs (the keeper), so neither half can drift silently.
"""
import unittest

from test.bases import WorldTestBase

from ..shop_data import DLC_GATED_SHOP_CHECK_FLAGS, SHOP_ROW_FLAGS
from ..data import LOCATIONS

GAME = "Elden Ring"


def _flags_in(world_base):
    mw = world_base.multiworld
    ap2flag = {ap: int(fl) for locs in LOCATIONS.values() for (_n, ap, fl) in locs}
    return {ap2flag[l.address] for l in mw.get_locations(1)
            if getattr(l, "address", None) in ap2flag}


class TestTheMotivatingCase(unittest.TestCase):
    def test_no_dlc_seed_has_no_dlc_gated_shop_rows(self):
        """AzoTax's seed shape: DLC off. Not one of the 36 may exist."""
        class _T(WorldTestBase):
            game = GAME
            options = {"num_regions": 0, "enable_dlc": False}
        t = _T("runTest"); t.setUp()
        flags = _flags_in(t)
        # WITNESSES: an empty world or an empty derived set greens the emptiness below for free.
        self.assertGreater(len(flags), 1000, "the no-DLC world built almost nothing")
        self.assertTrue(DLC_GATED_SHOP_CHECK_FLAGS, "the derived set is empty -- nothing is gated")
        present = flags & set(DLC_GATED_SHOP_CHECK_FLAGS)
        self.assertEqual(sorted(present), [],
                         "DLC-gated shop check(s) exist in a no-DLC seed -- with the DLC off "
                         "these can never open, and fill may park a required item there")

    def test_dlc_seed_keeps_every_one(self):
        """The other direction: the skip must not leak into DLC seeds."""
        class _T(WorldTestBase):
            game = GAME
            options = {"num_regions": 0, "enable_dlc": True}
        t = _T("runTest"); t.setUp()
        flags = _flags_in(t)
        self.assertGreater(len(flags), 1000, "the DLC world built almost nothing")
        self.assertTrue(DLC_GATED_SHOP_CHECK_FLAGS, "the derived set is empty -- nothing to keep")
        missing = set(DLC_GATED_SHOP_CHECK_FLAGS) - flags
        self.assertEqual(sorted(missing), [],
                         "DLC-gated shop check(s) MISSING from a DLC seed -- the skip fired "
                         "when the content is in play")


class TestTheDerivedSet(unittest.TestCase):
    def test_the_set_is_the_36_and_all_are_hub_shop_checks(self):
        """Pinned with its reason: Enia's 15 DLC armor rows, 2 Dancing Lion extras, and 19
        remembrance-trade rows = 36, every one a Roundtable Hold shop check. A GROWTH means the
        derivation started matching new rows -- name them; a SHRINK means a DLC gate stopped
        being visible to it -- that is AzoTax's bug returning, look before re-pinning."""
        # WITNESSES first: the subset assertions below pass for free over empty sets.
        self.assertEqual(len(DLC_GATED_SHOP_CHECK_FLAGS), 36)
        shop_flags = set(SHOP_ROW_FLAGS.values())
        self.assertTrue(shop_flags, "SHOP_ROW_FLAGS is empty -- shop_data did not generate")
        self.assertTrue(set(DLC_GATED_SHOP_CHECK_FLAGS) <= shop_flags,
                        "a DLC-gated flag is not a shop check flag at all")
        hub = {int(fl) for (_n, _ap, fl) in LOCATIONS.get("Roundtable Hold", [])}
        stray = sorted(set(DLC_GATED_SHOP_CHECK_FLAGS) - hub)
        self.assertEqual(stray, [],
                         "DLC-gated shop flag(s) outside Roundtable Hold: %r -- fine in "
                         "principle (their regions already leave with the DLC) but NEW, so "
                         "say why here" % stray)
