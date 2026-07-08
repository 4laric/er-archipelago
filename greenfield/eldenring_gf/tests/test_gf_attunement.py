"""Attunement-release gate tests (regionAttunement + random-start graces) -- WorldTestBase.

The gate is opt-in (attunement_gate, default 0). ON: regionAttunement is emitted per kept region with
a satisfiable threshold, the freely-reachable member set, and the bloom (remaining) graces; regionGraces
becomes K seeded-random start-door graces (K = clamp(ceil(n_graces/8),1,3)) and graceItems is empty.
OFF: no regionAttunement, and grace_rando keeps its default freebie behavior (single front-door grace +
non-empty scatter graceItems). Also: the assembled slot_data passes the greenfield contract both ways.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring_gf/tests/test_gf_attunement.py
"""
import math
import unittest
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf import contract  # noqa: E402
from worlds.eldenring_gf.region_graces import REGION_GRACE_POINTS  # noqa: E402
from worlds.eldenring_gf.features.attunement import (  # noqa: E402
    _threshold, _k_start_doors, _freely_reachable)

GAME = "Elden Ring (Greenfield)"


class AttunementUnit(unittest.TestCase):
    def test_threshold_clamp_and_cap(self):
        self.assertEqual(_threshold(0), 0)          # no checks -> trivially attuned
        self.assertEqual(_threshold(3), 3)          # capped at N (< floor 5) so it stays satisfiable
        self.assertEqual(_threshold(30), 5)         # round(3.0)=3 -> floor 5
        self.assertEqual(_threshold(80), 8)         # round(8.0)=8
        self.assertEqual(_threshold(200), 20)       # round(20)=20 -> ceil 20
        self.assertEqual(_threshold(300), 20)       # clamp ceiling
        for n in range(0, 400):
            t = _threshold(n)
            self.assertLessEqual(t, 20)
            self.assertLessEqual(t, n if n else 0)  # never more than the region's own checks
            if n >= 5:
                self.assertGreaterEqual(t, 5)

    def test_k_start_doors(self):
        self.assertEqual(_k_start_doors(1), 1)
        self.assertEqual(_k_start_doors(8), 1)
        self.assertEqual(_k_start_doors(9), 2)
        self.assertEqual(_k_start_doors(24), 3)     # Limgrave
        self.assertEqual(_k_start_doors(10), 2)     # Stormveil
        self.assertEqual(_k_start_doors(2), 1)      # Raya Lucaria
        self.assertEqual(_k_start_doors(999), 3)    # clamp ceiling

    def test_freely_excludes_boss_and_missable(self):
        # Limgrave has real checks; the freely set must be non-empty and a subset of its checks.
        from worlds.eldenring_gf.data import LOCATIONS
        from worlds.eldenring_gf.location_tags import LOCATION_TAGS
        from worlds.eldenring_gf.missable_locations import MISSABLE_LOCATIONS
        all_ids = [aid for (_n, aid, _f) in LOCATIONS.get("Limgrave", [])]
        free = _freely_reachable("Limgrave")
        self.assertTrue(free, "Limgrave freely-reachable set must be non-empty")
        self.assertTrue(set(free) <= set(all_ids))
        for aid in free:
            self.assertNotIn(aid, MISSABLE_LOCATIONS)
            self.assertNotIn("Boss", LOCATION_TAGS.get(aid, ()))


class AttunementOn(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "attunement_gate": True}

    def _sd(self):
        return self.world.fill_slot_data()

    def test_region_attunement_present_and_shaped(self):
        sd = self._sd()
        self.assertIn(contract.REGION_ATTUNEMENT, sd, "regionAttunement must be emitted when the gate is on")
        ra = sd[contract.REGION_ATTUNEMENT]
        self.assertTrue(ra, "regionAttunement must be non-empty for a full-Shattering seed")
        kept = set(self.world._kept())
        for region, v in ra.items():
            self.assertIn(region, kept, "regionAttunement is scoped to kept regions")
            self.assertEqual(set(v), {"threshold", "member_ap_ids", "bloom_flags"})
            self.assertIsInstance(v["threshold"], int)
            self.assertGreaterEqual(v["threshold"], 0)
            self.assertLessEqual(v["threshold"], 20)
            self.assertTrue(all(isinstance(x, int) for x in v["member_ap_ids"]))
            self.assertTrue(all(isinstance(x, int) for x in v["bloom_flags"]))
            # threshold is satisfiable from the region's own freely-reachable checks
            self.assertLessEqual(v["threshold"], len(v["member_ap_ids"]) or v["threshold"])

    def test_limgrave_sane(self):
        v = self._sd()[contract.REGION_ATTUNEMENT]["Limgrave"]
        self.assertGreaterEqual(v["threshold"], 5)
        self.assertLessEqual(v["threshold"], 20)
        self.assertTrue(v["member_ap_ids"], "Limgrave member_ap_ids must be non-empty")

    def test_region_graces_are_k_random_start_doors(self):
        sd = self._sd()
        graces = sd[contract.REGION_GRACES]
        ra = sd[contract.REGION_ATTUNEMENT]
        for region, pool in REGION_GRACE_POINTS.items():
            key = f"{region} Lock"
            if key not in graces:
                continue  # region not kept this seed
            lit = graces[key]
            k = min(_k_start_doors(len(pool)), len(pool))
            self.assertEqual(len(lit), k, f"{region}: expected {k} start-door graces, got {len(lit)}")
            self.assertTrue(set(lit) <= set(pool), f"{region}: start doors must be real region graces")
            # bloom = the pool minus the lit start doors (boss-gated graces are already out of the pool)
            bloom = set(ra[region]["bloom_flags"])
            self.assertEqual(bloom, set(pool) - set(lit), f"{region}: bloom must be pool minus start doors")
            self.assertEqual(bloom & set(lit), set(), f"{region}: bloom and start doors must be disjoint")

    def test_no_scatter_grace_items(self):
        # under the gate the scatter graces fold into the bloom, not the pool -> graceItems is empty.
        self.assertEqual(self._sd().get(contract.GRACE_ITEMS, {}), {})

    def test_slot_data_passes_contract(self):
        contract.validate_slot_data(self._sd(), profile=contract.GREENFIELD, strict=True)


class AttunementOff(WorldTestBase):
    game = GAME
    options = {"num_regions": 0}  # gate off (default); grace_rando default (freebie) behavior

    def test_no_region_attunement(self):
        sd = self.world.fill_slot_data()
        self.assertNotIn(contract.REGION_ATTUNEMENT, sd, "regionAttunement must be ABSENT when the gate is off")

    def test_freebie_grace_behavior_unchanged(self):
        sd = self.world.fill_slot_data()
        graces = sd[contract.REGION_GRACES]
        # freebie default: each kept region's lock lights exactly its single front-door grace
        for key, lit in graces.items():
            self.assertEqual(len(lit), 1, f"{key}: freebie mode lights one front-door grace")
        self.assertTrue(sd.get(contract.GRACE_ITEMS), "freebie mode scatters grace items")

    def test_slot_data_passes_contract(self):
        contract.validate_slot_data(self.world.fill_slot_data(), profile=contract.GREENFIELD, strict=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
