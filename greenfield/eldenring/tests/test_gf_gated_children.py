"""Gated children (2026-07-14): a region behind a vanilla hard wall is entered, not warped past.

Playtest bug: an Altus-anchored rolled seed was handed the East Capital Rampart grace (71102) --
Leyndell's bundle, a warp target on the far side of the capital's 2-Great-Rune gate -- walked
straight in and ended the run at Morgott. The fix is fourfold, and each fold gets its guard here:

  1. DATA ONCE: region_spine.REGION_PARENT names every gated child and the parent it is entered
     from, and every region-entry gate FEATURE must have an entry there (a future gate cannot land
     without one). features/graces.WALL_ARMED must pair every child with its arming predicate.
  2. GRACES: a kept gated child's bundle was emitted EMPTY while its wall was armed (never
     granted); disarming the wall reverted to granting, because a fixed in-game wall with no
     armed logic gate would otherwise be physically unwinnable.
  3. KEPT CLOSURE: compute_kept never keeps a child without its whole ancestor chain.
  4. REACHABILITY + ANCHOR: a child's checks require the parent's Lock chain in logic -- and the
     start anchor is never a gated child.
  5. THE OPEN FLAG IS NOT A GRACE (#278, added 2026-08-01). Folds 1-4 shipped in 2026-07 and the
     playtest bug came BACK anyway, through a door none of them watched. `regionGraces` is emptied
     while the wall is armed -- but `regionOpenFlags` shipped the SAME flag, because for every
     ordinary region the open flag IS the front-door grace by derivation (gen_data._front_door), and
     the client's `open_on_received_name` sets it directly on Lock receipt. So the Lock lit East
     Capital Rampart (71102) / Church of the Cuckoo (71402) / 73501 regardless, handing the player a
     fast-travel target past the wall. Folds 1-4 all passed while it did (35 green). One bit cannot
     be both the kick latch and a warp unlock (#240's shape), so gated children now carry a
     SYNTHETIC open flag and this fold is what keeps it synthetic.

🛑 FOLD 2 IS RETIRED ON EVERY SEED SINCE 2026-09-14 (Alaric: Leyndell is an ordinary Lock
region; Raya since 2026-08-16, #740). No wall is armed in logic anywhere: the capital's
Great-Rune wall is gone, its bundle rides the Leyndell Lock like any ungated region's, and the
physical two-rune seal is opened by the client on Lock receipt (lockRevealFlags 105+182). What
remains is the CONTAINMENT -- the parent chain, the kept-set closure, the anchor bar, the
synthetic open flag -- which is still the physical truth (the capital is entered from Altus)
and still what keeps fill honest. The live-seed classes below assert the granted state, not the
withheld one; a wall that returns must re-arm fold 2's tests with it, not inherit these.
"""
import random

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from Fill import distribute_items_restrictive  # noqa: E402
from BaseClasses import CollectionState  # noqa: E402
from worlds.eldenring.tables.data import REGIONS, LOCATIONS, HUB  # noqa: E402
from worlds.eldenring.region_spine import (  # noqa: E402
    REGION_PARENT, GOAL_REGION, SPINE, DLC_REGIONS, compute_kept, parent_chain, base_regions)
