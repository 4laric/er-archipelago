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
    surface_class_meta, class_containment, SURFACE_CLASS_FAMILIES, SURFACE_CLASS_LABELS,
)
from worlds.eldenring.location_tags import LOCATION_TAGS                # noqa: E402

# The TAGGED classes audited for v0.2. Still the whole tag half of the default surface.
#
# 🛑 `Remembrance` and `GreatRune` LEFT ON 2026-08-16 (#733) and the surface did not move: both are
# strict subsets of `MajorBoss`, so while that is present they admit nothing. They are still
# SELECTABLE -- only the default changed. The identity that makes this safe is asserted in
# test_gf_progression_surface_contract, by MEANING rather than by this name list, because a name list
# cannot tell a removal that changes the surface from one that does not.
V0_2_TAGGED_DEFAULT = {"KeyItem", "MajorBoss",
                       "Church", "Seedtree", "Fragment", "Revered", "ShopSlot"}
# ...plus the DERIVED half, added 2026-08-13 (#631). Kept as two names rather than one updated set
# because the split is the point: everything below that reasons about TAGS must use the tagged half,
# and it would silently measure nothing if SweepSlot were folded in.
V0_2_DEFAULT = V0_2_TAGGED_DEFAULT | {"SweepSlot"}


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
        # 🛑 AND THE NAME LIST IS NOT THE POINT. What must hold is that the shipped default admits
        # the same LOCATIONS the audited surface did; the two retired names are a subset of MajorBoss
        # and prove nothing by their presence or absence. Asserted here too so this file cannot be
        # "fixed" by editing the constant above (#733).
        from worlds.eldenring.features.progression_surface import allowed_ap_ids
        audited = set(allowed_ap_ids(LOCATION_TAGS, V0_2_DEFAULT | {"Remembrance", "GreatRune"}))
        shipped = set(allowed_ap_ids(LOCATION_TAGS, set(ProgressionSurface.default)))
        self.assertTrue(shipped, "the shipped default admits nothing -- this test measures nothing")
        self.assertEqual(shipped, audited,
                         "the shipped default no longer admits what the v0.2 audit approved")
        # The default moved on 2026-08-13 and this line is where that is legible. SweepSlot is not a
        # tag: it nominates one member of every enabled dungeon sweep, so a sweep can pay out
        # progression in a default seed. The reason is #631 -- at the default confine_foreign_
        # progression a slot was receiving 7 of the 60 foreign key items it should. Sibling
        # assertions live in test_gf_boss_sweeps.SweepSlotIsInTheDefaultSurface, including the one
        # that matters more: the SHIPPED TEMPLATE lists the classes explicitly, so the class default
        # alone would have reached nobody who generates from it.
        self.assertEqual(set(ProgressionSurface.default) - set(contract.SURFACE_DERIVED_CLASSES),
                         V0_2_TAGGED_DEFAULT,
                         "the TAGGED half of the default surface moved; that is a different and "
                         "much bigger change than adding a derived class")
        # 🛑 THIS IS A TAG COUNT, NOT A HOSTING COUNT, and the variable used to be called `hosts`
        # with a comment claiming "~193 locations" -- the exact conflation that also lived in the
        # ProgressionSurface docstring. This union applies NO bars (guessed region, missable,
        # erdtree-burn, surface-excluded, hub merchant) and not even contract.has_class's EniaShop
        # exclusion, so it is ~197. The number of checks that can actually HOST progression is 156.
        # Keep this as the cheap floor it is; the real figure is priced, per class, in
        # greenfield/surface_confidence.tsv and asserted against the live allowed_ap_ids in
        # test_gf_surface_confidence.py.
        tagged = {ap for ap, tags in LOCATION_TAGS.items() if V0_2_TAGGED_DEFAULT & set(tags)}
        self.assertGreater(len(tagged), 150,
                           "the default surface's TAG union collapsed (~197 expected); a real drop "
                           "here means classes stopped being derived, not that the surface shrank")

    def test_every_default_class_is_in_the_shared_vocabulary(self):
        for c in ProgressionSurface.default:
            self.assertIn(c, contract.SURFACE_CLASSES)
        self.assertTrue(set(ProgressionSurface.default) <= set(ProgressionSurface.valid_keys))

    # ---- determinism -----------------------------------------------------------------------------
    def test_order_is_canonical_not_set_iteration_order(self):
        """A set has no stable order across processes. The result must not depend on the container."""
        as_set = selected_surface({"ShopSlot", "MajorBoss", "Church"})
        as_list = selected_surface(["Church", "MajorBoss", "ShopSlot"])
        as_rev = selected_surface(["ShopSlot", "Church", "MajorBoss"])
        self.assertEqual(as_set, as_list)
        self.assertEqual(as_set, as_rev)
        vocab = [c for c in contract.SURFACE_CLASSES if c in {"ShopSlot", "MajorBoss", "Church"}]
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

    # ---- the wizard's per-key presentation -------------------------------------------------------
    # These keys are TAG NAMES, and several of them do not say what they select: `Church` is the 13
    # Sacred Tears (not "church locations"), `Basin` is Crystal Tears, `Seedtree` is Golden Seeds.
    # The wizard rendered them raw and alphabetical, so the grid both mis-described the classes and
    # scattered the four boss classes across it. The labels are the fix; the keys cannot move because
    # AP's VerifyKeys RAISES on an unknown key and every yaml in the wild would hard-fail.
    def test_every_vocabulary_class_has_a_label_and_a_family(self):
        """A gap here is INVISIBLE in the page: an unclaimed class is simply never drawn."""
        meta = surface_class_meta()
        self.assertEqual({m["key"] for m in meta}, set(contract.SURFACE_CLASSES),
                         "the grid must draw the vocabulary exactly")
        self.assertEqual(len(meta), len(contract.SURFACE_CLASSES), "a class is drawn twice")
        for m in meta:
            self.assertTrue(m["label"].strip(), "%s has no label" % m["key"])
            self.assertTrue(m["hint"].strip(), "%s has no hint" % m["key"])

    def test_a_class_with_no_label_or_family_RAISES_rather_than_vanishing(self):
        """The failure mode this guards is silence, so the helper must be loud.

        Passing a vocabulary the tables do not cover stands in for adding a 17th class and
        forgetting the presentation -- which would otherwise render as a bare tag name in a grid of
        labelled ones, or not render at all."""
        with self.assertRaises(ValueError):
            surface_class_meta(list(contract.SURFACE_CLASSES) + ["Underground"])

    def test_labels_do_not_silently_cover_a_retired_class(self):
        """The tables may not name classes the vocabulary no longer has -- that is a dead label
        nobody will notice, and it is how the 20 dead wizard lint rules happened."""
        named = set(SURFACE_CLASS_LABELS)
        for _fid, _lab, keys in SURFACE_CLASS_FAMILIES:
            named |= set(keys)
        self.assertEqual(named - set(contract.SURFACE_CLASSES), set(),
                         "presentation tables name classes outside the vocabulary")

    # ---- the containment lattice ----------------------------------------------------------------
    def test_containment_is_derived_and_matches_the_live_tags(self):
        """Recompute from LOCATION_TAGS independently. This is the relation contract.py carried as a
        COMMENT, inverted, for months -- so it is asserted from the data, in the direction that
        matters, rather than against a table that could be wrong the same way twice."""
        cont = class_containment()
        tagged = [c for c in contract.SURFACE_CLASSES if c not in contract.SURFACE_DERIVED_CLASSES]
        members = {c: {ap for ap, ts in LOCATION_TAGS.items() if c in (ts or ())}
                   for c in tagged}
        for parent, kids in cont.items():
            if parent not in members:
                continue
            for kid in kids:
                if kid not in members:
                    continue
                self.assertTrue(members[kid] < members[parent],
                                "%s does not strictly contain %s" % (parent, kid))
        # ...and nothing strictly contained is MISSING from the answer.
        for a in tagged:
            for b in tagged:
                if a != b and members[b] and members[b] < members[a]:
                    self.assertIn(b, cont.get(a, []),
                                  "%s contains %s but the lattice does not say so" % (a, b))

    def test_majorboss_contains_remembrance_and_greatrune_not_the_reverse(self):
        """🛑 THE CORRECTED DIRECTION, pinned. contract.py read "MajorBoss is a SUBSET of
        Remembrance/GreatRune". It is their SUPERSET, and the wizard now tells players so."""
        cont = class_containment()
        self.assertIn("Remembrance", cont.get("MajorBoss", []))
        self.assertIn("GreatRune", cont.get("MajorBoss", []))
        self.assertNotIn("MajorBoss", cont.get("Remembrance", []))
        self.assertNotIn("MajorBoss", cont.get("GreatRune", []))

    def test_the_shop_umbrella_contains_its_members(self):
        """`Shop` used to be tagged from the region_map `method` column while ShopNonSpell/ShopSlot
        were derived from the stock FLAG, so the umbrella was NARROWER than its members: 28
        ShopNonSpell checks and 3 ShopSlot pins carried no `Shop` tag. One predicate now
        (gen_data._is_shop_row), and this is the relation that proves it."""
        cont = class_containment()
        self.assertIn("ShopNonSpell", cont.get("Shop", []))
        self.assertIn("ShopSlot", cont.get("Shop", []))
        self.assertIn("ShopSlot", cont.get("ShopNonSpell", []))

    def test_containment_is_a_strict_order(self):
        cont = class_containment()
        for parent, kids in cont.items():
            self.assertNotIn(parent, kids, "%s contains itself" % parent)
            for kid in kids:
                self.assertNotIn(parent, cont.get(kid, []),
                                 "mutual containment %s <-> %s" % (parent, kid))

    def test_containment_takes_synthetic_tags_so_it_is_not_just_a_data_echo(self):
        tags = {1: ["Big", "Small"], 2: ["Big"], 3: ["Other"]}
        cont = class_containment(tags, ["Big", "Small", "Other"])
        self.assertEqual(cont, {"Big": ["Small"]})

    def test_wizard_key_meta_is_the_shape_the_page_reads(self):
        km = ProgressionSurface.wizard_key_meta()
        self.assertEqual({m["key"] for m in km["keys"]}, set(ProgressionSurface.valid_keys),
                         "the page must be able to draw every key AP will accept")
        fam_ids = {f["id"] for f in km["families"]}
        for m in km["keys"]:
            self.assertIn(m["family"], fam_ids, "%s sits in an undeclared family" % m["key"])
        self.assertTrue(km["contains"], "the containment lattice is empty -- the redundancy hint "
                                       "would never fire")

    # ---- the consequence, now FIXED rather than pinned ------------------------------------------
    def test_the_remembrance_greatrune_rung_is_skipped_rather_than_spent(self):
        """This replaces `test_the_remembrance_greatrune_ladder_rung_is_INERT_over_a_majorboss_base`,
        which pinned the defect and said in its own docstring: *"If it IS made, delete this test in
        the same commit and say so in the notes."* It is made (#733), and this is that.

        `_WIDEN_GROUPS` opens with `["Remembrance", "GreatRune"]` and both are strict SUBSETS of
        `MajorBoss`, so over a MajorBoss base that group admits zero locations. `build_ladder` used
        to skip a group only when every NAME in it was already accumulated, so it spent a whole
        STRICT retry standing still. It now measures what a rung ADMITS.

        🛑 The classes must still ACCUMULATE. Skipping the rung is not the same as dropping the
        classes: a later group combines with them, and on a base without MajorBoss they do real work
        (asserted below)."""
        from worlds.eldenring.features.progression_surface import allowed_ap_ids
        ladder = build_ladder({"MajorBoss"})
        sizes = [len(set(allowed_ap_ids(LOCATION_TAGS, set(r)))) for r in ladder]
        for i in range(1, len(sizes)):
            self.assertGreater(sizes[i], sizes[i - 1],
                               "rung %d (%s) admits nothing new" % (i, ladder[i]))
        self.assertIn("Remembrance", ladder[1],
                      "the classes must still be carried even though they earned no rung of their "
                      "own -- dropping them would change what LATER rungs admit")
        self.assertIn("KeyItem", ladder[1],
                      "the skipped group folds into the next one that does work")

    def test_the_two_still_widen_a_base_that_lacks_major_bosses(self):
        """The other side, and the reason they stay in `_WIDEN_GROUPS` at all. Containment is a fact
        about a PAIR of classes, not about a class: over a `{Church}` base, `+Remembrance,GreatRune`
        admits 31 locations it could not reach before. A fix that removed them from the widen order
        would have quietly cost that."""
        from worlds.eldenring.features.progression_surface import allowed_ap_ids
        ladder = build_ladder({"Church"})
        base = set(allowed_ap_ids(LOCATION_TAGS, set(ladder[0])))
        rung1 = set(allowed_ap_ids(LOCATION_TAGS, set(ladder[1])))
        self.assertIn("Remembrance", ladder[1])
        self.assertGreater(len(rung1), len(base),
                           "+Remembrance,GreatRune must still widen a base with no MajorBoss")

    def test_the_shipped_default_ladder_is_unchanged_by_733(self):
        """🛑 THE SAFETY PROPERTY. #733 took two classes out of the default and taught the ladder to
        measure admissions, and NEITHER may move the shipped ladder -- same number of rungs, same
        locations at each. If that ever stops holding, the default's fill sequence moved and every
        default seed is a different seed; that is a decision, not a side effect.

        🛑 ASSERTED AS AN IDENTITY AGAINST THE PRE-#733 SELECTION, NOT AS LITERAL SIZES. It shipped
        as `assertEqual(sizes, [176, 365, 433])` and that was wrong within the hour: #746 re-derived
        the MajorBoss roster from the game's own data, the base rung became 186, and a test about
        #733 went red over a change that had nothing to do with it. Worse, its own PR was green --
        CI runs on the branch HEAD, not on the merge, and #746 landed in between.

        The question is whether the two RETIRED classes change the ladder, so ask exactly that: build
        the ladder from the shipped default and from the shipped default plus the two, and require
        them to admit the same locations rung for rung. That survives any roster change and still
        fails the moment #733's premise stops being true."""
        from worlds.eldenring.features.progression_surface import allowed_ap_ids
        shipped = build_ladder(ProgressionSurface.default)
        pre733 = build_ladder(set(ProgressionSurface.default) | {"Remembrance", "GreatRune"})

        def sizes(ladder):
            return [len(set(allowed_ap_ids(LOCATION_TAGS, set(r)))) for r in ladder]

        got, want = sizes(shipped), sizes(pre733)
        self.assertTrue(got, "the shipped ladder is empty -- this test is measuring nothing")
        self.assertEqual(got, want,
                         "retiring Remembrance/GreatRune moved the shipped ladder: %s vs %s "
                         "(%s)" % (got, want, [sorted(r) for r in shipped]))
        # ...and it must still be a LADDER: every rung strictly wider than the last.
        for i in range(1, len(got)):
            self.assertGreater(got[i], got[i - 1],
                               "rung %d admits nothing new: %s" % (i, sorted(shipped[i])))

    def test_the_shipped_default_ladder_has_no_inert_rung(self):
        """The counterpart to the test above: every rung of the DEFAULT ladder must add locations.

        build_ladder skips a widen group with nothing new to add, which is what keeps the default's
        ladder honest. A regression that stopped skipping would waste ladder steps on seeds that are
        already struggling to place their locks."""
        from worlds.eldenring.features.progression_surface import allowed_ap_ids
        ladder = build_ladder(ProgressionSurface.default)
        sizes = [len(set(allowed_ap_ids(LOCATION_TAGS, set(r)))) for r in ladder]
        for i in range(1, len(sizes)):
            self.assertGreater(sizes[i], sizes[i - 1],
                               "default ladder rung %d (%s) adds no locations" % (i, ladder[i]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
