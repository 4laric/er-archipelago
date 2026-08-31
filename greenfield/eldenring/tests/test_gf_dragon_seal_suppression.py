"""The Cave of Knowledge Dragon Communion Seal stays source-neutralised (#999).

The check is enemy lot 301000010, slot 1, even though its shared acquisition flag and descriptor
make it look like an ordinary ground pickup.  The slot contains a weapon, so it must travel in the
historically named ``checkLotZeroEnemy`` table; putting it in the goods-blank or map table leaves
the Ulcerated Tree Spirit grant live and double-pays the vanilla Seal.
"""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

DRAGON_SEAL_LOT = 301000010


def test_dragon_seal_enemy_weapon_slot_is_repointed():
    from worlds.eldenring.check_lots_data import CHECK_LOT_ZERO_ENEMY

    assert CHECK_LOT_ZERO_ENEMY.get(DRAGON_SEAL_LOT) == [1]


class DragonSealSuppression(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0}

    def test_dragon_seal_repoint_is_emitted_in_the_enemy_table(self):
        slot_data = self.world.fill_slot_data()
        enemy = slot_data.get("checkLotZeroEnemy", {})
        assert enemy, "checkLotZeroEnemy must be emitted"
        assert enemy.get(str(DRAGON_SEAL_LOT)) == [1]

        # The same numeric row in the map table would edit a different param and leave the actual
        # boss grant untouched.  Pin the table identity, not merely the row/slot pair.
        assert str(DRAGON_SEAL_LOT) not in slot_data.get("checkLotZeroMap", {})
