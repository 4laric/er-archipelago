"""Sweep/kill correlator gate (#713) -- tools/check_sweep_kill_correlation.py.

The tool answers one question nothing else asks: when a boss sweep FIRED, did anything die for it?
This file is the acceptance from the issue, turned into a gate. All three cases are the ones the
issue names, because a detector that cannot reproduce the known case is not measuring it:

  A. islam's Liurnia session -- three sweeps in eight minutes, the middle one fired on nothing.
     `1034500800` must flag, and it must be the ONLY thing that flags.
     ⭐ The load-bearing part is that Adula has TWO triggers resolving to the SAME chr family, so a
     correlator that let one kill clean two sweeps would call this session green. That is the exact
     shape of the defect being hunted, sitting inside the fixture for it.
  B. A suppressed secondary head (#363, m31_22 Spiritcaller's Cave) -- one snail dies, three sweeps
     fire. None may flag. Without `boss_arena_pairs.tsv` as an INPUT, every phase-pair boss reads as
     "sweep with no kill" and buries the real signal.
     🛑 The fixture lists the SECONDARY first on purpose: primaries must consume before secondaries
     share, or dict order alone manufactures a false positive on the primary.
  C. bobler's Scadutree Avatar session -- a LEGITIMATE 2m45s gap between the kill and the sweep,
     one warp apart. It must not flag. This is the case `sweep_watch.rs` exists to explain, and it
     is the one a tight window would cry wolf on -- so the test also asserts that a 60s window DOES
     flag it, which is what keeps the default honest rather than accidental.

🛑 THE TOOL IS AP-FREE; THIS FILE IS NOT. `tools/check_sweep_kill_correlation.py` imports nothing
from the world package and runs in a bare checkout -- but this test lives inside `eldenring`, whose
`__init__` chain pulls `BaseClasses` the moment pytest imports the module. It is a `tests`-job suite
(see tools/gf_suite_ledger.py), not a `generators` one, and there is no `__main__` block pretending
otherwise.

Run:  python -m pytest greenfield/eldenring/tests/test_gf_sweep_kill_correlation.py
"""
import importlib.util
import os
import sys

import pytest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")


