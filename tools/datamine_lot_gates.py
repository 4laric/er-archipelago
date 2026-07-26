#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_lot_gates.py -- which EVENT FLAG must already be set before a CHECK can exist.

WHY (Alaric, 2026-07-25). ⚠️ The original exemplar here was `f67050`, and it was WRONG -- that
cookbook turned out to be UNGATED, obtainable five ways. The real one is `f400191`, the Golden Seed
at Stormhill Shack (gated on questline flags 3708/3709 via $InitializeCommonEvent(90005750) arg5,
confirmed in play by Alaric 2026-07-26: it is not there until you rest at a grace in Liurnia). The
shape of the argument was right even though the example was not, so it is kept below with the
correct flag substituted. `f400191` is regioned **Limgrave**, and Limgrave is CORRECT: that is where the player
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
# ER_EVENT_DIR mirrors the ER_ARTIFACTS_VV precedent (AGENTS.md §5): it lets the decompiled EMEVD be
# staged outside the repo for a specific investigation, so the emit below is the TOOL's own output and
# never a hand-edited or path-patched copy of it.
EVT = os.environ.get("ER_EVENT_DIR") or os.path.join(ROOT, "elden_ring_artifacts", "event")
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

# 🛑 THE AWARD VERB SET WAS WRONG, and it is why this tool concluded "AwardItemLot is RARE -- scripted
# awards are not the mechanism in ER". Corpus counts: AwardItemsIncludingClients 205,
# AwardGesture 29, AwardItemLot 26. The tool knew only the MINORITY verb, so the primary award path
# was invisible and its absence was read as evidence about the GAME rather than about the scan.
_AWARD_FNS = ("AwardItemsIncludingClients", "AwardItemLot", "AwardGesture")


