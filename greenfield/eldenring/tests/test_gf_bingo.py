"""Board invariants and generation refusals; no game process required."""
import pytest

from worlds.eldenring.bingo_board import LINES, has_line, is_complete, select_board
from test.bases import WorldTestBase
from Options import OptionError


def test_all_lines_and_incomplete_lines():
    assert len(LINES) == 12
    for line in LINES:
        done = [i in line for i in range(25)]
        assert has_line(done)
        done[line[0]] = False
        assert not has_line(done)
    assert not is_complete([True] * 12 + [False] * 13, "count", 13)
    assert is_complete([True] * 13 + [False] * 12, "count", 13)
    assert not is_complete([True] * 24 + [False], "blackout", 13)


def test_board_identity_is_order_independent_and_insufficient_pool_refuses():
    candidates = [{"flag": i + 1, "region": "Test", "label": str(i)} for i in range(40)]
    assert select_board(candidates, 7) == select_board(list(reversed(candidates)), 7)
    assert select_board(candidates, 7) != select_board(candidates, 8)
    with pytest.raises(ValueError, match="25 eligible"):
        select_board(candidates[:24], 7)


@pytest.mark.parametrize("extra", [{"vanilla_placement": "all"}, {"natural_progression": True},
                                  {"mario_mode": True}, {"goal": "elden_beast"}])
def test_incompatible_options_fail_actionably(extra):
    class _T(WorldTestBase):
        game = "Elden Ring"
        options = {"bingo_mode": True, "num_regions": 12, **extra}
    t = _T()
    try:
        with pytest.raises(OptionError, match="bingo"):
            t.world_setup(seed=7)
    finally:
        t.tearDown()


def test_objectives_choose_regions_with_prerequisite_closure():
    candidates = [{"flag": i + 1, "region": f"R{i // 15}", "label": str(i)} for i in range(90)]
    board = select_board(candidates, 42, region_limit=3, parents={"R1": "R0"},
                         start_pool={"R2"})
    owners = {c["region"] for c in board}
    kept = owners | ({"R0"} if "R1" in owners else set())
    assert len(board) == 25 and "R2" in owners and len(kept) <= 3
    assert board == select_board(list(reversed(candidates)), 42, region_limit=3,
                                 parents={"R1": "R0"}, start_pool={"R2"})


@pytest.mark.parametrize("seed", [1, 7, 42, 22222])
@pytest.mark.parametrize("extra", [{"enable_dlc": False},
                                  {"num_regions": 0}, {"start_region_pool": ["Limgrave"]}])
def test_kept_regions_are_exactly_objective_owners_and_prerequisites(seed, extra):
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    from worlds.eldenring.region_spine import parent_chain
    mw = setup_multiworld(AutoWorldRegister.world_types["Elden Ring"], seed=seed,
                         options={"bingo_mode": True, **extra})
    world = mw.worlds[1]
    owners = {c["region"] for c in world.gf_bingo_board}
    expected = owners | {p for r in owners for p in parent_chain(r)}
    assert set(world._kept()) == expected
    assert len(expected) <= world.options.bingo_region_limit.value
    assert owners <= set(world.gf_eligible)


def test_dlc_only_catalogue_fails_actionably():
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    with pytest.raises(OptionError, match="bingo needs 25 eligible"):
        setup_multiworld(AutoWorldRegister.world_types["Elden Ring"], seed=7,
                         options={"bingo_mode": True, "dlc_only": True})


def test_start_region_count_and_capacity_refusal():
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    from BaseClasses import ItemClassification
    from worlds.eldenring.features.progression_surface import apply
    mw = setup_multiworld(AutoWorldRegister.world_types["Elden Ring"], seed=42,
                         options={"bingo_mode": True, "start_regions": 3})
    world = mw.worlds[1]
    starts = {item.name.removesuffix(" Lock") for item in mw.precollected_items[1]
              if item.name.endswith(" Lock")}
    assert not starts
    assert not any(i.name.endswith(" Lock") for i in mw.itempool)
    sd = world.fill_slot_data()
    assert sd["areaLockFlags"] == []
    points = world.tables.modules["region_graces"].REGION_GRACE_POINTS
    assert all(set(points[r]) <= set(sd["startGraces"]) for r in world._kept())
    assert all(mw.state.can_reach(r, "Region", 1) for r in world._kept())
    # Foreign pressure beyond the square budget must fail before ordinary fill can spill it.
    for item in [i for i in mw.itempool if not i.advancement][:40]:
        item.classification = ItemClassification.progression
    with pytest.raises(OptionError, match="reward capacity"):
        apply(world)


