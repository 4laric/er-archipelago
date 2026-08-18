"""Direct quest prerequisites cannot be placed on their own dependent checks (#832)."""

import csv
from pathlib import Path

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
from BaseClasses import ItemClassification  # noqa: E402
from worlds.eldenring.features.quest_prerequisite_rules import (  # noqa: E402
    REVIEWED_PREREQUISITES,
    _AP_IDS_BY_FLAG,
)


class QuestPrerequisitePlacementRules(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0}

    def test_every_reviewed_pair_rejects_the_same_player_prerequisite(self):
        locations = {loc.address: loc for loc in self.multiworld.get_locations(self.player)}
        for _source_flag, target_flag, item_name in REVIEWED_PREREQUISITES:
            targets = _AP_IDS_BY_FLAG.get(target_flag, set())
            self.assertTrue(targets, f"dependent flag {target_flag} has no generated AP location")
            item = self.world.create_item(item_name)
            for ap_id in targets:
                if ap_id in locations:
                    self.assertFalse(locations[ap_id].item_rule(item),
                                     f"{item_name} was accepted by dependent flag {target_flag}")

    def test_foreign_copy_of_the_same_name_is_not_barred(self):
        source_flag, target_flag, item_name = REVIEWED_PREREQUISITES[0]
        ap_id = next(iter(_AP_IDS_BY_FLAG[target_flag]))
        loc = next(loc for loc in self.multiworld.get_locations(self.player)
                   if loc.address == ap_id)
        item = self.world.create_item(item_name)
        item.player = self.player + 1
        self.assertTrue(loc.item_rule(item), source_flag)

    def test_items_remain_filler_and_unrelated_filler_still_fits(self):
        locations = {loc.address: loc for loc in self.multiworld.get_locations(self.player)}
        for _source_flag, target_flag, item_name in REVIEWED_PREREQUISITES:
            self.assertEqual(self.world.create_item(item_name).classification,
                             ItemClassification.filler, item_name)
            for ap_id in _AP_IDS_BY_FLAG[target_flag]:
                if ap_id in locations:
                    self.assertTrue(locations[ap_id].item_rule(self.world.create_item("Rune")),
                                    f"existing rules were replaced at flag {target_flag}")


def test_reviewed_pairs_are_backed_by_typed_questline_evidence():
    from worlds.eldenring.tests._util import find_repo_root
    root = find_repo_root(str(Path(__file__).resolve()))
    if root is None:
        pytest.skip("repo-only questline_model.tsv is not installed with the apworld")
    repo = Path(root)
    table = repo / "greenfield" / "questline_model.tsv"
    with table.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(
            (line for line in handle if not line.lstrip().startswith("#")), delimiter="\t"))
    evidence = {
        (row["source_node"], row["target_node"])
        for row in rows if row["relation"] == "requires"
    }
    for source_flag, target_flag, _item_name in REVIEWED_PREREQUISITES:
        assert (f"flag:{source_flag}", f"flag:{target_flag}") in evidence
