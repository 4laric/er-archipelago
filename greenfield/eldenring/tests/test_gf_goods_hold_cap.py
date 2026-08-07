"""The item pool must not create goods copies the GAME cannot physically hold (#308).

THE MOTIVATING CASE, and it is the first test in this file (CONTRIBUTING rule 11).
Alaric's 2026-08-03 log, client `0.3.2 (59420f32f445)`:

    16:54:29 start-item backfill: 9/40 startItems absent -> attempting ["0x401ea99c" x9]
    16:54:29 start-item backfill: grant 0x401ea99c -> Placed
    16:54:29 start-item backfill: CONVERGED -- all 40 startItems present in bag
    16:54:30 [WARN] pot-cap: goods 0x401ea99c grant of 1 CAPPED to 0 (held 10, cap 10)
             -- the remainder is reported delivered but never enters the inventory.

Nine Hefty Cracked Pots attempted, ten already held against a ceiling of ten, zero arrived, and
every layer reported success.

WHY THE FIX IS HERE AND NOT IN THE CLIENT. `EquipParamGoods.maxNum` for the three EMEVD-tracked pot
rows EQUALS the held count that fires the mass phantom-check relief event (1460/1461/1462 ->
6902/6903/6904, `if (EventValue(..) != 20) RestartEvent()`), so the client's cap at `maxNum - 1` is
not a conservative choice -- it is the only reachable safe state. You cannot step over the threshold
(the game will not let you hold that many) and you cannot defer past it (`isDiscard=0`,
`isDeposit=0`, `maxRepositoryNum=0`: the held count only ever rises). No client change can deliver
these items; the generator must stop creating them.

WHAT THIS FILE GUARDS. Three things, in descending order of how quietly they would break:

 1. The clamp does not eat INTENTIONAL duplicates. Weapons/armour/talismans carry deliberate extra
    copies for pool quality (Alaric, 2026-08-04) -- and spells ARE goods (goodsType 5/16/18), so
    they are genuinely inside this filter's blast radius. They survive only because every spell row
    ships `maxNum` 99. That is measured here, not assumed.
 2. Consumables stay uncapped. Their stack drains, so a surplus copy is early, not lost.
 3. The start loadout is counted against the same ceiling. A clamp that looked only at the pool
    would leave the case above untouched -- the overflow came from the loadout.
"""
import os
import re
import unittest

try:
    from ._util import find_repo_root
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root

from ..item_ids import GOODS_HOLD_CAP, ITEM_CATALOG, LOCATION_ITEM
from ..hold_cap import hold_budget, hold_slot_available

_GOODS_NIBBLE = 0x40000000

# The start loadout's pot counts, from features/start_items.py. Duplicated here ON PURPOSE: if
# someone changes a loadout constant, this file should go red and make them look at the ceiling
# rather than silently re-open the overflow. test_start_loadout_constants_have_not_moved pins them.
_START = {"Cracked Pot": 10, "Ritual Pot": 4, "Perfume Bottle": 9, "Hefty Cracked Pot": 9}


def _start_items_src():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "features", "start_items.py"), encoding="utf-8") as fh:
        return fh.read()


def _pool_copies():
    """name -> copies an item_shuffle pool creates (one per location, as core.create_items does)."""
    out = {}
    for _ap, nm in LOCATION_ITEM.items():
        out[nm] = out.get(nm, 0) + 1
    return out


