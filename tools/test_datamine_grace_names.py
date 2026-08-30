import importlib.util
from pathlib import Path
import unittest


TOOLS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "datamine_grace_names", TOOLS / "datamine_grace_names.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class GraceNameFloorTest(unittest.TestCase):
    def test_empty_join_is_not_an_answer(self):
        with self.assertRaisesRegex(SystemExit, r"only 0 graces .*floor 419"):
            MODULE.require_complete_names({})

    def test_truncated_join_is_not_an_answer(self):
        names = {i: str(i) for i in range(MODULE.MIN_NAMED_GRACES - 1)}
        with self.assertRaisesRegex(SystemExit, r"only 418 graces .*floor 419"):
            MODULE.require_complete_names(names)

    def test_measured_complete_join_passes(self):
        names = {i: str(i) for i in range(MODULE.MIN_NAMED_GRACES)}
        MODULE.require_complete_names(names)


if __name__ == "__main__":
    unittest.main()