from worlds.eldenring.tables.region_graces import REGION_GRACE_POINTS  # noqa: E402
from worlds.eldenring.tables.region_open_flags import REGION_OPEN_FLAGS  # noqa: E402
from worlds.eldenring.tables.region_play_ids import REGION_PLAY_IDS  # noqa: E402
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
        # the region); a (0,0) range gates a check, not a door.
        for key, (region, (lo, hi)) in _LEGACY_KEYS.items():
            if hi > lo:
                assert region in REGION_PARENT, (
                    f"{key!r} gates entry to {region!r} but REGION_PARENT has no entry -- "
                    f"a region-entry gate must name the parent it is entered from")

    def test_goal_region_keeps_its_geography_parent(self):
        # 🛑 GEOGRAPHY, NOT A GATE (2026-09-14, Alaric's call). The capital's rune wall is retired;
        # "Leyndell": "Altus" stays because the capital is physically entered from Altus, and the
        # Lock chain, the kept-set closure, the anchor bar and the synthetic open flag all still
        # read it. If a future spine edit drops or re-parents it, that is a deliberate geography
        # change and it must fail here first, not surface as strandeds.
        assert REGION_PARENT.get(GOAL_REGION) == "Altus", (
            f"{GOAL_REGION} must stay parented under Altus for geography -- see the 2026-09-14 "
            f"note in region_spine.py")

    def test_wall_armed_pairs_every_child(self):
        assert set(WALL_ARMED) == set(REGION_PARENT), (
            "features/graces.WALL_ARMED must pair EVERY gated child with its arming predicate "
            "(an unpaired child withholds unconditionally, which is only safe as a stopgap)")

    def test_no_wall_is_armed_on_a_default_seed(self):
        # The ruling, stated as a pairing property rather than a seed property: both predicates
        # must read False with no gate state published. A wall that re-arms must do so by
        # publishing state a predicate reads -- and this names it.
        class _Empty:
            pass
        for child, armed in WALL_ARMED.items():
            assert armed(_Empty()) is False, (
                f"{child}'s wall arms with no gate state published -- since 2026-09-14 no wall "
                f"may arm in any logic mode except natural_progression's own capital wall, which "
                f"lives outside WALL_ARMED")


# ---- 3. compute_kept closure ----------------------------------------------------------------------
class TestKeptClosure:
    def test_rolled_sweep_never_keeps_a_child_parentless(self):
        rng = random.Random(20260714)
        pools = [list(REGIONS), base_regions()]
        for _ in range(400):
            pool = pools[rng.randrange(len(pools))]
            n = rng.randrange(1, len(pool) + 1)
            kept = compute_kept(n, rng, pool)
            for r in kept:
                for anc in parent_chain(r):
                    assert anc in kept, f"kept child {r} without ancestor {anc}: {kept}"

    def test_spine_prefix_closes_too(self):
        rng = random.Random(1)
        for n in range(1, len(SPINE) + 1):
            kept = compute_kept(n, rng, list(REGIONS))
            for r in kept:
                for anc in parent_chain(r):
                    assert anc in kept

    def test_goal_region_pulls_its_ancestors_by_either_route(self):
        # WAS test_goal_region_always_pulls_its_ancestors: `compute_kept(1, rng, base_regions())`
        # then `assert GOAL_REGION in kept`. The "always" was true only because compute_kept
        # force-kept GOAL_REGION under `auto` so the goal DERIVATION was guaranteed a terminus.
        # SPEC-ashen-capital-lock (2026-08-06) deleted that force-keep -- the goal is the Ashen
        # Capital now, reached from the HUB behind an item, and `num_regions: 1` has to be able to
        # keep ONE region. So the capital enters the kept set by exactly two routes, and the
        # CLOSURE claim (which is what this test is about) is asserted on both.
        assert parent_chain(GOAL_REGION), (
            "this test needs the goal region to HAVE a parent chain; if REGION_PARENT ever drops "
            "it, re-point the test at a child that still has one rather than letting it go vacuous")
        # route 1: an explicit `goal` forces it (features/goal_locations.forced_regions)
        kept = compute_kept(1, random.Random(2), base_regions(), forced=(GOAL_REGION,))
        assert GOAL_REGION in kept
        for anc in parent_chain(GOAL_REGION):
            assert anc in kept
        # route 2: the draw happens to take it -- and, the other half of the same fact, sometimes
        # it does NOT. A force-keep creeping back in would make `drew_it` 200 and red this.
        drew_it = 0
        for s in range(200):
            k = compute_kept(1, random.Random(s), base_regions())
            if GOAL_REGION in k:
                drew_it += 1
                for anc in parent_chain(GOAL_REGION):
                    assert anc in k, f"drawn goal region without ancestor {anc}: {k}"
        assert drew_it, "no n=1 draw in 200 seeds took the goal region -- route 2 went vacuous"
        assert drew_it < 200, (
            "EVERY n=1 draw kept the goal region: the `auto` force-keep is back, and with it "
            "bobler's 'num_regions: 1 gave me four regions'")

    def test_child_eligible_without_parent_is_a_hard_error(self):
        # An eligible pool that contains a gated child but not its parent is a scope-filter bug;
        # compute_kept must refuse loudly, never hand back an unreachable kept set -- on EVERY
        # path, including the n >= len(pool) full-pool return.
        rng = random.Random(3)
        with pytest.raises(ValueError):
            compute_kept(1, rng, ["Raya Lucaria Academy"])


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
        kept = ["Leyndell", "Altus", "Raya Lucaria Academy", "Liurnia"]
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


