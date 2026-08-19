"""Merchant bells may not enter a seed when every physical merchant region is sealed (#560)."""
import unittest

import pytest

from ..item_ids import ITEM_CATALOG
from ..merchant_bell_pool import merchant_bell_pool_allowed
from ..shop_data import MERCHANT_BELL_REGIONS

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
from ..data import HUB, LOCATIONS  # noqa: E402
from ..item_ids import LOCATION_ITEM  # noqa: E402


class MerchantBellPoolPolicy(unittest.TestCase):
    def test_generated_table_is_live_and_includes_empty_fail_closed_cases(self):
        self.assertEqual(len(MERCHANT_BELL_REGIONS), 36,
                         "the 36 menu-opening merchant bells changed; re-audit the hand-in table")
        self.assertEqual(MERCHANT_BELL_REGIONS[ITEM_CATALOG["Gostoc's Bell Bearing"]],
                         frozenset({"Stormveil"}))
        self.assertEqual(MERCHANT_BELL_REGIONS[ITEM_CATALOG["Rogier's Bell Bearing"]],
                         frozenset({"Stormveil"}),
                         "#558 resolved the two formerly-dark m10_00 merchants to Stormveil")
        empty = [gid for gid, regions in MERCHANT_BELL_REGIONS.items() if not regions]
        self.assertEqual(empty, [1073750758],
                         "Nomadic Merchant [11] is the sole zero-row fail-closed bell")

    def test_bell_is_allowed_when_any_merchant_region_is_kept(self):
        catalog = {"Bell": 123}
        regions = {123: frozenset({"Liurnia", "Mt. Gelmir"})}
        self.assertTrue(merchant_bell_pool_allowed(
            "Bell", {"Liurnia"}, item_catalog=catalog, bell_regions=regions))

    def test_bell_is_excluded_when_no_merchant_region_is_kept(self):
        catalog = {"Bell": 123}
        regions = {123: frozenset({"Weeping"})}
        self.assertFalse(merchant_bell_pool_allowed(
            "Bell", {"Liurnia", "Raya Lucaria Academy"},
            item_catalog=catalog, bell_regions=regions))

    def test_empty_evidence_fails_closed(self):
        self.assertFalse(merchant_bell_pool_allowed(
            "Bell", {"Roundtable Hold"}, item_catalog={"Bell": 123},
            bell_regions={123: frozenset()}))

    def test_unmapped_release_only_bell_is_unchanged(self):
        self.assertTrue(merchant_bell_pool_allowed(
            "Bone Peddler's Bell Bearing", set(),
            item_catalog={"Bone Peddler's Bell Bearing": 456}, bell_regions={}))


class MerchantBellPoolOutcome(WorldTestBase):
    """A small base seed exercises the production caller, not only the pure predicate."""
    game = "Elden Ring"
    options = {"num_regions": 3, "enable_dlc": False}

    def test_no_mapped_bell_in_the_pool_has_every_merchant_sealed(self):
        kept = frozenset([HUB] + list(self.world._kept()))
        excluded = set()
        for region in kept:
            for _name, ap_id, _flag in LOCATIONS.get(region, ()):
                item = LOCATION_ITEM.get(ap_id)
                if item and not merchant_bell_pool_allowed(item, kept):
                    excluded.add(item)
        self.assertTrue(excluded,
                        "fixture seed excludes no merchant bell; the production gate has no witness")
        leaked = sorted(item.name for item in self.multiworld.itempool
                        if item.player == self.player and item.name in excluded)
        self.assertEqual(leaked, [],
                         "merchant bells with no kept merchant leaked into the randomized pool")

    def test_filter_is_count_neutral(self):
        own_pool = [item for item in self.multiworld.itempool if item.player == self.player]
        own_open = [loc for loc in self.multiworld.get_unfilled_locations(self.player)]
        self.assertEqual(len(own_pool), len(own_open),
                         "filtered bells must pay the normal filler path one-for-one")


if __name__ == "__main__":
    unittest.main()