def _common_sigs():
    """{commonEventId: (params, [lot arg idx], {flag arg idx: test construct})} from common_func.

    ⭐ THE GATE IS A COMMON-EVENT ARGUMENT. This is the blind spot that made the first triage report
    "0 cross-region gates": the literal gate flag sits at the CALL SITE, while the test that consumes
    it sits in the CALLEE, on a PARAMETER --

        $InitializeCommonEvent(0, 90005750, 1041381702, 4350, 101910, 400191, 400191, 3708, 0)
        $Event(90005750, ..., function(assetEntityId, actionButtonParameterId, itemLotId,
                                       eventFlagId, eventFlagId2, eventFlagId3, sfxId) {
            WaitFor(EventFlag(eventFlagId3) && !AllBatchEventFlags(eventFlagId, eventFlagId2));
            ... AwardItemsIncludingClients(itemLotId);

    A scan for `EventFlag(<literal>)` inside event bodies sees NOTHING here. Measured: 185 of 256
    common events test a parameter as an event flag, and 3676 of 10449 $InitializeCommonEvent call
    sites target one of them -- so the literal-only pass was reading ~1% of the relevant corpus.

    (Exactly the defect Fable found in datamine_esd_flags.py: constant at the call site, use in the
    callee. Same fix shape, ported.)

    Pairing here is STRONGER than the co-occurrence pass: the lot and the gate come from the SAME
    call site, so the edge is not an inference about two things sharing an event body."""
    path = os.path.join(EVT, "common_func.emevd.dcx.js")
    if not os.path.isfile(path):
        print("  (no common_func.emevd.dcx.js -- common-argument gates NOT scanned)", file=sys.stderr)
        return {}
    text = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    ms = list(EVENT_RE.finditer(text))
    for i, m in enumerate(ms):
        eid = int(m.group(1))
        params = [q.strip() for q in m.group(2).split(",") if q.strip()]
        body = text[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(text)]
        lot_idx, flag_idx, batch_pairs = [], {}, []
        # ⭐ ROLE, NOT NAME. The first version of this pass emitted EVERY param tested as a flag as if
        # it were a prerequisite, and CI came back with 27 "cross-region gates" that were mostly this
        # bug. A FALSE gate is an unwinnable seed; a false non-gate is only a miss. So a param is a
        # GATE only when it is a positive requirement, and the two non-gate roles are excluded by
        # construction:
        #
        #   batch   AllBatchEventFlags(eventFlagId, eventFlagId2) -- the ACQUISITION RANGE ("already
        #           taken"), not a prerequisite. 90005750 pairs it with the check's OWN flag, so
        #           check 400381 was emitting 400382 -- the other end of its own range -- as its gate.
        #           An `arg == check flag` guard does not catch that; a RANGE guard does.
        #   bailout EndIf(EventFlag(p)) / if (EventFlag(p)) { ... EndEvent(); } -- a COMPLETION test.
        #           Its polarity is the OPPOSITE of a gate (the body runs when the flag is CLEAR).
        #           This is what the module docstring means by "POLARITY IS NOT ENCODED"; encode it.
        for bm in re.finditer(r"\b(?:All|Any)BatchEventFlags\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\s*\)", body):
            a, b = bm.group(1), bm.group(2)
            if a in params and b in params:
                batch_pairs.append((params.index(a), params.index(b)))
        batched = {i for pr in batch_pairs for i in pr}
        for j, q in enumerate(params):
            e = re.escape(q)
            if any(re.search(r"\b%s\s*\(\s*%s\s*\)" % (a, e), body) for a in _AWARD_FNS):
                lot_idx.append(j)
            if j in batched:
                continue                      # acquisition range -- never a gate
            if re.search(r"\bEndIf\(\s*!?\s*EventFlag\(\s*%s\s*\)" % e, body):
                continue                      # bail-out: completion test, inverted polarity
            if re.search(r"if\s*\(\s*EventFlag\(\s*%s\s*\)\s*\)\s*\{[^}]{0,400}?EndEvent\(\)" % e,
                         body, re.S):
                continue                      # `if (flag) { ... EndEvent(); }` -- same shape
            # ⚠️ The negation test must be LOCAL to the WaitFor. A body-wide
            # `not re.search(r"!EventFlag(p)", body)` deleted the one case we KNOW is true: 90005750
            # later contains `flag = !EventFlag(eventFlagId3) || ...`, so the Golden Seed's real gate
            # was filtered out by a line that has nothing to do with the requirement. Verifying a
            # filter against a known-true case is the only reason that was caught.
            for wm in re.finditer(r"\bWaitFor\(([^;]{0,300}?)\)\s*;", body, re.S):
                if any("!" not in om.group(1) for om in
                       re.finditer(r"(!?\s*)EventFlag\(\s*%s\s*\)" % e, wm.group(1))):
                    flag_idx[j] = "WaitFor"   # POSITIVE prerequisite -- the only real gate shape
                    break
        if lot_idx and flag_idx:
            out[eid] = (params, lot_idx, flag_idx, batch_pairs)
    return out


def _common_arg_gates(files, lot_to_flag, check_flags):
    """Rows in emit()'s shape, from call-site arguments. Returns (rows, stats)."""
    sigs = _common_sigs()
    rows, stat = [], collections.Counter()
    stat["sigs"] = len(sigs)
    if not sigs:
        return rows, stat
    for path in files:
        src = os.path.basename(path)
        text = open(path, encoding="utf-8", errors="replace").read()
        for m in COMMON_CALL_RE.finditer(text):
            ceid = int(m.group(1))
            if ceid not in sigs:
                continue
            stat["sites"] += 1
            args = [a.strip() for a in m.group(2).split(",")]
            _params, lot_idx, flag_idx, _batch = sigs[ceid]
            cfl = set()
            for i in lot_idx:
                if i < len(args) and args[i].lstrip("-").isdigit():
                    cfl |= {f for f in lot_to_flag.get(int(args[i]), ()) if f in check_flags}
            if not cfl:
                stat["site_lot_not_a_check"] += 1
                continue
            # Acquisition ranges resolved AT THE CALL SITE: any gate value inside one is the check's
            # own bookkeeping, not a prerequisite.
            ranges = []
            for ai, bi in sigs[ceid][3]:
                if ai < len(args) and bi < len(args) and args[ai].lstrip("-").isdigit() \
                        and args[bi].lstrip("-").isdigit():
                    lo, hi = sorted((int(args[ai]), int(args[bi])))
                    ranges.append((lo, hi))
            for gi, ctx in flag_idx.items():
                if gi >= len(args) or not args[gi].lstrip("-").isdigit():
                    stat["gate_arg_not_literal"] += 1
                    continue
                g = int(args[gi])
                if any(lo <= g <= hi for lo, hi in ranges):
                    stat["gate_in_acquisition_range"] += 1
                    continue
                if g <= 0:
                    stat["gate_sentinel"] += 1   # 0/-1 = "no gate" sentinel, never a flag
                    continue
                for c in sorted(cfl):
                    if g == c:
                        continue                  # a check's own acquisition flag is not its gate
                    rows.append((c, g, "commonarg/" + ctx, ceid, src,
                                 "$InitializeCommonEvent(%d) arg%d" % (ceid, gi)))
    return rows, stat