# ---- 2 + 4b. a live seed: bundles granted, logic parented, fill never strands -------------------
class GatedChildrenLiveSeed(WorldTestBase):
    game = GAME
    run_default_tests = False
    # all base regions kept (num_regions 0, DLC off default). No wall is armed on any seed now,
    # so every kept child's bundle rides its Lock.
    options = {"num_regions": 0}

    def _sd(self):
        return self.world.fill_slot_data()

    def test_no_child_bundle_withheld_others_granted(self):
        rg = self._sd()["regionGraces"]
        kept = set(self.world._kept())
        # Pin the base pair by name so a rename can't quietly empty the loop. (Scaduview folded
        # into Shadow Keep 2026-07-19; the Sewer folded into Leyndell 2026-08-20 -- each has its
        # own FoldedInto seed class below asserting the post-fold state.)
        assert {"Raya Lucaria Academy", "Leyndell"} <= kept & set(REGION_PARENT)
        # 🛑 RAYA GRANTS SINCE 2026-08-16 (#740), LEYNDELL SINCE 2026-09-14 (rune-wall
        # retirement). Both stay in REGION_PARENT -- the structural containment and the synthetic
        # 7698x open flag are unchanged -- so this loop has to name the granted state per child
        # rather than iterate blindly: an unpaired child withholds UNCONDITIONALLY, and "the
        # bundle is empty again" is a real regression either line must catch.
        for child in REGION_PARENT:
            if child not in kept:
                continue
            self.assertEqual(rg.get(f"{child} Lock"), list(REGION_GRACE_POINTS[child]),
                             f"{child}'s bundle must ride its Lock in full -- no wall is armed")
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
        # (The Sewer case folded into the Leyndell row 2026-08-20: its m35 checks ARE Leyndell
        # checks now, so the first case covers them by construction.)
        cases = [("Leyndell", "Altus Lock", ["Leyndell"]),
                 ("Raya Lucaria Academy", "Liurnia Lock", ["Raya Lucaria Academy"])]
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


    # ---- 5. the open flag must not BE a grace (#278) ---------------------------------------------
    def test_gated_child_open_flag_is_never_a_grace_flag(self):
        """The regression. Stated over EVERY grace flag in the seed, not just the child's own
        bundle: a warp target anywhere is a warp target, and pinning only the three known values
        would pass the day someone re-derives a fourth child onto a different grace."""
        all_graces = {f for fs in REGION_GRACE_POINTS.values() for f in fs}
        sd = self._sd()
        open_flags = sd["regionOpenFlags"]
        kept = set(self.world._kept())
        checked = 0
        for child in REGION_PARENT:
            if child not in kept:
                continue
            key = f"{child} Lock"
            flag = open_flags.get(key)
            assert flag is not None, f"{key} must ship an open flag (coarse_keys requires it)"
            assert flag not in all_graces, (
                f"{child}'s open flag {flag} IS a grace flag -- `open_on_received_name` sets it on "
                f"Lock receipt, so receiving the Lock lights a warp target on the far side of the "
                f"wall and the granted bundle is bypassed (#278)")
            checked += 1
        # 3 -> 2 (2026-08-20): the Sewer merged into Leyndell, so the base gated children are a
        # PAIR now (Leyndell + Raya Lucaria Academy). The witness still refuses zero/one.
        assert checked >= 2, f"expected the base pair at least, checked {checked}"

    def test_area_lock_ranges_use_that_same_non_grace_flag(self):
        """The kick must latch on the SAME synthetic bit. If areaLockFlags kept the grace id, the
        kick would still be watching a flag the Lock no longer sets -- sealed forever."""
        all_graces = {f for fs in REGION_GRACE_POINTS.values() for f in fs}
        sd = self._sd()
        triples = sd.get("areaLockFlags") or []
        kept = set(self.world._kept())
        for child in REGION_PARENT:
            if child not in kept:
                continue
            want = sd["regionOpenFlags"][f"{child} Lock"]
            pids = set(REGION_PLAY_IDS.get(child, ()))
            assert pids, f"{child} has no play-region geometry -- kick-watch would be silently off"
            covering = [t for t in triples if t[0] in pids or t[1] in pids]
            assert covering, f"{child}: no areaLockFlags range covers {sorted(pids)[:4]}"
            for t in covering:
                assert t[2] == want, (
                    f"{child}: areaLockFlags range {t} latches on {t[2]} but the Lock sets {want} "
                    f"-- the kick would never disarm")
                assert t[2] not in all_graces, f"{child}: kick range {t} latches on a grace flag"


