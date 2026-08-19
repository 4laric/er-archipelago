"""Infinite-stock money runes cost exactly their payout.

Finite AP checks intentionally roll an unrelated 0--5000 price, so a valuable rune can create a fun
one-shot flip. Applying that rule to an unlimited shelf would create an infinite money loop. The
infinite-stock path therefore uses the game-authored payout as both price and value.
"""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.rune_pricing import is_rune_item, rune_worth  # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402

GAME = "Elden Ring"
_GOODS = 0x40000000
_NAME_OF = {v: k for k, v in ITEM_CATALOG.items()}


def _direct_rune_ratios(seed, draws=50):
    """Call `shop_stock._price_for` DIRECTLY over every rune in the catalog.

    🛑 WHY NOT VIA A GENERATED SEED. The shelf set went from 455 rows to 14 on 2026-07-29, so a pinned
    seed can easily draw ZERO runes -- and then the e2e assertions below would pass while testing
    nothing, which is the dormant-gate class this project keeps getting bitten by. Calling the guard
    directly with synthetic input is the house rule for exactly this
    ([[guard-absent-from-corpus-needs-a-direct-call]]): it exercises the rune BRANCH regardless of
    what any seed happens to roll.
    """
    import random
    from worlds.eldenring.features import shop_stock
    from worlds.eldenring.shop_stock_data import RUNE_PAYOUT
    rng = random.Random(seed)
    out = []
    # 🛑 ITERATE THE DATUM, NOT THE PREDICATE. This loop used to walk ITEM_CATALOG and `continue` on
    # `not is_rune_item(name)` -- so it measured only the runes the predicate already accepted and
    # was blind, by construction, to the eleven it rejected. Those eleven were the bug. A test that
    # asks the suspect to select its own evidence is green for the same reason the bug survived.
    for row, w in sorted(RUNE_PAYOUT.items()):
        for _ in range(draws):
            out.append(shop_stock._price_for(row, rng) / w)
    return out


def _infinite_stock_rune_ratios(seed):
    class _T(WorldTestBase):
        game = GAME
        options = {"num_regions": 0, "reroll_infinite_shop_stock": True}
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


def test_infinite_stock_runes_cost_exactly_their_payout():
    """Neither the old 10x markup nor the finite-shop bargain roll may reach this path."""
    ratios = sorted(_direct_rune_ratios(4242) + _direct_rune_ratios(777))
    assert ratios, ("no rune in ITEM_CATALOG has a GOODS_PRICE entry -- the join broke and this test "
                    "proves nothing. Re-derive it rather than deleting this.")
    assert set(ratios) == {1.0}, (
        "infinite-stock rune price/payout ratios must all be 1.0, got %r; below 1 is an unlimited "
        "money loop and 10 is the retired GOODS_PRICE markup" % sorted(set(ratios)))


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
