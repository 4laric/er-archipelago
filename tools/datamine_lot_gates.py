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
⚠️ THE VOCABULARY IS MEASURED, NOT GUESSED -- and the first guess was WRONG.

v1 of this file looked for `If*EventFlag*` calls. `--vocab` on the real corpus (Alaric, 2026-07-25:
589 files, 4893 events) found ZERO of those. The predicate is a bare `EventFlag(<id>)` used as an
expression inside control flow, 12993 of them:

    EndIf(EventFlag(2052));            <- terminate the event when 2052 is SET
    SetEventFlagID(6001, ON);          <- the SETTER, excluded: this event CAUSES the flag

and `AwardItemLot(101590)` names a LOT, not a flag, so it is joined back through the committed
flag_lots.tsv. Had v1 been allowed to emit, it would have written an empty table and called it "no
gated checks found". That is why --vocab exists and why it runs first.

The tool has two modes and the first one is still not optional after any corpus change:

    python tools/datamine_lot_gates.py --vocab     # LOOK. Emits nothing. Prints the call-name
                                                   # histogram + real sample lines.
    python tools/datamine_lot_gates.py --emit      # only once --vocab has confirmed the names

`--emit` hard-refuses on a degenerate parse -- no events, no flag tests, no AwardItemLot sites, no
pairs, or an implausible flood -- rather than writing a table that looks fine and means nothing.

STILL NOT DERIVED, deliberately:
  * POLARITY. `EndIf(EventFlag(X))` means the body needs X CLEAR -- the opposite of "X appears in a
    condition, so X must be set". Each construct has its own sense, the tool RECORDS the construct
    verbatim in a `context` column and prints the histogram, and the sense is assigned once per
    context during triage. A false gate is an unwinnable seed.
  * TREASURE. `EnableAssetTreasure(assetEntityId)` names an ASSET, and asset -> lot needs the MSB.
    Counted and reported as unresolved, never guessed at.
  * COMMON EVENTS. Only the 26 literal `AwardItemLot(<lot>)` sites are followed; awards routed
    through a common event's `itemLotId` param are not. datamine_boss_drops.py does that join and is
    the model if the first pass shows it matters.
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

# CONFIRMED against the real corpus (Alaric ran --vocab, 2026-07-25: 589 files, 4893 events).
# The predicate is a BARE `EventFlag(<id>)` used as an expression inside control flow -- 12993 hits --
# not any `If*EventFlag*` call. My first guess matched ZERO of them, which is exactly why --vocab
# exists and why nothing was emitted before it ran.
#
#     EndIf(EventFlag(2052));            <- terminate the event when 2052 is SET
#     SetEventFlagID(6001, ON);          <- the SETTER, not a test (excluded below)
#
# Also real, and carrying a flag id in a condition: EventFlagState (399), WaitForEventFlag (87),
# AnyBatchEventFlags (329), AllBatchEventFlags (21), CountEventFlags (44).
FLAG_TEST_RE = re.compile(r"\bEventFlag\s*\(\s*(\d+)\s*\)")
FLAG_TEST_OTHER_RE = re.compile(
    r"\b(EventFlagState|WaitForEventFlag|AnyBatchEventFlags|AllBatchEventFlags|CountEventFlags)"
    r"\s*\(([^)]*)\)")
# The SETTER must never be read as a test: `SetEventFlagID(6001, ON)` says this event CAUSES the
# flag, which is the opposite of depending on it. Counting it as a gate would invert the graph.
FLAG_SET_RE = re.compile(r"\b(SetEventFlagID|SetNetworkconnectedEventFlagID|BatchSetEventFlags|"
                         r"BatchSetNetworkconnectedEventFlags|RandomlySetEventFlagInRange|"
                         r"DisplayGenericDialogAndSetEventFlags)\s*\(([^)]*)\)")

# CONFIRMED: `AwardItemLot(101590)` takes an ItemLotParam LOT ID, not a flag -- so the lot is mapped
# back to its check flag through the committed greenfield/flag_lots.tsv. Only 26 literal call sites;
# most awards go through common events with an `itemLotId` PARAM, which this pass does not resolve
# (datamine_boss_drops.py does that join and is the model if it turns out to matter).
AWARD_LOT_RE = re.compile(r"\bAwardItemLot\s*\(\s*(\d+)\s*\)")
# `$InitializeCommonEvent(<slot>, <commonEventId>, <args...>)` -- the indirection most awards take.
COMMON_CALL_RE = re.compile(r"\$InitializeCommonEvent\(\s*\d+\s*,\s*(\d+)\s*,\s*([^)]*)\)")
# CONFIRMED: treasure is enabled by ASSET ENTITY id, not by lot or flag. Resolving asset -> lot needs
# the MSB, which this tool does not read, so these are recorded as UNRESOLVED rather than guessed.
TREASURE_RE = re.compile(r"\b(EnableAssetTreasure|DisableAssetTreasure|ForceCharacterTreasure)"
                         r"\s*\(\s*(\w+)\s*\)")

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


