"""shop_checks option (#994): OFF removes every merchant-slot check.

Requested by Light -- so no item, yours or a foreign player's, is ever gated behind a purchase.
The removal is centralised in core._seed_locations (the one chokepoint), so region build, pool,
count and slot_data all agree the rows are gone; here we pin that ON keeps them and OFF drops them,
that slot_data stays consistent with the location set, and that the seed still generates count-exact
(WorldTestBase's own fill is the items==locations oracle).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.shop_data import SHOP_ROW_FLAGS  # noqa: E402

GAME = "Elden Ring"


def _shop_locations(world):
    return [l for l in world.multiworld.get_locations(world.player)
            if l.address is not None and str(l.address) in SHOP_ROW_FLAGS]


class ShopChecksOn(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "shop_checks": "true"}

    def test_shops_are_checks_by_default(self):
        assert _shop_locations(self.world), "shop_checks on: expected merchant-slot locations"
        sd = self.world.fill_slot_data()
        assert sd.get(contract.SHOP_ROW_FLAGS), "shopRowFlags must be emitted when shops are checks"


class ShopChecksOff(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "shop_checks": "false"}

    def test_no_merchant_slot_is_a_location(self):
        assert _shop_locations(self.world) == [], "shop_checks off: no shop-slot location may exist"

    def test_shop_tables_absent_from_slot_data(self):
        sd = self.world.fill_slot_data()
        assert contract.SHOP_ROW_FLAGS not in sd, "shopRowFlags must not be emitted with no shop checks"
        assert contract.SHOP_PREVIEW_GOODS not in sd
        contract.validate_slot_data(sd, strict=True)
