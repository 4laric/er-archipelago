"""#1100: Morgott's sweep restores the post-boss Rold gift flag that opens both seals."""

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring import boss_sweeps, data


MORGOTT_DEFEAT = 11_000_800
ROLD_GIFT_FLAG = 400_001
ROLD_GIFT_AP = 7_770_556


def test_rold_gift_is_the_leyndell_check_with_the_seal_flag():
    rows = [row for row in data.LOCATIONS["Leyndell"] if row[2] == ROLD_GIFT_FLAG]
    assert len(rows) == 1
    name, ap_id, flag = rows[0]
    assert (ap_id, flag) == (ROLD_GIFT_AP, ROLD_GIFT_FLAG)
    assert "Rold Medallion - talk to Melina after killing Morgott" in name


def test_morgott_sweep_pays_the_post_boss_gift():
    assert ROLD_GIFT_AP in boss_sweeps.DUNGEON_SWEEPS[MORGOTT_DEFEAT]
    assert boss_sweeps.POST_BOSS_GIFTS == {
        MORGOTT_DEFEAT: frozenset({ROLD_GIFT_AP}),
    }
    assert boss_sweeps.SWEEP_REGION[MORGOTT_DEFEAT] == "Leyndell"


def test_no_other_sweep_claims_the_rold_gift():
    owners = [trigger for trigger, members in boss_sweeps.DUNGEON_SWEEPS.items()
              if ROLD_GIFT_AP in members]
    assert owners == [MORGOTT_DEFEAT]
