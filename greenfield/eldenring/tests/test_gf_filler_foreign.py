"""filler_foreign_pct -- how much of this slot's filler is forced to stay home.

The option is live, `features/filler_foreign.py` is live, and `filler_foreign_localized` is a
contract key, so all of it needs a witness.

⚠️ REWRITTEN 2026-08-16 with the lever itself. These tests used to pin the NAME-uniform draw --
`len(localized) == len(names) * (100-pct) // 100` -- which is exactly the behaviour that made the
option a switch rather than a dial, and pinning it is part of why it survived. What they pin now is
the property the copy budget exists to deliver: monotone in copies, and NO CATEGORY EVER FULLY
BARRED (except at the explicit `pct: 0`).
"""
import collections

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from BaseClasses import ItemClassification as IC                        # noqa: E402
from worlds.eldenring.features.filler_foreign import (                  # noqa: E402
    FillerForeignFeature, FillerForeignPct, filler_names, FILLER_NAME, NO_CHANGE_PCT)
from worlds.eldenring.item_categories import (                          # noqa: E402
    FILLER as FILLER_CLASS, category_of, class_of)
from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS      # noqa: E402

GAME = "Elden Ring"


def _pre_reservation_filler_counts(world):
    """Reconstruct the filler pool filler_foreign saw before #582's pre-fill reservation."""
    items = [i for i in world.multiworld.itempool if i.player == world.player]
    items += [l.item for l in world.multiworld.get_locations(world.player)
              if getattr(l, "address", None) in MISSABLE_LOCATIONS
              and l.locked and l.item is not None and l.item.player == world.player]
    return collections.Counter(i.name for i in items if i.classification == IC.filler)


def test_filler_foreign_ships_at_the_measured_target():
    """🛑 THIS OPTION SHIPS NON-DEFAULT (70), and the number is measured, not chosen.

    It asserted `default == NO_CHANGE_PCT == 100` until 2026-08-16. 100 is still the no-op sentinel
    `_select` short-circuits on; it is no longer the default. 70 is where the export composition
    lands on Alaric's 1:1 useful:filler target WITH THE SHIPPED `keep_local` -- pooled over seeds,
    Hollow Knight 5 seeds 0.79:1 -> 1.00:1 and Bumper Stickers 3 seeds 0.77:1 -> 0.97:1.

    ⚠️ Only valid with the shipped keep_local: against `keep_local: []` the same sweep put 1:1 at
    pct 6-12. If either default moves, BOTH need re-measuring -- see the comment on the option."""
    assert FillerForeignPct.default == 70, (
        "the shipped filler_foreign_pct moved. It is a MEASURED value (1:1 export composition with "
        "the shipped keep_local); re-run the multiworld sweep before changing it, and change the "
        "comment on the option in the same commit.")
    assert NO_CHANGE_PCT == 100, "100 remains the no-op sentinel even though it is not the default"
    assert FillerForeignPct.range_start == 0 and FillerForeignPct.range_end == 100


def test_filler_names_always_include_rune():
    class _Stub:
        class options:
            item_shuffle = type("O", (), {"value": False})()
    assert filler_names(_Stub) == [FILLER_NAME], "shuffle off -> only the generic Rune filler exists"


def test_candidate_names_carry_no_useful_gear():
    """🛑 THE NIBBLE IS NOT THE CLASS. `filler_names` derived its set from the GOODS FullID nibble
    until 2026-08-16, and on 2026-08-12 `spells`, `spirit_ashes` and `crystal_tears` were promoted
    to USEFUL -- 341 of the 950 GOODS names -- so the candidate set had been holding back gear at
    the same rate as crafting mats. Ask the taxonomy, and assert it here so a future promotion
    cannot quietly put gear back."""
    class _Stub:
        class options:
            item_shuffle = type("O", (), {"value": True})()
    names = [n for n in filler_names(_Stub) if n != FILLER_NAME]
    assert names, "shuffle on -> the catalog contributes filler candidates"
    wrong = sorted(n for n in names if class_of(n) != FILLER_CLASS)
    assert not wrong, ("filler_foreign would localize %d non-FILLER item(s), e.g. %s -- it is "
                       "holding back gear" % (len(wrong), wrong[:5]))


