"""The Academy key pocket: its two overworld checks are RAYA LUCARIA region, not Liurnia.

MOTIVATING CASE (rule 11). lavakoala6 (Nexus, 2026-08-04) generated a seed whose spoiler put
`Golden Seed - near Main Academy Gate [f1035467100]` in SPHERE 1; in game the seed sits on the
broken east-bridge span at deck height (world (8972, 313, 11897) -- 75 m ABOVE the East Gate
Bridge Trestle grace below it), inside the Academy crest-warp pocket. Alaric, in game, same day:
"you can't access without academy key (and academy lock in our mod)". Every route into the pocket
is a crest-warp that reads Academy Glintstone Key POSSESSION (key_item_gates.tsv: the game's only
three goods-8109 checks, $Event(1035452600)/(1035462600)/(1036472600)), and the pocket ground is
play-region 14000 -- ACADEMY, not Liurnia 62000 (grace_ground.tsv row for grace 76206). A Liurnia
Lock alone therefore cannot put a player in front of this check, and logic that says otherwise
strands runs -- the same shape as the Isolated Merchant, #252, one tile over.

WHY THIS INVERTS test_the_walked_golden_seed_is_no_longer_barred (2026-08-01). That pin trusted
"WALKED AND CLEARED": a misattribution. On 08-01 the descriptor for f1035467100 read "near Academy
Gate Town" -- an anchor 872 m away and 27th-nearest (corrected 08-02 in location_descriptions.tsv)
-- and the seed actually collected on that walk was f1036447300, the Gate Town seed at lake level
(see its _REGION_CONFIRMED_FLAGS entry). Nobody has stood at f1035467100 without the key.

WHY THE REGION AND NOT A SURFACE BAR (#350). SURFACE_EXCLUDE_APS is consumed by the surface
SELECTION but is absent from core._NO_PROGRESSION_APS, the item_rule fill actually obeys -- a bar
would hide the check from the advertised surface while fill stays free to place progression on it.
The region is the lever that binds: in the Raya Lucaria Academy region the check demands the
Academy lock like every other academy check (er-region-confirmed-is-not-surface-exclude).

The Ash of War f1035467700 (Yura's invasion step; the summon sign stands in the same courtyard
pocket, common 90005774 / entity 1035460700 on m60_35_46) rides the same evidence.

Region is asked as REGION EQUALITY with the in-academy seed f14007990 (near Schoolhouse
Classroom), not as membership -- a check swept into the WRONG region passes membership-shaped
tests while being unobtainable (er-swept-into-the-wrong-region).
"""
import ast
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:  # direct/unittest fallback
    sys.path.insert(0, HERE)
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(HERE)

POCKET = {
    # 7774386 -> 7774402 (2026-08-07): +16 unplaced-global rows landed BEFORE this one, and ap ids
    # are positional (BASE_AP + index). NOTE its sibling below did NOT move -- the shift applies
    # only to locations after the insertion point, so do not blanket-add 16 to a pinned id.
    # 7774402 -> 7774401 (2026-08-07): one cut-content check (f400081) retired ahead of it.
    # Its sibling below does NOT move -- it sits before the removal, so never blanket-apply a delta.
    # 7774401 -> 7774277 and 7772688 -> 7772653 (2026-08-19, #330): 124 worldless Rada Fruit rows
    # left the corpus (_RADA_WORLDLESS); both pins sit after removals this time, and by different
    # amounts (124 vs 35), which is the same never-blanket-a-delta lesson from the other direction.
    # 7774277 -> 7774287 -> 7774237 (2026-08-19: +10 restored Rada rows, then -65 from the
    # worldless-singles cull). Flag-verified each time.
    # 7772653 -> 7772649 (2026-08-19, the cull): the sibling that "never moves" finally moved --
    # 4 culled flags sat before it. There is no pinned id the corpus cannot renumber.
    1035467100: 7774245,   # +5 on the #898 base, +2 more at the 8 audited-tile releases, +1 at the Crimson Hood ruling; flag-verified   # Golden Seed - near Main Academy Gate (the reported check)
    1035467700: 7772650,   # Ash of War: Raptor of the Mists - around Main Academy Gate
}
ANCHOR_FLAG = 14007990     # Golden Seed - near Schoolhouse Classroom: undisputed academy ground
ACADEMY = "Raya Lucaria Academy"