def _lot_to_flag():
    """ItemLotParam lot id -> the CHECK flag it awards, from the committed greenfield/flag_lots.tsv.

    `AwardItemLot` names a LOT, our checks are keyed by acquisition FLAG, and this is the join. It is
    a tracked tsv, so this half is verifiable without artifacts."""
    import csv
    path = os.path.join(GF, "flag_lots.tsv")
    if not os.path.isfile(path):
        sys.exit("FATAL: %s missing -- AwardItemLot names a LOT and there is no way to reach the "
                 "check flag without it." % path)
    out = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            try:
                out.setdefault(int(r["lot"]), set()).add(int(r["flag"]))
            except (KeyError, TypeError, ValueError):
                continue
    if len(out) < 1000:
        sys.exit("FATAL: only %d lots parsed from flag_lots.tsv -- refusing to scan against a "
                 "truncated join." % len(out))
    return out


def _context(body, pos):
    """The construct a flag test sits inside -- `EndIf`, `WaitFor`, `SkipIf`, `If`, negated, ...

    ⚠️ THE POLARITY IS NOT DERIVED HERE, ON PURPOSE. `EndIf(EventFlag(2052))` means "terminate the
    event when 2052 is SET", so the body below it requires the flag CLEAR -- the opposite of the
    reading a naive `flag appears in a condition => flag must be set` would give. Every construct has
    its own sense and I have not seen them all, so the context is RECORDED verbatim and the polarity
    is assigned once, per construct, during triage. Inventing it here is how a false gate -- an
    unwinnable seed -- gets written into a table that looks derived.
    """
    # Walk out to the OUTERMOST unclosed construct, not the nearest call. The first version took the
    # last identifier before the paren, which on `WaitFor(ElapsedSeconds(2) && EventFlag(7608))`
    # answered `ElapsedSeconds` -- a sibling argument, not the thing that decides the polarity. It
    # also read from a fixed 60-char window and so reported truncated identifiers (`racterTeamType`).
    # Both were visible in the first real run; neither was wrong enough to notice without the output.
    stmt = body.rfind(";", 0, pos) + 1
    nl = body.rfind("\n", 0, pos) + 1
    left = body[max(stmt, nl):pos]
    neg = bool(re.search(r"!\s*$", left))
    depth, name = 0, ""
    for m in re.finditer(r"([A-Za-z_]\w*)?\s*([()])", left):
        if m.group(2) == "(":
            if depth == 0 and m.group(1):
                name = m.group(1)          # outermost open construct on this statement
            depth += 1
        else:
            depth = max(0, depth - 1)
    return ("!" if neg else "") + (name or "?")


def _common_lot_params():
    """{commonEventId: itemLotId arg index} from common_func.

    Only 26 sites call `AwardItemLot(<literal>)`. The rest route through a common event that takes an
    `itemLotId` PARAM, so without this join the scan sees a fraction of the awards in the game -- the
    first real run returned 45 pairs, which is not a finding, it is a sample. Same parse
    tools/datamine_boss_drops.py already uses for boss handlers, so the shape is known-good rather
    than another guess."""
    path = os.path.join(EVT, "common_func.emevd.dcx.js")
    if not os.path.isfile(path):
        print("  (no common_func.emevd.dcx.js -- literal AwardItemLot sites only)", file=sys.stderr)
        return {}
    text = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for eid, body in _events(text):
        m = EVENT_RE.search(text[text.index(body):text.index(body) + 400])
        params = [p.strip() for p in (m.group(2) if m else "").split(",") if p.strip()]
        if "itemLotId" not in params or "AwardItemLot" not in body:
            continue
        out[eid] = params.index("itemLotId")
    return out


