"""dungeon_sweep's rungs must actually differ -- for a month they did not.

THE BUG. The slot_data emit gated on `dungeon_sweep.value != 0` and never filtered by boss class, so
`minidungeons`, `all` and `bosses` each granted the FULL sweep set. Three distinct player-facing
values, one behaviour. The option's own docstring described the ladder, the player guide repeated it,
and the v0.2.15 release notes told a player by name that `minidungeons` and `bosses` were "the two
middles". All of it was false, and nothing compared the values to each other.

🛑 A CHOICE WHOSE VALUES ARE INTERCHANGEABLE IS A TOGGLE WEARING A LADDER'S CLOTHES. Testing each
value in isolation -- "does it generate?", "does it emit a well-formed wire?" -- passes forever. The
only assertion that catches this compares the values AGAINST EACH OTHER, which is why the test below
is written as a strict ordering rather than four independent cases.

The default moved all -> bosses in the same change: the full set is what every non-none value
already granted, so `bosses` IS the shipped behaviour. Defaulting to `all` would have silently
dropped field sweeps (~38% of them) from every seed under cover of a bug fix.
"""
import pytest

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

GAME = "Elden Ring"
SEED = 4242


def _members(mode):
    """Total swept checks at a rung, at a PINNED seed (kept regions vary per seed)."""
    class _T(WorldTestBase):
        game = GAME
        options = {"num_regions": 0, } if mode is None else {"dungeon_sweep": mode}
    t = _T("runTest")
    t.options = {} if mode is None else {"dungeon_sweep": mode}
    t.world_setup(SEED)
    flags = t.world.fill_slot_data().get("dungeonSweepFlags") or {}
    return sum(len(v) for v in flags.values())


def test_the_rungs_are_strictly_increasing():
    """THE assertion the old suite lacked: the values compared to each other, not in isolation."""
    none, mini, alll, bosses = (_members(m) for m in ("none", "minidungeons", "all", "bosses"))
    assert none == 0, "none must sweep nothing, got %d" % none
    assert none < mini < alll < bosses, (
        "dungeon_sweep rungs are not strictly increasing: none=%d minidungeons=%d all=%d bosses=%d. "
        "If two are equal the option is a toggle pretending to be a ladder -- which is exactly the "
        "state this file exists to prevent." % (none, mini, alll, bosses))


def test_the_default_is_what_actually_shipped():
    """Making the rungs real must not quietly change what a default seed rolls.

    Every non-none value granted the full set before, so the shipped behaviour is `bosses`. Pinning
    this stops a future tidy-up from 'restoring' the documented default and dropping ~38% of sweeps
    from every seed."""
    from worlds.eldenring.features.boss_locks import DungeonSweep
    assert DungeonSweep.default == DungeonSweep.option_bosses, (
        "dungeon_sweep default is no longer `bosses`. The full sweep set is what shipped; changing "
        "this is a balance change and needs saying out loud, not a silent default move.")
    assert _members(None) == _members("bosses")


def test_field_bosses_are_what_all_and_bosses_differ_by():
    """The split that was asked for: `all` is dungeons WITHOUT field bosses."""
    from worlds.eldenring.features.boss_locks import _SWEEP_RUNGS
    assert "field" in _SWEEP_RUNGS["bosses"], "the top rung must include field bosses"
    assert "field" not in _SWEEP_RUNGS["all"], (
        "`all` must EXCLUDE field bosses -- that separation is the whole point of having both")
    assert _SWEEP_RUNGS["minidungeons"] < _SWEEP_RUNGS["all"] < _SWEEP_RUNGS["bosses"], (
        "the rungs must be nested class sets, or a 'higher' setting could lose a sweep a lower one grants")


# The PERMANENT sweep floor -- gen_data._SWEEP_NEVER_TAGS. `Legendary`, `Seedtree`, `Church`,
# `Fragment`, `Revered` and `Basin` are DELIBERATELY absent since 2026-08-13: they are admitted into
# the baked member lists and cut per seed by features/boss_locks.sweep_surface_cut against that
# seed's Progression Surface. Asserting the old whole-vocabulary set here would red on 145 checks
# that are now supposed to be there.
_SWEEP_NEVER = {"Remembrance", "Boss", "GreatRune", "KeyItem", "Shop", "ShopNonSpell", "ShopSlot",
                "MajorBoss", "LegacyBoss", "FieldBoss"}

