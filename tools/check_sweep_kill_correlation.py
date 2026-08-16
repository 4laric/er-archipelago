#!/usr/bin/env python3
r"""check_sweep_kill_correlation.py -- #713. Did every boss sweep that FIRED have a boss KILL behind it?

    python3 tools/check_sweep_kill_correlation.py log/archipelago-2026-08-15.log
    python3 tools/check_sweep_kill_correlation.py logs/*.log --window 300
    python3 tools/check_sweep_kill_correlation.py a.log --verbose     # show the clean ones too

Exit 0 = nothing flagged. Exit 1 = at least one sweep fired with no kill behind it. Exit 2 = the
tool could not run (missing table, unreadable path) -- a different failure from a finding, because a
gate that cannot tell "measured, and it is bad" from "did not measure" is not a gate.

WHY. #671 asks WHERE the trigger boss is fought. This asks something nothing checks at all: does the
trigger flag mean somebody killed something? Four ways a trigger can be wrong; modes 2 (`Patches
yields instead of dying`, #672) and 3 (`SWEEP_UNSPAWNED`) are closed, mode 4 (the suppressed
secondary heads) is an untested premise, and MODE 1 -- fires WITHOUT a kill -- has a confirmed
instance (#697) and had no instrument. This is the instrument.

⭐ IT IS A JOIN, NOT A DATAMINE. Both halves are already written to the same log by the same client:

    12:23:45 [INFO] sweep-watch: trigger flag 1034500800 -> SET (19 member(s) in its group)
    12:19:42 [INFO] boss-fight END: npc_param 45020920 outcome=BOSS DOWN t=114.0s ...

`sweep_watch.rs` says outright that it owns "the decision of what to SAY" about the flag, and it
never looks at a fight. Joining these by hand is exactly what found #697 -- three Liurnia sweeps in
eight minutes, two bracketing a third that fired on nothing. That comparison should be a gate, not a
thing somebody happens to notice.

OFFLINE ON PURPOSE (ruling 1, Alaric 2026-08-16). A `tools/` script runs over every log already
uploaded, costs no runtime in a player's game, and can be re-run when the rule changes. A live
client warning is louder and is one more thing that can fire wrongly mid-fight. This is a forensic
question, not a gameplay one.

THE WINDOW (ruling 2, Alaric 2026-08-16): 5 minutes, and generous ON PURPOSE.
🛑 THIS IS THE TRAP IN THE WHOLE FEATURE. `sweep_watch.rs`'s own motivating case is a LEGITIMATE
2m45s gap -- bobler killed the Scadutree Avatar's boss at 13:01:02 and the 49-check sweep landed at
13:03:47, one warp later, and he reported it as broken. A tight window would cry wolf on exactly the
case that module exists to explain. 300s clears it with room, and it costs us nothing on the case we
are hunting: #697's sweep had NO boss fight in the session at all, so it flags at any width.

    --window 300   how far BACK of a SET a kill may be                 (the 2m45s case lives here)
    --lead    60   how far FORWARD. The flag flips on death; the probe's END fires when the
                   healthbar leaves the live sets, which is after the death cam -- so a real kill
                   can be timestamped slightly AFTER the sweep it caused.

⭐ ONE KILL CLEANS ONE SWEEP, VIA A MAXIMUM MATCHING. A `BOSS DOWN` is consumed by the sweep that
claims it -- two sweeps paying out off one kill IS mode 1's shape, and without consumption islam's
log reads green (Adula has two triggers resolving to the SAME chr family, so the 12:19:42 kill would
silently clean the 12:23:45 sweep that fired on nothing).
🛑 BUT CONSUMPTION MUST NOT BE GREEDY. "Nearest kill wins, first come first served" lets an early
sweep take a late kill and strand a later sweep whose own kill has fallen out of its window -- two
same-family sweeps and two same-family kills, which is islam's shape again. That accuses a player
whose log contains the exonerating line, printed by our own `--unclaimed`. So the assignment is a
real maximum bipartite matching: a sweep is only unmatched when NO legal assignment could have fed
it.

🛑 THE SUPPRESSED HEADS ARE THE ALLOWLIST, NOT NOISE (`greenfield/boss_arena_pairs.tsv`, #363).
"One fight, several bars" -- so the bar the probe happens to name at the moment of death may belong
to ANY head in the arena, and the candidate set is therefore unioned in BOTH directions: a secondary
may match on its primary's npcs, and a primary may match on its secondaries'. One-directional was a
bug that accused the Spiritcaller Snail whenever the Godskin's bar was the one on screen -- and the
client's own `boss_fight_end_guard_replay.rs` quotes a real log line doing exactly that. Secondaries
may also SHARE a kill the primary already consumed; that is mode 4 working as designed.

WHAT THIS CANNOT DO, stated because a silent limit in an instrument is worse than a known one, and
every one of these resolves to UNJUDGED -- a third verdict that is never counted as clean:
* The flag->npc_param join is a CANDIDATE SET (`greenfield/sweep_trigger_npcs.tsv`), because the
  MSBs that would make it exact are deliberately not in the bundle. A wide set is LENIENT -- this
  under-reports, it does not invent. 9 triggers resolve to nothing at all.
* Flags already SET at the census were not observed to FIRE.
* A fight the probe could not classify. `outcome=unresolved` is documented as "real and expected
  around phase transitions and cutscenes", and an `INSTRUMENT FAULT` END is the client saying its
  own verdict is untrustworthy. Either one, in the window, on a candidate npc_param, excuses the
  sweep -- a boss really killed under those conditions never prints `BOSS DOWN`.
* An uninstrumented session (`ER_BOSSFIGHT_PROBE=0`, or no `boss-fight` lines at all). The log is
  APPENDED across launches, so a kill can belong to an earlier session entirely.
* A burst of SETs at one timestamp with no kill anywhere near any of them. Loading a DIFFERENT
  CHARACTER on the same seed does not reset `sweep_watch`, so the next poll replays that save's
  already-dead bosses as fresh transitions. That is a save swap, not N broken sweeps.

⭐ ENEMY RANDOMISATION -- IDENTITY-BLIND MODE, and this is the case that would otherwise have made
the tool useless to half the testers. matt's randomiser rewrites `regulation.bin`, `map/` and
`event/` on disk; `boss_healthbar_npc_param_id()` reads the LIVE occupant out of `GameDataMan` and
`match_boss` compares against `ChrIns.npc_param_id`, so what the probe prints is whoever is actually
standing in the arena. This table is derived from VANILLA params. On a matt stack the two describe
different creatures and every swapped arena would read as a sweep that fired on nothing -- a red
report across the board, for a supported configuration.

The repo has already ruled on this exact shape once: `gen_sweep_boss_names.py` keeps the ARENA's
vanilla boss and states the mismatch, because "sweeps are ARENA-keyed -- the reward follows the room,
not the character". The flag half is untouched by enemy rando; only the identity half breaks.

So when the client's own provenance block reports a co-loaded data mod -- it logs
`mod stack: THIRD-PARTY DATA MOD at ...` and `mod stack: fingerprinted randomizer(s): ...` on every
launch, and says in as many words "treat this session as NON-VANILLA: enemy/arena bindings ... may
not be the game's own" -- this drops identity and keeps timing: a sweep is clean if ANY `BOSS DOWN`
falls in its window. That is weaker, and it is still enough for the defect being hunted, because
#697's sweep had no boss fight near it AT ALL. Same fallback carries the 9 triggers whose vanilla
identity we never resolved.
🛑 Identity-blind clean is WEAKER EVIDENCE and every such line says so. It is never silently mixed
in with a real identity match.
"""
import argparse
import collections
import glob
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
GF = os.path.join(REPO, "greenfield")
TRIGGER_NPCS = os.path.join(GF, "sweep_trigger_npcs.tsv")
ARENA_PAIRS = os.path.join(GF, "boss_arena_pairs.tsv")

