"""#701 OPTION 2 ("B"), AGAINST REAL SEEDS -- the row is regioned to its EARLIEST KEPT site.

Sibling to `test_gf_hub_collapsed_merchant_sites.py`, which asserts the generated table and the pure
rule. This file asserts the behaviour: a seed that KEEPS one of a collapsed row's sites regions the
row to the earliest kept one, gates the check on reaching that region, and lets it carry progression
again -- and a seed that keeps NONE of them falls back to option C's bar, unchanged.

🛑 THE ACCEPTANCE TEST FLIPS MEANING FROM OPTION C's, DELIBERATELY. C's seed file asserts "a seed
holding none of Patches' regions places no progression on these rows"; this one asserts "a seed
holding one of them MAY". Both are true because they are about DIFFERENT SEEDS. C's file must stay
green -- B narrows C's bar to the none-kept case, it does not remove it -- and
`TheNoneKeptFallbackIsStillOptionC` below re-states that fallback from B's side so it cannot be
deleted along with C's files.

🛑 EVERY SEED IS SEARCHED, NOT ASSUMED (C's file's rule, and it matters more here). `num_regions` is a
DRAW SIZE, so "kept Mt. Gelmir but not Limgrave" is a probability, never a guarantee; a fixture that
hoped for a shape would quietly degrade into "some seed" the first time rng consumption upstream
moved. Each test states the kept-set shape it needs and skips over seeds that do not have it.

🛑 AND EVERY POSITIVE IS PAIRED. "The rows accept a Lock now" is measured against rows that must
still refuse it (the shop-release-gated pair, whose bar option B does not own), and the fill witness
from option C -- all 19 still exist and still take an item -- is kept.
"""
import os
import sys
import unittest

import pytest

from ..location_tags import SHOP_RELEASE_GATED_APS
from .test_gf_hub_collapsed_merchant_rows import (
    COMMUNION, COMMUNION_FLAGS, EXPECTED_PATCHES, EXPECTED_TOTAL, PATCHES, PATCHES_REGIONS,
    collapsed_rows)

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

_SEED_BUDGET = 60

class _CollapsedSeedBase(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 4, "enable_dlc": False}
    auto_construct = False

    def _seed_where(self, predicate, what):
        """Build until `predicate(kept)` holds. The shape is ASSERTED, never hoped for: num_regions
        is a DRAW SIZE, so every one of these subsets is a probability, not a guarantee."""
        for seed in range(_SEED_BUDGET):
            self.world_setup(seed)
            kept = set(getattr(self.world, "gf_kept", ()))
            self.assertTrue(kept, "the world exposed no kept-region list (gf_kept)")
            if predicate(kept):
                return seed, kept
        self.fail("no seed in %d tries %s -- the draw or the region set moved; fix the fixture, do "
                  "not delete the requirement" % (_SEED_BUDGET, what))

    def _resolved(self):
        from ..features.progression_surface import collapsed_site_regions
        return collapsed_site_regions(self.world)

    def _rows(self):
        want = {ap for (_n, ap, _f) in collapsed_rows()}
        got = [loc for loc in self.multiworld.get_locations(self.player) if loc.address in want]
        # POSITIVE WITNESS, kept from option C: regioning a row must not delete it.
        self.assertEqual(len(got), EXPECTED_TOTAL,
                         "%d of the %d collapsed rows are missing from the seed" %
                         (EXPECTED_TOTAL - len(got), EXPECTED_TOTAL))
        return got

    def _own_lock(self, region=None):
        """A region Lock of ours to probe with -- the item class Cokeman5's spoiler showed."""
        ours = [i for i in self.multiworld.get_items()
                if i.player == self.player and i.advancement and i.name.endswith(" Lock")]
        self.assertTrue(ours, "this seed has no region Lock to probe with; the assertions below "
                              "would pass for want of a subject")
        if region is not None:
            named = [i for i in ours if i.name != "%s Lock" % region]
            self.assertTrue(named, "every Lock in this seed is the site's own")
            return named[0]
        return ours[0]


