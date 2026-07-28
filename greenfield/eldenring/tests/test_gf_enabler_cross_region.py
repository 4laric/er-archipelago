"""No StartDisabled treasure is gated on another region's flag without protection.

THE CORPUS THIS SCREENS, and why it needed its own screen. `test_gf_lot_gates_cross_region` reads
ONLY `lot_gates.tsv` and holds unprotected cross-region gates there at zero. `treasure_enablers.tsv`
is a DIFFERENT corpus that screen has never read: it records what enables a `StartDisabled=1`
treasure, including `external_gate_flags` -- flags the enabling event tests that the check's own map
never sets. Screening those found one nothing protected:

    f580600  Belurat :: Message from Leda -- enabler `WaitFor(EventFlag(580600) || EventFlag(9146))`.
             The alternation is with the check's OWN acquisition flag ("already taken"), so 9146 is a
             requirement -- and 9146 is MESSMER's reward flag, m21_01.
             ✅ CONFIRMED IN-GAME, Alaric, 2026-07-28: "message from leda requires defeating messmer".

That is the bug this file exists to keep dead: a region Lock lights Belurat's graces, the player
warps straight to the pickup, and there is nothing there. The warp bypasses the ROUTE, never the
PREREQUISITE.

WHAT IS ASSERTED. Not "580600 is tagged" -- that is a fixture, and a fixture cannot catch the NEXT
one. The population is RE-DERIVED from the committed tsv every run, and every member must be either
missable-tagged or explicitly adjudicated below. A new unprotected enabler gate turns this red.

ADJUDICATION, and why a hand list is legitimate HERE. CONTRIBUTING allows one only where the
derivation genuinely cannot reach, and this is that case: whether a "cross-region" enabler is a real
prerequisite or a tile-straddle artifact is a question about the GAME, and the only oracle is a human
playing it. Each entry therefore carries a date, a source, and the reason -- and if the derivation
ever learns to tell these apart, the entry must be DELETED, not kept as belt-and-braces.
"""
import collections
import csv
import os
import re
import warnings

import pytest

pytest.importorskip("worlds.eldenring")
from worlds.eldenring.data import LOCATIONS  # noqa: E402
from worlds.eldenring.missable_locations import MISSABLE_LOCATIONS  # noqa: E402

_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# flag -> (verdict, why). ADJUDICATED BY THE LIVE-GAME ORACLE, never by a derivation.
ADJUDICATED_NOT_A_GATE = {
    1039537050: ("Rise puzzle, not a questline (Alaric, in-game, 2026-07-28)",
                 "Unseen Blade at the Bower of Bounty rise: 'a classic rise puzzle where you have "
                 "to interact with three objects near the rise to open the door'. The three gate "
                 "flags 1039520655 / 1039530655 / 1040530655 ARE a genuine conjunction -- the DAG "
                 "reads them as semantics=all, correctly -- but all three objects stand within "
                 "sight of the rise. The 'cross-region' reading comes from 1040530655 decoding to "
                 "tile m60_40_53, which is Altus: the rise sits ON the Gelmir/Altus tile boundary, "
                 "so this is a BORDER, not a gate (the tile->region arity trap). Corroborated by "
                 "the flag's own EMEVD setter event name: 'Magician's Tower_Stopping the gimmick "
                 "device' -- a mechanism, not a quest."),
    1039537060: ("Rise puzzle, not a questline (Alaric, in-game, 2026-07-28)",
                 "Slumbering Egg, same rise, same three objects, same reasoning as f1039537050. "
                 "Alaric: 'looks like slumbering egg is probably in the same rise'."),
}


def _rows(name):
    path = os.path.join(_PKG, name)
    if not os.path.isfile(path):
        pytest.skip("%s not installed beside the package -- this screen would run BLIND" % name)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(
            (ln for ln in fh if not ln.lstrip().startswith("#")), delimiter="\t")


def _cross_region_prerequisites():
    """-> [(target_flag, source_flag, source_region, target_region)] from questline_dag.tsv.

    Only `tool=treasure_enablers`, only `sense=set`: an EXCLUSION cannot strand a seed, and an
    `unknown` polarity is exactly what must not be reasoned with.
    """
    out = []
    for r in _rows("questline_dag.tsv"):
        if r.get("tool") != "treasure_enablers" or r.get("sense") != "set":
            continue
        if r.get("cross_region") != "yes":
            continue
        out.append((int(r["target_flag"]), int(r["source_flag"]),
                    r.get("source_region", ""), r.get("target_region", "")))
    return out


