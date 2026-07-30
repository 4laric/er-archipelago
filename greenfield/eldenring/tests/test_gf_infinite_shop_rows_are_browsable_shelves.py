"""INFINITE_SHOP_ROWS must be the browsable unlimited GOODS shelves -- it used to be the opposite.

THE BUG, 2026-07-29. gen_data selected these rows with `eventFlag_forStock == 0`, which is the exact
INVERSE of a shelf, and got 455 rows:

    332  ids 110000-111999, every one mtrlId != -1  -> the ALTER GARMENTS armour-conversion menu
    116  ids 112000-112999, every one costType == 4  -> ASH OF WAR DUPLICATION, priced in
                                                        **Lost Ashes of War**, not runes
      7  debug rows (value 100000, stock flag 0)

Not one is a merchant shelf, and two of those bands back menus a player CAN open -- so the feature
wrote random consumables into Boc's alteration list and the Roundtable duplication list, and wrote
rune-derived prices onto rows denominated in Lost Ashes. Meanwhile every below-value rune price a seed
produced lived somewhere unreachable, which is why a player reported three times that shop runes were
never worth buying and was right for a reason nobody had found (CONTRIBUTING rule 12).

🛑 THE PIN IS A REVIEWED DATUM, NOT A CONVENIENCE. These 14 ids were read off the game's own param and
checked ware by ware. Predicate drift in gen_data AND a vanilla-param refresh both turn this red, and
both deserve a human look -- do not re-baseline it to whatever the generator currently emits.

NO SKIPS. The CSV this reads is committed to the repo, so an absent file is a FAILURE, not a skip: a
gate that skips is the dormant-gate class this project keeps getting bitten by.
"""
import csv
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF = os.path.dirname(os.path.dirname(HERE))            # .../greenfield
REPO = os.path.dirname(GF)
SLP = os.path.join(REPO, "elden_ring_artifacts", "vanilla_er", "vanilla_er", "ShopLineupParam.csv")

# The 14 browsable unlimited goods shelves, with the ware each sells in vanilla.
#   600017/600020/600021/600022 -- seller UNIDENTIFIED (stock flags 220670-220720, no name in
#   flag_names.tsv). They pass every substantive clause, so they are included; do NOT claim in a
#   comment that they are reachable. 600020/600022 sell goods 15390/15210, which are non-AP crafting
#   materials absent from ITEM_CATALOG -- a name lookup on them returns nothing, which is not a bug.
EXPECTED = {
    100104: "Glass Shard (Kale)",
    100225: "Somber Smithing Stone [1] (Iji)",
    100226: "Somber Smithing Stone [2] (Iji)",
    100507: "Throwing Dagger",
    100601: "Kukri",
    100742: "Festering Bloody Finger",
    100801: "Poisonbone Dart",
    100802: "Poisoned Stone",
    100803: "Poisoned Stone Clump",
    100984: "Bloodrose",
    600017: "String (seller unidentified)",
    600020: "goods 15390, crafting material (seller unidentified)",
    600021: "Miranda Powder (seller unidentified)",
    600022: "goods 15210, crafting material (seller unidentified)",
}


