"""Pin direct maintainer adjudications to their intended generated tags."""
from ..certified_progression_hosts import (
    CERTIFIED_CHURCH_APS,
    CERTIFIED_GREAT_RUNE_APS,
    CERTIFIED_KEY_ITEM_APS,
    CERTIFIED_MAJOR_BOSS_APS,
    CERTIFIED_PROGRESSION_HOST_APS,
    CERTIFIED_REMEMBRANCE_APS,
    CERTIFIED_SEEDTREE_APS,
)
from ..features.evidence_progression_hosts import _always_hold_aps
from ..location_tags import LOCATION_TAGS


def test_certified_families_have_the_expected_tags():
    assert len(CERTIFIED_REMEMBRANCE_APS) == 25
    assert all("Remembrance" in LOCATION_TAGS[ap] for ap in CERTIFIED_REMEMBRANCE_APS)
    assert all("GreatRune" in LOCATION_TAGS[ap] for ap in CERTIFIED_GREAT_RUNE_APS)
    assert len(CERTIFIED_KEY_ITEM_APS) == 8
    assert all("KeyItem" in LOCATION_TAGS[ap] for ap in CERTIFIED_KEY_ITEM_APS)
    assert len(CERTIFIED_SEEDTREE_APS) == 30
    assert all("Seedtree" in LOCATION_TAGS[ap] for ap in CERTIFIED_SEEDTREE_APS)
    assert len(CERTIFIED_CHURCH_APS) == 4
    assert all("Church" in LOCATION_TAGS[ap] for ap in CERTIFIED_CHURCH_APS)
    assert len(CERTIFIED_MAJOR_BOSS_APS) == 7
    assert all("MajorBoss" in LOCATION_TAGS[ap] for ap in CERTIFIED_MAJOR_BOSS_APS)


def test_collectathon_certifications_do_not_override_independent_bars():
    from ..location_tags import DEFAULTED_REGION_APS, ERDTREE_BURN_APS, SURFACE_EXCLUDE_APS
    from ..missable_locations import MISSABLE_LOCATIONS
    barred = (set(DEFAULTED_REGION_APS) | set(ERDTREE_BURN_APS)
              | set(SURFACE_EXCLUDE_APS) | set(MISSABLE_LOCATIONS))
    assert (CERTIFIED_SEEDTREE_APS | CERTIFIED_CHURCH_APS).isdisjoint(barred)


def test_collectathon_certifications_restore_exactly_34_generated_holds():
    from ..evidence_progression_hosts import HOLD_PROGRESSION_HOST_APS
    from ..features.evidence_progression_hosts import hold_aps
    restored = CERTIFIED_SEEDTREE_APS | CERTIFIED_CHURCH_APS
    assert len(restored) == 34
    assert restored <= HOLD_PROGRESSION_HOST_APS
    assert hold_aps(None, candidates=restored).isdisjoint(restored)


def test_certified_union_is_exact():
    assert CERTIFIED_PROGRESSION_HOST_APS == (
        CERTIFIED_REMEMBRANCE_APS | CERTIFIED_GREAT_RUNE_APS | CERTIFIED_KEY_ITEM_APS
        | CERTIFIED_SEEDTREE_APS | CERTIFIED_CHURCH_APS
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
