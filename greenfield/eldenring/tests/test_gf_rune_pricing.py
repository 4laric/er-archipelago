"""Rune shop prices are ROLLED, not inherited.

A shop check keeps the price of the ware it used to sell (`shop_sell` rewrites equipId and leaves
`value` alone -- correct for gear, wrong for money). A slot that cost 3500 selling a Golden Rune [1]
worth 2000 is not a gamble, it is a slot nobody presses, and the check behind it never gets
collected. features/rune_pricing rolls those into [0, 2x the rune's own worth].
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.features import rune_pricing as rp  # noqa: E402
from worlds.eldenring.shop_data import SHOP_ROW_FLAGS, SHOP_ROW_IDS  # noqa: E402
from worlds.eldenring.shop_stock_data import GOODS_PRICE  # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring"
_ROW_MASK = 0x0FFFFFFF


class RuneNameTests(WorldTestBase):
    game = GAME
    options = {}

    def test_the_rune_family_matches(self):
        for n in ("Golden Rune [1]", "Golden Rune [13]", "Hero's Rune [3]",
                  "Lord's Rune", "Numen's Rune"):
            self.assertTrue(rp.is_rune_item(n), n)

    def test_things_that_merely_say_rune_do_not(self):
        """`Rune Arc` and the Great Runes are not money -- repricing them would be a different
        feature wearing this one's clothes."""
        for n in ("Rune Arc", "Godrick's Great Rune", "Great Rune of the Unborn",
                  "Rune Factory", "", None):
            self.assertFalse(rp.is_rune_item(n), repr(n))

    def test_the_payout_ladder_is_what_worth_means(self):
        """The load-bearing assumption, pinned: GOODS_PRICE is a MERCHANT price and a rune's is a 10x
        markup over its payout, so the roll must be relative to `GOODS_PRICE // 10`.

        Priced off the raw GOODS_PRICE, a Golden Rune [10] -- 5000 runes -- cost up to 125000 (Alaric,
        playtest 2026-07-25). This asserts the divisor against the published payout ladder, so if
        gen_data's price derivation ever changes, this fails loudly instead of silently repricing
        every rune slot by 10x."""
        ladder = [200, 400, 800, 1200, 1600, 2000, 2500, 3000, 3800, 5000, 6250, 7500, 10000]
        seen = 0
        for i, want in enumerate(ladder, start=1):
            full = ITEM_CATALOG.get("Golden Rune [%d]" % i)
            if full is None:
                continue
            seen += 1
            self.assertEqual(
                rp.rune_worth(full), want,
                "Golden Rune [%d] worth %r, expected its %d-rune payout. GOODS_PRICE // %d no longer "
                "reproduces the ladder -- the markup assumption has broken."
                % (i, rp.rune_worth(full), want, rp.GOODS_PRICE_MARKUP))
        self.assertGreaterEqual(seen, 10, "the Golden Rune ladder is missing from the catalog")

    def test_the_runes_are_actually_priceable(self):
        """The roll needs GOODS_PRICE to know the rune's worth. If the catalog and the price table
        stop overlapping this feature silently does nothing, so assert the join instead."""
        runes = [n for n in ITEM_CATALOG if rp.is_rune_item(n)]
        self.assertGreater(len(runes), 5, "no rune items in the catalog -- the join has drifted")
        priced = [n for n in runes if rp.rune_worth(ITEM_CATALOG[n])]
        self.assertGreater(
            len(priced), 5,
            "rune items exist but none has a derived worth in GOODS_PRICE, so every roll would be "
            "skipped and the feature would be inert: %r" % runes[:6])


class _StubItem:
    def __init__(self, name, player):
        self.name, self.player = name, player


class _StubLoc:
    def __init__(self, address, item):
        self.address, self.item = address, item


class RunePricingRolls(WorldTestBase):
    """Driven with stubbed placements: in a solo WorldTestBase world almost nothing is placed at
    fill_slot_data time, so a seed-driven assertion here would pass without entering the branch."""

    game = GAME
    options = {"num_regions": 6, "num_regions_order": "spine"}

    def _emit(self, placements):
        w = self.world
        locs = [_StubLoc(int(a), _StubItem(nm, pl)) for a, (nm, pl) in placements.items()]
        orig = w.multiworld.get_locations
        w.multiworld.get_locations = lambda player=None: locs
        try:
            return w.fill_slot_data().get("shopRunePrices", {})
        finally:
            w.multiworld.get_locations = orig

    def _a_shop_ap_id(self):
        ids = [a for a in sorted(SHOP_ROW_FLAGS, key=int) if SHOP_ROW_IDS.get(a)]
        self.assertTrue(ids, "no shop check has a ShopLineupParam row to reprice")
        return ids[0]

    def _a_rune(self):
        for n in sorted(ITEM_CATALOG):
            if rp.is_rune_item(n) and rp.rune_worth(ITEM_CATALOG[n]):
                return n, rp.rune_worth(ITEM_CATALOG[n])
        self.skipTest("no priceable rune in the catalog")

    def test_a_rune_reward_reprices_every_row_of_its_slot(self):
        aid = self._a_shop_ap_id()
        name, worth = self._a_rune()
        out = self._emit({aid: (name, self.world.player)})
        rows = [str(r) for r in SHOP_ROW_IDS[aid]]
        self.assertEqual(sorted(out), sorted(rows),
                         "every ShopLineupParam row behind the check must be repriced, not just one")
        for r in rows:
            self.assertGreaterEqual(out[r], 0)
            self.assertLessEqual(out[r], rp.PRICE_MULT * worth,
                                 "roll must stay within [0, %dx worth]" % rp.PRICE_MULT)

    def test_a_non_rune_reward_is_left_alone(self):
        """THE REGRESSION GUARD. Repricing gear would silently rewrite the whole shop economy."""
        aid = self._a_shop_ap_id()
        gear = next(n for n in sorted(ITEM_CATALOG) if not rp.is_rune_item(n))
        self.assertEqual(self._emit({aid: (gear, self.world.player)}), {})

    def test_a_foreign_reward_is_left_alone(self):
        """A foreign reward is not sold natively -- its slot shows a placeholder, and repricing it
        would leak which foreign slots hold runes."""
        aid = self._a_shop_ap_id()
        name, _ = self._a_rune()
        self.assertEqual(self._emit({aid: (name, self.world.player + 1)}), {})
