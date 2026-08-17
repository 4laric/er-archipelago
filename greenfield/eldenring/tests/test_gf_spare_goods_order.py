"""The spare preview pool must spend DESCRIBABLE rows first.

THE BUG, seen in game 2026-07-29: a shop slot showed the AP flower and the right name, and
`?GoodsInfo?` where the description belongs. The client had already said why --

    FMG extend-swap(cat 20): 10 of 12 id(s) are in NO vanilla group, so they have no string slot
    to redirect and CANNOT be named here -- they will render as `?GoodsName?` in game
    shop-preview: ... -> extend-swap names=12 infos=2 captions=2

`extend_swap_overrides` REDIRECTS the string slot of an id that already lives in a vanilla FMG
group. GoodsName (cat 10) covers far more ids than GoodsInfo (20) / GoodsCaption (24), so a spare
row can be nameable but not describable. `shops.py` indexes the pool POSITIONALLY, so which rows a
seed uses is decided by ORDER -- and the order was arbitrary (ascending id).

🛑 THE GAP WAS WRITTEN DOWN IN datamine_spare_goods.py ON 2026-07-25 ("this filter only proves the
NAME is writable ... if the description matters too, this wants the same test against
GoodsInfo.fmg.xml") AND NOTHING ACTED ON IT. A self-reported gap is not a safeguard.

Ordering, not filtering: requiring all three would cut the pool ~65 -> ~25, below the ~54 region
locks that each need a distinct row. Complete rows are spent first and it degrades gracefully.
"""
import importlib.util
import os
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
TSV = os.path.join(_FOUND or "", "greenfield", "spare_goods.tsv") if _FOUND else ""


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
class SpareGoodsOrder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(TSV):
            raise unittest.SkipTest("greenfield/spare_goods.tsv absent")
        cls.rows = []
        with open(TSV, encoding="utf-8-sig") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln[:1].isdigit():
                    parts = ln.split("\t")
                    cls.rows.append((int(parts[0]), int(parts[1]) if len(parts) > 1 else 0))

    def test_the_table_carries_the_completeness_column(self):
        """Without it the order is unexplained and the next regen will drop it."""
        self.assertTrue(self.rows, "no data rows parsed out of spare_goods.tsv")
        self.assertTrue(any(full for _g, full in self.rows),
                        "no row is marked fmg_full -- either the column is gone or the FMG scan "
                        "found nothing, and an empty result is a FAILURE, not a clean run")

    def test_describable_rows_come_first(self):
        """THE assertion. A seed uses the pool positionally, so complete rows must be at the front."""
        seen_incomplete = False
        for gid, full in self.rows:
            if not full:
                seen_incomplete = True
            elif seen_incomplete:
                self.fail(
                    "spare good %d carries name+info+caption but sits AFTER a name-only row. The "
                    "pool is indexed positionally, so this hands a seed an undescribable row while "
                    "a describable one goes unused -- the `?GoodsInfo?` bug. Emit complete rows "
                    "first (tools/datamine_spare_goods.py)." % gid)

    def test_the_generated_module_preserves_that_order(self):
        """gen_data used to `sorted(set(...))` this, which silently undoes the ordering.

        The datamine can be perfect and the pipeline still ship the bug, one stage downstream."""
        import importlib.util
        path = os.path.join(_FOUND, "greenfield", "eldenring", "shop_data.py")
        if not os.path.isfile(path):
            self.skipTest("shop_data.py not generated here")
        spec = importlib.util.spec_from_file_location("_gf_shop_data", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        emitted = list(getattr(mod, "SPARE_PREVIEW_GOODS", ()))
        if not emitted:
            self.skipTest("SPARE_PREVIEW_GOODS empty in this tree")
        self.assertEqual(emitted, [g for g, _f in self.rows],
                         "shop_data.SPARE_PREVIEW_GOODS does not match spare_goods.tsv row order -- "
                         "something re-sorted it, and the completeness ordering is lost")
        self.assertNotEqual(emitted, sorted(emitted),
                            "the emitted pool is in plain ascending id order, which is what a stray "
                            "sorted() produces -- the completeness ordering has been undone")

    def test_twin_maiden_bell_runs_are_not_preview_spares(self):
        """Cut bell rows still drive talk ESD and expose broken menu entries when granted."""
        path = os.path.join(_FOUND, "tools", "datamine_spare_goods.py")
        spec = importlib.util.spec_from_file_location("_datamine_spare_goods", path)
        miner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(miner)
        fixture = """
def bells():
    while True:
        ComparePlayerInventoryNumber(ItemType.Goods, 8910 + GetWorkValue(0), 0, 1, False)
        if GetWorkValue(0) > 55:
            break
    while True:
        ComparePlayerInventoryNumber(ItemType.Goods, 2008900 + GetWorkValue(0), 0, 1, False)
        if GetWorkValue(0) > 10:
            break
"""
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as fh:
            fh.write(fixture)
            fixture_path = fh.name
        try:
            refs = miner._talk_goods_references([fixture_path])
        finally:
            os.unlink(fixture_path)
        self.assertTrue(set(range(8910, 8966)) <= refs.keys())
        self.assertTrue(set(range(2008900, 2008911)) <= refs.keys())
        spares = {goods_id for goods_id, _full in self.rows}
        self.assertFalse(spares & refs.keys(),
                         "spare_goods.tsv contains a goods row inspected by talk ESD")


if __name__ == "__main__":
    unittest.main()
