"""Gated-children fix (2026-07-14): a region behind a vanilla hard wall is entered, not warped past.

Playtest bug: an Altus-anchored rolled seed was handed the East Capital Rampart grace (71102) --
Leyndell's bundle, a warp target on the far side of the capital's 2-Great-Rune gate -- walked
straight in and ended the run at Morgott. The fix is fourfold, and each fold gets its guard here:

  1. DATA ONCE: region_spine.REGION_PARENT names every gated child and the parent it is entered
     from, and every region-entry gate FEATURE must have an entry there (a future gate cannot land
     without one). features/graces.WALL_ARMED must pair every child with its arming predicate.
  2. GRACES: a kept gated child's bundle is emitted EMPTY while its wall is armed (never granted);
     disarming the wall (leyndell_runes_required: 0) reverts to granting, because a fixed in-game
     wall with no armed logic gate would otherwise be physically unwinnable.
  3. KEPT CLOSURE: compute_kept never keeps a child without its whole ancestor chain.
  4. REACHABILITY + ANCHOR: a child's checks require the parent's Lock chain in logic -- and the
     rune wall rides the "To Leyndell" ENTRANCE, so it is transitive to the Sewer -- and the start
     anchor is never a gated child.
"""
import random

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from Fill import distribute_items_restrictive  # noqa: E402
from BaseClasses import CollectionState  # noqa: E402
from worlds.eldenring.data import REGIONS, LOCATIONS  # noqa: E402
from worlds.eldenring.region_spine import (  # noqa: E402
    REGION_PARENT, GOAL_REGION, SPINE, DLC_REGIONS, compute_kept, parent_chain, base_regions)
from worlds.eldenring.region_graces import REGION_GRACE_POINTS  # noqa: E402
from worlds.eldenring.features.graces import WALL_ARMED  # noqa: E402
from worlds.eldenring.features.legacy_key_gates import _LEGACY_KEYS  # noqa: E402
from worlds.eldenring.features.start_grace import pick_anchor_region  # noqa: E402
from ._util import world_items  # noqa: E402

GAME = "Elden Ring"


# ---- 1. the parent map is the single, complete encoding ------------------------------------------
class TestParentMapInvariants:
    def test_parents_are_real_regions_and_chains_terminate(self):
        for child, parent in REGION_PARENT.items():
            assert child in REGIONS, child
            assert parent in REGIONS, parent
            chain = parent_chain(child)  # raises on a cycle
            assert chain and chain[0] == parent

    def test_every_region_entry_gate_feature_has_a_parent_entry(self):
        # legacy_key_gates: a key with a non-empty MAP RANGE gates region ENTRY (the whole map is
        # the region); a (0,0) range gates a check, not a door. leyndell_gate gates GOAL_REGION.
        for key, (region, (lo, hi)) in _LEGACY_KEYS.items():
            if hi > lo:
                assert region in REGION_PARENT, (
                    f"{key!r} gates entry to {region!r} but REGION_PARENT has no entry -- "
                    f"a region-entry gate must name the parent it is entered from")
        assert GOAL_REGION in REGION_PARENT, (
            "leyndell_gate gates entry to the goal region; REGION_PARENT must name its parent")

    def test_wall_armed_pairs_every_child(self):
        assert set(WALL_ARMED) == set(REGION_PARENT), (
            "features/graces.WALL_ARMED must pair EVERY gated child with its arming predicate "
            "(an unpaired child withholds unconditionally, which is only safe as a stopgap)")


# ---- 3. compute_kept closure ----------------------------------------------------------------------
class TestKeptClosure:
    def test_rolled_sweep_never_keeps_a_child_parentless(self):
        rng = random.Random(20260714)
        pools = [list(REGIONS), base_regions()]
        for _ in range(400):
            pool = pools[rng.randrange(len(pools))]
            n = rng.randrange(1, len(pool) + 1)
            kept = compute_kept(n, "rolled", rng, pool)
            for r in kept:
                for anc in parent_chain(r):
                    assert anc in kept, f"kept child {r} without ancestor {anc}: {kept}"

    def test_spine_prefix_closes_too(self):
        rng = random.Random(1)
        for n in range(1, len(SPINE) + 1):
            kept = compute_kept(n, "spine", rng, list(REGIONS))
            for r in kept:
                for anc in parent_chain(r):
                    assert anc in kept

    def test_goal_region_always_pulls_its_ancestors(self):
        # Leyndell is always kept on a base seed; its whole chain must ride along (Altus).
        rng = random.Random(2)
        kept = compute_kept(1, "rolled", rng, base_regions())
        assert GOAL_REGION in kept
        for anc in parent_chain(GOAL_REGION):
            assert anc in kept

    def test_child_eligible_without_parent_is_a_hard_error(self):
        # An eligible pool that contains a gated child but not its parent is a scope-filter bug;
        # compute_kept must refuse loudly, never hand back an unreachable kept set -- on EVERY
        # path, including the n >= len(pool) full-pool return.
        rng = random.Random(3)
        with pytest.raises(ValueError):
            compute_kept(1, "rolled", rng, ["Sewer"])


