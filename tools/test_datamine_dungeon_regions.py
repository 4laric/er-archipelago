import importlib.util
from pathlib import Path
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "datamine_dungeon_regions", TOOLS / "datamine_dungeon_regions.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DungeonRegionFloorTest(unittest.TestCase):
    def test_refuses_to_replace_table_when_connect_corpus_is_absent(self):
        grace_rows = [(f"m30_{i:02d}", "Limgrave", "grace", "test") for i in range(78)]
        with mock.patch.object(MODULE, "build", return_value=grace_rows), mock.patch.object(
            MODULE, "OUT", "/must/not/be/written.tsv"
        ):
            with self.assertRaisesRegex(SystemExit, r"connect=0 \(minimum 11\)"):
                MODULE.main([])

    def test_complete_measured_corpus_can_be_written(self):
        rows = [(f"m30_{i:02d}", "Limgrave", "grace", "test") for i in range(78)]
        rows += [(f"m31_{i:02d}", "Liurnia", "connect", "test") for i in range(11)]
        with mock.patch.object(MODULE, "build", return_value=rows), mock.patch(
            "builtins.open", mock.mock_open()
        ) as opened:
            self.assertEqual(MODULE.main([]), 0)
            opened.assert_called_once_with(MODULE.OUT, "w", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    unittest.main()
