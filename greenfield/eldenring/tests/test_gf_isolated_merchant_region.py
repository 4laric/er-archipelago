"""The Liurnia Isolated Merchant's 16 checks are RAYA LUCARIA ACADEMY region, not Liurnia -- #252.

MOTIVATING CASE (rule 11). #252: a player hit `Fevor's Cookbook [2] - from Isolated Merchant
[f68220]` holding a Stormveil Lock, on a seed whose spoiler listed it in sphere 1. The merchant
sits behind the Academy Glintstone Key -- Alaric in game, twice: 2026-08-01 "not accessible
without the raya lucaria key", 2026-08-04 "same deal for that merchant ... he's only accessible
once you have academy". His only physical instance stands on the academy island ring
(merchant_shops.tsv: talk 801176000 / entity 32001720, m60_35_45, ~46 m above the lake); the
tile's anchor grace is South Raya Lucaria Gate (76205), a crest-warp destination, and every route
onto the ring is a crest warp reading Academy Glintstone Key POSSESSION (key_item_gates.tsv: the
game's only three goods-8109 checks, one of them $Event(1035452600) in m60_35_45_00 -- this tile).

WHY THE REGION AND NOT THE SURFACE BAR THIS FILE USED TO GUARD (#350). From 2026-08-01 to
2026-08-04 the 16 sat in gen_data._SURFACE_EXCLUDE_FLAGS -- and that instrument DOES NOT BIND
FILL: SURFACE_EXCLUDE_APS is consumed by the surface SELECTION (features/progression_surface)
but is absent from core._NO_PROGRESSION_APS, the item_rule fill actually obeys. Measured on main
2026-08-04: f68220's item_rule accepted a Lock and the check was reachable with the Liurnia Lock
alone -- the bar trimmed the advertisement while fill stayed free to recreate exactly the
stranding #252 reported. The lever that binds is the REGION: in Raya Lucaria Academy the checks
demand the Academy lock chain (REGION_PARENT gates the academy under Liurnia) like every other
academy check, and they may host progression again -- behind the right door.

WHY A DERIVED POPULATION, RATHER THAN TRUSTING THE 16 LITERALS IN gen_data. The gate is on the
MERCHANT: 16 checks sit behind that one door, and the report named one of them. A pin list that
drifts from the merchant's actual stock would re-open the hole silently -- so this re-derives the
population from the committed tables every run and fails if pins and tsv disagree in EITHER
direction (a new row appears unpinned, or a pin goes stale).

🛑 AND THE TRAP THAT MAKES THE DERIVATION LOOK WRONG. All 16 rows list TWO sellers -- the
Isolated Merchant AND the Twin Maiden Husks at the HUB -- which reads as "always reachable,
nothing to fix". It is not: the Twin Maidens only stock a merchant's inventory once you hand them
that merchant's BELL BEARING, which drops from the merchant, behind the same door.
`merchant_shops.tsv` attributes at BLOCK level (#220): it records who CAN open a row, never
whether their stock is unlocked.

Region is asked as REGION EQUALITY with the in-academy seed f14007990 (near Schoolhouse
Classroom), not as membership (er-swept-into-the-wrong-region).
"""
import ast
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)
pytestmark_repo = pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)

# The merchant instance, by the only key that identifies him uniquely: name + the map tile he
# stands on. "Isolated Merchant" alone is ambiguous -- the game reuses it on three tiles
# (m60_35_45, m60_48_41, m60_41_32) and only this one is Academy-gated.
MERCHANT = "Isolated Merchant"
TILE = "m60_35_45"
ACADEMY = "Raya Lucaria Academy"
ANCHOR_FLAG = 14007990     # Golden Seed - near Schoolhouse Classroom: undisputed academy ground
REPORTED = 68220           # the check #252 was filed about

