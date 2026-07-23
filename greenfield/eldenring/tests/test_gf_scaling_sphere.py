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
    return {r: max((pid_t.get(p, 0) for p in sc.REGION_PLAY_IDS.get(r, [])), default=0)
            for r in world._kept()}


class SphereScalingRolled(WorldTestBase):
    game = GAME
    # rolled + a mid num_regions so the kept set is a random (non-prefix) slice -> fill order and
    # SPINE order genuinely differ, which is exactly the property under test.
    options = {"num_regions": 6, "num_regions_order": "rolled"}

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
            order = sc._order_from_spheres(region_sphere, sc._order_rng(world))
            expected = sc._ranges_from_targets(sc._targets_from_order(order))
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
