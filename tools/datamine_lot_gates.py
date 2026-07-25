#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_lot_gates.py -- which EVENT FLAG must already be set before a CHECK can exist.

WHY (Alaric, 2026-07-25). `f67050` -- Nomadic Warrior's Cookbook [7], the one Roderika leaves behind
at Stormhill Shack -- is regioned **Limgrave**, and Limgrave is CORRECT: that is where the player
physically stands to pick it up, and the region drives the client's kick geometry. But the pickup does
not exist until you have rested at a grace in **Liurnia**. So AP believes it is an early Limgrave
check and will happily place progression on it in a seed where Liurnia is locked or late.

That is not a misregion. It is a missing ACCESS RULE, and it is a different bug from every region
defect chased so far: the region is derived, correct, and still asserts a reachability we do not have.
The same shape as the HUB-quarantine mistake CONTRIBUTING already documents ("it asserts a
reachability we do not have. Unwinnable seed"), arriving from the opposite direction.

My guess is this is a POPULATION, not a one-off -- NPC-departure pickups, questline drops and
post-event spawns all have it. This tool is how we find out instead of guessing.

OUTPUT: greenfield/lot_gates.tsv -- check_flag, gate_flag, sense, event_id, source, evidence
        (`sense` 1 = the gate flag must be SET, 0 = must be CLEAR.)
        gen_data/core.py can then join gate_flag -> its own region and, where that differs from the
        check's region, emit a real `can_reach` rule instead of a false early claim.

INPUT: ESDLang/DarkScript3-decompiled EMEVD JS, `elden_ring_artifacts/event/*.emevd.dcx.js`.
       Windows-only artifacts -- this cannot run in the agent sandbox.

--------------------------------------------------------------------------------------------------
⚠️ READ THIS BEFORE TRUSTING ANY OUTPUT. The EMEVD instruction VOCABULARY is not guessed here, and it
must not be. I wrote this without the artifacts in front of me, so the patterns below are CANDIDATES
derived from how tools/datamine_boss_drops.py parses the same corpus -- not from having seen a flag
test. A parser that invents instruction names produces a confident, complete, WRONG table, which is
this repo's signature failure.

So the tool has two modes and the first one is not optional:

    python tools/datamine_lot_gates.py --vocab     # LOOK. Emits nothing. Prints the call-name
                                                   # histogram + real sample lines.
    python tools/datamine_lot_gates.py --emit      # only once --vocab has confirmed the names

`--vocab` output is the thing to paste back if the names do not match: FLAG_TEST_RE / AWARD_RE below
are then corrected against the real corpus, not against my recollection. `--emit` hard-refuses on a
degenerate parse (no events, no flag tests, or an implausible hit rate) rather than writing a table
that looks fine and means nothing.
--------------------------------------------------------------------------------------------------
"""
import argparse
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVT = os.path.join(ROOT, "elden_ring_artifacts", "event")
GF = os.path.join(ROOT, "greenfield")
OUT = os.path.join(GF, "lot_gates.tsv")

# One decompiled event: `$Event(<id>, <restart behaviour>, function(<params>) {`
EVENT_RE = re.compile(r"\$Event\((\d+),\s*\w+,\s*function\(([^)]*)\)\s*\{")

# CANDIDATE: a condition on an event flag. DarkScript3 emits the flag id as the last integer arg and
# the ON/OFF state as a bare word. Both orders are accepted because I have not seen the corpus.
FLAG_TEST_RE = re.compile(
    r"\b(If\w*EventFlag\w*|IsEventFlag\w*)\s*\(([^)]*)\)", re.I)
# CANDIDATE: the award/spawn side. AwardItemLot is certain (boss_drops relies on it); the
# treasure/asset enables are candidates.
AWARD_RE = re.compile(
    r"\b(AwardItemLot|Enable\w*Treasure|Enable\w*Asset|Enable\w*Obj\w*)\s*\(([^)]*)\)", re.I)
# ON/OFF -> sense. Anything else is reported, never assumed.
ON_WORDS = {"on", "true", "1", "enabled"}
OFF_WORDS = {"off", "false", "0", "disabled"}

_INT_RE = re.compile(r"-?\d+")


def _sources():
    files = sorted(glob.glob(os.path.join(EVT, "*.emevd.dcx.js")))
    if not files:
        sys.exit("FATAL: no *.emevd.dcx.js under %s -- these are Windows-only artifacts. "
                 "Nothing scanned, nothing written." % EVT)
    return files


def _events(text):
    """[(event_id, body)] for one file."""
    hits = [(int(m.group(1)), m.start()) for m in EVENT_RE.finditer(text)]
    out = []
    for i, (eid, start) in enumerate(hits):
        end = hits[i + 1][1] if i + 1 < len(hits) else len(text)
        out.append((eid, text[start:end]))
    return out


def vocab():
    """LOOK BEFORE PARSING. Prints what the corpus actually contains."""
    files = _sources()
    names = collections.Counter()
    ev_total = 0
    samples = collections.defaultdict(list)
    call = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
    for path in files:
        text = open(path, encoding="utf-8", errors="replace").read()
        ev_total += len(EVENT_RE.findall(text))
        for m in call.finditer(text):
            names[m.group(1)] += 1
        for line in text.splitlines():
            low = line.lower()
            for key in ("eventflag", "treasure", "awarditemlot", "asset"):
                if key in low and len(samples[key]) < 6:
                    samples[key].append(line.strip()[:150])
    print("files=%d  events=%d  distinct call names=%d" % (len(files), ev_total, len(names)))
    print("\n== call names mentioning FLAG / TREASURE / AWARD / ASSET (count, name) ==")
    for name, n in names.most_common():
        if re.search(r"flag|treasure|award|asset|obj", name, re.I):
            print("   %8d  %s" % (n, name))
    print("\n== sample lines (the ground truth for the regexes) ==")
    for key in ("eventflag", "treasure", "awarditemlot", "asset"):
        print("  --- %s" % key)
        for s in samples[key] or ["   (none found -- the vocabulary guess is WRONG for this one)"]:
            print("     " + s)
    print("\nIf FLAG_TEST_RE / AWARD_RE do not match the names above, FIX THEM before --emit.")
    return 0


def _ints(args):
    return [int(x) for x in _INT_RE.findall(args)]


def _sense(args):
    toks = [t.strip().strip("'\"").lower() for t in args.split(",")]
    for t in toks:
        base = t.split(".")[-1]
        if base in ON_WORDS:
            return 1
        if base in OFF_WORDS:
            return 0
    return None                                   # UNKNOWN -> reported, never defaulted


def emit(dry):
    files = _sources()
    check_flags = _check_flags()
    rows, unknown_sense, ev_total, tested = [], 0, 0, 0
    for path in files:
        src = os.path.basename(path)
        text = open(path, encoding="utf-8", errors="replace").read()
        for eid, body in _events(text):
            ev_total += 1
            gates = []
            for m in FLAG_TEST_RE.finditer(body):
                tested += 1
                ints = _ints(m.group(2))
                if not ints:
                    continue
                sense = _sense(m.group(2))
                if sense is None:
                    unknown_sense += 1
                    continue
                gates.append((ints[-1], sense, m.group(0)[:110]))
            if not gates:
                continue
            # every check flag this event AWARDS or ENABLES
            awarded = set()
            for m in AWARD_RE.finditer(body):
                awarded.update(i for i in _ints(m.group(2)) if i in check_flags)
            # ... plus check flags named anywhere in the body, which catches the treasure-entity
            # indirection this parser deliberately does NOT try to resolve (that needs the MSB).
            for i in _ints(body):
                if i in check_flags:
                    awarded.add(i)
            for cf in sorted(awarded):
                for gf, sense, ev in gates:
                    if gf == cf:
                        continue                  # a check's own acquisition flag is not its gate
                    rows.append((cf, gf, sense, eid, src, ev.replace("\t", " ")))
    print("scanned %d file(s), %d event(s), %d flag test(s); %d unresolved sense; %d raw pair(s)"
          % (len(files), ev_total, tested, unknown_sense, len(rows)))
    # REFUSE on a degenerate parse. Each of these means the vocabulary is wrong, and a table written
    # anyway would be confidently empty or confidently enormous -- both worse than no table.
    if ev_total < 100:
        sys.exit("FATAL: only %d events parsed -- EVENT_RE does not match this corpus. Run --vocab."
                 % ev_total)
    if tested == 0:
        sys.exit("FATAL: zero flag tests found -- FLAG_TEST_RE matches nothing. Run --vocab.")
    if not rows:
        sys.exit("FATAL: zero gated checks found. Either no check flag shares an event with a flag "
                 "test (implausible) or the parse is wrong. Run --vocab.")
    if len(rows) > 20000:
        sys.exit("FATAL: %d pairs -- the body-wide integer sweep is matching everything. Tighten "
                 "AWARD_RE before trusting this." % len(rows))
    rows.sort()
    if dry:
        for r in rows[:40]:
            print("   check %-10s gated on %-10s sense=%s  event %-12s %s" % r[:5])
        print("   ... %d row(s) total (dry run, nothing written)" % len(rows))
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_lot_gates.py -- DO NOT EDIT.\n")
        fh.write("# check_flag exists only once gate_flag is in state `sense` (1 set / 0 clear).\n")
        fh.write("# CANDIDATE PAIRS, not conclusions: co-occurrence in one event is evidence, not\n")
        fh.write("# proof. Triage before wiring any of it into logic -- a false gate is an\n")
        fh.write("# unwinnable seed, and a false NON-gate is the bug this exists to find.\n")
        fh.write("check_flag\tgate_flag\tsense\tevent_id\tsource\tevidence\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    print("wrote %s: %d candidate gate pair(s) over %d distinct check flag(s)"
          % (OUT, len(rows), len({r[0] for r in rows})))
    return 0


def _check_flags():
    """Every flag greenfield calls a CHECK (region_map.csv). The gate search is scoped to these:
    an event flag that is not a check is not something we can misrepresent the reachability of."""
    import csv
    path = os.path.join(GF, "region_map.csv")
    if not os.path.isfile(path):
        sys.exit("FATAL: %s missing -- the check set is what scopes this scan." % path)
    with open(path, encoding="utf-8", newline="") as fh:
        out = {int(r["flag"]) for r in csv.DictReader(fh)
               if (r.get("flag") or "").strip().lstrip("-").isdigit()}
    if len(out) < 1000:
        sys.exit("FATAL: only %d check flags parsed from region_map.csv -- refusing to scan against "
                 "a truncated check set." % len(out))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vocab", action="store_true",
                    help="LOOK FIRST: print the EMEVD call-name histogram + sample lines. No output.")
    ap.add_argument("--emit", action="store_true", help="write greenfield/lot_gates.tsv")
    ap.add_argument("--dry", action="store_true", help="parse and print, write nothing")
    args = ap.parse_args(argv)
    if args.vocab:
        return vocab()
    if args.emit or args.dry:
        return emit(dry=args.dry)
    ap.print_help()
    print("\nStart with --vocab. The instruction names in this file are CANDIDATES; see the header.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
