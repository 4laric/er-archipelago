"""PHANTOM-FLAG gate (tier A): every check's acquisition flag must EXIST in the game.

Elden Ring event flags are group-allocated: an unallocated id is a no-op. A location keyed on an
invented flag can never be observed to flip, so:
  * the check can never be sent  -> the seed can never be 100%'d;
  * AP fill can place a PROGRESSION item on it -> unrecoverable soft-lock (worst in multiworld, where
    another player's progression item lands on a flag that will never fire).

region_map.csv shipped 49 such checks (`method=synthetic_areacode`, invented ids). 43 of them provably
duplicated a check that already existed under its REAL flag, so gen_data now DROPS any row whose flag
is outside the real-flag universe (a derived predicate, not a blocklist -- so a future invented flag is
dropped automatically). This gate is the regression guard for that.

ORACLE (independent of gen_data): the universe of real acquisition flags, derived straight from the
Smithbox param dump -- `ItemLotParam_map` / `ItemLotParam_enemy` `getItemFlagId*` (world + enemy drops)
UNION `ShopLineupParam.eventFlag_forStock` (shop purchases). Every legit greenfield check is keyed on
one of these; nothing else can back a check.

Skips when the licensing-restricted artifacts are absent (that machine cannot build the universe).

Run:  python -m pytest greenfield/eldenring_gf/tests/test_gf_no_phantom_flags.py
  or: python greenfield/eldenring_gf/tests/test_gf_no_phantom_flags.py
"""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)


def _find_up(rel, start=GF_PKG):
    d = os.path.abspath(start)
    for _ in range(8):
        cand = os.path.join(d, rel)
        if os.path.exists(cand):
            return cand
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


PARAMS = _find_up(os.path.join("elden_ring_artifacts", "vanilla_er", "vanilla_er"))


def _real_flag_universe(param_dir):
    u = set()
    for fn in ("ItemLotParam_map.csv", "ItemLotParam_enemy.csv"):
        p = os.path.join(param_dir, fn)
        if not os.path.isfile(p):
            return None
        with open(p, newline="") as fh:
            rd = csv.DictReader(fh)
            cols = [c for c in rd.fieldnames if c.startswith("getItemFlagId")]
            for r in rd:
                for c in cols:
                    v = r.get(c, "0")
                    if v not in ("", "0", "-1"):
                        try:
                            u.add(int(v))
                        except ValueError:
                            pass
    p = os.path.join(param_dir, "ShopLineupParam.csv")
    if os.path.isfile(p):
        with open(p, newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    f = int(r.get("eventFlag_forStock", 0))
                    if f > 0:
                        u.add(f)
                except (TypeError, ValueError):
                    pass
    return u


class NoPhantomFlags(unittest.TestCase):
    def test_every_check_flag_exists_in_game(self):
        if not PARAMS:
            self.skipTest("elden_ring_artifacts params absent -- cannot build the real-flag universe")
        universe = _real_flag_universe(PARAMS)
        if not universe:
            self.skipTest("ItemLotParam not readable")
        spec = importlib.util.spec_from_file_location("_gfdata", os.path.join(GF_PKG, "data.py"))
        data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(data)

        phantoms = []
        total = 0
        for region, locs in data.LOCATIONS.items():
            for name, ap_id, flag in locs:
                total += 1
                if int(flag) not in universe:
                    phantoms.append(f"  {region} :: {name} (ap {ap_id}, flag {flag})")
        self.assertFalse(
            phantoms,
            "%d/%d checks are keyed on a flag that EXISTS NOWHERE in the game (invented id -> the "
            "check can never fire, and fill can strand a progression item on it):\n%s"
            % (len(phantoms), total, "\n".join(phantoms[:40])))


if __name__ == "__main__":
    unittest.main(verbosity=2)
