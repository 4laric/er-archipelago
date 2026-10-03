"""Experimental boss board: square checks are the hard progression surface.

First automatic catalogue is an AP adaptation of boss bingo objectives, not the full
Bingo Brawlers export. Encounter flags and arena owners come from our generated EMEVD
tables. Restricted combat, quests, and collection objectives are deliberately absent.
"""
import hashlib
import json

from BaseClasses import Location
from Options import Choice, Range, Toggle, OptionError, Visibility

from ..registry import Feature, register
from ..bingo_board import LOCATION_NAMES, is_complete, select_board
from .. import contract


class BingoMode(Toggle):
    """An experimental boss board supplies progression rewards.

    Objectives choose their regions; Num Regions is ignored.
    Selected regions open with their safe graces; no Region Lock items.
    Requires a fresh character and this branch's client. Default off."""
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Bingo Mode"


class BingoCatalogue(Choice):
    """Choose the original boss board or the E1 audit catalogue.

    E1 adds major bosses, levels, base stats, flasks and earned DLC blessings.
    Upgrade squares reserve reachable supplies. Requires the E1 client."""
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Bingo Catalogue"
    option_boss_board = 0
    option_e1 = 1
    default = 0


class BingoRegionLimit(Range):
    """Cap the board's regions, including their prerequisites.

    Objectives are chosen first; unrelated regions are omitted.
    Increase if 25 bosses cannot fit. Default six."""
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Bingo Region Limit"
    range_start = 2
    range_end = 12
    default = 6


class BingoGoal(Choice):
    """Finish on a line, a square count, or all 25 squares.

    Only applies to Bingo Mode. A line is the short-run default."""
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Bingo Goal"
    option_line = 0
    option_count = 1
    option_blackout = 2
    default = 0


class BingoSquareCount(Range):
    """Squares needed for the count goal; line and blackout ignore this."""
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Bingo Square Count"
    range_start = 1
    range_end = 25
    default = 13


class BingoLineSweepSize(Range):
    """Release a batch of native checks on the first completed line.

    Progression stays on squares. Already collected members reduce payout.
    Zero disables the bonus. Applies to every Bingo Goal."""
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Bingo First Line Sweep"
    range_start = 0
    range_end = 50
    default = 20


def active(world):
    return bool(getattr(getattr(world.options, "bingo_mode", None), "value", 0))


def e1(world):
    return active(world) and bool(world.options.bingo_catalogue.value)


def square_ids(world):
    return frozenset(c["location"] for c in getattr(world, "gf_bingo_board", ()))


def permits_progression(world, location, item):
    return not active(world) or not item.advancement or location.address in square_ids(world)


