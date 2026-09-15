"""Leyndell great-rune gate -- RETIRED 2026-09-14 (Leyndell becomes an ordinary Lock region).

Alaric's ruling: Leyndell, Royal Capital is no longer a gated child. Its grace bundle rides the
`Leyndell Lock` exactly like every ungated region (the same ruling already applied to Raya Lucaria
Academy on 2026-08-16, see features/graces.py). The physical two-Great-Rune seal is opened by the
client on receipt of the Leyndell Lock -- the world emits the seal flags (105 and 182, the pair
m60_45_52_00 $Event(1045522500) reads) through `lockRevealFlags["Leyndell Lock"]`
(features/area_locks.py), and the client sets them the way it used to set them on rune receipt
(keyitems.rs LEYNDELL_TWO_RUNES_FLAGS; no client change -- lockRevealFlags is parsed generically). Great Runes gate NOTHING
in Leyndell any more: they remain in the pool and are progression only under
`ending_condition: great_runes`.

What used to live here -- the synthetic rune wall (generate_early sample, set_rules
entrance/location rules, item_rule cycle-breaker, world.gf_leyndell_runes /
world.gf_leyndell_injected) -- is deleted, not moved. The one exception is
natural_progression mode, which mints no Locks: there the game's own two-rune wall is still the
wall, so that feature owns its two-rune logic (count, entrance rule and client count trigger)
itself now -- see features/natural_progression.py. Everywhere else the capital opens on its Lock.

The history is kept in git, not in this file: the wall's design notes (the vanilla floor,
#589's repair-not-disarm, #640's seeded sample, #764's move of the top-up to features/great_runes,
the ALL-SEVEN-COUNT EMEVD reading) lived here until this commit and are reachable from it.

Option `leyndell_runes_required` stays ACCEPTED as a deprecated no-op so old YAMLs still generate:
any value parses, every value is ignored, and a non-default value logs once that it is ignored.
(Follows the GlobalScadutreeBlessing deprecated pattern in features/scaling.py, and the option is
listed in tools/dump_options_metadata.py COMPATIBILITY_ONLY so it leaves the shipped template.)
"""
import logging

from Options import Range, Visibility

from ..gamename import GAME as _GAME  # the AP game name is typed once (#1465)
from ..registry import Feature, register

_log = logging.getLogger(_GAME)


class LeyndellRunesRequired(Range):
    """DEPRECATED 2026-09-14 -- Leyndell opens on its Lock like every other region; no Great Rune
    count gates it any more. Still honoured as in still accepted, so an existing yaml keeps
    generating the identical seed shape it would have: every value is ignored.

    Importable and visible in detailed tools/spoilers, never suggested in a new YAML."""
    # Importable and visible in detailed tools/spoilers, never suggested in a new YAML.
    visibility = Visibility.all & ~Visibility.template
    display_name = "Leyndell Great Runes Required (deprecated)"
    range_start = 0
    range_end = 6
    default = 2


@register
class LeyndellGate(Feature):
    name = "leyndell_gate"
    OPTIONS = {"leyndell_runes_required": LeyndellRunesRequired}

    def generate_early(self, world) -> None:
        # No wall to arm and no state to publish: the capital bundle rides the Leyndell Lock
        # (features/graces.py WALL_ARMED["Leyndell"] is False in every seed). Say so once when a
        # yaml still names a non-default value, so a player who set it knows it did nothing --
        # silence about an ignored knob is the failure this log line exists to prevent.
        opt = getattr(world.options, "leyndell_runes_required", None)
        if opt is not None and int(opt.value) != LeyndellRunesRequired.default:
            _log.info("leyndell_gate: leyndell_runes_required is deprecated and ignored "
                      "(Leyndell opens on its Lock since 2026-09-14) -- got %d.", int(opt.value))