# Swept checks that DO carry a FLOOR tag, as of 2026-08-13. A RATCHET, not an allowlist: these
# three are known debt, and anything new must fail.
#
# 🛑 WHY THEY EXIST. The LEGACY sweep pool is floor-filtered by construction (gen_data's
# `_filler_only` cut). The MINIDUNGEON path is not: `_members = _mem_map.get(_bmap, [])` takes the
# map's checks unfiltered. So "a sweep respects the floor" is true of the legacy pool -- which is
# what bounded the Grafted Scion bug to 36 harmless checks -- and NOT true in general.
#
# ⭐ IT SHRANK FROM SIX. The three Legendary rows (7772215 Uchigatana, 7772478 Godslayer's
# Greatsword, 7772562 Bull-Goat Helm) were debt only while Legendary was cut corpus-wide; it is a
# surface-cuttable class now, so a legendary SURFACE holding ordinary loot is the intended payout
# and those rows are no longer a defect to ratchet. Deleted rather than re-justified, which is the
# tightening this test's own `gone` branch asks for. The three below are floor classes and stay.
_KNOWN_IMPORTANT_IN_SWEEPS = {
    # ⚠️ ap ids are POSITIONAL and this ledger is keyed on them: #330's 124-row Rada removal
    # (2026-08-19) shifted all three by -35 while the CHECKS (flags 41027000 / 41027320 / 43017900,
    # verified identical) never moved. If this ledger drifts again for a corpus change, match by
    # flag before concluding the debt grew.
    # 2026-08-19 (the cull renumbered ap ids, twice -- the second time when the Crimson Hood
    # ruling put one location back ahead of these): 7772549 -> 7772545 -> 7772546,
    # 7772553 -> 7772549 -> 7772550, 7772568 -> 7772564 -> 7772565. Same three flags;
    # re-verified by flag identity each time.
    7772546,   # KeyItem   -- Gaol Upper Level Key            (f41027000)
    7772550,   # KeyItem   -- Gaol Lower Level Key            (f41027320)
    7772565,   # Boss      -- Dragon Heart, around Dragon's Pit (f43017900)
}


