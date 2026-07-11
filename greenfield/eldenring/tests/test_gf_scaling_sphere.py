"""Regression guard: completion-scaling targets must track the TRUE per-seed FILL SPHERES, not the
static region_spine.SPINE order.

The live scaling wire (slot_data regionSphereTargetRanges, features/scaling.py) is supposed to scale
each region by the playthrough sphere its `<Region> Lock` is actually obtained in -- so a random-start
`num_regions_order=rolled` seed scales from the region you can REACH first, not from geography. The
feature falls back to SPINE-order depth (sphere_target_ranges) only when the fill spheres can't be
computed. A silent regression -- e.g. mw.get_spheres() throwing so _region_fill_spheres() returns {}
-- would make the wire quietly revert to spine order while still "working". This test catches that:
for a real (post-fill) rolled seed the fill spheres must be non-empty, the wire must equal the
fill-sphere-derived ranges (NOT the spine ramp), and across a seed sweep at least one seed's region
ordering must diverge from SPINE (proving the targets are genuinely reachability-driven).

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

    def test_wire_tracks_fill_spheres_not_spine(self):
        any_diverged = False
        for seed in _SEEDS:
            world = self._fill(seed)
            kept = world._kept()

            region_sphere = sc._region_fill_spheres(world)
            self.assertTrue(
                region_sphere,
                f"seed={seed}: _region_fill_spheres() is empty on a filled world -> the scaling wire "
                f"silently fell back to SPINE order (regression).")

            # The slot_data wire must be exactly the fill-sphere-derived ranges, not the spine ramp.
            expected = sc._ranges_from_targets(sc._targets_from_spheres(region_sphere))
            wire = world.fill_slot_data()[contract.REGION_SPHERE_TARGET_RANGES]
            self.assertEqual(
                _tuples(wire), _tuples(expected),
                f"seed={seed}: regionSphereTargetRanges is not the fill-sphere wire.")

            # Divergence check: order the kept regions by their emitted target and compare to SPINE.
            pid_t = {lo: t for lo, _hi, t in wire}
            region_t = {r: max((pid_t.get(p, 0) for p in sc.REGION_PLAY_IDS.get(r, [])), default=0)
                        for r in kept}
            fill_order = [r for r, _ in sorted(region_t.items(), key=lambda kv: (kv[1], kv[0]))]
            spine_order = [r for r in SPINE if r in set(kept)]
            if fill_order != spine_order:
                any_diverged = True

        self.assertTrue(
            any_diverged,
            "no rolled seed produced a fill-sphere order that diverged from SPINE order -- the test "
            "is not actually exercising sphere-vs-spine scaling (or scaling reverted to spine).")
