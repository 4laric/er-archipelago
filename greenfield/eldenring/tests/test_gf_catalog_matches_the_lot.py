"""A check's item is what ITS OWN LOT awards, not what its name resolves to (er-archipelago#682).

MOTIVATING CASE. Alaric, 2026-08-14, stood at vanilla's capital gate holding two Great Runes and it
would not open. Two goods rows share each rune's name:

    GoodsName  191 = "Godrick's Great Rune"     GoodsName 8148 = "Godrick's Great Rune"
    lot 10010     -> goods 8148  flag 171        <- Godrick DROPS this one
    lot 34100500  -> goods 191   flag 191        <- the Divine Tower RESTORE awards this one

`ITEM_CATALOG` is name-keyed and the FMG walk is ascending, so we shipped 191 for the check at flag
171 -- and 191 does not carry `enable_ActiveBigRune`, so the gate never counted it.

🛑 IT WAS INVISIBLE FOUR WAYS, which is why this test exists rather than a comment: the blessing menu
accepts 191 (`goodsType 15`) so the rune lists and equips; `keyitems` sets its restored flag; and
`goal.rs` matches the great_runes ending on item NAMES. Nothing we had could see it.

🛑 A GLOBAL TIE-BREAK CANNOT FIX THIS and must not be reintroduced: BOTH rows are awarded by a real
lot, so "prefer the awarded row" has nothing to choose between. Only the check's OWN flag does.

Run:  python greenfield/eldenring/tests/test_gf_catalog_matches_the_lot.py
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)
GREENFIELD = os.path.dirname(GF_PKG)


def _load(name):
    spec = importlib.util.spec_from_file_location(
        "gf_" + name + "_lotcheck", os.path.join(GF_PKG, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ITEM_CATALOG = _load("item_ids").ITEM_CATALOG
GOODS = 0x40000000

# flag -> [goods id] from flag_lots.tsv (col 0 flag, col 5 item id, col 3 category==1 is goods).
# Resolve the tsv from either the source tree or the installed package, the way the sweep oracle does.
_TSV = next((p for p in (os.path.join(GF_PKG, "flag_lots.tsv"),
                         os.path.join(GREENFIELD, "flag_lots.tsv")) if os.path.isfile(p)), None)


def _lot_goods_by_flag():
    out = {}
    if not _TSV:
        return out
    with open(_TSV, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 6 or not p[0].isdigit():
                continue
            if p[3] != "1" or not p[5].isdigit():   # category 1 == goods
                continue
            out.setdefault(int(p[0]), []).append(int(p[5]))
    return out


LOT_GOODS = _lot_goods_by_flag()

# The six shardbearer runes: check flag -> the goods its boss actually drops.
RUNE_FLAG_TO_GOODS = {171: 8148, 172: 8149, 173: 8150, 174: 8151, 175: 8152, 176: 8153}
RUNE_NAMES = {
    171: "Godrick's Great Rune", 172: "Radahn's Great Rune", 173: "Morgott's Great Rune",
    174: "Rykard's Great Rune", 175: "Mohg's Great Rune", 176: "Malenia's Great Rune",
}


class TestCatalogMatchesTheLot(unittest.TestCase):

    def setUp(self):
        if not LOT_GOODS:
            self.skipTest("flag_lots.tsv not present beside the package")

    def test_every_great_rune_resolves_to_the_row_its_boss_drops(self):
        """THE MOTIVATING CASE. Red before #682: all six resolved to 191-196."""
        for flag, goods in sorted(RUNE_FLAG_TO_GOODS.items()):
            name = RUNE_NAMES[flag]
            if name not in ITEM_CATALOG:
                continue          # a rune absent from this build's catalog is not this test's business
            self.assertEqual(
                ITEM_CATALOG[name], GOODS | goods,
                f"{name} must resolve to goods {goods} (what flag {flag}'s lot awards), "
                f"not {ITEM_CATALOG[name] - GOODS}")

    def test_no_great_rune_resolves_into_the_restored_band(self):
        """🛑 The specific wrong answer, pinned by value. 191-196 are the DIVINE TOWER's rows -- they
        are real items with a real lot, which is exactly why no general rule excludes them."""
        for name in RUNE_NAMES.values():
            if name in ITEM_CATALOG:
                self.assertNotIn(ITEM_CATALOG[name] - GOODS, range(191, 197),
                                 f"{name} resolved to the restore row again")

    def test_every_catalogued_rune_name_is_a_row_some_lot_awards(self):
        """The structural half: a name must resolve to an id the game actually HANDS OUT.

        A catalog entry pointing at a row nothing awards is an item we can promise and never
        deliver, which is the whole shape of #682 stated without naming a specific rune."""
        awarded = {g for gs in LOT_GOODS.values() for g in gs}
        self.assertTrue(awarded, "fixture check: flag_lots parsed no goods")
        for name in RUNE_NAMES.values():
            if name in ITEM_CATALOG:
                self.assertIn(ITEM_CATALOG[name] - GOODS, awarded,
                              f"{name} resolves to a goods row no lot awards")

    def test_the_control_is_untouched(self):
        """⭐ `Great Rune of the Unborn` has no duplicate-named row, so it always resolved right --
        the control that proves this was a name collision and not rune handling. If the fix ever
        moves it, the fix has become a rune carve-out."""
        if "Great Rune of the Unborn" in ITEM_CATALOG:
            self.assertEqual(ITEM_CATALOG["Great Rune of the Unborn"] - GOODS, 10080)


if __name__ == "__main__":
    unittest.main()
