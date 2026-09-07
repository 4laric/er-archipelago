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
from contextlib import contextmanager


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
            assert ({id(item) for item in prog + useful + filler}
                    == {id(item) for item in multiworld.itempool}), (
                "fill_hook_shim: the unplaced items in the three pools are not the items left in "
                "multiworld.itempool -- a pass created or dropped an item")
        progitempool[:] = prog
        usefulitempool[:] = useful
        filleritempool[:] = filler
        fill_locations[:] = [loc for loc in fill_locations if loc.item is None]
        multiworld.itempool[:] = []
