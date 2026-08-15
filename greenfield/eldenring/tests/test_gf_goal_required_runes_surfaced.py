"""#656 -- a great_runes seed requires SPECIFIC runes, and the NAMES must stay retrievable.

MOTIVATING CASE (CONTRIBUTING rule 11). AHHHREPTAR, v0.4.0, 2026-08-14, reported as "doesn't send a
victory to the server". He finished a `great_runes` seed at `goal_great_runes: 4` holding four Great
Runes, and nothing happened. `core._resolve_required_runes` picks a SPECIFIC set -- `sorted(avail)
[:want]`, an alphabetical prefix -- and the client's `goal.rs is_met` checks those NAMES, so four
runes that are not THOSE four complete nothing. He had to open the spoiler log to find out which
four his seed meant.

The docs half of that fix (this PR) makes four player-facing surfaces say "a specific set, not any
N" -- release/EldenRing.yaml, the player guide, README, release/KNOWN-ISSUES.md -- and points every
one of them at the SAME non-spoiler route to the names: the seed ships them in slot_data as
`great_rune_items`, and the client logs them verbatim at connect
("goal: N item(s) must be HELD, not merely their boss killed: ...").

WHAT THIS FILE IS FOR. That prose is only true while the route exists. A future change that
narrowed `great_rune_items` to a count, or dropped it, would leave four documents confidently
telling players to look for something that is no longer there -- and no existing test would notice,
because the goal would still WORK (AP's completion_condition is built from the same list in-process).
So this pins the SURFACE, not the mechanism:

  * the required rune NAMES are in slot_data, under `great_rune_items` -- names, not a count;
  * they are real Great Runes, exactly `goal_great_runes` of them, and the same list the world
    resolved;
  * the contract still declares a CLIENT READER for that key (it was once a "diagnostic -- no
    client read", which is how the original bug survived);
  * holding every Great Rune that is NOT required completes nothing -- the reported failure;
  * the set is `sorted(available)[:want]`. NOT an endorsement: #640 may reroll the selector. It is
    pinned because the shipped prose DESCRIBES this picker ("the alphabetically first N"), so if the
    picker moves, this fails and the prose gets rewritten with it instead of quietly going false.

`great_rune_items`, NOT `goalRequiredItems`. The latter is the kept Region LOCKS and is a provably
disjoint list (test_gf_goal_required_items.test_it_does_not_collide_with_great_rune_items); the
client folds both into one `item_goals`. A test that went looking for the runes in
`goalRequiredItems` would pass vacuously on the empty intersection and pin nothing.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring.core import GREAT_RUNES  # noqa: E402
from worlds.eldenring import contract as _contract  # noqa: E402
from ._util import world_items  # noqa: E402

GAME = "Elden Ring"

# The connect-time log line the yaml, the guide and KNOWN-ISSUES all tell the player to look for.
# Kept here as prose, not asserted against the client: the client is a different repo and this suite
# cannot see it. What IS asserted below is the datum that line is printed FROM.
CLIENT_LOG_LINE = "goal: N item(s) must be HELD, not merely their boss killed: ..."


class RequiredRunesAreNamedInSlotData(WorldTestBase):
    """A full-region great_runes seed at 2: the required PAIR is retrievable and is not "any 2"."""
    game = GAME
    options = {
        "num_regions": 0,
        "item_shuffle": True,
        "ending_condition": "great_runes",
        "goal_great_runes": 2,
    }

    def _world(self):
        return self.multiworld.worlds[self.player]

    def test_slot_data_carries_the_NAMES_not_just_a_count(self):
        """`great_rune_items` is the whole non-spoiler route -- it must be a list of rune names."""
        world = self._world()
        sd = world.fill_slot_data()
        names = sd.get("great_rune_items")
        self.assertIsInstance(names, list,
                              "great_rune_items must be a list -- it is the ONLY route a player has "
                              "to the required set outside the spoiler log (#656)")
        self.assertEqual(len(names), 2, "goal_great_runes: 2 must resolve to two named runes")
        for n in names:
            self.assertIsInstance(n, str)
            self.assertIn(n, GREAT_RUNES, "%r is not a Great Rune item name" % (n,))
        self.assertEqual(list(names), list(world._required_runes()),
                         "the emitted names must BE the requirement, not a parallel list")
        # A count alone would satisfy `great_runes_required`; the names are the thing that matters.
        self.assertEqual(sd["great_runes_required"], len(names))

    def test_the_contract_still_declares_a_client_reader(self):
        """The key was once 'diagnostic -- no client read'. That is how the original bug survived,
        and it is what the shipped prose now depends on NOT being true again."""
        key = [k for k in _contract.CONTRACT if k.name == "great_rune_items"]
        self.assertEqual(len(key), 1, "great_rune_items must still be a contract key")
        self.assertIn("goal.rs", key[0].consumer,
                      "great_rune_items must still be declared as CLIENT-READ: the yaml, the player "
                      "guide and KNOWN-ISSUES all tell the player to read the names off the client's "
                      "connect log (%s), which is only honest while the client parses this key"
                      % CLIENT_LOG_LINE)

    def test_the_required_pair_is_a_strict_subset_so_guessing_can_be_wrong(self):
        """The premise of the whole issue: more runes are obtainable than are required."""
        world = self._world()
        avail = world._available_runes()
        req = world._required_runes()
        self.assertGreater(len(avail), len(req),
                           "premise check -- if every reachable rune were required, 'a specific "
                           "set' and 'any N' would be the same thing and there would be nothing to "
                           "warn the player about")
        self.assertTrue(set(req) < set(avail))

    def test_holding_every_WRONG_rune_completes_nothing(self):
        """AHHHREPTAR's run, reproduced: a state holding every Great Rune EXCEPT the required ones
        -- strictly MORE runes than the goal asks for -- must not complete.

        The state is built by hand rather than taken from `get_all_state`, and that detail is the
        finding: `get_all_state` collects ADVANCEMENT items only, and a Great Rune this seed does
        not require is plain filler (`core._class_for` promotes the required ones and nothing else).
        So the all-items state holds EXACTLY the required pair and the wrong-runes case cannot be
        reached by subtraction -- the non-required runes have to be collected in explicitly. A test
        that only removed the required runes would assert "holding no Great Rune completes nothing",
        which is not what was reported."""
        world = self._world()
        req = set(world._required_runes())
        cond = self.multiworld.completion_condition[self.player]
        state = self.multiworld.get_all_state(False)
        self.assertTrue(cond(state), "control: the all-items state must complete")
        # Land of Shadow duplicates the runes, so every copy of a required one has to go.
        for victim in [i for i in world_items(self) if i.name in req]:
            state.remove(victim)
        # ...and every rune the seed did NOT name goes in.
        wrong = [i for i in world_items(self) if i.name in GREAT_RUNES and i.name not in req]
        for item in wrong:
            state.collect(item, prevent_sweep=True)
        held = {i.name for i in wrong}
        self.assertGreaterEqual(
            len(held), len(req),
            "premise check -- this state must hold at least as many Great Runes as the goal asks "
            "for, or it is not the reported case (held %s, goal wants %d)" % (sorted(held), len(req)))
        for name in req:
            self.assertFalse(state.has(name, self.player))
        self.assertFalse(cond(state),
                         "holding %d Great Runes, none of them the %d this seed named, must send no "
                         "victory -- this is the reported failure (#656), and it is why 'collect N "
                         "Great Runes' was a lie" % (len(held), len(req)))

    def test_the_set_is_the_alphabetical_prefix_the_docs_describe(self):
        """release/EldenRing.yaml, the player guide and KNOWN-ISSUES all say the set is currently
        'the alphabetically first N of the Great Runes your kept regions can reach'. If #640 rerolls
        the selector, this fails -- rewrite those three surfaces in the same commit."""
        world = self._world()
        self.assertEqual(list(world._required_runes()),
                         sorted(world._available_runes())[:2])
