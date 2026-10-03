"""Ordered talismans preserve physical categories, DLC exclusions and pool size."""
from collections import Counter
from types import SimpleNamespace

from worlds.eldenring.features import power_progression as power
from worlds.eldenring.tables.item_ids import ITEM_CATALOG


def test_every_family_has_real_accessory_ids_in_numbered_order():
    ladders = power.families(ITEM_CATALOG)
    assert len(ladders) == len(power.FAMILY_NAMES) - 1
    assert "Progressive Arsenal Charm" not in ladders  # base is absent from grant catalogue
    for progressive, members in ladders.items():
        assert members[0] == progressive.removeprefix("Progressive ")
        assert all(ITEM_CATALOG[name] >> 28 == 2 for name in members)
        assert len(members) == len(set(members))
    assert len(set(power.ITEM_IDS.values())) == len(power.ITEM_IDS)


def test_top_rank_does_not_bypass_a_partial_seed_ladder_and_surplus_is_filler():
    world = SimpleNamespace(options=SimpleNamespace(progressive_talismans=SimpleNamespace(value=1)),
                            tables=SimpleNamespace(item_catalog=ITEM_CATALOG),
                            create_item=lambda name: SimpleNamespace(name=name))
    names = ["Boltdrake Talisman +3"] * 5 + ["Golden Rune [1]"]
    result = power.remap_rewards(world, [world.create_item(name) for name in names], "Golden Rune [1]")
    assert len(result) == len(names)
    assert Counter(item.name for item in result) == {"Progressive Boltdrake Talisman": 4, "Golden Rune [1]": 2}
    grants = power.grant_ladders(world)["Progressive Boltdrake Talisman"]
    assert [entry["goods"] for entry in grants] == [ITEM_CATALOG[name] for name in (
        "Boltdrake Talisman", "Boltdrake Talisman +1", "Boltdrake Talisman +2", "Boltdrake Talisman +3")]
    assert all(entry["consumed"] for entry in grants)  # one-time gear; never resurrect sold gear


def test_dlc_exclusion_and_default_off_identity():
    assert "Boltdrake Talisman +3" not in power.families(
        ITEM_CATALOG, ["Boltdrake Talisman +3"])["Progressive Boltdrake Talisman"]
    pool = [SimpleNamespace(name="Boltdrake Talisman +3")]
    world = SimpleNamespace(options=SimpleNamespace())
    assert power.remap_rewards(world, pool, "filler") is pool
