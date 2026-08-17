"""Phase 7 progressive-items tests -- WorldTestBase.

Asserts the client contract (progressiveGrants shape + GOODS-packed positive good ids) and the pool
effect (N copies of each active progressive item, count-neutral) when a toggle is on, and that
progressiveGrants is empty {} when every toggle is off. Progressive copies are `useful`, never
progression, so the seed stays winnable in every case.
"""
import pytest

import dataclasses
import re

# progressive_flasks is NO LONGER here: it is finished, frozen ON, and covered live by
# tests/test_gf_progressive_flasks.py (the unified "Progressive Flask Upgrade" ladder).

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.core import GFOptions  # noqa: E402

# SELF-EXPIRING FREEZE (2026-08-04), now HALF EXPIRED -- and it expired the way it was built to.
#
# The module-level skip used to hold while BOTH options were off the yaml surface, so re-exposing
# EITHER one woke all 20 tests and redded a tripwire, rather than leaving them dark behind an
# "un-skip when re-exposed" comment nobody re-reads. On 2026-08-10 `progressive_stone_bells` was
# unfrozen (issue #506) and that is exactly what happened: the tripwire went red, its instruction
# was "revalidate every test in this file, then delete this tripwire and the module skipif", and
# this is that.
#
# 🛑 THE GATE IS NOW PER-OPTION, not per-module. `progressive_stonesword_keys` is STILL frozen, so
# its case still cannot be constructed from yaml and keeps its own skip and its own tripwire. A
# single `and` over both options would have silently un-guarded the keys the moment the bells woke.
_SURFACE = {f.name for f in dataclasses.fields(GFOptions)}
_BELLS_FROZEN = "progressive_stone_bells" not in _SURFACE
_KEYS_FROZEN = "progressive_stonesword_keys" not in _SURFACE

_keys_skip = pytest.mark.skipif(
    _KEYS_FROZEN,
    reason="progressive_stonesword_keys is FROZEN OFF in v0.2 (defaults.py) -- not yaml-exposed. "
           "Self-expiring: re-exposing it wakes this class and reds the keys tripwire below.")
_bells_skip = pytest.mark.skipif(
    _BELLS_FROZEN,
    reason="progressive_stone_bells is FROZEN OFF -- not yaml-exposed. It was UNFROZEN on "
           "2026-08-10, so this skip firing again means a freeze was re-applied; say why.")


def test_the_freeze_tripwire_stonesword_keys_are_still_off_the_yaml_surface():
    """Never green while un-frozen, by design -- red the commit that re-exposes the keys."""
    assert _KEYS_FROZEN, (
        "progressive_stonesword_keys is back on the yaml surface, but its cases froze with the "
        "bells on 2026-07-11 and have not tracked the feature since. Revalidate "
        "ProgressiveStoneswordKeysOn, then delete this tripwire and _keys_skip.")


def test_the_unfrozen_default_matches_the_freeze_value():
    """⭐ THE CHECK THE PoolBuilderIntensity UNFREEZE WENT WITHOUT.

    `defaults.FROZEN_OPTIONS` pins a value AND removes the option from GFOptions, so while an option
    is frozen its class `default` is unreachable and rots unobserved. Unfreezing then silently moves
    every seed that does not name the option -- which is exactly how unfreezing pool_builder_intensity
    reverted the juice catalog inside a release whose changelog said nothing had changed.

    progressive_stone_bells was frozen at 0 and its class default is 0, so no seed moves. That is a
    fact worth an assertion rather than a sentence: the freeze value IS the default."""
    from worlds.eldenring.features.progressive import ProgressiveStoneBells
    assert ProgressiveStoneBells.default == 0, (
        "ProgressiveStoneBells.default is %r, but the option was FROZEN AT 0 until 2026-08-10 -- so "
        "unfreezing it just changed the behaviour of every seed that does not name it. Either move "
        "the default back to the freeze value or say, in the changelog, what moved."
        % (ProgressiveStoneBells.default,))
from worlds.eldenring.features.progressive import (  # noqa: E402
    PROG_STONESWORD_KEY,
    PROG_SMITHING_BELL, PROG_SOMBER_BELL,
    _GOODS_LADDERS, _POOL_COUNTS, _GOODS_NIBBLE, _BELL_GRANTS, _BELL_EARLY_COUNT,
    VANILLA_BELL_ITEMS, bell_ladder_len,
)
from ._util import world_items, world_pool_items  # noqa: E402

