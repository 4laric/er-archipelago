"""Pin direct maintainer adjudications to their intended generated tags."""
from ..certified_progression_hosts import (
    CERTIFIED_GREAT_RUNE_APS,
    CERTIFIED_KEY_ITEM_APS,
    CERTIFIED_PROGRESSION_HOST_APS,
    CERTIFIED_REMEMBRANCE_APS,
)
from ..location_tags import LOCATION_TAGS


def test_certified_families_have_the_expected_tags():
    assert len(CERTIFIED_REMEMBRANCE_APS) == 25
    assert all("Remembrance" in LOCATION_TAGS[ap] for ap in CERTIFIED_REMEMBRANCE_APS)
    assert all("GreatRune" in LOCATION_TAGS[ap] for ap in CERTIFIED_GREAT_RUNE_APS)
    assert all("KeyItem" in LOCATION_TAGS[ap] for ap in CERTIFIED_KEY_ITEM_APS)


def test_certified_union_is_exact():
    assert CERTIFIED_PROGRESSION_HOST_APS == (
        CERTIFIED_REMEMBRANCE_APS | CERTIFIED_GREAT_RUNE_APS | CERTIFIED_KEY_ITEM_APS
    )