# flag -> AP id, pinned: the region move must not renumber (positional ids are stable).
EXPECTED_APS = {
    68220: 7770136, 69710: 7770187, 69750: 7770191, 69910: 7770195,
    160760: 7770390, 160780: 7770391, 160800: 7770392, 160810: 7770393,
    # 7774841 -> 7774857 (2026-08-07): +16 positional shift, same cause as test_gf_academy_key_pocket.
    # 7774857 -> 7774856 (2026-08-07): same one-check retirement as test_gf_academy_key_pocket.
    # 7774856 -> 7774732 (2026-08-19, #330): -124 worldless Rada Fruit rows removed before it; the
    # three 777039x pins sit ahead of every removal and do not move. Same never-blanket-a-delta rule.
    # 7774732 -> 7774742 -> 7774677 (2026-08-19: +10 Rada restores, then -65 cull). Flag-verified.
    # 160820: 7774759 (main/#898) -> 7774682 on this branch (the census +9 and the cull -86 both
    # land before it); flag-verified. The three below sit under the watermark and do not move.
    160820: 7774682, 160880: 7770394, 160890: 7770395, 160910: 7770396,
    160920: 7770397, 160930: 7770398, 160940: 7770399, 160950: 7770400,
}


def _tsv(path):
    hdr = None
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if hdr is None:
                hdr = parts
                continue
            yield dict(zip(hdr, parts))


def _derived_flags():
    gf = os.path.join(_ROOT, "greenfield")
    rows = {r["row_id"] for r in _tsv(os.path.join(gf, "merchant_shops.tsv"))
            if r.get("merchant_name") == MERCHANT and r.get("map_id") == TILE}
    assert rows, (
        f"no ShopLineupParam rows attributed to {MERCHANT} on {TILE}. Either merchant_shops.tsv "
        "was re-emitted with different columns, or the merchant moved -- do not 'fix' this by "
        "deleting the assertion (an empty derivation is a FAILURE, not a clean run).")
    flags, all_stock = set(), set()
    for r in _tsv(os.path.join(gf, "shop_rows.tsv")):
        if str(r.get("stock_flag", "")).strip().isdigit():
            all_stock.add(int(r["stock_flag"]))
            if r["row_id"] in rows:
                flags.add(int(r["stock_flag"]))
    return rows, flags, all_stock


def _gen_data_literal(name):
    """A top-level literal from gen_data.py, by AST. 🛑 `import gen_data` DIES in any environment
    without the artifact tree (it SystemExits on the finale derivation, by design) -- importing it
    here would make this gate pass only where artifacts exist, the dormant-gate shape this repo
    keeps paying for. The declared set is source, so read the source."""
    src = os.path.join(_ROOT, "greenfield", "gen_data.py")
    with open(src, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    raise AssertionError(f"{name} not found in gen_data.py")


def _override_table():
    node = _gen_data_literal("FLAG_REGION_OVERRIDE")
    assert isinstance(node, ast.Dict), "FLAG_REGION_OVERRIDE is no longer a dict literal"
    return {k.value: v.value for k, v in zip(node.keys, node.values)
            if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)}


def _surface_excluded():
    call = _gen_data_literal("_SURFACE_EXCLUDE_FLAGS")
    assert isinstance(call, ast.Call), "_SURFACE_EXCLUDE_FLAGS is no longer frozenset({...})"
    out = {int(e.value) for e in call.args[0].elts if isinstance(e, ast.Constant)}
    assert out, "parsed an EMPTY exclusion set -- the literal moved, this is not a pass"
    return out


