"""`unobtainableLocations` -- the tracker is told which checks THIS seed can never award.

THE REPORT (Ace, 2026-09-13): Haligtree 116/123 with both Haligtree bosses dead; the leftovers
included Millicent's `Somber Ancient Dragon Smithing Stone [f400325]` (ap 7770602), a reward whose
questline starts with Gowry in Caelid -- and Caelid was not kept. The tracker listed it under
Haligtree because `locationRegions` only says WHERE a check is.

Three claims, each pinned separately:
  1. The reviewed route table is well-formed: real region names, real check flags, no route that
     names the check's own region (that is not a prerequisite, it is the check).
  2. The EMISSION is right per seed: a full-map seed hides nothing; a seed that keeps the
     Haligtree without Caelid hides exactly Millicent's four Prayer Room rewards; every id emitted
     is in `locationRegions` (a subset by construction, pinned anyway); the wire validates.
  3. The KEEPER: every strong cross-region row in questline_dag.tsv (sense=set, single,
     cross_region=yes) is either covered by a route or named in REVIEW_PENDING with a reason. A
     new datamine result therefore fails here instead of shipping unreviewed, and a pending row
     cannot become a route without the reason being deleted in the same diff.

AP-side semantics are deliberately untouched -- see features/unobtainable_locations.py -- so
there is no fill assertion here; the missable item-rule already owns that.
"""
import csv
import os

import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")
from worlds.eldenring import contract  # noqa: E402
from worlds.eldenring.features.unobtainable_locations import (  # noqa: E402
    REVIEWED_QUEST_ROUTES, REVIEW_PENDING, prerequisite_regions_by_flag, unobtainable_ids)
from worlds.eldenring.tables.data import HUB, LOCATIONS, REGIONS  # noqa: E402

GAME = "Elden Ring"
_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The Ace rows, stated independently of the feature. 7770598 (Heirloom) is NOT here on purpose:
# #1555 moved it to Caelid, so on current data a seed without Caelid does not contain it at all.
MILLICENT_HALIGTREE = {
    7770599: 400321,   # Unalloyed Gold Needle - around Prayer Room
    7770600: 400323,   # Millicent's Prosthesis
    7770601: 400324,   # Miquella's Needle
    7770602: 400325,   # Somber Ancient Dragon Smithing Stone (Ace's leftover)
}

_FLAG_REGIONS = {}
for _rn, _rows in LOCATIONS.items():
    for (_n, _ap, _fl) in _rows:
        _FLAG_REGIONS.setdefault(int(_fl), set()).add(_rn)


# ---- 1. the table ----------------------------------------------------------------------------
def test_contract_key_is_optional_int_list_and_moves_the_hash():
    key = contract.BY_NAME["unobtainableLocations"]
    assert key.shape == "INT_LIST"
    assert key.required is False, "an older apworld omits it; the client must stay inert, not fail"
    assert contract.UNOBTAINABLE_LOCATIONS == "unobtainableLocations"
    # A top-level key IS folded into CONTRACT_HASH (unlike OPTIONS_SUBKEYS), which is why the
    # CONTRACT-VERSIONS ledger row for this window records the move and the client bridge.
    assert "unobtainableLocations" in "\n".join(k.name for k in contract.CONTRACT)


def test_every_route_names_real_regions_and_real_check_flags():
    assert len(REVIEWED_QUEST_ROUTES) >= 10, "the table shrank below the reviewed set"
    for flag, regions in REVIEWED_QUEST_ROUTES.items():
        assert regions, "flag %d has an empty route -- delete the row instead" % flag
        for r in regions:
            assert r in REGIONS, "route for f%d names %r, not a tables.regions name" % (flag, r)
            assert r != HUB, "the hub is always kept; a route through it is a no-op (f%d)" % flag
        own = _FLAG_REGIONS.get(flag)
        assert own, "f%d has no check in data.LOCATIONS; a route for it hides nothing" % flag
        assert not (set(regions) & own), (
            "f%d's route names its own region %s -- that is the check, not a prerequisite"
            % (flag, sorted(set(regions) & own)))


def test_pending_rows_do_not_overlap_routes_and_carry_reasons():
    assert REVIEW_PENDING, "the pending list is the keeper's second bucket; it must exist"
    assert not (set(REVIEW_PENDING) & set(REVIEWED_QUEST_ROUTES)), "a flag is in both buckets"
    for flag, why in REVIEW_PENDING.items():
        assert isinstance(why, str) and len(why.split()) >= 6, "f%d needs a real reason" % flag


def test_the_ace_rows_are_routed_through_caelid():
    routes = prerequisite_regions_by_flag()
    for ap_id, flag in MILLICENT_HALIGTREE.items():
        assert "Caelid" in routes[flag], (ap_id, flag)
        assert "Haligtree" in _FLAG_REGIONS[flag], "the row moved; re-check the report"


# ---- 2. the pure function ---------------------------------------------------------------------
def test_pure_function_hides_millicent_when_caelid_is_dropped():
    rows = {"Haligtree": LOCATIONS["Haligtree"], HUB: LOCATIONS[HUB]}
    kept_without_caelid = ["Haligtree", "Altus", "Mountaintops of the Giants", "Limgrave"]
    got = unobtainable_ids(kept_without_caelid, HUB, rows)
    assert got == sorted(MILLICENT_HALIGTREE), got
    # ...and NOTHING once every station region is kept: the route is a conjunction.
    kept_all_stations = kept_without_caelid + ["Caelid"]
    assert unobtainable_ids(kept_all_stations, HUB, rows) == []
    # Dropping a different station (Altus) hides the same four -- any missing leg is enough.
    assert unobtainable_ids(["Haligtree", "Caelid", "Mountaintops of the Giants"], HUB, rows) \
        == sorted(MILLICENT_HALIGTREE)


