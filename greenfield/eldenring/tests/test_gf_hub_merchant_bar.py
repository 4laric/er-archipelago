"""#707 -- the hub-merchant bar must BAR something, and must read a tag the data actually emits.

`features/progression_surface._roundtable_merchant_aps()` exists to keep this world's progression off
Roundtable Hold's merchant rows: the hub is reachable at spawn, so a Lock or key item sold there is
"progression" you already hold on turn one.

It returned the EMPTY SET from 2026-07-24 to 2026-08-16. It filtered on the tag `ShopSlot`, and the
2026-07-24 ShopSlot rework redefined that tag as "at most ONE progression slot per MERCHANT, pinned to
a merchant-unique ware" and stopped emitting it for hub rows -- 12 `ShopSlot` rows exist game-wide and
NONE of them is in the hub. The guard was written six days before the tag it read changed meaning
underneath it, and nothing failed, because **a derivation that reads a tag the data does not supply is
indistinguishable from a derivation with nothing to do.**

So this file tests the two things that would have caught it, neither of which is "does the fix work":

  1. the tag names the bar reads are names the HUB actually carries (test_tags_are_emitted_by_the_hub);
  2. the bar is NON-EMPTY, with the count pinned (test_bar_is_non_empty_and_pinned).

and one that pins the consequence at the chokepoint rather than in the helper, because an unfired
guard is an untested one and this one had no witness for three weeks
(test_chokepoint_drops_hub_merchants).

⚠️ THE PINNED COUNTS ARE GENERATED-DATA FACTS. A regen that adds or moves hub merchant rows will move
them, and that is the test doing its job: re-measure, satisfy yourself the delta is the regen and not a
tag rework quietly emptying the guard again, then update the number here deliberately.
"""
import unittest
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
from BaseClasses import Item, ItemClassification

from .. import contract
from ..data import HUB, LOCATIONS
from ..features.progression_surface import (_HUB_MERCHANT_TAGS, _roundtable_merchant_aps,
                                            allowed_ap_ids)
from ..location_tags import (DEFAULTED_REGION_APS, ERDTREE_BURN_APS, LOCATION_TAGS,
                             SHOP_RELEASE_GATED_APS, SHOP_SLOT_PINS, SURFACE_EXCLUDE_APS)

# Every hub row carrying a merchant tag. #218 replaces the old number-anywhere-in-ESD heuristic with
# exact AwardItemLot calls: two false Hub rows retire while one real Hub award enters, for a net -1.
# 2026-08-24 (#1013): Enia's shop is VANILLA -- her 100 hub rows left the location pool entirely, so
# the bar drops 183 -> 83. The delta is exactly her row count, nothing else moved.
_PINNED_BAR = 83
# Of those, the ones a `Shop`-selecting seed would put on the surface before this bar fires: 83 minus
# the 63 covered by the other bars (the DEFAULTED / ERDTREE_BURN / SURFACE_EXCLUDE /
# SHOP_RELEASE_GATED union) = 20. Was 58 before #1013; the 38 that left were Enia's on-surface rows
# (the rest of her 100 were already covered by the release-gate bar).
_PINNED_ON_SURFACE = 20

_HUB_APS = frozenset(ap for (_n, ap, _f) in LOCATIONS.get(HUB, ()))


