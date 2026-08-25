"""progression_surface (v0.2) -- STANDALONE host harness (no Archipelago, no regen required).

The maintainer regenerates location_tags.py on Windows (build.ps1 -Greenfield); this sandbox has
neither elden_ring_artifacts nor (reliably) the AP framework. So this file tests only the PURE logic
-- the feasibility ladder, the restricted-progression predicate, the allowed-surface computation, the
MajorBoss vocabulary, and the MAJOR_BOSS_EXTRAS identifications against the CURRENT greenfield data --
by stubbing `Options` and loading the pure modules directly. The full MajorBoss tag invariant is
enforced at regen time by the assertion in gen_data.py (this file cross-checks its inputs now).

Run directly:  python3 eldenring/tests/test_gf_progression_surface.py
(Also import-safe under pytest: bare asserts, functions prefixed test_.)
"""
import ast
import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
GF = os.path.dirname(HERE)                      # .../eldenring
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
if "eldenring" not in sys.modules:
    _pkg = types.ModuleType("eldenring"); _pkg.__path__ = [GF]; sys.modules["eldenring"] = _pkg
    _fpkg = types.ModuleType("eldenring.features")
    _fpkg.__path__ = [os.path.join(GF, "features")]; sys.modules["eldenring.features"] = _fpkg

contract = _load("eldenring.contract", "contract.py")
_load("eldenring.registry", "registry.py")
location_tags = _load("eldenring.location_tags", "location_tags.py")
data = _load("eldenring.data", "data.py")
boss_data = _load("eldenring.boss_data", "boss_data.py")
ps = _load("eldenring.features.progression_surface", "features/progression_surface.py")


def _gen_data_path():
    """greenfield/gen_data.py, resolved for BOTH layouts."""
    _gd = os.path.join(GREENFIELD, "gen_data.py")
    if not os.path.isfile(_gd):
        # Installed world (_ap/worlds/eldenring): greenfield/ is not installed, but the repo
        # checkout the AP dir sits inside has it -- walk UP (the find_repo_root idiom) instead of
        # skipping. Resolved positionally, this oracle had never run in ANY CI job: every CI
        # checkout contains greenfield/gen_data.py, and the positional GREENFIELD ("two dirs up")
        # points at _ap/worlds there (2026-08-04 inert-test audit, section 2).
        d = HERE
        for _ in range(8):
            cand = os.path.join(d, "greenfield", "gen_data.py")
            if os.path.isfile(cand):
                _gd = cand
                break
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    if not os.path.isfile(_gd):
        import pytest
        pytest.skip("greenfield/gen_data.py not found in any parent -- the gen_data source oracles "
                    "need a repo checkout somewhere above the tests dir (every CI job has one; a "
                    "bare world install outside a repo genuinely cannot run it).")
    return _gd


