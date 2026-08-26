"""Progressive ability lock (#945/#980): the locked abilities become findable 'Unlock: X' items.

Static mode is covered by test_gf_ability_lock_option. These guard the PROGRESSIVE additions:
the synthetic item ids (fixed base, disjoint, useful, not game-grantable), that they are pooled
ONLY in progressive mode, the abilityUnlockItems map shape + requiresClientFeatures handshake, and
that a full generate stays count-exact with the items in the pool.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402

GAME = "Elden Ring"


# ---- AP-free id / contract facts -------------------------------------------------------------
def test_ids_are_a_disjoint_fixed_useful_block():
    from worlds.eldenring import core
    names = [nm for _k, nm in contract.ABILITY_UNLOCK_ITEM_NAMES]
    ids = [core.item_name_to_id[nm] for nm in names]
    # fixed, contiguous, at the declared base
    assert ids == [contract.ABILITY_UNLOCK_ITEM_BASE + i for i in range(len(names))]
    # useful, never filler (an unlock must not be swept or discarded)
    from BaseClasses import ItemClassification
    for nm in names:
        assert core._item_class[nm] == ItemClassification.useful
        # synthetic: the game is never asked to hand one over
        assert str(core.item_name_to_id[nm]) not in core._AP_IDS_TO_ITEM_IDS
    # disjoint from the spawn-trap block (7800000 + <10000)
    assert min(ids) >= core._SPAWN_TRAP_BASE + 10000


def test_map_is_a_declared_hashed_key():
    key = contract.BY_NAME["abilityUnlockItems"]
    assert key.shape == "STR_MAP"
    # it IS a top-level (hashed) key -- a new client capability, unlike the static option subkey
    assert "abilityUnlockItems" not in contract.OPTIONS_BY_NAME


# ---- the DEFAULT (2026-08-25 ruling): progressive, and inert until an ability is named ------
def test_mode_defaults_to_progressive():
    """Alaric's 2026-08-25 ruling: a seed that locks abilities should hand them back as items.

    The motivating case is the multiworld one -- a lock the player can never undo is a permanent
    handicap, while the progressive default turns it into the item hunt the mode was written for.
    Static stays available as the explicit opt-out."""
    from worlds.eldenring.features.ability_lock import AbilityLockMode
    assert AbilityLockMode.default == AbilityLockMode.option_progressive
    assert AbilityLockMode.option_static == 0, "static must remain a NAMED opt-out, not a removal"


class ProgressiveDefaultWithNoLockedAbilities(WorldTestBase):
    """The default flip must not move a seed that locks nothing -- the whole axis stays inert.

    locked_abilities defaults empty, and `_progressive_active` gates on it, so the new default mode
    pools no item, ships no map, and demands no client feature. This is the shipped-default seed."""
    game = GAME
    options = {"num_regions": 0}

    def test_the_axis_is_inert_without_a_locked_ability(self):
        from worlds.eldenring.features.ability_lock import AbilityLockMode
        assert int(self.world.options.ability_lock_mode.value) == AbilityLockMode.option_progressive
        assert set(self.world.options.locked_abilities.value) == set(), "empty is the default"
        names = {nm for _k, nm in contract.ABILITY_UNLOCK_ITEM_NAMES}
        pool_names = {i.name for i in self.multiworld.itempool if i.player == self.player}
        assert not (names & pool_names), "an empty lock set must pool no Unlock: item"
        sd = self.world.fill_slot_data()
        assert "abilityUnlockItems" not in sd
        assert contract.ABILITY_UNLOCK_FEATURE not in sd.get("requiresClientFeatures", [])
        assert sd["options"]["locked_abilities"] == []


class ProgressiveIsWhatAnUnpinnedModeGets(WorldTestBase):
    """A yaml that names abilities but NOT a mode now generates PROGRESSIVE (behaviour change).

    Before 2026-08-25 the same yaml generated a static, permanent lock. This pins the new
    resolution end to end: the items are pooled and the client handshake is demanded."""
    game = GAME
    options = {"num_regions": 0, "locked_abilities": ["roll"]}  # mode deliberately unset

    def test_unpinned_mode_pools_the_unlock_and_demands_the_feature(self):
        want = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)["roll"]
        pool_names = [i.name for i in self.multiworld.itempool if i.player == self.player]
        assert want in pool_names, "an unpinned mode must now resolve to progressive"
        sd = self.world.fill_slot_data()
        assert sd["abilityUnlockItems"] == {str(self.world.item_name_to_id[want]): "roll"}
        assert contract.ABILITY_UNLOCK_FEATURE in sd["requiresClientFeatures"]


# ---- static mode mints nothing ---------------------------------------------------------------
class StaticMintsNoItems(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "locked_abilities": ["roll", "r1"], "ability_lock_mode": "static"}

    def test_no_unlock_items_and_no_map(self):
        names = {nm for _k, nm in contract.ABILITY_UNLOCK_ITEM_NAMES}
        pool_names = {i.name for i in self.multiworld.itempool if i.player == self.player}
        assert not (names & pool_names), "static mode must not pool any Unlock: item"
        sd = self.world.fill_slot_data()
        assert "abilityUnlockItems" not in sd
        assert contract.ABILITY_UNLOCK_FEATURE not in sd.get("requiresClientFeatures", [])
        # the static set still rides the options echo
        assert sd["options"]["locked_abilities"] == ["r1", "roll"]


# ---- progressive mode pools exactly the locked set + ships the map ---------------------------
class ProgressivePoolsAndMaps(WorldTestBase):
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["roll", "r1", "jump"],
               "ability_lock_mode": "progressive"}

    def test_exactly_the_locked_abilities_are_pooled(self):
        want = {dict(contract.ABILITY_UNLOCK_ITEM_NAMES)[k] for k in ("roll", "r1", "jump")}
        pool_names = [i.name for i in self.multiworld.itempool if i.player == self.player]
        got = {n for n in pool_names if n.startswith("Unlock: ")}
        assert got == want, got
        # one copy each
        for n in want:
            assert pool_names.count(n) == 1, f"{n} appears {pool_names.count(n)}x"

    def test_map_shape_and_handshake(self):
        sd = self.world.fill_slot_data()
        m = sd["abilityUnlockItems"]
        assert set(m.values()) == {"roll", "r1", "jump"}
        for k in m:
            assert k == str(int(k)) and int(k) >= contract.ABILITY_UNLOCK_ITEM_BASE
        assert contract.ABILITY_UNLOCK_FEATURE in sd["requiresClientFeatures"]
        # the abilities ALSO start locked (client disables at connect, then unlocks on receipt)
        assert sd["options"]["locked_abilities"] == ["jump", "r1", "roll"]
        contract.validate_slot_data(sd, strict=True)

    # NB: count-exactness (items == fillable locations) is proven by WorldTestBase's own default
    # suite, which fills this very seed -- a surplus/deficit would raise FillError there. A naive
    # len(itempool) == len(get_locations) check is wrong (itempool excludes the precollected start
    # anchor and event locations), so it is deliberately not re-asserted here.


class ProgressiveHealUnlock(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "locked_abilities": ["heal"], "ability_lock_mode": "progressive"}

    def test_heal_is_a_findable_unlock_item(self):
        # heal locks the flask (client No-Flask SpEffect), but in progressive mode it is still just
        # another findable Unlock item -- the pool + map treat it like any ability.
        unlock_heal = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)["heal"]  # "Unlock: Heal"
        pool = [i.name for i in self.multiworld.itempool if i.player == self.player]
        assert pool.count(unlock_heal) == 1, pool
        sd = self.world.fill_slot_data()
        assert set(sd["abilityUnlockItems"].values()) == {"heal"}
        assert contract.ABILITY_UNLOCK_FEATURE in sd["requiresClientFeatures"]
        assert sd["options"]["locked_abilities"] == ["heal"]


# ---- goal requirement (#980 follow-up): unlocks are progression + gate the goal by default -------
class ProgressiveUnlocksGateTheGoalByDefault(WorldTestBase):
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["roll", "r1"],
               "ability_lock_mode": "progressive"}  # ability_unlocks_required defaults ON

    def test_created_items_are_progression(self):
        from BaseClasses import ItemClassification
        names = {dict(contract.ABILITY_UNLOCK_ITEM_NAMES)[k] for k in ("roll", "r1")}
        pool = {i.name: i for i in self.multiworld.itempool if i.player == self.player}
        for n in names:
            # the created item is upgraded to progression by core._class_for, even though the
            # module-level base classification stays useful (that base is asserted elsewhere)
            assert pool[n].advancement, f"{n} should be progression when goal-required"

    def test_single_source_and_goal_wire_agree(self):
        names = {dict(contract.ABILITY_UNLOCK_ITEM_NAMES)[k] for k in ("roll", "r1")}
        assert set(self.world._required_ability_unlocks()) == names
        sd = self.world.fill_slot_data()
        # both terminal conditions read the same list: the wire carries every required unlock
        assert names <= set(sd["goalRequiredItems"])
        contract.validate_slot_data(sd, strict=True)

    def test_completion_condition_actually_requires_them(self):
        names = [dict(contract.ABILITY_UNLOCK_ITEM_NAMES)[k] for k in ("roll", "r1")]
        cond = self.multiworld.completion_condition[self.player]
        full = self.multiworld.get_all_state(False)
        # WITNESS: the full state (unlocks included) DOES complete -- so the negative below is the
        # requirement biting, not a goal that never fires (test_gf_vacuous_pass discipline).
        assert cond(full), "the full collected state should satisfy the goal"
        # ...and dropping just the unlocks must break it: they are genuinely required.
        for n in names:
            full.remove(self.world.create_item(n))
        assert not cond(full), "goal must not fire without the required Unlock items held"


class ProgressiveUnlocksOptOutStayUseful(WorldTestBase):
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["roll", "r1"],
               "ability_lock_mode": "progressive",
               "ability_unlocks_required": False}

    def test_useful_not_progression_and_not_goal_required(self):
        from worlds.eldenring.features.ability_lock import _progressive_active, _locked_keys
        # WITNESS: the feature IS active with a real lock set, so an empty requirement below is the
        # opt-out doing its job, not the scan finding nothing (test_gf_vacuous_pass discipline).
        assert _progressive_active(self.world) and set(_locked_keys(self.world)) == {"roll", "r1"}
        names = {dict(contract.ABILITY_UNLOCK_ITEM_NAMES)[k] for k in ("roll", "r1")}
        pool = {i.name: i for i in self.multiworld.itempool if i.player == self.player}
        # the unlocks are pooled (witness they exist) but stay useful, not progression
        assert names <= set(pool), "opted-out unlocks must still be pooled"
        for n in names:
            assert pool[n].useful and not pool[n].advancement, f"{n} should stay useful when opted out"
        # BEHAVIOURAL: the goal does NOT require them -- a state holding everything but the unlocks
        # still reads complete (the mirror of the default-on test, and a positive assertion).
        cond = self.multiworld.completion_condition[self.player]
        full = self.multiworld.get_all_state(False)
        for n in names:
            full.remove(self.world.create_item(n))
        assert cond(full), "opted out: goal must still fire without the unlocks held"
        # still findable items with the map + handshake -- only the GOAL requirement is dropped
        sd = self.world.fill_slot_data()
        assert set(sd["abilityUnlockItems"].values()) == {"roll", "r1"}
        assert contract.ABILITY_UNLOCK_FEATURE in sd["requiresClientFeatures"]


# ---- Roll comes early (bobler playtest): early_items, still exportable -----------------------------
class RollUnlockIsForcedEarly(WorldTestBase):
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["roll", "l2"],
               "ability_lock_mode": "progressive"}

    def test_only_roll_is_declared_early(self):
        roll = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)["roll"]
        l2 = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)["l2"]
        early = self.multiworld.early_items[self.player]
        # Roll is forced early; L2 (an annoyance, not a cripple) is left to export freely.
        assert early.get(roll) == 1, "Roll unlock must be declared early"
        assert l2 not in early, "only Roll is forced early; other abilities export freely"

    def test_roll_actually_lands_in_an_early_sphere(self):
        from Fill import distribute_items_restrictive
        roll = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)["roll"]
        # WITNESS it was declared early, then prove Fill honoured it end to end.
        assert self.multiworld.early_items[self.player].get(roll) == 1
        distribute_items_restrictive(self.multiworld)
        spheres = list(self.multiworld.get_spheres())
        idx = next((i for i, sph in enumerate(spheres)
                    for loc in sph if loc.item and loc.item.name == roll), None)
        assert idx is not None and idx <= 1, f"Roll unlock should land in sphere 0-1, got {idx}"


# ---- An attack comes early when ALL FOUR attack inputs are locked (#1035) --------------------------
# Alaric's ruling, 2026-08-25: take the conservative option -- "have one attack in early_items if all
# of r1/r2/l1/l2 are locked". And: "spells don't count, you need an L or R button to cast a spell",
# so there is no caster carve-out; the L/R unlocks are the only attack path this code recognises.
# The mode is PINNED explicitly in every class below rather than relying on the default (#1036 moves
# that default; these tests must answer the same question on either side of it).
class AllAttacksLockedForcesOneAttackEarly(WorldTestBase):
    """THE MOTIVATING CASE (CONTRIBUTING rule 11): all four attack abilities locked, progressive
    mode -> exactly one attack Unlock is declared early."""
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["r1", "r2", "l1", "l2"],
               "ability_lock_mode": "progressive"}

    def test_exactly_one_attack_unlock_is_declared_early(self):
        from worlds.eldenring.features.ability_lock import (
            _progressive_active, _locked_keys, _ATTACK_KEYS, _FORCED_EARLY_ATTACK)
        # WITNESS the feature is actually live with all four attacks locked, so the assertions below
        # are the rule firing, not an inert seed (test_gf_vacuous_pass discipline).
        assert _progressive_active(self.world)
        assert set(_locked_keys(self.world)) == set(_ATTACK_KEYS)
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        early = self.multiworld.early_items[self.player]
        forced = [names[k] for k in _ATTACK_KEYS if early.get(names[k])]
        assert forced == [names[_FORCED_EARLY_ATTACK]], (
            "exactly ONE attack unlock must be forced early, and it must be the deterministic pick "
            f"({_FORCED_EARLY_ATTACK}); got {forced}")
        assert early[names[_FORCED_EARLY_ATTACK]] == 1
        # exportable: early_items, NOT local_early_items (the Roll precedent -- early wherever it lands)
        assert names[_FORCED_EARLY_ATTACK] not in self.multiworld.local_early_items[self.player]
        # and it is really in the pool, which is what makes the declaration placeable
        pool = {i.name for i in self.multiworld.itempool if i.player == self.player}
        assert names[_FORCED_EARLY_ATTACK] in pool

    def test_the_attack_actually_lands_in_an_early_sphere(self):
        from Fill import distribute_items_restrictive
        from worlds.eldenring.features.ability_lock import _FORCED_EARLY_ATTACK
        atk = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)[_FORCED_EARLY_ATTACK]
        assert self.multiworld.early_items[self.player].get(atk) == 1
        distribute_items_restrictive(self.multiworld)
        spheres = list(self.multiworld.get_spheres())
        idx = next((i for i, sph in enumerate(spheres)
                    for loc in sph if loc.item and loc.item.name == atk), None)
        assert idx is not None and idx <= 1, f"attack unlock should land in sphere 0-1, got {idx}"

    def test_the_pick_is_deterministic_not_drawn(self):
        # A constant, not a draw: the same yaml must always force the same unlock (no seed-dependent
        # assertion to re-measure). Re-running create_items on a fresh random state changes nothing.
        from worlds.eldenring.features.ability_lock import AbilityLock, _FORCED_EARLY_ATTACK
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        self.multiworld.early_items[self.player].clear()
        self.world.random.seed(1234567)
        AbilityLock().create_items(self.world)
        first = dict(self.multiworld.early_items[self.player])
        self.multiworld.early_items[self.player].clear()
        self.world.random.seed(7654321)
        AbilityLock().create_items(self.world)
        assert dict(self.multiworld.early_items[self.player]) == first
        assert first.get(names[_FORCED_EARLY_ATTACK]) == 1


class ThreeOfFourAttacksLockedForcesNothing(WorldTestBase):
    """THE CONTROL. Three attacks locked leaves one attack input free -- a damage source at start --
    so nothing is forced. Without this row the class above would pass on a rule that fired always."""
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["r1", "r2", "l1"],
               "ability_lock_mode": "progressive"}

    def test_no_attack_is_forced_early(self):
        from worlds.eldenring.features.ability_lock import _progressive_active, _locked_keys
        # WITNESS: the feature is live and three attacks ARE locked -- an empty early map below is
        # the threshold holding, not the feature being off.
        assert _progressive_active(self.world)
        assert set(_locked_keys(self.world)) == {"r1", "r2", "l1"}
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        early = self.multiworld.early_items[self.player]
        for k in ("r1", "r2", "l1", "l2"):
            assert names[k] not in early, f"{k} must not be forced early with an attack still free"
        # they are still pooled, so this is a forcing decision, not a pooling one
        pool = {i.name for i in self.multiworld.itempool if i.player == self.player}
        assert {names[k] for k in ("r1", "r2", "l1")} <= pool


class SpellsAreNoCarveOut(WorldTestBase):
    """The second ruling, pinned as behaviour: "spells don't count, you need an L or R button to cast
    a spell". Nothing about a caster-shaped seed relaxes the rule -- the world cannot see a loadout,
    and the only attack path recognised is an L/R unlock. Same lock set as the motivating case, with
    the spell-adjacent knobs on: the forcing is unchanged."""
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["r1", "r2", "l1", "l2"],
               "ability_lock_mode": "progressive",
               "ability_unlocks_required": False}

    def test_forced_even_with_unlocks_not_goal_required(self):
        from worlds.eldenring.features.ability_lock import _FORCED_EARLY_ATTACK, _required_unlock_names
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        # WITNESS the opt-out is really in force (no goal requirement), so this is the orthogonality
        # claim being tested and not the default path again.
        assert _required_unlock_names(self.world) == []
        assert self.multiworld.early_items[self.player].get(names[_FORCED_EARLY_ATTACK]) == 1

    def test_the_predicate_reads_the_lock_set_alone(self):
        # No spell, staff or seal can satisfy the rule: the predicate is a function of the LOCKED
        # ABILITY SET and nothing else, and every non-attack ability in the set is irrelevant to it.
        from worlds.eldenring.features.ability_lock import _all_attacks_locked, _ATTACK_KEYS
        assert _all_attacks_locked(list(_ATTACK_KEYS))
        # heal/roll/jump/crouch do not stand in for a missing attack -- three attacks + every other
        # lockable ability still reads False (the caster's "but I can cast" has no representation).
        assert not _all_attacks_locked(["r1", "r2", "l1", "roll", "jump", "heal", "crouch"])
        for drop in _ATTACK_KEYS:
            assert not _all_attacks_locked([k for k in _ATTACK_KEYS if k != drop]), (
                f"with {drop} unlocked there is still an attack input, so nothing is forced")


class RollAndAttackAreBothForcedEarly(WorldTestBase):
    """Both conditions at once: Roll locked AND all four attacks locked. early_items must carry TWO
    entries -- the two seams compose rather than one overwriting the other."""
    game = GAME
    options = {"num_regions": 0,
               "locked_abilities": ["roll", "r1", "r2", "l1", "l2"],
               "ability_lock_mode": "progressive"}

    def test_both_entries_present(self):
        from worlds.eldenring.features.ability_lock import _FORCED_EARLY_ATTACK
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        early = self.multiworld.early_items[self.player]
        assert early.get(names["roll"]) == 1, "Roll must still be forced early"
        assert early.get(names[_FORCED_EARLY_ATTACK]) == 1, "the attack must be forced early too"
        assert len({names["roll"], names[_FORCED_EARLY_ATTACK]} & set(early)) == 2

    def test_both_land_early_end_to_end(self):
        from Fill import distribute_items_restrictive
        from worlds.eldenring.features.ability_lock import _FORCED_EARLY_ATTACK
        names = dict(contract.ABILITY_UNLOCK_ITEM_NAMES)
        wanted = {names["roll"], names[_FORCED_EARLY_ATTACK]}
        assert wanted <= set(self.multiworld.early_items[self.player])
        distribute_items_restrictive(self.multiworld)
        spheres = list(self.multiworld.get_spheres())
        seen = {}
        for i, sph in enumerate(spheres):
            for loc in sph:
                if loc.item and loc.item.name in wanted:
                    seen.setdefault(loc.item.name, i)
        assert set(seen) == wanted, f"both must be placed, got {seen}"
        for nm, i in seen.items():
            assert i <= 1, f"{nm} should land in sphere 0-1, got {i}"