class TestTheMotivatingCase(unittest.TestCase):
    def test_the_four_pot_rows_are_capped_and_the_numbers_are_the_logged_ones(self):
        expect = {          # name: (ceiling, start, pool-before-clamp)
            # pool-before-clamp moved 2026-08-07 (#249, de-dup re-key): 17->18, 8, 7->8, 4->5.
            # These four are exactly the "common consumable, many sources" shape the old
            # ITEM-NAME filter was discarding, so they are where the placed rows land.
            "Cracked Pot": (19, 10, 18),
            "Ritual Pot": (9, 4, 8),
            "Perfume Bottle": (9, 9, 8),
            "Hefty Cracked Pot": (10, 9, 5),
        }
        pool = _pool_copies()
        for nm, (ceiling, start, copies) in expect.items():
            self.assertIn(nm, GOODS_HOLD_CAP, "%s lost its hold ceiling" % nm)
            self.assertEqual(GOODS_HOLD_CAP[nm], ceiling, nm)
            self.assertEqual(pool.get(nm, 0), copies, "%s pool copies moved" % nm)
            # The bug, stated as arithmetic: start + pool exceeds what the game will hold.
            self.assertGreater(start + copies, ceiling,
                               "%s no longer overflows -- if that is deliberate, update this "
                               "fixture; if it is not, the overflow moved somewhere else" % nm)

    def test_the_clamp_removes_exactly_the_undeliverable_surplus(self):
        pool = _pool_copies()
        budget = hold_budget(GOODS_HOLD_CAP, _START)
        clamped = {}
        for nm, copies in pool.items():
            for _ in range(copies):
                if nm in budget and not hold_slot_available(budget, nm):
                    clamped[nm] = clamped.get(nm, 0) + 1
                elif nm in budget:
                    budget[nm] -= 1
        # 2026-08-07 (#249): each rises by exactly the pool copies added above -- 8->9, 3, 7->8,
        # 3->4. The clamp is doing more work because the pool got bigger, not because a ceiling
        # or a start loadout moved (both pinned unchanged in this file).
        self.assertEqual(clamped.get("Cracked Pot"), 9)
        self.assertEqual(clamped.get("Ritual Pot"), 3)
        self.assertEqual(clamped.get("Perfume Bottle"), 8)
        self.assertEqual(clamped.get("Hefty Cracked Pot"), 4)

    def test_after_the_clamp_nothing_is_undeliverable(self):
        """The invariant the whole change exists for: start + surviving pool copies <= ceiling."""
        pool = _pool_copies()
        budget = hold_budget(GOODS_HOLD_CAP, _START)
        kept = {}
        for nm, copies in pool.items():
            for _ in range(copies):
                if nm not in budget:
                    continue
                if hold_slot_available(budget, nm):
                    budget[nm] -= 1
                    kept[nm] = kept.get(nm, 0) + 1
        over = {nm: (_START.get(nm, 0) + n, GOODS_HOLD_CAP[nm])
                for nm, n in kept.items() if _START.get(nm, 0) + n > GOODS_HOLD_CAP[nm]}
        self.assertEqual(over, {}, "still undeliverable after the clamp: %s" % over)


class TestTheClampDoesNotEatDeliberateDuplicates(unittest.TestCase):
    def test_no_weapon_armour_or_talisman_is_in_the_table(self):
        for nm in GOODS_HOLD_CAP:
            self.assertEqual(ITEM_CATALOG[nm] & 0xF0000000, _GOODS_NIBBLE,
                             "%s is not a goods item -- the clamp must never reach weapons, "
                             "armour or talismans, which carry intentional duplicates" % nm)

    def test_everything_the_clamp_actually_bites_is_pinned_here(self):
        """THE REVIEWED LIST. Every name whose pool copies exceed its ceiling -- i.e. everything
        this change removes from a default seed -- is enumerated, so a new entrant cannot arrive
        quietly.

        This matters most for SPELLS. Sorceries and incantations are goods (goodsType 5/16/18), so
        they sit inside this filter's blast radius and survive only because their rows ship
        `maxNum` 99. Nothing structural keeps them out. If a spell ever appears in this fixture the
        clamp is about to delete a duplicate somebody added on purpose (Alaric, 2026-08-04:
        weapons/armour/talismans/spells carry intentional duplicates for pool quality) -- so the
        right response is to look, not to re-baseline.

        An earlier version of this test asserted "nothing is ever clamped", which is the opposite
        of what the change does; it passed nothing and failed everything. A guard is a derivation
        too (CONTRIBUTING rule 8).
        """
        pool = _pool_copies()
        bites = {nm: (pool[nm], GOODS_HOLD_CAP[nm]) for nm in pool
                 if nm in GOODS_HOLD_CAP and pool[nm] > GOODS_HOLD_CAP[nm]}
        expected = {
            # unique-ish goods the pool duplicates past a maxNum of 1
            "Cerulean Crystal Tear": (2, 1), "Crimson Crystal Tear": (2, 1),
            "Ruptured Crystal Tear": (2, 1), "Cursemark of Death": (2, 1),
            "Dragon Cult Prayerbook": (2, 1), "Letter from Volcano Manor": (2, 1),
            "Lord of Blood's Favor": (2, 1), "Note: Flask of Wondrous Physick": (2, 1),
            "Note: Imp Shades": (2, 1), "Note: Stonedigger Trolls": (2, 1),
            "Unalloyed Gold Needle": (2, 1), "Whetstone Knife": (2, 1),
            "Memory Stone": (9, 8),
            # +1 (2026-08-07, #249 de-dup re-key). NOT a spell, so the stop-condition above does
            # not apply -- this is the same "unique-ish good the pool duplicates past a maxNum of
            # 1" shape as its neighbours here, and the clamp removing the surplus is correct: the
            # game will not hold two.
            #
            # The re-key off the ITEM NAME recovered a SECOND location carrying this item:
            #     Liurnia :: Rya's Necklace - from Blackguard        [f400300]   (already present)
            #     Sewer   :: Rya's Necklace - around Underground Roadside [f400081]  (recovered)
            # `_pool_copies` counts one copy per location, so pool copies went 1 -> 2 against a
            # ceiling of 1. Established by diffing LOCATION NAMES across the regen -- the same
            # regen renumbered the ap ids, so an id-level diff of this data says nothing.
            "Rya's Necklace": (2, 1),
        }
        # 🛑 NOT ONE OF THE FOUR POT ROWS IS IN THIS LIST, and that is the finding, not an
        # omission: every one of them is UNDER its ceiling on pool copies alone (17<=19, 8<=9,
        # 7<=9, 4<=10). They overflow only once the start loadout is added. A pool-only view of
        # this bug -- which is the obvious way to write it -- misses the exact case that was
        # reported. `TestTheMotivatingCase` covers them via hold_budget.
        for _pot in ("Cracked Pot", "Ritual Pot", "Perfume Bottle", "Hefty Cracked Pot"):
            self.assertNotIn(_pot, bites, _pot)
        self.assertEqual(bites, expected,
                         "the set of items the hold ceiling removes has changed -- if a SPELL is "
                         "in this diff, stop: that is a deliberate duplicate")

    def test_consumables_are_absent_by_derivation(self):
        """Golden Rune [1] ships 161 pool copies against maxNum 99 and must NOT be clamped: it is
        consumed, so the stack drains and the surplus is early rather than lost. Capping it would
        delete 62 real items from the pool to solve a problem it does not have."""
        for nm in ("Golden Rune [1]", "Starlight Shards", "Magic Grease", "Warming Stone"):
            if nm in ITEM_CATALOG:
                self.assertNotIn(nm, GOODS_HOLD_CAP, nm)


