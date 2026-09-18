"""Grace bundles -- every kept region's Lock lights its own bundle in full.

History: gated children (region_spine.REGION_PARENT) once had their bundle WITHHELD while a wall
the game enforces was armed in logic -- the Academy seal until 2026-08-16 (#740), the capital's
Great-Rune wall until 2026-09-14 (Leyndell becomes an ordinary Lock region). features/graces.py
emitted the child's bundle EMPTY and the player walked in past the game's own wall to touch the
graces themselves. Both walls are retired now: WALL_ARMED is False for every child in every seed,
and the bundle rides the Lock like any ungated region's.

This file keeps the bundle-shape assertions (no key smuggles another region's graces, the Ashen
carve-out, the HUB grace) and the retired-key guard close to the feature they watch. The
withholding mechanism itself is still implemented (bundle_withheld fails closed for an unpaired
child) and is still guarded by test_gf_gated_children.py's pairing test -- no wall being armed
is a ruling, not a deleted code path.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.tables.region_graces import REGION_GRACE_POINTS  # noqa: E402
from worlds.eldenring.region_spine import REGION_PARENT  # noqa: E402
from worlds.eldenring.tables.data import FINALE_REGION  # noqa: E402

GAME = "Elden Ring"
_RAYA = range(71400, 71500)
_LEYN = range(71100, 71200)
_ROUNDTABLE = 71190
# ⭐ THE 711xx BAND STOPPED BELONGING TO ONE REGION on 2026-08-06 (SPEC-ashen-capital-lock).
# `_LEYN` is a deliberately blanket band -- it catches Royal warp flags that are not even in
# Leyndell's own bundle (71100/71101/71106/71107), which is why it is a band and not a set. But the
# Ashen Capital now owns a REAL bundle at 71122-71125, inside that band, and those graces are NOT
# behind the Leyndell Lock: they are behind the burn ITEM (`Ashen Capital Lock`), which is the one
# key entitled to carry them. So the band keeps its breadth and the Ashen bundle is carved out BY
# NAME, derived from the generated table rather than re-typed as a range -- and the carve-out is
# paid for below by a positive test that exactly one key carries it.
_ASHEN_BUNDLE = tuple(REGION_GRACE_POINTS.get(FINALE_REGION, ()))
_ASHEN_KEY = f"{FINALE_REGION} Lock"


class BundlesRideTheirLocks(WorldTestBase):
    game = GAME
    run_default_tests = False
    options = {  # no wall is armed on any seed now; the bundle rides the Lock, always
        "num_regions": 0,
    }

    def _rg(self):
        return self.world.fill_slot_data()[contract.REGION_GRACES]

    def test_gated_children_bundles_are_granted(self):
        # 🛑 THE INVERSION (2026-09-14). This asserted every gated child's bundle WITHHELD while
        # its wall was armed. No wall is armed any more -- Raya's since 2026-08-16 (#740),
        # Leyndell's since the rune-wall retirement -- so every kept child grants its bundle in
        # full, exactly like an ungated region. Named per child rather than looped blindly: an
        # unpaired child fails CLOSED (withholds unconditionally), so "Leyndell's bundle is empty
        # again" is a real regression this line must still catch.
        rg = self._rg()
        kept = set(self.world._kept())
        assert {"Raya Lucaria Academy", "Leyndell"} <= kept & set(REGION_PARENT)
        for child in REGION_PARENT:
            if child not in kept:
                continue
            self.assertEqual(rg.get(f"{child} Lock"), list(REGION_GRACE_POINTS[child]),
                             f"{child}'s bundle must ride its Lock in full -- no wall is armed")
        # And the Leyndell bundle is the one the seal-open rides with: it must be non-empty, or
        # the Lock opens a region the player cannot warp into (see test_gf_gated_children.py's
        # lock-only tests for the same property from the logic side).
        self.assertTrue(rg.get("Leyndell Lock"), "the Leyndell Lock must light its graces")

    def test_no_bundle_carries_another_regions_walled_graces(self):
        # No key may smuggle a grace it does not own (the pre-v2 fold bug shape). Each region's
        # own Lock is entitled to its own band -- Raya's and Leyndell's included, since neither
        # wall exists any more. Every OTHER key carrying one is still the fold bug and still
        # fails here. See the _ASHEN_BUNDLE note at the top for why 71122-71125 is not such a
        # grace.
        rg = self._rg()
        for key, fs in rg.items():
            if key in ("Raya Lucaria Academy Lock", "Leyndell Lock"):
                continue
            leaked = [g for g in fs if g in _RAYA
                      or (g in _LEYN and g != _ROUNDTABLE and g not in _ASHEN_BUNDLE)]
            self.assertFalse(leaked, f"{key} carries graces it does not own {leaked}")

    def test_no_bundle_carries_a_walled_grace_it_does_not_own(self):
        # The positive half of the test above: each band IS carried, by exactly its own key, so
        # the smuggling test cannot pass by the bands being empty.
        rg = self._rg()
        raya = [g for g in rg.get("Raya Lucaria Academy Lock", []) if g in _RAYA]
        self.assertTrue(raya, "Raya's own Lock must carry Raya graces")
        leyn = [g for g in rg.get("Leyndell Lock", [])
                if g in _LEYN and g != _ROUNDTABLE and g not in _ASHEN_BUNDLE]
        self.assertTrue(leyn, "Leyndell's own Lock must carry capital graces")

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
                        "test_no_bundle_carries_another_regions_walled_graces is subtracting "
                        "nothing and that test is weaker than it reads")
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
