"""Boss-taxonomy gate: `boss_taxonomy.py` must classify every boss we know, once.

`tools/gen_boss_taxonomy.py` turns `BOSS_HEALTHBARS` + `MAJOR_SWEEP_TRIGGERS` + `map_names.tsv` +
the evergaol EMEVD family into one CLASS per boss. This oracle re-derives the parts it can from
the OTHER tables rather than re-running the generator, so a generator bug cannot hide behind
shared code:

  * COVERAGE     every healthbar defeat flag and the eight MSB furnace encounters are classified.
  * VOCABULARY   every emitted class is declared in BOSS_CLASSES, and the counts match the rows.
  * LADDER       remembrance_main is exactly MAJOR_SWEEP_TRIGGERS ∩ the healthbar roster; the
                 evergaol class is exactly EVERGAOL_TRIGGERS minus the majors that outrank it.
  * GEOGRAPHY    site_class agrees with the boss's map prefix, and each non-overworld boss_class
                 either IS its site_class or is one of the four ladder rungs that outrank it.
  * GAPS STAY VISIBLE  a class in UNDERIVED_CLASSES must be EMPTY and must carry a reason. If
                 someone derives furnace golems, this test tells them to drop the entry -- an
                 allowlist that outlives its cause is the failure mode AGENTS.md keeps naming.

Run:  python greenfield/eldenring/tests/test_gf_boss_taxonomy.py
"""
import importlib.util
import os
import unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GF_PKG = os.path.dirname(HERE)


