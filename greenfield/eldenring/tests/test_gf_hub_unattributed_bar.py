"""#1021 -- hub fallback is not evidence that an award is reachable from the hub."""

from ..core import _NO_PROGRESSION_APS
from ..tables.data import HUB, LOCATIONS
from ..features.progression_surface import _world_barred_aps
from ..tables.location_tags import HUB_UNATTRIBUTED_APS, LOCATION_TAGS


def test_hub_unattributed_census_is_nonempty_and_exact():
    hub = {ap for (_name, ap, _flag) in LOCATIONS[HUB]}
    expected = {ap for ap in hub if not LOCATION_TAGS.get(ap)}
    assert HUB_UNATTRIBUTED_APS == expected
    # 53 -> 50 on 2026-09-08, two independent removals composed:
    #  * world#1518: the derived tutorial-popup family took f550000 "About Sites of Grace" and
    #    f550210 "About Summoning Other Players" out of the corpus; both were filed under the hub,
    #    and no hub check gained or lost a tag.
    #  * #1511 (255's notebook): f1049557700 (Larval Tear) left the HUB for Consecrated Snowfield --
    #    its one map lot 1049550700 decodes to tile m60_49_55, so the "multiple scattered copies
    #    share these flags" premise that filed every Larval Tear in the hub never applied to it.
    #    Exactly one row left and none joined. The check is NOT unbarred by the move --
    #    gen_data._REGION_OVERRIDE_UNCONFIRMED_FLAGS carries it now, so it keeps the same DEFAULTED
    #    progression bar this census was giving it, by a different lever.
    # #1538: 50 -> 49. Exactly AP7773851 / f520800 (Bloodfiend Hexer ashes)
    # leaves the hub for Rivermouth Cave / Gravesite on native lot and event evidence.
    # It retains its DEFAULTED progression bar; no other member changes.
    assert len(expected) == 49, "re-measure the regenerated untagged-hub census"


def test_hub_unattributed_checks_are_permanently_barred():
    assert HUB_UNATTRIBUTED_APS <= _NO_PROGRESSION_APS

    class World:
        gf_capital_reconciler = False

    assert HUB_UNATTRIBUTED_APS <= _world_barred_aps(World())


def test_balled_up_is_in_the_bar():
    rows = [ap for (name, ap, _flag) in LOCATIONS[HUB] if "Balled Up" in name]
    assert len(rows) == 1
    assert rows[0] in HUB_UNATTRIBUTED_APS
