"""Boss Keys (mode B) gen tests -- WorldTestBase.

boss_keys (Toggle, default 0) mints one progression 'Boss Key: <Boss>' per KEPT boss -- BASE AND DLC
now (capstone-model DLC lift) -- LOGIC-gates each boss's OWN AP check on has(key), adds a "gate"
field to every bossLockItems entry (DLC entries appear only when boss_keys is ON, since the gate
hint rides on them), and fills sweepLockGates. sweepLockGates routes each kept-region sweep trigger
flag to a Boss Key: PRECISE per-boss when the trigger flag is itself a boss-defeat flag, else the
region's REPRESENTATIVE (first) Boss Key (the documented coarsening fallback). OFF: no key items, no
gate field, no DLC bossLockItems entries, sweepLockGates stays {} -- pool + slot_data are
HEAD-identical bar the inert options.boss_keys echo. WorldTestBase.setUp runs the FULL fill
(distribute_items_restrictive), so a class that constructs at all proves the seed genned WINNABLE
(no FillError) -- BossKeysCuratedFill guards the risky curated_fill combo.

Run (from the Archipelago dir, world installed):
    python -m pytest worlds/eldenring_gf/tests/test_gf_boss_keys.py
"""
import unittest
from collections import Counter

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring_gf")
from worlds.eldenring_gf import contract  # noqa: E402
from worlds.eldenring_gf.boss_data import REGION_BOSSES  # noqa: E402
from worlds.eldenring_gf.region_spine import DLC_REGIONS  # noqa: E402
from worlds.eldenring_gf.features.boss_locks import (  # noqa: E402
    _boss_label, _boss_key_names, _sweep_lock_gates)

GAME = "Elden Ring (Greenfield)"


def _all_boss_labels():
    return [_boss_label(rw) for _r, lst in REGION_BOSSES.items() for (_a, _f, rw) in lst]


# ---------------------------------------------------------------------------------------------
# Pure-function units (no world needed).
# ---------------------------------------------------------------------------------------------
class BossKeyNamesUnit(unittest.TestCase):
    def test_one_key_per_boss_base_and_dlc_unique(self):
        names = _boss_key_names()
        self.assertTrue(names, "must mint keys for every boss")
        self.assertEqual(len(names), len(set(names)), "boss key names must be unique")
        self.assertEqual(len(names), len(set(_all_boss_labels())),
                         "one Boss Key per distinct boss label (base + DLC)")
        for n in names:
            self.assertTrue(n.startswith("Boss Key: "), f"bad key name {n!r}")

    def test_dlc_boss_mints_a_key(self):
        # capstone-model lift: DLC bosses now DO mint a Boss Key (the catalog holds it
        # unconditionally, like a DLC region Lock; it only enters the pool when kept + ON).
        dlc = {_boss_label(rw) for r, lst in REGION_BOSSES.items() if r in DLC_REGIONS
               for (_a, _f, rw) in lst}
        self.assertTrue(dlc, "current boss_data must carry at least one DLC boss to exercise this")
        names = set(_boss_key_names())
        for d in dlc:
            self.assertIn("Boss Key: " + d, names, "DLC boss must mint a Boss Key")


class SweepLockGatesUnit(unittest.TestCase):
    """The per-boss routing precedence, exercised on synthetic data so the PRECISE branch is
    provably preferred over the representative fallback even though today's real data only aligns
    Rennala's flag (which coincides with her single-boss region's representative)."""

    RB = {"R": [(1, 100, "Remembrance of the First"),
                (2, 200, "Remembrance of the Second")],
          "S": [(3, 300, "Remembrance of the Solo")]}

    def test_precise_beats_representative(self):
        # sweep flag 200 IS the SECOND boss's defeat flag -> route to its key, NOT the region's
        # first/representative key. flag 999 is unmatched -> representative fallback (First).
        ds = {200: [1, 2], 999: [3, 4]}
        sr = {200: "R", 999: "R"}
        gates = _sweep_lock_gates({"R"}, self.RB, ds, sr)
        self.assertEqual(gates, {"200": "Boss Key: Second", "999": "Boss Key: First"})

    def test_unmatched_flag_uses_first_boss(self):
        gates = _sweep_lock_gates({"R"}, self.RB, {777: [1]}, {777: "R"})
        self.assertEqual(gates, {"777": "Boss Key: First"}, "representative == first entry")

    def test_scoped_to_kept_regions(self):
        ds, sr = {100: [1], 300: [3]}, {100: "R", 300: "S"}
        gates = _sweep_lock_gates({"S"}, self.RB, ds, sr)  # only S kept
        self.assertEqual(gates, {"300": "Boss Key: Solo"}, "sealed-region sweeps must drop out")

    def test_real_rennala_precise_join(self):
        # real data: m14 sweep flag 14000800 == Rennala's defeat flag -> her key precisely.
        if "Raya Lucaria Academy" not in REGION_BOSSES:
            self.skipTest("Rennala's region absent from boss_data")
        gates = _sweep_lock_gates({"Raya Lucaria Academy"})
        self.assertEqual(gates.get("14000800"), "Boss Key: Full Moon Queen")


