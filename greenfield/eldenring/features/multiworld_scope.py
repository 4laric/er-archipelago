"""multiworld_scope -- which of your checks take part in the multiworld (issue #1612).

THE ASK (Discord, vividoug, 2026-09-27): "keep the fillers in the game's default locations and only
have the key checks in the AP pool". Existing knobs are all keyed on ITEMS (`keep_local`,
`filler_foreign_pct`: which of MY items stay home) or on PROGRESSION (`progression_surface`: where
advancement may sit). This one is keyed on CHECKS:

  * `all` (default)   -- today's behaviour; nothing here runs.
  * `surface`         -- only Progression Surface checks exchange items with other worlds. Every
                         other check may hold only THIS world's own items, so the non-surface part
                         of the seed is a local shuffle. Other players' items (progression, useful
                         and filler alike) can land only on the surface.

HOW IT IS BUILT -- one widening of an existing rule, not a new rule:
core already installs `not foreign_bar_for(world)(item, player)` on every NON-surface location
(`confine_foreign_progression`). At 100 that bars foreign ADVANCEMENT. In `surface` mode
`progression_surface.foreign_bar_for` returns `foreign_item_barred` instead, which bars EVERY foreign
item. So the location set, the finale's copy of the rule and the surface resolution are the same
code the default path runs; only the predicate widens.

WHAT IT OVERRIDES (logged, never silent):
  * `confine_foreign_progression` -> 100. Below 100 core would not install the bar on every
    non-surface check, and the mode would leak.
  * `keep_local` -> [] and `filler_foreign_pct` -> 100. Both force items of mine to stay home.
    Under this mode the non-surface checks already keep everything that lands there home, and an
    item-side hold would additionally pin my own filler onto SURFACE checks -- the slots this mode
    reserves for exchange. The check-side rule replaces them.

WHAT IT REFUSES: `progression_sharing: open`, which lifts the foreign-progression bar -- the exact
opposite of this mode. An OptionError by name rather than a quiet override of the player's choice.

WHAT IT DOES NOT PROMISE: that every surface check pays a foreign item. The surface is OPEN, not
reserved: fill may still put one of my own items there. What leaves my world is exactly as many of
my items as foreign items that land on my surface (pigeonhole), progression first. Solo: no effect.

Generation only. No slot_data key, no contract hash move, no client half.
"""
import logging

from Options import Choice, OptionError

from ..registry import Feature, register


class MultiworldScope(Choice):
    """Which of your checks can hold other players' items.

    all: every check (default)
    surface: Progression Surface only; the rest shuffle your own items at home. Overrides
    keep_local and filler_foreign_pct; stops generation with progression_sharing open.
    """
    display_name = "Multiworld Scope"
    option_all = 0
    option_surface = 1
    default = 0


def is_surface(world) -> bool:
    opt = getattr(getattr(world, "options", None), "multiworld_scope", None)
    return bool(opt is not None and int(opt.value) == MultiworldScope.option_surface)


def foreign_item_barred(item, player):
    """True iff `item` belongs to ANOTHER player, whatever its classification. The `surface`-mode
    widening of `progression_surface.foreign_advancement_barred`."""
    return getattr(item, "player", player) != player


def apply_multiworld_scope(world) -> list:
    """Resolve `surface` onto the knobs it overrides. Called from core.generate_early right after
    `apply_progression_sharing` and BEFORE the feature loop, so local_items / filler_foreign /
    create_regions all read the resolved values. Returns [(option, old, new)] for the log line."""
    if not is_surface(world):
        return []
    opts = world.options
    sharing = getattr(opts, "progression_sharing", None)
    if sharing is not None and sharing.current_key == "open":
        raise OptionError(
            "[eldenring] multiworld_scope: surface and progression_sharing: open cannot both be on. "
            "surface keeps every other player's item on your Progression Surface; open lets their "
            "progression land on any safe check of yours. Pick balanced sharing with the surface "
            "scope, or multiworld_scope: all with open sharing.")
    changed = []
    conf = getattr(opts, "confine_foreign_progression", None)
    if conf is not None and int(conf.value) != 100:
        changed.append(("confine_foreign_progression", int(conf.value), 100))
        conf.value = 100
    kl = getattr(opts, "keep_local", None)
    if kl is not None and kl.value:
        changed.append(("keep_local", sorted(kl.value), []))
        kl.value = set()
    ffp = getattr(opts, "filler_foreign_pct", None)
    if ffp is not None and int(ffp.value) != 100:
        changed.append(("filler_foreign_pct", int(ffp.value), 100))
        ffp.value = 100
    return changed


@register
class MultiworldScopeFeature(Feature):
    name = "multiworld_scope"
    OPTIONS = {"multiworld_scope": MultiworldScope}

    def generate_early(self, world) -> None:
        if not is_surface(world):
            return
        log = logging.getLogger("Greenfield")
        log.info("[eldenring:%s] multiworld_scope: surface -- only Progression Surface checks take "
                 "other players' items; the rest shuffle this world's own items", world.player)
        for (name, old, new) in getattr(world, "gf_multiworld_scope_overrides", []):
            log.info("[eldenring:%s] multiworld_scope: %s %r overridden to %r", world.player,
                     name, old, new)