def _gen_data_literal(name):
    """A top-level literal from gen_data.py, by AST -- importing gen_data SystemExits without the
    Windows artifact tree (see test_gf_surface_exclude_isolated_merchant for the full reason)."""
    src = os.path.join(_ROOT, "greenfield", "gen_data.py")
    with open(src, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    raise AssertionError(f"{name} not found in gen_data.py")


def _data_locations():
    """data.py's LOCATIONS dict, parsed from source (AP-free)."""
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


pytestmark_repo = pytest.mark.skipif(_ROOT is None, reason=REPO_ONLY_REASON)


@pytestmark_repo
def test_the_override_pins_both_pocket_checks_to_the_academy():
    """The lever itself: FLAG_REGION_OVERRIDE carries both flags -> Raya Lucaria Academy."""
    node = _gen_data_literal("FLAG_REGION_OVERRIDE")
    assert isinstance(node, ast.Dict), "FLAG_REGION_OVERRIDE is no longer a dict literal"
    table = {k.value: v.value for k, v in zip(node.keys, node.values)
             if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)}
    for flag in POCKET:
        assert table.get(flag) == ACADEMY, (
            f"f{flag} must be FLAG_REGION_OVERRIDE'd to {ACADEMY!r}; got {table.get(flag)!r}. "
            "The tile decode says Liurnia only because grace_region_map files grace 76206 under "
            "the 62000 WARP-MENU bucket; the ground is play-region 14000 (grace_ground.tsv).")


@pytestmark_repo
def test_the_pocket_checks_share_the_academy_region_in_data():
    """data.py (the generated truth fill consumes): both checks sit in the SAME region list as the
    in-academy anchor seed, their AP ids unmoved by the move (positional ids are stable)."""
    locations = _data_locations()
    anchor_region, _, _ = _region_of_flag(locations, ANCHOR_FLAG)
    assert anchor_region == ACADEMY, f"the m14 anchor seed moved?! {anchor_region!r}"
    for flag, ap_id in POCKET.items():
        region, name, ap = _region_of_flag(locations, flag)
        assert region == anchor_region, (
            f"f{flag} ({name!r}) is in {region!r}, not {anchor_region!r} -- a Liurnia Lock cannot "
            "put a player in front of it (Academy crest-warp pocket, key_item_gates.tsv)")
        assert ap == ap_id, f"f{flag} AP id moved: {ap} != {ap_id} -- the region move must not renumber"
        assert "(region unconfirmed)" not in name, name


@pytestmark_repo
def test_the_surface_bar_stays_off_the_pocket():
    """The 07-31 tool stays retired: the fix is the region, NOT _SURFACE_EXCLUDE_FLAGS. A bar here
    would trim the advertised surface while fill keeps placing progression on the check
    (SURFACE_EXCLUDE_APS is absent from core._NO_PROGRESSION_APS -- #350). If someone re-adds it,
    they are re-fighting the 2026-08-01/08-04 record; read the note at _SURFACE_EXCLUDE_FLAGS."""
    call = _gen_data_literal("_SURFACE_EXCLUDE_FLAGS")
    assert isinstance(call, ast.Call), "_SURFACE_EXCLUDE_FLAGS is no longer frozenset({...})"
    excluded = {e.value for e in call.args[0].elts if isinstance(e, ast.Constant)}
    for flag in POCKET:
        assert flag not in excluded, f"f{flag}: region-gated AND surface-barred is double-booking"


