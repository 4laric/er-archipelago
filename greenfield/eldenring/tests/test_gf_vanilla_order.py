"""`num_regions_order: vanilla_order` -- the restored SPINE-order draw, and the alias that keeps
old yamls generating.

er-archipelago, 2026-08-11. This option has been a selection mode, then deprecated scenery, then a
selection mode again under a new name, and each transition had a way to go wrong silently:

  * a rename that DROPS the old value is not a warning, it is a hard generation failure -- AP's
    `Choice.from_text` RAISES `Could not find option "spine"`, so every yaml in the wild stops
    working. `alias_spine` is what prevents that, and an alias is invisible until someone uses it.
  * the DEFAULT is the thing nobody names and therefore nobody notices. `vanilla_order` keeps a
    fixed eight regions at num_regions=6; if it ever became the default, every seed that does not
    mention the option would quietly lose nine base regions. Same shape as the FROZEN_OPTIONS
    default rot that shipped in v0.2.16 -- pin the default, not the template.
  * "restored verbatim" is a claim about BEHAVIOUR. `test_vanilla_order_is_the_spine_prefix` is what
    makes it one.
"""
import random
import unittest

import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.region_spine import (SPINE, REGIONS, DLC_REGIONS,  # noqa: E402
                                           compute_kept, base_regions)

# 🛑 SPINE ORDER, NOT `REGIONS` ORDER. `base_regions()` walks REGIONS, which is a DIFFERENT order --
# its last five are not the late spine, and an earlier draft of this file asserted against them and
# failed on Weeping/Stormveil, regions vanilla_order keeps FIRST. The late spine is the tail of
# SPINE with the DLC removed.
_LATE_BASE_SPINE = [r for r in SPINE if r not in DLC_REGIONS][-5:]
from worlds.eldenring.core import NumRegionsOrder  # noqa: E402


class TestTheOptionSurface(unittest.TestCase):
    def test_the_default_is_rolled(self):
        # 🛑 THE WHOLE POINT OF THE RESTORE IS THAT IT IS OPT-IN. If this ever flips, every seed
        # that does not name the option keeps the same eight regions forever and nine base regions
        # become unreachable -- silently, because nothing else in the suite asserts identity.
        self.assertEqual(NumRegionsOrder.default, NumRegionsOrder.option_rolled)
        self.assertEqual(NumRegionsOrder(NumRegionsOrder.default).current_key, "rolled")

    def test_spine_still_resolves_and_is_not_a_second_name(self):
        self.assertEqual(NumRegionsOrder.from_text("spine").value,
                         NumRegionsOrder.option_vanilla_order)
        self.assertEqual(NumRegionsOrder.from_text("spine").current_key, "vanilla_order",
                         "an old yaml must GENERATE, and must then describe itself by the new name")
        # An alias lives outside name_lookup on purpose (AP Options.py). If `spine` appeared here it
        # would be a rival display name and which one the wizard/spoiler shows would be an accident.
        self.assertEqual(sorted(NumRegionsOrder.name_lookup.values()), ["rolled", "vanilla_order"])

    def test_an_unknown_value_still_raises(self):
        # WITNESS for the test above: proves from_text is strict, so "spine resolves" is a fact
        # about the alias and not about from_text being lenient with anything it is handed.
        with self.assertRaises(KeyError):
            NumRegionsOrder.from_text("limgrave_start")


class TestTheDraw(unittest.TestCase):
    """`compute_kept` directly -- no AP world, so these are cheap and run every time."""

    def kept(self, n, order, seed=1, **kw):
        return compute_kept(n, random.Random(seed), order=order, **kw)

    def test_vanilla_order_is_the_spine_prefix(self):
        # THE RESTORE, ASSERTED. Not "looks early-game" -- the literal first N of SPINE.
        for n in (1, 3, 6, 9):
            got = self.kept(n, "vanilla_order")
            self.assertEqual(got[:n], SPINE[:n],
                             "n=%d kept %r, expected the SPINE prefix %r" % (n, got[:n], SPINE[:n]))
        self.assertEqual(self.kept(1, "vanilla_order")[0], "Limgrave")

    def test_vanilla_order_ignores_the_rng_entirely(self):
        # Determinism is the feature being bought. Four different streams, one answer.
        answers = {tuple(self.kept(6, "vanilla_order", seed=s)) for s in (0, 1, 7, 99999)}
        self.assertEqual(len(answers), 1, "vanilla_order varied with the rng seed: %r" % (answers,))

    def test_rolled_still_varies_and_reaches_the_late_spine(self):
        # WITNESS + the contrast case. If `rolled` had accidentally been wired to the new branch,
        # every assertion above would still pass and only this one would notice.
        seen = set()
        for s in range(200):
            seen.update(self.kept(6, "rolled", seed=s))
        self.assertGreater(len(seen), 12, "rolled only ever reached %d regions" % len(seen))
        late = set(_LATE_BASE_SPINE)
        self.assertTrue(seen & late,
                        "rolled never reached the late base spine %r -- it is not drawing at "
                        "random" % sorted(late))
        # ...and the thing rolled is FOR: vanilla_order can never do this.
        vseen = set()
        for s in range(200):
            vseen.update(self.kept(6, "vanilla_order", seed=s))
        self.assertFalse(vseen & late,
                         "vanilla_order reached a late region at n=6; the prefix is not a prefix")

    def test_the_full_pool_branch_ignores_order(self):
        # n<=0 and n>=len(pool) mean "keep the whole eligible map" -- an ORDER cannot change a set.
        for n in (0, -1, len(REGIONS), len(REGIONS) + 5):
            self.assertEqual(sorted(self.kept(n, "vanilla_order")), sorted(self.kept(n, "rolled")),
                             "n=%d disagreed between the two orders" % n)

    def test_an_unknown_order_falls_back_to_rolled(self):
        # `order` arrives from `current_key`, so it can only be one of the two today -- but the
        # branch is an `if/else`, and this pins which side an unexpected string lands on. Rolled is
        # the safe one: a seed with variety, never a seed silently narrowed to eight regions.
        self.assertEqual(self.kept(6, "nonsense", seed=42), self.kept(6, "rolled", seed=42))

    def test_eligibility_and_the_bar_are_honoured_on_the_new_path(self):
        # Both filters exist to stop a region entering the seed; a second draw path is a second
        # place they can be forgotten. Limgrave is SPINE[0], so barring it is the sharpest probe.
        pool = [r for r in base_regions() if r != "Weeping"]
        got = self.kept(4, "vanilla_order", eligible=pool)
        self.assertNotIn("Weeping", got, "vanilla_order drew from outside `eligible`")
        barred = self.kept(4, "vanilla_order", eligible=pool, bar_from_draw=("Limgrave",))
        self.assertNotIn("Limgrave", barred, "vanilla_order ignored `bar_from_draw`")
        self.assertTrue(barred, "the bar emptied the draw instead of shortening it")


if __name__ == "__main__":
    unittest.main()
