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


import os as _os


def find_repo_root(start, marker="tools/check_integrity.py"):
    """Absolute path of the REPO CHECKOUT, or None when we are not running from one.

    WHY THIS EXISTS. `tools/gf_test.py` copies `greenfield/eldenring` into a pinned Archipelago
    checkout at `_ap/worlds/eldenring/`, and copies NO `tools/`. A test that derives the repo root
    positionally --

        HERE=.../tests -> .../eldenring -> .../greenfield -> repo      # true in the repo
        HERE=.../tests -> .../eldenring -> .../worlds     -> _ap       # under the harness

    -- silently resolves to `_ap` there and dies on FileNotFoundError. That is exactly how 45 tests
    went green locally and errored in CI on 2026-07-27: the repo-tooling suites (check browser, desc
    triage, provenance gate) all computed `REPO` by walking up a fixed number of directories.

    So: search UPWARD for a marker that only the real checkout has, and return None rather than a
    wrong path. Callers skip on None -- under the harness those tests genuinely cannot run, because
    the thing they test is not installed. They are run by the `generators` CI job instead, which
    checks out the repo proper. Same idiom as test_gf_gen_stamp._find_up.
    """
    d = _os.path.abspath(start)
    for _ in range(8):
        if _os.path.exists(_os.path.join(d, marker)):
            return d
        nd = _os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


REPO_ONLY_REASON = (
    "needs the repo checkout (tools/ is not installed into the AP world dir by gf_test.py); "
    "the `generators` CI job runs this suite"
)


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


def assert_goal_reachable(test, world=None, label=""):
    """The winnability claim, at its THIRD carrier -- see the history below before moving it again.

    It began as `assertIn(GOAL_REGION, kept)`: an `auto`-goal seed must keep the goal region.
    SPEC-ashen-capital-lock deleted that force-keep so `num_regions: 1` could really keep one
    region, and the claim moved to `assertIn("Ashen Capital Lock", pool)` -- the goal region is
    entered with that Lock, so the Lock being in the pool meant the goal was reachable.

    ⭐ #768 (2026-08-16) withdrew the Lock from the pool: the client grants the goal region's open
    flag once every OTHER goal item is held (client#245, `er_logic::goal_gate`). So the old
    assertion now asserts the opposite of the design, and the claim moves once more -- to the
    ENTRANCE REQUIREMENT, which is the thing that actually has to be satisfiable:

      * the goal region's own Lock is NOT in the pool (it is withheld, by construction), and
      * `finale_requirement_locks` is non-empty -- an empty requirement is a goal region that
        opens at connect, which is the burn #694 filed, and
      * every name it requires is obtainable in this seed: in the pool, or precollected.

    That last one is the winnability property in full. The previous spelling only ever checked
    that ONE item existed; this checks the whole requirement can actually be met."""
    from worlds.eldenring.data import FINALE_REGION
    from worlds.eldenring.features.finale import finale_requirement_locks
    w = world if world is not None else test.world
    tag = (" [%s]" % label) if label else ""
    names = world_item_names(test)
    lock = f"{FINALE_REGION} Lock"
    test.assertNotIn(
        lock, names,
        f"{lock} is in the pool{tag} -- #768 withholds it and lets the client grant the region "
        f"once every other goal item is held. In the pool, fill can place it in sphere 1 and the "
        f"player can stand in the endgame before doing anything (#694).")
    req = list(finale_requirement_locks(w))
    test.assertTrue(
        req,
        f"the goal region's entrance requires nothing{tag} -- it would open at connect, and the "
        f"run's ending is reachable before the run (#694 'the ending plays and the run does not "
        f"end').")
    have = set(names)
    missing = [r for r in req if r not in have]
    test.assertEqual(
        missing, [],
        f"the goal region's entrance requires {missing}{tag}, which this seed never mints -- the "
        f"goal is unreachable and the seed is unwinnable (winnability). requirement={req}")
