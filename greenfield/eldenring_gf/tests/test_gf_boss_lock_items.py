"""Mode-A boss-lock tracker item tests (bossLockItems) -- WorldTestBase.

bossLockItems mints a 'Felled: <Boss>' trophy per KEPT, BASE-GAME boss (DLC bosses are OUT for
v0.2). Mode A is slot_data + client only -- no new pool Items, no fill/logic touch -- so these tests
guard the EMISSION, not placement: presence + non-emptiness on a kept base seed, the
{name/region/boss_ap_id} value shape, base-only scoping (no DLC boss flag leaks even when DLC regions
are kept), the _boss_label derivation over the real reward strings, and that an assembled slot_data
still passes the client contract (profile greenfield).

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring_gf/tests/test_gf_boss_lock_items.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf import contract  # noqa: E402
from worlds.eldenring_gf.boss_data import REGION_BOSSES  # noqa: E402
from worlds.eldenring_gf.region_spine import DLC_REGIONS  # noqa: E402
from worlds.eldenring_gf.features.boss_locks import _boss_label  # noqa: E402

GAME = "Elden Ring (Greenfield)"


# ---------------------------------------------------------------------------------------------
# _boss_label unit cases (pure function -- no world needed).
# ---------------------------------------------------------------------------------------------
def test_boss_label_unit_cases():
    # 'Remembrance of the ' / 'Remembrance of ' prefix strip
    assert _boss_label("Remembrance of the Dancing Lion") == "Dancing Lion"
    assert _boss_label("Remembrance of the Fire Giant") == "Fire Giant"
    assert _boss_label("Remembrance of the Grafted") == "Grafted"
    assert _boss_label("Remembrance of Hoarah Loux") == "Hoarah Loux"
    # "'s Great Rune" / ' Great Rune' suffix strip
    assert _boss_label("Radahn's Great Rune") == "Radahn"
    assert _boss_label("Malenia's Great Rune") == "Malenia"
    assert _boss_label("Mohg's Great Rune") == "Mohg"
    assert _boss_label("Rykard's Great Rune") == "Rykard"
    # neither shape -> pass-through unchanged
    assert _boss_label("Elden Remembrance") == "Elden Remembrance"


def test_rennala_present_under_liurnia():
    # Rennala is a non-standard boss (her kill resolves into the rebirth mechanic + Great Rune of the
    # Unborn, so she has no method=boss_arena reward row) and was historically MISSING from
    # REGION_BOSSES. gen_data.py special-cases her via the artifact-verified m14 defeat flag 14000800,
    # keyed to "Liurnia of the Lakes" -- the capstone re-carve folded Raya Lucaria Academy into
    # Liurnia (it is not a standalone greenfield region). Guard that she stays captured on regen.
    assert "Liurnia of the Lakes" in REGION_BOSSES, "Rennala's region absent from REGION_BOSSES"
    lst = REGION_BOSSES["Liurnia of the Lakes"]
    flags = {fl for _aid, fl, _rw in lst}
    assert 14000800 in flags, f"Rennala defeat flag 14000800 missing (got {flags})"
    entry = next(t for t in lst if t[1] == 14000800)
    _aid, _fl, reward = entry
    assert reward == "Remembrance of the Full Moon Queen", f"unexpected reward {reward!r}"
    assert _boss_label(reward) == "Full Moon Queen", f"bad label {_boss_label(reward)!r}"
    assert isinstance(_aid, int) and _aid > 0, "Rennala boss ap-id must be a real positive location id"


def test_boss_label_over_all_rewards_clean():
    # every real reward string yields a non-empty, trimmed label with no leftover affixes.
    for lst in REGION_BOSSES.values():
        for _aid, _fl, reward in lst:
            lbl = _boss_label(reward)
            assert lbl, f"empty label from {reward!r}"
            assert lbl == lbl.strip(), f"untrimmed label from {reward!r}"
            assert "Remembrance of" not in lbl, f"prefix survived in {lbl!r}"
            assert "Great Rune" not in lbl, f"suffix survived in {lbl!r}"


class BossLockItemsKeptBase(WorldTestBase):
    """Full Shattering (num_regions=0) keeps every eligible region -- base AND DLC. That guarantees
    base bosses are present (non-empty assert) while DLC regions are ALSO kept, making the no-leak
    assertions meaningful (the emission must exclude DLC bosses on region grounds, not because the
    region happened to be sealed)."""
    game = GAME
    options = {"num_regions": 0}

    def _items(self):
        return self.world.fill_slot_data()[contract.BOSS_LOCK_ITEMS]

    def test_present_and_nonempty(self):
        sd = self.world.fill_slot_data()
        self.assertIn(contract.BOSS_LOCK_ITEMS, sd, "bossLockItems must be emitted")
        self.assertTrue(sd[contract.BOSS_LOCK_ITEMS],
                        "a kept base seed must mint at least one Felled: trophy")

    def test_value_shape_and_scoping(self):
        kept = set(self.world._kept())
        for k, v in self._items().items():
            # key = positive stringified-int boss-defeat flag
            self.assertEqual(k, str(int(k)), "bossLockItems keys are stringified boss flags")
            self.assertGreater(int(k), 0, "boss flag must be a positive int")
            # value = {name, region, boss_ap_id}
            self.assertIsInstance(v, dict)
            self.assertTrue(v["name"].startswith("Felled: "), f"name must be a Felled: trophy: {v!r}")
            self.assertGreater(len(v["name"]), len("Felled: "), "boss label must be non-empty")
            self.assertIn(v["region"], kept, "boss region must be kept")
            self.assertNotIn(v["region"], DLC_REGIONS, "no DLC boss may leak into bossLockItems")
            self.assertIsInstance(v["boss_ap_id"], int)

    def test_no_dlc_boss_flag_leaks(self):
        # every DLC boss flag must be ABSENT even though DLC regions are kept this seed.
        dlc_flags = {str(fl) for r, lst in REGION_BOSSES.items() if r in DLC_REGIONS
                     for _aid, fl, _rw in lst}
        leaked = dlc_flags & set(self._items())
        self.assertFalse(leaked, f"DLC boss flags leaked into bossLockItems: {sorted(leaked)}")

    def test_covers_every_kept_base_boss(self):
        # exactly the base-region kept bosses, one entry per boss flag (nothing missing, nothing extra).
        kept = set(self.world._kept())
        expected = {str(fl) for r, lst in REGION_BOSSES.items()
                    if r in kept and r not in DLC_REGIONS for _aid, fl, _rw in lst}
        self.assertEqual(set(self._items()), expected)

    def test_slot_data_passes_contract(self):
        # strict greenfield validation: raises ContractError if bossLockItems (or anything else)
        # is undeclared / wrong-shaped. bossLockItems is declared ANY, so this also proves it is
        # a DECLARED key (an undeclared emitted key would be rejected by the F2 strict-emission gate).
        sd = self.world.fill_slot_data()
        contract.validate_slot_data(sd, profile=contract.GREENFIELD, strict=True)
