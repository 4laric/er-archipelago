"""#616 -- a check pays as many copies as its vanilla lot slot grants, not always one.

THE BUG
-------
`greenfield/flag_lots.tsv` has carried a `num` column since the faithful flag->lots capture landed,
`gen_data._load_flag_lots` has parsed it into `FLAG_LOTS` all along, and NOTHING EVER READ IT. Every
check paid exactly one of its vanilla item. Four of the game's `Scadutree Fragment` lot slots grant
TWO, so a seed keeping all 46 fragment checks carried 46 units where the base game gives 50 -- and
the Scadutree blessing is a pure function of that number (`SCADU_CUM[20] == 50`, exactly the vanilla
supply), so a full sweep landed a rung low and `features/scadu_supply` documented the gap as a
"known bounded overshoot" rather than fixing it.

THE MOTIVATING CASE IS ap 7900001 -- the Hippo's fragment in Scadu Altus (`map` lot 10441, `num` 2).
It was ALREADY a projected co-check sibling and STILL paid one, which is why widening
`CO_CHECK_FLAGS` was never the fix: the quantity is a property of the LOT SLOT, and no amount of
co-check projection reads it. `test_the_hippo_co_check_pays_two_copies` is that case by name and by
number (CONTRIBUTING rule 11).

🛑 THE JOIN IS ON FullID, NEVER ON THE `name` COLUMN
-----------------------------------------------------
`tools/datamine_flag_lots.py` resolves the `name` column WITHOUT the `lotItemCategory` nibble and
says in as many words that it is "legibility, not load-bearing". Exactly one row collides today:
flag 12017460 / `map` lot 12010460 is `lotItemCategory` 3 -- the ARMOUR nibble -- and its item id
2010000 is the Mushroom Crown, while GOODS 2010000 is the Scadutree Fragment. So the name column
calls an armour row "Scadutree Fragment" and a name join counts 47 lots for 51 units.

That wrong number is not hypothetical: 47/51 was the figure this work started from, and it would
have put `SCADU_INJECTION_TARGET` one unit past a ladder that ends at 50.
`test_the_name_column_join_is_the_bug_this_avoids` pins the disagreement so the cheaper join cannot
quietly come back.
"""
import csv
import os
import sys

import pytest

pytest.importorskip("worlds.eldenring")

from worlds.eldenring.check_lots_data import LOCATION_LOT  # noqa: E402
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from worlds.eldenring.features import filler_curation as fc  # noqa: E402
from worlds.eldenring.features import scadu_supply as ss  # noqa: E402
from worlds.eldenring.item_ids import ITEM_CATALOG, LOCATION_ITEM  # noqa: E402

try:
    from worlds.eldenring.item_ids import LOCATION_UNITS  # noqa: E402
except ImportError:
    # DELIBERATELY TOLERANT. A tree whose `item_ids.py` predates #616 has no LOCATION_UNITS, and a
    # bare import would turn this file into a COLLECTION ERROR -- which reads as a broken checkout
    # rather than as the defect. Absent means "every check pays one", which is exactly what the bug
    # was, so the assertions below then fail on the ARITHMETIC and say 46 against 50 in words.
    LOCATION_UNITS = {}

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)

# lotItemCategory -> FullID top nibble. A DELIBERATE second copy of gen_data's `_LOT_CAT`: this test
# is an ORACLE for the generator, and an oracle that imports the thing it checks agrees with it by
# construction. Six ER categories, stable since the game shipped; if one is ever added, this test
# KeyErrors loudly rather than silently mis-joining.
LOT_CAT = {0: 4, 1: 4, 2: 0, 3: 1, 4: 2, 5: 8, 6: 4}

FRAGMENT = ss.FRAGMENT
# The vanilla supply, and the ONLY number in this file that is a claim rather than a derivation:
# ItemLotParam_map + ItemLotParam_enemy, goods 2010000, 46 lot slots -- 42 x1 and 4 x2.
VANILLA_FRAGMENT_LOTS = 46
VANILLA_FRAGMENT_UNITS = 50
HIPPO_AP = 7900001


def _flag_lots_rows():
    """Every row of greenfield/flag_lots.tsv, as dicts. Repo-only -- the tsv is an INPUT to the
    generator and is not installed alongside the world."""
    if _ROOT is None:
        pytest.skip(REPO_ONLY_REASON)
    path = os.path.join(_ROOT, "greenfield", "flag_lots.tsv")
    if not os.path.isfile(path):
        pytest.skip("greenfield/flag_lots.tsv not present")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _full_id(row):
    return (LOT_CAT[int(row["category"])] << 28) | int(row["item_id"])


def _fragment_rows():
    full = ITEM_CATALOG[FRAGMENT]
    return [r for r in _flag_lots_rows() if _full_id(r) == full]


def _fragment_checks():
    return sorted(ap for ap, nm in LOCATION_ITEM.items() if nm == FRAGMENT)


