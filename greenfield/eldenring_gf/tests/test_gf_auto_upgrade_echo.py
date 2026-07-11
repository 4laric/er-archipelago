"""auto_upgrade option -> slot_data['options']['auto_upgrade'] echo (WorldTestBase)."""
import pytest
WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf import contract  # noqa: E402
GAME = "Elden Ring (Greenfield)"

class AutoUpgradeOn(WorldTestBase):
    game = GAME
    options = {"auto_upgrade": True}
    def test_echo_on(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["auto_upgrade"] == 1, sd["options"]["auto_upgrade"]
        assert isinstance(sd["options"]["auto_upgrade"], int)
        contract.validate_slot_data(sd, strict=True)

