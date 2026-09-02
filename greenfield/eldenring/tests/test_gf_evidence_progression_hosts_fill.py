"""Adversarial fill coverage for evidence-confined progression hosting."""
from types import SimpleNamespace

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from BaseClasses import ItemClassification  # noqa: E402
from Options import OptionError  # noqa: E402
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from worlds.eldenring.evidence_progression_hosts import (  # noqa: E402
    HOLD_PROGRESSION_HOST_APS,
    TRUSTED_PROGRESSION_HOST_APS,
)
from worlds.eldenring.features.evidence_progression_hosts import (  # noqa: E402
    apply_location_rule,
    hold_aps,
)
from worlds.eldenring.features.finale import finale_entries  # noqa: E402
from worlds.eldenring.region_spine import DLC_REGIONS, REGIONS  # noqa: E402

GAME = "Elden Ring"
ALL_APS = {ap for rows in LOCATIONS.values() for (_name, ap, _flag) in rows}


def test_generated_host_sets_are_disjoint_live_location_ids():
    """Stale IDs make the guard look broader than the checks it can actually touch."""
    trusted = set(TRUSTED_PROGRESSION_HOST_APS)
    held = set(HOLD_PROGRESSION_HOST_APS)
    assert trusted, "the trusted witness population vanished"
    assert held, "the HOLD witness population vanished"
    assert trusted.isdisjoint(held), sorted(trusted & held)[:10]
    assert trusted | held <= ALL_APS, sorted((trusted | held) - ALL_APS)[:10]


def test_every_rollable_region_has_capacity_for_the_great_rune_floor():
    """Every one-region Great Rune seed has ten trusted hosts plus one reserve."""
    trusted = set(TRUSTED_PROGRESSION_HOST_APS)
    counts = {
        region: sum(ap in trusted for _name, ap, _flag in LOCATIONS[region])
        for region in REGIONS
    }
    assert counts, "the rollable-region census vanished"
    # A one-region Great Runes seed can require ten confined progression items.
    # Keep one additional trusted location available because another feature may
    # consume a host before progression-surface placement runs.
    underfilled = {region: count for region, count in counts.items() if count < 11}
    assert not underfilled, underfilled


class _FakeLocation:
    def __init__(self, address, prior=lambda _item: True):
        self.address = address
        self.item_rule = prior


def _item(name, player, classification):
    return SimpleNamespace(name=name, player=player, classification=classification,
                           advancement=bool(classification & ItemClassification.progression))


def test_hold_rule_composes_and_bars_every_advancement_class():
    """Boss Keys/Unlocks bypass the older Lock predicate; foreign items use another fill path."""
    rejected_by_prior = _item("Prior rejection witness", 1, ItemClassification.filler)
    loc = _FakeLocation(next(iter(HOLD_PROGRESSION_HOST_APS)),
                        prior=lambda item: item is not rejected_by_prior)
    apply_location_rule(SimpleNamespace(player=1), loc)

    advancement = (
        _item("Limgrave Lock", 1, ItemClassification.progression),
        _item("Boss Key: Margit, the Fell Omen", 1, ItemClassification.progression),
        _item("Unlock: Roll", 1, ItemClassification.progression),
        _item("Foreign Key", 2, ItemClassification.progression),
    )
    for item in advancement:
        assert not loc.item_rule(item), item.name
    assert loc.item_rule(_item("Useful weapon", 1, ItemClassification.useful))
    assert loc.item_rule(_item("Foreign filler", 2, ItemClassification.filler))
    assert not loc.item_rule(rejected_by_prior), "the evidence rule replaced the prior item_rule"


def test_trusted_location_preserves_its_existing_rule():
    rejected = _item("Prior rejection witness", 1, ItemClassification.filler)
    loc = _FakeLocation(next(iter(TRUSTED_PROGRESSION_HOST_APS)),
                        prior=lambda item: item is not rejected)
    apply_location_rule(SimpleNamespace(player=1), loc)
    assert not loc.item_rule(rejected)
    assert loc.item_rule(_item("Allowed", 1, ItemClassification.progression))


def test_finale_checks_stay_held_even_when_external_identity_is_trusted():
    finale_id = next(ap for _name, ap, _flag in finale_entries())
    assert finale_id in hold_aps(SimpleNamespace(), trusted={finale_id}, candidates={finale_id})