class TestGatedChildFlagBand:
    """Static pin on the synthetic ids. No world build -- this is about the ALLOCATION, which is the
    part we cannot verify from here: an unallocated flag silently no-ops, and here that fails in the
    STRANDING direction (Lock received, kick never disarms). The band is the evidence we have --
    coverage.REGION_FLAG_LO/HI make 71000-76999 valid, and inside it the baked-era reactors on 76970
    (KICK) and 76996 (deathlink) demonstrably fired, which is why [76970, 76996] is where a new
    client-owned flag goes. 🛑 The band is not a probe; each id still needs one in game (#278)."""
    LO, HI = 76970, 76999
    RESERVED = {76970, 76996, 76971, 76972}   # KICK, deathlink, er-logic test fixtures

    def _synthetic(self):
        return {c: REGION_OPEN_FLAGS[c] for c in REGION_PARENT if c in REGION_OPEN_FLAGS}

    def test_every_gated_child_flag_sits_in_the_probed_band(self):
        for child, flag in self._synthetic().items():
            assert self.LO <= flag <= self.HI, (
                f"{child}'s open flag {flag} is outside the client-owned band "
                f"[{self.LO}, {self.HI}] -- either it is still a grace id, or it is an id nobody "
                f"has evidence the game allocates")

    def test_flags_are_distinct_and_avoid_reserved_ids(self):
        flags = list(self._synthetic().values())
        assert len(flags) == len(set(flags)), f"gated children share an open flag: {flags}"
        clash = sorted(set(flags) & self.RESERVED)
        assert not clash, f"gated-child open flag(s) collide with reserved ids: {clash}"


