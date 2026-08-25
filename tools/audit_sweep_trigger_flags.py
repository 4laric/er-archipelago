#!/usr/bin/env python3
r"""audit_sweep_trigger_flags.py -- #987: is every sweep trigger key ever SET by the EMEVD corpus?

WHY THIS EXISTS. A sweep trigger is a flag the CLIENT POLLS (`sweep_watch`). #1015 fixed Dryleaf
Dane, whose two triggers keyed on ENTITY ids the EMEVD sets as flags nowhere, and the natural next
question was "how many more are there?". This is the re-runnable answer, and running it is the
only way to state the completeness claim honestly.

🛑🛑 READ THIS BEFORE YOU "FIX" ANYTHING IT PRINTS. **NEVER-SET IS NOT A DEFECT CLASS.** The
absence of a `Set[Networkconnected]EventFlagID(<key>, ...)` in the corpus does NOT mean the client
never sees the flag fire, and TWO CAPTURED PLAYER LOGS in this repo say so outright:

    greenfield/eldenring/tests/fixtures/sweep_kill_bobler_scadutree.log
        12:58:20  sweep-watch: census -- 1 group(s), 0 already set: [2050480810(49)]
        13:03:47  sweep-watch: trigger flag 2050480810 -> SET (49 member(s) in its group)
        13:03:47  Received item: Boss sweep (Scadu Altus)
    greenfield/eldenring/tests/fixtures/sweep_kill_suppressed_head.log
        14:10:05  sweep-watch: trigger flag 31220801 -> SET (12 member(s) in its group)
        14:10:05  sweep-watch: trigger flag 31220802 -> SET (12 member(s) in its group)

`2050480810` (a Scadutree Avatar referred-damage proxy) and `31220801`/`31220802` (the Spiritcaller
Cave duo partners) are all in this audit's NEVER-SET list, and all three were OBSERVED FIRING and
PAYING OUT. Whatever writes them is not an EMEVD flag instruction -- the same unwritten mechanism
every entity-keyed interior sweep has always rested on, and the premise `flag_equals_id` encodes.
So this audit measures ONE necessary-looking property and it is NOT the defect predicate:

    SUFFICIENT IS NOT NECESSARY. A key the corpus sets certainly fires. A key it does not set may
    still fire, and 3 of the 20 are on record doing it.

Use it as a LEAD GENERATOR against in-game evidence (a player report that a sweep did not pay), the
way #987 was actually diagnosed -- never as a licence to re-key a working trigger. Re-keying is not
free: it merges entries, moves the sweep-ownership digest and can change a trigger's `MajorBoss`
membership (measured 2026-08-24: merging the three Avatar proxies onto 2050480800 moved the
ownership digest 991951420a8525a4 -> 5847d65898b36345, re-owned 33 member links, and took
MAJOR_SWEEP_TRIGGERS 40 -> 41). That is a lot of movement to buy for a sweep the logs show working.

METHOD (so the completeness claim can be re-run and disputed). Every key of
`greenfield/eldenring/boss_healthbars.py` -- which is exactly the key space of
`boss_sweeps.DUNGEON_SWEEPS` plus the members-less entries -- is classified against every
`elden_ring_artifacts/event/*.emevd.dcx.js`:

  direct     a literal `Set[Networkconnected]EventFlag[ID](<key>, ...)` anywhere in the corpus.
  param      the parameterized-init shape: an `$Event` whose body sets a PARAMETER as a flag, and
             some `$Initialize[Common]Event` passes the key into that parameter slot. This is the
             shape that carries the flag==entity no-ops, and it is why a naive literal grep
             undercounts by 79.
  batch      inside the range of a `BatchSet[Networkconnected]EventFlags(lo, hi, ON)` or
             `RandomlySetEventFlagInRange(lo, hi, ON)` -- literal ranges AND parameterized ones
             resolved through their `$Initialize[Common]Event` args, because a range setter that
             takes its bounds as parameters is exactly as capable of covering a key. Only ON is
             counted: an OFF batch clears, it cannot make a trigger fire. Measured 2026-08-24: 78
             parameterized batch call sites set OFF and 9 set ON, spread over 6 events. Four of
             those events are initialised somewhere in the corpus and resolve to four literal
             ranges -- (12092855, 12092857), (1039440350, 1039440351), (1045390350, 1045390351),
             (2048429212, 2048429216), all randomised item-lot bands and none containing a trigger
             key. The other two (1044363701 in m60_44_36_00/_10, 1044373701 in m60_44_37_00/_10)
             are DEFINED AND NEVER INITIALISED anywhere in the corpus, so they set nothing at all.
  arena      a `greenfield/game_areas.tsv` row with `flag_equals_id=yes` on that defeat flag.
  NEVER-SET  none of the above. **A lead, not a bug** -- see above.

🛑 AN ID THAT RESOLVES IS NOT A TABLE MATCH. Only the FLAG ARGUMENT POSITION counts. Every one of
these keys appears in the corpus somewhere as an ENTITY (CharacterDead, DisplayBossHealthBar,
CreateReferredDamagePair, ...) and none of those readings is evidence about a flag.

Run:  python tools/gen_inputs.py --extract elden_ring_artifacts
      python tools/audit_sweep_trigger_flags.py            # the census
      python tools/audit_sweep_trigger_flags.py --never    # just the NEVER-SET leads
"""
import argparse
import csv
import glob
import importlib.util
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.dirname(HERE)
EVT = os.path.join(REPO, "elden_ring_artifacts", "event")
GF = os.path.join(REPO, "greenfield")