GAME = "Elden Ring"

# A VANILLA bell bearing is `<something> Miner's Bell Bearing [N]`. The two progressive names carry
# no `[N]`, so this cannot match them by accident -- and that is asserted, not assumed, in
# test_the_vanilla_bearing_pattern_does_not_match_the_progressive_names below. Without that witness
# a pattern that matched nothing would make every "zero vanilla bearings" assertion vacuous, which
# is the exact failure shape #539 itself had (a check that was never made).
_VANILLA_BEARING_RE = re.compile(r"Miner's Bell Bearing \[\d\]$")


def _vanilla_bearings(names):
    """The VANILLA bell bearings among `names`, sorted and de-duplicated."""
    return sorted({n for n in names if _VANILLA_BEARING_RE.search(n)})


def test_the_vanilla_bearing_pattern_does_not_match_the_progressive_names():
    """WITNESS for every #539 assertion below. `zero vanilla bearings in the pool` is only evidence
    if the pattern can actually match one and cannot match a progressive copy."""
    assert _vanilla_bearings([PROG_SMITHING_BELL, PROG_SOMBER_BELL]) == []
    assert _vanilla_bearings(["Somberstone Miner's Bell Bearing [5]"]) == \
        ["Somberstone Miner's Bell Bearing [5]"]


def test_vanilla_bell_items_covers_every_bearing_the_vanilla_data_has():
    """The substitution map must name EVERY bell bearing that can pay out, or #539 comes back for
    whichever one it missed. Derived from the real data rather than hand-listed here, so an item
    rename or a regen that adds a bearing fails LOUDLY instead of quietly shrinking the map.

    2026-08-13 (#191): it is NINE. `Somberstone Miner's Bell Bearing [1]` WAS missing, and the
    stated reason -- "it is not a looted item" -- was wrong. It hangs off flag 520670 as lot 20673,
    a SIBLING of a shared-flag family, and the catalog is CHECK-derived, so until the co-check
    allowlist widened no check ever named it. It is looted. See the somber-floor ruling below."""
    from worlds.eldenring.item_ids import ITEM_CATALOG, LOCATION_ITEM
    in_data = _vanilla_bearings(LOCATION_ITEM.values())
    assert in_data, "no bell bearing in LOCATION_ITEM -- this comparison would be vacuous"
    assert sorted(VANILLA_BELL_ITEMS) == in_data, (
        "features/progressive.VANILLA_BELL_ITEMS disagrees with the vanilla data: %s"
        % sorted(set(VANILLA_BELL_ITEMS) ^ set(in_data)))
    assert len(in_data) == 9
    for n in VANILLA_BELL_ITEMS:
        assert n in ITEM_CATALOG, "%s does not resolve -- it could never be substituted" % n


def test_substitution_alone_cannot_fill_the_somber_ladder():
    """⭐ THE #539 DESIGN RULING, AS AN ASSERTION RATHER THAN A PARAGRAPH.

    The issue proposed dropping `_POOL_COUNTS` for the bells entirely and letting substitution be
    the only source of copies, matching PROG_FLASK. That is wrong for the somber bell and the
    vanilla data says so: there are only FOUR somber bell checks in the whole game against FIVE
    somber rungs, so a substitution-only pool would leave rung 5 -- the Somber Smithing Stone [9]
    shop unlock -- unreachable in EVERY seed. Hence bell_inject_count's top-up. If this ever stops
    being true (a regen finds a fifth somber check), the floor is free to become a no-op -- but that
    should be a reviewed diff, not a silent one."""
    somber = [v for v, prog in VANILLA_BELL_ITEMS.items() if prog == PROG_SOMBER_BELL]
    smithing = [v for v, prog in VANILLA_BELL_ITEMS.items() if prog == PROG_SMITHING_BELL]
    # ⭐⭐⭐ 2026-08-13 (#191): THE CONDITION THIS TEST WATCHES FOR HAS HAPPENED. Its own docstring
    # said "if this ever stops being true (a regen finds a fifth somber check), the floor is free to
    # become a no-op -- but that should be a reviewed diff, not a silent one." The widened co-check
    # allowlist found the fifth: Somberstone Miner's Bell Bearing [1] (flag 520670, lot 20673).
    #
    # 🛑 THE FLOOR IS DELIBERATELY LEFT IN PLACE. Substitution CAN now cover all five rungs, so
    # bell_inject_count's top-up is very likely redundant -- but removing it changes what a seed
    # grants, which is a ruling and not a cleanup. This test now pins the NEW data truth and the
    # fact that the floor still runs; when the ruling lands, this is the assertion to revisit.
    assert len(somber) == 5 and len(smithing) == 4
    assert bell_ladder_len(PROG_SOMBER_BELL) == 5
    assert len(somber) >= bell_ladder_len(PROG_SOMBER_BELL), (
        "the fifth somber bell check regressed out of the data -- if Somberstone [1] stopped being "
        "a check, the somber floor is load-bearing again and this test must go back to `<`")