_MAP_FILE_RE = re.compile(r"^(m\d\d_\d\d_\d\d_\d\d)\.emevd")


def _setter_maps(files):
    """gate_flag -> {map_id that SETS it}, harvested from the same corpus.

    WHY THIS EXISTS. The cross-region screen used to resolve a gate flag's region by DECODING its
    number, and that only works for map-encoded flags. NPC/questline state flags are bare 4-digit ids
    (3708, 3709, 3409) with nothing to decode, so `resolve()` returned None and the pair was dropped
    -- 87 of 104 pairs, silently. That is how f400191 (Golden Seed, Stormhill Shack, gated on a
    Liurnia questline flag) shipped claiming an early Limgrave reachability it does not have, while
    the screen reported clean. A filter with no tally is a lie (CONTRIBUTING rule 4).

    A flag we cannot decode can still be LOCATED: whichever map's EMEVD calls SetEventFlag on it is
    where the thing that sets it happens. That is a datum, not a guess.

    `common.emevd` / `common_func` are DELIBERATELY EXCLUDED -- a common event is not a place, and
    letting it answer would hand back a confident non-region. A flag set from several maps is
    reported with ALL of them (a `|`-joined value), never collapsed to a first-wins pick: that is a
    genuine one-to-many, and the consumer must decide, not this tool.
    """
    out = collections.defaultdict(set)
    common_only = collections.Counter()
    for path in files:
        base = os.path.basename(path)
        m = _MAP_FILE_RE.match(base)
        for mm in FLAG_SET_RE.finditer(open(path, encoding="utf-8", errors="replace").read()):
            for fid in _ints(mm.group(2)):
                if m:
                    out[fid].add(m.group(1))
                else:
                    common_only[fid] += 1
    only_common = sorted(f for f in common_only if f not in out)
    print("setter-map index: %d flag(s) set by a MAP emevd; %d set ONLY from common/common_func "
          "(no place -- reported, not guessed)" % (len(out), len(only_common)))
    return out


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
        if "AwardItemLot" not in body:
            continue
        # SUBSTRING, not equality. Exact `itemLotId` matched exactly ONE common event on the real
        # corpus while the vocab dump plainly showed several `AwardItemLot(itemLotId)` sites -- the
        # decompiler decorates some param names (X0_4_itemLotId and friends). Matching the whole name
        # was a guess about the decompiler's style dressed as a key.
        idx = next((i for i, q in enumerate(params) if "itemlotid" in q.lower()), None)
        if idx is None:
            # Last resort: the event awards a lot from SOME param and we cannot tell which. Reported,
            # never guessed -- picking one would fabricate a check->gate edge.
            if re.search(r"AwardItemLot\s*\(\s*[A-Za-z_]", body):
                out.setdefault("_unnamed", set()).add(eid)
            continue
        out[eid] = idx
    return out


