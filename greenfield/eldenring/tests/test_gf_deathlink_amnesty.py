"""Separate inbound/outbound DeathLink amnesty options and compatibility handshake (#1051)."""

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.deathlink import CLIENT_FEATURE_TAG  # noqa: E402


class _Base(WorldTestBase):
    game = "Elden Ring"
    run_default_tests = False


class TestDeathLinkAmnestyDefaults(_Base):
    def test_defaults_preserve_every_death_and_need_no_new_client(self):
        slot_data = self.world.fill_slot_data()
        assert slot_data["options"]["death_link_amnesty_inbound"] == 1
        assert slot_data["options"]["death_link_amnesty_outbound"] == 1
        assert CLIENT_FEATURE_TAG not in slot_data.get("requiresClientFeatures", [])


class TestDeathLinkAmnestyIndependent(_Base):
    options = {
        "death_link": True,
        "death_link_amnesty_inbound": 2,
        "death_link_amnesty_outbound": 5,
    }

    def test_values_are_independent_and_require_the_capable_client(self):
        slot_data = self.world.fill_slot_data()
        assert slot_data["options"]["death_link"] == 1
        assert slot_data["options"]["death_link_amnesty_inbound"] == 2
        assert slot_data["options"]["death_link_amnesty_outbound"] == 5
        assert CLIENT_FEATURE_TAG in slot_data["requiresClientFeatures"]


class TestOutboundAmnestyAloneDeclaresFeature(_Base):
    options = {"death_link": True, "death_link_amnesty_outbound": 3}

    def test_one_nondefault_direction_is_enough(self):
        slot_data = self.world.fill_slot_data()
        assert slot_data["options"]["death_link_amnesty_inbound"] == 1
        assert slot_data["options"]["death_link_amnesty_outbound"] == 3
        assert CLIENT_FEATURE_TAG in slot_data["requiresClientFeatures"]
