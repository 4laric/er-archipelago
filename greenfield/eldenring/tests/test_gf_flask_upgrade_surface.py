"""Progressive Flask Upgrade important-check confinement (#1090)."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features import progressive
from worlds.eldenring.features import progression_surface as surface
from worlds.eldenring.features.flask_upgrade_surface import FlaskUpgradesOnProgressionSurface


GAME = "Elden Ring"


def test_option_defaults_off():
    assert FlaskUpgradesOnProgressionSurface.default == 0


class FlaskSurfaceOn(WorldTestBase):
    game = GAME
    options = {
        "enable_dlc": True,
        "num_regions": 0,
        "progressive_flasks": True,
        "flask_upgrades_on_progression_surface": True,
        # Deliberately undersized: seven Great Rune checks cannot host 56 copies. This makes the
        # widening guarantee load-bearing instead of merely asserting the common no-widen case.
        "progression_surface": {"GreatRune"},
    }

    def test_every_copy_has_enough_compatible_surface_hosts(self):
        world = self.world
        copies = progressive.flask_copy_count(world)
        probe = world.create_item(progressive.PROG_FLASK)
        allowed = world.gf_flask_surface_ids
        compatible = [
            location for location in self.multiworld.get_locations(world.player)
            if location.address in allowed and location.item_rule(probe)
        ]
        self.assertGreater(copies, 0)
        self.assertGreaterEqual(len(compatible), copies)

    def test_flask_is_refused_everywhere_outside_resolved_surface(self):
        world = self.world
        probe = world.create_item(progressive.PROG_FLASK)
        outside = [
            location for location in self.multiworld.get_locations(world.player)
            if location.address not in world.gf_flask_surface_ids
        ]
        self.assertTrue(outside, "no ordinary checks exist to prove the confinement")
        leaked = [location.name for location in outside if location.item_rule(probe)]
        self.assertEqual(leaked, [], "flask upgrade escaped the resolved important-check surface")

    def test_default_surface_widens_instead_of_silently_spilling(self):
        world = self.world
        probe = world.create_item(progressive.PROG_FLASK)
        base = surface.surface_ap_ids(
            world, surface.selected_surface(surface._selection(world)))
        base_compatible = [
            location for location in self.multiworld.get_locations(world.player)
            if location.address in base and location.item_rule(probe)
        ]
        copies = progressive.flask_copy_count(world)
        self.assertLess(len(base_compatible), copies,
                        "fixture no longer exercises the widening path")
        self.assertGreater(len(world.gf_flask_surface_ids), len(base))

    def test_flasks_remain_useful_not_progression(self):
        item = self.world.create_item(progressive.PROG_FLASK)
        self.assertEqual(item.name, progressive.PROG_FLASK)
        self.assertFalse(item.advancement)


class FlaskSurfaceOff(WorldTestBase):
    game = GAME
    options = {
        "enable_dlc": True,
        "num_regions": 0,
        "progressive_flasks": True,
        "flask_upgrades_on_progression_surface": False,
    }

    def test_off_preserves_ordinary_placement(self):
        world = self.world
        self.assertFalse(hasattr(world, "gf_flask_surface_ids"))
        probe = world.create_item(progressive.PROG_FLASK)
        base = surface.surface_ap_ids(
            world, surface.selected_surface(surface._selection(world)))
        ordinary = [
            location for location in self.multiworld.get_locations(world.player)
            if location.address not in base and location.item_rule(probe)
        ]
        self.assertTrue(ordinary, "option off still confines flask upgrades to the surface")
