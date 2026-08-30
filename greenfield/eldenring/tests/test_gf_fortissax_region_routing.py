"""#1002: Fortissax's dream arena is Deeproot, never Leyndell.

The player report was a Leyndell-lock screen at the portal after Fia's Champions. Pin every
independent input to the region-lock decision so a future regen cannot silently recreate it.
"""

from ..boss_reward_lots import BOSS_REWARD_TILE
from ..data import LOCATIONS
from ..region_open_flags import REGION_OPEN_FLAGS
from ..region_play_ids import REGION_PLAY_IDS


FORTISSAX_REWARD_FLAG = 510110
FORTISSAX_MAP = "m12_03"
DEEPROOT_PLAY_REGION = 12030


def test_fortissax_reward_is_emitted_under_deeproot() -> None:
    deeproot_flags = {int(flag) for _name, _ap_id, flag in LOCATIONS["Deeproot Depths"]}
    assert FORTISSAX_REWARD_FLAG in deeproot_flags
    assert all(
        FORTISSAX_REWARD_FLAG != int(flag)
        for _name, _ap_id, flag in LOCATIONS["Leyndell"]
    )


def test_fortissax_map_resolves_to_deeproot_play_region() -> None:
    assert BOSS_REWARD_TILE[FORTISSAX_REWARD_FLAG] == FORTISSAX_MAP
    assert DEEPROOT_PLAY_REGION in REGION_PLAY_IDS["Deeproot Depths"]
    assert DEEPROOT_PLAY_REGION not in REGION_PLAY_IDS["Leyndell"]


def test_deeproot_and_leyndell_have_distinct_unlock_flags() -> None:
    assert REGION_OPEN_FLAGS["Deeproot Depths"] == 71231
    assert REGION_OPEN_FLAGS["Leyndell"] == 76980
    assert REGION_OPEN_FLAGS["Deeproot Depths"] != REGION_OPEN_FLAGS["Leyndell"]