def test_bingo_off_preserves_default_generation():
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    world_type = AutoWorldRegister.world_types["Elden Ring"]
    baseline = setup_multiworld(world_type, seed=42, options={"num_regions": 6})
    explicit = setup_multiworld(world_type, seed=42,
                               options={"num_regions": 6, "bingo_mode": False})
    assert [(i.name, i.classification) for i in baseline.itempool] == [
        (i.name, i.classification) for i in explicit.itempool]
    assert [(l.name, l.address) for l in baseline.get_locations()] == [
        (l.name, l.address) for l in explicit.get_locations()]
    assert baseline.worlds[1].fill_slot_data() == explicit.worlds[1].fill_slot_data()
    assert "bingoBoard" not in explicit.worlds[1].fill_slot_data()


@pytest.mark.parametrize("seed", [1, 7, 42, 22222, 99])
@pytest.mark.parametrize("extra", [{"enable_dlc": False}, {"dlc_only": True}, {}])
def test_e1_generation_and_reward_capacity(seed, extra):
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    from worlds.eldenring.features.progression_surface import apply
    from worlds.eldenring.region_spine import parent_chain
    mw = setup_multiworld(AutoWorldRegister.world_types["Elden Ring"], seed=seed,
        options={"bingo_mode": True, "bingo_catalogue": "e1", **extra})
    w = mw.worlds[1]
    board = w.gf_bingo_board
    owners = {r for c in board for r in c.get("regions", [c["region"]])}
    assert set(w._kept()) == owners | {p for r in owners for p in parent_chain(r)}
    assert len(board) == 25
    assert sum(bool(c.get("supply_goal")) for c in board) <= 1
    assert len({c.get("family", f"boss:{c['flag']}") for c in board}) == 25
    for name, count in w.gf_bingo_requirements.items():
        assert sum(i.name == name and i.advancement for i in mw.itempool) >= count
    assert len(mw.itempool) == len([l for l in mw.get_unfilled_locations() if l.address is not None])
    apply(w)
    sd = w.fill_slot_data()
    assert sd["bingoBoard"]["version"] == 2
    assert "bingo_e1_v1" in sd["requiresClientFeatures"]
    flags = {c["flag"] for c in board if c["flag"]}
    overrides = getattr(w, "gf_extra_location_flags", {})
    for members in sd.get("dungeonSweepFlags", {}).values():
        assert all(sd["locationFlags"].get(str(aid), overrides.get(aid, 0)) not in flags for aid in members)


def test_e1_every_audited_template_has_an_adapter():
    from worlds.eldenring import bingo_e1
    from worlds.eldenring.tables.boss_healthbars import BOSS_HEALTHBARS
    from worlds.eldenring.tables.boss_sweeps import SWEEP_ARENA_REGION, SWEEP_REGION
    eligible = set(SWEEP_ARENA_REGION.values()) | {"Stormveil", "Liurnia"}
    cells = bingo_e1.candidates(BOSS_HEALTHBARS, SWEEP_ARENA_REGION, eligible, sweep_regions=SWEEP_REGION)
    assert {c["source"].removeprefix("S6-") for c in cells} == set(bingo_e1.BOSSES) | {s[0] for s in bingo_e1.STATE_GOALS}
    assert len({(c["source"], c["state"]["target"]) for c in cells if "state" in c}) == 14
    import csv
    from pathlib import Path
    from ._util import find_repo_root
    root = find_repo_root(__file__)
    assert root is not None
    audit = list(csv.DictReader((Path(root) / "docs/specs/bingo-objective-audit.csv").open(encoding="utf-8")))
    e1 = [r for r in audit if r["effort"] == "E1"]
    assert len(e1) == 61
    assert {r["id"] for r in e1} == {c["source"] for c in cells}
    for c in cells:
        if c["flag"]:
            assert c["flag"] in BOSS_HEALTHBARS
    assert all(c["flag"] != 15000850 for c in cells if c["source"] == "S6-BASE-018")
    assert all(c["flag"] == 31110800 for c in cells if c["source"] == "S6-BASE-026")