def _treasure_assets():
    """{asset entity id -> {check flags}} from greenfield/treasure_assets.tsv.

    THE join for `EnableAssetTreasure(assetEntityId)`, emitted by
    `tools/datamine_msb_item_regions.py --emit-assets`.

    ⚠️ Only ~229 of ~2824 treasures have a nonzero asset EntityID -- the rest are 0, and an asset with
    no entity cannot be named by that instruction at all. So a partial-looking resolve rate here is
    expected and is not evidence of a broken join; 229 is plausibly the whole EMEVD-addressable
    population. (f67050, the case this tool was built for, is one of the zeros -- measured 2026-07-25
    with `--explain 67050`.)
    """
    import csv
    path = os.path.join(GF, "treasure_assets.tsv")
    if not os.path.isfile(path):
        print("  (no greenfield/treasure_assets.tsv -- run "
              "`datamine_msb_item_regions.py --emit-assets` to resolve the treasure sites)",
              file=sys.stderr)
        return {}
    out = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = (ln for ln in fh if not ln.lstrip().startswith("#"))
        for r in csv.DictReader(rows, delimiter="\t"):
            try:
                out.setdefault(int(r["asset_entity"]), set()).add(int(r["flag"]))
            except (KeyError, TypeError, ValueError):
                continue
    if not out:
        sys.exit("FATAL: %s exists but parsed to ZERO rows -- a schema drift in the writer would "
                 "otherwise route every treasure site into 'unresolved', which reads as 'the asset "
                 "join did not work' rather than 'the file is unreadable'. Re-emit it." % path)
    return out


def _treasure_lots():
    """{treasure lot id -> {check flags}} from the committed greenfield/msb_flag_region.tsv.

    `EnableAssetTreasure(assetEntityId)` names an ASSET, and the first pass reported 186 of them
    unresolved -- the single largest untapped population, and the one holding the class this tool was
    built for (f67050, the Stormhill Shack cookbook, is a treasure). Resolving asset -> lot was
    assumed to need the MSB.

    It may not: msb_flag_region.tsv already carries `flag -> item_lot_id` for every treasure, and ER
    treasure asset entity ids and lot ids share a numbering (f67050 -> lot 1040390000). So this tries
    the direct join and the caller PRINTS THE MATCH RATE. A low rate means the numbering assumption is
    wrong and the MSB really is needed -- which is a measurement, not a hunch, and costs one run."""
    import csv
    path = os.path.join(GF, "msb_flag_region.tsv")
    if not os.path.isfile(path):
        return {}
    out = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        # SKIP THE COMMENT PREAMBLE FIRST. csv.DictReader takes the FIRST line as the header, and this
        # file opens with `# maps=all sources=...` -- so reading it raw makes every field name wrong,
        # every lookup a KeyError, and the whole join silently EMPTY. The smoke test caught it as
        # "treasure lot 1040390000 -> None" on a row that is plainly in the file. An empty join here
        # would have looked exactly like "the asset-id numbering assumption is wrong, we need the
        # MSB after all" -- a wrong conclusion, reached confidently, from a parsing bug.
        rows = (ln for ln in fh if not ln.lstrip().startswith("#"))
        for r in csv.DictReader(rows, delimiter="\t"):
            try:
                out.setdefault(int(r["item_lot_id"]), set()).add(int(r["flag"]))
            except (KeyError, TypeError, ValueError):
                continue
    if not out:
        sys.exit("FATAL: msb_flag_region.tsv parsed to ZERO lot->flag rows -- refusing to report "
                 "every treasure as unresolved on the strength of a broken join.")
    return out


