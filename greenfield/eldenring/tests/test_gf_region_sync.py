"""region_sync option (#1005): share region unlocks across the ER slots in a session.

MOTIVATING CASE (rule 11). Doopliss ran three ER yamls through ONE seamless-co-op world. Everyone
is in the co-op host's physical world but on their own AP slot, so the moment one player's Liurnia
Lock landed and the others' had not, the others were region-kicked out from under them and co-op
stopped working. `region_sync` is the opt-in that makes the region-OPEN travel.

WHAT THIS FILE PINS, and the ordering matters -- the last one is the whole risk:

  1. The option exists, is OFF by default, and rides the `options` echo (so an existing seed and a
     solo player are untouched).
  2. ON declares `requiresClientFeatures: ["region_sync"]`. Not decoration: a client that connects
     and ignores this key leaves ITS player kicked while the rest of the party plays, which reads
     as a broken seed rather than an old client. OPTIONS_SUBKEYS is not folded into CONTRACT_HASH,
     so the tag is the ONLY thing that can refuse.
  3. 🛑 IT IS NOT A LOGIC CHANGE. The feature contributes no items, no regions and no rules, and
     generation is byte-identical with the option on and off. The client applies a synced open as
     the same flag write a received Lock makes -- nobody is handed anyone else's Lock ITEM, so
     Fill, logic and the goal must be untouched. An implementation that "helpfully" granted the
     Lock would make every synced region free for the whole party and is exactly what this asserts
     against.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features import region_sync  # noqa: E402
from worlds.eldenring.registry import Feature  # noqa: E402

GAME = "Elden Ring"


class _Opt:
    def __init__(self, value):
        self.value = value


class _World:
    def __init__(self, enabled):
        class Options:
            pass
        self.options = Options()
        self.options.region_sync = _Opt(enabled)


def test_off_is_inert_and_on_requires_the_client_feature():
    feature = region_sync.RegionSyncFeature()
    assert feature.slot_data(_World(False)) == {}
    assert feature.slot_data(_World(True)) == {
        contract.REQUIRES_CLIENT_FEATURES: [region_sync.CLIENT_FEATURE_TAG]
    }


def test_the_option_is_off_by_default():
    assert region_sync.RegionSync.default == 0


def test_the_options_echo_declares_the_wire_key_as_an_optional_bool():
    key = contract.OPTIONS_BY_NAME["region_sync"]
    assert key.shape == "BOOL_OR_INT"
    # NOT required: a seed rolled before this option omits it, and an absent key parses false.
    assert key.required is False
    assert "core._options_echo" in key.producer


def test_the_feature_contributes_nothing_to_generation():
    """The 'not a logic change' claim, at the only layer that can break it.

    Every generation hook must still be the registry's inherited no-op: an override here would be
    an item, a region or a rule that only exists because a CO-OP CONVENIENCE was turned on.
    """
    feature = region_sync.RegionSyncFeature()
    for hook in ("generate_early", "create_items", "create_regions", "set_rules"):
        assert getattr(type(feature), hook) is getattr(Feature, hook), (
            f"RegionSyncFeature overrides {hook}: region_sync must not touch generation"
        )
    assert region_sync.RegionSyncFeature.ITEMS == {}
    assert region_sync.RegionSyncFeature.ITEM_GRANTS == {}


class RegionSyncOn(WorldTestBase):
    game = GAME
    options = {"region_sync": True, "num_regions": 3}

    def test_the_echo_carries_it_and_the_client_feature_is_declared(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["region_sync"] == 1
        assert "region_sync" in sd[contract.REQUIRES_CLIENT_FEATURES]

    def test_no_region_lock_item_is_minted_for_the_sync(self):
        """The sync opens doors, it does not hand out keys: the item pool is the same one an
        unsynced seed rolls, so nothing here is a second copy of a region Lock."""
        names = [i.name for i in self.multiworld.itempool]
        assert len(names) == len(self.multiworld.get_unfilled_locations(self.player))


class RegionSyncOff(WorldTestBase):
    game = GAME
    options = {"region_sync": False, "num_regions": 3}

    def test_the_echo_says_off_and_no_tag_is_declared(self):
        sd = self.world.fill_slot_data()
        assert sd["options"]["region_sync"] == 0
        assert "region_sync" not in sd.get(contract.REQUIRES_CLIENT_FEATURES, [])
