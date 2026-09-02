"""#1305: f520700 is Fog Rift Catacombs, never Auriza Side Tomb.

The v1.17 provenance is three-way agreement: check_maps.tsv and msb_flag_region.tsv resolve the
flag to m40_00, while questline_conditions.tsv resolves its award through boss flag 9270 on that
map. flag_lots.tsv records two co-firing rewards. The old description survived a region correction
because neither reward had a flag-level description and both fell through to a stale grace join.
"""

from ..data import LOCATIONS


FLAG = 520700


def test_every_fog_rift_reward_names_the_correct_catacomb():
    rows = [
        (region, name, ap_id)
        for region, locations in LOCATIONS.items()
        for name, ap_id, flag in locations
        if flag == FLAG
    ]
    assert len(rows) == 2, f"f{FLAG} should retain both co-firing rewards: {rows}"
    assert {region for region, _name, _ap_id in rows} == {"Gravesite"}
    for _region, name, _ap_id in rows:
        assert "Fog Rift Catacombs" in name
        assert "Auriza Side Tomb" not in name
