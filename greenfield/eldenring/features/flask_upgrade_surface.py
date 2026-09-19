"""Compatibility spelling for v0.5's hard flask-upgrade surface option (#1090).

In v0.6 flask upgrades are members of ``progression_surface_if_space`` for every seed: they prefer
the selected surface after required items, then spill normally. The old boolean remains accepted so
existing YAMLs keep generating, but no longer installs a hard item rule or widens the surface.
"""
from Options import Toggle, Visibility

from ..registry import Feature, register


class FlaskUpgradesOnProgressionSurface(Toggle):
    """Does nothing; kept only so old yamls that set it still load.

    Flask upgrades now prefer your Progression Surface spots when there is room, on every
    seed, whatever this says.
    """
    # Importable and visible in detailed tools/spoilers, never suggested in a new YAML.
    visibility = Visibility.complex_ui | Visibility.spoiler
    display_name = "Flask Upgrades on Progression Surface (no effect)"
    default = 0


@register
class FlaskUpgradeSurface(Feature):
    name = "flask_upgrade_surface"
    OPTIONS = {
        "flask_upgrades_on_progression_surface": FlaskUpgradesOnProgressionSurface,
    }
