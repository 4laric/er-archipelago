"""Pin direct maintainer adjudications to their intended generated tags."""
from ..certified_progression_hosts import (
    CERTIFIED_GREAT_RUNE_APS,
    CERTIFIED_KEY_ITEM_APS,
    CERTIFIED_MAJOR_BOSS_APS,
    CERTIFIED_PROGRESSION_HOST_APS,
    CERTIFIED_REMEMBRANCE_APS,
)
from ..features.evidence_progression_hosts import _always_hold_aps
from ..location_tags import LOCATION_TAGS


def test_certified_families_have_the_expected_tags():
    assert len(CERTIFIED_REMEMBRANCE_APS) == 25
    assert all("Remembrance" in LOCATION_TAGS[ap] for ap in CERTIFIED_REMEMBRANCE_APS)
    assert all("GreatRune" in LOCATION_TAGS[ap] for ap in CERTIFIED_GREAT_RUNE_APS)
    assert len(CERTIFIED_KEY_ITEM_APS) == 8
    assert all("KeyItem" in LOCATION_TAGS[ap] for ap in CERTIFIED_KEY_ITEM_APS)
    assert len(CERTIFIED_MAJOR_BOSS_APS) == 7
    assert all("MajorBoss" in LOCATION_TAGS[ap] for ap in CERTIFIED_MAJOR_BOSS_APS)


def test_certified_union_is_exact():
    assert CERTIFIED_PROGRESSION_HOST_APS == (
        CERTIFIED_REMEMBRANCE_APS | CERTIFIED_GREAT_RUNE_APS | CERTIFIED_KEY_ITEM_APS
        | CERTIFIED_MAJOR_BOSS_APS
    )


def test_new_default_surface_certifications_are_stable_and_finale_free():
    """The queue restores only non-missable, non-excluded checks with confirmed regions."""
    from ..location_tags import DEFAULTED_REGION_APS, SURFACE_EXCLUDE_APS
    from ..missable_locations import MISSABLE_LOCATIONS

    restored = ((CERTIFIED_KEY_ITEM_APS - {7900002}) | CERTIFIED_MAJOR_BOSS_APS)
    assert len(restored) == 14
    assert restored.isdisjoint(MISSABLE_LOCATIONS)
    assert restored.isdisjoint(DEFAULTED_REGION_APS)
    assert restored.isdisjoint(SURFACE_EXCLUDE_APS)
    assert restored.isdisjoint(_always_hold_aps())