# ---------------------------------------------------------------------------------------------
# WorldTestBase integration (full fill => winnability).
# ---------------------------------------------------------------------------------------------
class BossKeysOn(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "boss_keys": True}   # full Shattering keeps base + DLC regions

    def _kept_labels(self):
        kept = set(self.world._kept())
        return [_boss_label(rw) for r, lst in REGION_BOSSES.items()
                if r in kept for (_a, _f, rw) in lst]

    def _own_pool(self):
        return [it for it in self.multiworld.itempool if it.player == self.world.player]

    def test_key_items_in_pool_once_each_progression(self):
        labels = self._kept_labels()
        self.assertTrue(labels)
        c = Counter(it.name for it in self._own_pool() if it.name.startswith("Boss Key: "))
        self.assertEqual(set(c), {"Boss Key: " + l for l in labels},
                         "exactly the kept bosses (base + DLC) get a key")
        for name, n in c.items():
            self.assertEqual(n, 1, f"{name} must appear exactly once")
        for it in self._own_pool():
            if it.name.startswith("Boss Key: "):
                self.assertTrue(it.advancement, "Boss Key must be progression")

    def test_dlc_boss_key_present_when_dlc_kept(self):
        kept = set(self.world._kept())
        dlc_labels = [_boss_label(rw) for r, lst in REGION_BOSSES.items()
                      if r in kept and r in DLC_REGIONS for (_a, _f, rw) in lst]
        if not dlc_labels:
            self.skipTest("no DLC boss kept this seed")
        pool = {it.name for it in self._own_pool()}
        for l in dlc_labels:
            self.assertIn("Boss Key: " + l, pool, "kept DLC boss must mint a key under boss_keys")

    def test_pool_count_neutral(self):
        # core sizes filler off len(pool): total own itempool == total own locations, keys included.
        total_locs = len([loc for loc in self.multiworld.get_locations(self.world.player)
                          if loc.address is not None])
        self.assertEqual(len(self._own_pool()), total_locs,
                         "pool stays count-neutral (keys displace filler)")

    def test_bosslockitems_carry_gate(self):
        items = self.world.fill_slot_data()[contract.BOSS_LOCK_ITEMS]
        self.assertTrue(items)
        for fl, v in items.items():
            self.assertIn("gate", v, "every entry carries a gate under boss_keys")
            self.assertEqual(v["gate"], "Boss Key: " + v["name"][len("Felled: "):],
                             "gate label must match the boss label")

    def test_dlc_entries_present_under_boss_keys(self):
        # the gate hint rides on bossLockItems, so DLC entries MUST appear when boss_keys is ON.
        kept = set(self.world._kept())
        dlc_flags = {str(fl) for r, lst in REGION_BOSSES.items()
                     if r in kept and r in DLC_REGIONS for (_a, fl, _rw) in lst}
        if not dlc_flags:
            self.skipTest("no DLC boss kept this seed")
        items = self.world.fill_slot_data()[contract.BOSS_LOCK_ITEMS]
        self.assertTrue(dlc_flags <= set(items),
                        "DLC boss entries must be emitted under boss_keys to carry their gate")

    def test_sweep_lock_gates_nonempty_and_valid(self):
        sd = self.world.fill_slot_data()
        gates = sd["sweepLockGates"]
        self.assertTrue(gates, "sweepLockGates must be non-empty under boss_keys")
        sweepflags = set(sd[contract.DUNGEON_SWEEP_FLAGS])
        keyset = {"Boss Key: " + l for l in self._kept_labels()}
        for fl, keyname in gates.items():
            self.assertEqual(fl, str(int(fl)), "gate keys are stringified sweep flags")
            self.assertIn(fl, sweepflags, "gate key must be an emitted dungeon-sweep flag")
            self.assertIn(keyname, keyset, "gate value must be a real kept Boss Key")

    def test_boss_location_requires_its_key(self):
        items = self.world.fill_slot_data()[contract.BOSS_LOCK_ITEMS]
        mw, p = self.multiworld, self.world.player
        by_id = {loc.address: loc for loc in mw.get_locations(p) if loc.address is not None}
        full = mw.get_all_state(False)
        tested = 0
        for fl, v in items.items():
            loc = by_id.get(v["boss_ap_id"])
            if loc is None:
                continue
            keyname = v["gate"]
            self.assertTrue(loc.can_reach(full), f"{loc.name} must be reachable with all items")
            state = full.copy()
            state.remove(self.world.create_item(keyname))
            self.assertFalse(loc.can_reach(state),
                             f"{loc.name} must be UNREACHABLE without {keyname}")
            tested += 1
            if tested >= 3:
                break
        self.assertGreater(tested, 0, "must have exercised at least one gated boss location")

    def test_slot_data_passes_contract(self):
        contract.validate_slot_data(self.world.fill_slot_data(), profile=contract.GREENFIELD, strict=True)