class _BellsOnAssertions:
    """The three #539 properties, asserted against the BUILT POOL (never slot_data -- slot_data
    describes the ladder, the POOL is what the player can actually pick up). Mixed into every seed
    shape below, because the bug was invisible in the shape the old tests used: substitution removes
    a bearing only where its check was KEPT, and features/presence_floor injected every one that was
    not, so all eight were in the pool at num_regions=0 AND at num_regions=4."""

    def test_no_vanilla_bell_bearings_in_pool(self):
        """THE MOTIVATING CASE (CONTRIBUTING rule 11). boblerrr, live playtest 2026-08-10: a vanilla
        `Somberstone Miner's Bell Bearing [5]` paid out and handed over the top rung of a ladder
        that had barely started. With the ladder on, not one vanilla bearing may be in the pool."""
        from worlds.eldenring.item_ids import LOCATION_ITEM
        names = _pool_names(self.world)
        # WITNESS (test_gf_vacuous_pass's ratchet, and the reason it exists): "zero vanilla bearings"
        # is only evidence if the scan can see a pool AND the filter still matches the real names. A
        # renamed bearing would otherwise make this pass for the same reason a working fix does.
        self.assertGreater(len(names), 100, "the pool is empty -- this comparison is vacuous")
        # 8 -> 9 (2026-08-13, #191): the widened co-check allowlist placed one more vanilla
        # bearing (Somberstone Miner's Bell Bearing [1], flag 520670 lot 20673 -- a shared-flag
        # sibling that was never projected before). This is the WITNESS, not the claim: it only
        # asserts the filter still sees the real data. The claim is the zero-bearings-in-pool check
        # below, which is what proves the new one is substituted like the other eight.
        self.assertEqual(len(_vanilla_bearings(LOCATION_ITEM.values())), 9,
                         "the bearing filter no longer matches the vanilla data")
        found = _vanilla_bearings(names)
        self.assertEqual(found, [], "progressive_stone_bells is ON but the pool still holds the "
                                    "vanilla ladder: %s" % found)

    def test_bell_copies_equal_the_ladder_length(self):
        """One copy per rung, in every seed shape: no rung unreachable, no copy without a rung.
        _BELL_GRANTS is the single definition of the ladder, so it is also the expected count."""
        names = _pool_names(self.world)
        for nm in (PROG_SMITHING_BELL, PROG_SOMBER_BELL):
            self.assertEqual(names.count(nm), bell_ladder_len(nm), "%s copies != ladder rungs" % nm)

    def test_pool_stays_count_exact(self):
        """Substituting and injecting must not move the count: one pool item per location, always.

        Counted against the world's REAL locations rather than a join over data.LOCATIONS -- the
        join has to be told about feature-owned locations (the Ashen Capital) and is 12 short under
        dlc_only, which would make this assert the wrong thing in exactly the seed shape where the
        injected floor does the most work."""
        n_loc = len(list(self.world.multiworld.get_locations(self.world.player)))
        self.assertGreater(n_loc, 100, "the location set collapsed -- this comparison is vacuous")
        self.assertEqual(len(_pool_names(self.world)), n_loc)


