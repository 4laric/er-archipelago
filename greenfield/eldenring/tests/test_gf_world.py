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
from worlds.eldenring.data import HUB, REGIONS, LOCATIONS, FINALE_REGION  # noqa: E402
from worlds.eldenring import contract  # noqa: E402
from BaseClasses import ItemClassification  # noqa: E402
from ._util import world_items, world_pool_items  # noqa: E402

GAME = "Elden Ring"
FILLER = "Rune"


class GreenfieldWorldTest(WorldTestBase):
    game = GAME
    # Full map: every assertion here counts the WHOLE location set (4879) and every region
    # lock. num_regions defaults to 6 now, which would seal this into a six-region seed.
    options = {"num_regions": 0}

    # --- item pool -----------------------------------------------------------------
    def test_serpent_hunter_is_not_hintable(self):
        self.assertIn(
            "Serpent-Hunter",
            self.world.hint_blacklist,
            "the client grants it at Rykard; the server must not charge for an impossible hint",
        )

    def test_one_progression_lock_per_region(self):
        locks = [i for i in world_items(self) if i.name.endswith(" Lock")]
        # One lock per region. The Ashen Capital Lock is NOT in the AP item pool: since #768 the
        # client grants that region's open flag itself the moment every other goal item is held,
        # so the arena is unreachable until the run is done. The finale region stays out of REGIONS
        # (never rolled, never counted by num_regions) -- assertNotIn below guards that.
        self.assertEqual(sorted(i.name for i in locks),
                         sorted([f"{r} Lock" for r in REGIONS]),
                         "expected exactly one lock item per region")
        self.assertNotIn(FINALE_REGION, REGIONS,
                         "the finale must stay unrollable, or the line above double-counts it")
        for i in locks:
            self.assertEqual(i.classification, ItemClassification.progression,
                             f"{i.name} must be progression")

    def test_pool_fills_all_locations(self):
        total = sum(len(self.world._seed_locations(region)) for region in LOCATIONS)
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
        total = sum(len(self.world._seed_locations(region)) for region in LOCATIONS)
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
    # progressiveGrants: the unified flask ladder (features/progressive.flask_ladder) jitters WHICH
    # rungs are Golden Seeds and which are Sacred Tears, per seed -- so you know roughly when a tear is
    # due but never precisely which pickup it is. The client reads the ladder off slot_data, so a
    # per-seed ladder is exactly what it should see.
    # shopPreviewGoods: features/shops repoints each shop slot that holds a region Lock OR a FOREIGN
    # item to a dedicated spare good, so the client flowers it without re-iconing a real good globally.
    # WHICH slots hold a lock / a foreign item is a per-seed FILL outcome, so the preview map varies by
    # seed by construction (it was invariant only while the repoint loop was dead -- str/int key bug,
    # fixed 2026-07-23). Still DETERMINISTIC per seed (test_slot_data_is_deterministic guards that).
    # filler_foreign_localized: the COUNT of distinct filler names held home this seed. It was
    # constant at 0 while `filler_foreign_pct` defaulted to the 100 no-op; from 2026-08-16 it ships
    # at 70, and the draw is a per-seed copy budget spent over a per-seed pool, so the count moves
    # with the seed by construction. Still deterministic per seed -- the draw is cached on the world
    # and test_slot_data_is_deterministic above is what guards that, which is the property that
    # actually matters on the wire.
    # ⚠️ THIS ESCAPED A FULL LOCAL RUN AND FAILED IN CI. The key is an int count, so two seeds
    # agreeing on it is ordinary luck rather than evidence -- the suite passed locally and went red
    # on the same commit in CI. A varying-count key cannot be witnessed by one comparison; if
    # another lands here, do not conclude it is invariant because one pair matched.
    # `goalRequiredItems` joined this set on 2026-08-16 (#640), and it is a DELIBERATE widening of
    # the wire's variance, not a leak. The required Great Runes used to be `sorted(avail)[:N]` -- an
    # alphabetical prefix, so the key was identical on every seed by construction, which is why it
    # sat outside this set for months without anyone noticing it could not vary. That constancy WAS
    # the bug: at the default of 2 the goal named Godrick's and the Unborn rune forever, and
    # Rykard's (last alphabetically) could only ever be required by a seed asking for all seven
    # ("Rykard's Great Rune considered filler despite setting goal to Great Runes", AHHHREPTAR).
    # The selector is a seeded `world.random` sample now, so the key varies across seeds and is
    # still byte-identical for the SAME seed -- which test_slot_data_is_deterministic above proves
    # and is the property that actually matters on the wire.
    _SEED_VARYING = {"regionSphereTargetRanges", "shopInfiniteStock", "enemyDropRoll",
                     "progressiveGrants", "shopPreviewGoods", "filler_foreign_localized",
                     "goalRequiredItems"}

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
        # The finale's lock is the ONE key here whose region is not in REGIONS -- it is never
        # rolled, but it does own a front-door open flag of its own since SPEC-ashen-capital-lock
        # (before that its space borrowed Leyndell's, via core._lockless_host). Spelt as an
        # explicit union plus a presence check, so it is a carve-out for exactly one name and not
        # a hole any future lockless region could fall through.
        self.assertIn(f"{FINALE_REGION} Lock", ro,
                      "the finale's own open flag must be sent, or the client finds no flag for "
                      "its coarse key and calls the region permanently open")
        _named = set(REGIONS) | {FINALE_REGION}
        for k, v in ro.items():
            self.assertTrue(k.endswith(" Lock"), f"{k} is not a region-lock key")
            self.assertIn(k[:-len(" Lock")], _named)
            self.assertIsInstance(v, int)   # SCALAR per region (client HashMap<String,u32>), not a list
            self.assertGreater(v, 0)
