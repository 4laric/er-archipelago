#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_esd_flags.py -- every EVENT FLAG an NPC talk ESD SETS, and with what sense.

WHY
---
`datamine_esd_gates.py` mines the ESD for `OpenRegularShop` (shop gates) and `AwardItemLot` (dialogue
gifts). It does not touch `SetEventFlag`, which is ~4800 call sites and is where NPC STATE lives --
"Roderika has moved on", "this questline advanced". That vocabulary is what distinguishes an
NPC-STATE gate from a world/progression gate in `lot_gates.tsv`, and nothing derived it before.

The motivating class (HANDOFF-20260725-evening §4): a check regioned CORRECTLY that still cannot
EXIST yet, because its pickup only spawns after an NPC moves. Region oracles are blind to it -- the
region is right; what is missing is an ACCESS RULE.

WHAT THE DATA SAYS (measured 2026-07-25, and it is the reason this tool emits a JOIN KEY and not a
verdict): the flags an ESD sets are DISJOINT from pickup acquisition flags --

    ESD-set flags (2409 distinct) INTERSECT msb_flag_region (2803 flags) = 0
    ... INTERSECT the 1824 corpse (宝死体) flags                          = 0
    ... INTERSECT flag_lots (4558)                                        = 3   <- all 400xxx key-item
                                                                                   OBTAINED flags

    ⚠️ THE ZERO IS NOT SELF-VALIDATING, and this is the tool's main epistemic hazard. ~82% of it is
    guaranteed by FromSoft's block allocation: 2302 of the 2803 msb flags sit in the per-map x7xxx
    treasure block, which the ESD vocabulary does not occupy at all -- so A BROKEN JOIN PRINTS THE SAME
    ZERO. What licenses it is (a) the informative overlap band coming up empty too, (b) the zeroes
    surviving three successive parser widenings that grew the vocabulary 1429 -> 2058 -> 2398, and
    (c) the POSITIVE CONTROL below, which the tool now hard-fails on. Never quote the zero without it.

    POSITIVE CONTROL: 13 of the 53 `lot_gates.tsv` gate_flags are ESD-set. All cross-check numbers are
    RECOMPUTED at emit time and written into the output header -- they are not prose, and they cannot
    go stale silently (CONTRIBUTING rule 10).

So an ESD never sets a pickup's acquisition flag. The chain is three-legged:

    ESD sets an NPC-STATE flag  ->  EMEVD tests it  ->  treasure enabled/disabled

Only the middle leg lives in `lot_gates.tsv`, and that is why this table is an ORACLE to join
against, not an answer on its own. Worked example, both legs already in committed data:
`gate 20002739 -> check 20007810` in `lot_gates.tsv` with context `!if/DisableAssetTreasure`, and
20002739 appears below as ESD-set. 13 of the 53 `lot_gates` gate_flags resolve this way.

⚠️ NOT PROVEN: that f67050 (the Stormhill Shack cookbook) is gated this way. It is absent from
`lot_gates.tsv` entirely -- its asset EntityID is 0, so the EMEVD treasure scan never names it. This
tool does not reach it. Do not read a green run here as having explained f67050.

PARSING NOTES (each one a bug that produced a confident EMPTY result first)
- `SetEventFlag(<id>, FlagState.On)` -- argument 2 is an ENUM ATTRIBUTE, not an int. A `\\d+,\\d+`
  regex matches 1 of 4800 sites and reports "no data". Parsed with `ast`, not a regex.
- ~14% of sites pass a PARAMETER (`flag5`) or `const + flag5`. ESDLang FORWARDS parameters through
  call chains (`x37(flag1=1044339200)` -> `x43(flag1=flag1)` -> `x33` -> `SetEventFlag(flag1, ...)`),
  so a ONE-HOP lookup finds nothing and tallies "no caller value" -- a tally that is itself FALSE.
  Resolution is transitive over a per-file call graph, cycle-guarded and depth-capped; 680 of 708
  param/binop sites resolve, the remaining 28 are genuinely runtime and are counted.
- The `const + param` form is a QUESTLINE STEP LADDER. Dropping those biased the loss toward exactly
  the NPC-state progression flags this tool exists to capture.
- `SetEventFlagIf(<condition>, <target>, <sense>)`: the TARGET IS ARG 2 and the sense ARG 3. Arg 1 is
  the predicate -- reading it as the target would emit the GATE as though it were the thing gated.