# ---- 4a. the anchor is never a gated child ---------------------------------------------------------
class TestAnchorNeverGatedChild:
    COUNTS = {r: len(LOCATIONS.get(r, [])) for r in REGIONS}

    def test_sweep_full_kept_set(self):
        rng = random.Random(99)
        for _ in range(2000):
            region, _rule, _n = pick_anchor_region(
                REGIONS, rng, self.COUNTS, DLC_REGIONS, gated=frozenset(REGION_PARENT))
            assert region not in REGION_PARENT, f"anchor {region} is a gated child"

    def test_child_heavy_kept_set_still_anchors_on_an_ancestor(self):
        # the minimal closed kept set around the capital chain: children + their ancestors only.
        kept = ["Sewer", "Leyndell", "Altus", "Raya Lucaria Academy", "Liurnia"]
        rng = random.Random(7)
        for _ in range(200):
            region, _rule, _n = pick_anchor_region(
                kept, rng, self.COUNTS, DLC_REGIONS, gated=frozenset(REGION_PARENT))
            assert region in ("Altus", "Liurnia")

    def test_all_children_kept_set_raises_loudly(self):
        # an all-children kept set cannot exist post-closure; if handed one anyway, refuse.
        rng = random.Random(8)
        with pytest.raises(ValueError):
            pick_anchor_region(list(REGION_PARENT), rng, self.COUNTS, DLC_REGIONS,
                               gated=frozenset(REGION_PARENT))


# ---- 2 + 4b. a live seed: bundles withheld, logic transitive, fill never strands -------------------
class GatedChildrenLiveSeed(WorldTestBase):
    game = GAME
    run_default_tests = False
    # all base regions kept (num_regions 0, DLC off default) -> every gated child is present and
    # armed: item_shuffle + legacy keys are frozen ON; leyndell_runes_required defaults to 2.
    options = {"num_regions": 0}

    def _sd(self):
        return self.world.fill_slot_data()

    def test_armed_children_bundles_withheld_others_granted(self):
        rg = self._sd()["regionGraces"]
        kept = set(self.world._kept())
        # DLC children (Scaduview) are absent from a DLC-off seed -- assert only the kept ones
        # here, and pin the base trio by name so a rename can't quietly empty the loop.
        # ScaduviewContainmentSeed below covers the DLC child on an enable_dlc seed.
        assert {"Raya Lucaria Academy", "Leyndell", "Sewer"} <= kept & set(REGION_PARENT)
        for child in REGION_PARENT:
            if child not in kept:
                continue
            assert rg.get(f"{child} Lock") == [], (
                f"{child} bundle must be withheld (armed wall), got {rg.get(f'{child} Lock')}")
        # a non-gated region's bundle is untouched -- the fix must not eat normal grants.
        assert rg.get("Altus Lock") == list(REGION_GRACE_POINTS["Altus"])
        assert rg.get("Liurnia Lock") == list(REGION_GRACE_POINTS["Liurnia"])

    def test_rune_gate_keys_no_longer_emitted(self):
        sd = self._sd()
        assert "runeGatedGraces" not in sd, "runeGatedGraces is retired (client half never existed)"
        assert "greatRuneItemIds" not in sd

    def test_child_checks_unreachable_without_parent_lock(self):
        # a FULL state (everything, including the anchor precollect) minus every copy of the
        # parent's Lock -> every check of the child (and of the child's children) must be
        # unreachable; hand the Lock back -> reachable. The remove-all-copies pattern (per
        # test_gf_ending) is what makes this seed-robust: the withheld Lock may be the
        # precollected anchor, which a naive collect-everything-else loop would miss.
        cases = [("Leyndell", "Altus Lock", ["Leyndell", "Sewer"]),
                 ("Raya Lucaria Academy", "Liurnia Lock", ["Raya Lucaria Academy"]),
                 ("Sewer", "Leyndell Lock", ["Sewer"])]
        locs_by_region = {}
        for l in self.multiworld.get_locations(self.player):
            locs_by_region.setdefault(l.parent_region.name, []).append(l)
        for _child, parent_lock, gated_regions in cases:
            st = self.multiworld.get_all_state(False)
            copies = [it for it in world_items(self) if it.name == parent_lock]
            assert copies, f"{parent_lock} missing from the created items"
            for it in copies:
                st.remove(it)
            for region in gated_regions:
                sample = locs_by_region.get(region, [])[:8]
                assert sample, f"no locations found in {region}"
                for l in sample:
                    assert not l.can_reach(st), (
                        f"{l.name} ({region}) reachable WITHOUT {parent_lock}")
            st.collect(copies[0], prevent_sweep=True)
            for region in gated_regions:
                for l in locs_by_region.get(region, [])[:8]:
                    assert l.can_reach(st), f"{l.name} ({region}) blocked WITH {parent_lock}"

    def test_capital_and_sewer_unreachable_without_the_gate_runes(self):
        # the rune wall is TRANSITIVE: it guards the "To Leyndell" ENTRANCE (not just the capital's
        # own checks), so the Sewer -- entered down a well inside the capital -- is runeless-
        # unreachable too. A full state minus every copy of the gate's chosen runes must reach
        # neither region; collecting the runes back must open both.
        runes = set(getattr(self.world, "gf_leyndell_runes", ()))
        assert runes, "default seed must arm the rune gate (leyndell_runes_required=2)"
        st = self.multiworld.get_all_state(False)
        rune_copies = [it for it in world_items(self) if it.name in runes]
        assert rune_copies, "gate runes missing from the created items"
        for it in rune_copies:
            st.remove(it)
        locs_by_region = {}
        for l in self.multiworld.get_locations(self.player):
            locs_by_region.setdefault(l.parent_region.name, []).append(l)
        for region in ("Leyndell", "Sewer"):
            sample = locs_by_region.get(region, [])[:8]
            assert sample, f"no locations in {region}"
            for l in sample:
                assert not l.can_reach(st), (
                    f"{l.name} ({region}) reachable WITHOUT the gate runes -- the rune wall is "
                    f"not transitive to the capital's children")
        for it in rune_copies:
            st.collect(it, prevent_sweep=True)
        for region in ("Leyndell", "Sewer"):
            for l in locs_by_region.get(region, [])[:8]:
                assert l.can_reach(st), f"{l.name} ({region}) blocked WITH the runes"

    def test_fill_never_strands_progression_in_a_sealed_child(self):
        mw = self.multiworld
        distribute_items_restrictive(mw)
        assert mw.can_beat_game(), "full seed with gated children must stay beatable"
        # sphere sanity: sweeping from an empty state must reach every progression item.
        state = CollectionState(mw)
        state.sweep_for_advancements()
        for l in mw.get_locations(self.player):
            if l.item is not None and l.item.advancement:
                assert state.can_reach(l), (
                    f"progression {l.item.name} stranded on unreachable {l.name}")


