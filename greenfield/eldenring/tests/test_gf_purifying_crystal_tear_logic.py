"""Regression for #777: the Purifying Crystal Tear is pre-Mohg Altus content.

The tear comes from Eleonora's Altus encounter. It must require access to Altus, but it must not
inherit Mohg, Mohgwyn Palace, or Remembrance of the Blood Lord logic.
"""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from BaseClasses import CollectionState  # noqa: E402


class PurifyingCrystalTearLogicTest(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0, "enable_dlc": False}

    def test_tear_is_an_ordinary_altus_check(self):
        location = next(
            loc for loc in self.multiworld.get_locations(self.player)
            if loc.address == 7770039
        )

        self.assertIn("Purifying Crystal Tear", location.name)
        self.assertEqual("Altus", location.parent_region.name)
        self.assertTrue(
            location.access_rule(CollectionState(self.multiworld)),
            "the tear must have no Mohg-specific or quest-specific access rule",
        )
