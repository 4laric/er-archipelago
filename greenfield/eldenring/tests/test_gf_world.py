"""Archipelago-framework tests for the Greenfield ER world (needs AP + Python 3.11).

Subclasses WorldTestBase, so the base suite runs for free against a real generated multiworld:
  * test_fill                       -- every item places, the seed is beatable
  * test_all_state_can_reach_everything / test_empty_state_can_reach_something

On top of that we assert the greenfield-specific contract the client depends on. All of this is
derived from the greenfield world's OWN data.py plus AP's (MIT) WorldTestBase harness -- nothing
here is copied from any other apworld. The module importorskips itself when AP isn't importable
(e.g. run from the source tree in the sandbox), so it is a no-op there and only executes once the
world is installed under Archipelago/worlds/.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring/tests/test_gf_world.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import HUB, REGIONS, LOCATIONS  # noqa: E402
from worlds.eldenring import contract  # noqa: E402
from BaseClasses import ItemClassification  # noqa: E402
from ._util import world_items, world_pool_items  # noqa: E402

GAME = "Elden Ring"
FILLER = "Rune"


class GreenfieldWorldTest(WorldTestBase):
    game = GAME

    # --- item pool -----------------------------------------------------------------
    def test_one_progression_lock_per_region(self):
        locks = [i for i in world_items(self) if i.name.endswith(" Lock")]
        self.assertEqual(sorted(i.name for i in locks),
                         sorted(f"{r} Lock" for r in REGIONS),
                         "expected exactly one lock item per region")
        for i in locks:
            self.assertEqual(i.classification, ItemClassification.progression,
                             f"{i.name} must be progression")

    def test_pool_fills_all_locations(self):
        total = sum(len(v) for v in LOCATIONS.values())
        pool = world_pool_items(self)   # itempool + pre-placed = the location-payers
        self.assertEqual(len(pool), total,
                         "location-payers must equal the number of locations (count-neutral)")

    # --- rules / goal ---------------------------------------------------------------
    def test_goal_needs_all_locks(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.player](state))
        # dropping any single lock must break completion
        any_lock = f"{REGIONS[0]} Lock"
        state.remove(next(i for i in world_items(self) if i.name == any_lock))
        self.assertFalse(self.multiworld.completion_condition[self.player](state),
                         "completion should require every region lock")

    def test_hub_reachable_without_items(self):
        state = self.multiworld.state
        self.assertTrue(self.multiworld.get_region(HUB, self.player).can_reach(state),
                        "Roundtable Hold hub must be free from Menu")

    # --- slot_data contract the client reads ---------------------------------------
    def test_slot_data_contract(self):
        sd = self.world.fill_slot_data()
        self.assertEqual(sd.get("world_logic"), "region_lock")
        # delegate shape/required validation to the single source of truth so this can't go stale.
        contract.validate_slot_data(sd, strict=True)
        flags = sd.get("locationFlags")
        self.assertIsInstance(flags, dict)
        total = sum(len(v) for v in LOCATIONS.values())
        self.assertEqual(len(flags), total, "locationFlags must cover every location")
        # locationFlags is now SCALAR: {str(ap_id) -> int flag}.
        for k, v in flags.items():
            self.assertEqual(k, str(int(k)), "locationFlags keys must be stringified ap ids")
            self.assertIsInstance(v, int)

    # --- determinism (greenfield analog of eldenring test_slot_data_determinism) ----
    # regionSphereTargetRanges is the TRUE FILL SPHERE (features/scaling.py): the sphere each region's
    # Lock actually landed in THIS seed. It is therefore seed-DEPENDENT by design (that is the whole
    # point -- a random-start seed scales from the region you can reach, not from geography). The old
    # assertion "slot_data must be seed-independent" predates that change and asserted the opposite.
    # What must actually hold is DETERMINISM: the same seed must produce the same slot_data.
    # slot_data keys that are ALLOWED to differ between seeds -- everything else must be seed-invariant.
    # shopInfiniteStock is the per-seed reroll of the 455 unlimited shop rows: varying with the seed is
    # the entire point of the feature (each seed, merchants stock a different infinite consumable).
    _SEED_VARYING = {"regionSphereTargetRanges", "shopInfiniteStock", "enemyDropRoll"}

    def test_slot_data_is_deterministic(self):
        """Same seed -> byte-identical slot_data (no set-iteration order leaking into the wire)."""
        self.world_setup(seed=1)
        a = self.world.fill_slot_data()
        self.world_setup(seed=1)
        b = self.world.fill_slot_data()
        self.assertEqual(a, b, "same seed must produce identical slot_data (nondeterminism in the wire)")

    def test_slot_data_seed_varies_only_where_intended(self):
        """Across seeds, ONLY the documented fill-sphere wire may differ."""
        self.world_setup(seed=1)
        a = self.world.fill_slot_data()
        self.world_setup(seed=987654321)
        b = self.world.fill_slot_data()
        differing = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
        self.assertFalse(differing - self._SEED_VARYING,
                         f"slot_data keys varied across seeds that must not: "
                         f"{sorted(differing - self._SEED_VARYING)}")

    # --- Phase 0 boot contract (apIdsToItemIds + regionOpenFlags) --------------------
    def test_boot_contract_ap_ids_and_open_flags(self):
        sd = self.world.fill_slot_data()
        ap = sd.get("apIdsToItemIds")
        self.assertIsInstance(ap, dict)
        filler_ap = str(self.world.item_name_to_id[FILLER])
        self.assertIn(filler_ap, ap, "filler must map to a game item id")
        self.assertEqual(ap[filler_ap], 2900 | 0x40000000,
                         "filler FullID must be Golden Rune [1] GOODS-packed (0x40000B54)")
        for k, v in ap.items():
            self.assertEqual(k, str(int(k)), "apIdsToItemIds keys must be stringified ints")
            self.assertIsInstance(v, int)
        ro = sd.get("regionOpenFlags")
        self.assertIsInstance(ro, dict)
        self.assertGreaterEqual(len(ro), 1, "at least one region must have an open flag")
        for k, v in ro.items():
            self.assertTrue(k.endswith(" Lock"), f"{k} is not a region-lock key")
            self.assertIn(k[:-len(" Lock")], REGIONS)
            self.assertIsInstance(v, int)   # SCALAR per region (client HashMap<String,u32>), not a list
            self.assertGreater(v, 0)