def _load_tool():
    root = find_repo_root(HERE)
    if root is None:
        pytest.skip(REPO_ONLY_REASON)
    path = os.path.join(root, "tools", "check_sweep_kill_correlation.py")
    if not os.path.exists(path):
        pytest.skip("tools/check_sweep_kill_correlation.py is absent")
    spec = importlib.util.spec_from_file_location("_sweep_kill_correlation", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


@pytest.fixture(scope="module")
def tables(tool):
    try:
        npcs = tool.load_trigger_npcs()
    except SystemExit as exc:
        pytest.skip(str(exc))
    return npcs, tool.load_arena_pairs(), tool.load_skips()


def run(tool, tables, name, window=None, lead=None, path=None):
    """-> {verdict: [flag, ...]} over every session in the fixture (or in `path`)."""
    npcs, pairs, skips = tables
    window = tool.DEFAULT_WINDOW if window is None else window
    lead = tool.DEFAULT_LEAD if lead is None else lead
    out = {}
    for session in tool.parse_log(path or os.path.join(FIXTURES, name)):
        findings, _unclaimed = tool.correlate(session, npcs, pairs, skips, window, lead)
        for f in findings:
            out.setdefault(f.verdict, []).append(f.flag)
    return out


def write_log(tmp_path, name, lines):
    """A one-session log with the client's real prefix, for the cases no fixture covers."""
    head = [
        "12:05:00 [INFO] === SESSION START 2026-08-16 12:05:00 | pid 7 | this file is APPENDED "
        "across launches: everything above belongs to an earlier run ===",
        "12:05:11 [INFO] boss-fight probe: ON (default). Samples player and boss HP ~2 Hz while a "
        "boss healthbar is up.",
    ]
    p = tmp_path / name
    p.write_text("\n".join(head + list(lines)) + "\n", encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------------------------
# A. The known case. If this ever goes green, the instrument stopped measuring.
# ---------------------------------------------------------------------------------------------
def test_islam_liurnia_flags_1034500800_and_only_that_one(tool, tables):
    got = run(tool, tables, "sweep_kill_islam_liurnia.log")
    assert got.get("FIRED WITHOUT A KILL") == [1034500800], (
        "the 12:23:45 sweep fired with no boss fight anywhere in the session (#697) and is the "
        "only thing in this log that should flag -- got %r" % (got,))
    assert sorted(got.get("clean", [])) == [1034420800, 1035500800], (
        "the sweeps at 12:19:42 and 12:27:56 each landed on their own BOSS DOWN and must come back "
        "clean -- got %r" % (got,))


def test_one_kill_cannot_clean_two_sweeps(tool, tables):
    """⭐ The consumption rule, stated as its own test because it is what makes case A readable.

    Both Adula triggers resolve to chr 4502, so the 12:19:42 kill is inside the 300s window of the
    12:23:45 sweep as well. Two sweeps paying out off one kill IS the defect; if the tool ever
    stops consuming, this test is the one that says so rather than a silently green log.
    """
    npcs, _pairs, _skips = tables
    assert npcs[1034420800]["npcs"] == npcs[1034500800]["npcs"], (
        "this test is only meaningful while both Adula triggers share a candidate set; if the join "
        "got sharper, re-point it at another shared-chr pair rather than deleting it")
    got = run(tool, tables, "sweep_kill_islam_liurnia.log")
    assert got.get("FIRED WITHOUT A KILL") == [1034500800]


def test_a_trigger_with_no_vanilla_identity_falls_back_to_timing(tool, tables):
    """The third Liurnia sweep is clean, but on WEAKER evidence, and the line has to say so.

    Royal Knight Loretta's healthbar nameId decodes to chr 3253, which has no NpcParam rows at all
    (the model is 3252; 3253 is a name variant), so the trigger has no candidate set -- one of the
    9 in the UNRESOLVED roll-call. Rather than refusing to judge it, the tool drops identity and
    keeps timing: a boss died in the window, so the sweep is answered for. That is enough for the
    defect being hunted (#697's sweep had no fight near it at all) and it is exactly what the issue
    expects of this sweep -- but "a boss died here" is not "THIS boss died here", and the detail
    must not let a reader mistake one for the other.
    """
    npcs, pairs, skips = tables
    sessions = tool.parse_log(os.path.join(FIXTURES, "sweep_kill_islam_liurnia.log"))
    findings, _ = tool.correlate(sessions[0], npcs, pairs, skips, tool.DEFAULT_WINDOW,
                                 tool.DEFAULT_LEAD)
    loretta = [f for f in findings if f.flag == 1035500800]
    assert len(loretta) == 1 and loretta[0].verdict == "clean"
    assert "IDENTITY-BLIND" in loretta[0].detail
    # ...and the sweeps we CAN name must not be downgraded with it.
    adula = [f for f in findings if f.flag == 1034420800]
    assert adula[0].verdict == "clean" and "IDENTITY-BLIND" not in adula[0].detail


# ---------------------------------------------------------------------------------------------
# B. Mode 4 working as designed must stay silent.
# ---------------------------------------------------------------------------------------------
def test_a_suppressed_head_kill_does_not_flag(tool, tables):
    got = run(tool, tables, "sweep_kill_suppressed_head.log")
    assert not got.get("FIRED WITHOUT A KILL"), (
        "one snail died and three sweeps fired; #363 says that is the design, so all three are "
        "clean -- got %r" % (got,))
    assert sorted(got.get("clean", [])) == [31220800, 31220801, 31220802]


def test_the_primary_consumes_before_the_secondaries_share(tool, tables):
    """The fixture lists secondary 31220801 BEFORE primary 31220800, which is the order that used
    to break: the secondary took the only kill and the primary -- not allowed to share -- flagged.
    """
    npcs, pairs, _skips = tables
    assert pairs.get(31220801) == 31220800 and 31220800 not in pairs
    assert not npcs[31220800]["npcs"] & npcs[31220801]["npcs"], (
        "the snail and the Godskin are different chr families; if they ever overlap this test "
        "stops exercising the sharing path")
    got = run(tool, tables, "sweep_kill_suppressed_head.log")
    assert 31220800 in got.get("clean", [])


# ---------------------------------------------------------------------------------------------
# C. The trap. A legitimate gap must survive, and the window must be the thing that saves it.
# ---------------------------------------------------------------------------------------------
def test_boblers_2m45s_warp_gap_does_not_flag(tool, tables):
    got = run(tool, tables, "sweep_kill_bobler_scadutree.log")
    assert not got.get("FIRED WITHOUT A KILL"), (
        "13:01:02 kill, 13:03:47 sweep, one warp apart -- the case sweep_watch.rs was written to "
        "explain. Flagging it would cry wolf on the motivating example -- got %r" % (got,))
    assert got.get("clean") == [2050480810]


def test_a_tight_window_would_have_cried_wolf(tool, tables):
    """The default is 300s BECAUSE 165s is real. This asserts the number is doing work: at 60s the
    same log flags, so a future 'tidy-up' that narrows the window fails here with the reason
    attached rather than quietly re-introducing the false positive.
    """
    got = run(tool, tables, "sweep_kill_bobler_scadutree.log", window=60)
    assert got.get("FIRED WITHOUT A KILL") == [2050480810]


# ---------------------------------------------------------------------------------------------
# The false-positive suite. Every case here was a real bug found in review, and each one accused a
# player whose own log held the exonerating line. They are grouped because they share one rule:
# a reading that could legitimately explain the sweep must produce UNJUDGED, never an accusation.
# ---------------------------------------------------------------------------------------------
def test_the_primary_is_clean_when_the_secondarys_bar_is_the_one_that_dies(tool, tables, tmp_path):
    """"One fight, several bars" -- so the bar the probe names at death may be the SECONDARY's.

    In Spiritcaller's Cave the snail summons the Godskins and the bar on screen when it ends is
    usually theirs. A secondary->primary-only candidate map accused the SNAIL (and the other
    Godskin) on a perfectly ordinary kill. The client's own boss_fight_end_guard_replay.rs quotes
    npc_param 35600972 -- a Godskin row -- from a real log.
    """
    log = write_log(tmp_path, "secondary_bar.log", [
        "14:02:10 [INFO] sweep-watch: census -- 3 group(s), 0 already set: "
        "[31220800(12), 31220801(12), 31220802(12)]",
        "14:10:03 [INFO] boss-fight END: npc_param 35600972 outcome=BOSS DOWN t=79.4s unseen=0.0s "
        "last boss 0/12400 (0%) player 1102/1420 (77%)",
        "14:10:05 [INFO] sweep-watch: trigger flag 31220800 -> SET (12 member(s) in its group)",
        "14:10:05 [INFO] sweep-watch: trigger flag 31220801 -> SET (12 member(s) in its group)",
        "14:10:05 [INFO] sweep-watch: trigger flag 31220802 -> SET (12 member(s) in its group)",
    ])
    got = run(tool, tables, None, path=log)
    assert not got.get("FIRED WITHOUT A KILL"), (
        "one Godskin bar came down and the whole arena paid out; none of the three heads may be "
        "accused -- got %r" % (got,))


def test_consumption_is_a_maximum_matching_not_a_greedy_grab(tool, tables, tmp_path):
    """Two same-family sweeps, two same-family kills, and a legal assignment exists.

    Greedy "nearest kill wins, first come first served" let the 12:20:00 sweep take the 12:20:50
    kill, stranding the 12:25:00 sweep whose own kill (12:15:20) had fallen out of its window --
    and the tool then printed that exonerating kill in its own `--unclaimed` section. A sweep may
    only be unmatched when NO legal assignment could have fed it.
    """
    log = write_log(tmp_path, "greedy.log", [
        "12:05:12 [INFO] sweep-watch: census -- 2 group(s), 0 already set: "
        "[1034420800(21), 1034500800(19)]",
        "12:15:20 [INFO] boss-fight END: npc_param 45020920 outcome=BOSS DOWN t=100.0s unseen=0.0s "
        "last boss 0/19200 (0%) player 412/652 (63%)",
        "12:20:00 [INFO] sweep-watch: trigger flag 1034420800 -> SET (21 member(s) in its group)",
        "12:20:50 [INFO] boss-fight END: npc_param 45020920 outcome=BOSS DOWN t=100.0s unseen=0.0s "
        "last boss 0/19200 (0%) player 388/652 (59%)",
        "12:25:00 [INFO] sweep-watch: trigger flag 1034500800 -> SET (19 member(s) in its group)",
    ])
    got = run(tool, tables, None, path=log)
    assert not got.get("FIRED WITHOUT A KILL"), (
        "12:20:00<-12:15:20 and 12:25:00<-12:20:50 is a legal pairing; both sweeps are fed -- "
        "got %r" % (got,))
    assert sorted(got.get("clean", [])) == [1034420800, 1034500800]


def test_a_fight_the_client_could_not_classify_excuses_the_sweep(tool, tables, tmp_path):
    """`outcome=unresolved` is documented as real and expected around phase transitions and
    cutscenes. A boss actually killed in that state never prints BOSS DOWN, so accusing the sweep
    is accusing the player for our instrument's blind spot.
    """
    log = write_log(tmp_path, "unresolved.log", [
        "12:05:12 [INFO] sweep-watch: census -- 1 group(s), 0 already set: [1034420800(21)]",
        "12:19:42 [INFO] boss-fight END: npc_param 45020920 outcome=unresolved t=114.0s "
        "unseen=114.0s last unread (the boss was never found in the live sets)",
        "12:19:44 [INFO] sweep-watch: trigger flag 1034420800 -> SET (21 member(s) in its group)",
    ])
    got = run(tool, tables, None, path=log)
    assert got.get("UNJUDGED") == [1034420800] and not got.get("FIRED WITHOUT A KILL")


def test_an_instrument_fault_end_excuses_the_sweep(tool, tables, tmp_path):
    """An END the client marked INSTRUMENT FAULT is the client disowning its own classification.

    `end_instrument_fault` only ever marks PLAYER DOWN lines, which is precisely a fight whose
    "the player lost" verdict is not to be trusted -- i.e. one that may have been a win.
    """
    log = write_log(tmp_path, "fault.log", [
        "12:05:12 [INFO] sweep-watch: census -- 1 group(s), 0 already set: [1034420800(21)]",
        "12:19:42 [INFO] boss-fight END: npc_param 45020920 outcome=PLAYER DOWN t=34.5s "
        "unseen=25.6s last boss 0/19200 (0%) player 414/414 (100%) -- INSTRUMENT FAULT: the player "
        "is at 100% on a PLAYER DOWN",
        "12:19:44 [INFO] sweep-watch: trigger flag 1034420800 -> SET (21 member(s) in its group)",
    ])
    got = run(tool, tables, None, path=log)
    assert got.get("UNJUDGED") == [1034420800] and not got.get("FIRED WITHOUT A KILL")


def test_a_collapsed_duplicate_line_is_still_read(tool, tables, tmp_path):
    """Every sink sits behind `CollapseDuplicates`, which rewrites a repeated record as
    "... repeated N times (M total): <message>". Anchored regexes missed those, so a collapsed
    BOSS DOWN vanished from the evidence while the sweep it caused stayed and got accused.
    """
    log = write_log(tmp_path, "collapsed.log", [
        "12:05:12 [INFO] sweep-watch: census -- 1 group(s), 0 already set: [1034420800(21)]",
        "12:19:42 [INFO] ... repeated 2 times (3 total): boss-fight END: npc_param 45020920 "
        "outcome=BOSS DOWN t=114.0s unseen=0.0s last boss 0/19200 (0%) player 412/652 (63%)",
        "12:19:44 [INFO] sweep-watch: trigger flag 1034420800 -> SET (21 member(s) in its group)",
    ])
    got = run(tool, tables, None, path=log)
    assert got.get("clean") == [1034420800] and not got.get("FIRED WITHOUT A KILL")


def test_a_silenced_probe_excuses_everything(tool, tables, tmp_path):
    """`ER_BOSSFIGHT_PROBE=0` prints its own banner. Reading that and then judging anyway would be
    the tool ignoring the one line that says it cannot measure.
    """
    p = tmp_path / "silenced.log"
    p.write_text(
        "12:05:00 [INFO] === SESSION START 2026-08-16 12:05:00 | pid 7 | this file is APPENDED "
        "across launches: everything above belongs to an earlier run ===\n"
        "12:05:11 [INFO] boss-fight probe: SILENCED by ER_BOSSFIGHT_PROBE=0 / probes.boss_fight=false\n"
        "12:05:12 [INFO] sweep-watch: census -- 1 group(s), 0 already set: [1034420800(21)]\n"
        "12:19:44 [INFO] sweep-watch: trigger flag 1034420800 -> SET (21 member(s) in its group)\n"
        "12:20:00 [INFO] boss-fight START: t=0.0s npc_param 45020920 npc_id 5240 region 1034420 "
        "boss 19200/19200 (100%) player 652/652 (100%)\n", encoding="utf-8")
    got = run(tool, tables, None, path=str(p))
    assert got.get("UNJUDGED") == [1034420800] and not got.get("FIRED WITHOUT A KILL")


def test_a_same_poll_burst_with_no_kills_reads_as_a_save_swap(tool, tables, tmp_path):
    """`sweep_watch.reset()` is only called for a NEW SEED, and the poll is gated on being in
    world. Quitting to the menu and loading a DIFFERENT CHARACTER on the same seed therefore
    replays that save's already-dead bosses as a burst of fresh SET transitions in one poll.

    🛑 A burst is not by itself a signature -- the m31_22 fixture innocently fires three heads in
    one poll -- so the rule only engages when NOT ONE member of the burst found a kill.
    """
    log = write_log(tmp_path, "saveswap.log", [
        "12:05:12 [INFO] sweep-watch: census -- 3 group(s), 0 already set: "
        "[10000800(30), 14000800(24), 16000800(18)]",
        "12:31:00 [INFO] boss-fight START: t=0.0s npc_param 45020920 npc_id 5240 region 1034420 "
        "boss 19200/19200 (100%) player 652/652 (100%)",
        "12:40:00 [INFO] sweep-watch: trigger flag 10000800 -> SET (30 member(s) in its group)",
        "12:40:00 [INFO] sweep-watch: trigger flag 14000800 -> SET (24 member(s) in its group)",
        "12:40:00 [INFO] sweep-watch: trigger flag 16000800 -> SET (18 member(s) in its group)",
    ])
    got = run(tool, tables, None, path=log)
    assert not got.get("FIRED WITHOUT A KILL"), (
        "three legacy sweeps in one poll with no kill near any of them is a character load, not "
        "three broken sweeps -- got %r" % (got,))
    assert sorted(got.get("UNJUDGED", [])) == [10000800, 14000800, 16000800]


def test_the_burst_rule_does_not_swallow_a_real_finding(tool, tables, tmp_path):
    """The counterweight to the test above. A burst where SOME member matched is a real poll of a
    real arena, and the members that found nothing are still answerable -- otherwise one innocent
    sweep in a group would launder every defect beside it.
    """
    log = write_log(tmp_path, "burst_partial.log", [
        "12:05:12 [INFO] sweep-watch: census -- 3 group(s), 0 already set: "
        "[1034420800(21), 14000800(24), 16000800(18)]",
        "12:39:50 [INFO] boss-fight END: npc_param 45020920 outcome=BOSS DOWN t=90.0s unseen=0.0s "
        "last boss 0/19200 (0%) player 412/652 (63%)",
        "12:40:00 [INFO] sweep-watch: trigger flag 1034420800 -> SET (21 member(s) in its group)",
        "12:40:00 [INFO] sweep-watch: trigger flag 14000800 -> SET (24 member(s) in its group)",
        "12:40:00 [INFO] sweep-watch: trigger flag 16000800 -> SET (18 member(s) in its group)",
    ])
    got = run(tool, tables, None, path=log)
    assert got.get("clean") == [1034420800]
    assert sorted(got.get("FIRED WITHOUT A KILL", [])) == [14000800, 16000800]


# ---------------------------------------------------------------------------------------------
# D. Enemy randomisation. A supported configuration, and the one that would otherwise have turned
#    the whole report red for half the testers.
# ---------------------------------------------------------------------------------------------
def test_a_matt_stack_is_judged_identity_blind_not_condemned(tool, tables):
    """matt's rando rewrites regulation.bin / map/ / event/ on disk; the probe reads the LIVE
    occupant out of GameDataMan. So on a swapped arena the npc_param the log carries has nothing to
    do with the vanilla boss this table names, and a strict identity join would accuse every
    randomised sweep in the session.

    The client says it outright in the same log: "treat this session as NON-VANILLA: enemy/arena
    bindings ... may not be the game's own". Sweeps stay ARENA-keyed, so the FLAGS are untouched --
    only identity breaks. Drop identity, keep timing.

    The fixture's kill is npc_param 40000110, which is in NO trigger's candidate set.
    """
    npcs, pairs, skips = tables
    sessions = tool.parse_log(os.path.join(FIXTURES, "sweep_kill_matt_enemy_rando.log"))
    assert len(sessions) == 1
    assert sessions[0].data_mod == "thefifthmatt ER Randomizer", (
        "the fingerprint line is how the tool knows; if mod_stack's format moves this is the test "
        "that says so -- got %r" % (sessions[0].data_mod,))
    assert not any(40000110 in m["npcs"] for m in npcs.values()), (
        "this fixture is only meaningful while the swapped-in npc_param is foreign to every "
        "candidate set")
    findings, _ = tool.correlate(sessions[0], npcs, pairs, skips, tool.DEFAULT_WINDOW,
                                 tool.DEFAULT_LEAD)
    by_flag = {f.flag: f for f in findings}
    assert by_flag[1034420800].verdict == "clean"
    assert "IDENTITY-BLIND" in by_flag[1034420800].detail


def test_enemy_rando_does_not_make_the_tool_blind_to_the_defect(tool, tables):
    """The counterweight. Identity-blind is weaker, not off: the second sweep in the same fixture
    fired 7m29s after the only kill in the session and must still be caught. This is what makes the
    degrade worth having rather than a polite way of measuring nothing -- #697's sweep had no fight
    near it AT ALL, and that remains visible without knowing who died.
    """
    got = run(tool, tables, "sweep_kill_matt_enemy_rando.log")
    assert got.get("FIRED WITHOUT A KILL") == [1034500800]


def test_a_vanilla_session_is_not_downgraded(tool, tables):
    """Identity-blind must engage on evidence, not by default. A log with no `mod stack:` data-mod
    line keeps the strong join -- otherwise the whole feature quietly becomes timing-only.
    """
    npcs, _pairs, _skips = tables
    sessions = tool.parse_log(os.path.join(FIXTURES, "sweep_kill_islam_liurnia.log"))
    assert sessions[0].data_mod is None
    del npcs


# ---------------------------------------------------------------------------------------------
# Parsing invariants the three fixtures do not otherwise pin.
# ---------------------------------------------------------------------------------------------
def test_census_already_set_flags_are_unjudged_not_clean(tool, tables):
    """A flag already SET at the census was never observed to FIRE, so it cannot be adjudicated.

    Counting it as clean would let a log full of pre-set flags report a perfect score.
    """
    npcs, pairs, skips = tables
    sessions = tool.parse_log(os.path.join(FIXTURES, "sweep_kill_islam_liurnia.log"))
    assert len(sessions) == 1 and sessions[0].start_date == "2026-08-15"
    session = sessions[0]
    session.census_set = [(1034420800, 21, 5)]
    findings, _ = tool.correlate(session, npcs, pairs, skips, tool.DEFAULT_WINDOW, tool.DEFAULT_LEAD)
    census = [f for f in findings if f.clock == "census"]
    assert census and all(f.verdict == "UNJUDGED" for f in census)


def test_a_session_that_never_censused_is_unjudged(tool, tables, tmp_path):
    """`SweepWatch::observe` emits the census on its first call and returns, so a `-> SET`
    transition can never be a session's first sweep-watch line. One that is means the file was
    rotated or truncated mid-session -- we never saw the baseline, so there is nothing to judge.
    """
    p = tmp_path / "truncated.log"
    p.write_text(
        "10:05:00 [INFO] === SESSION START 2026-08-15 10:05:00 | pid 2 | this file is APPENDED "
        "across launches: everything above belongs to an earlier run ===\n"
        "10:05:30 [INFO] boss-fight START: t=0.0s npc_param 32520921 npc_id 3252 region 1035500 "
        "boss 6960/6960 (100%) player 652/652 (100%)\n"
        "10:06:00 [INFO] sweep-watch: trigger flag 1034420800 -> SET (21 member(s) in its group)\n",
        encoding="utf-8")
    got = run(tool, tables, None, path=str(p))
    assert got.get("UNJUDGED") == [1034420800] and not got.get("FIRED WITHOUT A KILL")


def test_a_session_with_no_fight_lines_is_unjudged_not_guilty(tool, tables):
    """`ER_BOSSFIGHT_PROBE=0` silences the probe, and the log is APPENDED across launches -- so a
    session with no boss-fight lines may simply be reading a flag whose kill happened yesterday.

    Flagging those would condemn every uninstrumented session wholesale, which is how a detector
    gets switched off. #697 is unaffected: that session held two other fights.
    """
    npcs, pairs, skips = tables
    session = tool.Session("synthetic.log", 1, "2026-08-16", 1)
    session.censused = True
    session.sets = [(3600, 1034420800, 21, 10, "01:00:00")]
    findings, _ = tool.correlate(session, npcs, pairs, skips, tool.DEFAULT_WINDOW, tool.DEFAULT_LEAD)
    assert len(findings) == 1
    assert findings[0].verdict == "UNJUDGED"
    assert "uninstrumented" in findings[0].detail
