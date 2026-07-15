"""Grace gates -- gated children (region_spine.REGION_PARENT) never get their bundle granted while
their wall is armed. features/graces.py emits the child's bundle EMPTY; the player enters past the
game's own wall (Academy key / Great Runes / the capital well) and touches the graces themselves.
Replaces the old re-key model (Academy graces on the key item, capital graces on runeGatedGraces):
the runeGatedGraces client half never existed, so it could not gate anything -- see
tests/test_gf_gated_children.py for the full fix surface. This file keeps the HUB-grace assertions
(71190 must never ride a bundle) and the retired-key guard close to the feature they watch.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.region_graces import REGION_GRACE_POINTS  # noqa: E402
from worlds.eldenring.region_spine import REGION_PARENT  # noqa: E402

GAME = "Elden Ring"
_RAYA = range(71400, 71500)
_LEYN = range(71100, 71200)
_ROUNDTABLE = 71190


class GatesArmed(WorldTestBase):
    game = GAME
    run_default_tests = False
    options = {  # defaults arm both walls: item_shuffle/legacy keys frozen on, leyndell runes = 2
        "num_regions": 0, "leyndell_runes_required": 2,
    }

    def _rg(self):
        return self.world.fill_slot_data()[contract.REGION_GRACES]

    def test_gated_child_bundles_are_withheld(self):
        rg = self._rg()
        for child in REGION_PARENT:
            self.assertEqual(rg.get(f"{child} Lock"), [],
                             f"{child}'s bundle must be withheld while its wall is armed")

    def test_no_bundle_carries_a_walled_grace(self):
        # no OTHER key may smuggle a capital/Academy grace either (the pre-v2 fold bug shape).
        rg = self._rg()
        for key, fs in rg.items():
            leaked = [g for g in fs if g in _RAYA or (g in _LEYN and g != _ROUNDTABLE)]
            self.assertFalse(leaked, f"{key} carries walled graces {leaked}")

    def test_hub_grace_is_a_start_grace_not_a_bundle_rider(self):
        sd = self.world.fill_slot_data()
        for key, fs in sd[contract.REGION_GRACES].items():
            self.assertNotIn(_ROUNDTABLE, fs, f"71190 (HUB) must not ride bundle {key}")
        self.assertIn(_ROUNDTABLE, sd.get(contract.START_GRACES, []),
                      "the Roundtable/HUB grace 71190 must be granted as a start grace")

    def test_torrent_enable_flag_rides_the_whistle_grant(self):
        # start_with_steed (frozen ON) grants the whistle GOODS; the game gates Torrent summoning on
        # obtained-flag 60100, which vanilla only sets via Melina's (here-bypassed) hand-off. Without
        # 60100 the player carries the whistle but stays mountless (er-torrent-regionlock-mountless).
        sd = self.world.fill_slot_data()
        steed = getattr(self.world.options, "start_with_steed", None)
        if steed is not None and steed.value:
            self.assertIn(60100, sd.get(contract.START_GRACES, []),
                          "start_with_steed on -> Torrent enable flag 60100 must be in startGraces, "
                          "else the whistle is inert and the player is mountless")

    def test_rune_gate_keys_retired(self):
        sd = self.world.fill_slot_data()
        self.assertNotIn("runeGatedGraces", sd,
                         "runeGatedGraces is retired -- its client half never existed")
        self.assertNotIn("greatRuneItemIds", sd)

    def test_ungated_bundles_are_untouched(self):
        rg = self._rg()
        kept = set(self.world._kept())
        for r, fs in REGION_GRACE_POINTS.items():
            if r in kept and fs and r not in REGION_PARENT:
                self.assertEqual(rg.get(f"{r} Lock"), list(fs),
                                 f"{r}'s bundle must be granted in full")
