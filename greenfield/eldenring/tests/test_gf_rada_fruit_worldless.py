"""#330's acceptance test: the worldless Rada Fruit rows are out of the pool, and the class is
DERIVED, not a hand list that calcifies.

THE MOTIVATING CASE (cokeman5, three times over: Nexus 2026-08-03, Discord 2026-08-15, #330
2026-08-18): *"My tracker is saying Shadowkeep is full of Rada fruit locations ... I haven't been
able to find any of these"* -- and later, the expensive form: *"I had heard a lot of the fake
locations had been fixed. Are these real?"* A player who believes checks are fake stops looking.

They were real param rows and mostly not real PICKUPS: vanilla expresses one "Rada Fruit xN" corpse
as N consecutive lots (own flag each), our datapackage sold every row as a location, and 52 more
rows reference no world object either datamine can find. Full mechanism: #330 (2026-08-19 comment).

This test RE-DERIVES the excluded class from the same committed inputs gen_data used and pins it,
so the tsv inputs shifting under the frozenset turns red here instead of silently changing what is
excluded. It also asserts the four proven singletons STAYED, because a fix that deletes the one row
a player verifiably hand-fired (f21007670) would be the overshoot #330 warned against.
"""
import csv
import os
import sys
import unittest
from collections import Counter, defaultdict

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

KEPT_M21_SINGLETONS = {21007200, 21007670, 21027000, 21027190}


def _derive_worldless(repo):
    gf = os.path.join(repo, "greenfield")
    rada = set()
    with open(os.path.join(gf, "flag_lots.tsv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("name") == "Rada Fruit":
                rada.add(row["flag"])
    coords = defaultdict(list)
    with open(os.path.join(gf, "item_grace_coords.tsv"), encoding="utf-8") as fh:
        for row in csv.DictReader([l for l in fh if l[:1] != "#"], delimiter="\t"):
            if row.get("kind") == "item":
                coords[row["key"]].append((row["map_id"], row["x"], row["y"], row["z"]))
    census = set()
    with open(os.path.join(gf, "msb_flag_region.tsv"), encoding="utf-8") as fh:
        for line in fh:
            if line[:1] != "#" and not line.startswith("flag\t"):
                census.add(line.split("\t", 1)[0])
    spot = Counter(c for fl in rada for c in coords.get(fl, ()))
    out = set()
    for fl in rada:
        cs = coords.get(fl)
        if not cs and fl not in census:
            out.add(int(fl))                                   # (a) worldless
        elif fl.startswith("21") and cs and any(spot[c] > 1 for c in cs):
            out.add(int(fl))                                   # (b) m21 bundle-stack row
    return out, {int(f) for f in rada}


class RadaFruitWorldless(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if REPO is None:
            raise unittest.SkipTest(REPO_ONLY_REASON)
        if REPO not in sys.path:
            sys.path.insert(0, REPO)
        cls.derived, cls.all_rada = _derive_worldless(REPO)
        from .. import data
        cls.flags = {int(flag) for rows in data.LOCATIONS.values() for (_n, _a, flag) in rows}
        cls.names = {int(flag): name for rows in data.LOCATIONS.values()
                     for (name, _a, flag) in rows}

    def test_the_derived_class_matches_gen_datas_frozenset(self):
        """The rule, not the list, is the fix -- an input shifting under the frozenset fails HERE."""
        sys.path.insert(0, os.path.join(REPO, "greenfield"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_rada_gd_src", os.path.join(REPO, "greenfield", "gen_data.py"))
        # gen_data executes a full regen on import; read the literal instead.
        src = open(os.path.join(REPO, "greenfield", "gen_data.py"), encoding="utf-8").read()
        import ast
        for node in ast.walk(ast.parse(src)):
            if (isinstance(node, ast.Assign) and node.targets
                    and getattr(node.targets[0], "id", "") == "_RADA_WORLDLESS"):
                literal = set(ast.literal_eval(node.value.args[0]))
                break
        else:
            self.fail("_RADA_WORLDLESS is gone from gen_data.py")
        self.assertEqual(literal, self.derived,
                         "gen_data._RADA_WORLDLESS no longer matches the rule derived from the "
                         "committed tsvs -- re-derive (only in: %r / only in rule: %r)"
                         % (sorted(literal - self.derived)[:5], sorted(self.derived - literal)[:5]))

    def test_the_worldless_rows_are_not_locations(self):
        # WITNESS (test_gf_vacuous_pass): both sides of the intersection below must be non-empty
        # sets, or "no worldless row is a location" is also what a broken derivation would say.
        self.assertTrue(self.derived, "WITNESS: the derivation produced nothing")
        self.assertTrue(self.flags, "WITNESS: data.LOCATIONS scanned as empty")
        self.assertEqual(len(self.derived), 124, "the derived class changed size -- say which rows "
                                                 "and which input moved before re-pinning")
        alive = sorted(self.derived & self.flags)
        self.assertEqual(alive, [], "worldless Rada rows still in the pool: %r" % alive[:8])

    def test_the_proven_pickups_stayed(self):
        """WITNESS + the overshoot guard: the fix must not delete what verifiably fires."""
        gone = sorted(KEPT_M21_SINGLETONS - self.flags)
        self.assertEqual(gone, [], "m21 coordinate-singleton Rada rows left the pool: %r" % gone)
        kept = sorted((self.all_rada - self.derived) & self.flags)
        self.assertGreater(len(kept), 50,
                           "almost no Rada rows survive -- the m20 corpus (MSB-attributed corpses "
                           "that fire by hand) should still be here")
        for fl in KEPT_M21_SINGLETONS:
            self.assertIn("Rada Fruit", self.names[fl])


if __name__ == "__main__":
    unittest.main(verbosity=2)