def _units(ap_id):
    """What the WORLD pays at `ap_id`, in fragments. `LOCATION_UNITS` omits every x1, so an absent
    key is one -- the same default `core.stacked_vanilla_name` applies."""
    return LOCATION_UNITS.get(ap_id, 1)


def _flag_of():
    return {row[1]: row[2] for rows in LOCATIONS.values() for row in rows}


# ---- the join ----------------------------------------------------------------------------------
def test_the_name_column_join_is_the_bug_this_avoids():
    """The `name` column and the FullID join DISAGREE, by exactly one armour row.

    If this ever stops failing the name join, the collision has gone away and the guard below is
    protecting against nothing -- find out why before deleting it."""
    rows = _flag_lots_rows()
    full = ITEM_CATALOG[FRAGMENT]
    by_name = [r for r in rows if (r.get("name") or "").strip() == FRAGMENT]
    by_id = [r for r in rows if _full_id(r) == full]
    assert len(by_id) == VANILLA_FRAGMENT_LOTS, (
        "the FullID join must find exactly the %d vanilla fragment lot slots, found %d"
        % (VANILLA_FRAGMENT_LOTS, len(by_id)))
    assert len(by_name) == VANILLA_FRAGMENT_LOTS + 1, (
        "the name join is supposed to OVER-count by the Mushroom Crown row; it found %d, so the "
        "collision this test pins has changed shape" % len(by_name))
    extra = [r for r in by_name if _full_id(r) != full]
    assert len(extra) == 1
    r = extra[0]
    assert int(r["category"]) == 3 and LOT_CAT[3] == 1, (
        "the over-counted row must be the ARMOUR-nibble one (lotItemCategory 3, flag 12017460 = "
        "the Mushroom Crown), got %r" % (r,))
    assert (int(r["flag"]), r["table"], int(r["lot"])) == (12017460, "map", 12010460)


# ---- the supply --------------------------------------------------------------------------------
def test_vanilla_scadutree_supply_is_fifty_units_over_forty_six_lots():
    rows = _fragment_rows()
    assert len(rows) == VANILLA_FRAGMENT_LOTS
    assert sum(int(r["num"] or 1) for r in rows) == VANILLA_FRAGMENT_UNITS
    # ...and it is exactly the top of the blessing ladder, which is WHY the target is 20. Vanilla
    # budgets a complete sweep to reach level 20 and not a unit further.
    assert ss.SCADU_CUM[ss.SCADU_INJECTION_TARGET] == VANILLA_FRAGMENT_UNITS


def test_every_fragment_check_pays_the_copies_its_own_lot_slot_grants():
    """The per-location oracle: join each fragment check's flag to the tsv on FullID, restrict a
    co-check sibling to ITS OWN (table, lot) -- a family shares one flag, so an unbound join would
    read the whole family -- and demand the world's number.

    Rebuilt from the raw tsv + `check_lots_data.LOCATION_LOT`, so it is an independent answer and
    not `gen_data`'s answer read back."""
    flag_of = _flag_of()
    by_flag = {}
    for r in _fragment_rows():
        by_flag.setdefault(int(r["flag"]), []).append(r)

    checks = _fragment_checks()
    assert len(checks) == VANILLA_FRAGMENT_LOTS, (
        "the world declares %d Scadutree Fragment checks against %d vanilla lot slots -- a check "
        "was gained or lost and every number below is about a different game"
        % (len(checks), VANILLA_FRAGMENT_LOTS))

    wrong = []
    for ap_id in checks:
        cand = by_flag.get(flag_of.get(ap_id), [])
        if ap_id in LOCATION_LOT:
            table, lot = LOCATION_LOT[ap_id]
            cand = [r for r in cand if r["table"] == table and int(r["lot"]) == lot]
        nums = {int(r["num"] or 1) for r in cand}
        if len(nums) != 1 or _units(ap_id) not in nums:
            wrong.append((ap_id, flag_of.get(ap_id), sorted(nums), _units(ap_id)))
    assert not wrong, (
        "these checks pay a different number of copies than their vanilla lot slot grants "
        "(ap_id, flag, lot num(s), world pays): %r" % (wrong,))

    assert sum(_units(a) for a in checks) == VANILLA_FRAGMENT_UNITS, (
        "the seed's fragment checks pay %d unit(s) against vanilla's %d -- the blessing ladder "
        "tops out at SCADU_CUM[20] = %d and this is what fills it"
        % (sum(_units(a) for a in checks), VANILLA_FRAGMENT_UNITS, VANILLA_FRAGMENT_UNITS))
    assert sum(1 for a in checks if _units(a) > 1) == 4, \
        "four of the 46 lot slots are x2; a different count means the capture moved"


