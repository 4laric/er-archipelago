"""The three MSB-backed Ruin-Strewn Precipice rune drops remain real checks (#950)."""

import csv
from pathlib import Path

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

ROWS = {
    39207970: (420126020, "c4201_9003"),
    39207980: (420126010, "c4201_9002"),
    39207990: (420126000, "c4201_9000"),
}


def test_precipice_runes_keep_their_msb_witnesses_and_generated_locations():
    from worlds.eldenring.data import LOCATIONS
    from worlds.eldenring.tests._util import find_repo_root

    flags = {int(flag) for region in LOCATIONS.values() for _name, _ap_id, flag in region}
    assert set(ROWS) <= flags

    root = find_repo_root(str(Path(__file__).resolve()))
    if root is None:
        pytest.skip("repo-only msb_flag_region.tsv is not installed with the apworld")
    with (Path(root) / "greenfield" / "msb_flag_region.tsv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = csv.DictReader(
            (line for line in handle if not line.lstrip().startswith("#")), delimiter="\t"
        )
        msb = {int(row["flag"]): (int(row["item_lot_id"]), row["treasure_name"])
               for row in rows if row["flag"]}
    assert {flag: msb.get(flag) for flag in ROWS} == ROWS


def test_precipice_rune_enemy_lots_are_source_neutralised():
    from worlds.eldenring.check_lots_data import CHECK_LOT_SLOTS_ENEMY

    assert {lot: CHECK_LOT_SLOTS_ENEMY.get(lot) for lot, _entity in ROWS.values()} == {
        420126020: [1],
        420126010: [1],
        420126000: [1],
    }


class PrecipiceRuneChecks(WorldTestBase):
    game = "Elden Ring"
    options = {"num_regions": 0}

    def test_all_three_enemy_lots_are_emitted_to_the_client(self):
        blank = self.world.fill_slot_data().get("checkLotBlankEnemy", {})
        assert blank, "checkLotBlankEnemy must be emitted"
        for lot, _entity in ROWS.values():
            assert blank.get(str(lot)) == [1]
