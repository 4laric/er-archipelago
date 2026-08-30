#!/usr/bin/env python3
r"""datamine_achievement_bosses.py -- the game's OWN roster of major bosses.

WHY THIS EXISTS (#737). `MajorBoss` is the class the default progression surface confines this
world's own progression to, and its membership was a HAND-CURATED list -- `MAJOR_BOSS_EXTRAS` in
gen_data.py, a set of "hand-picked field/evergaol/dragon bosses". Joined against matt's published
roster it was wrong in both directions: it carried bosses nobody would call major and missed ten that
everybody would (Margit, Red Wolf of Radagon, Royal Knight Loretta, Godskin Duo, Godskin Noble,
Commander Niall, Mimic Tear, Valiant Gargoyles, Elemer of the Briar, Dragonkin Soldier of Nokstella).

Matt's UI calls his set "Major bosses -- 30 checks, INCLUDING ALL ACHIEVEMENT BOSSES", and that
phrase is the derivation. We do not need his list: the game ships its own, and it is not a judgement
call. common.emevd registers one trophy event and every achievement is a call site of it:

    // トロフィー取得_XX -- Trophy acquisition_XX
    $Event(9300, Restart, function(achievementId, eventFlagId, timeSeconds) {
        EndIf(ThisEventSlot());
        WaitFor(PlayerIsInOwnWorld() && EventFlag(eventFlagId));
        WaitFixedTimeSeconds(timeSeconds);
        AwardAchievement(achievementId);
    });

    $InitializeEvent(4,  9300,  4, 10000800, 0);     <- achievement 4 fires on Godrick's defeat flag
    $InitializeEvent(26, 9300, 26, 14000850, 0);     <- achievement 26, Red Wolf of Radagon
    ...

So "is this boss an achievement boss" is a JOIN, not an opinion: the achievement's `eventFlagId` is
the boss's defeat flag, and BOSS_HEALTHBARS already keys on exactly that. 32 call sites, 29 of them
on a boss defeat flag.

🛑 TWO CLASSIFIER SOURCES, BECAUSE ONE OF THEM IS WRONG ABOUT THE FIRE GIANT. Achievement 21 hangs
off `1052520800`, which the healthbar capture does not carry -- so a healthbars-only classifier
writes "collection" beside the Fire Giant, which is not a gap, it is a confident false statement in a
committed table. `BOSS_REWARD_DEFEAT` knows that flag, and nothing but a boss death produces a boss
reward flag. The classifier is the union of the two and every row records WHICH one answered.

🛑 WHAT THIS TOOL DOES NOT DECIDE. It emits the ROSTER, not the tag. Turning a defeat flag into the
CHECK that death grants is `boss_reward_lots.BOSS_REWARD_DEFEAT`'s job and gen_data's join; keeping
that separate is deliberate, because "which bosses are major" and "which check does a boss pay" are
two questions and this project has been bitten before by a function that answered both.

🛑 EVERY ROW IS ACCOUNTED FOR, INCLUDING THE ONES THAT ARE NOT BOSSES. Three call sites hang off a
flag NEITHER capture knows, and they are not misses -- they are the COLLECTION achievements (all
legendary armaments / sorceries / incantations), which fire on a counter flag rather than on a death.
They are emitted with `kind=collection` rather than dropped, because a row that silently vanishes and
a row that never existed look identical in a green run, and the next person to widen this scan needs
to see that the classifier ran on them and said no.

The ENDING achievements (1, 2, 3 -- Elden Lord, Age of the Stars, Lord of Frenzied Flame) are not
here at all: m11_71 and m19_00 call `AwardAchievement` INLINE rather than through event 9300, so
they have no eventFlagId argument to join on. They are not bosses either, so nothing is lost; it is
recorded so that "why is this 32 and not 35" has an answer that is not a shrug.

Emits greenfield/achievement_bosses.tsv:

    achievement_id  defeat_flag  kind  source  map  boss_class  boss_name

    python3 tools/datamine_achievement_bosses.py           # regenerate
    python3 tools/datamine_achievement_bosses.py --check    # verify committed file is current
    python3 tools/datamine_achievement_bosses.py --list     # print, write nothing
"""
import argparse
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
COMMON = os.path.join(REPO, "elden_ring_artifacts", "event", "common.emevd.dcx.js")
OUT = os.path.join(REPO, "greenfield", "achievement_bosses.tsv")