def test_the_hippo_co_check_pays_two_copies():
    """ap 7900001, `Scadu Altus :: Scadutree Fragment - Hippo` -- THE reported case.

    It was already a projected co-check sibling (it is in `LOCATION_LOT`) and still paid one, which
    is the whole reason the fix is a lot-QUANTITY read and not another entry in `CO_CHECK_FLAGS`."""
    assert LOCATION_ITEM.get(HIPPO_AP) == FRAGMENT
    assert HIPPO_AP in LOCATION_LOT, (
        "7900001 must still be a co-check sibling -- if it is not, this test no longer pins the "
        "'already a co-check and still paid 1' shape the issue is about")
    assert LOCATION_LOT[HIPPO_AP] == ("map", 10441)
    assert _units(HIPPO_AP) == 2, (
        "the Hippo's fragment lot (map 10441) grants 2 and this check pays %d" % _units(HIPPO_AP))
    row = [r for r in _fragment_rows()
           if r["table"] == "map" and int(r["lot"]) == 10441]
    assert len(row) == 1 and int(row[0]["num"]) == 2
    # Its PRIMARY, on the same flag, is a different item at x1 -- which is what an unbound
    # flag-level join would have smeared across both.
    assert LOCATION_ITEM.get(7773926) != FRAGMENT and _units(7773926) == 1


# ---- what carries the second copy into the pool -------------------------------------------------
def test_every_resolvable_multi_copy_lot_is_a_registered_grant():
    """Every captured source quantity must promote to an exact, grantable stacked AP item."""
    from worlds.eldenring.core import item_name_to_id
    stacked_vanilla_name = getattr(
        __import__("worlds.eldenring.core", fromlist=["core"]), "stacked_vanilla_name", None)
    assert stacked_vanilla_name is not None, (
        "core.stacked_vanilla_name is missing -- nothing promotes a multi-copy location to its "
        "stacked item, so every one of them pays a single copy (#616)")
    assert ss.FRAGMENT_X2 in item_name_to_id
    assert ss.ScaduSupply.ITEM_GRANTS[ss.FRAGMENT_X2] == (ITEM_CATALOG[FRAGMENT], 2)
    assert stacked_vanilla_name(FRAGMENT, HIPPO_AP, item_name_to_id) == (ss.FRAGMENT_X2, 2)
    for ap_id, qty in LOCATION_UNITS.items():
        nm = LOCATION_ITEM.get(ap_id)
        if not nm or nm not in ITEM_CATALOG:
            continue
        assert stacked_vanilla_name(nm, ap_id, item_name_to_id) == (f"{nm} x{qty}", qty)


def test_the_stacked_name_survives_the_filler_tail():
    """The x2 rides the SAME collectathon protection as the x1 -- `_ECONOMY_SUBSTR` matches on
    SUBSTRING, so "Scadutree Fragment x2" is covered by the "Scadutree Fragment" entry.

    It must NOT be added to `COLLECTATHON_ITEMS`: that tuple's own test requires every member to be
    in `ITEM_CATALOG`, and the stack is a feature-minted AP name with no catalog row of its own.
    This is the assertion that says the existing protection reaches it anyway."""
    assert not fc._is_junk_consumable(ss.FRAGMENT_X2), (
        "the filler tail would displace the stacked fragment -- the four vanilla x2 lots would pay "
        "junk instead, which is the test_gf_collectathon_protected failure shape one name over")
    assert ss.FRAGMENT_X2 not in fc.COLLECTATHON_ITEMS


# ---- the live pool ------------------------------------------------------------------------------
WorldTestBase = pytest.importorskip("test.bases").WorldTestBase


class VanillaFragmentUnitsInThePool(WorldTestBase):
    """A whole-map seed with the blessing OFF injects nothing, so the pool's fragment units are
    PURELY what the kept checks pay -- 50, the base game's own supply. This is the end-to-end half:
    the two tests above are about the table, this one is about what `core.create_items` built."""
    game = "Elden Ring"
    run_default_tests = False
    options = {"num_regions": 0, "enable_dlc": 1, "global_scadutree_blessing": 0}

    def test_a_whole_map_seed_carries_the_vanilla_fifty(self):
        try:
            from ._util import world_items
        except ImportError:
            from _util import world_items
        items = [i for i in world_items(self) if i.name in (FRAGMENT, ss.FRAGMENT_X2)]
        stacks = sum(1 for i in items if i.name == ss.FRAGMENT_X2)
        units = sum(2 if i.name == ss.FRAGMENT_X2 else 1 for i in items)
        mode, _t, natural, _w, injected = ss.plan(self.world)
        assert mode == 0 and injected == 0, "blessing is off; nothing may be injected"
        assert len(items) == VANILLA_FRAGMENT_LOTS and stacks == 4, (
            "expected the 46 vanilla checks as 42 x1 + 4 x2, got %d item(s) of which %d stacked"
            % (len(items), stacks))
        assert units == VANILLA_FRAGMENT_UNITS, (
            "a whole-map seed pays %d fragment unit(s); the base game gives %d, and the blessing "
            "ladder needs all 50 to reach level 20" % (units, VANILLA_FRAGMENT_UNITS))
        assert natural == VANILLA_FRAGMENT_UNITS, (
            "scadu_supply.natural_fragments reads %d, the pool holds %d -- plan() and "
            "create_items disagree and the injection would be sized off the wrong number"
            % (natural, units))