def _data_locations():
    src = os.path.join(_ROOT, "greenfield", "eldenring", "data.py")
    with open(src, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "LOCATIONS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("LOCATIONS not found in data.py")


def _region_of_flag(locations, flag):
    hits = [(region, name, ap) for region, rows in locations.items()
            for (name, ap, f) in rows if f == flag]
    assert len(hits) == 1, f"flag {flag} appears {len(hits)} times in data.py: {hits}"
    return hits[0]


@pytestmark_repo
def test_the_derivation_sees_the_merchant():
    """Rule 2: an empty result is a failure. If this shrinks, the join broke, not the game."""
    rows, flags, _ = _derived_flags()
    assert len(rows) >= 15, f"only {len(rows)} shop rows for {MERCHANT}@{TILE}"
    assert len(flags) >= 15, f"only {len(flags)} check flags derived; expected the full stock"


@pytestmark_repo
def test_every_flag_this_merchant_sells_is_pinned_to_the_academy():
    """The lever itself, both directions: every derived stock flag carries a FLAG_REGION_OVERRIDE
    pin to Raya Lucaria Academy, and every SHOP stock flag pinned to the academy is one this
    merchant actually sells (a stale pin is as much drift as a missing one)."""
    _, flags, all_stock = _derived_flags()
    table = _override_table()
    unpinned = sorted(f for f in flags if table.get(f) != ACADEMY)
    assert not unpinned, (
        f"{len(unpinned)} check(s) sold by {MERCHANT}@{TILE} lack the {ACADEMY!r} region pin: "
        f"{unpinned}. The gate is the merchant, not the item -- pin the whole stock in "
        "gen_data.FLAG_REGION_OVERRIDE (NOT _SURFACE_EXCLUDE_FLAGS, which does not bind fill, "
        "#350).")
    stale = sorted(f for f, reg in table.items()
                   if reg == ACADEMY and f in all_stock and f not in flags)
    assert not stale, (
        f"{len(stale)} shop flag(s) pinned to {ACADEMY!r} are no longer attributed to "
        f"{MERCHANT}@{TILE}: {stale}. Either the tsv regressed or the pin outlived the stock.")


@pytestmark_repo
def test_the_surface_bar_is_retired_for_the_stock():
    """Region-gated AND surface-barred is double-booking: the bar reads as a second source of
    truth and hides which lever binds. The pocket's overworld checks keep the same rule
    (test_gf_academy_key_pocket)."""
    _, flags, _ = _derived_flags()
    double = sorted(flags & _surface_excluded())
    assert not double, (
        f"{len(double)} merchant check(s) are BOTH region-pinned and surface-excluded: {double}. "
        "The region already gates them behind the Academy lock; drop the _SURFACE_EXCLUDE_FLAGS "
        "rows (they never bound fill anyway -- #350).")


@pytestmark_repo
def test_the_generated_world_files_the_stock_in_the_academy():
    """data.py (the generated truth fill consumes): all 16 sit in the SAME region list as the
    in-academy anchor seed, their AP ids unmoved by the move."""
    locations = _data_locations()
    anchor_region, _, _ = _region_of_flag(locations, ANCHOR_FLAG)
    assert anchor_region == ACADEMY, f"the m14 anchor seed moved?! {anchor_region!r}"
    _, flags, _ = _derived_flags()
    assert flags == set(EXPECTED_APS), (
        f"the merchant's stock changed: {sorted(flags ^ set(EXPECTED_APS))}. Re-derive "
        "EXPECTED_APS deliberately -- it pins the flag->ap_id mapping across the region move.")
    for flag, ap_id in EXPECTED_APS.items():
        region, name, ap = _region_of_flag(locations, flag)
        assert region == anchor_region, (
            f"f{flag} ({name!r}) is in {region!r}, not {anchor_region!r} -- a Liurnia Lock alone "
            "must not put a player in front of this merchant (crest-warp ring, "
            "key_item_gates.tsv)")
        assert ap == ap_id, f"f{flag} AP id moved: {ap} != {ap_id} -- the region move must not renumber"


@pytestmark_repo
def test_the_shipped_tags_no_longer_surface_exclude_the_stock():
    """location_tags.py (the shipped projection of the gen_data set): the 16 AP ids are out of
    SURFACE_EXCLUDE_APS, so the surface math and the region agree about who gates these checks."""
    src = os.path.join(_ROOT, "greenfield", "eldenring", "location_tags.py")
    with open(src, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "SURFACE_EXCLUDE_APS" for t in node.targets):
            aps = set(ast.literal_eval(node.value.args[0]))
            leftovers = sorted(set(EXPECTED_APS.values()) & aps)
            assert not leftovers, (
                f"{len(leftovers)} merchant AP id(s) still in the shipped SURFACE_EXCLUDE_APS: "
                f"{leftovers} -- regen after editing gen_data (the shipped file is generated).")
            return
    raise AssertionError("SURFACE_EXCLUDE_APS not found in location_tags.py")


@pytestmark_repo
def test_the_reported_check_is_covered_end_to_end():
    """Rule 11: the case that motivated the gate is the acceptance test, by name and number."""
    _, flags, _ = _derived_flags()
    assert REPORTED in flags, "the derivation no longer sees f68220, the flag #252 was filed about"
    assert _override_table().get(REPORTED) == ACADEMY, (
        "f68220 -- the reported check -- is not region-pinned to the academy")


# ---------------------------------------------------------------------------------------------
# The fill-binding half: a generated multiworld demands the Academy lock for the merchant's
# stock. Runs where Archipelago is installed (the `tests` job); AP-free environments run the
# source half above. This is the assertion #350 says a surface test can never make: it asks the
# item_rule and the reachability fill actually uses, not the advertised surface.
# ---------------------------------------------------------------------------------------------
try:
    from test.bases import WorldTestBase
    from BaseClasses import CollectionState
    from worlds.eldenring.data import REGIONS
    _HAVE_AP = True
except ImportError:
    _HAVE_AP = False

if _HAVE_AP:

    class _MerchantBindsMixin:
        # NOT a TestCase: pytest's unittest integration collects every TestCase subclass whatever
        # its name (see test_gf_academy_key_pocket for the phantom-generation story). The default
        # battery is disabled: this suite is surgical.
        run_default_tests = False
        REPORTED_SUFFIX = "from Isolated Merchant [f68220]"
        ANCHOR_SUFFIX = "[f14007990]"
        OLD_LIURNIA_NAME = "Liurnia :: Fevor's Cookbook [2] - from Isolated Merchant [f68220]"
        STOCK_SUFFIXES = tuple(f"from Isolated Merchant [f{f}]" for f in EXPECTED_APS)

        def _find(self, suffix):
            for loc in self.multiworld.get_locations(1):
                if loc.name.endswith(suffix):
                    return loc
            return None

        def _stock(self):
            return [l for l in self.multiworld.get_locations(1)
                    if l.name.endswith(self.STOCK_SUFFIXES)]

        def test_the_stock_demands_the_academy_lock(self):
            reported = self._find(self.REPORTED_SUFFIX)
            anchor = self._find(self.ANCHOR_SUFFIX)
            if reported is None:
                # Academy sealed this roll: the whole stock must be sealed WITH it -- and the old
                # Liurnia-named check must not exist under any roll.
                self.assertIsNone(anchor, "stock sealed but the academy anchor exists -- split region?")
                self.assertEqual(self._stock(), [], "f68220 sealed but siblings of the stock exist")
                self.assertIsNone(self._find(self.OLD_LIURNIA_NAME))
                return
            self.assertIsNotNone(anchor, "stock kept but the academy anchor is missing")
            stock = self._stock()
            self.assertEqual(len(stock), 16, sorted(l.name for l in stock))
            for loc in stock:
                self.assertIs(loc.parent_region, anchor.parent_region,
                              f"{loc.name}: REGION equality, not membership -- the stock must live "
                              "where the academy anchor lives (er-swept-into-the-wrong-region)")
            lock = f"{reported.parent_region.name} Lock"
            # The stock may host progression again -- the OLD bar (EXCLUDED-shaped item_rule) must
            # not have survived the move; the gate is the region now.
            probe = self.world.create_item(lock)
            self.assertTrue(probe.advancement)
            for loc in stock:
                self.assertTrue(loc.item_rule(probe),
                                f"{loc.name} still refuses advancement -- a second, stale bar?")
            # Locks are PRE-PLACED on rollable checks (the lock chain), not pooled -- an
            # "everything except X" state must harvest placed items as well as the pool.
            everything = (list(self.multiworld.itempool)
                          + list(self.multiworld.precollected_items[1])
                          + [l.item for l in self.multiworld.get_locations(1) if l.item is not None])
            state = CollectionState(self.multiworld)
            for item in everything:
                if item.advancement and item.name != lock:
                    state.collect(item, prevent_sweep=True)
            for loc in stock:
                self.assertFalse(loc.can_reach(state),
                                 f"every advancement item EXCEPT {lock!r} reaches {loc.name} -- "
                                 "this is the #252 stranding shape (a Liurnia Lock alone opened "
                                 "the merchant)")
            state.collect(self.world.create_item(lock), prevent_sweep=True)
            for loc in stock:
                self.assertTrue(loc.can_reach(state), f"{lock!r} itself must open {loc.name}")

    class TestMerchantAllRegionsKept(_MerchantBindsMixin, WorldTestBase):
        # every base region kept -> the academy EXISTS and the bind is exercised, deterministically.
        game = "Elden Ring"
        options = {"num_regions": len(REGIONS)}   # ALL regions kept; 30 -> 28 when
        # Charo's and Stone Coffin merged into Cerulean (#526). A literal here is the
        # #404 mistake -- the documented maximum drifting past what the option accepts.

    class TestMerchantDefaultShape(_MerchantBindsMixin, WorldTestBase):
        # the shipped default shape; the academy may roll sealed, in which case the co-seal branch
        # asserts instead (deterministic pass either way, no census skips).
        game = "Elden Ring"
        options = {"num_regions": 6}


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-v", os.path.abspath(__file__)]))