# ---------------------------------------------------------------------------------------------
# The fill-binding half: a generated multiworld demands the Academy lock for the pocket. Runs
# where Archipelago is installed (the `tests` job); AP-free environments run the source half above.
# ---------------------------------------------------------------------------------------------
try:
    from test.bases import WorldTestBase
    from BaseClasses import CollectionState
    from worlds.eldenring.data import REGIONS
    _HAVE_AP = True
except ImportError:
    _HAVE_AP = False

if _HAVE_AP:

    class _PocketBindsMixin:
        # NOT a TestCase: pytest's unittest integration collects every TestCase subclass whatever
        # its name, so a WorldTestBase base class here would run as a phantom third generation.
        # The inherited default battery (test_fill & co) is disabled: this suite is surgical
        # (the battery runs with the shipped default options elsewhere), and running it at the
        # num_regions=30 shape would add a NEW random-seed fill surface to CI in a fix PR.
        run_default_tests = False
        SEED = "[f1035467100]"
        AOW = "[f1035467700]"
        ANCHOR = "[f14007990]"
        OLD_LIURNIA_NAME = "Liurnia :: Golden Seed - near Main Academy Gate [f1035467100]"

        def _find(self, suffix):
            for loc in self.multiworld.get_locations(1):
                if loc.name.endswith(suffix):
                    return loc
            return None

        def test_the_pocket_demands_the_academy_lock(self):
            seed = self._find(self.SEED)
            anchor = self._find(self.ANCHOR)
            if seed is None:
                # Academy sealed this roll: the pocket must be sealed WITH it -- and the old
                # Liurnia-named check must not exist under any roll.
                self.assertIsNone(anchor, "pocket sealed but the academy anchor exists -- split region?")
                self.assertIsNone(self._find(self.AOW), "pocket sealed but the Ash of War exists")
                self.assertIsNone(self._find(self.OLD_LIURNIA_NAME))
                return
            self.assertIsNotNone(anchor, "seed kept but the academy anchor is missing")
            self.assertIs(seed.parent_region, anchor.parent_region,
                          "REGION equality, not membership: the seed must live where the academy "
                          "anchor lives (er-swept-into-the-wrong-region)")
            aow = self._find(self.AOW)
            if aow is not None:
                self.assertIs(aow.parent_region, anchor.parent_region)
            lock = f"{seed.parent_region.name} Lock"
            # Locks are PRE-PLACED on rollable checks (the lock chain), not pooled -- an
            # "everything except X" state must harvest placed items as well as the pool.
            everything = (list(self.multiworld.itempool)
                          + list(self.multiworld.precollected_items[1])
                          + [l.item for l in self.multiworld.get_locations(1) if l.item is not None])
            state = CollectionState(self.multiworld)
            for item in everything:
                if item.advancement and item.name != lock:
                    state.collect(item, prevent_sweep=True)
            self.assertFalse(seed.can_reach(state),
                             f"every advancement item EXCEPT {lock!r} reaches the pocket -- this is "
                             "the sphere-1 defect lavakoala6 reported (a Liurnia Lock alone opened it)")
            state.collect(self.world.create_item(lock), prevent_sweep=True)
            self.assertTrue(seed.can_reach(state), f"{lock!r} itself must open the pocket")

    class TestPocketAllRegionsKept(_PocketBindsMixin, WorldTestBase):
        # every base region kept -> the academy EXISTS and the bind is exercised, deterministically.
        game = "Elden Ring"
        options = {"num_regions": len(REGIONS)}   # ALL regions kept; follows the generated spine
        # Charo's and Stone Coffin merged into Cerulean (#526). A literal here is the
        # #404 mistake -- the documented maximum drifting past what the option accepts.

    class TestPocketDefaultShape(_PocketBindsMixin, WorldTestBase):
        # the shipped default shape; the academy may roll sealed, in which case the co-seal branch
        # asserts instead (deterministic pass either way, no census skips).
        game = "Elden Ring"
        options = {"num_regions": 6}


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-v", os.path.abspath(__file__)]))