_EV_RE = re.compile(r"\$Event\((\d+),\s*\w+,\s*function\(([^)]*)\)\s*\{", re.S)
_INIT_RE = re.compile(r"\$Initialize(?:Common)?Event\(\s*\d+\s*,\s*(\d+)\s*,\s*([^)]*)\)")
_SETF_RE = re.compile(r"Set(?:Networkconnected)?EventFlag(?:ID)?\(\s*([\w\-]+)\s*,")
_BATCH_LIT = re.compile(r"(?:BatchSet(?:Networkconnected)?EventFlags"
                        r"|RandomlySetEventFlagInRange)\(\s*(\d+)\s*,\s*(\d+)\s*,?\s*(\w*)")
_BATCH_PARAM = re.compile(r"(?:BatchSet(?:Networkconnected)?EventFlags"
                          r"|RandomlySetEventFlagInRange)\(\s*([A-Za-z]\w*)\s*,\s*(\w+)\s*,\s*(\w+)")


def _events(txt):
    """(event id, [param names], body) for every $Event in a DarkScript emevd .js."""
    idx = [(m.group(1), m.group(2), m.start()) for m in _EV_RE.finditer(txt)]
    for i, (eid, params, start) in enumerate(idx):
        end = idx[i + 1][2] if i + 1 < len(idx) else len(txt)
        yield int(eid), [p.strip() for p in params.split(",")] if params.strip() else [], txt[start:end]