class TestTheDerivation(unittest.TestCase):
    def test_the_table_is_not_empty(self):
        """Rule 2: an empty result is a failure, not a clean run. An absent EquipParamGoods.csv
        makes GOODS_HOLD_CAP `{}`, which turns every test above into a vacuous pass."""
        self.assertGreater(len(GOODS_HOLD_CAP), 100, len(GOODS_HOLD_CAP))

    def test_the_three_emevd_rows_carry_the_minus_one_margin(self):
        """`maxNum` equals the relief-event threshold exactly, so these three -- and only these
        three -- are capped one below it. The Hefty Cracked Pot has no counter in the 589-file
        corpus and therefore sits at its plain maxNum."""
        self.assertEqual(GOODS_HOLD_CAP["Cracked Pot"], 19)      # maxNum 20, event 1460 != 20
        self.assertEqual(GOODS_HOLD_CAP["Ritual Pot"], 9)        # maxNum 10, event 1461 != 10
        self.assertEqual(GOODS_HOLD_CAP["Perfume Bottle"], 9)    # maxNum 10, event 1462 != 10
        self.assertEqual(GOODS_HOLD_CAP["Hefty Cracked Pot"], 10)  # maxNum 10, NO counter

    def test_absence_from_the_table_means_unbounded_not_zero(self):
        """The failure mode that would clamp the entire pool to nothing."""
        self.assertTrue(hold_slot_available({}, "Anything At All"))
        self.assertTrue(hold_slot_available({"Cracked Pot": 1}, "Nightrider Glaive"))
        self.assertFalse(hold_slot_available({"Cracked Pot": 0}, "Cracked Pot"))

    def test_a_loadout_already_over_the_ceiling_reports_negative_rather_than_zero(self):
        """A negative budget is a WORSE bug than a pool overflow (the loadout alone cannot be
        delivered), so it is preserved rather than flattened to 0 and hidden."""
        self.assertEqual(hold_budget({"X": 5}, {"X": 8})["X"], -3)

    def test_start_loadout_constants_have_not_moved(self):
        """`_START` above duplicates features/start_items.py on purpose -- this is the test that
        makes the duplication safe instead of a drift waiting to happen. Read as SOURCE, not
        imported: that module pulls in Archipelago, and this file is deliberately AP-free so the
        derivation stays checkable in the cheap tier."""
        src = _start_items_src()
        for const, nm in (("_START_CRACKED_POTS", "Cracked Pot"),
                          ("_START_RITUAL_POTS", "Ritual Pot"),
                          ("_START_PERFUME_BOTTLES", "Perfume Bottle"),
                          ("_START_HEFTY_CRACKED_POTS", "Hefty Cracked Pot")):
            m = re.search(r"^%s\s*=\s*(\d+)" % const, src, re.M)
            self.assertIsNotNone(m, "%s vanished from start_items.py" % const)
            self.assertEqual(int(m.group(1)), _START[nm],
                             "%s moved -- check it against GOODS_HOLD_CAP[%r] = %d before "
                             "updating this fixture" % (const, nm, GOODS_HOLD_CAP[nm]))

    def test_slot_data_and_the_hold_count_read_the_same_builder(self):
        """One builder, two consumers. Two copies of the option conditionals would drift silently,
        and a start loadout the clamp under-counts simply re-opens the bug."""
        src = _start_items_src()
        calls = src.count("plain_start_ids(world)") - src.count("def plain_start_ids(world)")
        self.assertEqual(calls, 2,
                         "both slot_data() and start_hold_counts() must build the list through "
                         "plain_start_ids, or what is GRANTED and what the clamp SUBTRACTS can "
                         "drift apart")


if __name__ == "__main__":
    unittest.main()