class _NoAdvancementOnHoldMixin:
    def _filled_hold_locations(self):
        from Fill import distribute_items_restrictive

        own_advancement = [item for item in self.multiworld.get_items()
                           if item.player == self.player and item.advancement]
        self.assertTrue(own_advancement, "this matrix row minted no own advancement")
        trusted = set(TRUSTED_PROGRESSION_HOST_APS)
        trusted_live = [loc for loc in self.multiworld.get_locations(self.player)
                        if loc.address in trusted]
        self.assertTrue(trusted_live, "this matrix row enabled zero TRUSTED checks")
        distribute_items_restrictive(self.multiworld)
        held = set(hold_aps(self.world))
        live = [loc for loc in self.multiworld.get_locations(self.player) if loc.address in held]
        self.assertTrue(live, "this matrix row exercised zero HOLD checks")
        unfilled = [loc.name for loc in live if loc.item is None]
        self.assertFalse(unfilled[:10], "fill left HOLD checks empty: %s" % unfilled[:10])
        return held, live

    def test_hold_population_is_live_and_contains_no_advancement(self):
        _held, live = self._filled_hold_locations()
        self.assertTrue(live, "the HOLD population vanished")
        offenders = [f"{loc.name} <- P{loc.item.player} {loc.item.name}"
                     for loc in live if loc.item.advancement]
        self.assertFalse(offenders[:10], "advancement reached HOLD checks: %s" % offenders[:10])


class HeavilySealedDlcOffAbilityPressure(_NoAdvancementOnHoldMixin, WorldTestBase):
    game = GAME
    options = {
        "num_regions": 3,
        "enable_dlc": False,
        "locked_abilities": ["jump", "roll", "r1", "r2", "l1", "l2", "heal"],
        "ability_lock_mode": "progressive",
    }

    def test_unlocks_exist_and_are_kept_off_hold(self):
        held, _live = self._filled_hold_locations()
        unlocks = [loc for loc in self.multiworld.get_locations(self.player)
                   if loc.item is not None and loc.item.player == self.player
                   and loc.item.name.startswith("Unlock: ")]
        self.assertTrue(unlocks, "ability-pressure row minted no Unlock items")
        self.assertFalse([loc.name for loc in unlocks if loc.address in held])

    def test_the_row_is_actually_heavily_sealed(self):
        live = {loc.address for loc in self.multiworld.get_locations(self.player)
                if loc.address is not None}
        # Region selection is intentionally random and three large regions can exceed a quarter
        # of the corpus. The coverage row only needs a genuinely minority live population.
        self.assertLess(len(live), len(ALL_APS) // 2,
                        "the heavily-sealed row no longer seals most checks")


class OneRegionGreatRunesIsValid(_NoAdvancementOnHoldMixin, WorldTestBase):
    """One region is legal when the rune goal leaves real progression in the pool."""
    game = GAME
    options = {"num_regions": 1, "enable_dlc": False, "ending_condition": "great_runes"}

    def test_exactly_one_region_was_requested_and_fill_really_ran(self):
        self.assertEqual(1, self.options["num_regions"])
        _held, live = self._filled_hold_locations()
        self.assertTrue(all(loc.item is not None for loc in live))


class DlcOnlyProgressionPressure(_NoAdvancementOnHoldMixin, WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "enable_dlc": True, "dlc_only": True}

    def test_only_dlc_regions_survive_and_the_row_fills(self):
        kept = set(self.world._kept())
        self.assertTrue(kept, "DLC-only row kept no regions")
        self.assertLessEqual(kept, set(DLC_REGIONS), sorted(kept - set(DLC_REGIONS)))
        _held, live = self._filled_hold_locations()
        self.assertTrue(all(loc.item is not None for loc in live))


class DefaultRegionsDlcOn(_NoAdvancementOnHoldMixin, WorldTestBase):
    game = GAME
    options = {"num_regions": 6, "enable_dlc": True}


class AllRegionsNarrowSurfaceDlcOff(_NoAdvancementOnHoldMixin, WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "enable_dlc": False,
               "progression_surface": {"MajorBoss"}}


class AllRegionsNarrowSurfaceDlcOn(_NoAdvancementOnHoldMixin, WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "enable_dlc": True,
               "progression_surface": {"MajorBoss"}}


