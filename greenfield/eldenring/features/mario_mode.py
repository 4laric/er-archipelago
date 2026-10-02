"""Opt-in er-mario moveset unlocks (#1619).

Basic movement and punching stay available. These useful items have no reachability or goal
rules: the bridge enforces them inside libsm64, not Elden Ring's Tarnished action inputs.
Fixed item ids are registered by core, outside sequential feature allocation.
"""
from Options import Toggle, OptionError, Visibility
from BaseClasses import ItemClassification
from ..registry import Feature, register
from .. import contract

GOLDMASK_AP_ID = 7774610
REGRESSION = "Law of Regression"
REGRESSION_REGION = "Leyndell"
REGRESSION_FEATURE = "mario_regression_v1"


def goldmask_available(world):
    """The hub-labelled gesture physically needs Royal Leyndell; no independent sweep exists."""
    return not is_on(world) or REGRESSION_REGION in world._kept()


def regression_required(world):
    return is_on(world) and goldmask_available(world) and any(
        row[1] == GOLDMASK_AP_ID for row in world._seed_locations(world.tables.hub))


class MarioMode(Toggle):
    """Experimental er-mario: find items to unlock moves.

    Two Progressive Jumps give Double then Triple; Backflip and Side Flip are separate.
    Basic jump/punch stay free. Gear/spells become runes, except Law of Regression:
    keep it to Interact at Radagon's statue. Moves never gate checks or goals.
    Needs a compatible bridge and your SM64 ROM. Turn Vanilla Placement, Auto Equip,
    DeathLink and TrapLink off; empty Locked Abilities and omit No Flask traps.
    """
    display_name = "Mario Mode (Experimental)"
    default = 0


class MarioStatUpgrades(Toggle):
    """Randomize Mario health and attack power.

    Requires Mario Mode. Start at 4/8 health wedges and 75% normal damage.
    Four Progressive Health items add one maximum wedge each, without healing.
    Three Progressive Power items raise damage to 100%, 125%, then 150%.
    Coins, grace and stars respect the current health maximum. Stats never gate
    checks or goals. Needs a new seed and compatible paired Mario/client DLLs.
    """
    display_name = "Mario Stat Upgrades"
    # A companion-mode tuning knob belongs on advanced/weighted surfaces.
    visibility = Visibility.all & ~Visibility.simple_ui
    default = 0


class MarioFludd(Toggle):
    """Find FLUDD nozzles and tank upgrades for Mario.

    Requires Mario Mode. Hover, Rocket and Turbo start locked; each has one nozzle item.
    Three Progressive FLUDD Tanks raise capacity from 60 to 80, 100, then 120 units.
    Tank upgrades never refill water. Squirt is unfinished and is not included.
    Nozzles never gate checks or goals. Needs a new seed and compatible paired DLLs.
    """
    display_name = "Mario FLUDD (Experimental)"
    visibility = Visibility.all & ~Visibility.simple_ui
    default = 0


def fludd_on(world):
    return bool(_value(world, "mario_fludd"))


def stats_on(world):
    return bool(_value(world, "mario_stat_upgrades"))


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
    if name == REGRESSION and regression_required(world):
        return False  # quest key: Interact at the statue invokes the native reveal effect
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
    regression_seen = False
    for item in pool:
        if item.name == REGRESSION and regression_required(world):
            # The feature reserves one ordinary pool slot. Vanilla merchant copies pay filler.
            if regression_seen:
                out.append(world.create_item(filler_name))
                continue
            regression_seen = True
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
    OPTIONS = {"mario_mode": MarioMode, "mario_stat_upgrades": MarioStatUpgrades,
               "mario_fludd": MarioFludd}

    def generate_early(self, world):
        if fludd_on(world) and not is_on(world):
            raise OptionError("mario_fludd requires mario_mode: turn Mario Mode on "
                              "or turn Mario FLUDD off.")
        if not fludd_on(world):
            fludd_names = {name for _key, name, _aid, _count in contract.MARIO_FLUDD_ITEMS}
            starts = {name for option in ("start_inventory", "start_inventory_from_pool")
                      for name, count in _value(world, option, {}).items() if count > 0}
            if hasattr(world, "multiworld"):
                starts.update(item.name for item in world.multiworld.precollected_items
                              .get(world.player, ()))
            if fludd_names & starts:
                raise OptionError("FLUDD start inventory requires mario_fludd: turn it on "
                                  "with mario_mode or remove nozzle/tank start items.")
        if stats_on(world) and not is_on(world):
            raise OptionError("mario_stat_upgrades requires mario_mode: turn Mario Mode on "
                              "or turn Mario Stat Upgrades off.")
        if not stats_on(world):
            stat_names = {name for _key, name, _aid, _count in contract.MARIO_STAT_ITEMS}
            starts = {name for option in ("start_inventory", "start_inventory_from_pool")
                      for name, count in _value(world, option, {}).items() if count > 0}
            if hasattr(world, "multiworld"):
                starts.update(item.name for item in world.multiworld.precollected_items
                              .get(world.player, ()))
            if stat_names & starts:
                raise OptionError("Mario stat start inventory requires mario_stat_upgrades: "
                                  "turn it on with mario_mode or remove Progressive Health/Power.")
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
        world.gf_mario_quest_items = [REGRESSION] if regression_required(world) else []

    def create_items(self, world):
        if not is_on(world):
            return []
        return ([world.create_item(REGRESSION)] if regression_required(world) else []) + [
            world.create_item(name) for key, name in contract.MARIO_UNLOCK_ITEM_NAMES
            for _ in range(2 if key == "progressive_jump" else 1)] + ([
                world.create_item(name) for _key, name, _aid, count in contract.MARIO_STAT_ITEMS
                for _ in range(count)] if stats_on(world) else []) + ([
                world.create_item(name) for _key, name, _aid, count in contract.MARIO_FLUDD_ITEMS
                for _ in range(count)] if fludd_on(world) else [])

    def set_rules(self, world):
        if not regression_required(world):
            return
        location = next((loc for loc in world.multiworld.get_locations(world.player)
                         if loc.address == GOLDMASK_AP_ID), None)
        if location is None:
            return
        # ESD t112001100 awards f60848 only after the statue's reveal flag f11009556.
        # Native event 11003723 needs player SpEffect 1673014 within 4m of entity 11000716.
        # The bridge supplies that effect on Interact with the randomized spell in inventory;
        # Goldmask's dialogue still owns the award. No advanced Mario move gates this check.
        previous = location.access_rule
        player = world.player
        location.access_rule = lambda state, p=previous: (
            p(state) and state.has(REGRESSION, player)
            and state.can_reach(REGRESSION_REGION, "Region", player))
        previous_item = location.item_rule
        location.item_rule = lambda item, p=previous_item: p(item) and item.name != REGRESSION

    def slot_data(self, world):
        if not is_on(world):
            return {}
        return {
            "abilityUnlockItems": {
                str(world.item_name_to_id[name]): key
                for key, name in contract.MARIO_UNLOCK_ITEM_NAMES
            } | ({str(aid): key for key, _name, aid, _count in contract.MARIO_STAT_ITEMS}
                 if stats_on(world) else {})
            | ({str(aid): key for key, _name, aid, _count in contract.MARIO_FLUDD_ITEMS}
               if fludd_on(world) else {}),
            "requiresClientFeatures": [contract.MARIO_CAPABILITIES_FEATURE, REGRESSION_FEATURE]
            + ([contract.MARIO_STATS_FEATURE] if stats_on(world) else [])
            + ([contract.MARIO_FLUDD_FEATURE] if fludd_on(world) else []),
        }