def _gen_data_literal(name):
    """A module-level literal out of gen_data.py WITHOUT importing it (importing would run the whole
    data pipeline / need elden_ring_artifacts)."""
    tree = ast.parse(open(_gen_data_path(), encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError("%s not found in gen_data.py" % name)


def _major_boss_extras():
    return _gen_data_literal("MAJOR_BOSS_EXTRAS")


def _apid_region():
    return {aid: reg for reg, locs in data.LOCATIONS.items() for (_nm, aid, _fl) in locs}


def _achievement_bosses():
    """greenfield/achievement_bosses.tsv -> [(achievement_id, defeat_flag, boss_name)] for the
    kind=boss rows. THE GAME'S OWN major-boss roster: every call site of common.emevd's trophy event,
    joined to the boss whose defeat flag it fires on (tools/datamine_achievement_bosses.py).

    Resolved beside the installed package first -- gf_test copies greenfield/*.tsv INTO the world --
    then in the repo, so this oracle runs in both layouts instead of skipping in the one CI uses."""
    for cand in (os.path.join(GF, "achievement_bosses.tsv"),
                 os.path.join(GREENFIELD, "achievement_bosses.tsv")):
        if os.path.isfile(cand):
            out = []
            with open(cand, encoding="utf-8-sig") as fh:
                for ln in fh:
                    if not ln.strip() or ln.lstrip().startswith("#") \
                            or ln.startswith("achievement_id\t"):
                        continue
                    pv = ln.rstrip("\n").split("\t")
                    if len(pv) >= 7 and pv[2] == "boss":
                        out.append((int(pv[0]), int(pv[1]), pv[6]))
            assert out, "%s has no kind=boss rows -- an empty roster is a failure, not a pass" % cand
            return out
    import pytest
    pytest.skip("achievement_bosses.tsv not found beside the world or in greenfield/ -- the roster "
                "oracle cannot run (every CI layout has it; a bare install outside a repo may not).")


def _reward_flags_of(defeat_flag):
    """The acquisition flag(s) a boss's DEATH grants. BOSS_REWARD_DEFEAT is {reward: defeat}, so
    this is its inverse -- the same hop gen_data makes, and the reason the roster can be keyed on a
    defeat flag while the tags are keyed on an acquisition flag."""
    rl = _load("eldenring.boss_reward_lots", "boss_reward_lots.py")
    return [rf for rf, df in rl.BOSS_REWARD_DEFEAT.items() if df == defeat_flag]


def _ach_no_check():
    """gen_data._ACH_NO_CHECK -- the ledger of achievement bosses that have NO check in our data.
    EMPTY, and asserted empty by test_every_achievement_boss_is_tagged_or_ledgered; this parenthetical
    said "Margit, and only Margit today" until the ledger's one entry turned out to be wrong."""
    return _gen_data_literal("_ACH_NO_CHECK")


# ---- vocabulary ---------------------------------------------------------------------------------
def test_majorboss_in_vocabulary():
    assert "MajorBoss" in contract.SURFACE_CLASSES
    # the surface vocabulary (contract.SURFACE_CLASSES -- name outlived the deleted option)
    assert "MajorBoss" in ps.ProgressionSurface.valid_keys


def test_has_class_majorboss():
    assert contract.has_class(["MajorBoss"], {"MajorBoss"})
    assert not contract.has_class(["Remembrance"], {"MajorBoss"})   # not selected
    # Enia hard-exclude still wins
    assert not contract.has_class(["MajorBoss", "EniaShop"], {"MajorBoss"})


# ---- ladder -------------------------------------------------------------------------------------
def test_build_ladder_from_majorboss():
    rungs = ps.build_ladder(["MajorBoss"])
    assert rungs[0] == ["MajorBoss"]
    # 🛑 NO ["MajorBoss", "Remembrance", "GreatRune"] RUNG (#733). Both are strict subsets of
    # MajorBoss, so that group admits ZERO locations over this base and `build_ladder` no longer
    # spends a STRICT retry on it -- it folds into the next group that does work. The classes are
    # still carried, because a base WITHOUT MajorBoss (see the Church ladder in
    # test_gf_progression_surface_option) is widened by them for real.
    assert rungs[1] == ["MajorBoss", "Remembrance", "GreatRune", "KeyItem"]
    # KeyItem (small, hand-reviewable) is promoted AHEAD of Legendary (large, scattered); Boss between.
    assert rungs[2] == ["MajorBoss", "Remembrance", "GreatRune", "KeyItem", "Boss"]
    assert rungs[3] == ["MajorBoss", "Remembrance", "GreatRune", "KeyItem", "Boss", "Legendary"]
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


def test_selected_surface_filters_and_canonicalises_order():
    """Order comes from the VOCABULARY, not the caller.

    progression_surface is a yaml OptionSet as of v0.2, and a Python set of strings has no stable
    iteration order across processes (string hashing is randomised per run). If the surface's order
    followed the caller's container, two runs of the SAME seed would build different ladders. So the
    order is canonical -- and this test asserts exactly that, where it used to assert the opposite
    ("order preserved"), which was only safe while the option was a list."""
    vocab = contract.SURFACE_CLASSES
    got = ps.selected_surface(["MajorBoss", "Bogus", "Shop"])
    assert got == [c for c in vocab if c in {"MajorBoss", "Shop"}]
    # identical whatever container / order it arrives in
    assert ps.selected_surface({"Shop", "MajorBoss"}) == got
    assert ps.selected_surface(["Shop", "MajorBoss"]) == got


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
    # Ability Unlocks are EXEMPT too -- made progression so the GENERAL fill exports them to partner
    # worlds (cross-game BK); confining them locally would defeat that. #980 follow-up.
    assert not ps.is_restricted_progression(_FakeItem("Unlock: Roll", P, True), P)
    # non-advancement and foreign items are not ours to confine
    assert not ps.is_restricted_progression(_FakeItem("Rune", P, False), P)
    assert not ps.is_restricted_progression(_FakeItem("Limgrave Lock", P + 1, True), P)


def test_foreign_advancement_barred_predicate():
    """confine_foreign_progression bars OTHER players' advancement from our non-surface checks; our own
    items (any) and any non-advancement item pass. This is the predicate core._add_locations uses as
    `not foreign_advancement_barred(item, self.player)`."""
    P = 3
    # a foreign world's advancement item -> barred from our filler checks
    assert ps.foreign_advancement_barred(_FakeItem("Mothwing_Cloak", P + 1, True), P)
    # our OWN advancement is NOT barred here -- apply()'s spill/ladder valve must stay open
    assert not ps.foreign_advancement_barred(_FakeItem("Limgrave Lock", P, True), P)
    # foreign FILLER/useful is fine on our filler checks (only progression is confined)
    assert not ps.foreign_advancement_barred(_FakeItem("Geo", P + 1, False), P)
    # our own filler, trivially fine
    assert not ps.foreign_advancement_barred(_FakeItem("Rune", P, False), P)


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
    # Cross-check by FLAG, not by the stored ap-id: dense ap-ids drift on regen (an EXCLUDE_FLAGS
    # change shifts every later ap-id), so the hand-typed ap-id is only documentary. The flag is stable
    # and is what region_of resolves, so region membership must be checked flag -> region.
    flag_regions = {}
    for reg, locs in data.LOCATIONS.items():
        for (_nm, _aid, fl) in locs:
            flag_regions.setdefault(fl, set()).add(reg)
    for region, lst in extras.items():
        assert region in data.LOCATIONS, f"extras region {region!r} not a real region"
        for tup in lst:
            # NO ap-id in the tuple. It used to carry a "documentary" one that went stale on every
            # single regen (ap-ids are positional), and gen_data printed a NOTE about it forever.
            # The flag is the durable key; the ap-id is derived. Pinning it was pinning the symptom.
            assert len(tup) == 4, f"expected (flag, boss, drop, confidence), got {tup!r}"
            flag, boss, drop, conf = tup
            assert isinstance(flag, int)
            assert conf in valid_conf, f"bad confidence {conf!r} for {boss!r}"
            # every extra flag must be a REAL check somewhere in the current data
            assert flag in flag_regions, f"{boss!r} flag {flag} is not a real check"
            if conf == "HIGH":
                # HIGH = already filed in the stated region in current data (no regen needed)
                assert region in flag_regions[flag], (
                    f"HIGH extra {boss!r} flag {flag} is in {sorted(flag_regions[flag])!r}, "
                    f"not {region!r}")
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


def test_one_major_boss_check_per_roster_entry():
    """#737, direction 1. A roster entry is ONE boss, so it must be ONE MajorBoss check.

    MAJOR_BOSS_EXTRAS is keyed on the boss's acquisition FLAG -- correctly, because ap-ids drift and
    flags do not. But a flag resolves to a FAMILY: the primary row plus every sibling lot the same
    getItemFlagId drives, each its own co-check. Tagging the family made two DLC field bosses' entire
    ARMOUR SETS into major bosses -- Dancer of Ranah's Hood/Dress/Bracer/Trousers and Blackgaol
    Knight's Helm/Armor/Gauntlets/Greaves -- and `MajorBoss` is in SURFACE_DEFAULT_CLASSES, so four
    pairs of trousers sat on the default progression surface. It also made every count derived from
    the tag read 52 where the entity count is 43.

    Asserted on the COUNT PER FLAG rather than on a list of the eight offenders: a hand-list would
    have to be edited every time a boss gains a drop, which is the failure mode, not the fix. Zero is
    a failure too -- a roster member that resolves to nothing has dropped silently out of the surface,
    which is the direction no count would ever have shown.
    """
    tags = location_tags.LOCATION_TAGS
    flag_majors = {}
    for reg, locs in data.LOCATIONS.items():
        for (_nm, aid, fl) in locs:
            if "MajorBoss" in tags.get(aid, ()):
                flag_majors.setdefault(fl, []).append((aid, _nm))
    # WITNESS (test_gf_vacuous_pass): the scan below asserts a collection is EMPTY, so it has to say
    # first that it saw anything at all. A join that silently stops matching -- a renamed tag, an
    # emptied roster -- would otherwise pass for the same reason a correct one does.
    assert len(flag_majors) >= 30, (
        "only %d flag(s) carry a MajorBoss check -- the tag join has stopped matching, so the "
        "arity assertion below would pass vacuously" % len(flag_majors))

    # Both halves of the roster, each keyed on the flag it is keyed on in gen_data: the ANCHORS by
    # acquisition flag, the ACHIEVEMENT bosses by defeat flag resolved through BOSS_REWARD_DEFEAT.
    entries = [(boss, flag, region) for region, lst in _major_boss_extras().items()
               for (flag, boss, _d, _c) in lst]
    ledger = _ach_no_check()
    for (ach_id, defeat_flag, name) in _achievement_bosses():
        if defeat_flag in ledger:
            continue
        for reward_flag in _reward_flags_of(defeat_flag):
            entries.append((name or ("achievement %d" % ach_id), reward_flag, None))

    # 🛑 "ONE CHECK" MEANS ONE PRIMARY, AND RENNALA IS WHY THE DISTINCTION IS REAL. Flag 197 pays
    # BOTH the Remembrance of the Full Moon Queen and the Great Rune of the Unborn -- one death, two
    # checks, and both are majors by definition (CLOSURE 1: only a demigod drops either). That is not
    # the armour-set shape at all. So the rule is: exactly one PRIMARY check per roster entry, and
    # any further MajorBoss check on the same flag must be a sibling co-check that earns the tag on
    # its own as a Remembrance or Great Rune -- never merely by sharing the flag.
    tags_of = {aid: tuple(t) for aid, t in location_tags.LOCATION_TAGS.items()}
    bad = []
    for (boss, flag, region) in entries:
        hits = sorted(flag_majors.get(flag, []))
        where = ", %s" % region if region else ""
        primary = [(a, n) for (a, n) in hits if a < 7900000]
        if len(primary) != 1:
            bad.append("%s (flag %s%s): %d PRIMARY MajorBoss check(s) %s"
                       % (boss, flag, where, len(primary), [n for (_a, n) in primary]))
        for (a, n) in hits:
            if a >= 7900000 and not {"Remembrance", "GreatRune"} & set(tags_of.get(a, ())):
                bad.append("%s (flag %s%s): sibling co-check %d %r is MajorBoss only because it "
                           "shares the flag -- one boss is one roster member, not one per lot"
                           % (boss, flag, where, a, n))
    assert len(entries) >= 25, ("the roster shrank to %d entries -- check that before reading the "
                                "assertion below, which would pass on an empty one" % len(entries))
    assert not bad, ("a roster entry must resolve to exactly one MajorBoss check -- one boss, one "
                     "check:\n  " + "\n  ".join(bad))


def test_remembrance_and_great_rune_stay_inside_major_boss():
    """The containment the surface is built on, asserted rather than assumed.

    Only demigods and shardbearers drop a Remembrance or a Great Rune, so both sets are subsets of
    MajorBoss by definition -- gen_data closes them in explicitly (CLOSURE 1). Ticking MajorBoss in
    the progression surface therefore already covers both, which is what lets the wizard tell a
    player those two boxes select nothing further. If a change to the roster ever broke it, the
    wizard would be quietly wrong rather than loudly broken, so it is asserted here and not left to
    the derivation that happens to establish it today."""
    tags = location_tags.LOCATION_TAGS
    maj = {a for a, t in tags.items() if "MajorBoss" in t}
    for cls in ("Remembrance", "GreatRune"):
        outside = sorted(a for a, t in tags.items() if cls in t and a not in maj)
        assert not outside, f"{cls} check(s) outside MajorBoss: {outside}"
    assert maj <= {a for a, t in tags.items() if "Boss" in t}, "MajorBoss is not a subset of Boss"


def test_every_region_has_at_least_one_major():
    """The property the whole arrangement exists for: strict "locks only on major bosses" has to be
    FEASIBLE in every region, which needs at least one MajorBoss check in each. The old form of this
    test asserted the weaker, more fragile thing -- that MAJOR_BOSS_EXTRAS covers every region with
    no boss_arena major -- which stopped being true the moment the roster was derived (#737): Altus
    is covered by Elemer of the Briar now, not by a hand entry, and the anchor for it was deleted.
    Assert the invariant, not the mechanism that currently supplies it."""
    tags = location_tags.LOCATION_TAGS
    per_region = {}
    for reg, locs in data.LOCATIONS.items():
        if reg == data.HUB:
            continue
        per_region[reg] = sum(1 for (_nm, aid, _fl) in locs if "MajorBoss" in tags.get(aid, ()))
    assert per_region, "no regions found -- this assertion would pass vacuously"
    empty = sorted(r for r, n in per_region.items() if not n)
    assert not empty, ("region(s) with NO MajorBoss check: %s. Strict progression_surface is "
                       "infeasible there, so the feasibility ladder has to widen the surface for "
                       "the whole seed -- either the roster reaches them or MAJOR_BOSS_EXTRAS needs "
                       "an anchor." % empty)


def test_every_region_anchor_is_load_bearing():
    """The host-side mirror of gen_data's redundancy hard error, and of CONTRIBUTING's rule that a
    redundant manual override is a FAILURE rather than harmless belt-and-braces.

    MAJOR_BOSS_EXTRAS has exactly one job left: a region the DERIVED roster does not reach still
    needs one high-confidence check. So an entry whose region already has a derived major has no
    justification -- and unlike the gen-time check, this one runs without the artifacts, which is the
    layout most people edit that list in. Six entries were deleted under this rule on 2026-08-16;
    three of them were the very checks the achievement roster derives."""
    tags = location_tags.LOCATION_TAGS
    ledger = _ach_no_check()
    derived = {aid for reg, locs in data.LOCATIONS.items() for (_nm, aid, _fl) in locs
               if {"Remembrance", "GreatRune"} & set(tags.get(aid, ()))}
    for (_ach, defeat_flag, _nm) in _achievement_bosses():
        if defeat_flag in ledger:
            continue
        for rf in _reward_flags_of(defeat_flag):
            derived |= {aid for reg, locs in data.LOCATIONS.items() for (_n2, aid, fl) in locs
                        if fl == rf and aid < 7900000}
    assert len(derived) >= 40, ("the derived roster resolved to only %d check(s) -- too few for the "
                                "redundancy question below to mean anything" % len(derived))
    apid_region = _apid_region()
    derived_regions = {apid_region[a] for a in derived if a in apid_region}
    redundant = []
    for region, lst in _major_boss_extras().items():
        for (flag, boss, _d, _c) in lst:
            if region in derived_regions:
                redundant.append("%s (%s, flag %s): %s already has a derived major"
                                 % (boss, region, flag, region))
    assert not redundant, ("MAJOR_BOSS_EXTRAS entr(y/ies) with nothing left to anchor -- delete "
                           "them, do not keep a hand override the derivation already covers:\n  "
                           + "\n  ".join(redundant))


def test_every_achievement_boss_is_tagged_or_ledgered():
    """The roster's own completeness gate, on the side of it a count cannot see.

    MajorBoss growing is easy to notice. A boss quietly LEAVING the roster -- a defeat flag re-keyed,
    a reward-lot capture re-mined, a rename upstream -- shrinks the default progression surface and
    reports a clean run, because nothing downstream knows how many achievement bosses there are
    supposed to be. So every kind=boss row in the game's own trophy table must end up tagged, or be
    named in gen_data's _ACH_NO_CHECK ledger with a reason.

    🛑 THE LEDGER IS EMPTY AND THAT IS ASSERTED, because it briefly was not and the entry was WRONG.
    It held Margit, on the reasoning that no boss-drop row for him exists in our data. His drop is
    the Stormveil Talisman Pouch; what was missing was a join, not a check (m10_00's `Defeat Margit`
    event flips reward flag 9100, and datamine_boss_reward_lots was discarding that row because
    Morgott's event back-fills the same flag behind a guard). A waiver is the one place a wrong
    belief can sit and look like diligence -- it turns "our derivation is missing something" into a
    documented fact about the game, and nothing downstream asks again. So the bound is zero, and
    adding an entry has to be a reviewed diff that cites the EMEVD awarding nothing."""
    tags = location_tags.LOCATION_TAGS
    ledger = _ach_no_check()
    roster = _achievement_bosses()
    assert len(roster) >= 25, ("the achievement roster has only %d boss row(s) -- re-emit "
                               "achievement_bosses.tsv before trusting anything below" % len(roster))
    assert not ledger, (
        "the no-check ledger is no longer empty: %r. Each entry is an achievement boss the "
        "progression surface cannot use -- a data gap to FIX, not a waiver to add, and the last one "
        "of these turned out to be a missing join rather than a missing check. Before adding one, "
        "find the EMEVD event that awards nothing." % sorted(ledger))
    missing = []
    for (ach, defeat_flag, name) in roster:
        if defeat_flag in ledger:
            continue
        tagged = [aid for rf in _reward_flags_of(defeat_flag)
                  for reg, locs in data.LOCATIONS.items() for (_nm, aid, fl) in locs
                  if fl == rf and "MajorBoss" in tags.get(aid, ())]
        if not tagged:
            missing.append("%s (achievement %d, defeat flag %d)" % (name or "?", ach, defeat_flag))
    assert not missing, ("achievement boss(es) carrying no MajorBoss check and not in the "
                         "_ACH_NO_CHECK ledger:\n  " + "\n  ".join(missing))


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
