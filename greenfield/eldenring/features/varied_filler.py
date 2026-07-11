"""varied_filler -- received filler is real ER junk consumables, not a monotone Rune (matt-free).

greenfield's non-juice filler is otherwise all one item (Golden Rune [1]); in a multiworld that hands
co-op partners a wall of identical Runes. This draws each filler grant from FILLER_POOL (goods-tier
consumables/materials the catalog resolved -- greases, boluses, butterflies, smithing stones, ...),
so filler feels like real loot. Count-neutral, fill-safe (all filler-classified), deterministic
(world.random). Composes UNDER pool_builder: pool_builder still juices the top of the tail with
rare/legendary equippables; this varies whatever filler remains. On by default.

B (filler_upgrade_weight): the per-sphere upgrade-curve analyzer (tools/analyze_upgrade_curve.py)
showed standard-weapon upgrades STARVED under uniform filler (median stuck ~+2). This knob over-weights
smithing/somber stones in the draw so upgrade materials appear more densely -- count-neutral, still
fill-safe, tunable against the measured curve.
"""
from Options import DefaultOnToggle, Range, Toggle
from ..registry import Feature, register


class VariedFiller(DefaultOnToggle):
    """Received filler items are a varied mix of real ER consumables/materials instead of all being
    the same Golden Rune. On by default; off = the monotone Rune filler."""
    display_name = "Varied Filler"


class FillerUpgradeWeight(Range):
    """How heavily smithing/somber upgrade stones are favored among varied filler. Weight W makes each
    stone item W times as likely to be drawn as a non-stone filler item; 1 (DEFAULT) = uniform, no
    change. With ~17 stone names vs ~195 other filler, W=8 makes roughly 40% of filler grants upgrade
    stones -- the lever for the measured standard-weapon starvation. Only changes WHICH filler items
    appear (count-neutral, fill-safe); ignored unless Varied Filler is on."""
    display_name = "Filler Upgrade-Stone Weight"
    range_start = 1
    range_end = 40
    default = 1


class StoneInjection(Range):
    """B (shuffle-safe): swap this many filler-classified non-stone pool items for LOW smithing stones
    ([1]/[2]/[3], round-robin). Count-neutral (filler->filler, winnability preserved). Unlike Filler
    Upgrade-Stone Weight (which only touches the ~1% Rune-fallback tail and is inert under item_shuffle),
    this operates on the SHUFFLED pool, so it actually raises the low-tier stone supply that the
    upgrade-curve analyzer showed starves standard weapons. 0 (default) = off."""
    display_name = "Low Smithing-Stone Injection"
    range_start = 0
    range_end = 400
    default = 0


class StoneRamp(Toggle):
    """B-ramp (AUTO-SIZED): when on, distribute smithing stones along the TRUE per-seed fill spheres so
    the achieved standard-weapon curve tracks the smoothstep difficulty target (max weapon by the
    deepest sphere), FRONT-LOADED at the low end: the low tiers ([1]-[3] -> +9) ramp forward to be
    affordable by ~20% run depth instead of ~40%, so early standard weapons are usable; +10 and up stay
    on the original smoothstep. No count to tune -- per sphere it places exactly the stones needed to
    AFFORD the target at that depth under the current flatten_regular_upgrades ladder, MINUS the vanilla
    stones already reachable there. Scales automatically with num_regions (= sphere count) and the
    flatten setting. Count-neutral (filler->stone in place), winnable, and pinned to THIS world's own
    locations (never scattered to other worlds; those checks stop hosting others' items -> a bit more
    solo). Off by default; pair with flatten_regular_upgrades = 3 for the tuned fit."""
    display_name = "Smithing-Stone Auto Ramp"


@register
class VariedFillerFeature(Feature):
    name = "varied_filler"
    OPTIONS = {"varied_filler": VariedFiller, "filler_upgrade_weight": FillerUpgradeWeight,
               "stone_injection": StoneInjection, "stone_ramp": StoneRamp}
    # No slot_data key + no items: filler items are already ITEM_CATALOG entries core registers, and
    # the choice happens in core.create_items / get_filler_item_name. This feature only adds options.
