"""Regression guard: completion-scaling targets must be the ORDER RAMP over the TRUE per-seed FILL
SPHERES -- a total topological linearization of the lock chain -- not the static region_spine.SPINE
order, and not the old raw-sphere tiers.

The live scaling wire (slot_data regionSphereTargetRanges, features/scaling.py) linearizes the fill
spheres (the sphere each region's `<Region> Lock` is actually obtained in) into a TOTAL order --
sphere ascending, seed-deterministic random tie-breaks among same-sphere regions -- and ramps the
target evenly over ORDER POSITION. Why (Alaric playtest 2026-07-15, "felt easy... spent most time in
sphere 1-2"): the lock DAG is wide early, so raw-sphere tiers parked most of the map at the sphere-1/2
target; the order ramp spreads same-sphere regions across distinct tiers while never scaling a region
above its reachability (sphere-primary sort).

Guarded here, per seed on a REAL post-fill rolled world:
  * the fill spheres are non-empty (a silent revert to SPINE order is the historical regression);
  * the wire equals the order-ramp pipeline exactly (order -> position targets -> ranges);
  * the order is a valid TOPOLOGICAL sort: walking regions by ascending target never visits a region
    whose lock sphere is below a predecessor's (no region before its prerequisites);
  * same-sphere regions DIVERGE: whenever a sphere holds >= 2 regions, their targets differ (the old
    model gave them identical targets -- that is the "felt easy" bug);
  * DETERMINISM: rebuilding the same seed gives the byte-identical wire (the tie-break RNG is keyed
    on (multiworld.seed, player), not the shared world.random stream);
  * across the seed sweep, at least one ordering diverges from SPINE (proving reachability-driven).

WorldTestBase.setUp runs gen_steps only (through pre_fill), NOT the main item fill, so the test
distributes items explicitly to reach a real post-fill state before inspecting the spheres.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features import scaling as sc  # noqa: E402
from worlds.eldenring.region_spine import SPINE  # noqa: E402

GAME = "Elden Ring"
_SEEDS = (1, 2, 3, 4, 5)


def _tuples(ranges):
    return sorted(tuple(t) for t in ranges)


def test_blessing_floor_producer_stays_alive_though_off_by_default():
    # global_scadutree_blessing is frozen OFF (defaults.py, 2026-07-18) so NO default seed emits
    # dlcScadutreeFloorRanges -- but the `scaled` option value and the pure producer are RETAINED.
    # This proves the producer still works, so dlcScadutreeFloorRanges in
    # test_gf_slot_data_fixture._CONTRACT_NOT_EMITTED is a JUSTIFIED not-emitted key, not a rotted
    # one: a kept DLC region yields a [lo, hi, floor] triple per play_region bucket, and a base-game
    # seed yields nothing (inert).
    from worlds.eldenring.region_spine import DLC_REGIONS
    floors = sc.blessing_floor_ranges(sorted(DLC_REGIONS))
    assert floors, "blessing_floor_ranges must still emit floors for kept DLC regions"
    assert all(len(t) == 3 for t in floors), "each floor is a [lo, hi, floor] triple"
    assert sc.blessing_floor_ranges(["Limgrave", "Liurnia"]) == [], "no DLC kept -> no floors (inert)"


def test_dlc_buckets_are_derived_from_the_region_set_not_the_blessing_option():
    """THE BUG (2026-07-27): the client's only 'is this a DLC region?' test was
    `blessing_floor_for_region(&cfg.dlc_blessing_floors, r).is_some()` -- and those floors are
    emitted ONLY when global_scadutree_blessing == 2, which has NOT been the default since
    2026-07-18. So on every default seed the DLC flag was `false` for every bucket in the game.
    Nothing failed, because it only shortened a log line.

    `dlcRegionBuckets` answers the question the question was actually about. Gated here so it can
    never drift back into depending on an option: the bucket set must be identical whatever
    global_scadutree_blessing says, and it must be non-empty exactly when a DLC region is kept.
    """
    from worlds.eldenring.region_spine import DLC_REGIONS

    dlc = sorted(DLC_REGIONS)
    buckets = sc.dlc_region_buckets(dlc)
    assert buckets, "kept DLC regions must yield buckets"
    assert buckets == sorted(set(buckets)), "sorted and de-duplicated"
    assert all(isinstance(b, int) for b in buckets)

    # Base-game-only kept set -> empty (inert; the key is not emitted at all).
    assert sc.dlc_region_buckets(["Limgrave", "Liurnia"]) == []

    # The DLC buckets and the blessing floors describe the SAME regions, but the floors are the ones
    # that vanish with an option. Same bucket universe, different emission conditions.
    floor_buckets = sorted({lo for lo, _hi, _f in sc.blessing_floor_ranges(dlc)})
    assert floor_buckets == buckets, (
        "the blessing floors and the DLC bucket wire disagree about which buckets are DLC -- one of "
        "them is wrong, and only the bucket wire is emitted unconditionally")


def test_the_kick_exempt_combat_buckets_are_on_the_scaling_wire():
    """#688 (bobler playtest 2026-08-15) -- THE MOTIVATING CASE, as a test.

    Buckets 18000 (m18_00: Stranded Graveyard cliff + Fringefolk Hero's Grave, 12 Limgrave checks,
    Ulcerated Tree Spirit 18000800 and Soldier of Godrick 18000850) and 10010 (m10_01, the Chapel
    intro and the Grafted Scion) are KICK-exempt on purpose -- kicking a player out of the intro
    crashed the game. Scaling borrowed the kick's table, so those two buckets never reached
    regionSphereTargetRanges either, and an unwired bucket takes the client's FLOOR tier
    (completion_scaling_floor is frozen at 0) -- i.e. it ships VANILLA. In bobler's tier-0 seed the
    same npc_id 4910 read 7,141 HP in bucket 18000 against 3,386 HP in a wired region: 2.109x,
    exactly SCALING_HP_LADDER[6]/SCALING_HP_LADDER[0]. A bucket-18000 boss read 31,518 HP while the
    largest boss in any wired region read 6,564.

    AND THE HUB, 11100 -- the half the first fix got wrong. It was left off the wire as "the
    Roundtable has no combat"; bobler, the same day: "this npc fight was almost harder than every
    boss in the run bc roundtable was unscaled". Ensha invades the hub, and BOSS_HEALTHBARS has no
    11100 entry because an NPC invader carries no healthbar -- so the boss probe could not have seen
    that fight and its silence was never evidence. The hub is in EVERY seed and holds 239 checks.

    Pure: the wire producer, not a rolled seed, so the failure names the geometry and not the fill.
    """
    wire = sc.sphere_target_ranges(["Limgrave", "Stormveil"])
    at = {lo: t for lo, _hi, t in wire}
    assert at, "precondition: the wire is non-empty"
    assert 18000 in at, (
        "bucket 18000 (Fringefolk Hero's Grave / Stranded Graveyard) is absent from the scaling "
        "wire, so the client leaves it VANILLA -- 2.109x the HP of the same enemy in a wired "
        "region. Kick-exempt is not scaling-exempt (region_groups.SCALING_FLOOR_PLAY_IDS).")
    assert 10010 in at, (
        "bucket 10010 (Chapel of Anticipation intro) is absent from the scaling wire -- see #688.")
    assert 11100 in at, (
        "bucket 11100 (Roundtable Hold) is absent from the scaling wire, so the hub -- the one "
        "place every seed sends you and where Ensha invades -- ships at vanilla difficulty. "
        "'No combat there' was the reasoning and it is false (#688).")
    for pid in (11100, 18000, 10010):
        assert at[pid] == 0, (
            "bucket %d is on the wire at target %d; it is pinned to the FLOOR of the ramp (0) so "
            "that ground reachable turn one can never outpace the player." % (pid, at[pid]))


def test_intra_fold_scaling_delta_bumps_clamps_and_never_inflates(monkeypatch):
    # Pure mechanism test (SPEC-intra-fold-scaling-delta-20260722.md). Uses a CONTROLLED delta so it
    # is robust to future tuning of the shipped _SCALING_BUCKET_DELTA values. Synthetic wire: three
    # regions at targets 0 / 5000 / 10000; region-mid has a folded sub-bucket (999) at its base.
    triples = [[100, 100, 0], [500, 500, 5000], [999, 999, 5000], [900, 900, 10000]]

    monkeypatch.setattr(sc, "_SCALING_BUCKET_DELTA", {999: 2500})
    out = {lo: t for lo, _, t in sc._apply_bucket_delta([list(t) for t in triples])}
    assert out[999] > 5000, "folded bucket must bump above its region base"
    assert out[999] < 10000, "bump must stay STRICTLY below the next region (no sphere-jump)"
    assert out[500] == 5000, "a non-fold bucket in the same region is unchanged"
    assert max(out.values()) == 10000, "delta must not inflate the client-normalized max"

    # a delta on the TOP-target bucket must be a no-op, never a lowering
    monkeypatch.setattr(sc, "_SCALING_BUCKET_DELTA", {900: 2500})
    out2 = {lo: t for lo, _, t in sc._apply_bucket_delta([list(t) for t in triples])}
    assert out2[900] == 10000, "delta on the top region must not lower the bucket"

    # empty delta == identity
    monkeypatch.setattr(sc, "_SCALING_BUCKET_DELTA", {})
    assert sc._apply_bucket_delta([list(t) for t in triples]) == triples


def _region_targets(world, wire):
    """region -> emitted target, resolved through the play_region buckets."""
    pid_t = {lo: t for lo, _hi, t in wire}
    return {r: max((pid_t.get(p, 0) for p in sc.SCALING_PLAY_IDS.get(r, [])), default=0)
            for r in world._kept()}


class SphereScalingRolled(WorldTestBase):
    game = GAME
    # rolled + a mid num_regions so the kept set is a random (non-prefix) slice -> fill order and
    # SPINE order genuinely differ, which is exactly the property under test.
    options = {"num_regions": 6}

    def _fill(self, seed):
        from Fill import distribute_items_restrictive
        self.world_setup(seed)               # fresh multiworld through pre_fill
        distribute_items_restrictive(self.multiworld)   # the main fill -> spheres become real
        return self.world

    def test_wire_is_the_topological_order_ramp(self):
        any_diverged_from_spine = False
        any_same_sphere_pair = False
        for seed in _SEEDS:
            world = self._fill(seed)
            kept = world._kept()

            region_sphere = sc._region_fill_spheres(world)
            self.assertTrue(
                region_sphere,
                f"seed={seed}: _region_fill_spheres() is empty on a filled world -> the scaling wire "
                f"silently fell back to SPINE order (regression).")

            # The slot_data wire must be exactly the order-ramp pipeline, end to end.
            # 2026-08-10: the FINALE is appended to the order (features/scaling._finale_for_wire).
            # It is NOT in _kept() and NOT in SPINE -- it is never rolled -- so the pipeline this
            # test mirrors has to append it too, or the mirror asserts a wire we deliberately stopped
            # emitting. Its position is a design fact, not a fill result: it ends the run.
            order = sc._order_from_spheres(region_sphere, sc._order_rng(world))
            _finale = sc._finale_for_wire(world)
            self.assertIsNotNone(
                _finale,
                f"seed={seed}: a base-game seed built no finale, so the appended-tail branch is "
                f"untested here (an oracle that measures nothing is a lie).")
            expected = sc._ranges_from_targets(sc._targets_from_order(order + [_finale]))
            wire = world.fill_slot_data()[contract.REGION_SPHERE_TARGET_RANGES]
            self.assertEqual(
                _tuples(wire), _tuples(expected),
                f"seed={seed}: regionSphereTargetRanges is not the fill-sphere ORDER-RAMP wire.")

            region_t = _region_targets(world, wire)

            # TOPOLOGICAL VALIDITY: ascending target must never descend in sphere -- a region may not
            # scale above (sort after) a region it is a prerequisite of.
            by_target = sorted(region_t, key=lambda r: (region_t[r], r))
            for a, b in zip(by_target, by_target[1:]):
                self.assertLessEqual(
                    region_sphere[a], region_sphere[b],
                    f"seed={seed}: order ramp is not a topological sort -- {a!r} (sphere "
                    f"{region_sphere[a]}, target {region_t[a]}) precedes {b!r} (sphere "
                    f"{region_sphere[b]}, target {region_t[b]}).")

            # SAME-SPHERE DIVERGENCE: regions sharing a sphere must NOT share a target (the old
            # raw-sphere model's exact failure). Every same-sphere pair must differ.
            spheres = {}
            for r in kept:
                spheres.setdefault(region_sphere[r], []).append(r)
            for s_val, regs in spheres.items():
                if len(regs) < 2:
                    continue
                any_same_sphere_pair = True
                targets = [region_t[r] for r in regs]
                self.assertEqual(
                    len(targets), len(set(targets)),
                    f"seed={seed}: same-sphere regions share a target (sphere {s_val}: "
                    f"{sorted((r, region_t[r]) for r in regs)}) -- the order ramp regressed to "
                    f"raw-sphere tiers.")

            # DETERMINISM: rebuild the identical seed -> byte-identical wire.
            world2 = self._fill(seed)
            wire2 = world2.fill_slot_data()[contract.REGION_SPHERE_TARGET_RANGES]
            self.assertEqual(
                _tuples(wire), _tuples(wire2),
                f"seed={seed}: the scaling wire is not deterministic per seed (tie-break RNG leaked "
                f"shared state?).")

            # Divergence check vs static geography (any seed suffices across the sweep).
            spine_order = [r for r in SPINE if r in set(kept)]
            if by_target != spine_order:
                any_diverged_from_spine = True

        self.assertTrue(
            any_same_sphere_pair,
            "no rolled seed produced a sphere holding >= 2 regions -- the divergence assertion never "
            "ran; widen the seed sweep (an oracle that measures nothing is a lie).")
        self.assertTrue(
            any_diverged_from_spine,
            "no rolled seed produced an order that diverged from SPINE order -- the test is not "
            "actually exercising reachability-driven scaling (or scaling reverted to spine).")


class DlcOffSeed(WorldTestBase):
    """enable_dlc = False -- the DLC scaling wires must be ABSENT, not present-and-empty.

    `dlcRegionBuckets` is gated on the KEPT REGION SET intersecting the DLC regions
    (features/scaling.py), not on an option read -- which is exactly the gate shape a per-option
    audit misses. Off-state coverage added with the 2026-08-04 "off means off" sweep (audit
    finding P1 generalized); paired in test_gf_off_means_off.OFF_LEDGER."""
    game = GAME
    options = {"num_regions": 0, "enable_dlc": False}

    def test_dlc_buckets_absent_without_dlc(self):
        sd = self.world.fill_slot_data()
        leaked = [k for k in ("dlcRegionBuckets", "dlcScadutreeFloorRanges") if k in sd]
        assert leaked == [], (
            "DLC scaling wires %r emitted on a no-DLC seed: the client would carry scaling "
            "buckets/floors for play regions this seed can never enter -- the kept-region gate "
            "in features/scaling.py is not doing its job" % (leaked,))


# ---------------------------------------------------------------------------------------------
# THE FINALE MUST BE ON THE WIRE (2026-08-10, bobler playtest -- "ashen and roundtable seems to be
# untouched"). The Ashen Capital is never ROLLED (gen_data: "LOCATIONS[FINALE_REGION] is NOT in
# REGIONS"), so it is not in world._kept() and not in SPINE -- and EVERY scaling path keys on one of
# those two. Its geometry has always existed (region_play_ids: 'Ashen Capital': [11050, 19000]) and
# area_locks special-cases it explicitly (core.py, features/area_locks.py `gf_finale_active`), so
# region LOCKS worked while SCALING silently skipped the entire endgame -- including play_region
# 19000, the Elden Throne, where the goal fight happens.
#
# Evidence this is written against: across all 7 seeds in bobler's 08-10/08-11 client logs,
# `regionSphereTargetRanges` contained 11050 or 19000 ZERO times, and the client logged
# "region 11050 is not in the sphere wire -- left VANILLA (no tier, no down-state)" nine times.
# The client's degrade for an unwired bucket is the FLOOR tier and an INFO line, so this could only
# ever be caught here.
_FINALE_REGION = "Ashen Capital"


class FinaleIsOnTheScalingWire(WorldTestBase):
    """num_regions=1 -- the exact shape of bobler's 08-11 seed (`region_count = 1`), which is also
    the degenerate case: one rolled region plus the always-locked finale. Before the fix this seed
    emitted five buckets, all Mt. Gelmir, all target 0, and nothing for the capital at all."""
    game = GAME
    options = {"num_regions": 1, "enable_dlc": False}

    def test_finale_buckets_are_wired_and_deepest(self):
        world = self.world
        self.assertTrue(
            getattr(world, "gf_finale_active", False),
            "precondition: this seed has no finale, so it cannot test the finale wire.")

        wire = world.fill_slot_data()[contract.REGION_SPHERE_TARGET_RANGES]
        by_pid = {lo: t for lo, _hi, t in wire}

        owed = sc.SCALING_PLAY_IDS[_FINALE_REGION]
        self.assertEqual(
            [p for p in owed if p not in by_pid], [],
            f"the finale's play_region buckets {owed} are absent from regionSphereTargetRanges "
            f"-- the Ashen Capital and the Elden Throne run VANILLA, with the down-state off. "
            f"wire={sorted(by_pid)}")

        # ...and it is the HARDEST thing in the seed: the finale ends the run, so nothing may
        # out-scale it. (Alaric, 2026-08-10: "yeah its last region by default now".)
        top = max(by_pid.values())
        for pid in owed:
            self.assertEqual(
                by_pid[pid], top,
                f"finale bucket {pid} is at target {by_pid[pid]} but the seed's deepest target is "
                f"{top} -- the endgame is scaled below a region you clear before it.")


class FinaleWireCoverageAcrossSeeds(WorldTestBase):
    """Same claim on a rolled mid-size draw, so the guard is not pinned to the degenerate seed."""
    game = GAME
    options = {"num_regions": 6}

    def test_every_reachable_region_has_every_bucket_wired(self):
        from Fill import distribute_items_restrictive
        saw_finale = False
        for seed in _SEEDS:
            self.world_setup(seed)
            distribute_items_restrictive(self.multiworld)
            world = self.world
            wire = world.fill_slot_data()[contract.REGION_SPHERE_TARGET_RANGES]
            wired = {lo for lo, _hi, _t in wire}

            owed = list(world._kept())
            if getattr(world, "gf_finale_active", False):
                owed.append(_FINALE_REGION)
                saw_finale = True

            # WITNESS (test_gf_vacuous_pass shape 2): "nothing is missing" is also what an empty
            # wire and an empty owed-set say, and both are exactly how this regression would come
            # back. Say out loud that the scan saw something.
            self.assertTrue(wired, f"seed={seed}: the scaling wire is EMPTY.")
            self.assertTrue(owed, f"seed={seed}: no regions in play to check.")

            missing = {r: [p for p in sc.SCALING_PLAY_IDS.get(r, []) if p not in wired]
                       for r in owed}
            missing = {r: p for r, p in missing.items() if p}
            self.assertEqual(
                missing, {},
                f"seed={seed}: region(s) the player can stand in have buckets that never reach "
                f"the scaling wire, so the client leaves them VANILLA: {missing}")

        self.assertTrue(
            saw_finale,
            "no seed in the sweep built a finale, so the branch this guard exists for never ran -- "
            "the coverage assertion passed without ever looking at the Ashen Capital.")


# ---------------------------------------------------------------------------------------------
# THE FLOOR PINS (2026-08-15, Alaric's ruling on bobler's Roundtable report; #688).
#
# 11100 (hub), 18000 (Stranded Graveyard cliff / Fringefolk Hero's Grave) and 10010 (the Chapel
# intro) take the LOWEST scaling in the run -- emitted target 0 -- in EVERY seed. Not their host
# region's tier: 18000 rides Limgrave and 10010 rides Stormveil in PLAY_REGION_GROUPS, and
# _order_from_spheres linearises the lock chain with a seed-deterministic tie-break, so those
# regions sit wherever the fill puts them. Limgrave happened to be at target 0 in bobler's seed.
# That is a coincidence, and a coincidence is not a design.
#
# 🛑 THE CASE A ONE-SEED TEST MISSES is the one where the host region is NOT KEPT AT ALL -- then
# there is no order position to inherit even in principle, and the naive fix emits nothing. Both
# halves below cover it: the pure half by choosing kept sets without Limgrave/Stormveil, the world
# half by requiring the sweep to have SEEN such a draw.
# ---------------------------------------------------------------------------------------------
_PINS = (11100, 18000, 10010)


def test_the_floor_pinned_buckets_sit_at_target_zero_in_every_seed():
    """Pure, over kept-sets chosen to include the two cases the old design got wrong."""
    assert sorted(sc.SCALING_FLOOR_PLAY_IDS) == sorted(_PINS), (
        "SCALING_FLOOR_PLAY_IDS is %r; this guard names its members literally, so a change here is "
        "a change to the ruling and must be argued." % sorted(sc.SCALING_FLOOR_PLAY_IDS))

    cases = {
        "both hosts kept":     ["Limgrave", "Stormveil", "Liurnia", "Altus"],
        "NO Limgrave":         ["Stormveil", "Liurnia", "Caelid"],       # 18000's host is absent
        "NO Stormveil":        ["Limgrave", "Liurnia", "Altus"],         # 10010's host is absent
        "neither host kept":   ["Liurnia", "Caelid", "Altus"],
        "one region only":     ["Caelid"],
        "with the finale":     ["Liurnia", "Caelid"],
    }
    for label, kept in cases.items():
        finale = "Ashen Capital" if label == "with the finale" else None
        for ramp in (100, 50, 25):
            wire = sc.sphere_target_ranges(kept, ramp_pct=ramp, finale=finale)
            at = {lo: t for lo, _hi, t in wire}
            assert at, f"{label} @ ramp {ramp}: the wire is EMPTY"
            for pid in _PINS:
                assert pid in at, (
                    f"{label} @ ramp {ramp}: pinned bucket {pid} is absent from the wire, so the "
                    f"client leaves it VANILLA. A pin whose host region is not in the seed still "
                    f"has to be emitted -- that is the whole reason it is a pin.")
                assert at[pid] == 0, (
                    f"{label} @ ramp {ramp}: pinned bucket {pid} emitted at target {at[pid]}, not "
                    f"0. It must never inherit a host region's order position.")
            # THE TWO INVARIANTS THE PINS COULD HAVE BROKEN, checked rather than assumed:
            targets = [t for _lo, _hi, t in wire]
            assert min(targets) == 0, (
                f"{label} @ ramp {ramp}: the minimum emitted target is {min(targets)}, so the pins "
                f"are no longer the floor of the ramp.")
            ramped = [t for lo, _hi, t in wire if lo not in sc.SCALING_FLOOR_PLAY_IDS]
            assert ramped, f"{label} @ ramp {ramp}: no RAMPED buckets -- the wire is all pins"
            assert max(targets) == max(ramped), (
                f"{label} @ ramp {ramp}: the pins moved the maximum emitted target from "
                f"{max(ramped)} to {max(targets)}. The client normalizes by that maximum "
                f"(scaling.rs tier_for_target), so a pin must never touch it -- and 0 cannot.")


class FloorPinsAcrossRolledSeeds(WorldTestBase):
    """The same claim on REAL rolled worlds, through the LIVE order-ramp path.

    The pure test above exercises `sphere_target_ranges` (the SPINE-order fallback). Seeds normally
    take `_ranges_from_targets(_targets_from_order(...))` instead, which is a different producer
    over a different order, so it needs its own witness. `num_regions` is small on purpose: it makes
    a draw WITHOUT Limgrave or Stormveil the common case rather than a lucky one.
    """
    game = GAME
    options = {"num_regions": 3}

    def test_every_seed_pins_the_three_buckets_to_the_ramp_floor(self):
        from Fill import distribute_items_restrictive
        seeds = (11, 12, 13, 14, 15, 16, 17, 18)
        saw_without_limgrave = saw_without_stormveil = 0
        checked = 0
        for seed in seeds:
            self.world_setup(seed)
            distribute_items_restrictive(self.multiworld)
            world = self.world
            wire = world.fill_slot_data()[contract.REGION_SPHERE_TARGET_RANGES]
            at = {lo: t for lo, _hi, t in wire}
            kept = set(world._kept())
            self.assertTrue(at, f"seed={seed}: the scaling wire is EMPTY")
            saw_without_limgrave += "Limgrave" not in kept
            saw_without_stormveil += "Stormveil" not in kept
            checked += 1
            for pid in _PINS:
                self.assertIn(pid, at,
                              f"seed={seed} (kept={sorted(kept)}): pinned bucket {pid} never "
                              f"reached regionSphereTargetRanges -- the client leaves it VANILLA.")
                self.assertEqual(
                    at[pid], 0,
                    f"seed={seed} (kept={sorted(kept)}): pinned bucket {pid} emitted at target "
                    f"{at[pid]}. The hub, the tutorial cliff and the intro take the LOWEST scaling "
                    f"in the run, in every seed -- not their host region's order position.")
            targets = [t for _lo, _hi, t in wire]
            self.assertEqual(min(targets), 0, f"seed={seed}: 0 is not the minimum emitted target")
            ramped = [t for lo, _hi, t in wire if lo not in sc.SCALING_FLOOR_PLAY_IDS]
            self.assertTrue(ramped, f"seed={seed}: the wire is all pins and no ramp")
            self.assertEqual(
                max(targets), max(ramped),
                f"seed={seed}: the pins raised the maximum emitted target, which the client "
                f"normalizes by. 0 cannot do that, so something else is in the pin list.")

        # WITNESSES (test_gf_vacuous_pass shape 2). "Every seed passed" is also what zero seeds and
        # an empty wire say, and the specific draw this fix exists for is the one where the pinned
        # bucket's HOST REGION is not in the seed at all.
        self.assertEqual(checked, len(seeds), "the sweep did not run every seed")
        self.assertGreater(
            saw_without_limgrave, 0,
            "no seed in the sweep left Limgrave OUT, so bucket 18000's host region was present "
            "every time and the case the pin exists for never ran. Widen the sweep or drop "
            "num_regions.")
        self.assertGreater(
            saw_without_stormveil, 0,
            "no seed in the sweep left Stormveil OUT, so bucket 10010's host region was present "
            "every time and the case the pin exists for never ran. Widen the sweep or drop "
            "num_regions.")
