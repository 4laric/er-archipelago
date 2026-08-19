"""Finite AP shop-check prices are rolled independently of their rewards.

Every active finite shop check gets one seeded price in [0, 5000], shared by all of its physical
rows. The reward is deliberately not inspected, so the price cannot leak item identity. Separate
rune-datum tests protect the infinite-stock path, where runes must cost their exact payout.
"""
import re

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
    options = {"num_regions": 0, }

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


class RuneDatumTests(WorldTestBase):
    """The predicate is DERIVED (RUNE_PAYOUT = refId_default -> SpEffectParam.soul, sortGroupId 100).

    These are the cases the retired name whitelist got wrong. It matched the 21 base-game money runes
    and missed all eleven DLC ones, and because a miss falls through to GOODS_PRICE = sellValue*10,
    every one of them was priced at TEN TIMES its payout -- through two "10x fixed" commits and three
    player reports.
    """

    game = GAME
    options = {"num_regions": 0, }

    # The retired predicate, kept HERE so it can never silently become production again.
    _LEGACY_RUNE_RE = re.compile(r"^(?:Golden|Hero's|Lord's|Numen's) Rune(?: \[\d+\])?$")

    def test_the_dlc_runes_are_priced_at_their_payout(self):
        """THE MOTIVATING CASE (CONTRIBUTING rule 11), by name. Marika's Rune pays 80000 and was
        charged 800000."""
        for name, payout in (("Shadow Realm Rune [1]", 7500), ("Shadow Realm Rune [7]", 30000),
                             ("Rune of an Unsung Hero", 50000), ("Marika's Rune", 80000),
                             ("Leda's Rune", 40000)):
            full = ITEM_CATALOG.get(name)
            if full is None:
                continue
            self.assertTrue(rp.is_rune(full), "%s is a money rune and must be priced as one" % name)
            self.assertEqual(rp.rune_worth(full), payout, name)

    def test_everything_the_old_whitelist_matched_is_still_a_rune(self):
        """No regression: the datum must be a SUPERSET of the names the regex used to catch."""
        matched = [n for n in ITEM_CATALOG if self._LEGACY_RUNE_RE.match(n)]
        self.assertGreater(len(matched), 15, "the base-game rune names have gone from the catalog")
        for n in matched:
            self.assertTrue(rp.is_rune_item(n),
                            "%s was priced by the old whitelist and is not by the datum" % n)

    def test_the_datum_is_strictly_wider_than_the_whitelist(self):
        """And it must be a STRICT superset -- if this ever equalises, the DLC join has broken."""
        datum = {n for n in ITEM_CATALOG if rp.is_rune_item(n)}
        legacy = {n for n in ITEM_CATALOG if self._LEGACY_RUNE_RE.match(n)}
        self.assertTrue(legacy < datum,
                        "the derived rune set is no wider than the retired name whitelist: %r"
                        % sorted(datum - legacy)[:5])

    def test_remembrances_are_not_money(self):
        """Remembrances are soul-granting (20000-50000) and must NOT be repriced: one is worth the
        weapon you trade it for, not its rune value. sortGroupId is what separates them."""
        for n in ITEM_CATALOG:
            if "Remembrance" in n:
                self.assertFalse(rp.is_rune_item(n), n)

    def test_the_two_derivations_still_agree(self):
        """soul (the datum) vs GOODS_PRICE // 10 (the retired inference). Independent chains; if they
        stop agreeing, this names which rune moved instead of silently repricing it."""
        checked = 0
        for row, payout in rp.RUNE_PAYOUT.items():
            price = GOODS_PRICE.get(row)
            if not price:
                continue
            checked += 1
            self.assertEqual(price // rp.GOODS_PRICE_MARKUP, payout,
                             "goods %d: GOODS_PRICE//%d = %d but SpEffectParam.soul = %d"
                             % (row, rp.GOODS_PRICE_MARKUP, price // rp.GOODS_PRICE_MARKUP, payout))
        self.assertGreater(checked, 25, "the RUNE_PAYOUT/GOODS_PRICE join has drifted")


class _StubLoc:
    def __init__(self, address):
        self.address = address


class FiniteShopPricingRolls(WorldTestBase):
    """Drive the feature with explicit active checks so every assertion enters the pricing branch."""

    game = GAME
    options = {"num_regions": 6}

    def _emit(self, aids, seed=189):
        w = self.world
        locs = [_StubLoc(int(a)) for a in aids]
        orig = w.multiworld.get_locations
        orig_seed = w.multiworld.seed
        w.multiworld.get_locations = lambda player=None: locs
        w.multiworld.seed = seed
        try:
            return rp.RunePricing().slot_data(w)["shopRunePrices"]
        finally:
            w.multiworld.get_locations = orig
            w.multiworld.seed = orig_seed

    def _shop_ap_ids(self, count=2):
        _fixed, alt_ids = rp.fixed_alt_currency_prices()
        ids = [a for a in sorted(SHOP_ROW_FLAGS, key=int)
               if SHOP_ROW_IDS.get(a) and a not in alt_ids]
        self.assertGreaterEqual(len(ids), count, "not enough finite rune-priced shop checks")
        return ids[:count]

    def _fixed_prices(self):
        return rp.fixed_alt_currency_prices()[0]

    def test_every_active_finite_check_gets_one_price_for_all_its_rows(self):
        aids = self._shop_ap_ids()
        out = self._emit(aids)
        rows = {str(r) for aid in aids for r in SHOP_ROW_IDS[aid]}
        expected = set(self._fixed_prices()) | rows
        self.assertEqual(set(out), expected,
                         "finite rows plus every unconditional altar row must be present")
        for aid in aids:
            values = {out[str(r)] for r in SHOP_ROW_IDS[aid]}
            self.assertEqual(len(values), 1, "all rows of one AP check must share its price")
            price = values.pop()
            self.assertGreaterEqual(price, 0)
            self.assertLessEqual(price, rp.FINITE_PRICE_MAX)

    def test_roll_is_seeded_and_independent_of_location_iteration_order(self):
        aids = self._shop_ap_ids(3)
        self.assertEqual(self._emit(aids, 4242), self._emit(reversed(aids), 4242))
        self.assertNotEqual(self._emit(aids, 4242), self._emit(aids, 4243))

    def test_alt_currency_rows_stay_at_one(self):
        fixed = self._fixed_prices()
        self.assertTrue(fixed, "the generated alternate-currency row set is empty")
        out = self._emit(self._shop_ap_ids(1))
        self.assertEqual({row: out[row] for row in fixed}, fixed)
        self.assertEqual(set(fixed.values()), {1})


def test_finite_shop_pricing_is_behavior_not_a_yaml_option():
    from worlds.eldenring.defaults import FROZEN_OPTIONS
    assert not rp.RunePricing.OPTIONS
    assert "rune_shop_pricing" not in FROZEN_OPTIONS
