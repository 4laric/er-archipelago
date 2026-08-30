import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("build_tile_grace.py")
SPEC = importlib.util.spec_from_file_location("build_tile_grace", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CensusFloorTests(unittest.TestCase):
    def complete(self):
        names = dict.fromkeys(range(MODULE.MIN_NAMED_GRACES), "grace")
        tileof = dict.fromkeys(range(MODULE.MIN_GRACE_TILE_FLAGS), "tile")
        arena = set(range(MODULE.MIN_ARENA_GRACES))
        tile_grace = dict.fromkeys(range(MODULE.MIN_OUTPUT_TILES), "grace")
        return names, tileof, arena, tile_grace

    def test_complete_census_passes(self):
        MODULE._validate_census(*self.complete())

    def test_each_incomplete_dimension_refuses(self):
        for index in range(4):
            values = list(self.complete())
            value = values[index]
            value.remove(next(iter(value))) if isinstance(value, set) else value.pop(next(iter(value)))
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "incomplete"):
                MODULE._validate_census(*values)


if __name__ == "__main__":
    unittest.main()
