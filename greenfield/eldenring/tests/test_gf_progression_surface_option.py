"""progression_surface as a yaml OptionSet (v0.2): the one player-facing lever over WHICH locations
may hold progression.

It was frozen for v0.2 under "always-on in the playtest yaml -> now the behaviour". That was the wrong
reason: it was small (33 locations: MajorBoss/Remembrance/GreatRune) because the location DATA could not
be trusted, so it was held to what a human could hand-verify. The provenance work removed that
constraint, so it is exposed -- with the widened, ground-truth-audited default baked in.

What this guards:
  * the default is exactly the v0.2 surface, so a yaml that never mentions it generates as before;
  * DETERMINISM -- an OptionSet is a SET, and Python randomises string hashing per process, so the
    selection's order must come from the VOCABULARY, never from the set. (Same class of bug as
    regionSphereTargetRanges being emitted in set-iteration order.)
  * narrowing is SAFE: the feasibility ladder widens rather than failing, and an EMPTY surface turns
    confinement off instead of raising -- per the headline gate, any yaml gens clean or rejects
    gracefully, never a FillError.
"""
import importlib.util
import os
import unittest

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract                                    # noqa: E402
from worlds.eldenring.features.progression_surface import (             # noqa: E402
    ProgressionSurface, selected_surface, build_ladder,
)
from worlds.eldenring.location_tags import LOCATION_TAGS                # noqa: E402

V0_2_DEFAULT = {"KeyItem", "MajorBoss", "Remembrance", "GreatRune",
                "Church", "Seedtree", "Fragment", "Revered", "ShopSlot"}


class ProgressionSurfaceOption(unittest.TestCase):
    def test_it_is_a_yaml_option_now(self):
        from worlds.eldenring import core
        import dataclasses
        names = {f.name for f in dataclasses.fields(core.GFOptions)}
        self.assertIn("progression_surface", names,
                      "progression_surface must be yaml-settable (it is the WHICH-locations-hold-"
                      "progression lever); if it got re-frozen, that is a regression")

    def test_default_is_the_audited_v0_2_surface(self):
        self.assertEqual(set(ProgressionSurface.default), V0_2_DEFAULT)
        hosts = {ap for ap, tags in LOCATION_TAGS.items() if V0_2_DEFAULT & set(tags)}
        self.assertGreater(len(hosts), 150, "the default surface should host ~178 locations")

    def test_every_default_class_is_in_the_shared_vocabulary(self):
        for c in ProgressionSurface.default:
            self.assertIn(c, contract.IMPORTANT_LOCATION_TYPES)
        self.assertTrue(set(ProgressionSurface.default) <= set(ProgressionSurface.valid_keys))

    # ---- determinism -----------------------------------------------------------------------------
    def test_order_is_canonical_not_set_iteration_order(self):
        """A set has no stable order across processes. The result must not depend on the container."""
        as_set = selected_surface({"ShopSlot", "MajorBoss", "Church"})
        as_list = selected_surface(["Church", "MajorBoss", "ShopSlot"])
        as_rev = selected_surface(["ShopSlot", "Church", "MajorBoss"])
        self.assertEqual(as_set, as_list)
        self.assertEqual(as_set, as_rev)
        vocab = [c for c in contract.IMPORTANT_LOCATION_TYPES if c in {"ShopSlot", "MajorBoss", "Church"}]
        self.assertEqual(as_set, vocab, "order must come from the vocabulary")

    def test_the_ladder_is_deterministic_for_a_set_input(self):
        a = build_ladder({"MajorBoss", "Church"})
        b = build_ladder({"Church", "MajorBoss"})
        self.assertEqual(a, b, "the feasibility ladder must not vary with set iteration order")

    # ---- narrowing is safe -----------------------------------------------------------------------
    def test_empty_surface_turns_confinement_off_rather_than_raising(self):
        self.assertEqual(selected_surface(set()), [])
        self.assertEqual(build_ladder(set()), [],
                         "an empty surface is a NO-OP (progression scatters), never a FillError")

    def test_a_tiny_surface_widens_via_the_ladder(self):
        ladder = build_ladder({"KeyItem"})
        self.assertTrue(ladder, "a 9-location surface must produce a ladder, not nothing")
        self.assertEqual(ladder[0], ["KeyItem"], "rung 0 is the player's own choice")
        self.assertGreater(len(ladder[-1]), 1, "the ladder must widen when the base cannot host")
        for i in range(1, len(ladder)):
            self.assertTrue(set(ladder[i - 1]) <= set(ladder[i]), "each rung only ADDS classes")

    def test_garbage_classes_are_filtered_not_fatal(self):
        self.assertEqual(selected_surface({"NotATag", "MajorBoss"}), ["MajorBoss"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