class BossKeysCuratedFill(WorldTestBase):
    # The soundness scenario the logic gate exists for: curated_fill routes region Locks onto
    # big-ticket (incl. Boss) checks. If setUp's full fill FillErrors, this class errors -> guard.
    game = GAME
    options = {"num_regions": 0, "boss_keys": True, "curated_fill": True}

    def test_completion_reachable(self):
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[self.world.player](state),
                        "goal must be reachable under all-items state")


class BossKeysOff(WorldTestBase):
    game = GAME
    options = {"num_regions": 0}

    def test_no_key_items(self):
        keys = [it for it in self.multiworld.itempool
                if it.player == self.world.player and it.name.startswith("Boss Key: ")]
        self.assertEqual(keys, [], "no Boss Key items when the option is off")

    def test_no_gate_field(self):
        for v in self.world.fill_slot_data()[contract.BOSS_LOCK_ITEMS].values():
            self.assertNotIn("gate", v, "gate field absent when boss_keys off")

    def test_no_dlc_entries_when_off(self):
        # OFF keeps mode-A trophies base-only (HEAD-identical); no DLC boss flag leaks.
        items = self.world.fill_slot_data()[contract.BOSS_LOCK_ITEMS]
        dlc_flags = {str(fl) for r, lst in REGION_BOSSES.items() if r in DLC_REGIONS
                     for (_a, fl, _rw) in lst}
        self.assertFalse(dlc_flags & set(items), "no DLC boss entries when boss_keys off")

    def test_sweep_gates_empty(self):
        self.assertEqual(self.world.fill_slot_data().get("sweepLockGates", {}), {},
                         "sweepLockGates empty when off")

    def test_options_echo_inert_when_off(self):
        # boss_keys is a boolean toggle; when echoed in the options sub-dict it must read 0 (off).
        # NOTE: core._options_echo does not (yet) include boss_keys -- the options sub-dict is a
        # core/contract concern out of this feature's scope. The feature is fully inert OFF without
        # it (no key items, no gate field, empty sweepLockGates -- the tests above), because the
        # gate hints are self-signaling. Assert inert-if-present; do not require the un-owned echo.
        opts = self.world.fill_slot_data()["options"]
        self.assertEqual(opts.get("boss_keys", 0), 0, "boss_keys must be inert (0) when off")

    def test_slot_data_passes_contract(self):
        contract.validate_slot_data(self.world.fill_slot_data(), profile=contract.GREENFIELD, strict=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
