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
    assert len(starts) == 3
    assert starts <= {c["region"] for c in world.gf_bingo_board}
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
