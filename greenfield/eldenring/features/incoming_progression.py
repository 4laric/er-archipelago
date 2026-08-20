"""Reserve a representative share of every partner game's progression in Elden Ring.

Archipelago's ordinary fill is intentionally free to produce an asymmetric multiworld.  That is
usually desirable, but it means an Elden Ring slot can export several of its own keys while hosting
none of its partners' advancement.  ``balance_progression_across_games`` defaults to a different
shape: for every other game represented at the table, reserve 1/N of that game's
eligible unplaced advancement on this slot's progression surface, where N is the number of distinct
games.  The outgoing half lives beside the existing cross-game pass in progression_surface.py.

This is a PLACEMENT guarantee, not a playthrough guarantee.  The spoiler's reduced playthrough may
later prune an advancement item whose route proved redundant.
"""
from collections import defaultdict, deque
import logging

from Options import Toggle

from ..registry import Feature, register

_LOG = logging.getLogger("eldenring")


class BalanceProgressionAcrossGames(Toggle):
    """Balance Elden Ring progression with every represented partner game.

    N is the number of distinct games in the multiworld. Every partner receives its own near-1/N
    share of this slot's fill-visible progression, and this slot receives a 1/N share from every
    partner game. Items that their owner requires to remain local are excluded. The incoming
    reservation uses this slot's Progression Surface and obeys normal item, location, and
    reachability rules. Generation fails with a capacity diagnostic if the requested share cannot
    legally fit.

    Disable it for Archipelago's ordinary asymmetric fill. This guarantees advancement-classified
    placements. It cannot guarantee that every reserved
    item remains in the spoiler's minimal playthrough after redundant routes are pruned.
    """
    display_name = "Balance Progression Across Games"
    default = 1


