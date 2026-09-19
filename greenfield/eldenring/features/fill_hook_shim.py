"""The one adapter between core's `stage_fill_hook` signature and our seven placement passes.

`stage_fill_hook` hands us the unplaced items already split into three classified pools
(`progitempool` / `usefulitempool` / `filleritempool`) and the shuffled open-location list, and
from that moment `multiworld.itempool` is dead: `distribute_items_restrictive` never reads it
again in the `balanced` algorithm. Our passes, all seven of them, pop their batch from
`multiworld.itempool` and return leftovers to it, and every one of them builds reachability with
`multiworld.get_all_state(False)`, which *collects* `multiworld.itempool` (`BaseClasses.py:434`).
Run them against an empty pool and they would see a world with no items and refuse everything.

So rather than teach seven passes (~600 lines with measured behaviour and tests keyed on
`multiworld.itempool`) a new dialect, `pool_view` restores the view they expect for the duration
of the hook and reconciles core's lists on the way out. The whole contract difference lives here.
If a pass is ever rewritten to take the pools directly it simply stops needing the shim.

See docs/specs/SPEC-fill-hook-migration-20260907.md section 2, and its parent
SPEC-core-fill-hooks-upstream-20260907.md section 0 for why the hook is the right one.
"""
from collections import Counter
from contextlib import contextmanager


def _who(multiworld, player):
    """`Name (Game)` for a player id, degrading to the bare id when the multiworld cannot say."""
    try:
        return "%s (%s)" % (multiworld.get_player_name(player), multiworld.worlds[player].game)
    except Exception:  # noqa: BLE001 -- diagnostics must never mask the error they describe
        return "player %s" % (player,)


def _describe(multiworld, items, limit=6):
    """`3x Small Heart [Name (Game)], ...` -- the most common (owner, name) pairs in `items`."""
    counts = Counter((item.player if hasattr(item, "player") else None, item.name) for item in items)
    parts = ["%dx %s [%s]" % (n, name, _who(multiworld, player))
             for (player, name), n in counts.most_common(limit)]
    more = len(counts) - limit
    return ", ".join(parts) + (", and %d more kind(s)" % more if more > 0 else "")


@contextmanager
def pool_view(multiworld, progitempool, usefulitempool, filleritempool, fill_locations):
    """Present the three pools as `multiworld.itempool` for the body, then reconcile.

    Enter: `multiworld.itempool` becomes prog + useful + filler -- the same Item objects core
    holds, not copies, so a pop/extend by a pass is visible to the reconciliation below.

    Exit (always, including on exception): rebuild each pool BY FILTERING THE ORIGINAL on
    `item.location is None`, which preserves core's shuffled order and makes it impossible for an
    item to change classification; drop filled locations from `fill_locations`; then empty
    `multiworld.itempool` so the dead list stays dead and any later reader fails loudly.
    """
    # BEFORE we touch anything: an item that already has a location is not unplaced, so it has no
    # business in these pools. Every world's own `fill_hook` runs before this stage hook and gets
    # the same three lists, and a hook that places an item without removing THAT OBJECT from its
    # pool (`list.remove(item)` matches by name and player, so it removes an unplaced twin instead)
    # leaves the placed item behind. That is not ours to repair -- the twin is already gone -- and
    # it used to surface at exit as "a pass created or dropped an item", which sent the reader
    # into our own passes. Name the owner instead. (2026-09-18: alttpr's pot hook, build of
    # 2026-08-28, fixed upstream in 7235bc60 by removing by identity.)
    stale = [item for pool in (progitempool, usefulitempool, filleritempool)
             for item in pool if item.location is not None]
    if stale:
        raise AssertionError(
            "fill_hook_shim: %d item(s) were already PLACED when Elden Ring's stage_fill_hook "
            "started, yet are still in the unplaced pools: %s. Some world's own fill_hook placed "
            "them without removing them from the pool it was handed -- not an Elden Ring pass. "
            "Update or disable that world's apworld." % (len(stale), _describe(multiworld, stale)))
    multiworld.itempool[:] = list(progitempool) + list(usefulitempool) + list(filleritempool)
    try:
        yield
    finally:
        prog = [item for item in progitempool if item.location is None]
        useful = [item for item in usefulitempool if item.location is None]
        filler = [item for item in filleritempool if item.location is None]
        if __debug__:
            # A pass that created a NEW item instead of returning the one it popped, or dropped one
            # on the floor, shows up here rather than as a missing item three passes later. None of
            # today's seven does either (`progression_surface.apply:1785` creates filler, but it
            # runs in `pre_fill`, not under this view).
            unplaced_ids = {id(item) for item in prog + useful + filler}
            pool_ids = {id(item) for item in multiworld.itempool}
            if unplaced_ids != pool_ids:
                only_pools = [item for item in prog + useful + filler if id(item) not in pool_ids]
                only_view = [item for item in multiworld.itempool if id(item) not in unplaced_ids]
                raise AssertionError(
                    "fill_hook_shim: the unplaced items in the three pools are not the items left "
                    "in multiworld.itempool -- a pass created or dropped an item. In the pools "
                    "only: %s. In multiworld.itempool only: %s (%d already placed)."
                    % (_describe(multiworld, only_pools) or "none",
                       _describe(multiworld, only_view) or "none",
                       sum(1 for item in only_view if item.location is not None)))
        progitempool[:] = prog
        usefulitempool[:] = useful
        filleritempool[:] = filler
        fill_locations[:] = [loc for loc in fill_locations if loc.item is None]
        multiworld.itempool[:] = []
