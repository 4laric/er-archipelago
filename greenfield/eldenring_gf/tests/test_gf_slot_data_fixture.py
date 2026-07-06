"""Contract-snapshot test for the Greenfield ER world's slot_data -- WorldTestBase.

This is the CONTRACT-DRIFT GUARD for the client contract. The Rust client reads a fixed set of
slot_data keys (world_logic, locationFlags, apIdsToItemIds, region locks/graces, sweeps, shops,
deathlink, start items, progressive grants, ...). If a future edit to core.py or any features/*.py
adds, renames, or drops a slot_data key, this test fails -- forcing a conscious update here (and, by
extension, a conscious look at whether the client was updated too).

EXPECTED_KEYS below is the single source of truth for "what the client contract is". It is asserted
EXACTLY (subset AND superset) against fill_slot_data().keys() with a RICH option set that turns on
every optional feature, so no key can silently appear or disappear.

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

GAME = "Elden Ring (Greenfield)"

# ---------------------------------------------------------------------------------------------
# THE CONTRACT. Every slot_data key the greenfield world emits when EVERY optional feature is on.
# Adding/removing/renaming a key in core.py or features/*.py MUST be reflected here, or the
# test_exact_keyset assertion below trips. This is deliberate: the client reads exactly these keys.
# ---------------------------------------------------------------------------------------------
EXPECTED_KEYS = {
    # --- core._base_slot_data (always emitted) ---
    "world_logic",            # str  : "region_lock"
    "locationFlags",          # dict[str(ap_id)] -> list[int] (event flags per location)
    "apIdsToItemIds",         # dict[str(ap_id)] -> int (FullID)
    "regionOpenFlags",        # dict["<region> Lock"] -> int (scalar open flag)
    "region_count",           # int  : len(kept)
    "completionScalingBasis", # int  : 1
    "regionSphereTargets",    # dict[str region] -> float (0..1)
    "ending_condition",       # str  : "region_locks" | "great_runes"
    "great_runes_required",   # int  : effective (clamped) rune requirement
    "great_rune_items",       # list[str] : required Great Rune item names
    # --- features/scaling.py (always) ---
    "completion_scaling",         # int  : 4 (client curve id)
    "completion_scaling_floor",   # int
    "global_scadutree_blessing",  # int
    # --- features/boss_locks.py ---
    "bossLocations",          # dict[str region] -> list[int] (always)
    "dungeonSweepFlags",      # dict[str(flag)] -> list[int] (only when dungeon_sweep != none)
    "dungeonSweeps",          # dict (location-keyed variant; {} for now)  (dungeon_sweep != none)
    "sweepLockGates",         # dict ({} for now)                          (dungeon_sweep != none)
    # --- features/shops.py (always) ---
    "shopRowFlags",           # dict[str(ap_id)] -> int (stock flag)
    "shopPreviewGoods",       # dict[str(ap_id)] -> int (FullID)
    # --- features/grace_rando.py (always) ---
    "regionGraces",           # dict["<region> Lock"] -> list[int]
    "graceItems",             # dict["Grace: ..."] -> int (grace flag)
    "startGraces",            # list[int]
    # --- features/deathlink.py (always) ---
    "death_link",             # bool
    # --- features/start_items.py (always) ---
    "startItems",             # list[int] (FullIDs granted at game start)
    # --- features/pool_builder.py (always) ---
    "pool_builder",           # bool
    "pool_builder_juice_added",  # int
    # --- features/progressive.py (always) ---
    "progressiveGrants",      # dict[item_name] -> list[dict] ({"goods": int, "flags": list[int]})
}

# The subset that is emitted UNCONDITIONALLY (every seed, whatever the options). The three
# dungeon-sweep keys are omitted only when dungeon_sweep == "none"; everything else is always there.
ALWAYS_KEYS = EXPECTED_KEYS - {"dungeonSweepFlags", "dungeonSweeps", "sweepLockGates"}


def _assert_types(tc, sd):
    """Value-type invariants shared by both the rich and default worlds (only for keys present)."""
    # scalars
    tc.assertIsInstance(sd["world_logic"], str)
    tc.assertIsInstance(sd["region_count"], int)
    tc.assertIsInstance(sd["completionScalingBasis"], int)
    tc.assertIsInstance(sd["completion_scaling"], int)
    tc.assertIsInstance(sd["completion_scaling_floor"], int)
    tc.assertIsInstance(sd["global_scadutree_blessing"], int)
    tc.assertIsInstance(sd["ending_condition"], str)
    tc.assertIsInstance(sd["great_runes_required"], int)
    tc.assertIsInstance(sd["death_link"], bool)
    tc.assertIsInstance(sd["pool_builder"], bool)
    tc.assertIsInstance(sd["pool_builder_juice_added"], int)

    # list[str]
    tc.assertIsInstance(sd["great_rune_items"], list)
    tc.assertTrue(all(isinstance(x, str) for x in sd["great_rune_items"]))
    # list[int]
    tc.assertIsInstance(sd["startItems"], list)
    tc.assertTrue(all(isinstance(x, int) for x in sd["startItems"]))
    tc.assertIsInstance(sd["startGraces"], list)
    tc.assertTrue(all(isinstance(x, int) for x in sd["startGraces"]))

    # locationFlags : dict[str(int)] -> list[int]
    lf = sd["locationFlags"]
    tc.assertIsInstance(lf, dict)
    for k, v in lf.items():
        tc.assertEqual(k, str(int(k)), "locationFlags keys must be stringified ints")
        tc.assertIsInstance(v, list)
        tc.assertTrue(all(isinstance(f, int) for f in v))

    # apIdsToItemIds : dict[str(int)] -> int
    ap = sd["apIdsToItemIds"]
    tc.assertIsInstance(ap, dict)
    for k, v in ap.items():
        tc.assertEqual(k, str(int(k)), "apIdsToItemIds keys must be stringified ints")
        tc.assertIsInstance(v, int)

    # regionOpenFlags : dict[str] -> int (SCALAR, not a list)
    ro = sd["regionOpenFlags"]
    tc.assertIsInstance(ro, dict)
    for k, v in ro.items():
        tc.assertIsInstance(k, str)
        tc.assertIsInstance(v, int)

    # regionSphereTargets : dict[str] -> float (int is allowed for the single-region edge)
    rs = sd["regionSphereTargets"]
    tc.assertIsInstance(rs, dict)
    for k, v in rs.items():
        tc.assertIsInstance(k, str)
        tc.assertIsInstance(v, (int, float))

    # bossLocations : dict[str] -> list[int]
    bl = sd["bossLocations"]
    tc.assertIsInstance(bl, dict)
    for k, v in bl.items():
        tc.assertIsInstance(k, str)
        tc.assertIsInstance(v, list)
        tc.assertTrue(all(isinstance(x, int) for x in v))

    # shopRowFlags / shopPreviewGoods : dict[str(int)] -> int
    for key in ("shopRowFlags", "shopPreviewGoods"):
        d = sd[key]
        tc.assertIsInstance(d, dict)
        for k, v in d.items():
            tc.assertEqual(k, str(int(k)), f"{key} keys must be stringified ints")
            tc.assertIsInstance(v, int)

    # regionGraces : dict[str] -> list[int]
    rg = sd["regionGraces"]
    tc.assertIsInstance(rg, dict)
    for k, v in rg.items():
        tc.assertIsInstance(k, str)
        tc.assertIsInstance(v, list)
        tc.assertTrue(all(isinstance(x, int) for x in v))

    # graceItems : dict[str] -> int
    gi = sd["graceItems"]
    tc.assertIsInstance(gi, dict)
    for k, v in gi.items():
        tc.assertIsInstance(k, str)
        tc.assertIsInstance(v, int)

    # progressiveGrants : dict[str] -> list[dict] (each {"goods": int, "flags": list[int]})
    pg = sd["progressiveGrants"]
    tc.assertIsInstance(pg, dict)
    for k, ladder in pg.items():
        tc.assertIsInstance(k, str)
        tc.assertIsInstance(ladder, list)
        for step in ladder:
            tc.assertIsInstance(step, dict)
            tc.assertIn("goods", step)
            tc.assertIsInstance(step["goods"], int)
            tc.assertIn("flags", step)
            tc.assertIsInstance(step["flags"], list)
            tc.assertTrue(all(isinstance(f, int) for f in step["flags"]))

    # sweep keys (present only when emitted): dungeonSweepFlags dict[str(int)] -> list[int];
    # dungeonSweeps / sweepLockGates are dicts.
    if "dungeonSweepFlags" in sd:
        dsf = sd["dungeonSweepFlags"]
        tc.assertIsInstance(dsf, dict)
        for k, v in dsf.items():
            tc.assertEqual(k, str(int(k)), "dungeonSweepFlags keys must be stringified ints")
            tc.assertIsInstance(v, list)
            tc.assertTrue(all(isinstance(x, int) for x in v))
        tc.assertIsInstance(sd["dungeonSweeps"], dict)
        tc.assertIsInstance(sd["sweepLockGates"], dict)


class SlotDataFixtureRich(WorldTestBase):
    """RICH options: every optional feature on -> exercises EVERY expected key.

    This is the contract-drift guard: the keyset must equal EXPECTED_KEYS exactly. If a source
    change adds a new key, sd.keys() - EXPECTED_KEYS is non-empty -> fail. If it drops one,
    EXPECTED_KEYS - sd.keys() is non-empty -> fail. Either way, this file must be updated
    deliberately, and the client contract re-checked.
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
                         f"{sorted(extra)} -- add them to EXPECTED_KEYS (and update the client) "
                         "on purpose")
        self.assertEqual(got, EXPECTED_KEYS)

    def test_value_types(self):
        _assert_types(self, self.world.fill_slot_data())

    def test_structural_invariants(self):
        sd = self.world.fill_slot_data()
        # apIdsToItemIds: stringified-int keys -> int values (type-checked; assert non-empty here).
        self.assertTrue(sd["apIdsToItemIds"], "apIdsToItemIds must not be empty")
        for k, v in sd["apIdsToItemIds"].items():
            self.assertEqual(k, str(int(k)))
            self.assertIsInstance(v, int)
        # locationFlags keys are stringified ints and cover every hub+kept location.
        kept = list(self.world._kept())
        expected_locs = sum(len(LOCATIONS.get(r, [])) for r in [HUB] + kept)
        self.assertEqual(len(sd["locationFlags"]), expected_locs,
                         "locationFlags must cover every hub+kept location")
        for k in sd["locationFlags"]:
            self.assertEqual(k, str(int(k)))
        # region_count == len(kept)
        self.assertEqual(sd["region_count"], len(kept),
                         "region_count must equal the number of kept regions")
        # the rich seed actually turned the optional features ON (proves the keys are exercised,
        # not just present-and-empty).
        self.assertEqual(sd["world_logic"], "region_lock")
        self.assertTrue(sd["dungeonSweepFlags"], "dungeon_sweep=all must emit sweep flags")
        self.assertTrue(sd["progressiveGrants"], "progressive_flasks=on must emit grants")
        self.assertTrue(sd["graceItems"], "grace_rando=on must emit scatter grace items")

    def test_determinism_same_world_twice(self):
        # fill_slot_data() on the same world twice returns equal keysets (and equal payloads).
        a = self.world.fill_slot_data()
        b = self.world.fill_slot_data()
        self.assertEqual(set(a.keys()), set(b.keys()),
                         "fill_slot_data must return a stable keyset across calls")
        self.assertEqual(a, b, "fill_slot_data must be deterministic on the same world")


class SlotDataFixtureDefault(WorldTestBase):
    """DEFAULT options: the always-present keys must still be there with correct types.

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
        _assert_types(self, self.world.fill_slot_data())

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
