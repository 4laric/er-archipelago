"""Independent Mario movement addons preserve old seeds and ordinary AP reachability."""
from itertools import product
from types import SimpleNamespace
import pytest

pytest.importorskip("worlds.eldenring")
from BaseClasses import ItemClassification
from Options import OptionError
from test.general import setup_multiworld
from worlds.AutoWorld import AutoWorldRegister
from worlds.eldenring import contract, core
from worlds.eldenring.features.mario_mode import ADDONS, MarioFeature, MarioCappy, MarioSonicMovement

WORLD = AutoWorldRegister.world_types["Elden Ring"]
BASE = {"num_regions": 3, "mario_mode": True}


def test_addon_ids_are_collision_free_useful_and_wire_optional():
    assert MarioCappy.default == MarioSonicMovement.default == 0
    ids = [aid for _option, _label, items, _feature in ADDONS
           for _key, _name, aid, _count in items]
    assert ids == list(range(7910016, 7910021))
    assert len(set(core.item_name_to_id.values())) == len(core.item_name_to_id)
    # The optional bingoBoard key moves the 0.6.5 contract; addon wire is unchanged.
    assert contract.CONTRACT_HASH.startswith("189fbb37")
    for option, _label, items, _feature in ADDONS:
        assert contract.OPTIONS_BY_NAME[option].shape == "BOOL_OR_INT"
        for _key, name, aid, count in items:
            assert core.item_name_to_id[name] == aid
            assert core._item_class[name] == ItemClassification.useful
            assert str(aid) not in core._AP_IDS_TO_ITEM_IDS
            assert count == 1


@pytest.mark.parametrize("stats,fludd,cappy,sonic", list(product([False, True], repeat=4)))
def test_addons_compose_count_neutrally_without_logic_gates(stats, fludd, cappy, sonic):
    opts = {**BASE, "mario_stat_upgrades": stats, "mario_fludd": fludd}
    baseline = setup_multiworld(WORLD, seed=7, options=opts)
    mw = setup_multiworld(WORLD, seed=7, options={**opts, "mario_cappy": cappy,
                                               "mario_sonic_movement": sonic})
    assert len(mw.itempool) == len(baseline.itempool) == len(mw.get_unfilled_locations())
    assert [(l.name, l.address) for l in mw.get_locations()] == [
        (l.name, l.address) for l in baseline.get_locations()]
    world = mw.worlds[1]
    sd = world.fill_slot_data()
    all_state = mw.get_all_state(False)
    names = {name for _option, _label, items, _feature in ADDONS
             for _key, name, _aid, _count in items}
    for item in mw.itempool:
        if item.name in names:
            all_state.remove(item)
    assert mw.can_beat_game(all_state), "addon moves must never become goal requirements"
    reference = mw.get_all_state(False)
    assert {l.address for l in mw.get_locations() if l.can_reach(all_state)} == {
        l.address for l in mw.get_locations() if l.can_reach(reference)}
    for option, _label, items, feature in ADDONS:
        enabled = cappy if option == "mario_cappy" else sonic
        assert (option in sd["options"]) == enabled
        assert (feature in sd["requiresClientFeatures"]) == enabled
        for key, name, aid, count in items:
            assert sum(i.name == name for i in mw.itempool) == (count if enabled else 0)
            assert (sd["abilityUnlockItems"].get(str(aid)) == key) == enabled
    assert len(MarioFeature().create_items(world)) == (
        len(MarioFeature().create_items(baseline.worlds[1])) + 2 * cappy + 3 * sonic)
    if not cappy and not sonic:
        assert [(i.name, i.classification) for i in mw.itempool] == [
            (i.name, i.classification) for i in baseline.itempool]
        assert sd == baseline.worlds[1].fill_slot_data()


@pytest.mark.parametrize("option,label,items,feature", ADDONS)
@pytest.mark.parametrize("route", ["start_inventory", "start_inventory_from_pool", "precollected"])
def test_disabled_addon_start_items_rejected_even_with_mario_off(option, label, items, feature, route):
    for _key, name, _aid, _count in items:
        world = SimpleNamespace(player=1, options=SimpleNamespace())
        if route == "precollected":
            world.multiworld = SimpleNamespace(precollected_items={1: [SimpleNamespace(name=name)]})
        else:
            setattr(world.options, route, SimpleNamespace(value={name: 1}))
        with pytest.raises(OptionError, match=f"{label} start inventory requires {option}"):
            MarioFeature().generate_early(world)


def test_zero_quantities_do_not_enable_addons():
    names = {name: 0 for _option, _label, items, _feature in ADDONS
             for _key, name, _aid, _count in items}
    MarioFeature().generate_early(SimpleNamespace(options=SimpleNamespace(
        start_inventory=SimpleNamespace(value=names),
        start_inventory_from_pool=SimpleNamespace(value=names))))


def test_addon_multiworld_receipts_and_pool_are_player_specific():
    from Fill import distribute_items_restrictive
    mw = setup_multiworld([WORLD, WORLD], seed=22222, options=[
        {**BASE, "mario_cappy": True, "mario_fludd": True},
        {**BASE, "mario_sonic_movement": True, "mario_stat_upgrades": True}])
    assert len(mw.itempool) == len(mw.get_unfilled_locations())
    for player in (1, 2):
        sd = mw.worlds[player].fill_slot_data()
        for option, _label, items, feature in ADDONS:
            enabled = (player == 1) == (option == "mario_cappy")
            assert (feature in sd["requiresClientFeatures"]) == enabled
            for key, name, aid, count in items:
                assert sum(i.name == name and i.player == player for i in mw.itempool) == (
                    count if enabled else 0)
                assert (sd["abilityUnlockItems"].get(str(aid)) == key) == enabled
    distribute_items_restrictive(mw)
    assert not mw.get_unfilled_locations()
    assert mw.can_beat_game()