def test_pure_function_only_reports_rows_it_was_given():
    # The emitter scopes rows to the seed; the function must not invent ids from the corpus.
    rows = {"Limgrave": LOCATIONS["Limgrave"]}
    got = unobtainable_ids(["Limgrave"], HUB, rows)     # Mt. Gelmir dropped -> Istvan's set
    assert 7900255 in got, "Scaled Greaves (f1042397500) needs the Volcano Manor letter"
    assert not (set(got) & set(MILLICENT_HALIGTREE)), "Haligtree rows were not in the input"
    assert unobtainable_ids(["Limgrave", "Mt. Gelmir"], HUB, rows) == []


# ---- 3. the emission --------------------------------------------------------------------------
class FullMap(WorldTestBase):
    game = GAME
    options = {"num_regions": 0}

    def test_full_map_emits_an_empty_list_not_an_absent_key(self):
        sd = self.world.fill_slot_data()
        assert contract.UNOBTAINABLE_LOCATIONS in sd, "absent means 'old apworld' to the client"
        assert sd[contract.UNOBTAINABLE_LOCATIONS] == []
        assert set(self.world._kept()) == set(REGIONS), "0 = the whole map; the premise of this test"
        contract.validate_slot_data(sd, strict=True)


class HaligtreeWithoutCaelid(WorldTestBase):
    game = GAME
    # The first TWO regions on the vanilla path (Limgrave, Weeping -- one region alone mints too
    # little progression for start_regions) plus the Malenia goal, which force-keeps the
    # Haligtree. Caelid is none of those, so Millicent can never be met at Gowry's shack.
    options = {"num_regions": 2, "num_regions_order": "vanilla_order", "goal": "malenia"}

    def test_millicents_prayer_room_rewards_are_hidden(self):
        kept = set(self.world._kept())
        assert "Haligtree" in kept and "Caelid" not in kept, sorted(kept)
        sd = self.world.fill_slot_data()
        got = sd[contract.UNOBTAINABLE_LOCATIONS]
        for ap_id in MILLICENT_HALIGTREE:
            assert ap_id in got, (ap_id, got)
        haligtree_ids = set(sd[contract.LOCATION_REGIONS]["Haligtree"])
        assert set(MILLICENT_HALIGTREE) <= haligtree_ids, "the rows must still be IN the seed"
        # Subset of locationRegions by construction -- pinned, because the client drops any id it
        # cannot place and would silently hide nothing.
        placed = {i for ids in sd[contract.LOCATION_REGIONS].values() for i in ids}
        assert got and set(got) <= placed, sorted(set(got) - placed)
        assert got == sorted(set(got)), "sorted, unique: the wire is a function of the seed"
        contract.validate_slot_data(sd, strict=True)

    def test_ap_side_is_untouched(self):
        # The hidden checks still exist for the multiworld as ordinary addressed locations: hidden
        # from the tracker, not removed from the seed (the inherited test_fill fills them).
        own = {loc.address for loc in self.multiworld.get_locations(self.player)}
        for ap_id in MILLICENT_HALIGTREE:
            loc = self.multiworld.get_location(
                next(n for (n, a, _f) in LOCATIONS["Haligtree"] if a == ap_id), self.player)
            assert loc.address == ap_id and ap_id in own


# ---- 4. the keeper -----------------------------------------------------------------------------
def _dag_rows():
    path = os.path.join(_PKG, "questline_dag.tsv")
    if not os.path.isfile(path):
        pytest.skip("questline_dag.tsv not installed beside the package -- keeper would run BLIND")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(
            (ln for ln in fh if not ln.lstrip().startswith("#")), delimiter="\t")


def test_every_strong_cross_region_dag_row_is_routed_or_pending():
    strong = {}
    seen = 0
    for r in _dag_rows():
        seen += 1
        if (r.get("cross_region") or "").strip() != "yes":
            continue
        if (r.get("sense") or "").strip() != "set":
            continue
        if (r.get("group_semantics") or "").strip() != "single":
            continue
        flag = int((r.get("target_flag") or "0").strip() or 0)
        strong.setdefault(flag, set()).add((r.get("source_region") or "").strip())
    assert seen > 1000, "questline_dag.tsv parsed to %d rows -- the keeper went blind" % seen
    assert len(strong) >= 15, "the strong cross-region class shrank to %d targets" % len(strong)
    routes = prerequisite_regions_by_flag()
    unreviewed = {f: s for f, s in strong.items() if f not in routes and f not in REVIEW_PENDING}
    assert unreviewed == {}, (
        "strong cross-region DAG rows with neither a route nor a REVIEW_PENDING reason: %s"
        % sorted(unreviewed.items()))
    # A routed flag's evidenced source region must be ON its route (or be the hub): a route that
    # contradicts the evidence is a review error, not a refinement.
    covered = 0
    for flag, sources in strong.items():
        if flag in routes:
            covered += 1
            missing = {s for s in sources if s and s != HUB and s not in routes[flag]}
            assert not missing, "f%d route %s omits evidenced source region(s) %s" % (
                flag, sorted(routes[flag]), sorted(missing))
    assert covered >= 5, "fewer routed flags than the reviewed table claims: %d" % covered