def _assert_grant_shape(testcase, tiers):
    """A grant ladder must be a non-empty list of {"goods": GOODS-packed positive int, "flags": []}."""
    testcase.assertIsInstance(tiers, list)
    testcase.assertGreater(len(tiers), 0)
    for step in tiers:
        testcase.assertIsInstance(step, dict)
        testcase.assertIn("goods", step)
        testcase.assertIn("flags", step)
        goods = step["goods"]
        testcase.assertIsInstance(goods, int)
        testcase.assertNotIsInstance(goods, bool)
        testcase.assertGreater(goods, 0, "GOODS-packed FullID must be a positive int")
        testcase.assertEqual(goods & 0xF0000000, _GOODS_NIBBLE, "good must be GOODS-packed")
        testcase.assertIsInstance(step["flags"], list)


def _pool_names(world):
    return [it.name for it in world_pool_items(world) if it.player == world.player]


class ProgressiveOff(WorldTestBase):
    game = GAME  # the bell/key toggles default off

    def test_no_bell_or_key_grants_when_off(self):
        """REVALIDATED 2026-08-10 (the tripwire's instruction). This used to assert
        `progressiveGrants == {}`, which was true on 2026-07-11 and has been false ever since
        `progressive_flasks` was frozen ON -- the flask ladder is always in there. The suite was
        skipped for that whole period, so a test asserting a premise that had stopped holding sat
        green-by-absence for a month. Assert the thing this class is actually about: the toggles
        that are OFF contribute nothing."""
        sd = self.world.fill_slot_data()
        self.assertIn("progressiveGrants", sd)
        grants = sd["progressiveGrants"]
        # WITNESS: the dict must be populated by SOMETHING, or "the bells are absent" is what an
        # empty/missing key says too.
        self.assertTrue(grants, "progressiveGrants is empty -- progressive_flasks is frozen ON, so "
                                "its ladder should always be here; this assertion is now vacuous.")
        for nm in (PROG_STONESWORD_KEY, PROG_SMITHING_BELL, PROG_SOMBER_BELL):
            self.assertNotIn(nm, grants)

    def test_no_progressive_items_in_pool_when_off(self):
        names = set(_pool_names(self.world))
        for nm in (PROG_STONESWORD_KEY, PROG_SMITHING_BELL, PROG_SOMBER_BELL):
            self.assertNotIn(nm, names)

    def test_every_vanilla_bell_bearing_is_still_in_the_pool_when_off(self):
        """#539 GUARDS ITS OWN OFF CASE. The fix substitutes the vanilla bearings away and drops them
        from the presence floor; a seed that does not enable the toggle must be untouched by both,
        so all eight are still here. (All eight, not "some": the presence floor guarantees the ones
        whose home region was not kept, so the count does not depend on the region draw.)"""
        found = _vanilla_bearings(_pool_names(self.world))
        self.assertEqual(found, sorted(VANILLA_BELL_ITEMS),
                         "the toggle is OFF but the vanilla bell bearings moved")

    def test_pool_stays_count_exact_when_off(self):
        n_loc = len(list(self.world.multiworld.get_locations(self.world.player)))
        self.assertGreater(n_loc, 100, "the location set collapsed -- this comparison is vacuous")
        self.assertEqual(len(_pool_names(self.world)), n_loc)



@_keys_skip
class ProgressiveStoneswordKeysOn(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "progressive_stonesword_keys": True}

    def test_key_grant_shape(self):
        grants = self.world.fill_slot_data()["progressiveGrants"]
        self.assertIn(PROG_STONESWORD_KEY, grants)
        _assert_grant_shape(self, grants[PROG_STONESWORD_KEY])
        self.assertEqual(len(grants[PROG_STONESWORD_KEY]), len(_GOODS_LADDERS[PROG_STONESWORD_KEY]))
        # bells not active under this toggle
        self.assertNotIn(PROG_SMITHING_BELL, grants)

    def test_key_copies_in_pool(self):
        names = _pool_names(self.world)
        self.assertEqual(names.count(PROG_STONESWORD_KEY), _POOL_COUNTS[PROG_STONESWORD_KEY])



