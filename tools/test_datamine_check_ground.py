import importlib.util
from pathlib import Path
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "datamine_check_ground", TOOLS / "datamine_check_ground.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CheckGroundTriageFloorTest(unittest.TestCase):
    def test_missing_triage_table_is_not_an_empty_answer(self):
        with self.assertRaisesRegex(SystemExit, "cannot answer"):
            MODULE._load_triage("/missing/check_region_triage.tsv")

    def test_truncated_triage_table_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "triage.tsv"
            path.write_text(
                "flag\tregion\n"
                + "".join(f"{i}\tLimgrave\n" for i in range(MODULE.MIN_TRIAGE_ROWS - 1)),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, r"only 455 checks \(floor 456,"):
                MODULE._load_triage(path)


if __name__ == "__main__":
    unittest.main()
