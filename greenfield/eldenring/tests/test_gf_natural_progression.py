"""natural_progression (Vanilla Progression) mode -- SPEC-vanilla-progression-20260722.md.

Subclasses WorldTestBase, so the generic suite runs for free against a real generated multiworld
(test_fill = every item places and the seed is BEATABLE; all_state/empty_state reachability). On top
of that we assert the mode's contract: ZERO synthetic region locks, real vanilla keys are the gates,
the entrance gates actually bind, and naturalKeyTriggers is emitted for the client.

importorskips when AP isn't importable (source-tree runs), like the other framework tests.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from BaseClasses import ItemClassification, CollectionState  # noqa: E402
from worlds.eldenring.features import natural_progression as _np  # noqa: E402
from ._util import world_items  # noqa: E402

GAME = "Elden Ring"


class NaturalProgressionTest(WorldTestBase):
    game = GAME
    # default accessibility (all locations reachable) -- the stronger guarantee: the whole real-key
    # DAG must be satisfiable with no stranded region. The cycle-breaker in the feature's set_rules is
    # what makes this hold even under accessibility:minimal.
    options = {"natural_progression": True, "enable_dlc": True}

    def _names(self):
        return [i.name for i in world_items(self)]

    # --- ZERO synthetic locks the PLAYER receives ------------------------------------
    # "<R> Lock" survives only as an internal AP EVENT (code=None), never as a receivable item, so a
    # real synthetic lock = a "<R> Lock" that is in the item pool or precollected (has a real code).
    def test_no_receivable_region_locks(self):
        p = self.player
        receivable = [i for i in self.multiworld.itempool if i.player == p]
        receivable += list(self.multiworld.precollected_items[p])
        locks = sorted({i.name for i in receivable if i.name.endswith(" Lock") and i.code is not None})
        self.assertEqual(locks, [], f"natural_progression must mint NO receivable '<Region> Lock'; got {locks}")

    def test_lock_tokens_are_events(self):
        # the "<R> Lock" identifiers that DO exist must all be events (code=None), placed + locked.
        p = self.player
        for i in world_items(self):
            if i.name.endswith(" Lock"):
                self.assertIsNone(i.code, f"{i.name} must be an EVENT (code=None), not a real item")

    # --- real vanilla keys are the progression gates ---------------------------------
    def test_real_keys_marked_progression(self):
        world = self.multiworld.worlds[self.player]
        keys = set(_np.key_items(world))
        self.assertIn("Rusty Key", keys)
        self.assertIn("Remembrance of the Grafted", keys)
        self.assertIn("Remembrance of the Blood Lord", keys)   # DLC entry chokepoint
        names = self._names()
        for k in ("Rusty Key", "Remembrance of the Grafted"):
            hits = [i for i in world_items(self) if i.name == k]
            self.assertTrue(hits, f"gate key {k!r} must be in the pool")
            self.assertTrue(all(i.classification & ItemClassification.progression for i in hits),
                            f"gate key {k!r} must be progression")

    # --- the entrance gates actually bind (test the predicate on a fresh state) -------
    def _gate_binds(self, region, key):
        """The 'To <region>' edge is False on an empty state and True once `key` is held."""
        p = self.player
        ent = self.multiworld.get_entrance(f"To {region}", p)
        empty = CollectionState(self.multiworld)
        key_item = next(i for i in self.multiworld.get_items() if i.name == key and i.player == p)
        with_key = CollectionState(self.multiworld)
        with_key.collect(key_item, prevent_sweep=True)
        return ent.access_rule(empty), ent.access_rule(with_key)

    def test_stormveil_gated_on_rusty_key(self):
        without, with_key = self._gate_binds("Stormveil", "Rusty Key")
        self.assertFalse(without, "Stormveil must be sealed with no Rusty Key")
        self.assertTrue(with_key, "Rusty Key must open Stormveil")

    def test_liurnia_gated_on_grafted_remembrance(self):
        without, with_key = self._gate_binds("Liurnia", "Remembrance of the Grafted")
        self.assertFalse(without, "Liurnia must be sealed with no Rem. of the Grafted")
        self.assertTrue(with_key, "Rem. of the Grafted must open Liurnia")

    # --- goal = reach the capital (2 Great Runes via leyndell_gate) -------------------
    def test_goal_is_reach_leyndell(self):
        p = self.player
        state = self.multiworld.get_all_state(False)
        self.assertTrue(self.multiworld.completion_condition[p](state),
                        "full state must satisfy the goal (reach Leyndell)")

    # --- client contract: naturalKeyTriggers emitted ---------------------------------
    def test_natural_key_triggers_emitted(self):
        sd = self.multiworld.worlds[self.player].fill_slot_data()
        self.assertIn("naturalKeyTriggers", sd, "naturalKeyTriggers must be in slot_data")
        trig = sd["naturalKeyTriggers"]
        self.assertIn("Stormveil Lock", trig, "Stormveil trigger keyed by its <Region> Lock identifier")
        clause = trig["Stormveil Lock"]["anyOf"]
        self.assertTrue(any("Rusty Key" in c["items"] for c in clause),
                        "Stormveil's trigger must reference Rusty Key")
