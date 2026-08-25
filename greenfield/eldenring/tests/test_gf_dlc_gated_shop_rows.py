"""AzoTax's no-DLC goal-lock (Discord 2026-08-20): DLC-gated hub shop rows leave a no-DLC seed.

Enia stands in Roundtable Hold -- kept in EVERY seed -- and 36 of her shop rows are gated on DLC
content: the remembrance trades consume a DLC remembrance as their EquipMtrlSetParam material
(the 2,000,000 goods block), and the DLC boss armor sets release on DLC ceremony flags while
selling >=3,000,000 protectors. With `enable_dlc: false` those checks could never open; a
two-player seed on a pre-#860 apworld had a goal-required item parked on one.

2026-08-24 (#1013): Enia's whole shop is VANILLA again -- excluded from randomization -- so the
36 are no longer checks at all and `DLC_GATED_SHOP_CHECK_FLAGS` is EMPTY. That emptiness is
explained, not data loss: every one of the 36 is in `data.NOT_RANDOMIZED` under the
`enia_vanilla` rule. The #913 machinery stays armed: gen_data still derives and emits the RAW
set (`DLC_GATED_SHOP_ROW_FLAGS`), so if a DLC-gated hub row ever becomes a check again the
core.py per-seed skip has its input back without re-deriving anything.

THE RULE, not the list: the check set must equal the raw set minus the NOT_RANDOMIZED ledger --
never pinned independently -- and no raw-set flag may exist in a no-DLC seed.
"""
import unittest

from test.bases import WorldTestBase

from ..shop_data import (
    DLC_GATED_SHOP_CHECK_FLAGS,
    DLC_GATED_SHOP_ROW_FLAGS,
    SHOP_ROW_FLAGS,
)
from ..data import LOCATIONS, NOT_RANDOMIZED

GAME = "Elden Ring"


def _flags_in(world_base):
    mw = world_base.multiworld
    ap2flag = {ap: int(fl) for locs in LOCATIONS.values() for (_n, ap, fl) in locs}
    return {ap2flag[l.address] for l in mw.get_locations(1)
            if getattr(l, "address", None) in ap2flag}


class TestTheMotivatingCase(unittest.TestCase):
    def test_no_dlc_seed_has_no_dlc_gated_shop_rows(self):
        """AzoTax's seed shape: DLC off. Not one of the raw 36 may exist as a check."""
        class _T(WorldTestBase):
            game = GAME
            options = {"num_regions": 0, "enable_dlc": False}
        t = _T("runTest"); t.setUp()
        flags = _flags_in(t)
        # WITNESSES: an empty world or an empty raw set greens the emptiness below for free.
        self.assertGreater(len(flags), 1000, "the no-DLC world built almost nothing")
        self.assertEqual(len(DLC_GATED_SHOP_ROW_FLAGS), 36,
                         "the raw derived set changed -- see TestTheDerivedSet before "
                         "re-pinning anything")
        present = flags & set(DLC_GATED_SHOP_ROW_FLAGS)
        self.assertEqual(sorted(present), [],
                         "DLC-gated shop flag(s) exist as checks in a no-DLC seed -- with the "
                         "DLC off these can never open, and fill may park a required item "
                         "there (AzoTax's goal-lock)")

    def test_dlc_seed_keeps_every_gated_check(self):
        """The other direction: the skip must not leak into DLC seeds. With Enia vanilla the
        check set is EMPTY, so the subset assertion is vacuous BY CONSTRUCTION (the witness
        below keeps the world real) -- it re-arms itself the day a gated hub row becomes a
        check again."""
        class _T(WorldTestBase):
            game = GAME
            options = {"num_regions": 0, "enable_dlc": True}
        t = _T("runTest"); t.setUp()
        flags = _flags_in(t)
        self.assertGreater(len(flags), 1000, "the DLC world built almost nothing")
        missing = set(DLC_GATED_SHOP_CHECK_FLAGS) - flags
        self.assertEqual(sorted(missing), [],
                         "DLC-gated shop check(s) MISSING from a DLC seed -- the skip fired "
                         "when the content is in play")


class TestTheDerivedSet(unittest.TestCase):
    def test_the_raw_set_is_the_36(self):
        """Pinned with its reason: Enia's 15 DLC boss-armor releases, 2 Dancing Lion extras,
        and 19 remembrance-trade rows = 36. A GROWTH means the derivation started matching new
        rows -- name them; a SHRINK means a DLC gate stopped being visible to it -- that is
        AzoTax's bug returning, look before re-pinning."""
        self.assertEqual(len(DLC_GATED_SHOP_ROW_FLAGS), 36)

    def test_the_check_set_is_the_raw_set_minus_the_ledger(self):
        """The emptiness of the check set must be EXPLAINED by NOT_RANDOMIZED, never pinned:
        check == raw minus ledgered flags. With Enia vanilla (#1013) every raw flag carries the
        `enia_vanilla` rule and the check set is empty; if any raw flag is ever a check again
        this equality still holds without a re-pin."""
        self.assertEqual(
            set(DLC_GATED_SHOP_CHECK_FLAGS),
            {fl for fl in DLC_GATED_SHOP_ROW_FLAGS if fl not in NOT_RANDOMIZED},
            "a DLC-gated flag left the check set without a NOT_RANDOMIZED entry explaining "
            "why (or vice versa) -- unexplained set drift is the #913 failure mode")
        # And the ledger entries that DO explain it name the rule:
        for fl in DLC_GATED_SHOP_ROW_FLAGS:
            if fl in NOT_RANDOMIZED:
                self.assertIn("enia_vanilla", NOT_RANDOMIZED[fl],
                              "DLC-gated flag %d is ledgered under an unexpected rule -- say "
                              "why here" % fl)

    def test_every_check_is_a_hub_shop_check(self):
        """Shape guard for when the check set is non-empty again (today: vacuous)."""
        shop_flags = set(SHOP_ROW_FLAGS.values())
        self.assertTrue(shop_flags, "SHOP_ROW_FLAGS is empty -- shop_data did not generate")
        self.assertTrue(set(DLC_GATED_SHOP_CHECK_FLAGS) <= shop_flags,
                        "a DLC-gated check flag is not a shop check flag at all")
        hub = {int(fl) for (_n, _ap, fl) in LOCATIONS.get("Roundtable Hold", [])}
        stray = sorted(set(DLC_GATED_SHOP_CHECK_FLAGS) - hub)
        self.assertEqual(stray, [],
                         "DLC-gated shop check(s) outside Roundtable Hold: %r -- fine in "
                         "principle (their regions already leave with the DLC) but NEW, so "
                         "say why here" % stray)
