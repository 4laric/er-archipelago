"""`_class` and `_geography` answer DIFFERENT questions, and m61 is where they must disagree.

`datamine_boss_healthbars._class` answers "how should this boss's sweep be built?" and deliberately
calls the m61 DLC overworld `legacy`: the field pass builds its neighbourhood out of
`^m60_(\\d\\d)_(\\d\\d)$` tiles only, so an m61 boss classed `field` gets NO SWEEP AT ALL. Measured
2026-08-02 by making the change and regenerating: sweeps went 240 triggers / 3187 member links /
31 regions -> 212 / 3040 / 27. All 28 DLC overworld bosses lost their sweep; none gained one.

`_geography` answers "where does this boss stand?", where m61 IS field -- and that is what a player-
facing LOCATION TAG has to say. Tagging off `_class` labelled 15 DLC overworld boss checks
(Ghostflame Dragon, Dancer of Ranah, Rugalea, Romina...) as legacy-DUNGEON checks.

🛑 This file exists so nobody "simplifies" the two into one. Either direction is a real bug:
collapsing onto `_class` mislabels the DLC overworld; collapsing onto `_geography` deletes 28 sweeps.
They may only be unified by making the field pass MAP-AWARE (key the tile grid by (map, x, y) so a
neighbourhood can never span m60/m61) -- and then this test should be updated, not deleted.
"""
import importlib.util
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))


def _hb():
    p = os.path.join(REPO, "tools", "datamine_boss_healthbars.py")
    spec = importlib.util.spec_from_file_location("_hb_probe", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@unittest.skipUnless(_FOUND is not None, REPO_ONLY_REASON)
class ClassIsNotGeography(unittest.TestCase):
    def test_m61_is_legacy_for_sweeps_and_field_for_geography(self):
        hb = _hb()
        self.assertEqual(hb._class("m61_50"), "legacy",
                         "m61 must stay 'legacy' for SWEEP scoping or its 28 bosses lose their "
                         "sweeps entirely -- see the module docstring for the measurement")
        self.assertEqual(hb._geography("m61_50"), "field",
                         "m61 is the Land of Shadow OVERWORLD; a location tag calling it a legacy "
                         "dungeon is simply false")

    def test_m60_agrees_in_both(self):
        hb = _hb()
        self.assertEqual(hb._class("m60_49"), "field")
        self.assertEqual(hb._geography("m60_49"), "field")

    def test_geography_folds_the_minidungeon_classes(self):
        hb = _hb()
        for mp in ("m30_00", "m31_00", "m32_00", "m41_00"):
            self.assertEqual(hb._geography(mp), "underground", mp)
            self.assertIn(hb._class(mp), ("catacomb", "cave", "tunnel", "dungeon"), mp)

    def test_real_legacy_dungeons_agree(self):
        """The DLC's legacy dungeons (Belurat m20, Shadow Keep m21, Stone Coffin m22, Metyr m25,
        Midra m28) are genuinely legacy in BOTH -- m61 is the only prefix that differs."""
        hb = _hb()
        for mp in ("m10_00", "m20_00", "m21_00", "m22_00", "m25_00", "m28_00", "m35_00"):
            self.assertEqual(hb._class(mp), "legacy", mp)
            self.assertEqual(hb._geography(mp), "legacy", mp)

    def test_m61_is_the_only_prefix_where_they_differ(self):
        hb = _hb()
        prefixes = {v[0][:3] for v in _load_healthbars().values()}
        differ = sorted(p for p in prefixes
                        if (hb._class(p + "_00") == "field") != (hb._geography(p + "_00") == "field"))
        self.assertEqual(differ, ["m61"],
                         "another map prefix now disagrees between sweep-class and geography; "
                         "decide deliberately which is right for it")


def _load_healthbars():
    p = os.path.join(REPO, "greenfield", "eldenring", "boss_healthbars.py")
    g = {}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), g)
    return g["BOSS_HEALTHBARS"]


if __name__ == "__main__":
    unittest.main()