class FillerForeignNoOp(WorldTestBase):
    game = GAME
    # The SENTINEL, no longer the default -- see test_filler_foreign_ships_at_the_measured_target.
    options = {"num_regions": 4, "item_shuffle": True, "filler_foreign_pct": 100}

    def test_the_sentinel_localizes_nothing(self):
        self.assertEqual(FillerForeignFeature().names_to_localize(self.world), [],
                         "pct 100 is the no-op sentinel and must localize nothing")


class FillerForeignShippedDefault(WorldTestBase):
    game = GAME
    options = {"num_regions": 4, "item_shuffle": True}   # no pct -> the shipped 70

    def test_the_shipped_default_actually_holds_something(self):
        """An option that ships non-default and does nothing is worse than one that ships inert."""
        held = FillerForeignFeature().names_to_localize(self.world)
        self.assertTrue(held, "the shipped default (70) must localize something")
        self.assertTrue(set(held).issubset(self.world.options.local_items.value),
                        "set_rules must have pushed the draw into local_items")


class FillerForeignAllLocal(WorldTestBase):
    game = GAME
    options = {"num_regions": 4, "item_shuffle": True, "filler_foreign_pct": 0}

    def test_zero_pct_takes_everything_including_last_names(self):
        """`pct: 0` is the ONE exemption from the per-category guarantee. The player asked for every
        scrap of filler to stay home; a safeguard that overrides an explicit request is a bug."""
        feat = FillerForeignFeature()
        localized = set(feat.names_to_localize(self.world))
        pool = set(_pre_reservation_filler_counts(self.world))
        self.assertTrue(pool, "no filler in the pool -- this test has lost its subject")
        self.assertEqual(localized, pool, "pct 0 forces every filler name in the pool local")
        self.assertTrue(pool.issubset(self.world.options.local_items.value),
                        "set_rules must have pushed them into local_items")


class FillerForeignPartial(WorldTestBase):
    game = GAME
    options = {"num_regions": 4, "item_shuffle": True, "filler_foreign_pct": 12}

    def _counts(self):
        return _pre_reservation_filler_counts(self.world)

    def test_it_spends_a_COPY_budget_not_a_name_budget(self):
        """The whole point. At pct 12 roughly 88% of COPIES go home -- while the NAME share is a
        different (and much larger) number, because the copy distribution is ~38:1 skewed."""
        counts = self._counts()
        held = set(FillerForeignFeature().names_to_localize(self.world))
        self.assertTrue(held, "pct 12 must localize something")
        copies_held = sum(counts[n] for n in held)
        total = sum(counts.values())
        share = copies_held / total
        self.assertGreater(share, 0.60,
                           "only %.0f%% of filler COPIES held at pct 12 -- the budget is not being "
                           "spent in copies (name-uniform regression?)" % (100 * share))
        self.assertLess(share, 1.0, "pct 12 is not pct 0; something must stay eligible")

    def test_no_category_is_ever_fully_barred(self):
        """🛑 THE PROPERTY THE STRATIFICATION EXISTS FOR. A single pool-wide draw at this share
        swept `merchant_bells` (11 names), `other` (2) and `crafting` (2) to zero free names --
        measured 2026-08-16. Nothing targeted them; they are just small. That is the whole-category
        bar `keep_local` is the explicit knob for, arriving in a seed where the player named
        nothing."""
        counts = self._counts()
        held = set(FillerForeignFeature().names_to_localize(self.world))
        free_by_cat = collections.Counter()
        total_by_cat = collections.Counter()
        for n in counts:
            total_by_cat[category_of(n)] += 1
            if n not in held:
                free_by_cat[category_of(n)] += 1
        self.assertGreater(len(total_by_cat), 3, "too few categories present to be a real test")
        barred = sorted(c for c in total_by_cat if free_by_cat[c] == 0)
        self.assertFalse(barred, "these categories have NO item left eligible to travel: %s" % barred)

    def test_the_draw_is_cached_so_slot_data_agrees_with_set_rules(self):
        """The draw consumes world.random. Recomputing it would move the seed AND report a different
        set than the one locality was actually applied to."""
        feat = FillerForeignFeature()
        a = feat.names_to_localize(self.world)
        b = feat.names_to_localize(self.world)
        self.assertEqual(a, b, "the draw is not cached -- two calls disagree")
        self.assertEqual(feat.slot_data(self.world)["filler_foreign_localized"], len(a))
        self.assertTrue(set(a).issubset(self.world.options.local_items.value))