@_bells_skip
class ProgressiveStoneBellsOn(_BellsOnAssertions, WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "progressive_stone_bells": True}

    def test_bell_grant_shape_and_flags(self):
        grants = self.world.fill_slot_data()["progressiveGrants"]
        for nm in (PROG_SMITHING_BELL, PROG_SOMBER_BELL):
            self.assertIn(nm, grants)
            self.assertIsInstance(grants[nm], list)
            self.assertTrue(grants[nm])
            # ladder length matches the declared tier grant table
            self.assertEqual(len(grants[nm]), len(_BELL_GRANTS[nm]))
            # #804: the stock flags ARE the handed-in bearing. A physical good after these flags
            # are set is rejected by Elden Ring as already held/at capacity, then retried forever.
            for step in grants[nm]:
                self.assertIsInstance(step, dict)
                self.assertNotIn("goods", step, f"{nm} rung must not grant a physical bearing")
                self.assertEqual(set(step), {"flags"})
                self.assertIsInstance(step["flags"], list)
                self.assertTrue(step["flags"], f"{nm} rung missing shop-unlock flags")
        # keys not active under this toggle
        self.assertNotIn(PROG_STONESWORD_KEY, grants)

    def test_the_bells_have_no_fixed_pool_count(self):
        """#539: the two bells LEFT _POOL_COUNTS. A fixed count on top of substitution would ADD
        copies, which is the arithmetic that made the fix a design decision rather than a one-liner.
        This used to assert the pool held _POOL_COUNTS[...] copies of each; the count now comes from
        the ladder (test_bell_copies_equal_the_ladder_length) and the fixed entries are gone."""
        self.assertNotIn(PROG_SMITHING_BELL, _POOL_COUNTS)
        self.assertNotIn(PROG_SOMBER_BELL, _POOL_COUNTS)
        # WITNESS: the table still has an entry, so "not in" is about the bells, not an empty dict.
        self.assertIn(PROG_STONESWORD_KEY, _POOL_COUNTS)

    def test_bells_forced_early(self):
        # generate_early must have registered the sphere-0 early_items for each active bell.
        early = self.world.multiworld.early_items[self.world.player]
        for nm, n in _BELL_EARLY_COUNT.items():
            self.assertGreaterEqual(early.get(nm, 0), n, f"{nm} not forced into sphere 0")

    def test_pool_count_neutral(self):
        """The toggle may add items, never CHANGE THE COUNT -- one pool item per location, always.

        🛑 THE FINALE HAS TO BE TOLD. `_kept()` does not include FINALE_REGION: the Ashen Capital is
        never rolled, it is created per-seed by features/finale.py. This test froze on 2026-07-11,
        before that existed, and its total was 12 short of the pool for exactly that reason (4919 vs
        4931 -- and the Ashen Capital ships 12 checks). Same omission the coverage gate had to be
        taught. Revalidated 2026-08-10 when the freeze expired."""
        from worlds.eldenring.data import HUB, LOCATIONS, FINALE_REGION
        regions = [HUB] + list(self.world._kept())
        if FINALE_REGION not in regions:
            regions.append(FINALE_REGION)
        total = sum(len(LOCATIONS.get(r, [])) for r in regions)
        # WITNESS: a total of 0 would make the equality below say nothing.
        self.assertGreater(total, 1000, "the location join collapsed -- this comparison is vacuous")
        self.assertEqual(len(_pool_names(self.world)), total)


@_bells_skip
class ProgressiveStoneBellsOnDefaultRegions(_BellsOnAssertions, WorldTestBase):
    """THE SHIPPED SEED SHAPE -- the default region draw, which is what boblerrr was playing. The
    older bell case pinned num_regions=0 (every region kept), where every bell check survives and
    substitution alone would look like it had done the job; here most bell checks are sealed away
    and the copies come mostly from the injected floor. Same three assertions, different arithmetic
    reaching them."""
    game = GAME
    options = {"progressive_stone_bells": True}


@_bells_skip
class ProgressiveStoneBellsOnNoSubstitution(_BellsOnAssertions, WorldTestBase):
    """ZERO SUBSTITUTED COPIES, deterministically. With item_shuffle off core never walks the vanilla
    items, so vanilla_substitutions is never consulted and the ladder is built entirely by
    bell_inject_count -- the floor case, without having to hope a random region draw seals every bell
    check. This is the shape #539's "drop _POOL_COUNTS" would have left with a zero-copy ladder and
    a generate_early asking AP to bias a sphere-0 copy that does not exist."""
    game = GAME
    options = {"num_regions": 4, "progressive_stone_bells": True, "item_shuffle": False}
