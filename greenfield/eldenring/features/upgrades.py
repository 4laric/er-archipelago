"""Weapon upgrade knobs -- auto_upgrade (raise received weapons to your live level) and
flatten_regular_upgrades (graduated smithing-stone cost for standard reinforcement).

AUTO_UPGRADE (Toggle). When on, the shared runtime client raises every RECEIVED weapon, at the
moment it is granted, to the highest reinforce level you currently HOLD on that weapon's own
smithing track (normal, cap +25 / somber, cap +10) -- raise-only, never lowering an already-higher
weapon, cap-clamped, and idempotent under the reconnect re-grant burst. There is no target-level
magnitude to pick: the client reads this as nonzero == on and derives the level from your live
inventory (er-logic/upgrades.rs apply_auto_upgrade + upgrades_replay.rs). Greenfield emits the
resolved int in slot_data["options"]["auto_upgrade"] (core._options_echo). On by default (the
2026-08-20 unfreeze kept the frozen value as the default). Matches
the old matt world's AutoUpgradeOption(Toggle) semantics 1:1.

FLATTEN_REGULAR_UPGRADES (Range) -- graduated smithing-stone COST for standard weapon reinforcement.
Vanilla ER charges 2/4/6 stones per tier-band for standard weapons; the shared runtime client can
flatten that ladder to a uniform N stones per +level (the upgrades client path). Greenfield emits the
resolved int in slot_data["options"] (core._options_echo); the client reads it as stones-per-level.

GRADUATED: 0 = off (vanilla 2/4/6), 1..4 = uniform N stones/level.
The per-sphere upgrade-curve analyzer (tools/analyze_upgrade_curve.py --fit) found N=3 tracks the
smoothstep difficulty target best across a stone_ramp x ladder grid (vanilla undershoots, N=1
overshoots by MAE ~8). Two stones per level remains the existing-release default; set 1 for
Somber-like pacing or 3 for the tuned curve.

auto_upgrade and flatten_regular_upgrades are INDEPENDENT knobs: auto_upgrade RAISES the received
weapon's level; flatten only cheapens the COST of reinforcing standard weapons yourself.
"""
from Options import Range, Toggle
from ..registry import Feature, register


class AutoUpgrade(Toggle):
    """Raises every weapon you receive or pick up to your best upgrade level.

    It matches the highest level you hold on that weapon's track (regular up to +25, somber
    up to +10; the two never mix) and never lowers one. To catch up a weapon you got early,
    put it down with Leave (not Discard, which destroys it) and pick it up again. On by
    default; off leaves weapons at their found level and you pay for upgrades.
    """
    # The default IS the ex-frozen value (2026-08-20 unfreeze). While an option is frozen its class
    # default is unreachable and rots; moving it in the same commit is what keeps a default seed's
    # behaviour identical (the PoolBuilderIntensity lesson). Pinned by test_gf_option_groups.
    default = 1
    display_name = "Auto-Upgrade Weapons"


class FlattenRegularUpgrades(Range):
    """Caps how many Smithing Stones each upgrade level of a regular weapon costs.

    Vanilla charges 2, 4, then 6 stones for each set of three levels that share a stone
    type, and 0 keeps that. Any other number caps every level at that many stones, so lower
    is cheaper. Default 2, cheaper than vanilla. Somber weapons and the final step to +25 do
    not change. A randomized seed sizes its early stone supply to match.
    """
    display_name = "Smithing Stone Cost Cap (0 = vanilla)"
    range_start = 0
    range_end = 4
    default = 2


@register
class UpgradesFeature(Feature):
    name = "upgrades"
    OPTIONS = {
        "auto_upgrade": AutoUpgrade,
        "flatten_regular_upgrades": FlattenRegularUpgrades,
    }
    # OPTIONS-only: the value is emitted centrally in slot_data["options"] by core._options_echo
    # (contract keys auto_upgrade + flatten_regular_upgrades), so no slot_data hook here.