- ESDLang parameter DEFAULTS are excluded. NOT because they are sentinels (an earlier version claimed
  that; it is false -- they are mostly real baked values), but because ESDLang emits every kwarg
  explicitly at every call site, so a default never binds. Verified: identical output either way.

INPUT: ESDLang-decompiled Python (Windows one-time step; see datamine_esd_gates.py docstring).
OUTPUT: greenfield/esd_flags.tsv -- flag, sense, talk_id, map_id, how
  sense = on | off   (FlagState.On / FlagState.Off)
  how   = literal      (the id was an integer literal at the call site)
        | arg          (resolved transitively through this file's call graph; never guessed)
        | argsum       (`const + param` -- a questline STEP LADDER)
        | conditional  (SetEventFlagIf)
        | rawsense<N>  (second arg was the raw int N, not a FlagState enum; sense=other)

USAGE:
    python tools/datamine_esd_flags.py --probe    # print what was parsed, write nothing
    python tools/datamine_esd_flags.py            # write greenfield/esd_flags.tsv
"""
import argparse
import ast
import collections
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(REPO, "elden_ring_artifacts")
PYDIR_DEFAULT = os.path.join(ART, "talk")
OUT = os.path.join(REPO, "greenfield", "esd_flags.tsv")

# F3 (Fable review 2026-07-25): `SetEventFlagIf` and `SetEventFlagValue` were dropped BEFORE any
# counter -- "a filter with no tally is a lie" (CONTRIBUTING rule 4). The sibling datamine_esd_gates.py
# already carried SetEventFlagValue; the house convention knew and this tool did not.
_SETFLAG_FNS = {"SetEventFlag"}
_SETFLAG_IF_FNS = {"SetEventFlagIf"}          # (cond, TARGET, sense) -- target is ARG 2, sense ARG 3
_SETFLAG_VALUE_FNS = {"SetEventFlagValue"}    # multi-bit VALUE write; base flag tallied, not emitted
_SENSE = {"On": "on", "Off": "off"}

# Depth cap for transitive kwarg propagation. Longest chain MEASURED on the 2026-07-25 corpus is 5
# hops (min-depth histogram {0:325, 1:137, 2:75, 3:67, 4:27, 5:49} over the 2398 flags), so 8 is slack.
# ⚠️ Truncation at the cap is SILENT -- _resolve_param returns whatever it reached, and only a fully
# empty resolution is tallied. If a future corpus needs deeper chains this will quietly under-resolve,
# so raise the cap rather than trusting the tallies to notice.
_PROP_DEPTH = 8

def _fn_name(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _const_int(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _const_int(node.operand)
        return None if v is None else -v
    return None


def _sense_of(node):
    """FlagState.On/Off -> 'on'/'off'. An int second arg is NOT a sense; report it as unknown."""
    if isinstance(node, ast.Attribute) and node.attr in _SENSE:
        return _SENSE[node.attr]
    return None


def _map_of(path, pydir):
    """m60_00_00_00 from .../talk/m60_00_00_00-only/t123.py -- the containing dir, suffix stripped."""
    d = os.path.basename(os.path.dirname(os.path.abspath(path)))
    for suf in ("-only", "-talkesdbnd-dcx"):
        if d.endswith(suf):
            d = d[: -len(suf)]
    return d if d.startswith("m") else "?"


def _talk_id_of(path):
    stem = os.path.basename(path)[:-3]
    digits = "".join(ch for ch in stem if ch.isdigit())
    return digits or stem


def _bindings(tree):
    """(callee_fn_name, kwarg_name) -> ({literal ints}, {(caller_fn, caller_param) forwarded}).

    ESDLang emits `call = t204101000_x5(flag1=10000850, flag2=flag2, ...)`. The FORWARDING form is the
    one the first version of this tool missed (F1): a kwarg whose value is a bare Name is a parameter
    handed down from the caller, so the constant lives one or more hops UP. Recording those edges is
    what turns 321 resolved sites into ~537.

    Parameter DEFAULTS are deliberately not collected. (The original comment claimed they are 6000
    sentinels -- Fable showed that is FALSE, they are mostly real baked values. They are excluded for a
    different and sufficient reason: ESDLang emits every kwarg explicitly at every call site, so a
    default never binds. Verified: resolution with and without default-fallback gives an identical set.)
    """
    lit = collections.defaultdict(set)
    fwd = collections.defaultdict(set)
    owner = _enclosing_fns(tree)
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        fn = _fn_name(n)
        if not fn:
            continue
        for kw in n.keywords:
            if kw.arg is None:
                continue
            v = _const_int(kw.value)
            if v is not None:
                lit[(fn, kw.arg)].add(v)
            elif isinstance(kw.value, ast.Name):
                # owner is now a CHAIN (innermost first, F6); the forwarding edge is owed to every
                # enclosing def, because a nested `def ExitPause()` forwards its parent's parameter.
                # ⚠️ LATENT (D4): the edge is attached to EVERY enclosing def NAME, and resolution
                # tries each enclosing scope, so two sibling machines sharing a parameterised def name
                # could cross-contaminate. Measured zero effect on this corpus -- no duplicate-named
                # def is ever called with kwargs, and no call site omits a declared kwarg. Object-key
                # the scope if that ever stops being true.
                for enclosing in (owner.get(n) or [""]):
                    fwd[(fn, kw.arg)].add((enclosing, kw.value.id))
    return lit, fwd


def _resolve_param(key, lit, fwd, depth=_PROP_DEPTH, seen=None):
    """All literal ints that can reach parameter `key` = (fn_name, param_name), following forwards.

    Cycle-guarded and depth-capped. Constants only -- never a default, never a runtime expression.
    """
    if seen is None:
        seen = set()
    if key in seen or depth < 0:
        return set()
    seen.add(key)
    out = set(lit.get(key, ()))
    for up in fwd.get(key, ()):
        out |= _resolve_param(up, lit, fwd, depth - 1, seen)
    return out


def _flag_values(node, fnname, lit, fwd):
    """Literal flag ids a SetEventFlag first-argument can take. ([], reason) when it cannot be reduced.

    Handles three shapes, in the order they occur in the corpus:
      literal            -> {n}
      Name (a parameter) -> resolve through the call graph
      BinOp const + Name -> F2: base-plus-offset QUESTLINE STEP LADDERS. Abandoning these was biased
                            toward losing exactly the NPC-state progression flags this tool exists for.
    """
    v = _const_int(node)
    if v is not None:
        return {v}, "literal"
    if isinstance(node, ast.Name):
        got = _resolve_param((fnname, node.id), lit, fwd)
        return (got, "arg") if got else (set(), "param %s (unreachable)" % node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        for a, b in ((node.left, node.right), (node.right, node.left)):
            base = _const_int(a)
            if base is not None and isinstance(b, ast.Name):
                got = _resolve_param((fnname, b.id), lit, fwd)
                if got:
                    return {base + g for g in got}, "argsum"
                return set(), "binop %s+%s (unreachable)" % (base, b.id)
        return set(), "binop name+name (runtime)"
    return set(), type(node).__name__ + " expr (runtime)"


def _enclosing_fns(tree):
    """node -> [innermost .. outermost] enclosing FunctionDef NAMES.

    F6: the first version keyed a flat dict by name and relied on `ast.walk` BFS order to make
    "innermost" come out right. It did -- 0 mismatches over all 365 files -- but the order is
    explicitly unspecified, and 324/365 files carry duplicate def names (`ExitPause` up to 19x). This
    builds the chain by parent links instead, and returns the whole chain OUTWARD so a SetEventFlag
    inside a nested `def ExitPause()` can still resolve a parameter declared by its enclosing machine
    (21 such sites were being lost).
    """
    chain = {}

    def walk(node, stack):
        for child in ast.iter_child_nodes(node):
            nxt = ([child.name] + stack) if isinstance(child, ast.FunctionDef) else stack
            chain[child] = nxt
            walk(child, nxt)

    chain[tree] = []
    walk(tree, [])
    return chain


def scan(pydir, pyfile):
    files = [pyfile] if pyfile else sorted(glob.glob(os.path.join(pydir, "**", "*.py"), recursive=True))
    if not files:
        sys.exit("FATAL: no ESDLang .py under %s -- nothing scanned, nothing written. These are "
                 "Windows-only artifacts; see the module docstring." % (pyfile or pydir))

    rows = set()
    stat = collections.Counter()
    unresolved = collections.Counter()
    parse_failed = []

    for fp in files:
        src = open(fp, encoding="utf-8", errors="replace").read()
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            parse_failed.append((os.path.basename(fp), str(e)))
            continue
        stat["files"] += 1
        talk, mp = _talk_id_of(fp), _map_of(fp, pydir)
        lit, fwd = _bindings(tree)
        chain = _enclosing_fns(tree)

        for n in ast.walk(tree):
            fn = _fn_name(n) if isinstance(n, ast.Call) else None
            if fn is None:
                continue
            is_plain, is_if, is_val = fn in _SETFLAG_FNS, fn in _SETFLAG_IF_FNS, fn in _SETFLAG_VALUE_FNS
            if not (is_plain or is_if or is_val):
                continue

            if is_val:
                # A multi-bit VALUE write, not an on/off state flag. Excluded BY DESIGN -- but tallied,
                # because an untallied filter is indistinguishable from "the data is not there".
                stat["site_value_write"] += 1
                continue

            stat["sites"] += 1
            # SetEventFlagIf(<condition>, <target>, <sense>) -- the TARGET IS ARG 2, not arg 1, and the
            # sense is arg 3. Verified across all 75 sites in the corpus: arity 3, arg2 always an int
            # literal, arg3 always FlagState.*. (Arg 1 is the predicate and is NOT a flag being set --
            # reading it as the target would emit the GATE as though it were the thing gated.)
            need = 3 if is_if else 2
            if len(n.args) < need:
                stat["site_bad_arity"] += 1
                continue
            flag_node = n.args[1] if is_if else n.args[0]
            sense = _sense_of(n.args[2] if is_if else n.args[1])
            if sense is None:
                # D1 (Fable re-review): these 19 sites are SetEventFlag(<real NPC-state flag>, -1) x18
                # and (..., 2) x1 -- an enum value ESDLang emitted raw, not junk. Dropping them lost 11
                # distinct flags that appear NOWHERE else in the vocabulary, so a later lot_gates join
                # against one would have misclassified an NPC-state gate as a world gate. Emitted as
                # sense=other rather than discarded; the raw int is preserved in `how` so a consumer can
                # decide, and nothing here silently vanishes.
                raw = _const_int(n.args[2] if is_if else n.args[1])
                if raw is None:
                    stat["site_sense_unparsed"] += 1
                    unresolved["sense expr (runtime)"] += 1
                    continue
                sense, forced_how = "other", "rawsense%d" % raw
            else:
                forced_how = None

            # Resolve against the chain OUTWARD: a nested `def ExitPause()` sees its parent's params.
            vals, how = set(), "?"
            for owner_fn in (chain.get(n) or [""]):
                vals, how = _flag_values(flag_node, owner_fn, lit, fwd)
                if vals:
                    break
            if not vals:
                stat["site_unresolved"] += 1
                unresolved[how] += 1
                continue

            kind = forced_how or ("conditional" if is_if else how)
            for v in vals:
                rows.add((v, sense, talk, mp, kind))
            stat["site_" + ("rawsense" if forced_how else
                            ("conditional" if is_if else how))] += 1

    return rows, stat, unresolved, parse_failed


def crosscheck(rows, repo):
    """F5: the KEY STRUCTURAL CLAIM, COMPUTED -- never again asserted only in prose.

    The disjointness zeroes are ~82% guaranteed by FromSoft's flag-block allocation (2302 of the 2803
    msb_flag_region flags sit in the per-map x7xxx treasure block, which the ESD vocabulary does not
    occupy at all). A BROKEN JOIN PRINTS THE SAME ZERO. So the zero is not self-validating: it is
    reported alongside a mandatory POSITIVE CONTROL (lot_gates gate_flag hits), and the caller fails
    when the control is empty.
    """
    # A MISSING input must not silently disable the guards below. Found while break-testing: running
    # the script from a copied path moved REPO, every load() returned None, and the disjointness +
    # positive-control checks skipped without a word -- the table would still have been emitted, with
    # -1 in its header. Absent inputs are a FATAL, not a quiet pass.
    missing = [n for n in ("msb_flag_region.tsv", "flag_lots.tsv", "lot_gates.tsv")
               if not os.path.exists(os.path.join(repo, "greenfield", n))]
    if missing:
        sys.exit("FATAL: cross-check input(s) missing under %s/greenfield: %s. Without them the "
                 "disjointness check and the positive control CANNOT RUN, and this table is not "
                 "evidence of anything. Set ER_REPO. Nothing written."
                 % (repo, ", ".join(missing)))

    def load(name):
        fp = os.path.join(repo, "greenfield", name)
        if not os.path.exists(fp):
            return None
        out = []
        with open(fp, encoding="utf-8") as fh:
            hdr = None
            for line in fh:
                if line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if hdr is None:
                    hdr = parts
                    continue
                out.append(dict(zip(hdr, parts)))
        return out

    esd = {r[0] for r in rows}
    res = {"esd": len(esd)}
    msb = load("msb_flag_region.tsv")
    if msb is not None:
        allm = {int(x["flag"]) for x in msb if x["flag"].isdigit()}
        corpse = {int(x["flag"]) for x in msb if "\u5b9d\u6b7b\u4f53" in (x.get("treasure_name") or "")}
        res.update(msb=len(allm), msb_hit=len(esd & allm), corpse=len(corpse), corpse_hit=len(esd & corpse))
    fl = load("flag_lots.tsv")
    if fl is not None:
        f = {int(x["flag"]) for x in fl if x["flag"].isdigit()}
        res.update(lots=len(f), lots_hit=len(esd & f))
    lg = load("lot_gates.tsv")
    if lg is not None:
        gf = {int(x["gate_flag"]) for x in lg if x["gate_flag"].lstrip("-").isdigit()}
        res.update(gates=len(gf), gates_hit=len(esd & gf), gates_hits=sorted(esd & gf))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pydir", default=PYDIR_DEFAULT)
    ap.add_argument("--pyfile")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--probe", action="store_true", help="print what was parsed; write nothing")
    args = ap.parse_args()

    if not args.pyfile and not os.path.isdir(args.pydir):
        sys.exit("FATAL: %s not found. Decompile the ESDs first (see datamine_esd_gates.py)." % args.pydir)

    pyfile_mode = bool(args.pyfile)
    rows, stat, unresolved, parse_failed = scan(args.pydir, args.pyfile)

    print("files parsed        : %d" % stat["files"])
    print("SetEventFlag sites  : %d" % stat["sites"])
    for k, lbl in (("site_literal", "literal id"), ("site_arg", "arg-resolved (call graph)"),
                   ("site_argsum", "const+arg (step ladder)"), ("site_conditional", "SetEventFlagIf")):
        print("  %-25s: %d" % (lbl, stat[k]))
    print("  %-25s: %d   <- counted, never dropped" % ("UNRESOLVED", stat["site_unresolved"]))
    for k, v in unresolved.most_common(6):
        print("      %5d  %s" % (v, k))
    print("  %-25s: %d   (raw int sense, emitted as sense=other)" % ("non-enum sense", stat["site_rawsense"]))
    print("  %-25s: %d" % ("sense unparsable", stat["site_sense_unparsed"]))
    print("  %-25s: %d   (multi-bit, excluded by design)" % ("SetEventFlagValue", stat["site_value_write"]))
    print("  %-25s: %d" % ("bad arity", stat["site_bad_arity"]))
    print("rows: %d | distinct flags: %d | on: %d off: %d"
          % (len(rows), len({r[0] for r in rows}),
             len({r[0] for r in rows if r[1] == "on"}), len({r[0] for r in rows if r[1] == "off"})))
    if parse_failed:
        print("PARSE FAILURES (%d):" % len(parse_failed))
        for nm, e in parse_failed[:5]:
            print("    %s: %s" % (nm, e))

    if not rows:
        sys.exit("FATAL: zero SetEventFlag rows -- the decompiler vocabulary moved. Nothing written.")
    if parse_failed:
        sys.exit("FATAL: %d file(s) failed to parse -- a partial corpus silently SHRINKS this oracle, "
                 "and a shrinking oracle stops protecting you quietly. Nothing written."
                 % len(parse_failed))

    # F4: the floor SCALES with corpus size. A flat 2000 fired on correct code -- it made --pyfile mode
    # unreachable and reported "BROKEN PARSE" about a clean parse of a single 40-site ESD.
    # D2: floor / sense / cross-check are CORPUS-LEVEL claims. In --pyfile mode a single ESD legitimately
    # has ~6-60 sites, one sense, and no gate hits, so enforcing them there FATALs on correct input
    # (235/365 files trip the floor alone). Single-file mode is a probe: warn, never exit.
    corpus = not pyfile_mode
    def fail(msg):
        if corpus:
            sys.exit("FATAL: " + msg)
        print("WARNING (--pyfile, corpus-level check not applicable): " + msg)

    floor = max(5, int(6 * stat["files"]))
    if corpus and stat["site_literal"] < floor:
        sys.exit("FATAL: %d literal sites over %d file(s) (floor %d) -- reads like a BROKEN PARSE, not "
                 "a smaller corpus. Nothing written." % (stat["site_literal"], stat["files"], floor))
    # F4, converse half: the floor guards VOLUME only. These guard SHAPE, which volume cannot see.
    if {r[3] for r in rows} == {"?"}:
        sys.exit("FATAL: every map_id is '?' -- the corpus layout moved. Nothing written.")
    if len({r[1] for r in rows}) < 2:
        fail("only one sense present -- FlagState parsing is inverted or collapsed. Nothing written.")

    xc = crosscheck(rows, REPO)
    print("\nCROSS-CHECK (computed, not asserted):")
    if "msb" in xc:
        print("  esd INTERSECT msb_flag_region (%d): %d" % (xc["msb"], xc["msb_hit"]))
        print("  esd INTERSECT corpse          (%d): %d" % (xc["corpse"], xc["corpse_hit"]))
    if "lots" in xc:
        print("  esd INTERSECT flag_lots       (%d): %d" % (xc["lots"], xc["lots_hit"]))
    if "gates" in xc:
        print("  esd INTERSECT lot_gates gate  (%d): %d  <- POSITIVE CONTROL" % (xc["gates"], xc["gates_hit"]))
        print("     %s" % xc.get("gates_hits"))
    # The consumer's invariant: an ESD-set flag that IS a pickup acquisition flag would break the
    # three-legged model this table encodes. Fail loudly rather than emit a table nobody re-checks.
    if xc.get("msb_hit") or xc.get("corpse_hit"):
        # Disjointness stays FATAL even for --pyfile: an overlap is a MODEL break wherever it shows up.
        sys.exit("FATAL: %d msb / %d corpse overlap -- the DISJOINTNESS this table is built on no "
                 "longer holds. That is a model change, not a number to update. Nothing written."
                 % (xc.get("msb_hit", 0), xc.get("corpse_hit", 0)))
    if "gates_hit" in xc and xc["gates_hit"] == 0:
        fail("positive control EMPTY -- 0 of %d lot_gates gate_flags are ESD-set. The zeroes above are "
             "then unfalsifiable and this table is not evidence of anything." % xc["gates"])

    if args.probe:
        print("\n--probe: nothing written.")
        return

    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/datamine_esd_flags.py -- DO NOT EDIT, re-emit.\n")
        fh.write("# Every event flag an NPC talk ESD SETS = the NPC-STATE flag vocabulary.\n")
        fh.write("# JOIN KEY, NOT A VERDICT. The chain is: ESD sets -> EMEVD tests -> treasure\n")
        fh.write("# enabled/disabled. Join gate_flag in lot_gates.tsv against this to tell an\n")
        fh.write("# NPC-STATE gate from a world/progression gate.\n")
        fh.write("# MEASURED THIS RUN (recomputed on every emit; the tool hard-fails if the\n")
        fh.write("# disjointness breaks or the positive control goes empty):\n")
        fh.write("#   esd flags %d | msb_flag_region %d/%d | corpse %d/%d | flag_lots %d/%d\n"
                 % (xc["esd"], xc.get("msb_hit", -1), xc.get("msb", -1),
                    xc.get("corpse_hit", -1), xc.get("corpse", -1),
                    xc.get("lots_hit", -1), xc.get("lots", -1)))
        fh.write("#   POSITIVE CONTROL: %d/%d lot_gates gate_flags are ESD-set\n"
                 % (xc.get("gates_hit", -1), xc.get("gates", -1)))
        fh.write("# how: literal | arg (call-graph resolved) | argsum (const+param step ladder)\n")
        fh.write("#      | conditional (SetEventFlagIf)\n")
        fh.write("flag\tsense\ttalk_id\tmap_id\thow\n")
        for r in sorted(rows):
            fh.write("%d\t%s\t%s\t%s\t%s\n" % r)
    print("\nwrote %s (%d rows)" % (args.out, len(rows)))


if __name__ == "__main__":
    main()
