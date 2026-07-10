"""progression_surface (v0.2) -- STANDALONE host harness (no Archipelago, no regen required).

The maintainer regenerates location_tags.py on Windows (build.ps1 -Greenfield); this sandbox has
neither elden_ring_artifacts nor (reliably) the AP framework. So this file tests only the PURE logic
-- the feasibility ladder, the restricted-progression predicate, the allowed-surface computation, the
MajorBoss vocabulary, and the MAJOR_BOSS_EXTRAS identifications against the CURRENT greenfield data --
by stubbing `Options` and loading the pure modules directly. The full MajorBoss tag invariant is
enforced at regen time by the assertion in gen_data.py (this file cross-checks its inputs now).

Run directly:  python3 eldenring_gf/tests/test_gf_progression_surface.py
(Also import-safe under pytest: bare asserts, functions prefixed test_.)
"""
import ast
import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
GF = os.path.dirname(HERE)                      # .../eldenring_gf
GREENFIELD = os.path.dirname(GF)                # .../greenfield


# ---- stub the AP `Options` module so the feature imports without Archipelago ---------------------
def _install_options_stub():
    if "Options" in sys.modules:
        return
    opt = types.ModuleType("Options")

    class _Base:
        def __init__(self, *a, **k):
            pass

    for _n in ("OptionList", "Choice", "Toggle", "DefaultOnToggle", "Range"):
        setattr(opt, _n, type(_n, (_Base,), {}))
    sys.modules["Options"] = opt


def _load(modname, relpath):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(GF, relpath))
    m = importlib.util.module_from_spec(spec)
    sys.modules[modname] = m
    spec.loader.exec_module(m)
    return m


_install_options_stub()
# minimal package skeleton so the feature's relative imports (..contract, ..registry, ..location_tags)
# resolve without pulling in core.py (which needs Archipelago).
if "eldenring_gf" not in sys.modules:
    _pkg = types.ModuleType("eldenring_gf"); _pkg.__path__ = [GF]; sys.modules["eldenring_gf"] = _pkg
    _fpkg = types.ModuleType("eldenring_gf.features")
    _fpkg.__path__ = [os.path.join(GF, "features")]; sys.modules["eldenring_gf.features"] = _fpkg

contract = _load("eldenring_gf.contract", "contract.py")
_load("eldenring_gf.registry", "registry.py")
location_tags = _load("eldenring_gf.location_tags", "location_tags.py")
data = _load("eldenring_gf.data", "data.py")
boss_data = _load("eldenring_gf.boss_data", "boss_data.py")
ps = _load("eldenring_gf.features.progression_surface", "features/progression_surface.py")