def emit(dry):
    files = _sources()
    check_flags = _check_flags()
    lot_to_flag = _lot_to_flag()
    common_lots = _common_lot_params()
    unnamed = common_lots.pop("_unnamed", set())
    print("common events awarding an itemLotId param: %d (%d more award from a param this cannot "
          "name -- reported, not guessed)" % (len(common_lots), len(unnamed)))
    treasure_lots = _treasure_lots()
    treasure_assets = _treasure_assets()
    setter_maps = _setter_maps(files)
    rows = []
    ev_total = tested = awards = treasure_unresolved = treasure_hits = treasure_character = 0
    treasure_asset_ids = set()
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
            for m in TREASURE_RE.finditer(body):
                verb, arg = m.group(1), m.group(2)
                if verb == "ForceCharacterTreasure":
                    # A CHARACTER entity, not an asset. Joining it against an asset table can only
                    # ever miss, and counting those misses as "unresolved asset sites" inflates the
                    # number this whole effort is measured by. Segregated.
                    treasure_character += 1
                    continue
                if not arg.lstrip("-").isdigit():
                    treasure_unresolved += 1
                    continue
                # NO FALLBACK to the lot-id table. That join was MEASURED DEAD (0 of 186) and left
                # in as an `or` -- so any numeric collision between an asset entity id and a lot id
                # would fabricate a check->gate edge, and a fabricated gate is an unwinnable seed.
                # Fable demonstrated it: EnableAssetTreasure(1000) "resolving" to a flag via the lot
                # table. A disproven join kept as a fallback is not belt-and-braces, it is a lie
                # about why the code works.
                hit = treasure_assets.get(int(arg))
                if hit:
                    treasure_hits += 1
                    # THE VERB IS THE POLARITY. A pair from Disable* means the flag makes the check
                    # UNAVAILABLE (missable) -- the inverted sense of an Enable pair -- and without
                    # the verb the two are indistinguishable in the tsv, so one `context` would span
                    # two opposite populations. Carried into the context column.
                    awarded |= {(f, verb) for f in hit if f in check_flags}
                else:
                    treasure_unresolved += 1
                    treasure_asset_ids.add(int(arg))
            for entry in sorted(awarded, key=lambda e: (e[0] if isinstance(e, tuple) else e)):
                cf, verb = entry if isinstance(entry, tuple) else (entry, "")
                for gf, ctx, ev in gates:
                    if gf == cf:
                        continue          # a check's own acquisition flag is not its gate
                    rows.append((cf, gf, (ctx + "/" + verb) if verb else ctx, eid, src,
                                 " ".join(ev.split())[:120]))
    print("scanned %d file(s), %d event(s); %d flag test(s), %d AwardItemLot call(s), "
          "%d treasure call(s) RESOLVED, %d unresolved, %d ForceCharacterTreasure (character "
          "entity, not an asset -- never resolvable here); %d pair(s)"
          % (len(files), ev_total, tested, awards, treasure_hits, treasure_unresolved,
             treasure_character, len(rows)))
    if treasure_asset_ids:
        sample = sorted(treasure_asset_ids)[:12]
        print("unresolved treasure ASSET ids (%d distinct) -- their numbering vs the lot ids in\n"
              "  msb_flag_region.tsv is what says whether a direct join is possible at all:\n   %s"
              % (len(treasure_asset_ids), ", ".join(str(a) for a in sample)))
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
    ca_rows, ca = _common_arg_gates(files, lot_to_flag, check_flags)
    print("common-ARGUMENT gates: %d common event(s) award a param lot AND test a param flag; "
          "%d call site(s); %d pair(s)" % (ca["sigs"], ca["sites"], len(ca_rows)))
    print("   lot arg not a check: %d | gate arg not literal: %d | gate 0/-1 sentinel: %d | "
          "gate inside acquisition range: %d"
          % (ca["site_lot_not_a_check"], ca["gate_arg_not_literal"], ca["gate_sentinel"],
             ca["gate_in_acquisition_range"]))
    if ca["sigs"] and not ca_rows:
        sys.exit("FATAL: %d flag-testing common event signatures parsed but ZERO pairs resolved. An "
                 "empty result from a join that MUST match is a failure, not a clean run."
                 % ca["sigs"])
    rows.extend(ca_rows)

    if not rows:
        sys.exit("FATAL: zero gated checks. Every AwardItemLot event is unconditional (implausible) "
                 "or the join through flag_lots.tsv missed. Run --vocab and check the lot ids.")
    if treasure_assets and treasure_hits == 0 and treasure_unresolved:
        sys.exit("FATAL: treasure_assets.tsv is loaded (%d entities) and resolved ZERO of %d "
                 "EnableAssetTreasure sites. That is the population this tool exists for, and it is "
                 "the one join that had no refusal condition. Either the asset ids in the EMEVD are "
                 "entity GROUPS rather than part entities, or the tsv was emitted for a subset of "
                 "maps -- check its `# maps=` header before reading anything else."
                 % (len(treasure_assets), treasure_unresolved))
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
        fh.write("# gate_map = the map emevd(s) that SET gate_flag, `|`-joined when several do.\n")
        fh.write("#   Empty = no MAP sets it (common-event only, or nothing found). This is the\n")
        fh.write("#   region handle for gate flags whose NUMBER carries no map encoding -- the\n")
        fh.write("#   NPC/questline state flags the numeric decode was blind to.\n")
        fh.write("check_flag\tgate_flag\tcontext\tevent_id\tsource\tevidence\tgate_map\n")
        _resolved = 0
        for r in rows:
            _gm = "|".join(sorted(setter_maps.get(int(r[1]), ())))
            if _gm:
                _resolved += 1
            fh.write("\t".join(str(x) for x in r) + "\t" + _gm + "\n")
    _distinct = {r[1] for r in rows}
    _dist_res = len({g for g in _distinct if setter_maps.get(int(g))})
    print("wrote %s: %d candidate pair(s) over %d distinct check flag(s)"
          % (OUT, len(rows), len({r[0] for r in rows})))
    print("gate_map resolved: %d/%d pair(s), %d/%d distinct gate flag(s). The UNRESOLVED remainder "
          "is the screen's real blind spot -- it is printed, not hidden."
          % (_resolved, len(rows), _dist_res, len(_distinct)))
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


