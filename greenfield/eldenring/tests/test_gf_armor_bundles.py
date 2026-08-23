"""armor_bundles option (world#985): the #849 set-wrappers become a YAML Toggle.

on (default) is the shipped behavior and is covered by test_gf_pool_compaction.py's live-pool
worlds; this file owns the OFF state -- no wrapper items, no `armorBundles` wire, and no
`armor_bundles` client-feature demand, so an older client accepts the seed.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.item_ids import ARMOR_BUNDLES  # noqa: E402

GAME = "Elden Ring"


class ArmorBundlesOffSeed(WorldTestBase):
    game = GAME
    options = {"armor_bundles": False, "num_regions": 4}

    def test_no_wrapper_items_in_pool_when_off(self):
        names = [item.name for item in self.multiworld.itempool if item.player == self.player]
        # Witnesses first: an empty pool or an empty bundle table would make the disjointness
        # assert vacuous (test_gf_vacuous_pass).
        assert names and ARMOR_BUNDLES
        wrappers = set(ARMOR_BUNDLES) & set(names)
        assert not wrappers, (
            "armor_bundles: false still minted wrapper items: %s -- the pool_compaction gate in "
            "core.create_items is not reading the option" % sorted(wrappers))

    def test_armor_bundle_wire_absent_when_off(self):
        sd = self.world.fill_slot_data()
        assert "armorBundles" not in sd, (
            "armorBundles in slot_data with armor_bundles: false -- the client reconciler would "
            "arm for wrappers the seed never mints")
        demanded = sd.get(contract.REQUIRES_CLIENT_FEATURES, [])
        assert "armor_bundles" not in demanded, (
            "requiresClientFeatures still demands 'armor_bundles' on an off seed -- every older "
            "client would refuse it for nothing")


class ArmorBundlesOnSeed(WorldTestBase):
    """Default is ON (#985 preserves the shipped behavior); pin the wire so a flipped default
    fails here rather than in a player log."""

    game = GAME
    options = {"num_regions": 4}

    def test_wire_present_by_default(self):
        sd = self.world.fill_slot_data()
        assert "armorBundles" in sd
        assert "armor_bundles" in sd.get(contract.REQUIRES_CLIENT_FEATURES, [])