DEFAULT_WINDOW = 300
DEFAULT_LEAD = 60
# How many same-second SETs, none of which found a kill, read as a save/character swap rather than
# as that many independent defects. Three is the smallest burst the real data produces innocently
# (m31_22 fires three heads in one poll), so the rule only engages at a size that has an innocent
# precedent -- and only when NOT ONE of them matched.
BURST_MIN = 3

EXIT_OK, EXIT_FINDINGS, EXIT_CANNOT_RUN = 0, 1, 2

# ---------------------------------------------------------------------------------------------
# The client's line grammar. Pinned against the emitters, not guessed:
#   crates/shared/src/lib.rs          simplelog Config::default() -> "HH:MM:SS [LEVEL] msg"
#   crates/shared/src/log_collapse.rs the duplicate collapser that REWRITES a repeated record
#   crates/er-logic/src/sweep_watch.rs             census / SET / CLEARED / NEW group
#   crates/er-logic/src/boss_fight_sample.rs       format_sample / format_end, Outcome::label()
#   crates/eldenring-archipelago/src/boss_fight_probe.rs   the probe's ON / SILENCED banner
# 🛑 The file is opened in APPEND mode, one file per DAY, across launches -- so a single log holds
#    several sessions and the only absolute date in it is on the SESSION START line.
# ---------------------------------------------------------------------------------------------
RE_LINE = re.compile(r"^(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})\s+\[[A-Z]+\]\s+(?P<msg>.*)$")
# 🛑 EVERY sink sits behind `CollapseDuplicates`, which re-emits a repeated record as
# "... repeated N times (M total): <the original message>". Anchored patterns miss those entirely --
# and a collapsed BOSS DOWN is a kill that vanishes from the evidence while the sweep it caused
# stays. Strip the prefix before dispatching; it is the difference between a lenient tool and one
# that accuses on its own parser's blind spot.
RE_COLLAPSED = re.compile(r"^\.\.\. repeated \d+ times \(\d+ total\): ")
RE_SESSION = re.compile(r"=== SESSION START (?P<date>\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2} \| pid (?P<pid>\d+)")
RE_SET = re.compile(r"^sweep-watch: trigger flag (?P<flag>\d+) -> SET \((?P<members>\d+) member")
RE_NEW = re.compile(r"^sweep-watch: NEW group, trigger flag (?P<flag>\d+) = (?P<state>SET|clear)")
RE_CENSUS = re.compile(r"^sweep-watch: census -- \d+ group\(s\), \d+ already set: \[(?P<body>.*)\]")
RE_CENSUS_ENTRY = re.compile(r"(?P<flag>\d+)\((?P<members>\d+)\)(?P<set>=SET)?")
RE_END = re.compile(r"^boss-fight END: npc_param (?P<npc>-?\d+) "
                    r"outcome=(?P<outcome>BOSS DOWN|PLAYER DOWN|unresolved)\b")
