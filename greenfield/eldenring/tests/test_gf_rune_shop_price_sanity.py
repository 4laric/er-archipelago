"""A rune must never be sold for more than it pays out -- on EITHER pricing path.

THE BUG, reported by Alaric 2026-07-29: "rune pricing is bugged, i have never seen a single rune
priced below its value ... nothing remotely close to the 0 end."

There are TWO paths that put a price on a shop slot and only one of them knew about runes:

  * features/rune_pricing prices shop CHECKS holding a rune. Innocent -- measured over 3 seeds /
    350 slots it is a clean uniform [0, 2x worth]: median ratio 1.03, 50% below worth, 5% below
    0.10x, minimum 0.002x.
  * features/shop_stock rerolls INFINITE-STOCK slots and priced every roll at GOODS_PRICE. For a
    consumable that is the vanilla shop price and is exactly right. For a rune GOODS_PRICE is
    `sellValue * 10` and a rune's sellValue IS its payout -- so a Golden Rune [5] cost 16,000 for
    1,600 runes. Ten times value, every rune, every seed.

🛑 THE SECOND PATH IS THE BIGGER ONE: ~455 rerolled slots against ~113 priced checks, at the
unlimited-stock merchants a player returns to. The correct feature was measured and blamed while the
one nobody thought about did the damage -- so this test walks BOTH and asserts on the ratio, not on
either implementation.
"""
import statistics

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.rune_pricing import is_rune_item, rune_worth, PRICE_MULT  # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring"
_GOODS = 0x40000000
_NAME_OF = {v: k for k, v in ITEM_CATALOG.items()}


def _infinite_stock_rune_ratios(seed):
    class _T(WorldTestBase):
        game = GAME
        options = {"reroll_infinite_shop_stock": True}
    t = _T("runTest")
    t.options = {"reroll_infinite_shop_stock": True}
    t.world_setup(seed)
    roll = t.world.fill_slot_data().get("shopInfiniteStock") or {}
    out = []
    for _row, entry in roll.items():
        gid = entry[0]
        price = entry[2]
        full = gid | _GOODS
        if not is_rune_item(_NAME_OF.get(full, "")):
            continue
        worth = rune_worth(full)
        if worth:
            out.append(price / worth)
    return out


def test_infinite_stock_runes_are_not_priced_at_ten_times_value():
    """THE regression. A flat 10.0x on every rune is what shipped."""
    ratios = sorted(r for s in (4242, 777) for r in _infinite_stock_rune_ratios(s))
    assert ratios, ("no rune landed in an infinite-stock slot across two seeds -- this test then "
                    "proves nothing. If the roster changed, re-derive it rather than deleting this.")
    assert max(ratios) <= PRICE_MULT + 0.01, (
        "an infinite-stock rune costs %.2fx its payout; the roll is capped at %dx. A flat 10.0x here "
        "is the GOODS_PRICE bug returning -- GOODS_PRICE is sellValue*10 and for a rune sellValue IS "
        "the payout." % (max(ratios), PRICE_MULT))


def test_the_roll_actually_reaches_the_cheap_end():
    """Alaric's actual complaint: not just 'too expensive' but 'never anywhere near 0'.

    A uniform [0, 2x] should put ~half below worth. Asserting the SHAPE catches a future change that
    keeps the cap but skews the distribution -- which would still read as 'runes are never a deal'."""
    ratios = sorted(r for s in (4242, 777, 31337) for r in _infinite_stock_rune_ratios(s))
    below = sum(1 for r in ratios if r < 1.0)
    assert 0.30 <= below / len(ratios) <= 0.70, (
        "only %.0f%% of infinite-stock runes are priced below their payout (n=%d). A uniform "
        "[0, 2x worth] roll should be near 50%%; a skew here means runes are never worth buying, "
        "which is the complaint that started this." % (100 * below / len(ratios), len(ratios)))
    assert min(ratios) < 0.25, (
        "the cheapest rune across three seeds is %.2fx its payout -- the roll never reaches the "
        "cheap end, so it is not really a gamble." % min(ratios))


def test_both_pricing_paths_agree_on_what_a_rune_is_worth():
    """The two paths must divide out the same 10x, or one of them reprices every rune by an order
    of magnitude while the other looks fine."""
    from worlds.eldenring.shop_stock_data import GOODS_PRICE
    checked = 0
    for name, full in ITEM_CATALOG.items():
        if not is_rune_item(name) or (full & 0xF0000000) != _GOODS:
            continue
        raw = GOODS_PRICE.get(full & 0x0FFFFFFF)
        worth = rune_worth(full)
        if not (raw and worth):
            continue
        checked += 1
        assert raw == worth * 10, (
            "%s: GOODS_PRICE %d is not 10x rune_worth %d. The markup this whole fix divides out has "
            "changed; re-derive it before trusting either path." % (name, raw, worth))
    assert checked >= 10, "checked only %d runes -- the catalog join broke" % checked