class SyntheticFinaleHostsAreGuarded(_NoAdvancementOnHoldMixin, WorldTestBase):
    """Ashen Capital locations are constructed outside core's ordinary location loop."""
    game = GAME
    options = {"num_regions": 0, "enable_dlc": False}

    def test_every_synthetic_finale_check_is_live_hold_and_filler_only(self):
        held, _live = self._filled_hold_locations()
        finale_ids = {ap for _name, ap, _flag in finale_entries()}
        self.assertTrue(finale_ids, "the synthetic finale fixture vanished")
        finale = [loc for loc in self.multiworld.get_locations(self.player)
                  if loc.address in finale_ids]
        self.assertEqual(finale_ids, {loc.address for loc in finale},
                         "not every synthetic finale check was constructed")
        self.assertLessEqual(finale_ids, held,
                             "newly TRUSTED finale checks need an updated seam witness")
        self.assertFalse([f"{loc.name} <- {loc.item.name}" for loc in finale
                          if loc.item is None or loc.item.advancement])


class SpecialProgressionFamilies(_NoAdvancementOnHoldMixin, WorldTestBase):
    """Released Locks take a different placement route from confined region Locks."""
    game = GAME
    options = {
        "num_regions": 0,
        "enable_dlc": False,
        "progression_bias": 0,
    }

    def test_released_locks_are_kept_off_hold(self):
        held, _live = self._filled_hold_locations()
        own = [loc for loc in self.multiworld.get_locations(self.player)
               if loc.item is not None and loc.item.player == self.player]
        locks = [loc for loc in own if loc.item.name.endswith(" Lock")]
        self.assertTrue(locks, "special-path row minted no released region Locks")
        self.assertFalse([loc.name for loc in locks if loc.address in held])


class TestTwoPlayerForeignAdvancementPressure:
    """The ordinary multiworld fill, not a hand-built predicate, supplies foreign advancement."""
    def test_foreign_advancement_exists_but_not_on_hold(self):
        from Fill import distribute_items_restrictive
        from test.general import setup_multiworld
        from test.general import TestWorld
        from worlds.AutoWorld import AutoWorldRegister

        opts = {"num_regions": 3, "enable_dlc": False}
        world_type = AutoWorldRegister.world_types[GAME]
        multiworld = setup_multiworld([world_type, TestWorld], options=[opts, {}])
        # TestWorld intentionally contributes no pool. Promote one ER filler into a foreign-owned
        # advancement probe without changing the pool/location count; ordinary AP fill must consult
        # the destination's all-owner evidence rule.
        probe = next(item for item in multiworld.itempool
                     if item.player == 1 and not item.advancement)
        probe.player = 2
        probe.name = "Foreign progression probe"
        probe.classification = ItemClassification.progression
        distribute_items_restrictive(multiworld)
        world = multiworld.worlds[1]
        held = set(hold_aps(world))
        live = [loc for loc in multiworld.get_locations(1) if loc.address in held]
        assert live, "the real two-player seed exercised zero HOLD checks"
        trusted_live = [loc for loc in multiworld.get_locations(1)
                        if loc.address in TRUSTED_PROGRESSION_HOST_APS]
        assert trusted_live, "the real two-player seed enabled zero TRUSTED checks"
        offenders = [f"{loc.name} <- P{loc.item.player} {loc.item.name}"
                     for loc in live if loc.item is not None and loc.item.advancement]
        assert not offenders[:10], "advancement reached HOLD checks: %s" % offenders[:10]
        foreign = [loc for loc in multiworld.get_locations(1)
                   if loc.item is not None and loc.item.player != 1
                   and loc.item.advancement]
        assert foreign, "two-player row placed no foreign advancement in player 1's world"
        assert not [loc.name for loc in foreign if loc.address in held]


class TestSyntheticBossKeyPressure:
    """Boss Keys are currently frozen off, but their normal-fill category must stay covered."""
    def test_boss_key_probe_is_kept_off_hold(self):
        from Fill import distribute_items_restrictive
        from test.general import setup_multiworld
        from worlds.AutoWorld import AutoWorldRegister

        world_type = AutoWorldRegister.world_types[GAME]
        multiworld = setup_multiworld([world_type], options=[{"num_regions": 3}])
        probe = next(item for item in multiworld.itempool if not item.advancement)
        probe.name = "Boss Key: evidence-host probe"
        probe.classification = ItemClassification.progression
        distribute_items_restrictive(multiworld)
        world = multiworld.worlds[1]
        location = next(loc for loc in multiworld.get_locations(1) if loc.item is probe)
        assert location.address not in hold_aps(world), location.name
