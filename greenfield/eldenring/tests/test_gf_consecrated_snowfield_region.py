"""Issue #868: Consecrated Snowfield is a first-class region, not a Mountaintops fold."""

from .. import boss_sweeps, data, region_graces, region_open_flags, region_play_ids
from ..features import natural_progression
from ..location_tags import DEFAULTED_REGION_APS
from ..region_spine import SPINE


SNOWFIELD = "Consecrated Snowfield"
MOUNTAINTOPS = "Mountaintops of the Giants"


def _flags(region):
    return {flag for _name, _ap_id, flag in data.LOCATIONS[region]}


def test_snowfield_is_a_rollable_region_with_its_own_lock():
    assert SNOWFIELD in data.REGIONS
    assert SPINE.index(MOUNTAINTOPS) < SPINE.index(SNOWFIELD) < SPINE.index("Haligtree")


def test_snowfield_direct_access_uses_the_named_entrance_and_own_bundle():
    assert region_open_flags.REGION_OPEN_FLAGS[SNOWFIELD] == 76550
    bundle = set(region_graces.REGION_GRACE_POINTS[SNOWFIELD])
    assert {76550, 76551, 73019, 73112, 73211, 76652, 76653} <= bundle
    assert bundle.isdisjoint(region_graces.REGION_GRACE_POINTS[MOUNTAINTOPS])


def test_runtime_kick_and_scaling_geometry_are_split_at_the_same_boundary():
    snow = {30190, 30200, 31120, 32110, 65030}
    mount = {30170, 30180, 31220, 65000, 65010, 65020}
    assert set(region_play_ids.REGION_PLAY_IDS[SNOWFIELD]) == snow
    assert set(region_play_ids.SCALING_PLAY_IDS[SNOWFIELD]) == snow
    assert set(region_play_ids.REGION_PLAY_IDS[MOUNTAINTOPS]) == mount
    assert set(region_play_ids.SCALING_PLAY_IDS[MOUNTAINTOPS]) == mount
    assert snow.isdisjoint(mount)


def test_snowfield_checks_and_sweeps_move_but_castle_sol_stays_mountaintops():
    snow_flags = _flags(SNOWFIELD)
    mount_flags = _flags(MOUNTAINTOPS)
    assert {530550, 1048557900, 1049547900} <= snow_flags
    assert 1051587800 in mount_flags  # Haligtree Secret Medallion (Left), Castle Sol
    assert 1051587800 not in snow_flags

    ruled_arenas = (30190800, 30200800, 31120800, 32110800,
                    1048570800, 1050560800, 1050570850)
    for trigger in ruled_arenas + (1248550800,):
        assert boss_sweeps.SWEEP_REGION[trigger] == SNOWFIELD
    for trigger in ruled_arenas:
        assert boss_sweeps.SWEEP_ARENA_REGION[trigger] == SNOWFIELD

    # The Avatar rewards are correctly owned by Snowfield, but their MSB evidence is a graceless
    # seam tile. Re-regioning must not silently promote either guess into progression eligibility.
    ap_by_flag = {flag: ap_id for locs in data.LOCATIONS.values()
                  for _name, ap_id, flag in locs}
    assert {ap_by_flag[65130], ap_by_flag[65170]} <= set(DEFAULTED_REGION_APS)


def test_natural_progression_requires_both_secret_medallion_halves():
    assert natural_progression.GATE_CLAUSES[SNOWFIELD] == [
        ("Haligtree Secret Medallion (Left)", "Haligtree Secret Medallion (Right)")
    ]
