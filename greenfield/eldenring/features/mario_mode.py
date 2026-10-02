"""Opt-in er-mario moveset unlocks (#1619).

Basic movement and punching stay available. These useful items have no reachability or goal
rules: the bridge enforces them inside libsm64, not Elden Ring's Tarnished action inputs.
Fixed item ids are registered by core, outside sequential feature allocation.
"""
from Options import Toggle, OptionError
from BaseClasses import ItemClassification
from ..registry import Feature, register
from .. import contract


class MarioMode(Toggle):
    """Experimental er-mario: find items to unlock moves.
    Two Progressive Jumps give Double, then Triple Jump; Backflip and Side Flip are separate.
    Basic jump and punch stay available; moves never gate checks or finishing.
    Gear and spells become runes; pickup checks and keys remain.
    Needs a compatible bridge and your own SM64 ROM. Set Vanilla Placement, Auto Equip,
    DeathLink and TrapLink off, Locked Abilities empty, and omit No Flask traps.
    """
    display_name = "Mario Mode (Experimental)"
    default = 0


def is_on(world):
    return bool(getattr(getattr(world.options, "mario_mode", None), "value", 0))


def _value(world, key, default=0):
    return getattr(getattr(world.options, key, None), "value", default)


def equipment_reward(world, name):
    """Only game-confirmed unusable categories, plus synthetic armor wrappers.

    Key goods, talismans, consumables and progression are preserved. This is reward filtering,
    never location filtering. Armor bundles are recognized by their owner, not name heuristics.
    """
    from .armor_bundles import is_bundle_name, MIXED_ARMOR_SETS
    from ..item_categories import category_of
    if is_bundle_name(name) or name in MIXED_ARMOR_SETS:
        return True
    # Casting needs a staff or seal, which Mario's forced fists prevent. The existing
    # goods taxonomy separates spells from keys/consumables; never infer this by name.
    if category_of(name) == "spells":
        return True
    full = world.tables.item_catalog.get(name)
    return full is not None and (full & 0xF0000000) in (0, 0x10000000, 0x80000000)


def filter_rewards(world, pool, filler_name):
    """Count-neutral final reward filter, before early-item declarations and fill.

    All contributors and the filler allocator have finished here, so none can reintroduce gear.
    Refuse any progression gear rather than silently remove a declared requirement.
    """
    if not is_on(world):
        return pool
    out = []
    for item in pool:
        if equipment_reward(world, item.name):
            if item.classification & ItemClassification.progression:
                raise OptionError(
                    "mario_mode cannot replace progression equipment %r; remove that item "
                    "requirement or turn Mario Mode off." % item.name)
            out.append(world.create_item(filler_name))
        else:
            out.append(item)
    return out


@register
class MarioFeature(Feature):
    name = "mario_mode"
    OPTIONS = {"mario_mode": MarioMode}

    def generate_early(self, world):
        if not is_on(world):
            return
        from . import vanilla_placement
        problems = []
        if not world._shuffle_on():
            problems.append("item_shuffle must be on")
        if vanilla_placement.is_on(world):
            problems.append("vanilla_placement must be off")
        if _value(world, "locked_abilities", ()):
            problems.append("locked_abilities must be empty (Mario uses separate actions)")
        if _value(world, "auto_equip"):
            problems.append("auto_equip must be off (Mario enforces his costume and fists)")
        if _value(world, "death_link"):
            problems.append("death_link must be off until Mario death synchronization is verified")
        if _value(world, "trap_link"):
            problems.append("trap_link must be off (linked No Flask traps do not affect Mario health)")
        if "no_flask" in _value(world, "traps", ()):
            problems.append("remove no_flask from traps (Mario heals through coins)")
        if problems:
            raise OptionError("mario_mode: " + "; ".join(problems) + ".")

    def create_items(self, world):
        if not is_on(world):
            return []
        return [world.create_item(name) for key, name in contract.MARIO_UNLOCK_ITEM_NAMES
                for _ in range(2 if key == "progressive_jump" else 1)]

    def slot_data(self, world):
        if not is_on(world):
            return {}
        return {
            "abilityUnlockItems": {
                str(world.item_name_to_id[name]): key
                for key, name in contract.MARIO_UNLOCK_ITEM_NAMES
            },
            "requiresClientFeatures": [contract.MARIO_CAPABILITIES_FEATURE],
        }
