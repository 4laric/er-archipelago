"""ShopSlot pin invariants: per MERCHANT, at most one progression-eligible shop slot, pinned to a
ware only that merchant sells in the field -- and every unpinned merchant is skipped VISIBLY.

Model (reworked 2026-07-24). A merchant enters the progression pool at most once. The old unit was
the ShopLineupParam 100-block and the old uniqueness test was "this ware is sold under exactly one
stock flag game-wide"; both were proxies and both were wrong. merchant_shops.tsv (talk ESD
`OpenRegularShop`) says which NPC opens which row, and under the old test 8 of 10 pins were sold by
2-7 merchants apiece -- one was filed in a region no seller stands in.

Three corrections encoded here:
  * MERCHANT := talk_id, not the 100-block. The block is not a merchant (merchant_shops.tsv's own
    header exists to say so).
  * The HUB MIRROR does not create ambiguity. The Twin Maiden Husks (m11_10) re-sell a merchant's
    stock once you hand in that merchant's BELL BEARING, which you get by killing them -- so the hub
    copy is never an alternative EARLY route. Counting it leaves ~zero pinnable checks; discounting
    it leaves 181.
  * A pin must be able to HOLD progression: not release-gated, not region-DEFAULTED, not MISSABLE
    (which now includes every alt-currency shop row, costType != 0 -- the Dragon Communion altars).

Ground truth: greenfield/shop_rows.tsv + greenfield/merchant_shops.tsv, both REQUIRED_INPUTS copied
into the installed world by tools/gf_test.py. No hand lists.
"""
import collections
import os
import unittest

from ..location_tags import (LOCATION_TAGS, SHOP_SLOT_PINS, SHOP_SLOT_SKIPS,
                             DEFAULTED_REGION_APS, SHOP_RELEASE_GATED_APS)
from ..missable_locations import MISSABLE_LOCATIONS
from ..shop_data import SHOP_ROW_IDS

_HERE = os.path.dirname(os.path.abspath(__file__))
_GF_PKG = os.path.dirname(_HERE)
_GREENFIELD = os.path.dirname(_GF_PKG)
_HUB_TILE = "m11_10"


def _input(name):
    for base in (_GF_PKG, _GREENFIELD):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    return None


def _tsv(path, skip_prefixes=("#", "row_id", "talk_id")):
    out = []
    with open(path, encoding="utf-8-sig") as fh:
        for ln in fh:
            if not ln.strip() or ln.startswith(skip_prefixes):
                continue
            out.append(ln.rstrip("\n").split("\t"))
    return out


def _sellers():
    """(flag -> {talk_id opening a row with it}, talk_id -> {map_id})."""
    sp, mp = _input("shop_rows.tsv"), _input("merchant_shops.tsv")
    if not (sp and mp):
        return None, None
    row2flag = {}
    for q in _tsv(sp):
        if len(q) >= 6 and q[0].isdigit() and q[5].isdigit():
            row2flag[int(q[0])] = int(q[5])
    f2t, t2m = collections.defaultdict(set), collections.defaultdict(set)
    for q in _tsv(mp):
        if len(q) < 5 or not q[0].isdigit():
            continue
        fl = row2flag.get(int(q[0]))
        if fl is None:
            continue
        f2t[fl].add(q[1])
        if q[4].strip():
            t2m[q[1]].add(q[4].strip())
    return f2t, t2m


def _shop_slot_aps():
    return {ap for ap, tags in LOCATION_TAGS.items() if "ShopSlot" in tags}


class ShopSlotPins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f2t, cls.t2m = _sellers()
        if cls.f2t is None:
            raise unittest.SkipTest("shop_rows.tsv / merchant_shops.tsv not resolvable")
        # ap -> stock flag, via its first shop row
        cls.flag_of = {}
        row2flag = {}
        for q in _tsv(_input("shop_rows.tsv")):
            if len(q) >= 6 and q[0].isdigit() and q[5].isdigit():
                row2flag[int(q[0])] = int(q[5])
        for ap, rows in SHOP_ROW_IDS.items():
            if rows:
                cls.flag_of[int(ap)] = row2flag.get(rows[0])

    def _field_openers(self, flag):
        return {t for t in self.f2t.get(flag, ())
                if any(m != _HUB_TILE for m in self.t2m.get(t, ()))}

    def test_pins_exist(self):
        """Rule 2: an empty result is a FAILURE. gen_data FATALs on zero; assert it here too."""
        self.assertTrue(SHOP_SLOT_PINS, "ZERO ShopSlot pins -- the shop class fell off the surface")

    def test_tagged_aps_match_the_pin_table(self):
        self.assertEqual(_shop_slot_aps(), set(SHOP_SLOT_PINS.values()),
                         "ShopSlot-tagged ap ids != SHOP_SLOT_PINS values")
        self.assertEqual(len(SHOP_SLOT_PINS), len(set(SHOP_SLOT_PINS.values())),
                         "an ap id is pinned for two merchants")

    def test_every_pin_has_exactly_one_FIELD_seller_and_it_is_its_key(self):
        """THE CAP, restated on the real unit: the pinned ware must be sold by exactly one merchant
        outside the hub, and that merchant must be the talk_id it is filed under."""
        bad = []
        for talk, ap in sorted(SHOP_SLOT_PINS.items()):
            flag = self.flag_of.get(ap)
            if flag is None:
                bad.append((talk, ap, "no shop row / stock flag"))
                continue
            field = self._field_openers(flag)
            if field != {str(talk)}:
                bad.append((talk, ap, "field sellers = %s" % sorted(field)))
        self.assertEqual(bad, [], "pin(s) whose field-seller set is not exactly their merchant: %r"
                                  % bad[:5])

    def test_pins_are_not_dead(self):
        """A pin must be able to HOLD progression: not release-gated, not DEFAULTED, not missable."""
        pinned = set(SHOP_SLOT_PINS.values())
        self.assertEqual(set(), pinned & set(SHOP_RELEASE_GATED_APS),
                         "a ShopSlot pin is release-gated -- eligible in name, barred in fill")
        self.assertEqual(set(), pinned & set(DEFAULTED_REGION_APS),
                         "a ShopSlot pin has a GUESSED region -- eligible in name, barred in fill")
        self.assertEqual(set(), pinned & set(MISSABLE_LOCATIONS),
                         "a ShopSlot pin is MISSABLE (alt-currency shop / limited consumable) -- "
                         "progression placed there can be spent away")

    def test_pins_and_skips_are_disjoint_and_reasoned(self):
        self.assertEqual(set(), set(SHOP_SLOT_PINS) & set(SHOP_SLOT_SKIPS),
                         "a merchant is both pinned and skipped")
        for talk, why in SHOP_SLOT_SKIPS.items():
            self.assertTrue(isinstance(why, str) and why.strip(),
                            f"skipped merchant {talk} has no reason -- skips must be LOUD")

    def test_pin_keys_are_real_merchants(self):
        known = {t for ts in self.f2t.values() for t in ts}
        unknown = [t for t in SHOP_SLOT_PINS if str(t) not in known]
        self.assertEqual(unknown, [], "pin key(s) are not talk ESD ids from merchant_shops.tsv: %r"
                                      % unknown[:5])


if __name__ == "__main__":
    unittest.main()
