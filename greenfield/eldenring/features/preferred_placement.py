"""Soft placement preferences for useful items that should feel important without gating fill.

Items in ``PROGRESSION_SURFACE_IF_SPACE`` first reserve their fair cross-game share, then try the
owner's selected progression surface. Any item a restrictive pass cannot match returns to ordinary
fill. There is no surface widening and no generation failure: preferred means "if there is space".
"""
import inspect
import logging

from .progressive import PROG_FLASK, VANILLA_FLASK_ITEMS
from .scadu_supply import FRAGMENT, FRAGMENT_X2

_LOG = logging.getLogger("eldenring")

PROGRESSION_SURFACE_IF_SPACE = frozenset({
    FRAGMENT, FRAGMENT_X2, PROG_FLASK, *VANILLA_FLASK_ITEMS,
})
FOREIGN_SHARE_ITEMS = frozenset({FRAGMENT, FRAGMENT_X2})
_UNITS = {FRAGMENT: 1, FRAGMENT_X2: 2}


def preferred_items(world):
    """Unplaced soft-preference items owned by ``world``."""
    return [item for item in world.multiworld.itempool
            if item.player == world.player and item.name in PROGRESSION_SURFACE_IF_SPACE]


def foreign_unit_target(total_units: int, foreign_open: int, all_open: int) -> int:
    """Proportional foreign share, with one unit when a partner and supply both exist."""
    if total_units <= 0 or foreign_open <= 0 or all_open <= 0:
        return 0
    return min(total_units, max(1, round(total_units * foreign_open / all_open)))


def take_units(items, target: int, rng):
    """Select whole item objects until at least ``target`` fragment units are represented."""
    candidates = list(items)
    rng.shuffle(candidates)
    picked, units = [], 0
    for item in candidates:
        if units >= target:
            break
        picked.append(item)
        units += _UNITS.get(item.name, 1)
    return picked


def _fill(multiworld, locations, items, *, name, one_item_per_player=False):
    """Partial locked restrictive fill; leave refused item objects in ``items``."""
    if not locations or not items:
        return
    from Fill import fill_restrictive
    kwargs = {"lock": True}
    params = inspect.signature(fill_restrictive).parameters
    if "allow_partial" in params:
        kwargs["allow_partial"] = True
    if "one_item_per_player" in params:
        kwargs["one_item_per_player"] = one_item_per_player
    fill_restrictive(multiworld, multiworld.get_all_state(False), locations, items,
                     name=name, **kwargs)


def reserve_foreign_share(multiworld, worlds) -> None:
    """Put each ER world's proportional fragment-unit share in non-ER worlds, if possible."""
    er_players = {world.player for world in worlds}
    foreign_players = set(multiworld.player_ids) - er_players
    if not foreign_players:
        return
    all_open = [loc for loc in multiworld.get_unfilled_locations()
                if getattr(loc, "address", None) is not None and not getattr(loc, "locked", False)]
    foreign_open = [loc for loc in all_open if loc.player in foreign_players]
    if not foreign_open:
        return

    batch = []
    for world in worlds:
        local = set(getattr(world.options, "local_items", None)
                    and world.options.local_items.value or ())
        candidates = [item for item in preferred_items(world)
                      if item.name in FOREIGN_SHARE_ITEMS and item.name not in local]
        total_units = sum(_UNITS[item.name] for item in candidates)
        target = foreign_unit_target(total_units, len(foreign_open), len(all_open))
        batch.extend(take_units(candidates, target, world.random))
    if not batch:
        return

    selected = {id(item) for item in batch}
    multiworld.itempool[:] = [item for item in multiworld.itempool if id(item) not in selected]
    multiworld.random.shuffle(batch)
    locations = list(foreign_open)
    multiworld.random.shuffle(locations)
    total = len(batch)
    _fill(multiworld, locations, batch, name="Preferred Foreign Blessing Share",
          one_item_per_player=True)
    multiworld.itempool.extend(batch)
    _LOG.info("[greenfield] preferred-placement: sent %d/%d selected fragment item(s) abroad; "
              "%d returned to ordinary fill.", total - len(batch), total, len(batch))


def place_on_surface(multiworld, worlds) -> None:
    """Soft-place remaining category members on each owner's selected surface."""
    from . import progression_surface as surface

    for world in worlds:
        items = preferred_items(world)
        classes = surface.selected_surface(surface._selection(world))
        if not items or not classes:
            continue
        ids = surface.surface_ap_ids(world, classes)
        locations = [loc for loc in multiworld.get_locations(world.player)
                     if loc.item is None and getattr(loc, "address", None) in ids]
        if not locations:
            continue
        world.random.shuffle(items)
        world.random.shuffle(locations)
        selected = {id(item) for item in items}
        multiworld.itempool[:] = [item for item in multiworld.itempool if id(item) not in selected]
        total = len(items)
        _fill(multiworld, locations, items, name="Progression Surface If Space")
        multiworld.itempool.extend(items)
        _LOG.info("[eldenring:%s] preferred-placement: put %d/%d fragment item(s) on the selected "
                  "progression surface; %d spilled to ordinary fill.", world.player,
                  total - len(items), total, len(items))
