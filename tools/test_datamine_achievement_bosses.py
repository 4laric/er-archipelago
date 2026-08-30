import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("datamine_achievement_bosses.py")
SPEC = importlib.util.spec_from_file_location("datamine_achievement_bosses", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def rows(total, bosses):
    return [(i, i, "boss" if i < bosses else "collection") for i in range(total)]


class AchievementCensusFloorTests(unittest.TestCase):
    def test_complete_census_passes(self):
        MODULE.validate_census(rows(MODULE.MIN_ACHIEVEMENTS, MODULE.MIN_BOSS_ACHIEVEMENTS))

    def test_short_total_refuses(self):
        with self.assertRaisesRegex(SystemExit, "achievements=31"):
            MODULE.validate_census(rows(MODULE.MIN_ACHIEVEMENTS - 1,
                                        MODULE.MIN_BOSS_ACHIEVEMENTS))

    def test_short_boss_classifier_refuses(self):
        with self.assertRaisesRegex(SystemExit, "boss achievements=28"):
            MODULE.validate_census(rows(MODULE.MIN_ACHIEVEMENTS,
                                        MODULE.MIN_BOSS_ACHIEVEMENTS - 1))


if __name__ == "__main__":
    unittest.main()
