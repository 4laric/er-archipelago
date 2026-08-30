import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("datamine_sweep_trigger_npcs.py")
SPEC = importlib.util.spec_from_file_location("datamine_sweep_trigger_npcs", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def census(total, resolved):
    return {
        i: {"method": "chr_boss" if i < resolved else "UNRESOLVED"}
        for i in range(total)
    }


class SweepTriggerFloorTests(unittest.TestCase):
    def test_complete_census_passes(self):
        MODULE.validate_census(census(MODULE.MIN_TRIGGERS, MODULE.MIN_RESOLVED_TRIGGERS))

    def test_short_trigger_scan_refuses(self):
        with self.assertRaisesRegex(SystemExit, "triggers=243"):
            MODULE.validate_census(census(MODULE.MIN_TRIGGERS - 1,
                                          MODULE.MIN_RESOLVED_TRIGGERS))

    def test_classifier_regression_refuses(self):
        with self.assertRaisesRegex(SystemExit, "resolved=234"):
            MODULE.validate_census(census(MODULE.MIN_TRIGGERS,
                                          MODULE.MIN_RESOLVED_TRIGGERS - 1))


if __name__ == "__main__":
    unittest.main()