def test_f580600_the_case_this_screen_was_built_for_is_still_seen():
    """END TO END, BY NAME (CONTRIBUTING rule 11).

    This one was PRODUCED and then lost twice before it was wired: named as "the one real
    cross-region prerequisite, still unwired" in both the 2026-07-26 and 2026-07-27 handoffs, and
    protected by nothing in between. A screen that can no longer SEE it is back in that state, so
    every stage is asserted: the row exists, its polarity is still `set`, it is still read as
    cross-region, and the check is tagged.
    """
    rows = [r for r in _rows("questline_dag.tsv")
            if r.get("target_flag") == "580600" and r.get("source_flag") == "9146"]
    assert rows, ("f580600 <- 9146 has vanished from questline_dag.tsv. Either the treasure-enabler "
                  "producer regressed or `_enabler_sense` stopped resolving the own-flag "
                  "alternation -- re-emit with `python tools/build_questline_dag.py`.")
    assert all(r["sense"] == "set" for r in rows), (
        "f580600 <- 9146 is no longer read as a PREREQUISITE (senses %s). Messmer's death is a "
        "requirement, confirmed in-game 2026-07-28; if the polarity rule changed, it is the rule "
        "that is wrong." % sorted({r["sense"] for r in rows}))
    assert all(r["cross_region"] == "yes" for r in rows), (
        "f580600 <- 9146 no longer reads as cross-region, so the screen below can no longer reach "
        "it. That is the exact state in which this bug shipped twice.")
    ap = {f: a for _r, locs in LOCATIONS.items() for (_n, a, f) in locs}.get(580600)
    assert ap is not None, "f580600 is not a location any more -- it fell out of the world"
    assert ap in MISSABLE_LOCATIONS, (
        "f580600 (Message from Leda) is NOT missable-tagged, so fill may put REQUIRED progression "
        "on a check that does not exist until Messmer is dead. A region Lock lights Belurat's "
        "graces and the player warps to an empty spot. Add 580600 to gen_data._ENABLER_CROSS_REGION "
        "and regen.")


def test_no_unprotected_cross_region_enabler_gate():
    pairs = _cross_region_prerequisites()
    assert pairs, ("questline_dag.tsv yielded ZERO cross-region treasure-enabler prerequisites. "
                   "One is KNOWN (f580600 <- 9146, confirmed in-game). An empty screen is a "
                   "FAILURE, not a clean run -- the join or the emit has broken.")
    check_ap = {f: a for _r, locs in LOCATIONS.items() for (_n, a, f) in locs}
    check_name = {f: n for _r, locs in LOCATIONS.items() for (n, _a, f) in locs}
    assert MISSABLE_LOCATIONS, "MISSABLE_LOCATIONS is empty -- every gate would read as protected"

    unprotected, adjudicated = [], []
    for target, source, sreg, treg in pairs:
        if check_ap.get(target) in MISSABLE_LOCATIONS:
            continue
        where = ("f%d [%s] %s <- f%d [%s]"
                 % (target, treg, check_name.get(target, "")[:44], source, sreg))
        (adjudicated if target in ADJUDICATED_NOT_A_GATE else unprotected).append(where)

    warnings.warn(
        "[enabler cross-region] %d cross-region prerequisite pair(s) over %d check(s); %d "
        "adjudicated NOT a gate by the live-game oracle, %d unprotected."
        % (len(pairs), len({t for t, _s, _a, _b in pairs}), len(adjudicated), len(unprotected)),
        stacklevel=2)

    assert not unprotected, (
        "%d StartDisabled treasure(s) are gated on ANOTHER region's flag and are NOT missable-tagged. "
        "Each claims a reachability it does not have, and a region Lock will warp a player to an "
        "empty pickup. Either add the flag to gen_data._ENABLER_CROSS_REGION and regen, or -- if the "
        "live game says it is a border artifact rather than a gate -- adjudicate it in "
        "ADJUDICATED_NOT_A_GATE with a date, a source and a reason:\n  %s"
        % (len(unprotected), "\n  ".join(unprotected)))


def test_adjudications_are_still_load_bearing():
    """A hand list that has stopped doing anything must be DELETED, not kept as belt-and-braces.

    CONTRIBUTING is explicit that a redundant manual override is "a lie about why the code works":
    the next reader cannot tell which entries carry weight, so nobody dares remove any. So every
    adjudication must still be REACHED by the derivation -- if the screen no longer reports a flag
    as a cross-region prerequisite, its exemption is dead code and the entry goes.
    """
    reachable = {t for t, _s, _a, _b in _cross_region_prerequisites()}
    stale = sorted(set(ADJUDICATED_NOT_A_GATE) - reachable)
    assert not stale, (
        "ADJUDICATED_NOT_A_GATE exempts %s, but the screen no longer reports them as cross-region "
        "prerequisites at all -- the exemption protects nothing. Delete the entr%s; a redundant "
        "override hides which of the others are load-bearing."
        % (stale, "y" if len(stale) == 1 else "ies"))
    for flag, (verdict, why) in sorted(ADJUDICATED_NOT_A_GATE.items()):
        assert re.search(r"\d{4}-\d{2}-\d{2}", verdict), (
            "adjudication for f%d has no DATE. 'Ground truth expires; date it like a dump file.'"
            % flag)
        assert len(why) > 80, (
            "adjudication for f%d has no real reason attached. An unexplained exemption is "
            "indistinguishable from a mistake six months from now." % flag)
