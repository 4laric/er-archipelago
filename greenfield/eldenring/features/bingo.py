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
    Requires a fresh character and this branch's client. Default off."""
    visibility = Visibility.all & ~Visibility.simple_ui
    display_name = "Bingo Mode"


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
        board = select_board(candidates, f"{world.multiworld.seed}:{world.player}:boss-board-v1",
                             region_limit=world.options.bingo_region_limit.value,
                             parents=REGION_PARENT, start_pool=(start_pool or
                                 {c["region"] for c in candidates if c["region"] not in REGION_PARENT}),
                             starts=world.options.start_regions.value)
    except ValueError as e:
        raise OptionError(f"{e}; increase bingo_region_limit or broaden the eligible content") from e
    world.gf_bingo_board = board
    regions = {cell["region"] for cell in board}
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
    # Existing extra-location seam keeps the native pool allocator count-neutral.
    world.gf_extra_locations = list(getattr(world, "gf_extra_locations", ())) + \
        [(name, aid, 0) for name, aid in LOCATION_NAMES.items()]


@register
class Bingo(Feature):
    name = "bingo"
    OPTIONS = {"bingo_mode": BingoMode, "bingo_region_limit": BingoRegionLimit, "bingo_goal": BingoGoal,
               "bingo_square_count": BingoSquareCount, "bingo_line_sweep_size": BingoLineSweepSize}

    def create_regions(self, world):
        if not active(world):
            return
        hub = world.multiworld.get_region("Roundtable Hold", world.player)
        for name, aid in LOCATION_NAMES.items():
            hub.locations.append(Location(world.player, name, aid, hub))

    def create_items(self, world):
        return [world.create_item(world.get_filler_item_name()) for _ in range(25)] if active(world) else []

    def set_rules(self, world):
        if not active(world):
            return
        mw, player = world.multiworld, world.player
        board = world.gf_bingo_board
        for cell in board:
            loc = mw.get_location(f"Bingo Square {cell['location'] - min(LOCATION_NAMES.values()) + 1:02d}", player)
            loc.access_rule = lambda state, region=cell["region"]: state.can_reach(region, "Region", player)
        # Both own and incoming advancement obey this hard surface; no exemptions or widening.
        for loc in mw.get_locations(player):
            prev = loc.item_rule
            loc.item_rule = lambda item, p=prev, l=loc: p(item) and permits_progression(world, l, item)
        goal = world.options.bingo_goal.current_key
        count = world.options.bingo_square_count.value
        mw.completion_condition[player] = lambda state: is_complete(
            [state.can_reach(c["region"], "Region", player) for c in board], goal, count)

    def slot_data(self, world):
        if not active(world):
            return {}
        payload = {"version": 1, "catalogue": "ap-boss-board-v1", "cells": world.gf_bingo_board,
                   "goal": world.options.bingo_goal.current_key,
                   "count": world.options.bingo_square_count.value,
                   "line_sweep": world.gf_bingo_line_sweep}
        payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return {contract.BINGO_BOARD: payload, contract.REQUIRES_CLIENT_FEATURES: ["bingo_v1"]}
