"""flatten_regular_upgrades -- graduated smithing-stone cost for standard weapon reinforcement.

Vanilla ER charges 2/4/6 stones per tier-band for standard weapons; the shared runtime client can
flatten that ladder to a uniform N stones per +level (the upgrades client path). Greenfield emits the
resolved int in slot_data["options"] (core._options_echo); the client reads it as stones-per-level.

Was a constant-0 on/off echo; now GRADUATED: 0 = off (vanilla 2/4/6), 1..4 = uniform N stones/level.
The per-sphere upgrade-curve analyzer (tools/analyze_upgrade_curve.py --fit) found N=3 tracks the
smoothstep difficulty target best across a stone_ramp x ladder grid (vanilla undershoots, N=1
overshoots by MAE ~8). Off by default (no change from prior behavior); set 3 for the tuned curve.

CLIENT NOTE: the upgrades path must read this int as stones-per-level (not just nonzero == flatten
to 1). Until that lands, values 1..4 all behave as the old on (1/level) in-game.
"""
from Options import Range
from ..registry import Feature, register


class FlattenRegularUpgrades(Range):
    """Stones per +level for STANDARD weapon reinforcement -- the client flattens the vanilla 2/4/6
    ladder to a uniform cost. 0 = off (vanilla 2/4/6); 1..4 = uniform N stones per level (lower =
    weapons upgrade faster). The upgrade-curve analyzer found 3 best matches the smoothstep difficulty
    scaling (0/vanilla undershoots the target, 1 overshoots it). Off by default. Somber weapons
    (1 stone/level) and the +25 Ancient Dragon step are unaffected."""
    display_name = "Flatten Regular Upgrades (stones/level)"
    range_start = 0
    range_end = 4
    default = 0


@register
class UpgradesFeature(Feature):
    name = "upgrades"
    OPTIONS = {"flatten_regular_upgrades": FlattenRegularUpgrades}
    # OPTIONS-only: the value is emitted centrally in slot_data["options"] by core._options_echo
    # (contract key flatten_regular_upgrades), so no slot_data hook here.