class ScaduviewContainmentSeed(WorldTestBase):
    """The Scaduview kick (in-game, 2026-07-15): 'Region unlocked: Scaduview' (76935 set), warp to
    its own front-door grace 'Hinterland' -> SEALED REGION (area 2100010) -> Roundtable. The ground
    at that grace is m21_00's DEFAULT play region (bucket 21000 = Shadow Keep, shared with the whole
    Keep interior -- subs 2100000/01/11..15), so the kick is unfixable by rebucketing: Scaduview is
    a containment child of Shadow Keep (region_spine.REGION_PARENT), bundle withheld, logic
    transitive through the Keep's Lock. This seed pins all three halves on an enable_dlc world."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "enable_dlc": True}

    def test_scaduview_bundle_withheld_and_keep_lock_gates_it(self):
        rg = self.world.fill_slot_data()["regionGraces"]
        assert rg.get("Scaduview Lock") == [], (
            f"Scaduview bundle must be withheld (containment wall), got {rg.get('Scaduview Lock')}")
        assert rg.get("Shadow Keep Lock") == list(REGION_GRACE_POINTS["Shadow Keep"]), (
            "the parent's own bundle must stay granted")
        # logic half: a full state minus every Shadow Keep Lock copy reaches NO Scaduview check;
        # handing one copy back opens it (remove-all-copies per test_gf_ending -- the withheld
        # Lock may be precollected).
        st = self.multiworld.get_all_state(False)
        copies = [it for it in world_items(self) if it.name == "Shadow Keep Lock"]
        assert copies, "Shadow Keep Lock missing from the created items"
        for it in copies:
            st.remove(it)
        locs = [l for l in self.multiworld.get_locations(self.player)
                if l.parent_region is not None and l.parent_region.name == "Scaduview"]
        assert locs, "no Scaduview locations on an enable_dlc seed"
        for l in locs[:8]:
            assert not l.can_reach(st), (
                f"{l.name} (Scaduview) reachable WITHOUT Shadow Keep Lock -- containment broken")
        st.collect(copies[0], prevent_sweep=True)
        for l in locs[:8]:
            assert l.can_reach(st), f"{l.name} (Scaduview) blocked WITH Shadow Keep Lock"


class LeyndellWallDisarmed(WorldTestBase):
    """leyndell_runes_required: 0 disarms the rune gate -> the capital bundle is GRANTED again
    (the game's own wall stays 2 runes; only the granted warp can honor 'no requirement'), while
    the Sewer (containment wall, no knob) stays withheld."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "leyndell_runes_required": 0}

    def test_disarmed_capital_grants_sewer_still_withheld(self):
        rg = self.world.fill_slot_data()["regionGraces"]
        assert rg.get("Leyndell Lock") == list(REGION_GRACE_POINTS["Leyndell"]), (
            "disarmed rune gate must grant the capital bundle or the capital is unwinnable")
        assert rg.get("Sewer Lock") == []
        assert rg.get("Raya Lucaria Academy Lock") == []


class SewerRuneRegressionSeed(WorldTestBase):
    """Alaric's in-game generation combo, 2026-07-15 ('a great rune was in the sewer on mohg's
    drop'): num_regions 0 + DLC + region_locks ending + leyndell_runes_required 2 + accessibility
    MINIMAL. Under minimal, AP's fill_restrictive SKIPS the location reachability check whenever
    the exploration state can already beat the game (Fill.py perform_access_check) -- and because
    the region_locks completion never mentions the gate runes, a rune's own placement is exactly
    when the check is skipped. The strict progression-surface pre-fill (which runs in this
    fixture: WorldTestBase's gen steps end at pre_fill) then LOCKS the rune wherever item_rule
    allows. Seed 36 locked Godrick's Great Rune onto Mohg the Omen (Sewer :: [Incantation]
    Bloodflame Talons, f510250) -- behind the very wall it opens -- an unrescuable strand that
    post_fill's audit rightly FillErrors. item_rule is the ONE rule can_fill honors even with the
    access check skipped, so the deterministic guard here is: every location in the walled
    subtree -- the capital AND everything hanging off it (Sewer, Ashen Capital finale) -- must
    REJECT every gating item outright."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "enable_dlc": True, "ending_condition": "region_locks",
               "leyndell_runes_required": 2, "accessibility": "minimal"}

    def test_gating_items_barred_from_the_whole_walled_subtree(self):
        from worlds.eldenring.data import FINALE_REGION
        from worlds.eldenring.features.leyndell_gate import (
            _GATING_ITEMS, _gated_region_names)
        gated = _gated_region_names(self.world)
        # the derivation must span the KNOWN children -- a rename/reparent that drops one of
        # these must fail here, not resurface as a 1-in-N FillError in someone's overnight gen.
        assert {"Leyndell", "Sewer", FINALE_REGION} <= set(gated), gated
        gating = [self.world.create_item(nm) for nm in sorted(_GATING_ITEMS)
                  if nm in self.world.item_name_to_id]
        assert gating, "no gating items resolvable from the catalog"
        checked = 0
        for loc in self.multiworld.get_locations(self.player):
            if loc.parent_region is None or loc.parent_region.name not in gated:
                continue
            for it in gating:
                assert not loc.item_rule(it), (
                    f"{loc.name} ({loc.parent_region.name}) accepts gating item {it.name} -- "
                    f"inside the rune wall this can deadlock the gate (seed-36 class)")
            checked += 1
        assert checked >= 50, f"suspiciously few gated-subtree locations audited ({checked})"

    def test_no_gating_item_pre_filled_into_the_walled_subtree(self):
        # the strict surface pre-fill already ran (gen steps end at pre_fill): whatever it
        # placed-and-LOCKED must respect the wall.
        from worlds.eldenring.features.leyndell_gate import (
            _GATING_ITEMS, _gated_region_names)
        gated = _gated_region_names(self.world)
        for loc in self.multiworld.get_locations(self.player):
            if loc.item is None or loc.parent_region is None:
                continue
            if loc.parent_region.name in gated:
                assert loc.item.name not in _GATING_ITEMS, (
                    f"pre-fill placed {loc.item.name} at {loc.name} inside the rune wall")

    def test_full_fill_leaves_no_stranded_progression(self):
        # end-to-end: full fill + the post_fill audit must not FillError, and an empty-state
        # sweep must reach every own progression item (the audit's own bar).
        mw = self.multiworld
        distribute_items_restrictive(mw)
        from worlds.eldenring.features import progression_surface as _ps
        _ps.audit_reachable(self.world)  # raises FillError on a locked strand
        assert mw.can_beat_game()
        state = CollectionState(mw)
        state.sweep_for_advancements()
        for l in mw.get_locations(self.player):
            if l.item is not None and l.item.advancement:
                assert state.can_reach(l), (
                    f"progression {l.item.name} stranded on unreachable {l.name}")
