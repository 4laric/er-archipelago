"""`infinite_hub_wares` stocks what it names, on the rows it names, and rejects what it cannot do.

Requested on Nexus (2026-07-29): an option for infinite Rune Arcs and Larval Tears at a shop you can
reach from the start. Both wares were already in the reroll pool, so the ask is determinism. The rows
used are already `sellQuantity -1`, so the existing shopInfiniteStock wire carries them with no
client change and no new contract key (a new key moves CONTRACT_HASH and forces a client update on
every player).

THE THREE PROPERTIES WORTH PINNING:

  1. Every hub row must BE a shelf. A pin on a row the generator no longer emits is a silent no-op --
     the dormant-gate class -- so it raises instead.
  2. Naming a ware must change EXACTLY the rows it lands on. The draw is consumed even for a pinned
     row precisely so the rng stream does not shift; without that, asking for one ware would quietly
     re-roll every other shelf.
  3. An impossible request is REJECTED, loudly and specifically -- too many wares, an unknown name, a
     non-good, an unpriced good. Silently dropping the extras is the failure this option would
     otherwise ship: a player asks for four things, gets three, and nothing says so.
"""
import pytest

pytest.importorskip("worlds.eldenring")
from Options import OptionError  # noqa: E402
from worlds.eldenring.features import shop_stock as ss  # noqa: E402
from worlds.eldenring.shop_stock_data import INFINITE_SHOP_ROWS, GOODS_PRICE  # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG  # noqa: E402
from worlds.eldenring import contract  # noqa: E402

_GOODS = 0x40000000
_MASK = 0x0FFFFFFF


def _gid(name):
    return ITEM_CATALOG[name] & _MASK


class _Opt:
    def __init__(self, value):
        self.value = value


class _MW:
    seed = 20260730


class _World:
    """The attributes features/shop_stock actually reads. A stub keeps the seed FIXED across the
    with/without comparison, which is the whole point of test_wares_change_exactly_their_own_rows."""

    def __init__(self, wares=()):
        self.multiworld = _MW()
        self.player = 1
        self.options = type("O", (), {
            "reroll_infinite_shop_stock": _Opt(1),
            "infinite_hub_wares": _Opt(set(wares)),
        })()


def _roll(wares=()):
    return ss.ShopStockFeature().slot_data(_World(wares))[contract.SHOP_INFINITE_STOCK]


def test_every_hub_row_is_actually_a_shelf():
    """Property 1. If the shelf derivation moves, this says so instead of the option going quiet."""
    for row in ss.HUB_SHELF_ROWS:
        assert row in INFINITE_SHOP_ROWS, (
            "hub row %d is not among the %d browsable shelves, so a ware placed there would vanish"
            % (row, len(INFINITE_SHOP_ROWS)))


def test_the_default_is_empty_and_changes_nothing():
    assert ss.InfiniteHubWares.default == frozenset()
    assert _roll() == _roll(())


def test_the_requested_wares_are_priceable_goods():
    """The two the request was actually about, by name (CONTRIBUTING rule 11)."""
    for ware in ("Rune Arc", "Larval Tear"):
        full = ITEM_CATALOG.get(ware)
        assert full is not None and (full & ~_MASK) == _GOODS, "%r is not a good" % ware
        assert (full & _MASK) in GOODS_PRICE, "%r has no derived price" % ware


@pytest.mark.parametrize("wares", [("Rune Arc",), ("Rune Arc", "Larval Tear")])
def test_wares_change_exactly_their_own_rows(wares):
    """Property 2, and the reason the draw is consumed on both sides of the override."""
    off = _roll()
    on = _roll(wares)
    changed = {k for k in on if on[k] != off[k]}
    expected = {str(r) for r in ss.HUB_SHELF_ROWS[:len(wares)]}
    assert changed == expected, (
        "asking for %r changed %r, expected %r -- a ware must not disturb the other shelves"
        % (list(wares), sorted(changed), sorted(expected)))
    for row, ware in zip(ss.HUB_SHELF_ROWS, sorted(wares)):
        assert on[str(row)] == [_gid(ware), 3, GOODS_PRICE[_gid(ware)]], (
            "shelf %d should carry %s at its derived price, got %r" % (row, ware, on[str(row)]))


def test_the_assignment_is_deterministic():
    """Sets are unordered; the row a ware lands on must not be."""
    a = _roll(("Rune Arc", "Larval Tear"))
    b = _roll(("Larval Tear", "Rune Arc"))
    assert a == b


def test_the_least_valuable_rows_are_spent_first():
    """600020 and 600022 sell unnamed crafting materials; 600021 and 600017 sell real craftables. One
    ware must cost the player nothing at all."""
    assert ss.HUB_SHELF_ROWS[:2] == (600020, 600022)


def test_too_many_wares_is_REJECTED_not_truncated():
    """Property 3. Silently dropping the extras is the bug this option would otherwise ship."""
    five = ("Rune Arc", "Larval Tear", "Golden Rune [1]", "Smithing Stone [1]", "Grace Mimic")
    with pytest.raises(OptionError) as e:
        _roll(five)
    msg = str(e.value)
    assert "infinite_hub_wares" in msg and str(len(ss.HUB_SHELF_ROWS)) in msg, (
        "the rejection must name the option and the number of shelves: %r" % msg)


def test_an_unknown_name_is_rejected():
    with pytest.raises(OptionError) as e:
        _roll(("Rune Arcs",))          # plural: the exact typo a player will make
    assert "Rune Arcs" in str(e.value)


def test_a_non_goods_ware_is_rejected():
    weapon = next((n for n, f in ITEM_CATALOG.items() if (f & ~_MASK) != _GOODS), None)
    if weapon is None:
        pytest.skip("no non-goods item in the catalog")
    with pytest.raises(OptionError):
        _roll((weapon,))


def test_an_unpriced_good_is_rejected():
    unpriced = next((n for n, f in ITEM_CATALOG.items()
                     if (f & ~_MASK) == _GOODS and (f & _MASK) not in GOODS_PRICE), None)
    if unpriced is None:
        pytest.skip("every catalog good has a derived price")
    with pytest.raises(OptionError):
        _roll((unpriced,))


def test_a_hub_row_that_is_not_a_shelf_RAISES(monkeypatch):
    """Mutation-proof for property 1: break the row and the guard must fire, not shrug."""
    monkeypatch.setattr(ss, "HUB_SHELF_ROWS", (999999,))
    with pytest.raises(OptionError):
        _roll(("Rune Arc",))