class TestHubMerchantBar(unittest.TestCase):

    def test_tags_are_emitted_by_the_hub(self):
        """#707's ROOT CAUSE as a test: the bar named a tag no hub row carried.

        Asserting the tag exists somewhere in LOCATION_TAGS is not enough -- `ShopSlot` passed that
        bar the whole time (12 rows, all outside the hub). The claim that has to hold is that the hub
        emits it."""
        emitted_anywhere = set()
        for tags in LOCATION_TAGS.values():
            emitted_anywhere.update(tags)
        for tag in _HUB_MERCHANT_TAGS:
            self.assertIn(tag, emitted_anywhere,
                          f"_HUB_MERCHANT_TAGS names {tag!r}, which no location carries at all.")
            hub_rows = sum(1 for ap in _HUB_APS if tag in LOCATION_TAGS.get(ap, ()))
            self.assertGreater(hub_rows, 0,
                               f"_HUB_MERCHANT_TAGS names {tag!r} but ZERO {HUB} rows carry it -- this "
                               f"is #707 exactly: the bar reads a tag the hub does not emit and "
                               f"silently bars nothing. Re-derive it from LOCATION_TAGS.")

    def test_bar_is_non_empty_and_pinned(self):
        """The acceptance criterion from #707. An unfired guard is an untested one."""
        got = _roundtable_merchant_aps()
        self.assertTrue(got, "the hub-merchant bar is EMPTY -- it is barring nothing (#707).")
        self.assertEqual(_PINNED_BAR, len(got),
                         f"hub merchant rows moved ({len(got)} vs pinned {_PINNED_BAR}). If a regen "
                         f"did this, confirm the delta is real rows and update the pin.")

    def test_bar_is_confined_to_the_hub(self):
        """The docstring's scope claim: hub MERCHANT rows only."""
        self.assertTrue(_roundtable_merchant_aps() <= _HUB_APS,
                        "the bar reaches outside Roundtable Hold.")

    def test_hub_non_merchant_checks_are_left_alone(self):
        """"...the hub's Golden Seed checks are left to the normal surface/defaulted logic." The hub
        has exactly one Seedtree row and 54 untagged ones; none is a merchant row."""
        barred = _roundtable_merchant_aps()
        seedtree = {ap for ap in _HUB_APS if "Seedtree" in LOCATION_TAGS.get(ap, ())}
        self.assertTrue(seedtree, "no hub Seedtree row -- this test has lost its subject.")
        self.assertFalse(seedtree & barred, "the bar swallowed the hub's Seedtree check(s).")

    def test_chokepoint_drops_hub_merchants(self):
        """THE WITNESS. Pins the effect where fill reads it, not in the helper.

        `Shop` is not in the default surface, so this defect never bit a default seed -- it bit the
        documented merchant-heavy selections (`Shop` / `ShopNonSpell`), which is the case the guard was
        written for. Measured through the real chokepoint with the real bars."""
        classes = set(contract.SURFACE_DEFAULT_CLASSES) | {"Shop"}
        other_bars = (frozenset(DEFAULTED_REGION_APS) | frozenset(ERDTREE_BURN_APS)
                      | frozenset(SURFACE_EXCLUDE_APS) | frozenset(SHOP_RELEASE_GATED_APS))

        # What the surface would be if this bar contributed nothing -- i.e. what shipped.
        unguarded = {ap for ap, tags in LOCATION_TAGS.items()
                     if contract.has_class(tags, classes) and ap not in other_bars}
        self.assertEqual(_PINNED_ON_SURFACE, len(unguarded & _HUB_APS),
                         "the hub's exposure under a Shop-selecting seed moved; re-measure before "
                         "updating the pin.")

        guarded = allowed_ap_ids(LOCATION_TAGS, classes, defaulted=other_bars)
        self.assertFalse(set(guarded) & _HUB_APS,
                         "hub rows survived allowed_ap_ids -- the bar is not reaching the chokepoint.")
        # ...and it removed exactly the hub, nothing else.
        self.assertEqual(unguarded - _HUB_APS, set(guarded),
                         "the bar changed the surface OUTSIDE the hub.")


class HubMerchantLocationRule(WorldTestBase):
    """A surface exclusion alone is bypassed when restricted progression spills to general fill."""
    game = "Elden Ring"
    # Full map makes the wandering-merchant positive witness deterministic: a small random draw can
    # legitimately keep none of the 12 vetted ShopSlot merchants.
    options = {"num_regions": 0}

    def test_every_hub_merchant_rejects_advancement_at_the_location_rule(self):
        item = Item("required progression probe", ItemClassification.progression, None, self.player)
        locations = {loc.address: loc for loc in self.multiworld.get_locations(self.player)}
        barred = _roundtable_merchant_aps()
        self.assertTrue(barred, "test basis: the hub merchant set vanished")
        missing = barred - locations.keys()
        self.assertFalse(missing, f"hub merchant AP ids are absent from the generated world: {missing}")
        leaked = [locations[ap].name for ap in barred if locations[ap].item_rule(item)]
        self.assertFalse(
            leaked,
            "hub merchant checks still accept required progression through general fill: %s"
            % leaked[:5])

    def test_wandering_merchant_slots_still_accept_a_great_rune(self):
        """The permanent bar owns hub-filed rows, not ordinary merchants in their real regions."""
        item = Item("Great Rune probe", ItemClassification.progression, None, self.player)
        locations = {loc.address: loc for loc in self.multiworld.get_locations(self.player)}
        present = sorted(set(SHOP_SLOT_PINS.values()) & locations.keys())
        self.assertTrue(present, "this seed contains no vetted wandering-merchant slot")
        refused = [locations[ap].name for ap in present if not locations[ap].item_rule(item)]
        self.assertFalse(
            refused,
            "the hub-only location bar swallowed wandering merchants in real regions: %s"
            % refused[:5])


if __name__ == "__main__":
    unittest.main()
