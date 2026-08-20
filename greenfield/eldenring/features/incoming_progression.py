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
    """Balance progression evenly across the distinct games at the table.

    N is the number of distinct games. Every partner game receives its own near-1/N share of this
    slot's travelling progression, and this slot reserves a 1/N share of every partner game's
    eligible advancement on its Progression Surface. Two slots of one game count as one game and
    are sampled fairly across their players. Items a player keeps local are never taken.

    The outgoing half only reshapes ``cross_game_progression: auto``. An explicit percentage --
    including 0 -- keeps its declared meaning and wins over this option. The incoming half runs
    whenever this is enabled and more than one game is present.

    Shares are capacity-aware: when a partner game has fewer open locations than its share, or
    the Progression Surface cannot host the full incoming request, the share is capped at what
    fits and the generation log states requested-versus-reserved per game. A placement the rules
    or reachability refuse outright still fails generation with a diagnostic. This concerns
    progression-classified placements, not whether every item survives the spoiler's
    redundant-route pruning.

    Disable for Archipelago's ordinary asymmetric fill.
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
    from Fill import fill_restrictive
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
            # DERIVED CAP, stated loudly, never a generation failure: a later ER slot takes what
            # remains after its balanced siblings reserved theirs. The refused-placement error
            # below stays fatal -- that one is a geometry problem, not an arithmetic one.
            take = min(quota, len(available))
            if take < quota:
                _LOG.warning(
                    "[eldenring:%s] incoming progression: %s share capped %d -> %d -- other "
                    "opted-in Elden Ring slots already reserved the rest of the pool.",
                    world.player, game, quota, take)
            picked = fair_sample_by_player(available, take, multiworld.random)
            requested.extend(picked)
            audit.append((game, len(available), quota))

        if not requested:
            for game, count, quota in audit:
                _LOG.info(
                    "[eldenring:%s] incoming progression: %s has %d eligible advancement; "
                    "requested %d (1/%d)", world.player, game, count, quota, game_count)
            continue
        if len(locations) < len(requested):
            # DERIVED CAP #2: the surface can only host what it has open. 1/N of a big partner
            # pool (Hollow Knight: 270 advancement) can exceed the whole surface -- the shipped
            # two-game smoke measured 135 requested vs 134 open, and a default-on option that
            # fails the shipped configuration is a defect, not a promise. Uniform trim after the
            # per-player fair sample keeps the mix representative; the log carries the exact
            # requested-vs-reserved numbers per game.
            multiworld.random.shuffle(requested)
            dropped = requested[len(locations):]
            requested = requested[:len(locations)]
            kept = {}
            for item in requested:
                kept[multiworld.worlds[item.player].game] = kept.get(
                    multiworld.worlds[item.player].game, 0) + 1
            detail = ", ".join(f"{game}: {kept.get(game, 0)}/{quota}"
                               for game, _count, quota in audit)
            _LOG.warning(
                "[eldenring:%s] incoming progression: surface capacity caps the reservation at "
                "%d of %d requested item(s) (%s -- reserved/requested). Widen "
                "progression_surface to host the full share.",
                world.player, len(requested), len(requested) + len(dropped), detail)

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
                    # full accessibility, read off the option class rather than hardcoding the
                    # enum -- AP has renamed/renumbered accessibility values before.
                    acc.value = getattr(type(acc), "option_full", 0)
            fill_restrictive(
                multiworld, state, locations, batch,
                lock=True, allow_partial=True, one_item_per_player=True,
                name="Elden Ring Balanced Incoming Progression")
        finally:
            for acc, value in saved:
                acc.value = value
        placed = len(requested) - len(batch)
        if batch:
            # Refusals DEGRADE LOUDLY rather than failing the table -- the outgoing half and the
            # #918 useful-export pass both settled on the same rule. The refused items rejoin the
            # general pool, and the log names them.
            multiworld.itempool.extend(batch)
            names = ", ".join(f"{item.name} (P{item.player})" for item in batch[:8])
            detail = ", ".join(f"{game}: {quota}/{count}" for game, count, quota in audit)
            _LOG.warning(
                "[eldenring:%s] incoming progression: placed %d/%d reserved item(s); rules or "
                "reachability refused %d, returned to the general pool (%s). First refused: %s",
                world.player, placed, len(requested), len(batch), detail, names)

        for game, count, quota in audit:
            _LOG.info(
                "[eldenring:%s] incoming progression: %s has %d eligible advancement; "
                "reserved %d (1/%d)", world.player, game, count, quota, game_count)


@register
class IncomingProgressionFeature(Feature):
    name = "incoming_progression"
    OPTIONS = {"balance_progression_across_games": BalanceProgressionAcrossGames}