def _major_boss_extras():
    """Extract the MAJOR_BOSS_EXTRAS literal from gen_data.py WITHOUT importing it (importing would run
    the whole data pipeline / need elden_ring_artifacts)."""
    src = open(os.path.join(GREENFIELD, "gen_data.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "MAJOR_BOSS_EXTRAS":
                    return ast.literal_eval(node.value)
    raise AssertionError("MAJOR_BOSS_EXTRAS not found in gen_data.py")


def _apid_region():
    return {aid: reg for reg, locs in data.LOCATIONS.items() for (_nm, aid, _fl) in locs}


# ---- vocabulary ---------------------------------------------------------------------------------
def test_majorboss_in_vocabulary():
    assert "MajorBoss" in contract.IMPORTANT_LOCATION_TYPES
    # selectable by both the surface and the important/big-ticket option (shared vocab)
    assert "MajorBoss" in ps.ProgressionSurface.valid_keys


def test_is_big_ticket_majorboss():
    assert contract.is_big_ticket(["MajorBoss"], {"MajorBoss"})
    assert not contract.is_big_ticket(["Remembrance"], {"MajorBoss"})   # not selected
    # Enia hard-exclude still wins
    assert not contract.is_big_ticket(["MajorBoss", "EniaShop"], {"MajorBoss"})


# ---- ladder -------------------------------------------------------------------------------------
def test_build_ladder_from_majorboss():
    rungs = ps.build_ladder(["MajorBoss"])
    assert rungs[0] == ["MajorBoss"]
    assert rungs[1] == ["MajorBoss", "Remembrance", "GreatRune"]
    assert rungs[2] == ["MajorBoss", "Remembrance", "GreatRune", "Boss", "KeyItem", "Legendary"]
    assert rungs[-1][-2:] == ["Seedtree", "Church"]
    # monotonic widening + no Shop auto-added
    for a, b in zip(rungs, rungs[1:]):
        assert set(a) < set(b)
    assert not any("Shop" in r for r in rungs)


def test_build_ladder_respects_wider_base_and_dedups():
    # a base that already contains a widen group must not re-add it (deduped rungs)
    rungs = ps.build_ladder(["MajorBoss", "Boss", "KeyItem", "Legendary"])
    flat = [frozenset(r) for r in rungs]
    assert len(flat) == len(set(flat)), "rungs must be unique"
    # Shop stays only if the USER put it in the base
    assert all("Shop" in r for r in ps.build_ladder(["MajorBoss", "Shop"]))


def test_build_ladder_empty_selection():
    assert ps.build_ladder([]) == []
    assert ps.selected_surface(["MajorBoss", "Bogus", "Shop"]) == ["MajorBoss", "Shop"]


# ---- restricted-progression predicate (Boss Keys exempt) ----------------------------------------
class _FakeItem:
    def __init__(self, name, player, advancement):
        self.name = name; self.player = player; self.advancement = advancement


def test_restricted_progression_predicate():
    P = 3
    assert ps.is_restricted_progression(_FakeItem("Limgrave Lock", P, True), P)
    assert ps.is_restricted_progression(_FakeItem("Radahn's Great Rune", P, True), P)
    assert ps.is_restricted_progression(_FakeItem("Academy Glintstone Key", P, True), P)
    # Boss Keys are EXEMPT (they'd swamp the tiny surface; boss_locks keeps them reachable)
    assert not ps.is_restricted_progression(_FakeItem("Boss Key: Godrick the Grafted", P, True), P)
    # non-advancement and foreign items are not ours to confine
    assert not ps.is_restricted_progression(_FakeItem("Rune", P, False), P)
    assert not ps.is_restricted_progression(_FakeItem("Limgrave Lock", P + 1, True), P)


# ---- allowed-surface computation over synthetic tags --------------------------------------------
def test_allowed_ap_ids_synthetic():
    tags = {1: ["MajorBoss", "Remembrance"], 2: ["Remembrance"], 3: ["Shop"],
            4: ["MajorBoss", "EniaShop"], 5: ["Boss"]}
    assert ps.allowed_ap_ids(tags, {"MajorBoss"}) == {1}          # 4 excluded by EniaShop
    assert ps.allowed_ap_ids(tags, {"MajorBoss", "Remembrance"}) == {1, 2}
    assert ps.allowed_ap_ids(tags, {"Boss"}) == {5}


# ---- MAJOR_BOSS_EXTRAS structure + identification cross-check against CURRENT data ---------------
def test_major_boss_extras_structure():
    extras = _major_boss_extras()
    assert isinstance(extras, dict) and extras, "MAJOR_BOSS_EXTRAS should be a non-empty dict"
    valid_conf = {"HIGH", "MEDIUM", "LOW", "TODO"}
    apid_region = _apid_region()
    for region, lst in extras.items():
        assert region in data.LOCATIONS, f"extras region {region!r} not a real region"
        for tup in lst:
            assert len(tup) == 5, f"expected (ap_id, flag, boss, drop, confidence), got {tup!r}"
            aid, flag, boss, drop, conf = tup
            assert isinstance(aid, int) and isinstance(flag, int)
            assert conf in valid_conf, f"bad confidence {conf!r} for {boss!r}"
            # every extra ap-id must be a REAL check somewhere in the current data
            assert aid in apid_region, f"{boss!r} ap {aid} is not a real check"
            if conf == "HIGH":
                # HIGH = already filed in the stated region in current data (no regen needed)
                assert apid_region[aid] == region, (
                    f"HIGH extra {boss!r} ap {aid} is in {apid_region[aid]!r}, not {region!r}")
            # MEDIUM/TODO may depend on a FLAG_REGION_OVERRIDE that lands only on regen (e.g. Bayle);
            # the gen_data.py invariant asserts the full in-region requirement at regen time.


def test_region_bosses_in_region_now():
    """The generated boss_arena majors must already be filed under their region in current data --
    this is the arena half of the gen_data MajorBoss invariant, checkable without regen."""
    apid_region = _apid_region()
    for region, lst in boss_data.REGION_BOSSES.items():
        for (aid, _fl, _nm) in lst:
            assert apid_region.get(aid) == region, (
                f"REGION_BOSSES {region!r} ap {aid} filed under {apid_region.get(aid)!r}")


def test_extras_cover_the_zero_major_regions():
    """Every region with no boss_arena major must be covered by an active MAJOR_BOSS_EXTRAS entry.
    (Consecrated Snowfield used to be the exception; it is now folded into Mountaintops of the Giants,
    whose Fire Giant is a boss_arena major, so there are no uncovered zero-major regions left.)"""
    extras = _major_boss_extras()
    arena_regions = {r for r, l in boss_data.REGION_BOSSES.items() if l}
    zero = [r for r in data.LOCATIONS if r != data.HUB and r not in arena_regions]
    covered = set(extras)
    for r in zero:
        assert r in covered, f"zero-major region {r!r} is not covered by an active MAJOR_BOSS_EXTRAS entry"


# ---- synthetic ladder-placement model (documents the confinement/spill intent; no fill_restrictive)
def test_synthetic_star_graph_confinement_model():
    """Model the region-lock star graph: Menu->Hub free; region R reachable iff its Lock is held.
    Greedy: with a precollected lock opening a majored region, the MajorBoss rung hosts the whole chain
    (each opened region's spare major hosts the next lock). Without an anchor and no hub major, rung 0
    places nothing and the ladder widens. This mirrors what fill_restrictive does; it is a pure sanity
    model of the ladder, not the real fill."""
    def confine(locks, region_majors, precollected, rung_classes_seq):
        """Return (placed_count, resolved_rung_index). region_majors: {region: n_major_slots}. Chain
        model: a precollected region is open (its majors are free host slots); placing a lock consumes
        one free slot and (once that lock is collected) opens its region, freeing its majors. A rung
        that includes Seedtree/Shop adds one always-reachable hub slot (the Roundtable Golden Seeds)."""
        remaining = [r for r in locks if r not in precollected]
        for idx, classes in enumerate(rung_classes_seq):
            hub_bootstrap = 1 if ("Seedtree" in classes or "Shop" in classes) else 0
            held = set(precollected)          # open regions
            used = 0                          # host slots consumed
            placed = 0
            pool = list(remaining)
            progressed = True
            while progressed and pool:
                progressed = False
                free = sum(region_majors.get(r, 0) for r in held) + hub_bootstrap - used
                if free > 0:
                    r = pool.pop(0)
                    used += 1; placed += 1
                    held.add(r)               # placing this lock (once found) opens its region
                    progressed = True
            if not pool:
                return placed, idx
        return placed, len(rung_classes_seq) - 1

    ladder = ps.build_ladder(["MajorBoss"])
    majors = {"Limgrave": 1, "Liurnia": 1, "Caelid": 1, "Altus": 1}
    locks = list(majors)
    # (a) precollected anchor into a majored region -> the other 3 locks confine at rung 0
    placed, rung = confine(locks, majors, precollected={"Limgrave"}, rung_classes_seq=ladder)
    assert placed == len(locks) - 1 and rung == 0, "anchored seed confines the remaining locks at rung 0"
    # (b) no anchor, no hub major at rung 0 -> must widen to the +Seedtree rung (hub Golden Seeds)
    placed2, rung2 = confine(locks, majors, precollected=set(), rung_classes_seq=ladder)
    assert placed2 == len(locks), "ladder must eventually place every lock"
    assert rung2 >= 3, "no-anchor seed should need the +Seedtree hub-bootstrap rung"


def test_lock_region_name():
    assert ps.lock_region_name("Limgrave Lock") == "Limgrave"
    assert ps.lock_region_name("Mountaintops of the Giants Lock") == "Mountaintops of the Giants"
    assert ps.lock_region_name("Rune") is None
    assert ps.lock_region_name("Golden Seed") is None


def test_regions_with_major_boss_and_anchor_bias():
    """The strict sphere-0 anchor bias: only regions that HOST a MajorBoss are eligible anchors, so
    core's precollect can open a majored region at sphere 0 and the strict rung-0 confinement holds."""
    locs = {"R1": [("a", 1, 10)], "R2": [("b", 2, 20)], "R3": [("c", 3, 30)], "Hub": [("h", 4, 40)]}
    tags = {1: ["MajorBoss"], 2: ["Shop"], 3: ["MajorBoss", "Remembrance"], 4: []}
    maj = ps.regions_with_major_boss(["R1", "R2", "R3", "Hub"], tags_map=tags, locations=locs)
    assert maj == {"R1", "R3"}, maj
    # lock items map back to their region; a majored one is preferred, a non-majored one is not.
    assert ps.lock_region_name("R1 Lock") in maj and ps.lock_region_name("R2 Lock") not in maj
    # ungenerated tags -> empty set (core then falls back to any kept region, no crash).
    assert ps.regions_with_major_boss(["R1", "R2"], tags_map={}, locations=locs) == set()


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
