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
    options = {"num_regions": 0, "natural_progression": True, "enable_dlc": True}

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

    # --- BORN-SOFTLOCK GUARD (2026-07-24) --------------------------------------------
    def test_every_sealed_region_has_an_opener(self):
        """core.py seals EVERY in-play region with an areaLock + open flag. A region that has an open
        flag but NO naturalKeyTrigger is sealed with nothing to bloom it -> the client never opens it:
        the start spoke (Limgrave) sealed = unplayable from turn one, and a count-gate (Caelid) or the
        capital (Leyndell) sealed forever is a logic/client soft-lock (AP logic can place goal
        progression there, the player can never reach it). So every KEPT region that HAS an open flag
        must carry a trigger -- INCLUDING the capital pair since the count primitive landed
        (2026-07-24): Leyndell/Sewer bloom on the Nth Great Rune, exactly when the vanilla wall opens
        (the 2026-07-24 playtest showed the areaLock seal does NOT open on the game's own wall). This
        is the guard that would have caught the first playtest's born-softlocked Limgrave."""
        from worlds.eldenring.region_open_flags import REGION_OPEN_FLAGS
        world = self.multiworld.worlds[self.player]
        trig = world.fill_slot_data().get("naturalKeyTriggers", {})
        sealed_no_opener = [r for r in world._kept()
                            if REGION_OPEN_FLAGS.get(r) is not None
                            and f"{r} Lock" not in trig]
        self.assertEqual(sorted(sealed_no_opener), [],
                         f"regions sealed with no client opener (born-softlock): {sorted(sealed_no_opener)}")

    def test_start_spoke_opens_at_start(self):
        """The flattened off-START spokes must bloom immediately, via an ALWAYS-OPEN trigger -- a
        clause with no items and no flags, which the client's natural_key_fired satisfies vacuously
        (all() over []) on the first tick. Limgrave (the start spoke) is the load-bearing case.
        Caelid must NOT ride this mechanism any more: it has a real COUNT trigger (below) -- the
        always-open interim made Caelid reachable at start ('I have Caelid access and I shouldn't',
        playtest 2026-07-24)."""
        world = self.multiworld.worlds[self.player]
        trig = world.fill_slot_data().get("naturalKeyTriggers", {})
        for region in ("Limgrave", "Weeping"):
            self.assertIn(f"{region} Lock", trig, f"{region} must have an opener trigger")
            clauses = trig[f"{region} Lock"]["anyOf"]
            self.assertTrue(any(not c.get("items") and not c.get("flags")
                                and not c.get("countItems") and not c.get("count")
                                for c in clauses),
                            f"{region} must open at start via an empty (always-satisfied) clause")

    # --- COUNT triggers (client count primitive, 2026-07-24) --------------------------
    def _count_clauses(self, region):
        world = self.multiworld.worlds[self.player]
        trig = world.fill_slot_data().get("naturalKeyTriggers", {})
        self.assertIn(f"{region} Lock", trig, f"{region} must have an opener trigger")
        return trig[f"{region} Lock"]["anyOf"]

    def test_caelid_count_trigger(self):
        """Caelid = COUNT gate (COUNT_GATES: 2 of the pooled remembrances), NOT always-open: the
        trigger must be a count clause the client's count primitive evaluates (fires on the 2nd
        received remembrance), and no clause may be empty/always-satisfied."""
        clauses = self._count_clauses("Caelid")
        self.assertEqual(len(clauses), 1, "Caelid: exactly one count clause")
        c = clauses[0]
        self.assertEqual(c.get("count"), 2, "Caelid opens on 2 of the set")
        count_items = c.get("countItems", [])
        self.assertGreaterEqual(len(count_items), 2, "count set must have >= count members")
        self.assertTrue(set(count_items) <= set(_np.REMEMBRANCES),
                        "Caelid's count set must be remembrances")
        self.assertFalse(c.get("items") or c.get("flags"),
                         "Caelid's count clause carries no all-of items/flags")
        # And it must never be satisfiable at start (the 2026-07-24 regression).
        self.assertFalse(any(not c.get("items") and not c.get("flags") and not c.get("count")
                             for c in clauses),
                         "Caelid must NOT open at start via an empty clause")

    def test_leyndell_count_trigger_on_great_runes(self):
        """The capital blooms client-side on the Nth Great Rune (N = leyndell_runes_required,
        default 2, clamped by leyndell_gate -> world.gf_leyndell_runes): the count trigger sets open
        flag 71102 exactly when the vanilla 2-rune wall opens. Sewer (73501, one wall deeper) rides
        the same rune count -- without it the client kick reseals the player at the well."""
        world = self.multiworld.worlds[self.player]
        runes = list(getattr(world, "gf_leyndell_runes", []))
        self.assertTrue(runes, "default seed must arm the rune gate (leyndell_runes_required=2)")
        for region in ("Leyndell", "Sewer"):
            clauses = self._count_clauses(region)
            self.assertEqual(len(clauses), 1, f"{region}: exactly one count clause")
            c = clauses[0]
            self.assertEqual(c.get("count"), len(runes),
                             f"{region} opens on the clamped rune count")
            count_items = c.get("countItems", [])
            self.assertTrue(count_items and all(n.endswith("Great Rune") for n in count_items),
                            f"{region}'s count set must be Great Runes")
            self.assertGreaterEqual(len(count_items), len(runes))
