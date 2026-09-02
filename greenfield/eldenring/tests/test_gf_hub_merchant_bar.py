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
from ..evidence_progression_hosts import TRUSTED_PROGRESSION_HOST_APS
from ..location_tags import (DEFAULTED_REGION_APS, ERDTREE_BURN_APS, LOCATION_TAGS,
                             SHOP_RELEASE_GATED_APS, SHOP_SLOT_PINS, SURFACE_EXCLUDE_APS)
from ..tarnished_pack import TARNISHED_PACK_LOCATION_FLAGS

# Every hub row carrying a merchant tag. #218 replaces the old number-anywhere-in-ESD heuristic with
# exact AwardItemLot calls: two false Hub rows retire while one real Hub award enters, for a net -1.
# 2026-08-24 (#1013): Enia's shop is VANILLA -- her 100 hub rows left the location pool entirely, so
# the bar drops 183 -> 83. 2026-08-28 (#1097): 35 more hub rows were generator-derived rewrites of
# curated starting/caster-kit shop blocks, not independent purchases. The block-level exclusion
# removes exactly those false checks, leaving 48 genuine Roundtable merchant rows. #1096 adds one
# optional Tarnished Pack merchant row to the static superset; it is absent from default seeds but
# must still be barred when the ownership toggle admits it. 2026-08-31 (#331): 49 -> 128 when 79
# proven multi-region rows began using the generator's documented HUB/defaulted fallback instead
# of inheriting a sibling merchant's legacy block region. #557 adds the one cookbook that a stale
# manual Limgrave override had kept outside the same derived family: 128 -> 129.
_PINNED_BAR = 129
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
        """"...the hub's non-merchant checks are left to the normal surface/defaulted logic."

        🛑 THE SUBJECT MOVED, so the assertion is stated over the CLASS instead of over one row.
        Until 2026-08-26 the hub had exactly one Seedtree row and this test named it: f400220, the
        Golden Seed. #445's ground audit re-filed it Stormveil -- the Hold was never a derivation
        for it and its lot is placed on an m10_00 enemy (see gen_data.FLAG_REGION_OVERRIDE[400220])
        -- so the hub has NO Seedtree row now and pinning one would be pinning a row that left.
        The property was never about Seedtrees: it is that this bar touches merchant rows and
        nothing else. That is what is asserted, over every non-merchant hub row, which is strictly
        more than the one-row version ever covered.
        """
        barred = _roundtable_merchant_aps()
        non_merchant = {ap for ap in _HUB_APS
                        if not any(t in _HUB_MERCHANT_TAGS for t in LOCATION_TAGS.get(ap, ()))}
        self.assertTrue(non_merchant,
                        "no non-merchant hub row at all -- this test has lost its subject.")
        self.assertFalse(non_merchant & barred,
                         "the bar swallowed non-merchant hub check(s): %r"
                         % sorted(non_merchant & barred))

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
        optional = {ap for (_n, ap, flag) in LOCATIONS.get(HUB, ())
                    if int(flag) in TARNISHED_PACK_LOCATION_FLAGS}
        self.assertEqual(missing, optional,
                         "only default-off Tarnished Pack hub merchants may be absent")
        active_barred = barred & locations.keys()
        self.assertTrue(active_barred, "no active hub merchant remained to exercise the item rule")
        leaked = [locations[ap].name for ap in active_barred if locations[ap].item_rule(item)]
        self.assertFalse(
            leaked,
            "hub merchant checks still accept required progression through general fill: %s"
            % leaked[:5])

    def test_wandering_merchant_slots_obey_the_evidence_bar(self):
        """Ordinary merchants avoid the hub bar, but HOLD checks still reject progression."""
        item = Item("Great Rune probe", ItemClassification.progression, None, self.player)
        locations = {loc.address: loc for loc in self.multiworld.get_locations(self.player)}
        present = sorted(set(SHOP_SLOT_PINS.values()) & locations.keys())
        self.assertTrue(present, "this seed contains no vetted wandering-merchant slot")
        trusted = set(TRUSTED_PROGRESSION_HOST_APS)
        wrong = [locations[ap].name for ap in present
                 if locations[ap].item_rule(item) != (ap in trusted)]
        self.assertFalse(wrong, "wandering merchant evidence policy disagrees with its ledger: %s"
                         % wrong[:5])


class TarnishedHubMerchantLocationRule(WorldTestBase):
    """The optional Roundtable row joins the same permanent progression bar when enabled."""
    game = "Elden Ring"
    options = {"num_regions": 0, "enable_tarnished_pack": True}

    def test_optional_hub_merchant_rejects_advancement(self):
        item = Item("required progression probe", ItemClassification.progression, None, self.player)
        locations = {loc.address: loc for loc in self.multiworld.get_locations(self.player)}
        optional = {ap for (_n, ap, flag) in LOCATIONS.get(HUB, ())
                    if int(flag) in TARNISHED_PACK_LOCATION_FLAGS}
        self.assertTrue(optional, "the static corpus has no Tarnished Pack hub merchant")
        self.assertTrue(optional <= locations.keys(), "enabled pack omitted its hub merchant")
        leaked = [locations[ap].name for ap in optional if locations[ap].item_rule(item)]
        self.assertFalse(leaked, "optional hub merchant accepted required progression: %s" % leaked)


if __name__ == "__main__":
    unittest.main()