def _rows():
    if not os.path.isfile(SLP):
        raise AssertionError(
            "ShopLineupParam.csv missing at %s. It is committed to this repo, so this is a real "
            "failure -- a skip here would make the gate dormant." % SLP)
    with open(SLP, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _i(r, k, d=0):
    try:
        return int(r.get(k) or d)
    except (TypeError, ValueError):
        return d


def _emitted():
    import importlib.util
    path = os.path.join(GF, "eldenring", "shop_stock_data.py")
    spec = importlib.util.spec_from_file_location("_gf_shop_stock_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [int(x) for x in mod.INFINITE_SHOP_ROWS]


class InfiniteShopRows(unittest.TestCase):

    def test_the_emitted_set_is_the_reviewed_fourteen(self):
        got = set(_emitted())
        self.assertEqual(
            got, set(EXPECTED),
            "INFINITE_SHOP_ROWS is not the reviewed shelf set.\n  unexpected: %s\n  missing: %s\n"
            "These 14 were read off the game's param and checked ware by ware. If the predicate or "
            "the params legitimately changed, re-derive and review -- do not re-baseline."
            % (sorted(got - set(EXPECTED)), sorted(set(EXPECTED) - got)))

    def test_re_deriving_from_the_param_reproduces_it(self):
        """Catches a hand-edit to the generated file that the pin alone would not."""
        derived = {_i(r, "ID") for r in _rows()
                   if _i(r, "equipType", 3) == 3 and _i(r, "mtrlId", -1) == -1
                   and _i(r, "costType") == 0 and _i(r, "sellQuantity", -1) == -1
                   and _i(r, "eventFlag_forRelease") == 0 and _i(r, "eventFlag_forStock") > 0
                   and _i(r, "equipId") > 0}
        self.assertEqual(derived, set(_emitted()),
                         "the generated file disagrees with a fresh derivation from the param -- "
                         "someone hand-edited shop_stock_data.py, or gen_data's predicate drifted")

    def test_every_shelf_satisfies_every_clause(self):
        """One mirror per clause. costType is the unit-error gate: a rune-derived price written onto
        a Lost-Ashes-of-War row is the wrong CURRENCY, which is how 116 rows got in."""
        by_id = {_i(r, "ID"): r for r in _rows()}
        for rid in _emitted():
            r = by_id.get(rid)
            self.assertIsNotNone(r, "shelf %d has no vanilla ShopLineupParam row" % rid)
            self.assertEqual(_i(r, "equipType", 3), 3, "shelf %d is not goods" % rid)
            self.assertEqual(_i(r, "mtrlId", -1), -1,
                             "shelf %d consumes a material -- craft/alteration menu, not a shelf" % rid)
            self.assertEqual(_i(r, "costType"), 0,
                             "shelf %d is not rune-priced; a rune-derived price is the wrong unit" % rid)
            self.assertEqual(_i(r, "sellQuantity", -1), -1, "shelf %d is not unlimited" % rid)
            self.assertEqual(_i(r, "eventFlag_forRelease"), 0, "shelf %d is release-gated" % rid)
            self.assertGreater(_i(r, "eventFlag_forStock"), 0,
                               "shelf %d has no stock flag -- that is the OLD inverted predicate" % rid)

    def test_the_alteration_and_duplication_bands_are_excluded(self):
        bad = [r for r in _emitted() if 110000 <= r < 113000]
        self.assertFalse(bad, "the Alter-Garments / AoW-duplication band is back in the set: %s" % bad)

    def test_no_shelf_shares_a_stock_flag_with_a_shop_check(self):
        """Our derivation says qty == -1 cannot be a check. Whether the GAME arms a stock flag on an
        unlimited-stock purchase is UNVERIFIED, so guard the overlap rather than trust it."""
        rows = _rows()
        check_flags = {_i(r, "eventFlag_forStock") for r in rows
                       if _i(r, "eventFlag_forStock") > 0 and _i(r, "sellQuantity", -1) >= 1}
        by_id = {_i(r, "ID"): r for r in rows}
        shelf_flags = {_i(by_id[r], "eventFlag_forStock") for r in _emitted() if r in by_id}
        overlap = sorted(shelf_flags & check_flags)
        self.assertFalse(overlap, "shelf and shop-check share stock flag(s) %s -- a reroll could fire "
                                  "someone's check" % overlap[:5])

    def test_the_minibaker_row_is_not_rerolled(self):
        self.assertNotIn(101801, _emitted(),
                         "101801 is the minibaker's reserved Stonesword Key vendor slot (flag 60290)")

    def test_the_set_is_small_and_non_empty(self):
        n = len(_emitted())
        self.assertTrue(0 < n < 40,
                        "expected a small browsable shelf set, got %d -- an empty result is a "
                        "FAILURE and a large one means the predicate loosened" % n)


if __name__ == "__main__":
    unittest.main()
