"""#1076 -- Seethewater and First Mt. Gelmir Campsite checks follow their Gelmir graces."""

from ..data import LOCATIONS
from ..boss_sweeps import SWEEP_REGION


FLAGS = {
    530385,
    1038527000, 1038527010, 1038527020, 1038527040, 1038527060, 1038527070,
    1038537000, 1038537010, 1038537020, 1038537030, 1038537040, 1038537050,
}


def test_mt_gelmir_grace_cluster_is_not_filed_under_altus():
    found = {
        flag: region
        for region, rows in LOCATIONS.items()
        for (_name, _ap, flag) in rows
        if flag in FLAGS
    }
    assert set(found) == FLAGS
    assert set(found.values()) == {"Mt. Gelmir"}


def test_seethewater_tibia_mariner_sweeps_only_mt_gelmir_members():
    assert SWEEP_REGION[1038520800] == "Mt. Gelmir"