@pytest.mark.parametrize("extra", [{"enable_dlc": False}, {"dlc_only": True}, {}])
def test_curated_graces_change_travel_only(extra):
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    from worlds.eldenring.region_spine import DLC_REGIONS
    from worlds.eldenring.features.bingo import BRAWLERS_BASE_GRACES, BRAWLERS_DLC_GRACE
    world_type = AutoWorldRegister.world_types["Elden Ring"]
    opts = {"bingo_mode": True, "bingo_catalogue": "e1", **extra}
    baseline = setup_multiworld(world_type, seed=42, options=opts)
    curated = setup_multiworld(world_type, seed=42, options={**opts, "bingo_graces": True})
    w = curated.worlds[1]
    sd = w.fill_slot_data()
    assert w.gf_bingo_board == baseline.worlds[1].gf_bingo_board
    assert [(i.name, i.classification) for i in curated.itempool] == [
        (i.name, i.classification) for i in baseline.itempool]
    names = w.tables.modules["region_graces"].REGION_GRACE_POINTS
    all_warp_flags = {f for flags in names.values() for f in flags} | {71190}
    expected = set(BRAWLERS_BASE_GRACES) if set(w._kept()) - DLC_REGIONS else {71190}
    if set(w._kept()) & DLC_REGIONS:
        expected.add(BRAWLERS_DLC_GRACE)
    assert set(sd["startGraces"]) & all_warp_flags == expected
    assert sd["startGraces"][0] == 71190  # Existing client sentinel remains a real grace.
    assert sd["areaLockFlags"] == [] and sd["regionGraces"] == {}
    assert not any(i.name.endswith(" Lock") for i in curated.itempool)
    assert sd["regionOpenFlags"] == {}  # Open tracker regions without extra anchor-grace grants.


def test_curated_graces_ignored_outside_bingo():
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    world_type = AutoWorldRegister.world_types["Elden Ring"]
    baseline = setup_multiworld(world_type, seed=42, options={"num_regions": 6})
    enabled = setup_multiworld(world_type, seed=42, options={"num_regions": 6, "bingo_graces": True})
    assert baseline.worlds[1].fill_slot_data()["startGraces"] == enabled.worlds[1].fill_slot_data()["startGraces"]


@pytest.mark.parametrize("seed", [1,7,42,22222,99])
@pytest.mark.parametrize("extra", [{"enable_dlc": False},{"dlc_only": True},{}])
def test_e2_generates_counters_with_supported_contributors(seed,extra):
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    from worlds.eldenring.features.bingo import evidence_flags
    mw=setup_multiworld(AutoWorldRegister.world_types["Elden Ring"],seed=seed,
        options={"bingo_mode":True,"bingo_catalogue":"e2",**extra})
    w=mw.worlds[1]
    sd=w.fill_slot_data()
    assert sd["bingoBoard"]["version"] == 3
    assert sd["requiresClientFeatures"][-1] == "bingo_e2_v1" or "bingo_e2_v1" in sd["requiresClientFeatures"]
    assert sum(bool(c.get("counter")) for c in w.gf_bingo_board) <= 3
    hits={}
    for c in w.gf_bingo_board:
        for f in evidence_flags(c): hits[f]=hits.get(f,0)+1
        for g in c.get("counter",[]):
            assert sum(m["weight"] for m in g["members"]) >= g["target"]
            assert len({m["flag"] for m in g["members"]}) == len(g["members"])
            assert all(m["region"] in w._kept() for m in g["members"])
    assert max(hits.values(),default=0) <= 2
    assert len(mw.itempool) == len([l for l in mw.get_unfilled_locations() if l.address is not None])
    for members in sd.get("dungeonSweepFlags",{}).values():
        assert all(sd["locationFlags"].get(str(aid),0) not in hits for aid in members)


