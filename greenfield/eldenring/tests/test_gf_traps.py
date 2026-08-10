"""Trap items -- the pool contract, and the cross-repo STRING contract that has no gate of its own.

A trap is a SYNTHETIC item (features/traps.py: `ITEMS` and no `ITEM_GRANTS`), so the client
recognises it by NAME in the receive stream exactly as it already recognises `Boss Key: <Boss>`.
That is what keeps this off the contract and out of version lockstep -- and it means the item name
is a promise to another repository with nothing enforcing it.

🛑 THE FAILURE THIS FILE EXISTS FOR: rename `Trap: Rune Thief` and nothing breaks. No error, no
failed build, no red gate -- just an item that arrives, is classified filler, and does nothing at
all, forever. `er_logic::traps::Trap::from_item_name` carries the same two strings on the other side
with its own test. These cases pin ours; the two lists must move together.
"""
import os
import sys
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = find_repo_root(HERE)

# The strings the CLIENT matches on. Written out literally rather than imported from the feature:
# importing would make this test agree with any rename by construction, which is the one thing it
# must not do.
EXPECTED = {
    "rune_thief": "Trap: Rune Thief",
    "no_flask": "Trap: No Flask",
}


def _mod():
    from worlds.eldenring.features import traps
    return traps


class TrapCatalogue(unittest.TestCase):
    """Pure table checks -- no world, no fill."""

    def test_the_catalogue_is_exactly_the_two_implemented_traps(self):
        """🛑 Rule 4: adding a name later is safe, REMOVING one is a compat break. So this asserts
        equality, not containment -- a third name appearing here without a client that fires it is a
        yaml value that promises something the game will not do."""
        self.assertEqual(_mod().TRAPS, EXPECTED)

    def test_every_name_carries_the_prefix_the_client_dispatches_on(self):
        t = _mod()
        # WITNESS: an empty catalogue would satisfy the loop below vacuously.
        self.assertEqual(len(t.TRAPS), 2)
        for key, name in t.TRAPS.items():
            self.assertTrue(name.startswith(t.TRAP_PREFIX),
                            f"{key!r} -> {name!r} does not start with {t.TRAP_PREFIX!r}; the client "
                            f"dispatches on that prefix, so this trap could never fire")
            self.assertTrue(name.isascii(), f"{name!r} is not ASCII")

    def test_option_keys_are_the_catalogue_keys(self):
        """The yaml surface and the mint table are the same set, or a player can enable a trap that
        mints nothing (or the reverse: a trap mints with no way to ask for it)."""
        t = _mod()
        self.assertEqual(set(t.Traps.valid_keys), set(t.TRAPS))

    def test_traps_are_off_by_default(self):
        """`obviously traps are optional` -- Alaric, 2026-08-08. A default seed must be unchanged."""
        t = _mod()
        self.assertEqual(set(t.Traps.default), set())


@unittest.skipUnless(REPO is not None, REPO_ONLY_REASON)
class TrapItemsInTheWorld(unittest.TestCase):
    """The dealing rule, exercised through the feature's own entry point with a stub world.

    A stub rather than WorldTestBase because everything under test is a pure function of two option
    values; standing up a multiworld to check a round-robin would test AP, not us.
    """

    class _Opt:
        def __init__(self, value):
            self.value = value

    class _World:
        def __init__(self, chosen, count):
            class O:
                pass
            self.options = O()
            self.options.traps = TrapItemsInTheWorld._Opt(frozenset(chosen))
            self.options.trap_count = TrapItemsInTheWorld._Opt(count)

    def test_no_traps_named_mints_nothing_however_high_the_count(self):
        """The OptionSet is the master switch: a count with nothing enabled is inert, so a player
        who sets a count and forgets the set gets an unchanged seed rather than a silent surprise."""
        self.assertEqual(_mod().trap_items(self._World([], 40)), [])

    def test_zero_count_mints_nothing_however_many_are_named(self):
        self.assertEqual(_mod().trap_items(self._World(["rune_thief", "no_flask"], 0)), [])

    def test_the_split_is_even_and_reproducible(self):
        got = _mod().trap_items(self._World(["rune_thief", "no_flask"], 8))
        self.assertEqual(len(got), 8)
        self.assertEqual(got.count("Trap: Rune Thief"), 4)
        self.assertEqual(got.count("Trap: No Flask"), 4)
        # Reproducible: the same options must give the same list, or a seed is not rebuildable from
        # its yaml. An OptionSet is a frozenset and iterating one is not order-stable, which is the
        # trap this ordering rule exists to avoid.
        self.assertEqual(got, _mod().trap_items(self._World(["no_flask", "rune_thief"], 8)))

    def test_an_odd_count_does_not_lose_an_item(self):
        got = _mod().trap_items(self._World(["rune_thief", "no_flask"], 7))
        self.assertEqual(len(got), 7, "the round-robin dropped one")

    def test_one_trap_enabled_mints_only_that_one(self):
        got = _mod().trap_items(self._World(["no_flask"], 5))
        self.assertEqual(got, ["Trap: No Flask"] * 5)


if __name__ == "__main__":
    unittest.main()
