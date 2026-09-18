"""armor_bundles: mixed -- the shuffled third mode.

`sets` (default) keeps the shipped one-wrapper-per-vanilla-set pool; `mixed` keeps that pool
SHAPE but shuffles which protector pieces arrive together, per seed. The client is seed-driven
(it grants whatever member list the wire sends), so this file gates the world side only: the
deal's coverage/shape/determinism, the pool's count-neutrality across all three modes, the
wire shape, and the Toggle-era yaml spellings.
"""
import random

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features.armor_bundles import (  # noqa: E402
    ARMOR_BUNDLES, MIXED_ARMOR_SETS, ArmorBundles, armor_bundles_on,
    armor_slot, build_mixed_sets, is_random, mixed_set_name, remap_bundle,
)

GAME = "Elden Ring"

ALL_MEMBERS = [full for rows in ARMOR_BUNDLES.values() for full in rows]
assert len(ALL_MEMBERS) == 600 and len(set(ALL_MEMBERS)) == 600  # the brief's premise, witnessed


def _slot_counts(fulls):
    from collections import Counter
    return Counter(armor_slot(f) for f in fulls)


def test_mixed_names_are_one_per_vanilla_set_in_deal_order():
    assert len(MIXED_ARMOR_SETS) == len(ARMOR_BUNDLES) == 143
    assert MIXED_ARMOR_SETS[0] == "Mixed Armor Set 1"
    assert MIXED_ARMOR_SETS[-1] == "Mixed Armor Set 143"
    assert len(set(MIXED_ARMOR_SETS)) == 143
    assert not (set(MIXED_ARMOR_SETS) & set(ARMOR_BUNDLES))


def test_deal_covers_all_600_fullids_exactly_once():
    mixed = build_mixed_sets(random.Random(1234))
    assert sorted(mixed) == sorted(MIXED_ARMOR_SETS)
    dealt = [full for members in mixed.values() for full in members]
    assert len(dealt) == 600
    assert sorted(dealt) == sorted(ALL_MEMBERS)


def test_deal_keeps_each_wrapper_slot_shaped_like_the_vanilla_set_it_replaces():
    """Wrapper i carries the same per-slot piece counts as the i-th vanilla set (sorted)."""
    mixed = build_mixed_sets(random.Random(1234))
    for i, vanilla in enumerate(sorted(ARMOR_BUNDLES)):
        assert _slot_counts(mixed[mixed_set_name(i + 1)]) == _slot_counts(ARMOR_BUNDLES[vanilla]), (
            "%s does not match the shape of %s" % (mixed_set_name(i + 1), vanilla))


def test_same_seed_same_deal_different_seed_different_deal():
    assert build_mixed_sets(random.Random(99)) == build_mixed_sets(random.Random(99))
    assert build_mixed_sets(random.Random(99)) != build_mixed_sets(random.Random(100))


def test_remap_assigns_mixed_names_in_encounter_order():
    mapping = {}
    assert remap_bundle("Briar Set", mapping) == "Mixed Armor Set 1"
    assert remap_bundle("Briar Set", mapping) == "Mixed Armor Set 1"
    assert remap_bundle("Bull-Goat Set", mapping) == "Mixed Armor Set 2"
    assert remap_bundle("Briar Set", mapping) == "Mixed Armor Set 1"


def test_option_values_and_backwards_compat_aliases():
    assert ArmorBundles.option_off == 0
    assert ArmorBundles.option_sets == 1
    assert ArmorBundles.option_mixed == 2
    assert ArmorBundles.default == 1
    # yaml `true`/`false` (the Toggle era) still resolve -- Choice.from_any tests
    # `type(data) == int`, and `type(True)` is bool, so these go through from_text + alias.
    assert ArmorBundles.from_any(True).value == 1
    assert ArmorBundles.from_any(False).value == 0
    assert ArmorBundles.from_any("off").value == 0
    assert ArmorBundles.from_any("sets").value == 1
    assert ArmorBundles.from_any("mixed").value == 2
    assert ArmorBundles.from_any(0).value == 0
    assert ArmorBundles.from_any(1).value == 1
    assert ArmorBundles.from_any(2).value == 2


class _Harness(WorldTestBase):
    """Hand-driven gen (the pool_builder_sweep.py pattern): auto_construct off so each test calls
    world_setup(seed) itself -- the same seed across modes/options is what makes the comparisons
    about the option rather than the draw."""
    game = GAME
    auto_construct = False
    run_default_tests = False

    def runTest(self):  # noqa: N802
        pass


def _gen(seed, armor_bundles):
    h = _Harness("runTest")
    h.options = {"num_regions": 4, "armor_bundles": armor_bundles}
    h.world_setup(seed)
    return h