def test_the_important_checks_inside_sweeps_do_not_grow():
    """Ratchet. Sweeps are filler-only in the LEGACY pool but not in the minidungeon path.

    Recorded rather than asserted-away because the six are real and pre-existing: two are DLC gaol
    keys, which a sweep can hand you for killing the boss they gate the route to. Fixing it means
    applying gen_data's `_filler_only` cut to the map path too -- a deliberate change with its own
    balance argument, not something to slip in under a test.

    Until then this stops the set GROWING, which is the part that would go unnoticed."""
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
    from worlds.eldenring.location_tags import LOCATION_TAGS
    from worlds.eldenring.boss_reward_lots import BOSS_REWARD_DEFEAT
    from worlds.eldenring.data import LOCATIONS
    important = set(_SWEEP_NEVER)
    # ⭐⭐⭐ THE BOSS'S OWN DROP IS NOT DEBT -- and it is DERIVED, not listed.
    # 2026-08-08: attributing the second reward mechanism to `Boss` put three checks in this set --
    # Omenkiller Rollo's drop, the Flamedrake Talisman at Groveside Cave, the Sewing Needle at
    # Coastal Cave. Each is swept by the trigger of THE VERY BOSS THAT DROPS IT. That is not a sweep
    # handing out someone else's key item; it is the sweep doing its job, and FILTERING it would mean
    # killing the boss no longer grants the boss's own reward -- strictly worse than the debt this
    # ratchet guards. So the exemption is a relation, computed from the same table that made them
    # `Boss` in the first place: `BOSS_REWARD_DEFEAT[flag_of(ap)] == the trigger sweeping it`.
    # It cannot be satisfied by adding an id, and a fourth such check needs no edit here.
    # 🛑 It does NOT weaken the ratchet. All six pre-existing rows FAIL this relation (verified), so
    # the hand list below is untouched and still carries exactly the real debt.
    _flag_of = {ap: int(fl) for locs in LOCATIONS.values() for (_n, ap, fl) in locs}
    # 2026-08-20 (#907): the relation gained a second table. BOSS_DROP_ENTITY is the field/evergaol
    # own-drop map (boss_drops.py), admitted into sweeps by gen_data's own-drop pass because the
    # vanilla award waits on CharacterDead and a host enemy randomizer breaks it. Same property as
    # BOSS_REWARD_DEFEAT: satisfied only by the flag's OWN trigger, never by adding an id here.
    from worlds.eldenring.boss_drops import BOSS_DROP_ENTITY
    own_reward = {ap for trig, members in DUNGEON_SWEEPS.items() for ap in members
                  if BOSS_REWARD_DEFEAT.get(_flag_of.get(ap)) == trig
                  or BOSS_DROP_ENTITY.get(_flag_of.get(ap)) == trig}
    found = {ap for members in DUNGEON_SWEEPS.values() for ap in members
             if important & set(LOCATION_TAGS.get(ap, ()))}
    new = sorted(found - _KNOWN_IMPORTANT_IN_SWEEPS - own_reward)
    assert not new, (
        "%d NEW important-tagged check(s) entered a sweep pool: %s. A sweep that hands out a key "
        "item makes the rung a progression decision. Either filter them out or justify each one "
        "here." % (len(new), new))
    gone = sorted(_KNOWN_IMPORTANT_IN_SWEEPS - found)   # own_reward NOT subtracted: a hand row that becomes an own-drop is still stale
    # AUDIT 2026-08-04: this branch used to `warnings.warn` and pass -- ledger decay was silent,
    # the same species as the stale-_EDGE_EXEMPT hole in test_gf_client_resets_are_called (finding
    # P3). A ratchet whose rows outlive the debt stops being read, and staleness is a fact about
    # THIS tree, checkable right here -- so it fails here. The fix is one deleted line, named below.
    assert not gone, (
        "%d known important-in-sweep check(s) are no longer in any sweep pool: %s. Shrink "
        "_KNOWN_IMPORTANT_IN_SWEEPS to match. If this was the _filler_only fix finally landing, "
        "deleting the row(s) is how the ratchet TIGHTENS and this failure is the reminder; if it "
        "was not, a sweep pool changed shape underneath the ledger and needs looking at -- either "
        "way a stale row must not sit here reading as live debt." % (len(gone), gone))


# ---------------------------------------------------------------------------------------------
# THE PER-SEED SURFACE CUT (2026-08-13). gen_data admits the six cuttable classes into the baked
# member lists; features/boss_locks takes back the ones THIS seed's Progression Surface claimed.
# The bake and the cut are two stages that are each individually correct and whose COMPOSITION is
# the thing players see -- CONTRIBUTING rule 11 -- so these assert the finished pipeline, by class.

_CUTTABLE = {"Seedtree", "Church", "Fragment", "Revered", "Basin", "Legendary"}


class _FakeOptionSet:
    def __init__(self, value):
        self.value = set(value)


class _FakeWorld:
    """Minimal duck for enabled_sweeps/sweep_surface_cut: a Progression Surface and nothing else.

    No dungeon_sweep option on purpose -- enabled_sweeps falls back to the 'bosses' rung, which is
    the shipped default, so these read the seed a player actually gets."""
    def __init__(self, surface):
        self.options = type("_O", (), {"progression_surface": _FakeOptionSet(surface)})()


def _classes_in(members, location_tags):
    out = set()
    for ap in members:
        out |= _CUTTABLE & set(location_tags.get(ap, ()))
    return out


