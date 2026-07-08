"""Focused unit test for the legible-key mapping layer (features/legible_keys.py).

Pure -- no Archipelago import. Validates:
  * every mapping key joins the exact ``_boss_label`` token boss_locks emits (re-derived here
    from boss_data.REGION_BOSSES so a data regen that renames a boss trips this test);
  * the resolver returns the vanilla name where mapped and the synthetic name elsewhere;
  * the synthetic <-> display inverse is consistent.
"""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.dirname(_HERE)                            # .../greenfield/eldenring_gf


def _load_by_path(name, relpath):
    """importlib-load a module by file path (same pattern as test_gf_data.py) so the AP-heavy
    package __init__ is never triggered -- keeps this in the data-invariant gate."""
    path = os.path.join(_PKG, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lk = _load_by_path("gf_legible_keys_under_test", os.path.join("features", "legible_keys.py"))


def _boss_label(reward):
    """Verbatim copy of boss_locks._boss_label (kept AP-free so this stays a data-invariant test).
    If boss_locks._boss_label ever changes shape, this copy must change with it -- that is the
    intended coupling: the mapping keys are only useful if they equal what boss_locks mints."""
    s = reward.strip()
    for pre in ("Remembrance of the ", "Remembrance of "):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    for suf in ("'s Great Rune", " Great Rune"):
        if s.endswith(suf):
            s = s[:-len(suf)]
            break
    return s.strip()


def _all_boss_labels():
    boss_data = _load_by_path("gf_boss_data_under_test", "boss_data.py")
    labels = set()
    for lst in boss_data.REGION_BOSSES.values():
        for (_aid, _fl, reward) in lst:
            labels.add(_boss_label(reward))
    return labels


class TestLegibleKeys(unittest.TestCase):
    def test_every_mapping_key_joins_a_real_boss_label(self):
        labels = _all_boss_labels()
        self.assertTrue(labels, "boss_data.REGION_BOSSES yielded no labels")
        missing = [k for k in lk.CAPSTONE_VANILLA_KEYS if k not in labels]
        self.assertEqual(missing, [], "mapping keys that do not match any _boss_label: %r" % missing)

    def test_expected_capstones_present(self):
        # The capstones the spec (SPEC-region-capstone-model 3/3a/4) gives a vanilla key.
        expected = {
            "Full Moon Queen": "Academy Glintstone Key",
            "Omen King": "Two Great Runes",
            "Radahn": "Dectus Medallion",
            "Malenia": "Haligtree Secret Medallion",
            "Rykard": "Drawing-Room Key",
            "Mohg": "Pureblood Knight's Medal",
            "Naturalborn": "Fingerslayer Blade",
            "Black Blade": "Deathroot",
            "a God and a Lord": "Messmer's Kindling",
            "Fire Giant": "Haligtree Secret Medallion (Right)",  # Mountaintops via Castle Sol (spec section 4)
        }
        self.assertEqual(lk.CAPSTONE_VANILLA_KEYS, expected)

    def test_mapped_boss_resolves_to_vanilla_name(self):
        self.assertEqual(lk.display_key_name("Full Moon Queen"), "Academy Glintstone Key")
        self.assertEqual(lk.display_key_name("a God and a Lord"), "Messmer's Kindling")
        self.assertTrue(lk.has_vanilla_key("Malenia"))

    def test_unmapped_boss_keeps_synthetic_name(self):
        # Bosses with no vanilla key must fall back to the synthetic Boss Key name.
        for label in ("Grafted", "Dancing Lion", "Impaler", "Twin Moon Knight"):
            self.assertFalse(lk.has_vanilla_key(label))
            self.assertEqual(lk.display_key_name(label), "Boss Key: " + label)

    def test_synthetic_inverse_is_consistent(self):
        # display_for_synthetic("Boss Key: X") == display_key_name("X") for every real label.
        for label in _all_boss_labels():
            syn = lk.synthetic_key_name(label)
            self.assertEqual(syn, "Boss Key: " + label)
            self.assertEqual(lk.display_for_synthetic(syn), lk.display_key_name(label))
        # Non-synthetic strings pass through untouched.
        self.assertEqual(lk.display_for_synthetic("Rune Arc"), "Rune Arc")


if __name__ == "__main__":
    unittest.main()
