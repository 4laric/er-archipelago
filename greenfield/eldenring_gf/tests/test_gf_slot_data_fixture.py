"""Contract-snapshot test for the Greenfield ER world's slot_data -- WorldTestBase.

This is the CONTRACT-DRIFT GUARD for the client contract. The Rust client reads a fixed set of
slot_data keys. The single source of truth for the CONTRACT keys and their SHAPES is
`worlds.eldenring_gf.contract` -- so the shape/required checks here delegate to
`contract.validate_slot_data(sd, strict=True)` and CANNOT go stale when a shape changes.

The keyset guard (test_exact_keyset) still asserts the emitted keyset EXACTLY, but it BUILDS the
expected set FROM the contract (every greenfield contract key the world emits) plus the small,
explicitly-listed set of INFORMATIONAL non-contract extras the world also emits (option echoes /
diagnostics the client does not parse). If a source change adds, renames, or drops a slot_data key,
this test fails -- forcing a conscious update here (and a look at whether the client was updated too).

Design (matches the other greenfield WorldTestBase suites):
  * importorskip AP + the installed world, so this is a no-op in the source-tree sandbox and only
    runs once the world is installed under Archipelago/worlds/.
  * option keys/values mirror the feature option classes in core.py + features/*.py:
      - item_shuffle (Toggle)               -> True
      - dungeon_sweep (Choice)              -> "all"   (emits dungeonSweepFlags/dungeonSweeps/sweepLockGates)
      - grace_rando (DefaultOnToggle)       -> True    (emits regionGraces/graceItems/startGraces)
      - pool_builder (Toggle)               -> True    (needs item_shuffle on to have effect)
      - ending_condition (Choice)           -> "great_runes" + great_runes_required=2
      - progressive_flasks (Toggle)         -> True    (emits non-empty progressiveGrants)

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring_gf/tests/test_gf_slot_data_fixture.py
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf.data import HUB, LOCATIONS  # noqa: E402
from worlds.eldenring_gf import contract  # noqa: E402

GAME = "Elden Ring (Greenfield)"

# ---------------------------------------------------------------------------------------------
# THE CONTRACT keyset is derived from `contract.py` (single source of truth) so it can't go stale.
#   * CONTRACT_KEYS_EMITTED = greenfield contract keys that the world actually emits at rich scope
#     (the greenfield contract also declares two OPTIONAL keys the world does not currently emit --
#     enable_dlc, lockRevealFlags -- so we intersect the contract greenfield set with what is emitted
#     to keep the exact-keyset guard honest without hard-coding shapes).
#   * INFORMATIONAL_EXTRAS = keys the world emits that are NOT part of the client contract (option
#     echoes / diagnostics the Rust client ignores). These are listed explicitly so a NEW extra key
#     still trips the guard.
# ---------------------------------------------------------------------------------------------
_GF_CONTRACT_KEYS = {k.name for k in contract.CONTRACT if k.in_profile("greenfield")}

# Non-contract informational keys the greenfield world emits (verified against a real fill_slot_data).
# The Rust client does not parse these; they are option echoes / diagnostics.
INFORMATIONAL_EXTRAS = {
    "region_count",               # int  : len(kept)
    "completionScalingBasis",     # int  : 1
    "completion_scaling",         # int  : client curve id
    "completion_scaling_floor",   # int
    "global_scadutree_blessing",  # int
    "ending_condition",           # str  : "region_locks" | "great_runes"
    "great_runes_required",       # int  : effective (clamped) rune requirement
    "great_rune_items",           # list[str] : required Great Rune item names
    "bossLocations",              # dict[str region] -> list[int]
    "dungeonSweeps",              # dict (location-keyed variant; {} for now)
    "sweepLockGates",             # dict ({} for now)
    "pool_builder",               # bool
    "pool_builder_juice_added",   # int
    "pool_builder_intensity_floor",     # int : resolved juice rarity floor (1..3)
    "pool_builder_juice_candidates",    # int : size of the juice candidate set at this intensity
    "filler_foreign_localized",         # int : distinct filler names forced local this seed
}

# The keys the RICH seed (every optional feature on) is expected to emit: the greenfield contract keys
# it actually emits, plus the informational extras. Built at import time so it tracks contract.py.
# (enable_dlc / lockRevealFlags / versions are contract-declared but not emitted by the current
# world. regionSphereTargetRanges IS emitted as of I2 -- features/scaling.py, the live scaling wire.)
_CONTRACT_NOT_EMITTED = {"enable_dlc", "versions", "regionAttunement"}  # regionAttunement only emitted when attunement_gate is ON; areaLockFlags was UN-FOLDED 2026-07-08 (dead-drop fix, area_locks.py) -> emitted again for ALL regions
EXPECTED_KEYS = (_GF_CONTRACT_KEYS - _CONTRACT_NOT_EMITTED) | INFORMATIONAL_EXTRAS

# REQUIRED greenfield contract keys (must always be present, per the contract).
REQUIRED_KEYS = {k.name for k in contract.CONTRACT if k.required and k.in_profile("greenfield")}

# The subset emitted UNCONDITIONALLY (every seed, whatever the options). The three dungeon-sweep keys
# are the only ones that could drop (when dungeon_sweep == "none"); everything else is always there.
ALWAYS_KEYS = EXPECTED_KEYS - {"dungeonSweepFlags", "dungeonSweeps", "sweepLockGates"}


class SlotDataFixtureRich(WorldTestBase):
    """RICH options: every optional feature on -> exercises EVERY expected key.

    The keyset must equal EXPECTED_KEYS exactly. If a source change adds a new key, sd.keys() -
    EXPECTED_KEYS is non-empty -> fail. If it drops one, EXPECTED_KEYS - sd.keys() is non-empty ->
    fail. Either way this file must be updated deliberately, and the client contract re-checked.
    Shape/required validation is delegated to contract.validate_slot_data so it cannot go stale.
    """
    game = GAME
    options = {
        "item_shuffle": True,
        "dungeon_sweep": "all",
        "grace_rando": True,
        "pool_builder": True,
        "ending_condition": "great_runes",
        "great_runes_required": 2,
        "progressive_flasks": True,
    }

    def test_exact_keyset(self):
        sd = self.world.fill_slot_data()
        got = set(sd.keys())
        missing = EXPECTED_KEYS - got
        extra = got - EXPECTED_KEYS
        self.assertFalse(missing,
                         f"slot_data is MISSING expected client-contract keys: {sorted(missing)}")
        self.assertFalse(extra,
                         "slot_data has UNEXPECTED new keys not in the client contract: "
                         f"{sorted(extra)} -- add them to the contract (or INFORMATIONAL_EXTRAS) "
                         "and update the client on purpose")
        self.assertEqual(got, EXPECTED_KEYS)

    def test_value_types(self):
        # Delegate all shape/required checks to the single source of truth. Raises ContractError on
        # any shape/required drift -- so this test tracks contract.py and never encodes shapes itself.
        sd = self.world.fill_slot_data()
        contract.validate_slot_data(sd, strict=True)

    def test_structural_invariants(self):
        sd = self.world.fill_slot_data()
        # apIdsToItemIds: stringified-int keys -> int values; assert non-empty here.
        self.assertTrue(sd["apIdsToItemIds"], "apIdsToItemIds must not be empty")
        for k, v in sd["apIdsToItemIds"].items():
            self.assertEqual(k, str(int(k)))
            self.assertIsInstance(v, int)
        # locationFlags: stringified-int keys -> SCALAR int values now; cover every hub+kept location.
        kept = list(self.world._kept())
        expected_locs = sum(len(LOCATIONS.get(r, [])) for r in [HUB] + kept)
        self.assertEqual(len(sd["locationFlags"]), expected_locs,
                         "locationFlags must cover every hub+kept location")
        for k, v in sd["locationFlags"].items():
            self.assertEqual(k, str(int(k)))
            self.assertIsInstance(v, int)
        # region_count == len(kept)
        self.assertEqual(sd["region_count"], len(kept),
                         "region_count must equal the number of kept regions")
        # the rich seed actually turned the optional features ON (proves the keys are exercised,
        # not just present-and-empty).
        self.assertEqual(sd["world_logic"], "region_lock")
        self.assertTrue(sd["dungeonSweepFlags"], "dungeon_sweep=all must emit sweep flags")
        self.assertTrue(sd["progressiveGrants"], "progressive_flasks=on must emit grants")
        self.assertTrue(sd["graceItems"], "grace_rando=on must emit scatter grace items")

    def test_required_keys_present(self):
        # every REQUIRED greenfield contract key must be present.
        sd = self.world.fill_slot_data()
        missing = REQUIRED_KEYS - set(sd.keys())
        self.assertFalse(missing, f"slot_data missing REQUIRED contract keys: {sorted(missing)}")

    def test_determinism_same_world_twice(self):
        # fill_slot_data() on the same world twice returns equal keysets (and equal payloads).
        a = self.world.fill_slot_data()
        b = self.world.fill_slot_data()
        self.assertEqual(set(a.keys()), set(b.keys()),
                         "fill_slot_data must return a stable keyset across calls")
        self.assertEqual(a, b, "fill_slot_data must be deterministic on the same world")


class SlotDataFixtureDefault(WorldTestBase):
    """DEFAULT options: the always-present keys must still be there and pass the contract.

    Only grace_rando is pinned OFF here (its default is ON) to also exercise the empty-graceItems
    path. Everything else is left at its option default. NOTE: dungeon_sweep DEFAULTS to "all", so the
    three sweep keys are present by default too; the default class therefore asserts a SUPERSET of
    ALWAYS_KEYS (>=), not an exact match -- the exact-keyset contract guard lives in the rich class.
    """
    game = GAME
    options = {"grace_rando": False}

    def test_always_keys_present(self):
        sd = self.world.fill_slot_data()
        got = set(sd.keys())
        missing = ALWAYS_KEYS - got
        self.assertFalse(missing,
                         f"default seed is MISSING always-present contract keys: {sorted(missing)}")
        # nothing outside the full contract may appear even at defaults.
        extra = got - EXPECTED_KEYS
        self.assertFalse(extra,
                         f"default seed emitted keys outside the contract: {sorted(extra)}")

    def test_value_types(self):
        sd = self.world.fill_slot_data()
        contract.validate_slot_data(sd, strict=True)

    def test_bundle_grace_has_no_scatter(self):
        # grace_rando off -> bundle mode -> graceItems empty, but the KEY is still present.
        sd = self.world.fill_slot_data()
        self.assertIn("graceItems", sd)
        self.assertEqual(sd["graceItems"], {})

    def test_determinism_same_world_twice(self):
        a = self.world.fill_slot_data()
        b = self.world.fill_slot_data()
        self.assertEqual(set(a.keys()), set(b.keys()))
        self.assertEqual(a, b)