def draw_regions(world, start_pool):
    """Draw objectives first, then retain only their owners and prerequisite closure."""
    if not active(world):
        return
    for field in ("vanilla_placement", "natural_progression", "mario_mode", "boss_keys"):
        if bool(getattr(getattr(world.options, field, None), "value", 0)):
            raise OptionError(f"bingo_mode does not yet support {field}; disable {field} for the boss-board prototype")
    if getattr(world, "gf_goal_choice", "auto") != "auto":
        raise OptionError("bingo_mode replaces goal; set goal to auto and choose bingo_goal instead")
    BOSS_HEALTHBARS = world.tables.modules["boss_healthbars"].BOSS_HEALTHBARS
    SWEEP_ARENA_REGION = world.tables.modules["boss_sweeps"].SWEEP_ARENA_REGION
    # Simple dungeon/field encounters only: legacy fights can require quests, final-arena
    # gates, or preceding bosses. Those need action-specific logic before joining this catalogue.
    from . import great_runes
    # Major-rune/festival fights have additional access mechanics and detection overrides.
    excluded_flags = set(great_runes.GREAT_RUNE_DETECT_FLAGS.values())
    kept = set(world.gf_eligible)
    candidates = [{"flag": flag, "region": SWEEP_ARENA_REGION[flag],
                   "label": f"Defeat {info[3]} ({SWEEP_ARENA_REGION[flag]})"}
                  for flag, info in BOSS_HEALTHBARS.items()
                  if flag not in excluded_flags and info[2] in {"field", "catacomb", "cave", "tunnel"}
                  and info[3] and SWEEP_ARENA_REGION.get(flag) in kept]
    try:
        from ..region_spine import REGION_PARENT
        selector = select_board
        catalogue = "boss-board-v1"
        if e1(world):
            from .. import bingo_e1
            from .scaling import blessing_mode
            extra = bingo_e1.candidates(BOSS_HEALTHBARS, SWEEP_ARENA_REGION, kept,
                progressive_flasks=bool(world.options.progressive_flasks.value),
                blessing_mode=blessing_mode(world),
                sweep_regions=world.tables.modules["boss_sweeps"].SWEEP_REGION)
            mapped = {c["flag"] for c in extra if c["flag"]}
            candidates = [c for c in candidates if c["flag"] not in mapped] + extra
            # Include ordinary DLC encounters too; the original catalogue predated DLC taxonomy.
            used = {c["flag"] for c in candidates}
            candidates += [{"flag": flag, "region": SWEEP_ARENA_REGION[flag],
                            "label": f"Defeat {info[3]} ({SWEEP_ARENA_REGION[flag]})"}
                           for flag, info in BOSS_HEALTHBARS.items()
                           if flag not in used and info[0].startswith(("m20", "m21", "m22", "m25", "m28", "m40", "m41", "m43", "m61"))
                           and SWEEP_ARENA_REGION.get(flag) in kept and info[3]]
            selector, catalogue = bingo_e1.select, "e1-board-v1"
        board = selector(candidates, f"{world.multiworld.seed}:{world.player}:{catalogue}",
                             region_limit=world.options.bingo_region_limit.value,
                             parents=REGION_PARENT, start_pool=(), starts=1)
    except ValueError as e:
        raise OptionError(f"{e}; increase bingo_region_limit or broaden the eligible content") from e
    world.gf_bingo_board = board
    regions = {r for cell in board for r in cell.get("regions", [cell["region"]])}
    world.gf_bingo_anchor_pool = regions & start_pool if start_pool else regions - set(REGION_PARENT)
    from ..region_spine import parent_chain
    kept = regions | {parent for region in regions for parent in parent_chain(region)}
    if not kept <= set(world.gf_eligible):
        raise OptionError("bingo objective prerequisites are outside the eligible region pool")
    return [region for region in world.gf_eligible if region in kept]


def prepare(world):
    """Reserve native bonus checks after feature ownership has been resolved."""
    if not active(world):
        return
    kept = set(world._kept())
    from . import evidence_progression_hosts
    MISSABLE_LOCATIONS = world.tables.modules["missable_locations"].MISSABLE_LOCATIONS
    trusted = evidence_progression_hosts.trusted_aps() - set(MISSABLE_LOCATIONS)
    overrides = getattr(world, "gf_extra_location_flags", {})
    native = [(aid, overrides.get(aid, flag)) for region in [world.tables.hub] + sorted(kept)
              for _name, aid, flag in world._seed_locations(region)]
    eligible = {aid for region in kept for _name, aid, _flag in world._seed_locations(region)
                if aid in trusted}
    groups = {}
    boss_flags = set(world.tables.modules["boss_healthbars"].BOSS_HEALTHBARS)
    for aid, flag in native:
        if flag and flag not in boss_flags:
            groups.setdefault(flag, set()).add(aid)
    flags = sorted(groups, key=lambda flag: hashlib.sha256(
        f"{world.multiworld.seed}:{world.player}:line:{flag}".encode()).digest())
    members, limit = [], world.options.bingo_line_sweep_size.value
    for flag in flags:
        group = groups[flag]
        # A flag flush completes the whole physical pickup, so never reserve only part of it.
        if group <= eligible and len(members) + len(group) <= limit:
            members.extend(sorted(group))
    world.gf_bingo_line_sweep = members
    # Every bingo catalogue replaces the rune ending.
    world.gf_required_runes = []
    # Detection overrides for major bosses also appear as native checks. No synthetic
    # sweep may assert the same defeat evidence. Native flag polling remains available.
    board_flags = {c["flag"] for c in world.gf_bingo_board if c["flag"]}
    world.gf_bingo_protected_checks = {aid for aid, flag in native if flag in board_flags}
    if e1(world):
        requirements = {}
        for cell in world.gf_bingo_board:
            for name, count in cell.get("requirements", []):
                requirements[name] = max(requirements.get(name, 0), count)
        world.gf_bingo_requirements = requirements
        # The progressive feature owns its supply AND ladder. Raise its declared floor
        # before either is constructed, rather than injecting copies invisible to its ladder.
        floor = requirements.get("Progressive Flask Upgrade", 0)
        if floor:
            world.options.flask_upgrade_minimum.value = max(floor, world.options.flask_upgrade_minimum.value)
    # Existing extra-location seam keeps the native pool allocator count-neutral.
    world.gf_extra_locations = list(getattr(world, "gf_extra_locations", ())) + \
        [(name, aid, 0) for name, aid in LOCATION_NAMES.items()]