def test_the_default_surface_sweeps_legendaries_and_still_protects_the_collectathon():
    """THE MOTIVATING CASE. Alaric, 2026-08-13: "filler and useful, so non-progression only."

    At the DEFAULT Progression Surface, Church/Seedtree/Fragment/Revered are where this seed puts
    its Locks, so they must stay out of every sweep; Legendary and Basin are not on the default
    surface at all, so they are ordinary area loot and the boss pays them out. Asserted on the
    OUTPUT of enabled_sweeps rather than on the bake, because the bake contains all six and a cut
    that silently stopped running would leave every one of these classes in the payload."""
    from worlds.eldenring.features.boss_locks import enabled_sweeps
    from worlds.eldenring.location_tags import LOCATION_TAGS
    from worlds.eldenring import contract
    live = enabled_sweeps(_FakeWorld(contract.SURFACE_DEFAULT_CLASSES))
    members = {ap for mem in live.values() for ap in mem}
    got = _classes_in(members, LOCATION_TAGS)
    assert got == {"Legendary", "Basin"}, (
        "the default seed's sweep payload carries %s; it must carry exactly the two classes the "
        "default surface does NOT claim (Legendary, Basin). Anything more means the per-seed cut "
        "did not run; anything less means the bake stopped admitting them." % sorted(got))


def test_an_empty_surface_cuts_nothing_and_the_full_bake_shows_up():
    """An empty surface turns confinement off entirely, so there is no class to protect -- and the
    payload is then the whole bake. This is also the control for the test above: it proves the six
    classes really are in the baked member lists, so a green default-surface run is a statement
    about the CUT and not about an empty bake."""
    from worlds.eldenring.features.boss_locks import enabled_sweeps
    from worlds.eldenring.location_tags import LOCATION_TAGS
    live = enabled_sweeps(_FakeWorld(set()))
    members = {ap for mem in live.values() for ap in mem}
    got = _classes_in(members, LOCATION_TAGS)
    assert got == _CUTTABLE, (
        "an empty Progression Surface should leave all six cuttable classes in the sweep payload, "
        "got %s" % sorted(got))


def test_ticking_a_class_onto_the_surface_takes_it_back_out_of_the_sweep():
    """The knob, one class at a time. Each cuttable class, selected ALONE, must vanish from the
    payload and leave the other five untouched -- so the cut is per class and not a mood."""
    from worlds.eldenring.features.boss_locks import enabled_sweeps
    from worlds.eldenring.location_tags import LOCATION_TAGS
    baseline = _classes_in({ap for mem in enabled_sweeps(_FakeWorld(set())).values() for ap in mem},
                           LOCATION_TAGS)
    for cls in sorted(_CUTTABLE):
        members = {ap for mem in enabled_sweeps(_FakeWorld({cls})).values() for ap in mem}
        got = _classes_in(members, LOCATION_TAGS)
        assert got == baseline - {cls}, (
            "selecting %r on the Progression Surface should remove exactly that class from the "
            "sweep payload; got %s, wanted %s" % (cls, sorted(got), sorted(baseline - {cls})))


def test_the_floor_holds_whatever_the_surface_says():
    """No surface selection may put a floor class back into a sweep. The floor is not an option."""
    from worlds.eldenring.features.boss_locks import enabled_sweeps
    from worlds.eldenring.location_tags import LOCATION_TAGS
    from worlds.eldenring.boss_reward_lots import BOSS_REWARD_DEFEAT
    from worlds.eldenring.data import LOCATIONS
    _flag_of = {ap: int(fl) for locs in LOCATIONS.values() for (_n, ap, fl) in locs}
    from worlds.eldenring.boss_drops import BOSS_DROP_ENTITY
    for surface in (set(), _CUTTABLE, {"Legendary"}):
        live = enabled_sweeps(_FakeWorld(surface))
        own_reward = {ap for trig, mem in live.items() for ap in mem
                      if BOSS_REWARD_DEFEAT.get(_flag_of.get(ap)) == trig
                      or BOSS_DROP_ENTITY.get(_flag_of.get(ap)) == trig}
        # WITNESSES, both of them load-bearing: `assert not leaked` passes for free if the payload
        # is empty or if the floor vocabulary stopped matching any tag at all, and either would be
        # a silent hole rather than a green run (test_gf_vacuous_pass's ratchet, shape 2).
        members = {ap for mem in live.values() for ap in mem}
        assert len(members) > 3000, (
            "surface=%s produced only %d sweep member(s) -- this gate is asserting over almost "
            "nothing" % (sorted(surface), len(members)))
        floor_tagged = sum(1 for t in LOCATION_TAGS.values() if _SWEEP_NEVER & set(t))
        assert floor_tagged > 400, (
            "only %d location(s) carry ANY floor tag -- the tag join is broken, so `leaked` is "
            "empty for the wrong reason" % floor_tagged)
        leaked = {ap for mem in live.values() for ap in mem
                  if _SWEEP_NEVER & set(LOCATION_TAGS.get(ap, ()))}
        leaked -= own_reward | _KNOWN_IMPORTANT_IN_SWEEPS
        assert not leaked, ("surface=%s let %d floor-tagged check(s) into a sweep: %s"
                            % (sorted(surface), len(leaked), sorted(leaked)[:5]))