class ScaduviewFoldedIntoKeep(WorldTestBase):
    """Scaduview (the Hinterland) FOLDED into Shadow Keep 2026-07-19 (Alaric). As its own region it
    held no self-contained content -- Commander Gaius + his five-fragment reward, the Scadutree Avatar,
    one Finger Ruins -- every one entered THROUGH the Keep, so a standalone Scaduview Lock only
    STRANDED Gaius/Avatar behind a second gate a Scaduview-lock-only player could never open. After
    the fold they are Shadow Keep checks under the Keep's OWN Lock. This seed pins the fold on an
    enable_dlc world: (a) Scaduview is gone as a region, (b) the former-Scaduview checks live in
    Shadow Keep, and (c) they are gated by the Shadow Keep Lock (necessary-direction: removing it
    makes them unreachable -- the containment guarantee, now direct instead of transitive)."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "enable_dlc": True}

    # Stable event flags of former-Scaduview checks (survive ap-id renumbering): Gaius + Scadutree
    # Avatar remembrances, the Hinterland fragments, Sharpshot Talisman, the Finger Ruins.
    _FOLDED_FLAGS = ("[f510620]", "[f510640]", "[f2049487000]", "[f2049497500]", "[f2049497510]",
                     "[f2049497550]", "[f60861]")

    def test_scaduview_folded_into_shadow_keep(self):
        rg = self.world.fill_slot_data()["regionGraces"]
        assert "Scaduview Lock" not in rg, (
            f"Scaduview folded into Shadow Keep -- no Scaduview Lock expected, got "
            f"{rg.get('Scaduview Lock')}")
        # its grace bundle rides Shadow Keep now (not withheld -- the Keep is not a gated child).
        assert rg.get("Shadow Keep Lock") == list(REGION_GRACE_POINTS["Shadow Keep"]), (
            "Shadow Keep's own bundle (incl. the folded Hinterland graces) must stay granted")
        # region half: every former-Scaduview check is a Shadow Keep check now.
        folded = [l for l in self.multiworld.get_locations(self.player)
                  if any(f in l.name for f in self._FOLDED_FLAGS)]
        assert folded, "no former-Scaduview checks found on an enable_dlc seed"
        for l in folded:
            assert l.parent_region is not None and l.parent_region.name == "Shadow Keep", (
                f"{l.name} should be a Shadow Keep check after the fold, got "
                f"{l.parent_region.name if l.parent_region else None}")
        # logic half (necessary direction, robust to any extra per-check gating): a full state minus
        # every Shadow Keep Lock copy reaches NONE of them (remove-all-copies per test_gf_ending --
        # the withheld Lock may be the precollected anchor).
        st = self.multiworld.get_all_state(False)
        copies = [it for it in world_items(self) if it.name == "Shadow Keep Lock"]
        assert copies, "Shadow Keep Lock missing from the created items"
        for it in copies:
            st.remove(it)
        for l in folded:
            assert not l.can_reach(st), (
                f"{l.name} reachable WITHOUT Shadow Keep Lock -- the fold broke Keep gating")


class SewerFoldedIntoLeyndell(WorldTestBase):
    """The Sewer (Subterranean Shunning-Grounds, m35) MERGED into Leyndell 2026-08-20 (Alaric's
    audible on #917/#842). The well is inside the capital walls: one region, one wall. Mirrors
    ScaduviewFoldedIntoKeep above: (a) Sewer is gone as a region, (b) former-Sewer checks live in
    Leyndell, (c) the Leyndell Lock gates them (necessary direction), (d) the m35 graces ride
    Leyndell's bundle -- granted on the Lock since the 2026-09-14 rune-wall retirement."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    _FOLDED_FLAGS = ("[f510250]", "[f35007000]", "[f35007010]", "[f35007030]")

    def test_sewer_folded_into_leyndell(self):
        sd = self.world.fill_slot_data()
        rg = sd["regionGraces"]
        assert "Sewer Lock" not in rg and "Sewer Lock" not in sd["regionOpenFlags"]
        assert "Sewer" not in REGION_PARENT
        for f in (73501, 73502, 73503, 73504):
            assert f in REGION_GRACE_POINTS["Leyndell"], (
                f"m35 grace {f} missing from Leyndell's bundle post-merge")
        folded = [l for l in self.multiworld.get_locations(self.player)
                  if any(f in l.name for f in self._FOLDED_FLAGS)]
        assert folded, "no former-Sewer checks found"
        for l in folded:
            assert l.parent_region is not None and l.parent_region.name == "Leyndell", (
                f"{l.name} should be a Leyndell check after the merge, got "
                f"{l.parent_region.name if l.parent_region else None}")
        st = self.multiworld.get_all_state(False)
        copies = [it for it in world_items(self) if it.name == "Leyndell Lock"]
        assert copies, "Leyndell Lock missing from the created items"
        for it in copies:
            st.remove(it)
        for l in folded:
            assert not l.can_reach(st), (
                f"{l.name} reachable WITHOUT the Leyndell Lock -- the merge broke capital gating")


class TestDeprecatedLeyndellOptionAccepted(WorldTestBase):
    """`leyndell_runes_required` is a deprecated no-op since 2026-09-14: every value parses, every
    value is ignored, the capital opens on its Lock regardless. Old YAMLs must still generate --
    Archipelago warns on an UNKNOWN key and generates without it, but this key is still KNOWN, so
    a yaml carrying it generates exactly as one without it. Both spellings below must generate
    clean and grant the capital bundle; the :4 seed is the sharp one (under the old wall it armed
    a four-rune wall and withheld the bundle)."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "leyndell_runes_required": 0}

    def test_zero_still_generates_and_grants(self):
        rg = self.world.fill_slot_data()["regionGraces"]
        assert rg.get("Leyndell Lock") == list(REGION_GRACE_POINTS["Leyndell"])


class TestDeprecatedLeyndellOptionNonDefaultIgnored(WorldTestBase):
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0, "leyndell_runes_required": 4}

    def test_four_is_ignored_and_grants(self):
        # Under the retired wall this armed at four runes and withheld the bundle. Now it must
        # read exactly like the default: granted, beatable, no OptionError at gen (WorldTestBase
        # reaching this line IS the no-OptionError proof -- an incompatible combination dies in
        # generate_early, before any test runs).
        rg = self.world.fill_slot_data()["regionGraces"]
        assert rg.get("Leyndell Lock") == list(REGION_GRACE_POINTS["Leyndell"])
        assert self.multiworld.can_beat_game(), "deprecated-option seed must stay beatable"


class TestLeyndellLockOnly(WorldTestBase):
    """Leyndell is an ordinary Lock region (2026-09-14): the Lock is the ONLY gate, in logic and
    on the wire. Two halves, both asserted here because they are one ruling:

    (a) the regionGraces bundle is non-empty -- the full capital bundle, m35 graces included;
    (b) a seed with Leyndell kept and ZERO Great Runes reachable is still beatable under logic --
        no rune in hand, no rune needed. (Under `ending_condition: great_runes` runes ARE needed,
        by design: that goal counts them. This class runs the default region_locks ending, where
        nothing may ask for a rune.)
    (c) the seal-open rides the Lock on the wire: lockRevealFlags["Leyndell Lock"] carries the
        measured seal pair 105+182 (the flags m60_45_52_00 $Event(1045522500) reads), so the
        client opens the physical seal on the same receipt that lights the bundle."""
    game = GAME
    run_default_tests = False
    options = {"num_regions": 0}

    def test_leyndell_lock_bundle_is_the_full_capital_bundle(self):
        rg = self.world.fill_slot_data()["regionGraces"]
        bundle = rg.get("Leyndell Lock")
        assert bundle, "the Leyndell Lock must light its graces -- an empty bundle strands the warp"
        assert bundle == list(REGION_GRACE_POINTS["Leyndell"]), (
            "the bundle must be the whole capital bundle (m35 Shunning-Grounds graces included)")
        assert 73501 in bundle, "the merged m35 graces left the bundle?!"

    def test_seal_flags_ride_the_leyndell_lock(self):
        reveal = self.world.fill_slot_data().get("lockRevealFlags", {})
        assert reveal.get("Leyndell Lock") == [105, 182], (
            f"lockRevealFlags['Leyndell Lock'] must carry the measured seal pair, got "
            f"{reveal.get('Leyndell Lock')} -- the client opens the physical two-rune seal on "
            f"this receipt (world half; the client half is a separate PR)")

    def test_zero_runes_reachable_seed_still_beatable(self):
        # A full state (everything, including the anchor precollect) minus every copy of every
        # Great Rune: Leyndell's checks must stay reachable -- no rune in hand, no rune needed.
        # The remove-all-copies pattern (per test_gf_ending) is what makes this seed-robust.
        from worlds.eldenring.item_categories import GREAT_RUNES as _ALL_RUNES
        st = self.multiworld.get_all_state(False)
        rune_names = set(_ALL_RUNES)
        copies = [it for it in world_items(self) if it.name in rune_names]
        assert copies, "no Great Rune copies in the created items -- the test would prove nothing"
        for it in copies:
            st.remove(it)
        locs = [l for l in self.multiworld.get_locations(self.player)
                if getattr(getattr(l, "parent_region", None), "name", None) == "Leyndell"]
        assert len(locs) >= 8, f"suspiciously few Leyndell locations ({len(locs)})"
        for l in locs[:8]:
            assert l.can_reach(st), (
                f"{l.name} unreachable with zero Great Runes held -- a rune is gating the "
                f"capital again")
        # And the whole seed stays beatable on a rune-less sweep: Great Runes are `useful`, never
        # `advancement`, under the default region_locks ending -- so sweep_for_advancements from
        # an empty state never collects one, and every progression item it reaches is reached
        # with zero runes. (Under `ending_condition: great_runes` runes ARE needed, by design:
        # that goal counts them. This class runs the default ending, where nothing may ask for
        # a rune.)
        state = CollectionState(self.multiworld)
        state.sweep_for_advancements()
        for l in self.multiworld.get_locations(self.player):
            if l.item is not None and l.item.advancement:
                assert state.can_reach(l), (
                    f"progression {l.item.name} stranded on unreachable {l.name} in a seed "
                    f"whose sweep never held a Great Rune")
