"""#1317: Discarded Palace Key needs the narrow, data-proven Miniature Ranni chain."""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from BaseClasses import CollectionState, ItemClassification as IC  # noqa: E402
from Fill import distribute_items_restrictive  # noqa: E402
from worlds.eldenring.features.questline_check_gates import (  # noqa: E402
    MINIATURE_RANNI, PALACE_KEY_AP_ID, _active,
)
from ._util import world_items  # noqa: E402


class QuestlineCheckGateOn(WorldTestBase):
    game = "Elden Ring"
    run_default_tests = False
    options = {"item_shuffle": True, "num_regions": 0,
               "leyndell_runes_required": 0, "accessibility": "minimal"}

    def test_palace_key_needs_miniature_ranni_but_not_the_whole_vanilla_quest(self):
        world = self.multiworld.worlds[1]
        location = self.multiworld.get_location(
            "Ainsel River :: Discarded Palace Key [f400159]", 1)
        assert location.address == PALACE_KEY_AP_ID
        doll = next(item for item in world_items(self) if item.name == MINIATURE_RANNI)
        assert MINIATURE_RANNI in world.gf_questline_gate_items
        assert doll.classification & IC.progression

        state = CollectionState(self.multiworld)
        for item in world_items(self):
            if item.name != MINIATURE_RANNI and item.classification & IC.progression:
                state.collect(item, prevent_sweep=True)
        assert not location.can_reach(state), "Ainsel access alone must not imply the shadow kill"
        state.collect(doll, prevent_sweep=True)
        assert location.can_reach(state), "the doll plus ordinary Ainsel access is sufficient"

    def test_the_gate_cannot_hold_its_own_key(self):
        location = self.multiworld.get_location(
            "Ainsel River :: Discarded Palace Key [f400159]", 1)
        doll = next(item for item in world_items(self) if item.name == MINIATURE_RANNI)
        assert location and doll, "WITNESS: the check and its gating item must both exist"
        assert not location.can_fill(self.multiworld.get_all_state(False), doll, check_access=False)

    def test_the_added_progression_gate_still_fills_a_beatable_seed(self):
        distribute_items_restrictive(self.multiworld)
        assert self.multiworld.can_beat_game()


def test_no_randomized_item_means_no_ap_item_gate():
    class Stub:
        options = type("Options", (), {
            "item_shuffle": type("Option", (), {"value": 0})(),
        })()

        @staticmethod
        def _kept():
            return ["Ainsel River"]

    stub = Stub()
    assert "Ainsel River" in stub._kept(), "WITNESS: only the shuffle toggle is off"
    assert not _active(stub)
