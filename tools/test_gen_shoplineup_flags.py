import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("gen_shoplineup_flags.py")
SPEC = importlib.util.spec_from_file_location("gen_shoplineup_flags", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StockFlagFloorTests(unittest.TestCase):
    def test_complete_117_table_passes(self):
        MODULE.validate(dict.fromkeys(range(MODULE.MIN_STOCK_FLAG_ROWS), 1))

    def test_pre_117_table_refuses(self):
        table = dict.fromkeys(range(MODULE.MIN_STOCK_FLAG_ROWS - 11), 1)
        with self.assertRaisesRegex(SystemExit, "complete 1.17 floor"):
            MODULE.validate(table)


if __name__ == "__main__":
    unittest.main()
