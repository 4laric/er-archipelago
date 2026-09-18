"""#1076 -- Seethewater and First Mt. Gelmir Campsite checks follow their Gelmir graces."""

from ..tables.data import LOCATIONS
from ..tables.boss_sweeps import SWEEP_REGION


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


def test_seethewater_tibia_mariner_hosts_an_altus_sweep_of_altus_checks_only():
    # Ruled 2026-09-18: the boss is an Altus boss, the grace-cluster checks stay Gelmir's, so the
    # Gelmir ones are dealt to the Gelmir field bosses beside them (#1059), never to the Mariner.
    from ..tables.boss_sweeps import DUNGEON_SWEEPS
    assert SWEEP_REGION[1038520800] == "Altus"
    flag_of = {ap: fl for rows in LOCATIONS.values() for (_n, ap, fl) in rows}
    region_of = {ap: r for r, rows in LOCATIONS.items() for (_n, ap, _f) in rows}
    members = DUNGEON_SWEEPS[1038520800]
    assert {region_of[ap] for ap in members} == {"Altus"}
    assert not FLAGS & {flag_of[ap] for ap in members}