# The trophy event. Its signature is (achievementId, eventFlagId, timeSeconds) and its body is a
# single AwardAchievement -- both re-verified below rather than assumed, so a future regulation that
# reshapes the event fails loudly instead of being parsed into nonsense.
TROPHY_EVENT = 9300
_SIG = ("achievementId", "eventFlagId", "timeSeconds")
MIN_ACHIEVEMENTS = 32
MIN_BOSS_ACHIEVEMENTS = 29

_DEF = re.compile(r"\$Event\(\s*%d\s*,\s*\w+\s*,\s*function\(([^)]*)\)\s*\{(.*?)\n\}\);"
                  % TROPHY_EVENT, re.S)
_INIT = re.compile(r"\$InitializeEvent\(\s*\d+\s*,\s*%d\s*,\s*(\d+)\s*,\s*(\d+)\s*,"
                   % TROPHY_EVENT)


def validate_census(rows):
    bosses = sum(r[2] == "boss" for r in rows)
    short = []
    if len(rows) < MIN_ACHIEVEMENTS:
        short.append("achievements=%d (floor %d)" % (len(rows), MIN_ACHIEVEMENTS))
    if bosses < MIN_BOSS_ACHIEVEMENTS:
        short.append("boss achievements=%d (floor %d)" % (bosses, MIN_BOSS_ACHIEVEMENTS))
    if short:
        raise SystemExit("datamine_achievement_bosses: REFUSED incomplete census: %s. Nothing "
                         "written." % ", ".join(short))