def requested_share(eligible: int, game_count: int) -> int:
    """Nearest-integer 1/N share, with halves rounded up (unlike Python's bankers' round)."""
    if eligible <= 0 or game_count <= 1:
        return 0
    return (eligible + game_count // 2) // game_count


def fair_sample_by_player(items, count: int, rng):
    """Choose ``count`` items round-robin across owner slots, deterministically under ``rng``."""
    if count <= 0:
        return []
    buckets = defaultdict(list)
    for item in items:
        buckets[item.player].append(item)
    players = sorted(buckets)
    rng.shuffle(players)
    queues = {}
    for player in players:
        rng.shuffle(buckets[player])
        queues[player] = deque(buckets[player])
    chosen = []
    while len(chosen) < count:
        advanced = False
        for player in players:
            if queues[player]:
                chosen.append(queues[player].popleft())
                advanced = True
                if len(chosen) == count:
                    break
        if not advanced:
            break
    return chosen


def _enabled(world) -> bool:
    opt = getattr(getattr(world, "options", None), "balance_progression_across_games", None)
    return bool(int(getattr(opt, "value", opt or 0)))


def _eligible_by_game(multiworld, er_players):
    """Foreign advancement still in the pool, excluding owner-local item names."""
    out = defaultdict(list)
    for item in multiworld.itempool:
        if item.player in er_players or not item.advancement:
            continue
        owner = multiworld.worlds[item.player]
        local_opt = getattr(getattr(owner, "options", None), "local_items", None)
        local = set(getattr(local_opt, "value", local_opt or ()))
        if item.name in local:
            continue
        out[owner.game].append(item)
    return out


def reserve_incoming_progression(multiworld, worlds) -> None:
    """Stage-pre-fill reservation for every opted-in Elden Ring world."""
    destinations = [world for world in worlds if _enabled(world)]
    if not destinations:
        return

    # Imports stay local so the pure quota/sampling helpers remain cheap to test without an AP fill.
    from Fill import FillError, fill_restrictive
    from .progression_surface import _open_allowed, _selection, selected_surface

    er_players = {world.player for world in worlds}
    game_count = len({world.game for world in multiworld.worlds.values()}) or 1
    eligible = _eligible_by_game(multiworld, er_players)

    # Do not let slot number decide who gets first pick.  The RNG order is seed-deterministic and
    # every destination receives its independently requested 1/N share or generation fails.
    multiworld.random.shuffle(destinations)
    for world in destinations:
        locations = _open_allowed(world, selected_surface(_selection(world)))
        multiworld.random.shuffle(locations)
        requested = []
        audit = []
        for game in sorted(eligible):
            available = [item for item in eligible[game] if item in multiworld.itempool]
            # Every opted-in ER slot asks for the same 1/N share of the source game's ORIGINAL
            # eligible pool. Recomputing from the remainder would make later slots receive a
            # geometrically smaller share purely because the RNG happened to visit them later.
            quota = requested_share(len(eligible[game]), game_count)
            picked = fair_sample_by_player(available, quota, multiworld.random)
            if len(picked) != quota:
                raise FillError(
                    f"[eldenring:{world.player}] Balance Progression Across Games requests "
                    f"{quota} item(s) from {game}, but only {len(available)} remain after the other "
                    "opted-in Elden Ring slots were reserved. Reduce the number of receiving slots "
                    "or disable the option on one of them.")
            requested.extend(picked)
            audit.append((game, len(available), quota))

        if not requested:
            for game, count, quota in audit:
                _LOG.info(
                    "[eldenring:%s] incoming progression: %s has %d eligible advancement; "
                    "requested %d (1/%d)", world.player, game, count, quota, game_count)
            continue
        if len(locations) < len(requested):
            detail = ", ".join(f"{game}: {quota}/{count}" for game, count, quota in audit)
            raise FillError(
                f"[eldenring:{world.player}] Balance Progression Across Games requests "
                f"{len(requested)} item(s), but only {len(locations)} open Progression Surface "
                f"location(s) remain ({detail}). Widen progression_surface or disable the option.")

        selected = {id(item) for item in requested}
        multiworld.itempool[:] = [item for item in multiworld.itempool if id(item) not in selected]
        batch = list(requested)
        state = multiworld.get_all_state(False)
        # fill_restrictive keys its minimal-accessibility shortcut to the ITEM OWNER, not the
        # destination. Force the owners represented in this batch to full for this call so every
        # reserved ER location is actually checked for reachability; restore even on a FillError.
        owners = {item.player for item in requested}
        saved = []
        try:
            for player in owners:
                acc = getattr(getattr(multiworld.worlds[player], "options", None), "accessibility", None)
                if acc is not None and hasattr(acc, "value"):
                    saved.append((acc, acc.value))
                    acc.value = 0
            fill_restrictive(
                multiworld, state, locations, batch,
                lock=True, allow_partial=True, one_item_per_player=True,
                name="Elden Ring Balanced Incoming Progression")
        finally:
            for acc, value in saved:
                acc.value = value
        placed = len(requested) - len(batch)
        if batch:
            # The generation is about to fail, but restore the pool so diagnostic tooling sees a
            # coherent item count rather than interpreting this feature's attempted batch as loss.
            multiworld.itempool.extend(batch)
            names = ", ".join(f"{item.name} (P{item.player})" for item in batch[:8])
            detail = ", ".join(f"{game}: {quota}/{count}" for game, count, quota in audit)
            raise FillError(
                f"[eldenring:{world.player}] Balance Progression Across Games placed only "
                f"{placed}/{len(requested)} requested item(s); locality, reachability, or location "
                f"rules refused {len(batch)} ({detail}). First refused: {names}")

        for game, count, quota in audit:
            _LOG.info(
                "[eldenring:%s] incoming progression: %s has %d eligible advancement; "
                "reserved %d (1/%d)", world.player, game, count, quota, game_count)


@register
class IncomingProgressionFeature(Feature):
    name = "incoming_progression"
    OPTIONS = {"balance_progression_across_games": BalanceProgressionAcrossGames}