def self_test():
    """Offline proof of the setter-map harvest. The real EMEVD is Windows-only, so the LOGIC is
    exercised against fixtures here -- runnable in the agent sandbox, where the corpus is not.

    Deliberately includes the break-the-fix control: with common/common_func allowed to answer, a
    flag set only from common.emevd would report a 'region' that is not a place.
    """
    import tempfile
    fails = []

    def check(name, cond):
        print(("  PASS " if cond else "  FAIL ") + name)
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as d:
        def w(fn, body):
            open(os.path.join(d, fn), "w", encoding="utf-8").write(body)
        w("m60_41_38_00.emevd.dcx.js", "$Event(1, Default, function() { EndIf(EventFlag(3708)); });")
        w("m60_36_43_00.emevd.dcx.js", "$Event(2, Default, function() { SetEventFlagID(3708, ON); });")
        w("m60_37_43_00.emevd.dcx.js", "$Event(3, Default, function() { SetEventFlagID(9001, ON); "
                                       "SetEventFlagID(3708, ON); });")
        w("common.emevd.dcx.js", "$Event(4, Default, function() { SetEventFlagID(7777, ON); });")
        w("common_func.emevd.dcx.js", "$Event(5, Default, function() { SetEventFlagID(7778, ON); });")
        files = sorted(glob.glob(os.path.join(d, "*.emevd.dcx.js")))
        sm = _setter_maps(files)

        check("a map setter is found", sm.get(3708) is not None)
        check("MULTI-setter keeps every map, never first-wins",
              sm.get(3708) == {"m60_36_43_00", "m60_37_43_00"})
        check("a flag only TESTED is not treated as set there",
              "m60_41_38_00" not in sm.get(3708, set()))
        check("single-map setter resolves to exactly that map", sm.get(9001) == {"m60_37_43_00"})
        check("common.emevd is NOT a place", 7777 not in sm)
        check("common_func is NOT a place", 7778 not in sm)
        check("unset flag resolves to nothing, rather than to something plausible",
              sm.get(4242) is None)

        # BREAK THE FIX: if common files were allowed to answer, 7777 would get a bogus 'region'.
        broken = collections.defaultdict(set)
        for path in files:
            for mm in FLAG_SET_RE.finditer(open(path, encoding="utf-8").read()):
                for fid in _ints(mm.group(2)):
                    broken[fid].add(os.path.basename(path).split(".")[0])
        check("control: without the map-file guard, common.emevd answers (so the guard is real)",
              7777 in broken and "common" in broken[7777])

    print("")
    if fails:
        print("FAILED: %d -- %s" % (len(fails), ", ".join(fails)))
        return 1
    print("ALL PASS")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vocab", action="store_true",
                    help="LOOK FIRST: print the EMEVD call-name histogram + sample lines. No output.")
    ap.add_argument("--emit", action="store_true", help="write greenfield/lot_gates.tsv")
    ap.add_argument("--dry", action="store_true", help="parse and print, write nothing")
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="offline fixture tests for the setter-map harvest (no artifacts needed)")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.vocab:
        return vocab()
    if args.emit or args.dry:
        return emit(dry=args.dry)
    ap.print_help()
    print("\nStart with --vocab. The instruction names in this file are CANDIDATES; see the header.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
