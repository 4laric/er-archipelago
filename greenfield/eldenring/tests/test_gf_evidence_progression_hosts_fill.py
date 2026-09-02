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
from worlds.eldenring.region_spine import DLC_REGIONS  # noqa: E402

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
        self.assertLess(len(live), len(ALL_APS) // 4,
                        "the heavily-sealed row no longer seals most checks")


class OneRegionGreatRunesIsValid(_NoAdvancementOnHoldMixin, WorldTestBase):
    """One region is legal when the rune goal leaves real progression in the pool."""
    game = GAME
    options = {"num_regions": 1, "enable_dlc": False, "ending_condition": "great_runes"}

    def test_exactly_one_region_was_requested_and_fill_really_ran(self):
        self.assertEqual(1, self.options["num_regions"])
        _held, live = self._filled_hold_locations()
        self.assertTrue(all(loc.item is not None for loc in live))


def test_one_region_default_goal_is_an_invalid_minimum_not_a_fill_failure():
    """The adjacent invalid minimum must fail during option validation, before fill mutates state."""
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister

    world_type = AutoWorldRegister.world_types[GAME]
    with pytest.raises(OptionError, match="at least one must stay in the pool"):
        setup_multiworld([world_type], options=[{"num_regions": 1, "enable_dlc": False}])


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


class TwoPlayerForeignAdvancementPressure:
    """The ordinary multiworld fill, not a hand-built predicate, supplies foreign advancement."""
    def test_foreign_advancement_exists_but_not_on_hold(self):
        from Fill import distribute_items_restrictive
        from test.general import setup_multiworld
        from worlds.AutoWorld import AutoWorldRegister

        opts = {"num_regions": 3, "enable_dlc": False,
                "cross_game_progression": "never"}
        world_type = AutoWorldRegister.world_types[GAME]
        multiworld = setup_multiworld([world_type, world_type], options=[opts, opts])
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
