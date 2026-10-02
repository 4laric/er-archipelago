"""Mario generation contract, reward filtering and explicit option rejection (#1619)."""
from types import SimpleNamespace
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from BaseClasses import ItemClassification
from Options import OptionError
from worlds.eldenring import contract, core
from worlds.eldenring.features.mario_mode import MarioFeature, MarioMode, equipment_reward, filter_rewards


def test_mario_ids_are_fixed_useful_synthetic_and_disjoint():
    assert MarioMode.default == 0
    ids = []
    for index, (_key, name) in enumerate(contract.MARIO_UNLOCK_ITEM_NAMES):
        aid = core.item_name_to_id[name]
        ids.append(aid)
        assert aid == 7910000 + index
        assert core._item_class[name] == ItemClassification.useful
        assert str(aid) not in core._AP_IDS_TO_ITEM_IDS
    assert len(ids) == 9
    assert len(set(core.item_name_to_id.values())) == len(core.item_name_to_id)
    assert contract.OPTIONS_BY_NAME["mario_mode"].shape == "BOOL_OR_INT"
    assert "marioCapabilities" not in contract.BY_NAME  # existing optional wire, no hash drift


@pytest.mark.parametrize("key,value,message", [
    ("item_shuffle", 0, "item_shuffle must be on"),
    ("vanilla_placement", 1, "vanilla_placement must be off"),
    ("locked_abilities", {"jump"}, "locked_abilities must be empty"),
    ("locked_abilities", {"heal"}, "locked_abilities must be empty"),
    ("auto_equip", 1, "auto_equip must be off"),
    ("death_link", 1, "death_link must be off"),
    ("trap_link", 1, "trap_link must be off"),
    ("traps", {"no_flask"}, "remove no_flask"),
])
def test_mario_rejects_conflicts_without_overwriting_options(key, value, message):
    opts = {"mario_mode": 1, "item_shuffle": 1, key: value}
    world = SimpleNamespace(options=SimpleNamespace(**{
        name: SimpleNamespace(value=v) for name, v in opts.items()}))
    world._shuffle_on = lambda: bool(world.options.item_shuffle.value)
    with pytest.raises(OptionError, match=message):
        MarioFeature().generate_early(world)
    assert getattr(world.options, key).value == value
    world.options.mario_mode.value = 0
    MarioFeature().generate_early(world)  # off leaves every existing combination alone


class MarioOff(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0}

    def test_no_mario_items_or_wire_when_off(self):
        pool = self.multiworld.itempool
        assert not ({name for _key, name in contract.MARIO_UNLOCK_ITEM_NAMES}
                    & {item.name for item in pool})
        assert filter_rewards(self.world, pool, core.FILLER) is pool
        sd = self.world.fill_slot_data()
        assert sd["options"]["mario_mode"] == 0
        assert "abilityUnlockItems" not in sd
        assert contract.MARIO_CAPABILITIES_FEATURE not in sd.get("requiresClientFeatures", [])


class MarioOn(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0, "mario_mode": 1}

    def test_pool_and_wire_match_without_location_or_goal_gates(self):
        pool = [item for item in self.multiworld.itempool if item.player == self.player]
        locations = self.multiworld.get_unfilled_locations(self.player)
        assert len(pool) == len(locations)
        names = [item.name for item in pool]
        expected = {str(self.world.item_name_to_id[name]): key
                    for key, name in contract.MARIO_UNLOCK_ITEM_NAMES}
        for key, name in contract.MARIO_UNLOCK_ITEM_NAMES:
            assert names.count(name) == (2 if key == "progressive_jump" else 1)
            assert self.world.create_item(name).classification == ItemClassification.useful
        assert not any(equipment_reward(self.world, item.name) for item in pool)
        sd = self.world.fill_slot_data()
        assert sd["options"]["mario_mode"] == 1
        assert sd["abilityUnlockItems"] == expected
        assert contract.MARIO_CAPABILITIES_FEATURE in sd["requiresClientFeatures"]
        assert not ({name for _key, name in contract.MARIO_UNLOCK_ITEM_NAMES}
                    & set(sd.get("goalRequiredItems", [])))
        # Every retained generated pickup keeps its published AP address; no Mario locations.
        assert all(loc.address == self.world.location_name_to_id[loc.name]
                   for loc in locations if loc.name in self.world.location_name_to_id)
        assert not ({name for _key, name in contract.MARIO_UNLOCK_ITEM_NAMES}
                    & {loc.name for loc in locations})

    def test_filter_preserves_keys_talismans_consumables_and_moves(self):
        names = ["Stonesword Key", "Crimson Amber Medallion", "Golden Rune [1]",
                 "Wall Kick", "Dagger", "Glintstone Pebble"]
        pool = [self.world.create_item(name) for name in names]
        filtered = filter_rewards(self.world, pool, core.FILLER)
        assert [item.name for item in filtered] == names[:4] + [core.FILLER, core.FILLER]
        assert all(filtered[i] is pool[i] for i in range(4))
        assert len(filtered) == len(pool)
        pool[-1].classification = ItemClassification.progression
        with pytest.raises(OptionError, match="progression equipment"):
            filter_rewards(self.world, pool, core.FILLER)


class MarioSmallBundled(MarioOn):
    options = {"num_regions": 3, "mario_mode": 1, "armor_bundles": "sets"}


class MarioDLCMixed(MarioOn):
    options = {"num_regions": 3, "mario_mode": 1, "dlc_only": 1, "armor_bundles": "mixed"}


class MarioBaseUnbundled(MarioOn):
    options = {"num_regions": 3, "mario_mode": 1, "enable_dlc": 0, "armor_bundles": "off"}
