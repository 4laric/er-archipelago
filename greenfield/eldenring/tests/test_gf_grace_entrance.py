"""`region_grace_unlock: entrance` -- one grace per region, and it is the RIGHT one.

MOTIVATING CASE (CONTRIBUTING rule 11), from a Nexus report by **dafranky67**, 2026-07-29:
"is it supposed to unlock every grace for a region, wouldn't it make more sense to only have the
grace in the start of a region?" On `all` a Liurnia unlock lights 59 warp points at once. So the
named exemplars below are fixtures, not decoration: the pipeline must still pick *Lake-Facing
Cliffs* for Liurnia, or the option is built and pointed at the wrong grace.

🛑 THE TWO NEARBY TABLES THAT LOOK RIGHT AND ARE NOT -- both were checked and rejected, and this
file exists partly so nobody "simplifies" the derivation into one of them:
  * REGION_OPEN_FLAGS is one flag per region and equals REGION_GRACE_POINTS[r][0] for all 30 -- but
    it is a region-OPEN DETECTION anchor and resolves to cave interiors (Limgrave -> Murkwater Cave).
  * BonfireWarpParam.bonfireSubCategorySortId sorts within the warp MENU's 55 subcategories, not our
    30 regions, so its per-region minimum TIES in 12 of 30.
"""
import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.graces import entrance_grace  # noqa: E402
from worlds.eldenring.region_graces import REGION_GRACE_POINTS  # noqa: E402

# flag -> the PlaceName the game shows for that warp point. Derived (BonfireWarpParam.textId1 ->
# PlaceName FMG, 351/351 resolve), transcribed here so the assertion is legible without the artifacts.
EXEMPLARS = {
    "Liurnia": (76200, "Lake-Facing Cliffs"),      # the literal way in from Stormveil
    "Limgrave": (76100, "Church of Elleh"),
    "Weeping": (76150, "Church of Pilgrimage"),
    "Altus": (76301, "Altus Plateau"),         # lift-side entrance; #641
    "Gravesite": (76800, "Gravesite Plain"),       # where the DLC starts
    "Stormveil": (71003, "Gateside Chamber"),      # interior region: no 76xxx member at all
    "Leyndell": (71102, "East Capital Rampart"),   # interior
    "Raya Lucaria Academy": (71402, "Church of the Cuckoo"),
}


def test_every_region_resolves_to_exactly_one_entrance():
    for region, flags in REGION_GRACE_POINTS.items():
        if not flags:
            continue
        f = entrance_grace(flags, region)
        assert f in flags, "%s: entrance %s is not one of the region's graces" % (region, f)


def test_the_named_exemplars_are_still_what_the_pipeline_picks():
    """Rule 11: the case that motivated the work, asserted end to end by name."""
    wrong = []
    for region, (flag, name) in EXEMPLARS.items():
        if region not in REGION_GRACE_POINTS:
            wrong.append("%s: region is gone from REGION_GRACE_POINTS" % region)
            continue
        got = entrance_grace(REGION_GRACE_POINTS[region], region)
        if got != flag:
            wrong.append("%s: expected %s (%s), got %s" % (region, flag, name, got))
    assert not wrong, (
        "the entrance derivation moved off its verified answers: %s. These were confirmed by "
        "resolving BonfireWarpParam.textId1 -> PlaceName for all 30 regions; if the rule changed "
        "on purpose, re-verify by NAME and update the fixtures -- do not just re-baseline the "
        "numbers, which is how a regression gets laundered into a test." % wrong)


def test_only_the_ruled_altus_entrance_matches_its_open_anchor():
    """The rejected REGION_OPEN_FLAGS table stays rejected except for the explicit Altus ruling.

    If someone swaps the derivation for `REGION_GRACE_POINTS[r][0]` (which IS REGION_OPEN_FLAGS, and
    is one line shorter) every test above would still need to fail loudly. It does: for the
    overworld regions the anchor is a cave and the entrance is not."""
    from worlds.eldenring.region_open_flags import REGION_OPEN_FLAGS
    differing = [r for r in ("Limgrave", "Liurnia", "Caelid", "Altus", "Weeping")
                 if r in REGION_GRACE_POINTS
                 and entrance_grace(REGION_GRACE_POINTS[r], r) != REGION_OPEN_FLAGS.get(r)]
    assert set(differing) == {"Limgrave", "Liurnia", "Caelid", "Weeping"}, (
        "the entrance rule has collapsed onto REGION_OPEN_FLAGS for %s. That table is a region-open "
        "detection anchor, not a front door -- it grants Murkwater Cave for Limgrave." % differing)
    assert entrance_grace(REGION_GRACE_POINTS["Altus"], "Altus") == REGION_OPEN_FLAGS["Altus"] == 76301


def test_empty_input_fails_rather_than_inventing_an_answer():
    """CONTRIBUTING rule 1: a derivation that cannot answer must FAIL, not answer."""
    with pytest.raises(ValueError):
        entrance_grace([])