def test_the_legacy_pool_specifically_is_clean():
    """The claim that actually bounded the Grafted Scion bug, asserted where it is true."""
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
    from worlds.eldenring.boss_healthbars import BOSS_HEALTHBARS
    from worlds.eldenring.location_tags import LOCATION_TAGS
    important = set(_SWEEP_NEVER)
    from worlds.eldenring.data import LOCATIONS
    from worlds.eldenring.boss_drops import BOSS_DROP_ENTITY
    _flag_of = {ap: int(fl) for locs in LOCATIONS.values() for (_n, ap, fl) in locs}
    leaked = [ap for fl, members in DUNGEON_SWEEPS.items()
              if (BOSS_HEALTHBARS.get(fl) or (None, None, None))[2] == "legacy"
              for ap in members if important & set(LOCATION_TAGS.get(ap, ()))
              # 2026-08-20 (#907): a legacy-geography boss's OWN drop is not a leak -- the same
              # own-trigger relation the field tests carry.
              and BOSS_DROP_ENTITY.get(_flag_of.get(ap)) != fl]
    assert not leaked, (
        "the LEGACY sweep pool is supposed to be filler-only by construction (_filler_only), and %d "
        "important check(s) got in: %s" % (len(leaked), leaked[:5]))


# ---------------------------------------------------------------------------------------------
# THE GENERAL PROPERTY: a sweep must not hand you a check whose gate its TRIGGER does not satisfy.
#
# A sweep grants its members the moment its boss dies. If a member sits behind a key the boss does
# NOT sit behind, the sweep is a way past that key -- you get the gated check without ever holding
# what gates it. That is the softlock shape from the 2026-07-16 playtest, arriving through a
# different door.
#
# The six important-tagged checks currently in sweeps are NOT this bug, and it is worth writing down
# why so the next reader does not re-raise it:
#   * 3 legendaries -- no gate, no logic meaning.
#   * Gaol Upper/Lower Level Key -- gated, but so is the sweep's trigger: legacy_key_gates requires
#     BOTH keys for every gaol check AND for the Lamenter's own reward (its `extra`, f520770). You
#     cannot fire that sweep without already satisfying the gate. Consistent, not a hole.
#   * Dragon Heart -- the thing needing protection is not the Heart but the 25 places you SPEND it,
#     and those are exactly what the missable alt_currency guard bars from carrying advancement.
# ---------------------------------------------------------------------------------------------
def _key_requirements():
    """ap_id -> frozenset of key names that gate it, with every key active (the worst case)."""
    from worlds.eldenring.features import legacy_key_gates as lkg
    req = {}
    for ap, key in lkg._gated_location_ids(list(lkg._LEGACY_KEYS)).items():
        req.setdefault(ap, set()).add(key)
    for ap, keys in lkg._multi_gated_location_ids(lkg._MULTI_KEY_GATES).items():
        req.setdefault(ap, set()).update(keys)
    return {ap: frozenset(v) for ap, v in req.items()}


