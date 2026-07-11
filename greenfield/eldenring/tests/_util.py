"""Shared test helpers -- progression_surface awareness.

Since v0.2, greenfield's `pre_fill` (core.pre_fill -> progression_surface.apply) fill-places THIS
world's own progression (region Locks, required/gate Great Runes, folded-dungeon legacy keys) via
fill_restrictive, and `start_with_region_lock` precollects one Lock. `gen_steps` (used by
WorldTestBase.world_setup) runs `pre_fill`, so after setup those items are NO LONGER in
`multiworld.itempool` -- they sit in `precollected_items` or are already placed on a location.

Tests that assert on this world's created items must therefore look across all three buckets, not
just `itempool`. `world_items` returns every item this world created regardless of where pre_fill put
it, so it stays count-neutral: len(world_items) == number of this world's locations.
"""


def world_items(test):
    """All items this world CREATED (unplaced itempool + precollected + pre-placed on locations),
    restricted to this player. Order not guaranteed."""
    p = test.player
    mw = test.multiworld
    out = [i for i in mw.itempool if i.player == p]
    out += list(mw.precollected_items[p])
    out += [loc.item for loc in mw.get_locations(p)
            if loc.item is not None and loc.item.player == p]
    return out


def world_item_names(test):
    return [i.name for i in world_items(test)]


def world_pool_items(test):
    """Location-PAYING items = unplaced (itempool) + pre-placed on locations, this player. EXCLUDES
    precollected items: a precollected region Lock is replaced by filler in the pool (and start items
    are free extras), so counting precollected would double-count. Count-neutral basis:
    len(world_pool_items) == number of this world's locations."""
    p = test.player
    mw = test.multiworld
    out = [i for i in mw.itempool if i.player == p]
    out += [loc.item for loc in mw.get_locations(p)
            if loc.item is not None and loc.item.player == p]
    return out
