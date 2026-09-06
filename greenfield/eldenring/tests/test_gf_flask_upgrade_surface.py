"""v0.6 soft flask-upgrade placement compatibility (#1090)."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features import progressive
from worlds.eldenring.features.flask_upgrade_surface import FlaskUpgradesOnProgressionSurface
from worlds.eldenring.features.preferred_placement import PROGRESSION_SURFACE_IF_SPACE


GAME = "Elden Ring"


def test_legacy_option_stays_accepted_and_defaults_off():
    assert FlaskUpgradesOnProgressionSurface.default == 0


def test_both_flask_modes_are_in_the_soft_preference_category():
    assert progressive.PROG_FLASK in PROGRESSION_SURFACE_IF_SPACE
    assert set(progressive.VANILLA_FLASK_ITEMS) <= PROGRESSION_SURFACE_IF_SPACE


class FlaskSurfaceCompatibility(WorldTestBase):
    game = GAME
    options = {
        "enable_dlc": True,
        "num_regions": 0,
        "progressive_flasks": True,
        "flask_upgrades_on_progression_surface": True,
        "progression_surface": {"GreatRune"},
    }

    def test_legacy_true_no_longer_hard_confines_or_widens(self):
        world = self.world
        self.assertFalse(hasattr(world, "gf_flask_surface_ids"))
        probe = world.create_item(progressive.PROG_FLASK)
        ordinary = [location for location in self.multiworld.get_locations(world.player)
                    if location.item is None and location.item_rule(probe)]
        self.assertTrue(ordinary)

    def test_flasks_remain_useful_not_progression(self):
        item = self.world.create_item(progressive.PROG_FLASK)
        self.assertTrue(item.useful)
        self.assertFalse(item.advancement)
