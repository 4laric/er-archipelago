from types import SimpleNamespace

from worlds.eldenring import contract
from worlds.eldenring.features import mine_materials
from worlds.eldenring.mine_material_data import MINE_MATERIAL_LOTS


class _World:
    player = 1
    gf_dlc_excluded = frozenset()

    def __init__(self, seed, enabled=True):
        self.multiworld = SimpleNamespace(seed=seed)
        self.options = SimpleNamespace(
            reroll_mine_materials=SimpleNamespace(value=int(enabled)))


def _roll(seed, enabled=True):
    return mine_materials.MineMaterialsFeature().slot_data(_World(seed, enabled)).get(
        contract.MINE_MATERIAL_ROLL, {})


def test_census_exposes_only_placed_non_capstone_lots():
    assert len(MINE_MATERIAL_LOTS) == 11
    assert 998680 not in MINE_MATERIAL_LOTS       # Ancient Dragon Smithing Stone
    assert 998790 not in MINE_MATERIAL_LOTS       # Somber Ancient Dragon Smithing Stone


def test_off_is_vanilla_and_on_rewrites_every_eligible_template():
    assert _roll("off", enabled=False) == {}
    roll = _roll("on")
    assert set(map(int, roll)) == set(MINE_MATERIAL_LOTS)
    assert set(roll.values()) <= set(mine_materials.pool(_World("pool")))


def test_roll_is_idempotent_and_seeded_without_shared_rng_state():
    first = _roll("same-seed")
    assert first == _roll("same-seed")
    assert first != _roll("different-seed")


def test_replacements_are_repeatable_goods_not_upgrade_materials_or_keys():
    from worlds.eldenring.item_ids import ITEM_CATALOG

    names = {full & 0x0FFFFFFF: name for name, full in ITEM_CATALOG.items()}
    replacement_names = {names[gid] for gid in mine_materials.pool(_World("pool"))}
    assert replacement_names
    assert not any("Smithing Stone" in name or "Glovewort" in name
                   for name in replacement_names)
    assert replacement_names.isdisjoint({"Stonesword Key", "Imbued Sword Key", "Dragon Heart"})