def _trigger_keys(defeat_flag):
    """Keys that gate the BOSS whose defeat flag this is.

    Apply the gate's OWN predicate to the trigger. A key gate is a flag WINDOW -- the Academy key
    covers [14000000, 15000000), the gaol gate covers [41020000, 41030000) -- and boss defeat flags
    live in the same space as the checks they sit among. So the question "is this boss behind the
    key?" is the same range test the gate already runs on every check.

    An earlier version of this test demanded a defeat-flag -> reward-location join instead, which
    resolved only 103 of 241 triggers and reported the Academy and gaol sweeps as violations. They
    were not: 14000800/801/850 fall inside the Academy window and 41020800 inside the gaol's. The
    join was too narrow, not the logic wrong -- and the range test resolves ALL of them.
    """
    from worlds.eldenring.features import legacy_key_gates as lkg
    keys = set()
    for key, (_parent, (lo, hi)) in lkg._LEGACY_KEYS.items():
        if (lo <= defeat_flag < hi) or defeat_flag in lkg._LEGACY_EXTRA.get(key, frozenset()):
            keys.add(key)
    for g in lkg._MULTI_KEY_GATES:
        if any(lo <= defeat_flag < hi for (lo, hi) in g["ranges"]) or defeat_flag in g["extra"]:
            keys.update(g["keys"])
    return frozenset(keys)


def test_no_sweep_grants_a_check_its_trigger_is_not_gated_behind():
    """THE GENERAL PROPERTY: a swept check's gate must be implied by its sweep trigger's gate.

    A sweep grants its members the moment its boss dies. If a member sits behind a key the boss does
    NOT sit behind, the sweep is a way past that key -- you receive the gated check without ever
    holding what gates it. That is the 2026-07-16 gaol softlock arriving through a different door,
    and nothing asserted it until now.

    It currently holds because the two gated dungeons gate their boss too: the Academy window covers
    Red Wolf and Rennala, the gaol window covers the Lamenter. This test is what stops a future
    sweep -- a widened pool, a new gate, a re-region -- from quietly breaking that.

    🛑 WHAT IT CANNOT CATCH, established by mutating it rather than assumed. Member requirements and
    trigger requirements are BOTH derived from the same flag window, so narrowing a gate's window
    shrinks both together and this test stays green -- it cannot tell you a window is mis-scoped.
    What it DOES catch is contamination: a sweep containing a check gated by a key its own trigger is
    not behind. Verified by injecting an Academy-gated ap into a Stormveil sweep, which reds it with
    "trigger has []". Mis-scoped windows need a different instrument; do not read a green here as
    "the gates are right", only as "the sweeps do not cross them".
    """
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS

    req = _key_requirements()
    bad, gated_sweeps = [], 0
    for defeat, members in DUNGEON_SWEEPS.items():
        needed = frozenset().union(*(req.get(ap, frozenset()) for ap in members)) if members else frozenset()
        if not needed:
            continue
        gated_sweeps += 1
        have = _trigger_keys(defeat)
        if not needed <= have:
            bad.append("%s: members need %s, trigger has %s"
                       % (defeat, sorted(needed), sorted(have)))

    assert not bad, (
        "%d sweep(s) hand out a check their trigger is not gated behind -- the sweep is a way past "
        "that key:\n  %s" % (len(bad), "\n  ".join(bad[:8])))
    # An assertion that never examined a gated sweep proves nothing: a filter with no tally is a lie.
    assert gated_sweeps > 0, (
        "no sweep contained a key-gated member, so this property was never actually exercised. "
        "If the gates moved, re-derive them rather than deleting this.")


def test_carian_inverted_checks_stay_out_of_the_standard_layout_sweep():
    """The ordinary Study Hall fight must not pay out checks from the inverted layout."""
    from worlds.eldenring.boss_sweeps import DUNGEON_SWEEPS
    from worlds.eldenring.data import LOCATIONS
    from worlds.eldenring.features import legacy_key_gates as lkg

    statue_flags = set(lkg._LEGACY_EXTRA["Carian Inverted Statue"])
    flag_of = {ap: int(flag) for locs in LOCATIONS.values() for (_name, ap, flag) in locs}
    swept_flags = {flag_of[ap] for ap in DUNGEON_SWEEPS[34110800]}
    assert statue_flags.isdisjoint(swept_flags), (
        "Study Hall's standard-layout sweep bypasses the Carian Inverted Statue gate: %s"
        % sorted(statue_flags & swept_flags))
