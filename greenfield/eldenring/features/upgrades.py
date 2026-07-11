"""Weapon upgrade knobs -- auto_upgrade (raise received weapons to your live level) and
flatten_regular_upgrades (graduated smithing-stone cost for standard reinforcement).

AUTO_UPGRADE (Toggle). When on, the shared runtime client raises every RECEIVED weapon, at the
moment it is granted, to the highest reinforce level you currently HOLD on that weapon's own
smithing track (normal, cap +25 / somber, cap +10) -- raise-only, never lowering an already-higher
weapon, cap-clamped, and idempotent under the reconnect re-grant burst. There is no target-level
magnitude to pick: the client reads this as nonzero == on and derives the level from your live
inventory (er-logic/upgrades.rs apply_auto_upgrade + upgrades_replay.rs). Greenfield emits the
resolved int in slot_data["options"]["auto_upgrade"] (core._options_echo). Off by default. Matches
the old matt world's AutoUpgradeOption(Toggle) semantics 1:1.

FLATTEN_REGULAR_UPGRADES (Range) -- graduated smithing-stone COST for standard weapon reinforcement.
Vanilla ER charges 2/4/6 stones per tier-band for standard weapons; the shared runtime client can
flatten that ladder to a uniform N stones per +level (the upgrades client path). Greenfield emits the
resolved int in slot_data["options"] (core._options_echo); the client reads it as stones-per-level.

Was a constant-0 on/off echo; now GRADUATED: 0 = off (vanilla 2/4/6), 1..4 = uniform N stones/level.
The per-sphere upgrade-curve analyzer (tools/analyze_upgrade_curve.py --fit) found N=3 tracks the
smoothstep difficulty target best across a stone_ramp x ladder grid (vanilla undershoots, N=1
overshoots by MAE ~8). Off by default (no change from prior behavior); set 3 for the tuned curve.

CLIENT NOTE: the flatten path must read this int as stones-per-level (not just nonzero == flatten
to 1). Until that lands, values 1..4 all behave as the old on (1/level) in-game. auto_upgrade and
flatten_regular_upgrades are INDEPENDENT knobs: auto_upgrade RAISES the received weapon's level;
flatten only cheapens the COST of reinforcing standard weapons yourself.
"""
from Options import Range, Toggle
from ..registry import Feature, register


class AutoUpgrade(Toggle):
    """Automatically raise any RECEIVED weapon to the highest reinforce level you already hold on
    its smithing track (normal caps at +25, somber at +10). Raise-only: a received weapon already
    above your live level is left untouched. Off by default. (The level tracks your inventory live;
    there is no fixed target to choose.)"""
    display_name = "Auto-Upgrade Received Weapons"


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
    OPTIONS = {
        "auto_upgrade": AutoUpgrade,
        "flatten_regular_upgrades": FlattenRegularUpgrades,
    }
    # OPTIONS-only: the value is emitted centrally in slot_data["options"] by core._options_echo
    # (contract keys auto_upgrade + flatten_regular_upgrades), so no slot_data hook here.