@register
class Bingo(Feature):
    name = "bingo"
    OPTIONS = {"bingo_mode": BingoMode, "bingo_catalogue": BingoCatalogue, "bingo_region_limit": BingoRegionLimit, "bingo_goal": BingoGoal,
               "bingo_square_count": BingoSquareCount, "bingo_line_sweep_size": BingoLineSweepSize}

    def create_regions(self, world):
        if not active(world):
            return
        hub = world.multiworld.get_region("Roundtable Hold", world.player)
        for name, aid in LOCATION_NAMES.items():
            hub.locations.append(Location(world.player, name, aid, hub))

    def create_items(self, world):
        if not active(world):
            return []
        from BaseClasses import ItemClassification
        supplies = []
        for name, count in getattr(world, "gf_bingo_requirements", {}).items():
            if name == "Progressive Flask Upgrade":
                continue  # Existing progressive feature supplies the raised floor.
            for _ in range(count):
                item = world.create_item(name)
                item.classification = ItemClassification.progression
                supplies.append(item)
        return supplies + [world.create_item(world.get_filler_item_name()) for _ in range(25)]

    def set_rules(self, world):
        if not active(world):
            return
        mw, player = world.multiworld, world.player
        board = world.gf_bingo_board
        from BaseClasses import ItemClassification
        flask_count = getattr(world, "gf_bingo_requirements", {}).get("Progressive Flask Upgrade", 0)
        for item in mw.itempool:
            if item.player == player and item.name == "Progressive Flask Upgrade" and flask_count:
                item.classification = ItemClassification.progression
                flask_count -= 1
        # Join defeat identity to native boss reward checks. Their final rules include
        # legacy keys and action-specific quest gates, assigned by later features.
        rewards = world.tables.modules["boss_reward_lots"].BOSS_REWARD_DEFEAT
        native = {}
        for region in world._kept():
            for name, aid, flag in world._seed_locations(region):
                detect = getattr(world, "gf_extra_location_flags", {}).get(aid, flag)
                defeat = rewards.get(flag, detect)
                native.setdefault(defeat, []).append(mw.get_location(name, player))
        def reachable(state, cell):
            if not all(state.can_reach(r, "Region", player) for r in cell.get("regions", [cell["region"]])):
                return False
            if not all(state.has(name, player, count) for name, count in cell.get("requirements", [])):
                return False
            witnesses = native.get(cell["flag"], ())
            return not witnesses or any(loc.access_rule(state) for loc in witnesses)
        for cell in board:
            loc = mw.get_location(f"Bingo Square {cell['location'] - min(LOCATION_NAMES.values()) + 1:02d}", player)
            loc.access_rule = lambda state, c=cell: reachable(state, c)
        # Both own and incoming advancement obey this hard surface; no exemptions or widening.
        for loc in mw.get_locations(player):
            prev = loc.item_rule
            loc.item_rule = lambda item, p=prev, l=loc: p(item) and permits_progression(world, l, item)
        goal = world.options.bingo_goal.current_key
        count = world.options.bingo_square_count.value
        mw.completion_condition[player] = lambda state: is_complete(
            [reachable(state, c) for c in board], goal, count)

    def slot_data(self, world):
        if not active(world):
            return {}
        cells = [{k: v for k, v in c.items() if k in {"location", "flag", "region", "label", "state"}}
                 for c in world.gf_bingo_board]
        payload = {"version": 2 if e1(world) else 1, "catalogue": "ap-e1-board-v1" if e1(world) else "ap-boss-board-v1", "cells": cells,
                   "goal": world.options.bingo_goal.current_key,
                   "count": world.options.bingo_square_count.value,
                   "line_sweep": world.gf_bingo_line_sweep}
        payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return {contract.BINGO_BOARD: payload, contract.REQUIRES_CLIENT_FEATURES: ["bingo_e1_v1" if e1(world) else "bingo_v1"]}