RE_FIGHT_ANY = re.compile(r"^boss-fight (START|SAMPLE|END|CAPPED)\b")
RE_PROBE_SILENCED = re.compile(r"^boss-fight probe: SILENCED")
# `shared::mod_stack::log_provenance()` runs unconditionally right after logger init, so these sit
# at the head of every log. The DATA MOD line is the one that matters -- the fingerprint is a
# stronger hint but the client itself says "a hit is a STRONG hint, not a proof, and a miss proves
# nothing at all", so we key off the presence of foreign data files, not off the name.
RE_MOD_DATA = re.compile(r"^mod stack: THIRD-PARTY DATA MOD at .* -- (?P<files>.*)\.$")
RE_MOD_NAMED = re.compile(r"^mod stack: fingerprinted randomizer\(s\): (?P<names>.*)$")

INSTRUMENT_FAULT = "INSTRUMENT FAULT"

End = collections.namedtuple("End", "t npc lineno clock outcome fault")


# ---------------------------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------------------------
class CannotRun(Exception):
    """The tool could not measure. Distinct from measuring and finding something."""


def load_trigger_npcs(path=TRIGGER_NPCS):
    """{flag: {"npcs": set(), "method": str, "name": str, "class": str, "tile": str}}."""
    if not os.path.exists(path):
        raise CannotRun(
            "%s is missing. It is a Tier-2 emit (AGENTS §5a):\n"
            "    python3 tools/datamine_sweep_trigger_npcs.py\n"
            "🛑 Do not run this checker without it -- with no candidate sets every sweep would "
            "read as UNJUDGED and the log would look clean." % path)
    return _read_tsv(path, "trigger_flag", lambda row: {
        "npcs": {int(p) for p in (row.get("npc_params") or "").split(";") if p.strip()},
        "method": row.get("method", ""),
        "name": row.get("name", ""),
        "class": row.get("class", ""),
        "tile": row.get("tile", ""),
    })