def _load(relpath, modname):
    p = os.path.join(REPO, "greenfield", "eldenring", relpath)
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location(modname, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _boss_flags():
    """The two independent answers to "is this flag a boss defeat flag", and BOTH are needed.

    🛑 BOSS_HEALTHBARS ALONE GETS THE FIRE GIANT WRONG. Achievement 21 hangs off `1052520800`, which
    is not in the healthbar capture -- so a healthbars-only classifier calls the Fire Giant a
    COLLECTION achievement, which is not a miss, it is a confident false statement written into a
    committed table. It is a boss, and the evidence is one table over: BOSS_REWARD_DEFEAT maps a
    reward flag to that defeat flag, which nothing but a boss death produces.

    So the classifier is the UNION, and the row records WHICH source answered. A `source` column is
    the difference between "we know this is a boss" and "one of our two captures happens to mention
    it", and the second is the honest claim for the rows only BOSS_REWARD_DEFEAT knows.

    Returns {flag: (source, map, boss_class, boss_name)}.
    """
    hb = _load("boss_healthbars.py", "_hb")
    if hb is None:
        sys.exit("datamine_achievement_bosses: greenfield/eldenring/boss_healthbars.py is missing -- "
                 "without it nearly every row would classify as 'collection' and the roster would "
                 "come out near-empty while reporting success. Run datamine_boss_healthbars.py.")
    rl = _load("boss_reward_lots.py", "_rl")
    if rl is None:
        sys.exit("datamine_achievement_bosses: greenfield/eldenring/boss_reward_lots.py is missing "
                 "-- it is the second half of the classifier (the Fire Giant is only in that one). "
                 "Run datamine_boss_reward_lots.py.")

    out = {}
    # BOSS_REWARD_DEFEAT is {reward_flag: defeat_flag}; the VALUES are the defeat flags.
    for defeat_flag in dict(rl.BOSS_REWARD_DEFEAT).values():
        out[defeat_flag] = ("reward_defeat", "", "", "")
    # Healthbars carry the map, class and name, so they win where both know the flag.
    for flag, info in dict(hb.BOSS_HEALTHBARS).items():
        out[flag] = ("healthbar", info[0], info[2], info[3])
    return out


def derive():
    if not os.path.isfile(COMMON):
        sys.exit("datamine_achievement_bosses: %s is absent -- this needs the artifacts (Windows "
                 "box / gen_inputs bundle). Refusing to emit an empty roster." % COMMON)
    src = open(COMMON, encoding="utf-8", errors="replace").read()

    # (1) The event must still BE the trophy event, with the signature we are about to read
    # positionally. A silent reshape here would re-key the whole roster off the wrong argument.
    m = _DEF.search(src)
    if not m:
        sys.exit("datamine_achievement_bosses: common.emevd has no $Event(%d) -- the trophy event "
                 "has moved or been renamed; find it before trusting anything downstream."
                 % TROPHY_EVENT)
    params = tuple(p.strip() for p in m.group(1).split(",") if p.strip())
    if params != _SIG:
        sys.exit("datamine_achievement_bosses: $Event(%d) signature is %r, expected %r -- the "
                 "argument ORDER is what this tool reads positionally, so a reshape must be looked "
                 "at, never guessed through." % (TROPHY_EVENT, params, _SIG))
    if "AwardAchievement" not in m.group(2):
        sys.exit("datamine_achievement_bosses: $Event(%d) no longer awards an achievement -- the "
                 "slot has been reused for something else." % TROPHY_EVENT)

    known = _boss_flags()
    rows = []
    for ach, flag in _INIT.findall(src):
        ach, flag = int(ach), int(flag)
        info = known.get(flag)
        if info:
            source, mp, cls, name = info
            rows.append((ach, flag, "boss", source, mp, cls, name))
        else:
            # NOT a miss -- see the module docstring. A collection achievement fires on a counter
            # flag, and saying so beats dropping the row.
            rows.append((ach, flag, "collection", "", "", "", ""))
    if not rows:
        sys.exit("datamine_achievement_bosses: found the trophy event but ZERO call sites -- an "
                 "empty result is a failure, not a clean run.")
    rows.sort()
    validate_census(rows)
    return rows


HEADER = """\
# AUTO-GENERATED by tools/datamine_achievement_bosses.py -- DO NOT EDIT, re-emit.
#
# THE GAME'S OWN MAJOR-BOSS ROSTER. Every call site of common.emevd's $Event({ev}) -- the trophy
# event, `AwardAchievement(achievementId)` gated on `EventFlag(eventFlagId)` -- joined to
# BOSS_HEALTHBARS on that same eventFlagId, which for a boss achievement IS the defeat flag.
#
# kind=boss        the flag is a boss defeat flag; this achievement is "kill that boss"
# kind=collection  neither capture knows the flag. NOT a miss: these are the all-legendary-armaments
#                  / -sorceries / -incantations achievements, which fire on a counter flag. Kept in
#                  the file so the classifier's negative answers are visible rather than absent.
#
# source=healthbar      BOSS_HEALTHBARS knows the flag -- map, class and name come from it
# source=reward_defeat  ONLY BOSS_REWARD_DEFEAT knows it. Still a boss (nothing else produces a boss
#                       reward flag) but the healthbar capture missed it, so there is no name to
#                       print. The Fire Giant is here, and a healthbars-only classifier called him a
#                       collection achievement -- which is why there are two sources and a column
#                       saying which one answered.
#
# The three ENDING achievements are absent by construction: m11_71 and m19_00 call
# AwardAchievement INLINE, with no eventFlagId to join on. They are not bosses either.
#
# This file is the ROSTER, not the tag. gen_data turns a defeat flag into the CHECK that death
# grants via boss_reward_lots.BOSS_REWARD_DEFEAT, and asserts that every kind=boss row either
# resolves to exactly one check or is named in its unresolved ledger.
#
achievement_id\tdefeat_flag\tkind\tsource\tmap\tboss_class\tboss_name
"""


def render(rows):
    out = [HEADER.format(ev=TROPHY_EVENT)]
    for r in rows:
        out.append("\t".join(str(x) for x in r))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--check", action="store_true", help="verify the committed file is current")
    ap.add_argument("--list", action="store_true", help="print the roster, write nothing")
    a = ap.parse_args()

    rows = derive()
    bosses = [r for r in rows if r[2] == "boss"]
    text = render(rows)

    if a.list:
        sys.stdout.write(text)
        return 0

    if a.check:
        if not os.path.isfile(OUT):
            print("[STALE] %s does not exist" % OUT)
            return 1
        if open(OUT, encoding="utf-8", newline="").read() != text:
            print("[STALE] greenfield/achievement_bosses.tsv differs from a fresh emit\n"
                  "        fix: python3 tools/datamine_achievement_bosses.py")
            return 1
        print("[ok] achievement roster is current (%d achievement(s), %d on a boss defeat flag)"
              % (len(rows), len(bosses)))
        return 0

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("[ok] wrote greenfield/achievement_bosses.tsv -- %d achievement(s), %d on a boss defeat "
          "flag, %d collection" % (len(rows), len(bosses), len(rows) - len(bosses)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
