"""Boss Keys (mode B) gen tests -- WorldTestBase.

boss_keys (Toggle, default 0) mints one progression 'Boss Key: <Boss>' per KEPT base boss (same set
and labels as the mode-A Felled trophies), LOGIC-gates each boss's OWN AP check on has(key), adds a
"gate" field to every bossLockItems entry, and fills sweepLockGates (kept-region sweep flag -> the
region's representative base Boss Key). OFF: no key items, no gate field, sweepLockGates stays {} --
pool + slot_data are HEAD-identical bar the inert options.boss_keys echo. WorldTestBase.setUp runs
the FULL fill (distribute_items_restrictive), so a class that constructs at all proves the seed
genned WINNABLE (no FillError) -- BossKeysCuratedFill guards the risky curated_fill combo.

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
from worlds.eldenring_gf.features.boss_locks import _boss_label, _base_boss_key_names  # noqa: E402

GAME = "Elden Ring (Greenfield)"


def _base_boss_labels():
    return [_boss_label(rw) for r, lst in REGION_BOSSES.items() if r not in DLC_REGIONS
            for (_a, _f, rw) in lst]


class BossKeyNamesUnit(unittest.TestCase):
    def test_one_key_per_base_boss_and_unique(self):
        names = _base_boss_key_names()
        self.assertTrue(names, "must mint keys for the base bosses")
        self.assertEqual(len(names), len(set(names)), "boss key names must be unique")
        self.assertEqual(len(names), len(_base_boss_labels()),
                         "one Boss Key per base REGION_BOSSES entry")
        for n in names:
            self.assertTrue(n.startswith("Boss Key: "), f"bad key name {n!r}")

    def test_no_dlc_boss_mints_a_key(self):
        dlc = {_boss_label(rw) for r, lst in REGION_BOSSES.items() if r in DLC_REGIONS
               for (_a, _f, rw) in lst}
        names = set(_base_boss_key_names())
        for d in dlc:
            self.assertNotIn("Boss Key: " + d, names,
                             "DLC boss must not mint a Boss Key (base-only, v0.2)")


class BossKeysOn(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "boss_keys": True}

    def _kept_base_labels(self):
        kept = set(self.world._kept())
        return [_boss_label(rw) for r, lst in REGION_BOSSES.items()
                if r in kept and r not in DLC_REGIONS for (_a, _f, rw) in lst]

    def _own_pool(self):
        return [it for it in self.multiworld.itempool if it.player == self.world.player]

    def test_key_items_in_pool_once_each_progression(self):
        labels = self._kept_base_labels()
        self.assertTrue(labels)
        c = Counter(it.name for it in self._own_pool() if it.name.startswith("Boss Key: "))
        self.assertEqual(set(c), {"Boss Key: " + l for l in labels},
                         "exactly the kept base bosses get a key")
        for name, n in c.items():
            self.assertEqual(n, 1, f"{name} must appear exactly once")
        for it in self._own_pool():
            if it.name.startswith("Boss Key: "):
                self.assertTrue(it.advancement, "Boss Key must be progression")

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

    def test_sweep_lock_gates_nonempty_and_valid(self):
        sd = self.world.fill_slot_data()
        gates = sd["sweepLockGates"]
        self.assertTrue(gates, "sweepLockGates must be non-empty under boss_keys")
        sweepflags = set(sd[contract.DUNGEON_SWEEP_FLAGS])
        keyset = {"Boss Key: " + l for l in self._kept_base_labels()}
        for fl, keyname in gates.items():
            self.assertEqual(fl, str(int(fl)), "gate keys are stringified sweep flags")
            self.assertIn(fl, sweepflags, "gate key must be an emitted dungeon-sweep flag")
            self.assertIn(keyname, keyset, "gate value must be a real kept base Boss Key")

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

    def test_sweep_gates_empty(self):
        self.assertEqual(self.world.fill_slot_data().get("sweepLockGates", {}), {},
                         "sweepLockGates empty when off")

    def test_options_echo_present_inert(self):
        opts = self.world.fill_slot_data()["options"]
        self.assertIn("boss_keys", opts)
        self.assertEqual(opts["boss_keys"], 0, "boss_keys echoes 0 when off")

    def test_slot_data_passes_contract(self):
        contract.validate_slot_data(self.world.fill_slot_data(), profile=contract.GREENFIELD, strict=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
