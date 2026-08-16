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
from worlds.eldenring.data import FINALE_REGION  # noqa: E402

GAME = "Elden Ring"
_RAYA = range(71400, 71500)
_LEYN = range(71100, 71200)
_ROUNDTABLE = 71190
# ⭐ THE 711xx BAND STOPPED BELONGING TO ONE REGION on 2026-08-06 (SPEC-ashen-capital-lock).
# `_LEYN` is a deliberately blanket band -- it catches Royal warp flags that are not even in
# Leyndell's own bundle (71100/71101/71106/71107), which is why it is a band and not a set. But the
# Ashen Capital now owns a REAL bundle at 71122-71125, inside that band, and those graces are NOT
# behind the capital's Great-Rune wall: they are behind the burn ITEM (`Ashen Capital Lock`), which
# is the one key entitled to carry them. So the band keeps its breadth and the Ashen bundle is
# carved out BY NAME, derived from the generated table rather than re-typed as a range -- and the
# carve-out is paid for below by a positive test that exactly one key carries it.
_ASHEN_BUNDLE = tuple(REGION_GRACE_POINTS.get(FINALE_REGION, ()))
_ASHEN_KEY = f"{FINALE_REGION} Lock"


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
            if child == "Raya Lucaria Academy":
                # 🛑 NO LONGER WALLED (2026-08-16). The Academy Glintstone Key gate was retired, so
                # this child keeps its containment and its synthetic open flag but has no wall left
                # to withhold for. Named rather than skipped: an unpaired child fails CLOSED, so
                # "Raya's bundle is empty again" is a real regression this line must still catch.
                self.assertTrue(rg.get(f"{child} Lock"),
                                "the Academy Lock must grant its bundle -- see features/graces "
                                "WALL_ARMED and issue #740")
                continue
            self.assertEqual(rg.get(f"{child} Lock"), [],
                             f"{child}'s bundle must be withheld while its wall is armed")

    def test_no_bundle_carries_a_walled_grace(self):
        # no OTHER key may smuggle a capital/Academy grace either (the pre-v2 fold bug shape).
        # The invariant is "no key smuggles a grace past a wall it does not own" -- see the
        # _ASHEN_BUNDLE note at the top for why 71122-71125 is not such a grace.
        rg = self._rg()
        for key, fs in rg.items():
            # ⭐ RAYA'S OWN LOCK IS NOW ENTITLED TO RAYA'S GRACES (2026-08-16, #740). The invariant
            # this test exists for is "no key smuggles a grace past a wall it does not OWN" -- and
            # with the Academy wall retired, the Academy Lock owns them outright. Every OTHER key
            # carrying a _RAYA grace is still the fold bug and still fails here.
            if key == "Raya Lucaria Academy Lock":
                continue
            leaked = [g for g in fs if g in _RAYA
                      or (g in _LEYN and g != _ROUNDTABLE and g not in _ASHEN_BUNDLE)]
            self.assertFalse(leaked, f"{key} carries walled graces {leaked}")

    def test_the_ashen_bundle_rides_its_own_key_and_only_its_own_key(self):
        """The price of the _ASHEN_BUNDLE carve-out above, paid in full.

        The Ashen Capital has NO walk-in entrance -- warping to these four graces is the only way
        in -- so its lock must carry the whole bundle or it opens nothing. And exactly because the
        band above no longer flags them, some other key carrying them would go unnoticed: that is
        the old capital-grace-smuggling bug shape at a new address (before 2026-08-06 the graces
        were force-skipped in gen_data precisely because riding LEYNDELL's lock warped players
        into a capital they had not burned)."""
        self.assertTrue(_ASHEN_BUNDLE,
                        "no Ashen grace bundle in the generated table -- the carve-out in "
                        "test_no_bundle_carries_a_walled_grace is subtracting nothing and that "
                        "test is weaker than it reads")
        rg = self._rg()
        self.assertEqual(rg.get(_ASHEN_KEY), list(_ASHEN_BUNDLE),
                         f"{_ASHEN_KEY} must carry its bundle in full -- it is the only way in")
        for key, fs in rg.items():
            if key == _ASHEN_KEY:
                continue
            smuggled = [g for g in fs if g in _ASHEN_BUNDLE]
            self.assertFalse(smuggled, f"{key} carries Ashen Capital graces {smuggled}")

    def test_hub_grace_is_a_start_grace_not_a_bundle_rider(self):
        sd = self.world.fill_slot_data()
        for key, fs in sd[contract.REGION_GRACES].items():
            self.assertNotIn(_ROUNDTABLE, fs, f"71190 (HUB) must not ride bundle {key}")
        self.assertIn(_ROUNDTABLE, sd.get(contract.START_GRACES, []),
                      "the Roundtable/HUB grace 71190 must be granted as a start grace")

    def test_torrent_enable_flag_rides_the_whistle_grant(self):
        # start_with_steed (frozen ON) grants the whistle GOODS via the UNIQUE path: the pair
        # [whistle, 60100] in uniqueStartGrants makes the client set the Torrent enable flag AS
        # PART OF the grant (er-torrent-regionlock-mountless: without 60100 the whistle is inert).
        # 60100 must NOT ride startGraces any more -- the unconditional 7165bf8 shape would pre-set
        # the idempotency latch, and the flag-gated unique grant would then SKIP the whistle goods:
        # flag up, no whistle, still mountless.
        sd = self.world.fill_slot_data()
        steed = getattr(self.world.options, "start_with_steed", None)
        if steed is not None and steed.value:
            self.assertIn([0x40000000 | 130, 60100], sd.get(contract.UNIQUE_START_GRANTS, []),
                          "start_with_steed on -> [whistle, 60100] must be a unique start grant, "
                          "else the whistle is inert and the player is mountless")
        self.assertNotIn(60100, sd.get(contract.START_GRACES, []),
                         "60100 is the whistle grant's idempotency latch -- setting it "
                         "unconditionally in startGraces would make the unique grant skip the "
                         "whistle goods on a fresh save")

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