def emit(dry):
    files = _sources()
    check_flags = _check_flags()
    lot_to_flag = _lot_to_flag()
    common_lots = _common_lot_params()
    print("common events awarding an itemLotId param: %d" % len(common_lots))
    rows = []
    ev_total = tested = awards = treasure_unresolved = 0
    ctx_hist = collections.Counter()
    for path in files:
        src = os.path.basename(path)
        text = open(path, encoding="utf-8", errors="replace").read()
        for eid, body in _events(text):
            ev_total += 1
            # Blank the SETTERS first: a set is this event CAUSING the flag, never depending on it.
            scan = FLAG_SET_RE.sub(lambda m: " " * len(m.group(0)), body)
            gates = []
            for m in FLAG_TEST_RE.finditer(scan):
                tested += 1
                ctx = _context(scan, m.start())
                ctx_hist[ctx] += 1
                gates.append((int(m.group(1)), ctx, scan[max(0, m.start() - 40):m.end() + 10]))
            for m in FLAG_TEST_OTHER_RE.finditer(scan):
                for i in _ints(m.group(2)):
                    tested += 1
                    ctx_hist[m.group(1)] += 1
                    gates.append((i, m.group(1), m.group(0)[:110]))
            if not gates:
                continue
            awarded = set()
            for m in AWARD_LOT_RE.finditer(body):
                awards += 1
                awarded |= {f for f in lot_to_flag.get(int(m.group(1)), ()) if f in check_flags}
            for m in COMMON_CALL_RE.finditer(body):
                idx = common_lots.get(int(m.group(1)))
                if idx is None:
                    continue
                args = [a.strip() for a in m.group(2).split(",")]
                if idx >= len(args) or not args[idx].lstrip("-").isdigit():
                    continue
                awards += 1
                awarded |= {f for f in lot_to_flag.get(int(args[idx]), ()) if f in check_flags}
            treasure_unresolved += len(TREASURE_RE.findall(body))
            for cf in sorted(awarded):
                for gf, ctx, ev in gates:
                    if gf == cf:
                        continue          # a check's own acquisition flag is not its gate
                    rows.append((cf, gf, ctx, eid, src,
                                 " ".join(ev.split())[:120]))
    print("scanned %d file(s), %d event(s); %d flag test(s), %d AwardItemLot call(s), "
          "%d treasure call(s) UNRESOLVED (asset->lot needs the MSB); %d pair(s)"
          % (len(files), ev_total, tested, awards, treasure_unresolved, len(rows)))
    print("flag-test CONTEXTS (polarity is assigned per context in triage, never guessed here):")
    for ctx, n in ctx_hist.most_common(12):
        print("   %8d  %s" % (n, ctx))
    if ev_total < 100:
        sys.exit("FATAL: only %d events parsed -- EVENT_RE does not match this corpus. Run --vocab."
                 % ev_total)
    if tested == 0:
        sys.exit("FATAL: zero flag tests found -- FLAG_TEST_RE matches nothing. Run --vocab.")
    if awards == 0:
        sys.exit("FATAL: zero AwardItemLot call sites -- the award side matches nothing. Run --vocab.")
    if not rows:
        sys.exit("FATAL: zero gated checks. Every AwardItemLot event is unconditional (implausible) "
                 "or the join through flag_lots.tsv missed. Run --vocab and check the lot ids.")
    if len(rows) > 20000:
        sys.exit("FATAL: %d pairs -- too broad to be evidence. Tighten before trusting this."
                 % len(rows))
    rows.sort()
    if dry:
        for r in rows[:40]:
            print("   check %-10s gated on %-10s ctx=%-12s event %-12s %s" % r[:5])
        print("   ... %d row(s) total (dry run, nothing written)" % len(rows))
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_lot_gates.py -- DO NOT EDIT.\n")
        fh.write("# check_flag co-occurs with a test of gate_flag in one EMEVD event.\n")
        fh.write("# `context` is the construct the test sits in (EndIf / WaitFor / SkipIf / ...).\n")
        fh.write("# POLARITY IS NOT ENCODED: EndIf(EventFlag(X)) means the body needs X CLEAR, the\n")
        fh.write("#   OPPOSITE of the naive reading. Assign the sense per context during triage.\n")
        fh.write("# CANDIDATE PAIRS, not conclusions -- co-occurrence is evidence, not proof. A\n")
        fh.write("#   false gate is an unwinnable seed; a false non-gate is the bug this finds.\n")
        fh.write("check_flag\tgate_flag\tcontext\tevent_id\tsource\tevidence\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    print("wrote %s: %d candidate pair(s) over %d distinct check flag(s)"
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
