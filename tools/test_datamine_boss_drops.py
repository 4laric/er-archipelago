import importlib.util
from pathlib import Path
import unittest


TOOLS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "datamine_boss_drops", TOOLS / "datamine_boss_drops.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def row(flag, map_id):
    return (flag, flag, flag, f"item {flag}", "Limgrave", "test", map_id)


class BossDropFloorTest(unittest.TestCase):
    def test_empty_corpus_is_not_an_answer(self):
        with self.assertRaisesRegex(SystemExit, r"drops=0 .*maps=0"):
            MODULE.require_complete_rows([])

    def test_large_but_map_truncated_corpus_is_not_an_answer(self):
        rows = [row(i, "m10_00_00_00") for i in range(MODULE.MIN_DROP_ROWS)]
        with self.assertRaisesRegex(SystemExit, r"maps=1 \(minimum 71\)"):
            MODULE.require_complete_rows(rows)

    def test_measured_complete_shape_passes(self):
        rows = [row(i, f"map-{i % MODULE.MIN_DROP_MAPS}") for i in range(MODULE.MIN_DROP_ROWS)]
        MODULE.require_complete_rows(rows)


if __name__ == "__main__":
    unittest.main()
