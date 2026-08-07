"""num_regions (marquee) tests -- WorldTestBase, needs AP. Gen a sealed seed and assert the kept
set, goal, and slot_data region_count. Base suite (test_fill etc.) proves it stays winnable.

REWRITTEN 2026-08-05 with the removal of the `spine` order. These two fixtures used to name the
regions they expected -- first-N of SPINE plus the goal -- which only worked because the draw was
deterministic. A random draw cannot be asserted by identity, and re-pinning to a fixed seed would
just hide the same problem behind a magic number.

What they are actually about, and what they still assert, is AGREEMENT between the four views of the
kept set that a mis-scoped seed would desynchronise: the Lock ITEMS, the instantiated REGIONS, the
slot-data COUNT, and the parent closure. None of that needs to know which regions were drawn. The
draw itself (size, closure, goal presence, reachability of every region) is covered as properties
over a 400-seed sweep in test_gf_region_selection.py.
"""
import logging

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.region_spine import GOAL_REGION, REGIONS, parent_chain  # noqa: E402
from worlds.eldenring.data import FINALE_REGION  # noqa: E402
from ._util import world_item_names  # noqa: E402

GAME = "Elden Ring"

# ⭐ THE FIFTH LOCK (SPEC-ashen-capital-lock, 2026-08-06). The Erdtree burn became a synthetic
# progression item, `Ashen Capital Lock`, minted on every seed with the base game in play -- and
# the Ashen Capital is NEVER kept (not in REGIONS, never drawn, never the anchor). So "one Lock per
# kept region and no Lock for anything else" is now "...plus exactly this one", and it is named
# rather than filtered out, because the seed's goal now lives behind it.
_FINALE_LOCK = f"{FINALE_REGION} Lock"


def _assert_views_agree(tc, n):
    """The kept set seen four ways must be ONE set. Shared by both scopes below."""
    kept = list(tc.world._kept())
    tc.assertEqual(len(kept), len(set(kept)), "duplicate region in the kept set")
    tc.assertGreaterEqual(len(kept), n, f"kept {len(kept)} regions, num_regions asked for {n}")
    # WAS `assertIn(GOAL_REGION, kept)` -- "an `auto`-goal seed must keep the goal region
    # (winnability)". compute_kept force-kept GOAL_REGION under `auto` so the goal derivation had a
    # terminus; SPEC-ashen-capital-lock deleted that force-keep, because `num_regions: 1` must be
    # able to keep ONE region (bobler's case, below). The winnability claim did not go anywhere --
    # it moved: an `auto` seed with the base game in play ends on the Ashen Capital, which exists
    # unconditionally and is entered from the HUB with this lock. So the same sentence, at its new
    # carrier: this seed has a goal, and the item that opens it is in the pool.
    tc.assertIn(_FINALE_LOCK, world_item_names(tc),
                "an `auto`-goal seed must be able to reach its goal -- the finale is the goal now, "
                "and its lock is the only way in (winnability)")
    tc.assertNotIn(FINALE_REGION, kept,
                   "the Ashen Capital must never be KEPT -- it is not a rollable region, and a "
                   "draw that could hand it to you would also count it against num_regions")

    # (1) the ITEM side: one Lock per kept region, plus the finale's, and no Lock for anything else.
    locks = sorted(name for name in world_item_names(tc) if name.endswith(" Lock"))
    tc.assertEqual(locks, sorted([f"{r} Lock" for r in kept] + [_FINALE_LOCK]),
                   "the Lock items and the kept set must be the same list (plus the finale's) -- a "
                   "Lock for a sealed region is unobtainable, a kept region with no Lock is an "
                   "unlockable gate")

    # (2) the parent closure: a gated child is never kept without its ancestors.
    for r in kept:
        for anc in parent_chain(r):
            tc.assertIn(anc, kept, f"kept child {r} without ancestor {anc}")

    # (3) the REGION side: sealed regions are never instantiated. DERIVED from the draw -- the old
    # version hardcoded "Caelid", which a random draw can legitimately keep.
    names = {r.name for r in tc.multiworld.get_regions() if r.player == tc.player}
    sealed = set(REGIONS) - set(kept)
    tc.assertTrue(sealed, f"test basis broken: num_regions={n} must seal something")
    tc.assertEqual(names & sealed, set(), "a sealed region must not be instantiated")
    # WAS `assertIn(GOAL_REGION, names)` -- the goal region was always kept, so it was always
    # built. It is not always kept any more (see above); the region the goal actually lives in is
    # the finale, and IT must be built, or the entrance the lock opens leads nowhere.
    tc.assertIn(FINALE_REGION, names,
                "the finale is the goal region on a base-game seed and must be instantiated")

    # (4) the SLOT-DATA side: region_count is the kept count, and checks actually reached it.
    sd = tc.world.fill_slot_data()
    tc.assertEqual(sd["region_count"], len(kept),
                   "slot_data.region_count must equal the kept count")
    tc.assertGreater(len(sd["locationFlags"]), 0, "no locationFlags reached the client")


class NumRegions3(WorldTestBase):
    """A mid-sized sealed seed: 3 drawn + the goal region + the parent closure."""
    game = GAME
    options = {"num_regions": 3}

    def test_every_view_of_the_kept_set_agrees(self):
        _assert_views_agree(self, 3)


class NumRegions1(WorldTestBase):
    """The MINIMUM draw. Worth its own fixture: N=1 is where a seed that mis-scopes progression has
    the least room to hide it, and it is the corner the closure has to carry on its own."""
    game = GAME
    options = {"num_regions": 1}

    def test_every_view_of_the_kept_set_agrees(self):
        _assert_views_agree(self, 1)