def load_arena_pairs(path=ARENA_PAIRS):
    """{secondary flag: primary flag} -- the heads whose fight is reported by another head (#363)."""
    if not os.path.exists(path):
        return {}
    return _read_tsv(path, "secondary", lambda row: int(row["primary"]))


def _read_tsv(path, key, build):
    out = {}
    with open(path, encoding="utf-8") as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            cells = line.split("\t")
            if header is None:
                header = cells
                continue
            row = dict(zip(header, cells))
            out[int(row[key])] = build(row)
    return out


def load_skips():
    """`contract.sweep_slot_skips()` -- the triggers SweepSlot must not nominate from (#672).

    Loaded by file path, not by import: `eldenring/__init__` pulls Archipelago's `BaseClasses`, and
    a forensic tool must run in a bare checkout. Returns {} rather than dying if the shape moves --
    the skips only decorate a finding here, they never decide one.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "_er_contract", os.path.join(GF, "eldenring", "contract.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return dict(mod.sweep_slot_skips())
    except Exception:  # noqa: BLE001 -- decoration only, never a verdict
        return {}


# ---------------------------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------------------------
class Session:
    """One client launch: its own sweep-watch state, so events never correlate across a reconnect."""

    def __init__(self, path, index, start_date, start_line):
        self.path = path
        self.index = index
        self.start_date = start_date
        self.start_line = start_line
        self.sets = []            # (t, flag, members, lineno, clock)
        self.ends = []            # End(...) -- EVERY finished fight, not only the wins
        self.census_set = []      # (flag, members, lineno) -- already SET, never observed to fire
        self.new_group_set = []   # (flag, lineno)
        self.fight_lines = 0
        self.probe_silenced = False
        # 🛑 `SweepWatch::observe` emits the census on its FIRST call and returns -- a `-> SET`
        # transition can never be the first sweep-watch line of a real session. Seeing one without
        # a census means the file was rotated or truncated mid-session, and a transition whose
        # baseline we never saw cannot be adjudicated.
        self.censused = False
        # A co-loaded data mod. `None` = vanilla as far as the log can tell; otherwise a short
        # description for the report. 🛑 Absence is NOT proof of vanilla -- mod_stack only scans
        # our directory and two parents, and says so itself. Which is fine in this direction: the
        # risk of missing one is a false accusation we would rather not make, and the risk of
        # seeing one is only that we judge more leniently.
        self.data_mod = None

    @property
    def kills(self):
        """The ENDs that assert a win. Everything else is evidence of an UNREADABLE fight."""
        return [e for e in self.ends if e.outcome == "BOSS DOWN" and not e.fault]

    @property
    def ambiguous(self):
        """ENDs that cannot exonerate by themselves but must stop us accusing: `unresolved`, and
        any END the client marked INSTRUMENT FAULT (it is disowning its own classification)."""
        return [e for e in self.ends if e.outcome != "BOSS DOWN" or e.fault]

    @property
    def label(self):
        return "%s session %d (%s, line %d)" % (
            os.path.basename(self.path), self.index, self.start_date or "date unknown",
            self.start_line)


def parse_log(path):
    """-> [Session]. Clock is HH:MM:SS only; a backwards step means the log crossed midnight."""
    sessions = []
    cur = None
    day = 0
    prev = None

    def ensure(lineno):
        nonlocal cur
        if cur is None:
            # A log whose first SESSION START was rotated away still has to be readable.
            cur = Session(path, len(sessions) + 1, None, lineno)
            sessions.append(cur)
        return cur

    with open(path, encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, 1):
            m = RE_LINE.match(line.rstrip("\n"))
            if not m:
                continue          # continuation lines of a multi-line record (panic backtraces)
            clock = int(m["h"]) * 3600 + int(m["m"]) * 60 + int(m["s"])
            if prev is not None and clock < prev:
                day += 1
            prev = clock
            t = day * 86400 + clock
            msg = RE_COLLAPSED.sub("", m["msg"])
            raw = "%s:%s:%s" % (m["h"], m["m"], m["s"])

            sm = RE_SESSION.search(msg)
            if sm:
                cur = Session(path, len(sessions) + 1, sm["date"], lineno)
                sessions.append(cur)
                continue

            if msg.startswith("sweep-watch:"):
                s = ensure(lineno)
                mm = RE_SET.match(msg)
                if mm:
                    s.sets.append((t, int(mm["flag"]), int(mm["members"]), lineno, raw))
                    continue
                mm = RE_CENSUS.match(msg)
                if mm:
                    s.censused = True
                    for e in RE_CENSUS_ENTRY.finditer(mm["body"]):
                        if e["set"]:
                            s.census_set.append((int(e["flag"]), int(e["members"]), lineno))
                    continue
                mm = RE_NEW.match(msg)
                if mm and mm["state"] == "SET":
                    s.new_group_set.append((int(mm["flag"]), lineno))
                continue

            if RE_PROBE_SILENCED.match(msg):
                ensure(lineno).probe_silenced = True
                continue

            if msg.startswith("mod stack:"):
                s = ensure(lineno)
                mm = RE_MOD_DATA.match(msg)
                if mm:
                    s.data_mod = s.data_mod or "third-party data mod (%s)" % mm["files"]
                mm = RE_MOD_NAMED.match(msg)
                if mm:
                    s.data_mod = mm["names"]
                continue

            if RE_FIGHT_ANY.match(msg):
                s = ensure(lineno)
                s.fight_lines += 1
                mm = RE_END.match(msg)
                if mm:
                    s.ends.append(End(t, int(mm["npc"]), lineno, raw, mm["outcome"],
                                      INSTRUMENT_FAULT in msg))
    return sessions


# ---------------------------------------------------------------------------------------------
# The correlation
# ---------------------------------------------------------------------------------------------
Finding = collections.namedtuple("Finding", "verdict session flag members clock lineno detail")


def candidates(flag, npcs, pairs, secondaries):
    """The npc_params a kill behind `flag` may carry.

    🛑 UNIONED IN BOTH DIRECTIONS. `boss_arena_pairs.tsv`'s own header calls the conjunct case "one
    fight, several bars", and on the subordinate case (the Spiritcaller Snail summoning Godskins)
    the bar that is up when the fight ends is usually the SECONDARY's. Mapping secondary->primary
    only is what made the primary flag whenever the wrong bar was on screen.
    """
    own = set(npcs.get(flag, {}).get("npcs", ()))
    primary = pairs.get(flag)
    if primary:
        own |= set(npcs.get(primary, {}).get("npcs", ()))
        for sib in secondaries.get(primary, ()):
            own |= set(npcs.get(sib, {}).get("npcs", ()))
    for sec in secondaries.get(flag, ()):
        own |= set(npcs.get(sec, {}).get("npcs", ()))
    return own


def _match(eligible):
    """Maximum bipartite matching, sweeps -> kills. `eligible` is {sweep idx: [kill idx, ...]}.

    Kuhn's algorithm. It is ~15 lines and it is the difference between "no legal assignment could
    have fed this sweep" and "the assignment I happened to try first did not". Deterministic:
    sweeps are visited in time order and each adjacency list is sorted, so the same log always
    produces the same pairing and therefore the same report.
    """
    kill_to_sweep = {}

    def augment(sweep, seen):
        for k in eligible[sweep]:
            if k in seen:
                continue
            seen.add(k)
            if k not in kill_to_sweep or augment(kill_to_sweep[k], seen):
                kill_to_sweep[k] = sweep
                return True
        return False

    for sweep in sorted(eligible):
        augment(sweep, set())
    return {sweep: k for k, sweep in kill_to_sweep.items()}


def correlate(session, npcs, pairs, skips, window, lead):
    """-> ([Finding], unclaimed kills)."""
    secondaries = collections.defaultdict(list)
    for sec, prim in pairs.items():
        secondaries[prim].append(sec)

    findings = []
    cands = {}
    blind = set()         # sweeps judged on TIMING only -- enemy rando, or no vanilla identity
    unjudged_now = {}     # sweep index -> reason, decided before any matching
    ordered = sorted(range(len(session.sets)), key=lambda i: session.sets[i][0])

    for i in ordered:
        _t, flag, _members, _lineno, _clock = session.sets[i]
        meta = npcs.get(flag)
        if meta is None:
            unjudged_now[i] = "trigger is not in sweep_trigger_npcs.tsv -- re-emit the table"
            continue
        cands[i] = candidates(flag, npcs, pairs, secondaries)
        # Identity is only usable when this is a vanilla stack AND we resolved the vanilla boss.
        if session.data_mod or not cands[i]:
            blind.add(i)

    kills = session.kills

    def eligible_kills(i, pool=None):
        t = session.sets[i][0]
        pool = range(len(kills)) if pool is None else pool
        return [j for j in pool
                if (i in blind or kills[j].npc in cands[i])
                and t - window <= kills[j].t <= t + lead]

    # PRIMARIES (and every ordinary trigger) first, through a maximum matching: they must consume.
    # ⭐ IDENTITY-MATCHED ONES GO FIRST and identity-blind ones take the leftovers, so a sweep with
    # no vanilla identity can never steal the kill that belongs to one we CAN name.
    # SECONDARIES last, free to share a kill the primary already took -- one fight, several bars.
    primaries = [i for i in ordered if i in cands and session.sets[i][1] not in pairs]
    named = [i for i in primaries if i not in blind]
    matched = _match({i: eligible_kills(i) for i in named})
    left = [j for j in range(len(kills)) if j not in set(matched.values())]
    matched.update(_match({i: eligible_kills(i, left) for i in primaries if i in blind}))
    for i in [i for i in ordered if i in cands and session.sets[i][1] in pairs]:
        elig = eligible_kills(i)
        if elig:
            matched[i] = max(elig, key=lambda j: kills[j].t)

    claimed = {j for i, j in matched.items() if session.sets[i][1] not in pairs}

    # A burst of same-second SETs of which NOT ONE matched is a save/character swap replaying an
    # earlier save's dead bosses -- `sweep_watch` is not reset by a character load -- not N defects.
    by_clock = collections.defaultdict(list)
    for i in ordered:
        if i in cands:
            by_clock[session.sets[i][0]].append(i)
    burst = {i for t, group in by_clock.items() if len(group) >= BURST_MIN
             and not any(g in matched for g in group) for i in group}

    for i in ordered:
        t, flag, members, lineno, clock = session.sets[i]
        meta = npcs.get(flag, {})
        if i in unjudged_now:
            findings.append(Finding("UNJUDGED", session, flag, members, clock, lineno,
                                    unjudged_now[i]))
            continue
        if i in matched:
            k = kills[matched[i]]
            detail = "BOSS DOWN npc_param %d at %s (%+ds, line %d)" % (k.npc, k.clock, k.t - t,
                                                                       k.lineno)
            if i in blind:
                detail += (" ⚠ IDENTITY-BLIND (%s): matched on timing alone, so this says a boss "
                           "died here, not that it was THIS boss"
                           % (session.data_mod if session.data_mod
                              else "no vanilla identity for this trigger"))
            if flag in pairs:
                detail += " [suppressed head -- kill reported by primary %d]" % pairs[flag]
            findings.append(Finding("clean", session, flag, members, clock, lineno, detail))
            continue

        # Unmatched. Everything below is an EXCUSE, checked before an accusation is written.
        if not session.censused:
            excuse = ("this session emitted no sweep-watch census, which a real one always does "
                      "first -- the log was rotated or truncated and the baseline is unknown")
        elif session.probe_silenced:
            excuse = "the probe was SILENCED in this session (ER_BOSSFIGHT_PROBE=0)"
        elif session.fight_lines == 0:
            excuse = ("no boss-fight lines in this session at all -- uninstrumented (probe off, or "
                      "the kill belongs to an earlier launch in this appended file)")
        else:
            amb = [e for e in session.ambiguous
                   if (i in blind or e.npc in cands[i]) and t - window <= e.t <= t + lead]
            if amb:
                excuse = ("a fight of this boss's family ended at %s but the client could not "
                          "classify it (outcome=%s%s) -- a kill under that condition never prints "
                          "BOSS DOWN" % (amb[0].clock, amb[0].outcome,
                                         ", " + INSTRUMENT_FAULT if amb[0].fault else ""))
            elif i in burst:
                excuse = ("one of %d trigger(s) that flipped in the same poll with no kill near any "
                          "of them -- the shape of a save/character load replaying flags, not of %d "
                          "broken sweeps" % (len(by_clock[t]), len(by_clock[t])))
            else:
                excuse = None
        if excuse:
            findings.append(Finding("UNJUDGED", session, flag, members, clock, lineno, excuse))
            continue

        near = sorted((k for k in kills if i in blind or k.npc in cands[i]),
                      key=lambda k: abs(k.t - t))
        who = ("ANY boss (identity-blind: %s)"
               % (session.data_mod if session.data_mod else "no vanilla identity for this trigger")
               if i in blind else "npc_param %s" % (sorted(cands[i]),))
        if near:
            detail = ("no BOSS DOWN free to claim in [-%ds,+%ds]; nearest kill matching %s was at "
                      "%s (%+ds) and is accounted for by another sweep"
                      % (window, lead, who, near[0].clock, near[0].t - t))
        else:
            detail = ("no BOSS DOWN matching %s anywhere in the session (%d boss-fight line(s) "
                      "present)" % (who, session.fight_lines))
        if flag in skips:
            detail += " 🛑 and this trigger is in contract.sweep_slot_skips: %s" % skips[flag]
        findings.append(Finding("FIRED WITHOUT A KILL", session, flag, members, clock, lineno,
                                detail))

    for flag, members, lineno in session.census_set:
        findings.append(Finding("UNJUDGED", session, flag, members, "census", lineno,
                                "already SET at the census -- this session never observed it fire"))
    for flag, lineno in session.new_group_set:
        findings.append(Finding("UNJUDGED", session, flag, 0, "new group", lineno,
                                "group arrived already SET (reconnect / config reload)"))

    # Informational, and deliberately not a failure: a kill nothing claimed. Expected for a boss
    # whose sweep is off in this seed, for a suppressed head, and for a re-kill on NG+.
    unclaimed = [k for j, k in enumerate(kills) if j not in claimed]
    # Report in LOG order, not adjudication order: a reader is holding the log open beside this.
    findings.sort(key=lambda f: f.lineno)
    return findings, unclaimed


# ---------------------------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------------------------
def _expand(patterns):
    paths, seen = [], set()
    for pat in patterns:
        for p in sorted(glob.glob(pat)) or [pat]:
            real = os.path.abspath(p)
            if real in seen:
                continue
            seen.add(real)
            if not os.path.exists(p):
                raise CannotRun("no such log: %s" % p)
            if os.path.isdir(p):
                raise CannotRun("%s is a directory; pass log FILES (a glob is fine)" % p)
            paths.append(p)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", help="client logs (log/archipelago-YYYY-MM-DD.log); globs ok")
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                    help="seconds a kill may PRECEDE the sweep (default %d; bobler's legitimate "
                         "Scadutree gap was 165s)" % DEFAULT_WINDOW)
    ap.add_argument("--lead", type=int, default=DEFAULT_LEAD,
                    help="seconds a kill may FOLLOW the sweep (default %d; the END line lands after "
                         "the death cam)" % DEFAULT_LEAD)
    ap.add_argument("--verbose", action="store_true", help="print the clean sweeps too")
    ap.add_argument("--unclaimed", action="store_true",
                    help="print kills no sweep claimed (informational, never a failure)")
    args = ap.parse_args(argv)

    try:
        paths = _expand(args.logs)
        npcs = load_trigger_npcs()
    except CannotRun as exc:
        print(exc, file=sys.stderr)
        return EXIT_CANNOT_RUN
    pairs = load_arena_pairs()
    skips = load_skips()

    totals = collections.Counter()
    flagged, unjudged, clean, unclaimed_all, modded = [], [], [], [], []
    for path in paths:
        for session in parse_log(path):
            if session.data_mod:
                modded.append((session, session.data_mod))
            findings, unclaimed = correlate(session, npcs, pairs, skips, args.window, args.lead)
            unclaimed_all.extend(unclaimed)
            for f in findings:
                totals[f.verdict] += 1
                (flagged if f.verdict == "FIRED WITHOUT A KILL"
                 else unjudged if f.verdict == "UNJUDGED" else clean).append(f)

    def show(f):
        meta = npcs.get(f.flag, {})
        return "  %s  flag %d  %s (%s%s)  %d member(s)  line %d\n      %s" % (
            f.clock, f.flag, meta.get("name") or "?", meta.get("class", "?"),
            ", " + meta["tile"] if meta.get("tile") else "", f.members, f.lineno, f.detail)

    print("sweep/kill correlation -- %d log(s), window -%ds/+%ds" % (len(paths), args.window, args.lead))
    print("  clean %d | FIRED WITHOUT A KILL %d | UNJUDGED %d" % (
        totals["clean"], totals["FIRED WITHOUT A KILL"], totals["UNJUDGED"]))

    if modded:
        print("\n⚠ NON-VANILLA session(s) -- judged IDENTITY-BLIND (timing only). The probe prints "
              "whoever is\n  actually in the arena; this table is vanilla. Sweeps stay arena-keyed, "
              "so the flags are fine.")
        for session, what in modded:
            print("  %s: %s" % (session.label, what))

    if flagged:
        print("\n🛑 FIRED WITHOUT A KILL -- a sweep paid out and nothing died for it (#713 mode 1)")
        for f in flagged:
            print("%s\n%s" % (f.session.label, show(f)))

    if unjudged:
        print("\nUNJUDGED -- not a pass and not a failure; nothing here can be adjudicated")
        for f in unjudged:
            print(show(f))

    if clean and args.verbose:
        print("\nclean")
        for f in clean:
            print(show(f))

    if args.unclaimed and unclaimed_all:
        print("\nkills no sweep claimed (informational -- sweep off in this seed, suppressed head, "
              "or an NG+ re-kill)")
        for k in unclaimed_all:
            print("  %s  npc_param %d  line %d" % (k.clock, k.npc, k.lineno))

    return EXIT_FINDINGS if flagged else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
