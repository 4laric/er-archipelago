import importlib.util
from pathlib import Path
import unittest


TOOLS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "datamine_boss_healthbars", TOOLS / "datamine_boss_healthbars.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BossHealthbarFloorTest(unittest.TestCase):
    def test_empty_corpus_is_not_an_answer(self):
        with self.assertRaisesRegex(SystemExit, r"bosses=0 .*maps=0"):
            MODULE.require_complete_bosses({})

    def test_large_but_map_truncated_corpus_is_not_an_answer(self):
        bosses = {i: {"map": "m10_00"} for i in range(MODULE.MIN_BOSSES)}
        with self.assertRaisesRegex(SystemExit, r"maps=1 \(minimum 118\)"):
            MODULE.require_complete_bosses(bosses)

    def test_measured_complete_shape_passes(self):
        bosses = {
            i: {"map": f"m{i % MODULE.MIN_BOSS_MAPS:02d}_00"}
            for i in range(MODULE.MIN_BOSSES)
        }
        MODULE.require_complete_bosses(bosses)


if __name__ == "__main__":
    unittest.main()