def _load(name):
    path = os.path.join(GF_PKG, "tables", name + ".py")
    if not os.path.isfile(path):
        path = os.path.join(GF_PKG, name + ".py")
    spec = importlib.util.spec_from_file_location("_taxonomy_test_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TAX = _load("boss_taxonomy")
HB = _load("boss_healthbars").BOSS_HEALTHBARS
SWEEPS = _load("boss_sweeps")
# Death flags from the eight common-event 90005301 calls, not reward flags.
FURNACE_DEATH_FLAGS = {2045460200, 2050460300, 2050460310, 2046390200,
                       2046420300, 2048400200, 2248460291, 2251450280}

# Map prefix -> the site class it must produce. Deliberately a SECOND copy of the generator's
# table: if the two disagree, one of them was edited without the other being looked at, which is
# exactly what a gate is for.
EXPECTED_SITE = {
    "m30": "catacomb", "m31": "cave", "m32": "tunnel", "m40": "catacomb",
    "m41": "gaol", "m42": "tunnel", "m43": "cave", "m60": "overworld", "m61": "overworld",
}
# Classes that OUTRANK a boss's geography on the generator's ladder.
LADDER_OVERRIDES = frozenset({"remembrance_main", "dragon", "furnace_golem", "evergaol"})
# The one site class m30 may produce that is not EXPECTED_SITE["m30"] (hero's graves, split out of
# the catacomb prefix by map_names.tsv).
M30_SPLIT = "heros_grave"


class TestBossTaxonomy(unittest.TestCase):
    def test_covers_exactly_the_healthbar_roster(self):
        self.assertEqual(
            set(TAX.BOSS_TAXONOMY), set(HB) | FURNACE_DEATH_FLAGS,
            "boss_taxonomy must classify every DisplayBossHealthBar boss and no other flag; "
            "regenerate with python tools/gen_boss_taxonomy.py",
        )
        self.assertGreater(len(TAX.BOSS_TAXONOMY), 200)

    def test_furnaces_use_death_flags_and_have_regions(self):
        self.assertEqual({f for f, r in TAX.BOSS_TAXONOMY.items() if r[0] == "furnace_golem"}, FURNACE_DEATH_FLAGS)
        self.assertNotIn("furnace_golem", TAX.UNDERIVED_CLASSES)
        for flag in FURNACE_DEATH_FLAGS:
            row = TAX.BOSS_TAXONOMY[flag]
            self.assertEqual(row[1], "overworld")
            self.assertTrue(row[3])
            self.assertEqual(row[4], "Furnace Golem")

    def test_classes_are_declared_and_counts_agree(self):
        counted = Counter(v[0] for v in TAX.BOSS_TAXONOMY.values())
        unknown = set(counted) - set(TAX.BOSS_CLASSES)
        self.assertFalse(unknown, "undeclared boss class(es): %s" % sorted(unknown))
        for cls in TAX.BOSS_CLASSES:
            self.assertEqual(
                counted.get(cls, 0), TAX.BOSS_CLASS_COUNTS[cls],
                "BOSS_CLASS_COUNTS[%r] disagrees with the rows -- the table was hand-edited" % cls,
            )
        self.assertEqual(sum(TAX.BOSS_CLASS_COUNTS.values()), len(TAX.BOSS_TAXONOMY))

    def test_names_and_maps_come_from_the_healthbar_table(self):
        for flag, (_cls, _site, map_id, _region, name) in TAX.BOSS_TAXONOMY.items():
            if flag in FURNACE_DEATH_FLAGS:
                continue
            self.assertEqual(map_id, HB[flag][0], "map drifted for flag %d" % flag)
            self.assertEqual(name, HB[flag][3], "name drifted for flag %d" % flag)

    def test_remembrance_main_is_the_adjudicated_major_roster(self):
        ours = {f for f, v in TAX.BOSS_TAXONOMY.items() if v[0] == "remembrance_main"}
        self.assertEqual(
            ours, set(SWEEPS.MAJOR_SWEEP_TRIGGERS) & set(HB),
            "the remembrance/main class must BE boss_sweeps.MAJOR_SWEEP_TRIGGERS restricted to the "
            "healthbar roster -- it is the adjudicated roster (#734), not a second opinion on it",
        )

    def test_evergaols_are_the_emevd_family_minus_higher_rungs(self):
        self.assertGreaterEqual(len(TAX.EVERGAOL_TRIGGERS), 8)
        tagged = {f for f, v in TAX.BOSS_TAXONOMY.items() if v[0] == "evergaol"}
        self.assertTrue(tagged <= set(TAX.EVERGAOL_TRIGGERS))
        for flag in TAX.EVERGAOL_TRIGGERS:
            if flag in TAX.BOSS_TAXONOMY and flag not in tagged:
                self.assertIn(
                    TAX.BOSS_TAXONOMY[flag][0], LADDER_OVERRIDES,
                    "flag %d is sealed by the evergaol event family but was classified %r, which "
                    "does not outrank evergaol on the ladder" % (flag, TAX.BOSS_TAXONOMY[flag][0]),
                )
            # A trigger the healthbar table does not know is not an error here; it would already
            # have failed test_covers_exactly_the_healthbar_roster if it were ours to classify.

    def test_site_class_follows_the_map_prefix(self):
        for flag, (_cls, site, map_id, _region, name) in TAX.BOSS_TAXONOMY.items():
            prefix = map_id.split("_", 1)[0]
            expected = EXPECTED_SITE.get(prefix)
            if expected is None:
                self.assertEqual(
                    site, "legacy",
                    "flag %d (%s, %s) is on an interior prefix, so its site class must be "
                    "'legacy'; add the prefix to EXPECTED_SITE if a new family shipped"
                    % (flag, map_id, name),
                )
            elif prefix == "m30":
                self.assertIn(site, (expected, M30_SPLIT))
            else:
                self.assertEqual(site, expected, "flag %d (%s) site class" % (flag, map_id))

    def test_boss_class_is_its_site_class_unless_a_higher_rung_claimed_it(self):
        for flag, (cls, site, map_id, _region, _name) in TAX.BOSS_TAXONOMY.items():
            if cls in LADDER_OVERRIDES:
                continue
            expected = {"overworld": "overworld_field", "legacy": "legacy_dungeon"}.get(site, site)
            self.assertEqual(cls, expected, "flag %d (%s) class vs site" % (flag, map_id))

    def test_underived_classes_are_declared_empty_and_explained(self):
        for cls, reason in TAX.UNDERIVED_CLASSES.items():
            self.assertIn(cls, TAX.BOSS_CLASSES, "%r is not a declared class" % cls)
            self.assertEqual(
                TAX.BOSS_CLASS_COUNTS[cls], 0,
                "%r now has members -- DROP it from UNDERIVED_CLASSES in "
                "tools/gen_boss_taxonomy.py. A gap note that outlived its gap is a lie the next "
                "reader has to disprove." % cls,
            )
            self.assertGreater(len(reason), 40, "%r needs a real reason, not a label" % cls)

    def test_arena_regions_agree_with_the_sweep_table(self):
        for flag, (_cls, _site, _map_id, region, _name) in TAX.BOSS_TAXONOMY.items():
            if flag in FURNACE_DEATH_FLAGS:
                continue
            expected = SWEEPS.SWEEP_ARENA_REGION.get(flag, "")
            self.assertEqual(region, expected, "arena region drifted for flag %d" % flag)


if __name__ == "__main__":
    unittest.main()