class CollapsedRowsTakeTheirEarliestKeptSite(_CollapsedSeedBase):
    """B's NEW case: a seed that holds a site. RED before this change -- option C bars all 19
    unconditionally, so every one of these rows refused the Lock in every seed."""

    def test_a_seed_holding_limgrave_regions_the_patches_rows_to_limgrave(self):
        seed, kept = self._seed_where(lambda k: "Limgrave" in k, "kept Limgrave")
        resolved = self._resolved()
        patches = [ap for (_n, ap, _f) in collapsed_rows() if PATCHES in _n]
        self.assertEqual(len(patches), EXPECTED_PATCHES, "the rows under test vanished")
        wrong = sorted((ap, resolved.get(ap)) for ap in patches if resolved.get(ap) != "Limgrave")
        self.assertEqual(wrong, [], "seed %d kept %r; the Patches rows should be regioned to Limgrave "
                                    "(earliest kept site): %r" % (seed, sorted(kept), wrong[:3]))

    def test_a_seed_holding_mt_gelmir_but_not_limgrave_uses_mt_gelmir(self):
        """The kept-subset that makes a hardcoded 'Limgrave' fail at the SEED level too."""
        seed, kept = self._seed_where(lambda k: "Mt. Gelmir" in k and "Limgrave" not in k,
                                      "kept Mt. Gelmir without Limgrave")
        resolved = self._resolved()
        patches = [ap for (_n, ap, _f) in collapsed_rows() if PATCHES in _n]
        self.assertEqual(len(patches), EXPECTED_PATCHES, "the rows under test vanished")
        wrong = sorted((ap, resolved.get(ap)) for ap in patches if resolved.get(ap) != "Mt. Gelmir")
        self.assertEqual(wrong, [], "seed %d kept %r: %r" % (seed, sorted(kept), wrong[:3]))

    def test_the_dragon_communion_three_follow_their_own_pair(self):
        """Caelid kept, Limgrave not: the Communion rows resolve, the Patches rows must NOT (Caelid
        is not one of their sites) -- the two families in ONE seed, so neither can ride the other."""
        seed, kept = self._seed_where(
            lambda k: "Caelid" in k and not (k & set(PATCHES_REGIONS)),
            "kept Caelid and none of Patches' regions")
        resolved = self._resolved()
        communion = [ap for (_n, ap, _f) in collapsed_rows() if COMMUNION in _n]
        patches = [ap for (_n, ap, _f) in collapsed_rows() if PATCHES in _n]
        self.assertEqual(len(communion), len(COMMUNION_FLAGS))
        self.assertEqual(sorted(resolved.get(ap) for ap in communion),
                         ["Caelid"] * len(communion),
                         "seed %d kept %r; the Dragon Communion rows must take Caelid" % (seed, sorted(kept)))
        self.assertEqual([ap for ap in patches if ap in resolved], [],
                         "a Patches row resolved a region in a seed holding none of ITS sites")

    def test_a_regioned_row_may_carry_progression_and_is_gated_on_that_region(self):
        """THE POINT OF OPTION B, in both halves: the bar lifts, and what replaces it is real."""
        from BaseClasses import CollectionState
        seed, kept = self._seed_where(
            lambda k: "Limgrave" in k
            and "Limgrave Lock" not in {i.name for i in self.multiworld.precollected_items[self.player]},
            "kept Limgrave without precollecting its Lock")
        rows = self._rows()
        resolved = self._resolved()
        lock = self._own_lock(region="Limgrave")
        by_ap = {loc.address: loc for loc in rows}
        # The rows option B lifts: regioned, and not held back by an INDEPENDENT bar. Two of the 16
        # (7774847/7774848) are also SHOP_RELEASE_GATED -- the merchant does not stock them until an
        # unlock fires -- and the Dragon Communion three are missable-barred. Lifting one cause never
        # lifts another, so those are excluded here and asserted still-barred below.
        liftable = [ap for (_n, ap, _f) in collapsed_rows()
                    if PATCHES in _n and ap in resolved and ap not in SHOP_RELEASE_GATED_APS]
        self.assertGreaterEqual(len(liftable), 10, "too few liftable rows to measure anything")
        refused = sorted(by_ap[ap].name for ap in liftable if not by_ap[ap].item_rule(lock))
        self.assertEqual(refused, [],
                         "seed %d kept Limgrave, so these rows are gated on Limgrave and may carry "
                         "progression again -- they still refuse %r: %r" % (seed, lock.name, refused[:3]))
        # ...AND THE GATE IS REAL. Without Limgrave the row is not reachable; with it, it is. A lift
        # that left the row reachable at spawn would be #701 all over again, one option later.
        st = CollectionState(self.multiworld)
        probe = by_ap[liftable[0]]
        self.assertFalse(probe.access_rule(st),
                         "%r is reachable with no Limgrave Lock held -- the row was un-barred without "
                         "being gated, which is exactly the defect #701 reported" % probe.name)
        st.collect(next(i for i in self.multiworld.get_items() if i.name == "Limgrave Lock"),
                   prevent_sweep=True)
        self.assertTrue(probe.access_rule(st),
                        "%r is STILL unreachable holding Limgrave Lock -- the gate is not the site" % probe.name)
        # CONTROL: the release-gated pair keeps its own bar. One cause at a time.
        still = [ap for (_n, ap, _f) in collapsed_rows() if ap in SHOP_RELEASE_GATED_APS]
        self.assertTrue(still, "the release-gated pair vanished; this control no longer controls")
        leaked = sorted(by_ap[ap].name for ap in still if by_ap[ap].item_rule(lock))
        self.assertEqual(leaked, [], "option B lifted a bar it does not own (shop release gate): %r" % leaked)

    def test_every_collapsed_row_still_takes_an_item(self):
        """The positive witness survives the change: regioning is not deleting."""
        from Fill import distribute_items_restrictive
        seed, _kept = self._seed_where(lambda k: "Limgrave" in k, "kept Limgrave")
        rows = self._rows()
        distribute_items_restrictive(self.multiworld)
        real = [loc for loc in rows if loc.item is not None and loc.item.code is not None]
        self.assertGreater(len(real), 0, "not one of the %d rows took a real (non-event) item -- they "
                                         "have dropped out of the fill" % EXPECTED_TOTAL)
        empty = sorted(loc.name for loc in rows if loc.item is None)
        self.assertEqual(empty, [], "seed %d left collapsed row(s) with no item: %r" % (seed, empty[:5]))


