"""Pin direct maintainer adjudications to their intended generated tags."""
from ..certified_progression_hosts import (
    CERTIFIED_CHURCH_APS,
    CERTIFIED_GREAT_RUNE_APS,
    CERTIFIED_KEY_ITEM_APS,
    CERTIFIED_MAJOR_BOSS_APS,
    CERTIFIED_MAJOR_BOSS_WAVE2_APS,
    CERTIFIED_PROGRESSION_HOST_APS,
    CERTIFIED_REMEMBRANCE_APS,
    CERTIFIED_REVERED_APS,
    CERTIFIED_SEEDTREE_APS,
)
from ..features.evidence_progression_hosts import _always_hold_aps
from ..contract import has_class
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
    assert len(CERTIFIED_MAJOR_BOSS_APS) == 10
    assert all(has_class(LOCATION_TAGS[ap], {"MajorBoss"})
               for ap in CERTIFIED_MAJOR_BOSS_APS)
    assert len(CERTIFIED_REVERED_APS) == 7
    assert all("Revered" in LOCATION_TAGS[ap] for ap in CERTIFIED_REVERED_APS)


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
        | CERTIFIED_REVERED_APS
    )


def test_new_default_surface_certifications_are_stable_and_finale_free():
    """The queue restores only non-missable, non-excluded checks with confirmed regions."""
    from ..location_tags import DEFAULTED_REGION_APS, SURFACE_EXCLUDE_APS
    from ..missable_locations import MISSABLE_LOCATIONS

    restored = ((CERTIFIED_KEY_ITEM_APS - {7900002}) | CERTIFIED_MAJOR_BOSS_APS)
    assert len(restored) == 17
    assert restored.isdisjoint(MISSABLE_LOCATIONS)
    assert restored.isdisjoint(DEFAULTED_REGION_APS)
    assert restored.isdisjoint(SURFACE_EXCLUDE_APS)
    assert restored.isdisjoint(_always_hold_aps())


def test_revered_wave_preserves_deeper_gate_and_region_dispute_holds():
    """The two unresolved effective rows are named, not accidentally omitted."""
    from ..evidence_progression_hosts import HOLD_PROGRESSION_HOST_APS
    from ..location_tags import SURFACE_EXCLUDE_APS

    deeper_gated = 7771808       # statue after Divine Beast Dancing Lion
    region_disputed = 7773212    # Ancient Ruins|Enir Ilim in region_dispute_worksheet.tsv
    assert {deeper_gated, region_disputed}.isdisjoint(CERTIFIED_REVERED_APS)
    assert {deeper_gated, region_disputed} <= HOLD_PROGRESSION_HOST_APS
    assert {deeper_gated, region_disputed}.isdisjoint(SURFACE_EXCLUDE_APS)


def test_revered_wave_is_exactly_the_other_effective_generated_holds():
    from ..evidence_progression_hosts import HOLD_PROGRESSION_HOST_APS
    from ..location_tags import SURFACE_EXCLUDE_APS

    effective = {
        ap for ap, tags in LOCATION_TAGS.items()
        if "Revered" in tags and ap in HOLD_PROGRESSION_HOST_APS
        and ap not in SURFACE_EXCLUDE_APS
    }
    assert effective == CERTIFIED_REVERED_APS | {7771808, 7773212}

def test_major_boss_wave2_restores_three_and_preserves_seven_finale_rows():
    from ..evidence_progression_hosts import HOLD_PROGRESSION_HOST_APS
    from ..features.evidence_progression_hosts import hold_aps

    finale_rows = {7770655, 7770664, 7773787, 7900114, 7900115, 7900116, 7900117}
    assert CERTIFIED_MAJOR_BOSS_WAVE2_APS == {7770716, 7773799, 7900120}
    assert CERTIFIED_MAJOR_BOSS_WAVE2_APS <= HOLD_PROGRESSION_HOST_APS
    assert hold_aps(None, candidates=CERTIFIED_MAJOR_BOSS_WAVE2_APS).isdisjoint(
        CERTIFIED_MAJOR_BOSS_WAVE2_APS)
    assert finale_rows <= hold_aps(None, candidates=finale_rows)
