import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.pool_compaction import CUT_NAMES, compact_name  # noqa: E402
from worlds.eldenring.item_ids import ARMOR_BUNDLES, ARMOR_NAME_TO_BUNDLE, ITEM_CATALOG  # noqa: E402
from worlds.eldenring.item_tiers import ITEM_TIER_CATEGORY  # noqa: E402

GAME = "Elden Ring"


def test_exact_weapon_names_keep_the_first_copy_only():
    seen = set()
    assert compact_name("Dagger", seen) == "Dagger"
    assert compact_name("Dagger", seen) is None
    assert compact_name("Longsword", seen) == "Longsword"


def test_cut_items_always_pay_filler():
    for name in CUT_NAMES:
        assert compact_name(name, set()) is None


def test_non_weapons_are_not_accidentally_deduplicated():
    seen = set()
    assert compact_name("Golden Rune [1]", seen) == "Golden Rune [1]"
    assert compact_name("Golden Rune [1]", seen) == "Golden Rune [1]"


def test_every_bundle_member_is_armor_and_belongs_to_exactly_one_bundle():
    members = [full for rows in ARMOR_BUNDLES.values() for full in rows]
    assert members
    assert len(members) == len(set(members))
    assert all((full & 0xF0000000) == 0x10000000 for full in members)
    assert set(ARMOR_NAME_TO_BUNDLE) == {
        name for name, full in ITEM_CATALOG.items() if full in set(members)}


def test_armor_family_compacts_to_one_wrapper_including_altered_members():
    seen_weapons, seen_bundles = set(), set()
    # Tarnished Edition 1.17 no longer exposes the old Carian Knight Armor (Altered) row. Keep the
    # property pinned to a family that the current catalog actually contains instead of testing a
    # stale name that compact_name correctly treats as an unrelated item.
    assert compact_name("Aristocrat Headband", seen_weapons, seen_bundles) == "Aristocrat Set"
    assert compact_name("Aristocrat Garb", seen_weapons, seen_bundles) is None
    assert compact_name("Aristocrat Garb (Altered)", seen_weapons, seen_bundles) is None
    assert ITEM_CATALOG["Aristocrat Garb (Altered)"] in ARMOR_BUNDLES["Aristocrat Set"]


class TightPoolUsesWrappers(WorldTestBase):
    game = GAME
    options = {"num_regions": 4}

    def test_live_pool_has_no_cut_items_or_duplicate_weapons(self):
        names = [item.name for item in self.multiworld.itempool if item.player == self.player]
        assert CUT_NAMES.isdisjoint(names)
        weapons = [name for name in names if ITEM_TIER_CATEGORY.get(name) == "WEAPON"]
        assert len(weapons) == len(set(weapons))

    def test_live_pool_uses_one_wrapper_per_present_armor_family(self):
        names = [item.name for item in self.multiworld.itempool if item.player == self.player]
        assert set(ARMOR_NAME_TO_BUNDLE).isdisjoint(names)
        wrappers = [name for name in names if name in ARMOR_BUNDLES]
        assert wrappers, "representative reduced seed must exercise armor bundling"
        assert len(wrappers) == len(set(wrappers))

    def test_slot_data_maps_every_wrapper_to_grantable_protectors(self):
        bundles = self.world.fill_slot_data()["armorBundles"]
        assert bundles
        assert all(str(self.world.item_name_to_id[name]) in bundles for name in ARMOR_BUNDLES)
        assert all((full & 0xF0000000) == 0x10000000
                   for members in bundles.values() for full in members)
