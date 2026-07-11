"""Grace gates -- Raya Lucaria graces gate on the Academy Glintstone Key, Leyndell graces on N Great
Runes. features/graces.py pulls the gated sub-area graces out of the region-Lock bundle so they don't
light on region unlock, and re-keys them on the gating condition (regionGraces item key / runeGatedGraces).
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")

from worlds.eldenring_gf import contract  # noqa: E402

GAME = "Elden Ring (Greenfield)"
_RAYA = range(71400, 71500)
_LEYN = [g for g in range(71100, 71200) if g != 71190] + [73501, 73502, 73503, 73504]  # +Shunning-Grounds (m35 folds to Leyndell, rune-gated)


class GatesArmed(WorldTestBase):
    game = GAME
    options = {  # defaults arm both gates: item_shuffle on, legacy_dungeon_keys on, leyndell_runes=2
        "item_shuffle": True, "legacy_dungeon_keys": True, "leyndell_runes_required": 2,
    }

    def _sd(self):
        return self.world.fill_slot_data()

    def test_raya_graces_gated_on_academy_key(self):
        sd = self._sd()
        rg = sd[contract.REGION_GRACES]
        liurnia = rg.get("Liurnia of the Lakes Lock", [])
        self.assertFalse([g for g in liurnia if g in _RAYA],
                         "Raya Lucaria graces (714xx) must be pulled from the Liurnia Lock bundle")
        key = rg.get("Academy Glintstone Key", [])
        self.assertTrue(key and all(g in _RAYA for g in key),
                        f"Academy Glintstone Key must carry the Raya graces, got {key}")

    def test_leyndell_graces_rune_gated(self):
        sd = self._sd()
        altus = sd[contract.REGION_GRACES].get("Altus Plateau Lock", [])
        self.assertFalse([g for g in altus if g in _LEYN],
                         "Leyndell capital graces (711xx) must be pulled from the Altus Lock bundle")
        # 71190 (Roundtable, Table of Lost Grace) is an m11 flag but it is the HUB's grace, granted
        # by features/start_grace.py as a START grace -- see graces.py:_ROUNDTABLE_GRACE. It used to
        # ride in the Altus bundle only because m11_10 wrongly folded to Altus (the coarse
        # "Leyndell / Roundtable / Shunning-Grounds" bucket). gen_data now regions m11_10 as
        # Roundtable Hold, so 71190 correctly belongs to NO spoke bundle at all. The intent of this
        # assertion -- "the HUB grace must never be rune-gated" -- is now satisfied more strongly:
        # it cannot be gated because it is not in a gated bundle, and the player always starts with it.
        self.assertNotIn(71190, altus,
                         "71190 is the HUB start grace; it must not ride in the Altus Lock bundle")
        self.assertIn(71190, sd.get(contract.START_GRACES, []),
                      "the Roundtable/HUB grace 71190 must be granted as a start grace")
        rgg = sd.get(contract.RUNE_GATED_GRACES)
        self.assertTrue(rgg, "runeGatedGraces must be emitted when the Leyndell gate is armed")
        self.assertIn("2", rgg, f"expected the N=2 rune requirement key, got {list(rgg)}")
        self.assertTrue(all(g in _LEYN for g in rgg["2"]))
        self.assertTrue(sd.get(contract.GREAT_RUNE_ITEM_IDS),
                        "greatRuneItemIds must be emitted alongside runeGatedGraces")


