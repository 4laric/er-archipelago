"""Reserve this world's fair share of USEFUL exports into non-Elden-Ring worlds (#918's ruling).

THE PROBLEM, measured (2026-08-10, the confine curve): at the shipped
``confine_foreign_progression: 100`` a non-ER partner receives 0.0% useful items from us -- 498 of
498 placements were filler against a pool that is ~40% useful. Not a rule anywhere: it is a
FILL-ORDER ARTIFACT. Confine holds the partner's own progression to the partner's own locations,
which saturates them during ``fill_restrictive``; by the time AP's ``remaining_fill`` runs, the few
partner slots left sit at the BACK of the location list, and remaining_fill places the whole useful
tier FIRST from the FRONT. The useful tier is exhausted before the scan ever reaches a partner
slot. Per-class export rate measured filler 26.4% vs useful 1.6% -- a 16x suppression that no
locality option asked for.

THE RULING (Alaric, 2026-08-20): confine stays at 100 -- its INCOMING curation is the point of the
default -- and the export half is fixed at its own layer: a dedicated reservation pass places our
useful share into non-ER worlds before the ordering artifact can starve them.

THE SHARE IS A FIXED DERIVATION, not a knob (Alaric, same ruling): uniformity. AP spreads items in
proportion to open locations, so absent the artifact a non-ER share of the open grid would receive
the same share of our useful tier. ``N = round(useful_pool x non-ER open / all open)`` is exactly
that number, derived per seed -- it scales with multiworld shape and cannot go stale the way a
pinned count would.

MECHANISM: the #904 pattern (``keep_out_of_shops.reserve_forbidden_items`` proved it): sample N,
pop them from the pool, ``fill_restrictive`` them into non-ER unfilled locations only, return any
leftovers to the pool with a WARN. The batch is popped BEFORE the reachability state is built --
stated because #904 built its state first and the review flagged the circular-placement shape;
useful items never gate reachability, but the cheap correct order costs nothing.

Exclusions from the sample: names in ``options.local_items.value`` (keep_local /
exclude_local_item_only already flow through it -- AP's fill would refuse them on foreign
locations anyway; excluding them here avoids burning reservation slots on refusals).

ORDERING in stage_pre_fill: after the released-Lock placement (progression first), BEFORE
keep_out_of_shops.finalize_rules -- exporting an item shrinks what must fit in the owner's
non-shop grid, so capacity finalisation sees the truer, smaller demand.

What this deliberately does NOT touch: ER-to-ER traffic (measured healthy at 43.1% useful with no
help), progression exports (the ``progression_bias`` / ``cross_game_progression`` levers own
those), and the confine option itself.
"""
import logging
from typing import List

_LOG = logging.getLogger("eldenring")


def eligible_useful(world) -> List:
    """This world's exportable useful items: useful-classified, not advancement, not held local."""
    local = set(getattr(world.options, "local_items", None)
                and world.options.local_items.value or ())
    return [item for item in world.multiworld.itempool
            if item.player == world.player
            and item.useful and not item.advancement
            and item.name not in local]


def reservation_size(useful_count: int, foreign_open: int, all_open: int) -> int:
    """The uniformity share: what AP would send absent the displacement artifact. Pure."""
    if useful_count <= 0 or foreign_open <= 0 or all_open <= 0:
        return 0
    n = round(useful_count * foreign_open / all_open)
    return min(n, foreign_open)


def reserve_useful_exports(multiworld, worlds) -> None:
    """Place every ER world's derived useful share into non-ER locations before general fill."""
    er_players = {w.player for w in worlds}
    foreign_players = [p for p in multiworld.player_ids if p not in er_players]
    if not foreign_players:
        return  # ER-only multiworld: the artifact does not exist (ER-to-ER measured healthy)

    all_open = [loc for loc in multiworld.get_unfilled_locations()
                if getattr(loc, "address", None) is not None]
    foreign_open = [loc for loc in all_open if loc.player in set(foreign_players)]
    if not foreign_open:
        return

    batch = []
    for world in worlds:
        useful = eligible_useful(world)
        n = reservation_size(len(useful), len(foreign_open), len(all_open))
        if n <= 0:
            continue
        world.random.shuffle(useful)
        picked = useful[:n]
        batch.extend(picked)
        _LOG.info(
            "[eldenring:%s] export-reservation: %d of %d eligible useful item(s) reserved for "
            "%d non-ER location(s) (of %d open) -- the uniformity share (#918).",
            world.player, len(picked), len(useful), len(foreign_open), len(all_open))
    if not batch:
        return

    # Pop the batch FIRST, then build the state -- the reverse order lets an item help prove the
    # reachability of its own placement (the #904 review note, applied).
    selected = {id(item) for item in batch}
    multiworld.itempool[:] = [item for item in multiworld.itempool if id(item) not in selected]
    state = multiworld.get_all_state(False)

    from Fill import fill_restrictive
    total = len(batch)
    locations = list(foreign_open)
    multiworld.random.shuffle(batch)
    multiworld.random.shuffle(locations)
    fill_restrictive(
        multiworld, state, locations, batch,
        lock=True, allow_partial=True, one_item_per_player=True,
        name="Useful Export Reservation")
    placed = total - len(batch)

    if batch:
        # A partner's own rules (excluded locations, plando, tight pools) can refuse more than the
        # open-count arithmetic predicts. Generation still wins: leftovers rejoin the normal fill,
        # and the log says exactly how far the share degraded.
        multiworld.itempool.extend(batch)
        _LOG.warning(
            "[greenfield] export-reservation: placed %d of %d reserved useful item(s); %d "
            "returned to the general pool (partner-side location rules refused them). The "
            "partner still receives at least the placed share.",
            placed, total, len(batch))
    else:
        _LOG.info(
            "[greenfield] export-reservation: all %d reserved useful item(s) placed in non-ER "
            "worlds before general fill.", total)
