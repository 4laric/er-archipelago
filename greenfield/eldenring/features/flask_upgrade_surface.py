"""Compatibility spelling for v0.5's hard flask-upgrade surface option (#1090).

In v0.6 flask upgrades are members of ``progression_surface_if_space`` for every seed: they prefer
the selected surface after required items, then spill normally. The old boolean remains accepted so
existing YAMLs keep generating, but no longer installs a hard item rule or widens the surface.
"""
from Options import Toggle

from ..registry import Feature, register


class FlaskUpgradesOnProgressionSurface(Toggle):
    """Legacy v0.5 spelling; accepted but unnecessary in v0.6.

    Flask upgrades now always prefer unused progression-surface checks and safely spill into normal
    fill. They remain useful rather than required. This value is retained only so an older YAML
    containing it does not fail validation.
    """
    display_name = "Flask Upgrades on Progression Surface (legacy; now automatic)"
    default = 0


@register
class FlaskUpgradeSurface(Feature):
    name = "flask_upgrade_surface"
    OPTIONS = {
        "flask_upgrades_on_progression_surface": FlaskUpgradesOnProgressionSurface,
    }