# ---- #409: the gen log EXPLAINS the draw ---------------------------------------------------------
#
# 🛑 THE MOTIVATING CASE (CONTRIBUTING rule 11). bobler set `num_regions: 1` on 0.3.5 and got FOUR
# regions: the draw took Liurnia, `goal: elden_beast` force-kept Farum Azula + Leyndell, and the
# parent closure pulled Altus in behind Leyndell. Every step correct; nothing said so. He asked
# twice, an hour apart, and was still unsure -- so the deliverable is not a behaviour change (#402
# ruled that the goal is NOT clamped to the kept set, and that stands) but a LINE.
#
# The rendering itself is unit-tested AP-free in test_gf_region_selection.py. What only a real world
# can prove is that the line is actually EMITTED, on the seed shape that motivated it, with a total
# that matches the kept set the rest of generation went on to use.
#
# ⭐ RE-PREMISED 2026-08-06. This used to run `num_regions: 1` + `goal: elden_beast` -- bobler's own
# yaml -- because that combination FORCED two regions and so was guaranteed to exercise all three
# clauses of the line. SPEC-ashen-capital-lock empties `elden_beast`'s forced set (the finale hangs
# off the hub behind an item now, so nothing needs keeping for it), which means that yaml no longer
# grows the draw at all -- it is the FIX, and it gets its own test below. The clause structure is
# still the deliverable, so the fixture moves to `goal: promised_consort`, the one remaining choice
# that forces a region, and SEARCHES for a draw that also triggers the closure. Exhausting the
# search FAILS rather than skips: a line that is never rendered in full is an untested line.
def test_the_gen_log_states_the_breakdown_when_the_draw_grows(caplog):
    class _T(WorldTestBase):
        game = GAME
        options = {"num_regions": 1, "goal": "promised_consort"}

    t = _T()
    t.setUp()
    try:
        for seed in range(24):
            caplog.clear()
            with caplog.at_level(logging.INFO, logger="Greenfield"):
                t.world_setup(seed=seed)
            lines = [r.getMessage() for r in caplog.records if "num_regions:" in r.getMessage()]
            assert lines, (
                "generation logged NO num_regions breakdown. That silence is #409: the player is "
                "told the number he typed and never the number he got.")
            line = lines[-1]
            if "forced by goal=" not in line or "parent closure" not in line:
                continue          # this draw does not exercise all three clauses; try the next
            kept = list(t.world._kept())
            assert len(kept) > 1, (
                "test basis broken: the line claims a forced region and a closure, so the kept "
                "set cannot be the bare draw: %r / %r" % (kept, line))
            assert line.endswith("= %d kept" % len(kept)), (
                "the logged total disagrees with the kept set (%d regions): %r" % (len(kept), line))
            assert "drawn" in line and "forced by goal=promised_consort" in line, (
                "the line must name the draw AND the goal force-keep separately -- naming only the "
                "total is the state that confused the reporter: %r" % (line,))
            for r in kept:
                assert r in line, "kept region %r is missing from the breakdown: %r" % (r, line)
            return
        pytest.fail("no seed in range(24) produced a draw with BOTH a goal force-keep and a parent "
                    "closure, so the full three-clause breakdown went UNRENDERED. Widen the range, "
                    "or a contribution has stopped being reachable -- which is itself the #409 bug")
    finally:
        t.tearDown()


# 🛑 THE MOTIVATING CASE ITSELF, now that it is fixed (CONTRIBUTING rule 11). bobler's exact yaml.
# Before SPEC-ashen-capital-lock this seed kept FOUR regions and the deliverable was a LINE
# explaining why; the spec removes the reason instead. `num_regions` is a draw size, so `1` must
# mean one drawn region -- the goal no longer force-keeps anything, because the Ashen Capital is
# reached from the hub with an item rather than by keeping Farum Azula and Leyndell.
def test_the_motivating_case_keeps_exactly_what_it_drew(caplog):
    class _T(WorldTestBase):
        game = GAME
        options = {"num_regions": 1, "goal": "elden_beast"}

    t = _T()
    with caplog.at_level(logging.INFO, logger="Greenfield"):
        t.setUp()
    try:
        kept = list(t.world._kept())
        lines = [r.getMessage() for r in caplog.records if "num_regions:" in r.getMessage()]
        assert lines, "generation logged NO num_regions breakdown (#409)"
        line = lines[-1]
        assert "forced by goal=" not in line, (
            "goal=elden_beast force-kept a region again -- that is bobler's 'num_regions: 1 gave "
            "me four regions' coming back: %r" % (line,))
        assert "num_regions: 1 drawn (" in line, (   # the line carries an "[eldenring:N] " prefix
            "the draw must be one region wide: %r" % (line,))
        # ...and the ONLY thing that may grow it is the parent closure, which is physical
        # reachability rather than a policy choice (a kept gated child needs its ancestors). The
        # drawn region is read back off the line, so this is an EXACT set equality, not a bound.
        drawn = line.split("drawn (", 1)[1].split(")", 1)[0]
        assert set(kept) == {drawn} | set(parent_chain(drawn)), (
            "kept %r is not exactly the one drawn region plus its ancestors: %r" % (kept, line))
        assert line.endswith("= %d kept" % len(kept)), (
            "the logged total disagrees with the kept set (%d regions): %r" % (len(kept), line))
    finally:
        t.tearDown()