def test_e2_full_catalogue_exposes_source_blockers():
    from worlds.eldenring.core import TABLES
    from worlds.eldenring import bingo_e2
    cells,unavailable=bingo_e2.candidates(TABLES,TABLES.regions,12)
    assert len(bingo_e2.CATALOGUE)==133
    assert set(unavailable)=={"S6-BASE-011-V03","S6-BASE-047-V03",
        "S6-DLC-019-V01","S6-DLC-019-V02","S6-DLC-019-V03",
        "S6-BASE-121-V01","S6-BASE-121-V02"}
    assert len({c["variant"] for c in cells})==126
    # Miniboss partner bars cannot become independent dungeon completions.
    for c in cells:
        for g in c.get("counter",[]):
            assert all(m["flag"] not in {12020801,31110801,31110802,30100801} for m in g["members"])


def test_e2_catalogue_matches_audit_variant_ledger():
    import csv
    from pathlib import Path
    from ._util import find_repo_root
    from worlds.eldenring.bingo_e2 import CATALOGUE
    rows = list(csv.DictReader((Path(find_repo_root(__file__)) / "docs/specs/bingo-objective-audit.csv").open(encoding="utf-8")))
    assert {r["variant_id"] for r in rows if r["effort"] == "E2"} == {r["variant"] for r in CATALOGUE}


def test_e2_start_inventory_excludes_matching_collection_goals(monkeypatch):
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    from worlds.eldenring import bingo_e1
    select = bingo_e1.select
    def checked(candidates, seed, **kwargs):
        assert not any(c.get("source") in {"S6-BASE-080", "S6-BASE-108"} for c in candidates)
        return select(candidates, seed, **kwargs)
    monkeypatch.setattr(bingo_e1, "select", checked)
    setup_multiworld(AutoWorldRegister.world_types["Elden Ring"], seed=42,
        options={"bingo_mode":True,"bingo_catalogue":"e2",
                 "start_inventory":{"Cracked Pot":19,"Memory Stone":8}})


@pytest.mark.parametrize("source", ["S6-BASE-080", "S6-BASE-081", "S6-BASE-094",
    "S6-BASE-095", "S6-BASE-108", "S6-DLC-050", "S6-DLC-053", "S6-DLC-074", "S6-DLC-077"])
@pytest.mark.parametrize("armor_bundles", ["sets", "mixed", "off"])
def test_e2_forced_collection_supplies_are_fillable_and_not_starting_gifts(monkeypatch, source, armor_bundles):
    from Fill import distribute_items_restrictive
    from test.general import setup_multiworld
    from worlds.AutoWorld import AutoWorldRegister
    from worlds.eldenring import bingo_e1
    from worlds.eldenring.features import start_items
    select = bingo_e1.select
    def forced(candidates, seed, **kwargs):
        target = max((c for c in candidates if c.get("source") == source),
                     key=lambda c: sum(q for _, q in c["requirements"]))
        board = select([c for c in candidates if not c.get("supply_goal")], seed, **kwargs)
        board[-1] = dict(target, location=board[-1]["location"])
        return board
    monkeypatch.setattr(bingo_e1, "select", forced)
    mw = setup_multiworld(AutoWorldRegister.world_types["Elden Ring"], seed=42,
        options={"bingo_mode": True, "bingo_catalogue": "e2", "bingo_region_limit":12, "armor_bundles":armor_bundles})
    w = mw.worlds[1]
    cell = next(c for c in w.gf_bingo_board if c.get("source") == source)
    watched = {fid for g in cell["collection"] for m in g["members"] for ids in m["items"] for fid in ids}
    assert not watched.intersection(start_items.plain_start_ids(w))
    for name, quantity in cell["requirements"]:
        assert sum(i.name == name and i.advancement for i in mw.itempool) >= quantity
    distribute_items_restrictive(mw)
    assert mw.can_beat_game()