def scan():
    """-> (direct literals, {event: {flag param idx}}, literal ranges, texts, param-batch states)."""
    direct, setter_params, batches, texts, pbatch = set(), {}, [], {}, Counter()
    batch_params = {}    # event id -> {(lo param idx, hi param idx)} for ON range setters
    files = sorted(glob.glob(os.path.join(EVT, "*.emevd.dcx.js")))
    if not files:
        sys.exit("FATAL: %s is empty -- run `python tools/gen_inputs.py --extract "
                 "elden_ring_artifacts` first." % EVT)
    for f in files:
        txt = open(f, encoding="utf-8", errors="replace").read()
        texts[os.path.basename(f)] = txt
        for m in _BATCH_LIT.finditer(txt):
            if m.group(3) != "OFF":
                batches.append((int(m.group(1)), int(m.group(2))))
        for m in _BATCH_PARAM.finditer(txt):
            pbatch[m.group(3)] += 1          # ON / OFF -- an OFF batch can never make a key fire
        for eid, pl, body in _events(txt):
            for m in _BATCH_PARAM.finditer(body):
                lo, hi, st = m.group(1), m.group(2), m.group(3)
                if st == "ON" and pl and lo in pl and hi in pl:
                    batch_params.setdefault(eid, set()).add((pl.index(lo), pl.index(hi)))
            for m in _SETF_RE.finditer(body):
                a = m.group(1)
                if a.isdigit():
                    direct.add(int(a))
                elif pl and a in pl:
                    setter_params.setdefault(eid, set()).add(pl.index(a))
    return direct, setter_params, batches, texts, pbatch, batch_params


def param_set(setter_params, batch_params, texts):
    """Resolve the parameterized shapes through their init calls.

    -> (ids passed into a flag-argument slot of a setter event,
        [(lo, hi)] ranges an ON range-setter is actually initialised with)."""
    out, ranges = set(), []
    for txt in texts.values():
        for m in _INIT_RE.finditer(txt):
            eid = int(m.group(1))
            args = [a.strip() for a in m.group(2).split(",")]
            for i in setter_params.get(eid, ()):
                if i < len(args) and args[i].isdigit():
                    out.add(int(args[i]))
            for lo, hi in batch_params.get(eid, ()):
                if lo < len(args) and hi < len(args) and args[lo].isdigit() and args[hi].isdigit():
                    ranges.append((int(args[lo]), int(args[hi])))
    return out, ranges


def arena_flags():
    """Defeat flags the arena machinery grants (game_areas.tsv, flag_equals_id=yes)."""
    path = os.path.join(GF, "game_areas.tsv")
    rows = [ln for ln in open(path, encoding="utf-8") if not ln.startswith("#")]
    return {int(r["defeat_flag"]) for r in csv.DictReader(rows, delimiter="\t")
            if (r.get("flag_equals_id") or "").strip() == "yes" and r["defeat_flag"].isdigit()}


def _load(name):
    """A generated pure-data module WITHOUT the eldenring package (which needs Archipelago)."""
    spec = importlib.util.spec_from_file_location("_a_" + name, os.path.join(GF, "eldenring", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--never", action="store_true", help="print only the NEVER-SET leads")
    args = ap.parse_args()
    bars = _load("boss_healthbars").BOSS_HEALTHBARS
    sweeps = _load("boss_sweeps").DUNGEON_SWEEPS
    direct, sp, batches, texts, pbatch, bp = scan()
    pset, pranges = param_set(sp, bp, texts)
    batches += pranges
    arenas = arena_flags()

    def classify(k):
        if k in direct:
            return "direct"
        if k in pset:
            return "param"
        if any(lo <= k <= hi for lo, hi in batches):
            return "batch"
        if k in arenas:
            return "arena"
        return "NEVER-SET"

    counts, never = Counter(), []
    for k, b in sorted(bars.items()):
        c = classify(k)
        counts[c] += 1
        if c == "NEVER-SET":
            never.append((k, b, len(sweeps.get(k, ()))))
    if not args.never:
        print("corpus: %d emevd file(s); parameterized batch setters by state %s; "
              "%d ON range(s) resolved to literal bounds" % (len(texts), dict(pbatch), len(pranges)))
        print("trigger keys: %d (%d carry a sweep) | %s"
              % (len(bars), sum(1 for k in bars if k in sweeps), dict(counts)))
    print("NEVER-SET in the EMEVD corpus -- LEADS, NOT BUGS (%d); see this file's docstring:"
          % len(never))
    for k, b, n in never:
        print("  %-12d %-12s %-9s %-34s members=%d" % (k, b[1], b[2], b[3] or "?", n))


if __name__ == "__main__":
    main()