class TheNoneKeptFallbackIsStillOptionC(_CollapsedSeedBase):
    """C's case, re-asserted from B's side. If C's two files were ever deleted, this rule must not
    go with them: with no kept site there is no region to stand behind, so the bar stays."""

    def test_the_none_kept_seed_resolves_nothing_and_keeps_the_bar(self):
        seed, kept = self._seed_where(lambda k: not (k & set(PATCHES_REGIONS)),
                                      "kept none of Patches' regions")
        resolved = self._resolved()
        rows = self._rows()
        patches = [ap for (_n, ap, _f) in collapsed_rows() if PATCHES in _n]
        self.assertEqual([ap for ap in patches if ap in resolved], [],
                         "seed %d kept %r -- no Patches row may resolve a region" % (seed, sorted(kept)))
        lock = self._own_lock()
        by_ap = {loc.address: loc for loc in rows}
        accepted = sorted(by_ap[ap].name for ap in patches if by_ap[ap].item_rule(lock))
        self.assertEqual(accepted, [],
                         "option B lifted the bar with NO kept site: %r. C is B's fallback, not "
                         "something B removed" % accepted[:3])
        # The control C's own file carries: 'refuses everything' must not read as 'refuses progression'.
        others = [loc for loc in self.multiworld.get_locations(self.player)
                  if loc.address not in set(patches) and loc.item_rule(lock)]
        self.assertGreater(len(others), 0, "no location in this seed accepts %r" % lock.name)


