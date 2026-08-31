"""The Tonic of Forgetfulness' shared grant paths stay source-neutralised (#957).

Flag 400070 has two map-lot faces, 100700 and 100726.  Rya and Patches award lot 100700 from
their ESD, while the alternate world pickup uses the same flag through 100726.  Repointing both
lots to the AP placeholder suppresses every lot-backed path without arming the unsafe global
item-id suppressor for goods 8128.
"""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

TONIC_LOTS = (100700, 100726)


def test_both_tonic_lots_are_goods_blanked_at_the_source():
    from worlds.eldenring.check_lots_data import CHECK_LOT_SLOTS_MAP

    assert {lot: CHECK_LOT_SLOTS_MAP.get(lot) for lot in TONIC_LOTS} == {
        100700: [1],
        100726: [1],
    }


class TonicSuppression(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0}

    def test_every_tonic_grant_lot_is_emitted_to_the_client(self):
        blank = self.world.fill_slot_data().get("checkLotBlankMap", {})
        assert blank, "checkLotBlankMap must be emitted"
        for lot in TONIC_LOTS:
            assert blank.get(str(lot)) == [1], (
                f"Tonic lot {lot} must be repointed so ESD and world grants cannot leak goods 8128"
            )
