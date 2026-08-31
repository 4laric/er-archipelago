"""Optional placement confinement for Progressive Flask Upgrades (#1090).

Flask upgrades are useful, not progression: this feature changes where they may land without
claiming they gate reachability or victory.  The selected ``progression_surface`` is the first
choice.  If it cannot host every copy, the same reviewed feasibility ladder used for Region Locks
widens it explicitly.  There is no silent spill to arbitrary locations.
"""
import logging

from Options import Toggle

from ..registry import Feature, register


class FlaskUpgradesOnProgressionSurface(Toggle):
    """Keep Progressive Flask Upgrades on important checks.

    Off (default) preserves ordinary placement.  On starts with your ``progression_surface``
    selection and, only when that surface is too small for every flask copy, widens through its
    existing reviewed fallback ladder.  Flask upgrades remain useful rather than required: this
    affects placement quality, not logic or the victory condition.
    """
    display_name = "Flask Upgrades on Progression Surface"
    default = 0


def _enabled(world):
    option = getattr(getattr(world, "options", None),
                     "flask_upgrades_on_progression_surface", None)
    return bool(option is not None and int(option.value))


def _open_compatible(world, ap_ids, probe):
    """Unfilled own locations in ``ap_ids`` whose existing rules accept the flask item."""
    return [
        location for location in world.multiworld.get_locations(world.player)
        if location.address in ap_ids
        and location.item is None
        and not getattr(location, "locked", False)
        and location.item_rule(probe)
    ]


def _resolved_surface(world, copies, probe):
    """First progression-surface ladder rung with room for every flask copy."""
    from . import progression_surface as surface

    selection = surface.selected_surface(surface._selection(world))
    for classes in surface.build_ladder(selection):
        ap_ids = frozenset(surface.surface_ap_ids(world, classes))
        if len(_open_compatible(world, ap_ids, probe)) >= copies:
            return ap_ids, tuple(classes)
    return frozenset(), tuple()


@register
class FlaskUpgradeSurface(Feature):
    name = "flask_upgrade_surface"
    OPTIONS = {
        "flask_upgrades_on_progression_surface": FlaskUpgradesOnProgressionSurface,
    }

    def create_regions(self, world) -> None:
        if not _enabled(world):
            return

        from . import progressive
        from . import progression_surface as surface
        if not progressive._flasks_on(world) or not progressive._shuffle_on(world):
            return

        copies = progressive.flask_copy_count(world)
        if copies <= 0:
            return
        probe = world.create_item(progressive.PROG_FLASK)
        allowed, classes = _resolved_surface(world, copies, probe)
        if not allowed:
            from Options import OptionError
            raise OptionError(
                "flask_upgrades_on_progression_surface needs %d compatible important checks, "
                "but even the widest reviewed progression-surface rung has fewer. Widen "
                "progression_surface or turn this option off; flask upgrades never silently "
                "spill onto ordinary checks." % copies)

        base = tuple(surface.selected_surface(surface._selection(world)))
        if classes != base:
            logging.getLogger("Elden Ring").info(
                "[greenfield] flask surface widened from %s to %s to host all %d upgrade copies",
                ", ".join(base) or "(empty)", ", ".join(classes), copies)

        world.gf_flask_surface_ids = allowed
        for location in world.multiworld.get_locations(world.player):
            previous = location.item_rule
            address = location.address
            location.item_rule = (
                lambda item, prev=previous, ap_id=address, ids=allowed:
                prev(item) and (item.name != progressive.PROG_FLASK or ap_id in ids)
            )