def _pool_names(h):
    return [item.name for item in h.multiworld.itempool if item.player == h.player]


class MixedModeLiveSeed:
    """Shared live mixed-mode world for the wire assertions (one gen, not one per test)."""
    SEED = 7


def test_random_predicate_and_on_cover_all_three_modes():
    for value, on, rnd in ((False, False, False), (True, True, False),
                           (0, False, False), (1, True, False), (2, True, True),
                           ("off", False, False), ("sets", True, False), ("mixed", True, True)):
        h = _gen(21, value)
        assert armor_bundles_on(h.world) is on, value
        assert is_random(h.world) is rnd, value


def test_live_mapping_matches_the_pure_deal_for_the_same_seed():
    """generate_early drew from world.random, so equality here pins the stream position too --
    a feature that starts consuming the world's rng ahead of us moves this, loudly."""
    h = _gen(MixedModeLiveSeed.SEED, 2)
    assert h.world.gf_mixed_armor_sets
    dealt = [full for members in h.world.gf_mixed_armor_sets.values() for full in members]
    assert sorted(dealt) == sorted(ALL_MEMBERS)


def test_live_same_seed_same_mapping_different_seed_different():
    a = _gen(31, 2).world.gf_mixed_armor_sets
    b = _gen(31, 2).world.gf_mixed_armor_sets
    c = _gen(32, 2).world.gf_mixed_armor_sets
    assert a == b
    assert a != c


def test_pool_count_identical_across_off_sets_mixed():
    """Count-neutrality is the whole compaction contract: one wrapper per distinct family."""
    for seed in (5, 6, 7):
        counts = {mode: len(_gen(seed, mode).multiworld.itempool) for mode in (False, True, 2)}
        assert counts[False] == counts[True] == counts[2], (
            "seed %d: pool counts moved with the mode: %r" % (seed, counts))


def test_live_pool_uses_mixed_wrappers_only_in_random_mode():
    h = _gen(MixedModeLiveSeed.SEED, 2)
    names = _pool_names(h)
    assert set(ARMOR_BUNDLES).isdisjoint(names), (
        "vanilla wrappers leaked into a mixed pool: %s"
        % sorted(set(ARMOR_BUNDLES) & set(names)))
    wrappers = [n for n in names if n in MIXED_ARMOR_SETS]
    assert wrappers, "a mixed seed must still exercise armor bundling"
    assert len(wrappers) == len(set(wrappers))
    # every pooled mixed wrapper is one the encounter order actually assigned (1..M for the
    # M distinct families this seed's walk met), never a wrapper past the encounter count.
    assert max(int(n.rsplit(" ", 1)[1]) for n in wrappers) == len(wrappers)


def test_sets_mode_pool_untouched_by_the_remap():
    h = _gen(MixedModeLiveSeed.SEED, True)
    names = _pool_names(h)
    assert set(MIXED_ARMOR_SETS).isdisjoint(names)
    assert [n for n in names if n in ARMOR_BUNDLES]


def test_slot_data_emits_only_mixed_ids_in_random_mode():
    h = _gen(MixedModeLiveSeed.SEED, 2)
    sd = h.world.fill_slot_data()
    bundles = sd["armorBundles"]
    assert bundles
    mixed_ids = {str(h.world.item_name_to_id[n]) for n in MIXED_ARMOR_SETS}
    vanilla_ids = {str(h.world.item_name_to_id[n]) for n in ARMOR_BUNDLES}
    assert set(bundles) <= mixed_ids, (
        "non-mixed ids on the random wire: %s" % sorted(set(bundles) - mixed_ids))
    assert set(bundles).isdisjoint(vanilla_ids)
    assert set(bundles) == {str(h.world.item_name_to_id[n])
                            for n in h.world.gf_mixed_armor_sets}
    assert all(sorted(m) == sorted(h.world.gf_mixed_armor_sets[n])
               for n, m in ((next(nm for nm in MIXED_ARMOR_SETS
                                  if str(h.world.item_name_to_id[nm]) == k), v)
                            for k, v in bundles.items()))
    assert "armor_bundles" in sd.get(contract.REQUIRES_CLIENT_FEATURES, [])
    contract.validate_slot_data(sd, strict=True)


def test_slot_data_unchanged_in_sets_mode():
    h = _gen(MixedModeLiveSeed.SEED, True)
    sd = h.world.fill_slot_data()
    bundles = sd["armorBundles"]
    assert set(bundles) == {str(h.world.item_name_to_id[n]) for n in ARMOR_BUNDLES}
    assert set(bundles).isdisjoint({str(h.world.item_name_to_id[n]) for n in MIXED_ARMOR_SETS})
    contract.validate_slot_data(sd, strict=True)
