#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_questline_conditions.py -- the QUESTLINE-CONDITION EXTRACTOR (er-archipelago #1085).

Per AWARD SITE in the decompiled EMEVD + talk-ESD corpus, resolve the guard condition cone down to
ROOTS (BOSS_KILL / ITEM_POSSESSION / MAP_ACCESS / DIALOGUE_STEP / NPC_STATE / REGION_ACCESS /
COUNT_FLAGS / ...) and emit a synthesized access rule. Phase 2 (2026-08-27) resolves cones
PER BRANCH: `else` arms are negated, talk-list menu entries carry the condition they were
registered under, and item consumption is PATH-scoped. Nine acceptance fixtures live in
`extract_questline_conditions_fixtures.py`; the phase-2 report is the issue thread on #1085.

    python tools/extract_questline_conditions.py ARTIFACTS_DIR -o OUTDIR
    python tools/extract_questline_conditions.py ARTIFACTS_DIR --dag-corpus greenfield/questline_conditions.tsv

ARTIFACTS_DIR is the directory produced by `python3 tools/gen_inputs.py --ensure
elden_ring_artifacts`: event/*.emevd.dcx.js, event/common_func.emevd.dcx.js, talk/**/t*.py and
vanilla_er/**/ItemLotParam_*.csv. Those artifacts are licensing-restricted and are NOT in CI, which
is why the corpus this tool emits is COMMITTED and this tool is not run by any gate -- the same
shape `tools/datamine_flag_names.py` / `greenfield/flag_names.tsv` already have (AGENTS §5).

WHAT `--dag-corpus` IS FOR. `tools/build_questline_dag.py` (SPEC-questline-dag-20260728) built its
graph from three AWARD-SITE corpora, and §9a records what that cost: 117 of 283 edges placed their
source NOWHERE, and f510110 (Fortissax) was asserted ABSENT because an award-site corpus cannot see
a gate on whether the FIGHT EXISTS. This mode emits one row per (award site, cone root) with the
root's SETTER cited, which is exactly what those two gaps were missing. It is a CORPUS, not a
verdict: the builder decides which rows become edges, and this file's own limits ride along in the
`designation` / `cone_completeness` / `disjunctive` columns rather than being filtered away here.

🛑 HONESTY, unchanged from phase 1: zero EMEVD/ESD sites for a thing is NOT evidence of "no gate" --
ObjAct / MSB / ChrActivateConditionParam / ceremony / shop-lineup gating is outside this corpus
ENTIRELY. UNRESOLVED is a first-class outcome and is never papered over. A cone with no roots means
"no gate visible here", never "no gate".

🛑 THE CONE IS AN OVER-APPROXIMATION. Roots from the arms of a disjunction are unioned into one
conjunction (`disjunctive=Y` marks the sites where the SITE guards contain an `||`; a disjunction
met further down a setter chain is not marked at all). So no consumer may read a site's roots as a
proven AND -- see the `group_semantics` argument in build_questline_dag.py.
"""
import re, os, sys, csv, json, heapq
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esd_ast   # phase 2: per-branch ESD slicing (ast-based)

AWARD_VERBS_EMEVD = ("AwardItemLot", "DirectlyGivePlayerItem",
                     "AwardItemsIncludingClients", "GrantItemsToPlayer", "AwardGesture")
AWARD_RE_EMEVD = re.compile(r'\b(' + "|".join(AWARD_VERBS_EMEVD) + r')\s*\(([^;]*)\)\s*;')
CALL_RE = re.compile(r'(!?)\s*\b([A-Za-z_]\w*)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)')

SESSION_PREDS = {
    "PlayerIsInOwnWorld", "HasMultiplayerState", "ThisEventSlot", "OnlineMode",
    "CharacterType", "IsClient", "EventFlagState", "ELSE_BRANCH",
}
NON_PREDICATE = {"InitializeEvent", "InitializeCommonEvent", "Event", "Goto", "Label",
                 "Signed", "WaitFixedTimeSeconds", "WaitFixedTimeFrames",
                 # python/decompiler syntax picked up by the call regex
                 "not", "or", "and", "if", "Loop", "print", "int", "len"}
BOSS_PREDS = {"CharacterDead", "CharacterRatioDead", "CharacterHPValue"}
# ESD/EMEVD forms that are presentation or state-machine plumbing, not access gates.
# Listed EXPLICITLY (not dropped silently) and counted in the report.
NOISE_PREDS = {
    "GetCurrentStateElapsedTime", "GetCurrentStateElapsedFrames", "ElapsedSeconds",
    "GetWhetherChrEventAnimHasEnded", "DoesSelfHaveSpEffect", "CharacterHasSpEffect",
    "GetDistanceToPlayer", "CheckSpecificPersonTalkHasEnded",
    "CheckSpecificPersonGenericDialogIsOpen", "IsClientPlayer", "IsPlayerDead",
    # phase 2: per-branch slicing reaches the ESD menu loops, whose
    # `assert not (CheckSpecificPersonMenuIsOpen(1, 0) and not ...)` spin is
    # presentation plumbing, not an access gate.
    "CheckSpecificPersonMenuIsOpen", "ClearPreviousMenuSelection",
    "GetOneLineHelpStatus", "SignedAlt", "Signed", "Done", "Get", "Set",
    "IsCharacterDisabled", "GetChrDeadState", "IsAttackedBySpecificPerson",
    "HasSpEffectId",
}
DIALOGUE_CHOICE_PREDS = {"GetTalkListEntryResult", "GetTalkListEntryResultForGoods",
                         "CheckActionButtonArea", "GetPlayerMenuIsOpen"}
REGION_PREDS = {"InArea", "PlayerInMap", "ActionButtonInArea", "EntityInRadiusOfEntity",
                "PlayerInArea", "InsideMapArea", "EntityInRadiusOfEntityRegion"}
ITEM_PREDS = {"PlayerHasItemIncludingBBox", "PlayerHasItem", "ComparePlayerInventoryNumber"}


def split_args(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "," and depth == 0:
            out.append(cur.strip()); cur = ""; continue
        if ch in "([": depth += 1
        elif ch in ")]": depth -= 1
        cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def is_int(s):
    try: int(s); return True
    except Exception: return False


EVENT_HDR = re.compile(r'^\$Event\((\d+),\s*(\w+),\s*function\(([^)]*)\)\s*\{')


class Ev:
    __slots__ = ("file", "eid", "params", "lines", "comment")
    def __init__(s, file, eid, params, lines, comment):
        s.file, s.eid, s.params, s.lines, s.comment = file, eid, params, lines, comment


def parse_emevd(path, fname):
    txt = open(path, encoding="utf-8", errors="replace").read().splitlines()
    events, i, last_comment = {}, 0, ""
    while i < len(txt):
        line = txt[i]
        if line.startswith("//"):
            last_comment = line.lstrip("/ ").strip()
        m = EVENT_HDR.match(line)
        if not m:
            i += 1; continue
        eid = m.group(1)
        params = [p.strip() for p in m.group(3).split(",") if p.strip()]
        body, j, depth = [], i + 1, 1
        while j < len(txt):
            depth += txt[j].count("{") - txt[j].count("}")
            if depth <= 0:
                break
            body.append(txt[j]); j += 1
        events[eid] = Ev(fname, eid, params, body, last_comment)
        last_comment = ""
        i = j + 1
    return events


def logical_lines(lines):
    buf, ind = "", 0
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if not buf:
            ind = len(raw) - len(raw.lstrip())
        buf = (buf + " " + s).strip() if buf else s
        if buf.count("(") <= buf.count(")"):
            yield ind, buf
            buf = ""
    if buf:
        yield ind, buf


GUARD_OPEN = re.compile(r'^(?:\}\s*)?(?:else\s+)?if\s*\((.*)\)\s*\{$')
WAITFOR = re.compile(r'^WaitFor\((.*)\);$')
ENDIF = re.compile(r'^(EndIf|RestartIf|TerminateIf)\((.*)\);$')
CONDVAR = re.compile(r'^(\w+)\s*(\|=|&=|=)\s*(.*);$')


def inline_vars(expr, condvars):
    for k, v in condvars.items():
        expr = re.sub(r'\b%s(?:\.Passed)?\b' % re.escape(k), "(%s)" % v, expr)
    return expr


def guarded_statements(ev):
    """Yield (stmt, guards, saw_control_flow). guards = [(polarity, expr)]."""
    stack, seq, condvars = [], [], {}
    saw_cf = False
    for ind, s in logical_lines(ev.lines):
        while stack and ind <= stack[-1][0]:
            stack.pop()
        m = GUARD_OPEN.match(s)
        if m:
            stack.append((ind, True, inline_vars(m.group(1), condvars)))
            continue
        if s.startswith("}") or s.startswith("else"):
            if s.startswith("} else") or s.startswith("else"):
                stack.append((ind, True, "ELSE_BRANCH()"))
            continue
        m = WAITFOR.match(s)
        if m:
            seq.append((True, inline_vars(m.group(1), condvars))); continue
        m = ENDIF.match(s)
        if m:
            seq.append((False, inline_vars(m.group(2), condvars))); continue
        if s.startswith("GotoIf") or s.startswith("SkipIf") or s.startswith("Goto("):
            saw_cf = True
            continue
        m = CONDVAR.match(s)
        if m and not re.match(r'^[A-Z]', s):
            name, op, rhs = m.groups()
            rhs = inline_vars(rhs, condvars)
            if op == "=" or name not in condvars:
                condvars[name] = rhs
            elif op == "&=":
                condvars[name] = "(%s) && (%s)" % (condvars[name], rhs)
            else:
                condvars[name] = "(%s) || (%s)" % (condvars[name], rhs)
            continue
        guards = list(seq) + [(p, c) for (_i, p, c) in stack]
        yield s, guards, saw_cf


class Atom:
    __slots__ = ("pred", "args", "neg")
    def __init__(s, pred, args, neg):
        s.pred, s.args, s.neg = pred, args, neg
    def key(s):
        return ("!" if s.neg else "") + s.pred + "(" + ",".join(s.args) + ")"
    def __repr__(s): return s.key()


def atoms_of(expr, neg=False):
    out = []
    for m in CALL_RE.finditer(expr):
        bang, pred, argtxt = m.group(1), m.group(2), m.group(3)
        if pred in NON_PREDICATE:
            continue
        pre = expr[:m.start()].rstrip()
        n = bool(bang) or pre.endswith("!")
        out.append(Atom(pred, split_args(argtxt), n != neg))
    return out


def has_or(expr):
    return "||" in expr or " or " in expr


class Corpus:
    def __init__(self, art):
        self.art = art
        self.events = {}
        self.calls = defaultdict(list)
        edir = os.path.join(art, "event")
        for fn in sorted(os.listdir(edir)):
            if not fn.endswith(".js"): continue
            self.events[fn] = parse_emevd(os.path.join(edir, fn), fn)
        INIT = re.compile(r'\$Initialize(Common)?Event\(\s*[^,]+,\s*(\d+)\s*(?:,([^;]*))?\)')
        for fn, evs in self.events.items():
            for eid, ev in evs.items():
                for ln in ev.lines:
                    for m in INIT.finditer(ln):
                        common, target, argtxt = m.group(1), m.group(2), m.group(3) or ""
                        args = [a for a in split_args(argtxt.rstrip(")").rstrip()) if a]
                        key = ("common_func.emevd.dcx.js" if common else fn, target)
                        self.calls[key].append((fn, eid, args))
        self.lot_flag, self.lot_item = {}, {}
        vdir = None
        for root, dirs, files in os.walk(os.path.join(art, "vanilla_er")):
            if "ItemLotParam_map.csv" in files:
                vdir = root; break
        if vdir:
            for f in ("ItemLotParam_map.csv", "ItemLotParam_enemy.csv"):
                p = os.path.join(vdir, f)
                if not os.path.exists(p): continue
                for row in csv.DictReader(open(p, encoding="utf-8", errors="replace")):
                    fid = row.get("getItemFlagId") or "0"
                    if fid and fid != "0":
                        self.lot_flag[row["ID"]] = int(fid)
                    self.lot_item[row["ID"]] = row.get("lotItemId01", "")
        self.esd = {}            # (rel, machine) -> source lines
        self.esd_params = {}
        self.esd_stmts = {}      # (rel, machine) -> [(stmt text, path guards)]
        self.esd_callers = defaultdict(list)
        self._ctx_memo = {}
        self.esd_entry_cond = {}   # (rel, machine, entry idx) -> [cond, ...]
        self.esd_workval = {}      # (rel, machine) -> {idx: literal or None}
        troot = os.path.join(art, "talk")
        self.esd_no_machines = []
        self._pending_entry = []
        self.arming_flags = set()
        for root, _d, files in os.walk(troot):
            for f in sorted(files):
                if not f.endswith(".py"): continue
                p = os.path.join(root, f)
                txt = open(p, encoding="utf-8", errors="replace").read()
                rel = os.path.relpath(p, troot)
                machines = esd_ast.parse_esd_file(rel, txt)
                if not machines:
                    # empty or machine-less talk file (m10_00 t334011000.py is a
                    # 1-line stub); recorded, not a parse error
                    self.esd_no_machines.append(rel); continue
                for name, m in machines.items():
                    wv = {}
                    for idx, vals in m.workvals.items():
                        wv[idx] = (vals.pop() if len(vals) == 1 and
                                   next(iter(vals)).lstrip("-").isdigit() else None)
                        vals.add(wv[idx])
                    self.esd_workval[(rel, name)] = wv
                    self.esd[(rel, name)] = m.lines
                    self.esd_params[(rel, name)] = m.params
                    self.esd_stmts[(rel, name)] = [
                        (t, [(pol, self.sub_workval(rel, name, e))
                             for (pol, e) in g]) for (t, g) in m.stmts]
                    self._pending_entry.append((rel, name))
                    for (callee, guards, kw) in m.calls:
                        if (rel, callee) in self.esd or callee in machines:
                            self.esd_callers[(rel, callee)].append(
                                (name, [(pol, self.sub_workval(rel, name, e))
                                        for (pol, e) in guards], kw))
                for m2 in machines.values():
                    for conds in m2.registers.values():
                        for c in conds:
                            for fm in re.finditer(r'GetEventFlag\((\d+)\)', c):
                                self.arming_flags.add(int(fm.group(1)))
                for (mach, idx), conds in esd_ast.entry_conditions(machines).items():
                    self.esd_entry_cond[(rel, mach, idx)] = conds
                # Attach menu-entry availability IN THE MACHINE THAT BRANCHES on
                # GetTalkListEntryResult(), before any caller inherits those
                # guards -- the flag setter is usually 2 machines further down
                # (Fia: _x33 branches, _x35 calls _x87 which sets f12039157).
                for (r2, n2) in self._pending_entry:
                    self.esd_stmts[(r2, n2)] = [
                        (t, self.attach_entries(r2, n2, g))
                        for (t, g) in self.esd_stmts[(r2, n2)]]
                for k, lst in self.esd_callers.items():
                    if k[0] != rel: continue
                    self.esd_callers[k] = [
                        (n, self.attach_entries(rel, n, g), kw) for (n, g, kw) in lst]
                self._pending_entry = []

    def attach_entries(self, rel, mach, guards):
        """`GetTalkListEntryResult() == N` is reachable only if entry N was
        OFFERED.  Availability is resolved at MACHINE scope (see
        esd_ast.entry_conditions): the nearest registering machine in the
        intra-file call graph, callees first.  Fia `t322001203_x33` entry 6 =
        "Give Cursemark of Death", offered iff f12039176 (registered by _x45,
        t322001203:968)."""
        extra = []
        for (pol, expr) in guards:
            if not pol:
                continue
            for m in re.finditer(r'GetTalkListEntryResult\(\)\s*==\s*(\d+)', expr):
                conds = self.esd_entry_cond.get((rel, mach, int(m.group(1))))
                if conds and conds != ["True"]:
                    extra.append((True, " || ".join("(%s)" % c for c in conds)))
        return list(guards) + extra

    def sub_workval(self, rel, mach, expr):
        """SetWorkValue/GetWorkValue dataflow, INTRA-machine only.  A read with
        no unique literal write in the same machine becomes
        WORKVALUE_UNRESOLVED(i) -- an UNRESOLVED root, never a guess.  Talk
        work values are also written by the EMEVD/ceremony side, which this
        corpus does not connect, so cross-machine reads stay unresolved."""
        if "GetWorkValue" not in expr:
            return expr
        wv = self.esd_workval.get((rel, mach), {})
        def rep(m):
            i = m.group(1)
            v = wv.get(int(i)) if i.isdigit() else None
            return v if v is not None else "WORKVALUE_UNRESOLVED(%s)" % i
        return re.sub(r'GetWorkValue\((\w+)\)', rep, expr)

    def esd_contexts(self, rel, mach, depth=0, seen=None):
        """[(bind, inherited_guards)] for a machine, <=3 hops up the ESD call
        graph.  Always includes the empty context so a machine that is never
        called is still analysed (its params then stay symbolic -> UNRESOLVED)."""
        seen = seen or frozenset()
        if depth > 2 or (rel, mach) in seen:
            return [({}, [])]
        ck = (rel, mach, depth)
        if depth == 0 and ck in self._ctx_memo:
            return self._ctx_memo[ck]
        seen = seen | {(rel, mach)}
        out = []
        for (caller, cg, kw) in self.esd_callers.get((rel, mach), [])[:(24 if depth == 0 else 3)]:
            for (cbind, cinh) in self.esd_contexts(rel, caller, depth + 1, seen):
                g = [(p, subst(e, cbind)) for (p, e) in cg] + cinh
                bind = {k: subst(v, cbind) for k, v in kw.items()}
                out.append((bind, g))
        out = out or [({}, [])]
        out = out[:(24 if depth == 0 else 6)]
        if depth == 0:
            self._ctx_memo[ck] = out
        return out

    def resolve_args(self, ev):
        if not ev.params:
            return [(ev.file, ev.eid, {})]
        sites = self.calls.get((ev.file, ev.eid), [])
        out = []
        for (cf, ce, args) in sites:
            out.append((cf, ce, dict(zip(ev.params, args))))
        return out or [(ev.file, ev.eid, {})]


def subst(expr, bind):
    if not bind: return expr
    return re.sub(r'\b[A-Za-z_]\w*\b', lambda m: bind.get(m.group(0), m.group(0)), expr)


SET_RE = re.compile(r'^Set(?:Networkconnected)?EventFlagID\(\s*([^,]+),\s*(ON|OFF)\s*\);$')
BATCH_OFF = re.compile(r'^BatchSet(?:Networkconnected)?EventFlags\(\s*([^,]+),\s*([^,]+),\s*OFF\s*\);$')


class Setter:
    __slots__ = ("file", "eid", "guards", "kind")
    def __init__(s, file, eid, guards, kind):
        s.file, s.eid, s.guards, s.kind = file, eid, guards, kind


CONSUME_RE = re.compile(r'PlayerEquipmentQuantityChange\(ItemType\.Goods,\s*(\d+),\s*-\d+\)')
POSSESS = ("ComparePlayerInventoryNumber(ItemType.Goods, %s, "
           "CompareType.GreaterOrEqual, 1, False)")


def path_consumes(stmts):
    """[(guard prefix, goods id)] for every item CONSUMPTION in a machine.

    A machine that takes an item cannot have run without it, so a consumption
    is a possession requirement -- but only for statements on the SAME PATH.
    v1 applied the machine's consumptions to every statement in it; with
    per-branch slicing we can require the consumption's guard stack to be a
    PREFIX of the statement's, which is what makes goods 8100 a requirement of
    the `# lot:100200` award in `t304001000_x43` (both under
    `GetTalkListEntryResult() == 1`) without leaking it onto the entry-2 arm."""
    out = []
    for (stmt, g) in stmts:
        for m in CONSUME_RE.finditer(stmt):
            out.append((list(g), m.group(1)))
    return out


def consume_reqs(consumes, guards):
    gs = [tuple(x) for x in guards]
    out = []
    for (cg, gid) in consumes:
        cgt = [tuple(x) for x in cg]
        if all(x in gs for x in cgt):
            out.append((True, POSSESS % gid))
    return out


def build_setters(C):
    setters = defaultdict(list)
    boss_flags, band_flags = set(), set()
    for fn, evs in C.events.items():
        for eid, ev in evs.items():
            binds = C.resolve_args(ev)
            is_boss_ev = any("HandleBossDefeatAndDisplayBanner" in l for l in ev.lines)
            for stmt, guards, cf in guarded_statements(ev):
                m = SET_RE.match(stmt)
                if not m or m.group(2) != "ON":
                    continue
                target = m.group(1).strip()
                # Every concrete call site is evidence.  This used to stop at 12, which
                # silently discarded setters for heavily reused common functions (for
                # example 90005300 has 252 bindings).  Resolver-side fan-out remains
                # explicitly bounded; source discovery must be complete and measured.
                for (cfile, ceid, bind) in binds:
                    t = subst(target, bind)
                    if not is_int(t):
                        continue
                    f = int(t)
                    g = [(p, subst(e, bind)) for (p, e) in guards]
                    kind = "SET"
                    if is_boss_ev or any(a.pred in BOSS_PREDS
                                         for (_p, e) in g for a in atoms_of(e)):
                        kind = "BOSS"; boss_flags.add(f)
                    setters[f].append(Setter(fn, eid, g, kind))
            pend = None
            for _ind, s in logical_lines(ev.lines):
                mb = BATCH_OFF.match(s)
                if mb and is_int(mb.group(1)) and is_int(mb.group(2)):
                    pend = (int(mb.group(1)), int(mb.group(2))); continue
                ms = SET_RE.match(s)
                if ms and ms.group(2) == "ON" and pend and is_int(ms.group(1)):
                    f = int(ms.group(1))
                    if pend[0] <= f <= pend[1]:
                        band_flags.add(f)
                    pend = None
    for (rel, mach), lines in C.esd.items():
        ctxs = C.esd_contexts(rel, mach)[:24]
        consumes = path_consumes(C.esd_stmts[(rel, mach)])
        for stmt, guards0 in C.esd_stmts[(rel, mach)]:
            guards0 = list(guards0) + consume_reqs(consumes, guards0)
            for (bind, inh) in ctxs:
                st = subst(stmt, bind)
                guards = [(p, subst(e, bind)) for (p, e) in guards0] + inh
                for m in re.finditer(r'SetEventFlag\(\s*(\d+),\s*FlagState\.On\s*\)', st):
                    setters[int(m.group(1))].append(Setter("talk/" + rel, mach, guards, "ESD"))
                for m in re.finditer(r'SetEventFlagIf\(\s*(.*?),\s*(\d+),\s*FlagState\.On\s*\)', st):
                    setters[int(m.group(2))].append(
                        Setter("talk/" + rel, mach, guards + [(True, m.group(1))], "ESD"))
    return setters, boss_flags, band_flags


MAX_DEPTH = 8            # flag-expansion hops from the award site
DIALOGUE_LIMIT = 2       # extra hops allowed INSIDE one talk-ESD questline chain
SITE_BUDGET = 90         # flags visited per award site before we stop and say so
RUNE_BAND = (190, 199)


class Resolver:
    """Per-award-site, budgeted, breadth-first expansion of the guard cone.

    Design note (why not a full transitive closure): an UNBOUNDED closure over
    flag setters swallows the whole game -- the first prototype resolved the
    Fortissax remembrance into 140 roots including the tutorial ESD, because
    every NPC-state flag is written by a manager event that also reads a dozen
    unrelated flags.  So expansion is TYPED and BOUNDED: roots are terminal,
    boss flags expand one hop (their handler can itself be gated), NPC-state
    band flags expand along the band DAG, dialogue flags expand inside their
    own ESD, and everything else expands only if it has <= 4 setters.
    """

    MAP_RE = re.compile(r'(m\d\d_\d\d)')

    def __init__(self, C, setters, boss_flags, band_flags):
        self.C, self.setters = C, setters
        self.boss_flags, self.band_flags = boss_flags, band_flags
        self.negatives = Counter()
        self.noise = Counter()

    def map_root(self, fname):
        m = self.MAP_RE.search(fname)
        return {"MAP_ACCESS(%s)" % m.group(1)} if m else set()

    def add_root(self, root, cite=""):
        """Record a root AND where it was read/set.

        The citation is the whole reason build_questline_dag.py can place an extractor edge's
        source: SPEC-questline-dag §9a's largest recorded gap is that 117 of 283 tier-1 edges
        place their source NOWHERE. FIRST-WINS and never overwritten -- the first sighting is the
        one at the smallest cone depth (the walk is breadth-first by (depth, dialogue depth)), so
        a later, deeper sighting is a worse citation, not a better one.
        """
        self.roots.add(root)
        if cite and root not in self.cites:
            self.cites[root] = cite

    def add_roots(self, roots, cite=""):
        for r in roots:
            self.add_root(r, cite)

    # ---- per-site state ------------------------------------------------
    def resolve(self, guards, site_file=None):
        self.roots, self.unres = set(), set()
        self.cites = {}
        self.site_file = site_file or ""
        self.armed = 0
        self.seen_flags, self.visits = set(), 0
        if site_file:
            self.add_roots(self.map_root(site_file), site_file)
        self.q, self.seq = [], 0
        for (pol, expr) in guards:
            self.walk_expr(expr, pol, 0, 0)
        # BREADTH-FIRST by (depth, dialogue depth): with a per-site flag budget
        # a depth-first walk spends the whole budget in the first sprawling
        # subtree it enters and never reaches a shallow sibling.  That is how
        # f12030800 (Champions, 1 hop off the Fortissax cone) went missing.
        while self.q:
            _d, _g, _n, f, depth, dlg, dfile = heapq.heappop(self.q)
            self.expand_flag(f, depth, dlg, dfile)
        return set(self.roots), set(self.unres)

    def walk_expr(self, expr, pol, depth, dlg=0, dlg_file=None):
        for a in atoms_of(expr):
            eff_neg = (a.neg != (not pol))
            if eff_neg:
                # "not already done" self-gate; a requirement to keep something
                # OFF is never an access requirement.  Recorded, not expanded.
                self.negatives[a.key()] += 1
                continue
            self.walk_atom(a, depth, dlg, dlg_file)

    def walk_atom(self, a, depth, dlg=0, dlg_file=None):
        p, args = a.pred, a.args
        if p in SESSION_PREDS:
            return
        if p in NOISE_PREDS or re.match(r'^t\d+(_x\d+)?$', p):
            self.noise[p] += 1
            return
        if p in DIALOGUE_CHOICE_PREDS:
            self.add_root("DIALOGUE_CHOICE(%s)" % p, self.site_file); return
        if p in ("EventFlag", "GetEventFlag") and args and is_int(args[0]):
            self.walk_flag(int(args[0]), depth, dlg, dlg_file); return
        if p in ("AnyBatchEventFlags", "AllBatchEventFlags") and len(args) >= 2 \
                and is_int(args[0]) and is_int(args[1]):
            lo, hi = int(args[0]), int(args[1])
            if hi - lo > 24:
                self.add_root("FLAG_BAND(%d-%d)" % (lo, hi), self.site_file); return
            for f in range(lo, hi + 1):
                if self.setters.get(f) or f in self.band_flags:
                    self.walk_flag(f, depth, dlg, dlg_file)
            return
        if p == "CountEventFlags":
            if len(args) >= 3:
                self.add_root("COUNT_FLAGS(%s-%s)" % (args[1], args[2]), self.site_file)
            else:
                self.unres.add(a.key())
            return
        if p in ITEM_PREDS:
            gid = None
            if p == "ComparePlayerInventoryNumber" and len(args) >= 2 and is_int(args[1]):
                gid = args[1]
            else:
                for x in args:
                    if is_int(x): gid = x; break
            self.add_root("ITEM_POSSESSION(goods %s)" % gid, self.site_file); return
        if p in BOSS_PREDS:
            self.add_root("BOSS_KILL(entity %s)" % (args[0] if args else "?"), self.site_file); return
        if p in REGION_PREDS:
            self.add_root("REGION_ACCESS(%s %s)" % (p, ",".join(args[:2])), self.site_file); return
        self.unres.add(a.key())

    def walk_flag(self, f, depth, dlg=0, dlg_file=None):
        if f in self.seen_flags:
            return
        self.seen_flags.add(f)
        self.seq += 1
        heapq.heappush(self.q, (depth, dlg, self.seq, f, depth, dlg, dlg_file))

    def expand_flag(self, f, depth, dlg=0, dlg_file=None):
        self.visits += 1
        if self.visits > SITE_BUDGET:
            self.unres.add("BUDGET_EXCEEDED(f%d)" % f); return
        if depth > MAX_DEPTH:
            self.unres.add("DEPTH_CAP(f%d)" % f); return
        sets = self.dedupe(self.setters.get(f, []))
        if f in self.C.arming_flags and sets and all(s.kind == "ESD" for s in sets):
            # A menu-entry ARMING flag (one that appears inside an
            # AddTalkListDataIf condition) is a derived VARIABLE recomputed by
            # the machine's own bookkeeping every time the menu opens -- Fia's
            # _x43 clears 12039170..12039176 and _x46/_x47 re-set them.  It is
            # not a questline state, so it is INLINED (its setter guards are
            # substituted for it) rather than emitted as a DIALOGUE_STEP root.
            self.armed += 1
            for s2 in sets[:4]:
                for (pol, expr) in s2.guards:
                    self.walk_expr(expr, pol, depth, dlg, dlg_file or s2.file)
            return
        if RUNE_BAND[0] <= f <= RUNE_BAND[1]:
            self.add_root("GREAT_RUNE_FLAG(f%d)" % f, self.cite_of(sets)); return
        if f in self.boss_flags:
            self.add_root("BOSS_KILL(f%d)" % f, self.cite_of(sets))
            limit = 1                       # the handler itself can be gated
        elif f in self.band_flags:
            self.add_root("NPC_STATE(f%d)" % f, self.cite_of(sets))
            limit = MAX_DEPTH               # walk the band DAG
        elif sets and all(s.kind == "ESD" for s in sets):
            # A dialogue-progress flag chain inside talk ESD is ONE questline
            # (Fia: 12039157 <- 12039170 <- 12039161 <- possession of goods
            # 8191).  Those hops get their own budget instead of consuming the
            # main depth, because a menu-driven questline is arbitrarily many
            # dialogue steps deep while still being a single access fact.
            self.add_root("DIALOGUE_STEP(f%d @ %s)" % (f, sets[0].file), self.cite_of(sets))
            same = [x for x in sets if dlg_file is None or x.file == dlg_file]
            if dlg < DIALOGUE_LIMIT and same:
                for s2 in same[:4]:
                    for (pol, expr) in s2.guards:
                        self.walk_expr(expr, pol, depth, dlg + 1, s2.file)
            elif dlg >= DIALOGUE_LIMIT and same:
                self.unres.add("DIALOGUE_DEPTH_CAP(f%d)" % f)
            return
        elif not sets:
            self.unres.add("UNSET_FLAG(f%d)" % f); return
        elif len(sets) > 4:
            self.unres.add("MANY_SETTERS(f%d,n=%d)" % (f, len(sets))); return
        else:
            limit = MAX_DEPTH
        if depth >= limit:
            return
        for s in sets[:4]:
            if depth <= 1 and dlg == 0:
                self.add_roots(self.map_root(s.file), s.file)
            for (pol, expr) in s.guards:
                self.walk_expr(expr, pol, depth + 1, 0, None)

    @staticmethod
    def cite_of(sets):
        """`file:event` of the setter a flag root was named from. Empty when nothing set it."""
        return "%s:%s" % (sets[0].file, sets[0].eid) if sets else ""

    @staticmethod
    def dedupe(sets):
        out, seen = [], set()
        for s in sets:
            k = (s.file, tuple(g[1] for g in s.guards))
            if k in seen: continue
            seen.add(k); out.append(s)
        return out


def spawn_gates(C):
    """entity -> set(flag) : DisableCharacter(E) held until a flag/band turns ON.
    Reads the WaitFor that follows the disable in the same guard block
    (m12_03:12030700 -> WaitFor(AnyBatchEventFlags(4128, 4129)) for Fia's
    deathbed body 12030702, bound at the $InitializeEvent call site)."""
    out = defaultdict(set)
    for fn, evs in C.events.items():
        for eid, ev in evs.items():
            binds = C.resolve_args(ev)
            pending = None
            for _ind, stmt in logical_lines(ev.lines):
                m = re.match(r'^DisableCharacter\(([^,)]+)\);$', stmt)
                if m:
                    pending = m.group(1).strip(); continue
                m = WAITFOR.match(stmt)
                if m and pending:
                    for (_cf, _ce, bind) in binds:
                        ent = subst(pending, bind)
                        if not is_int(ent):
                            continue
                        for a in atoms_of(subst(m.group(1), bind)):
                            if a.neg:
                                continue
                            if a.pred == "EventFlag" and a.args and is_int(a.args[0]):
                                out[int(ent)].add(int(a.args[0]))
                            elif a.pred in ("AnyBatchEventFlags", "AllBatchEventFlags") \
                                    and len(a.args) >= 2 and is_int(a.args[0]) \
                                    and int(a.args[1]) - int(a.args[0]) <= 24:
                                out[int(ent)].update(range(int(a.args[0]), int(a.args[1]) + 1))
                    pending = None
    return out


def band_edges(C, setters, band_flags):
    """NPC-state DAG: [(prereq_flags, target_flag, file, event)] for every
    band-manager transition (common.emevd $Event(4139): 4127 && 12030800 -> 4128)."""
    edges = []
    for f in sorted(band_flags):
        for s in setters.get(f, []):
            pre = set()
            for (pol, expr) in s.guards:
                for a in atoms_of(expr):
                    if pol and not a.neg and a.pred == "EventFlag" and a.args and is_int(a.args[0]):
                        pre.add(int(a.args[0]))
            edges.append((frozenset(pre), f, s.file, s.eid))
    return edges


def emevd_award_sites(C):
    for fn, evs in C.events.items():
        for eid, ev in evs.items():
            hits = [(s, g, cf) for (s, g, cf) in guarded_statements(ev)
                    if AWARD_RE_EMEVD.search(s)]
            if not hits:
                continue
            binds = C.resolve_args(ev)
            for (stmt, guards, cf) in hits:
                m = AWARD_RE_EMEVD.search(stmt)
                verb, argtxt = m.group(1), m.group(2)
                for (cfile, ceid, bind) in binds:
                    a = split_args(subst(argtxt, bind))
                    g = [(p, subst(e, bind)) for (p, e) in guards]
                    yield dict(file=(cfile if bind else fn), event=eid,
                               callsite=(ceid if bind else ""), verb=verb,
                               args=a, guards=g, cf=cf)


ESD_AWARD = re.compile(r'#\s*lot:(\d+)|DirectlyGivePlayerItem\(([^)]*)\)|'
                       r'PlayerEquipmentQuantityChange\(([^)]*)\)')


def esd_award_sites(C):
    for (rel, mach), lines in C.esd.items():
        ctxs = C.esd_contexts(rel, mach)[:24]
        consumes = path_consumes(C.esd_stmts[(rel, mach)])
        for stmt, guards0 in C.esd_stmts[(rel, mach)]:
          guards0 = list(guards0) + consume_reqs(consumes, guards0)
          for (bind, inh) in ctxs:
            stmt2 = subst(stmt, bind)
            guards = [(p, subst(e, bind)) for (p, e) in guards0] + inh
            m = ESD_AWARD.search(stmt2)
            if not m:
                continue
            if m.group(1):
                verb, args = "ESD_lot", [m.group(1)]
            elif m.group(2):
                verb, args = "DirectlyGivePlayerItem", split_args(m.group(2))
            else:
                args = split_args(m.group(3))
                if any(x.startswith("-") for x in args):
                    continue
                verb = "PlayerEquipmentQuantityChange"
            yield dict(file="talk/" + rel, event=mach, callsite="", verb=verb,
                       args=args, guards=guards, cf=False)


def designate(roots, unres):
    if unres:
        return "UNRESOLVED"
    if any(r.startswith(("NPC_STATE", "DIALOGUE_STEP")) for r in roots):
        return "MISSABLE"
    return "IN_LOGIC_RULE"


def rule_text(roots):
    if not roots:
        return "TRUE (no interpretable guard in this corpus)"
    return " AND ".join(sorted(roots))


def run(art, outdir="."):
    C = Corpus(art)
    setters, boss_flags, band_flags = build_setters(C)
    R = Resolver(C, setters, boss_flags, band_flags)
    rows, seen = [], set()
    for site in list(emevd_award_sites(C)) + list(esd_award_sites(C)):
        disj = any(has_or(e) for (_p, e) in site["guards"])
        roots, unres = R.resolve(site["guards"], site["file"])
        lot, flag = None, None
        for x in site["args"]:
            if is_int(x) and x in C.lot_flag:
                lot = x; flag = C.lot_flag[x]; break
        key = (site["file"], site["event"], site["callsite"], site["verb"],
               ",".join(site["args"]))
        if key in seen:
            continue
        seen.add(key)
        rows.append(dict(
            cites=dict(R.cites), roots=sorted(roots),
            file=site["file"], event=site["event"], callsite=site["callsite"],
            verb=site["verb"], args=",".join(site["args"]),
            lot=lot or "", flag=flag if flag else "",
            designation=designate(roots, unres),
            rule=rule_text(roots),
            disjunctive="Y" if disj else "",
            control_flow_skipped="Y" if site["cf"] else "",
            unresolved="; ".join(sorted(unres)[:8]),
        ))
    cols = ["file", "event", "callsite", "verb", "args", "lot", "flag",
            "designation", "rule", "disjunctive", "control_flow_skipped", "unresolved"]
    with open(os.path.join(outdir, "questline_conditions.tsv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    cnt = Counter(r["designation"] for r in rows)
    print("award sites: %d" % len(rows))
    for k, v in cnt.most_common():
        print("  %-14s %d" % (k, v))
    json.dump(dict(rows=rows, boss_flags=sorted(boss_flags),
                   band_flags=sorted(band_flags), counts=dict(cnt)),
              open(os.path.join(outdir, "_questline_state.json"), "w"))
    return C, R, rows



# ---- the DAG-facing corpus (--dag-corpus) -------------------------------------------------------
# ONE ROW PER (award site, cone root). The rule text in questline_conditions' `rule` column is for a
# human; this is the machine layer build_questline_dag.py joins on, and the difference that matters
# is the SETTER CITATION -- SPEC-questline-dag §9a's largest single gap ("117 of 283 edges place
# their source NOWHERE"), which the cone walk already knows and phase 1 threw away.
#
# 🛑 EVERY ROW IS EMITTED, INCLUDING THE ONES THE DAG WILL REFUSE. `designation` and
# `cone_completeness` ride along so the ADMISSION RULE lives in the consumer, where its keeper test
# can read it, instead of being a silent filter here. A filter with no tally is a lie (CONTRIBUTING
# rule 4), so the classes that are dropped are dropped ONCE, here, and counted in the header.
_DAG_ROOT_RE = re.compile(
    r'^(BOSS_KILL|NPC_STATE|DIALOGUE_STEP|GREAT_RUNE_FLAG)\(f(\d+)'
    r'|^ITEM_POSSESSION\(goods (\d+)\)$'
    r'|^MAP_ACCESS\((m\d\d_\d\d)\)$')
# Roots that name no addressable source. BOSS_KILL(entity N) is an ENTITY id, not an event flag --
# a DIFFERENT ID SPACE, and reading one as the other is CONTRIBUTING rule 3. REGION_ACCESS,
# COUNT_FLAGS, FLAG_BAND and DIALOGUE_CHOICE are conditions with no single source id at all.
_DAG_CAP_FORMS = ("BUDGET_EXCEEDED", "DEPTH_CAP", "DIALOGUE_DEPTH_CAP")

_DAG_COLS = ["target_flag", "target_lot", "site_file", "site_event", "site_callsite", "site_verb",
             "designation", "cone_completeness", "disjunctive", "control_flow_skipped",
             "root_class", "source_id", "source_kind", "setter_cite", "unresolved_forms"]


def cone_completeness(unres):
    """complete | budget_capped | unreadable -- and the distinction is load-bearing.

    `complete`      nothing in the cone was refused.
    `budget_capped` every refusal is a CAP (per-site flag budget, depth cap, dialogue-depth cap).
                    The cone is INCOMPLETE, which under-specifies -- it can only MISS a
                    prerequisite, never invent one -- so the roots it did resolve are still read.
    `unreadable`    at least one guard could not be read at all (UNSET_FLAG, MANY_SETTERS,
                    WORKVALUE_UNRESOLVED, a predicate with no rule). Those cones are refused
                    wholesale by the DAG builder, because "we could not read that guard" is not
                    the same kind of ignorance as "we stopped walking".
    """
    if not unres:
        return "complete"
    forms = [u.split("(")[0] for u in unres]
    return "budget_capped" if all(f in _DAG_CAP_FORMS for f in forms) else "unreadable"


def emit_dag_corpus(rows, path):
    out, skipped, seen = [], Counter(), set()
    for r in rows:
        if not r["flag"]:
            skipped["site-has-no-award-flag"] += 1
            continue
        unres = [u for u in (r["unresolved"] or "").split("; ") if u]
        for root in r["roots"]:
            m = _DAG_ROOT_RE.match(root)
            if not m:
                skipped["root-class-not-addressable:" + root.split("(")[0]] += 1
                continue
            if m.group(2):
                kind, sid, cls = "flag", m.group(2), m.group(1)
            elif m.group(3):
                kind, sid, cls = "goods", m.group(3), "ITEM_POSSESSION"
            else:
                kind, sid, cls = "map", m.group(4), "MAP_ACCESS"
            row = dict(target_flag=r["flag"], target_lot=r["lot"], site_file=r["file"],
                       site_event=r["event"], site_callsite=r["callsite"], site_verb=r["verb"],
                       designation=r["designation"],
                       cone_completeness=cone_completeness(unres),
                       disjunctive=r["disjunctive"],
                       control_flow_skipped=r["control_flow_skipped"],
                       root_class=cls, source_id=sid, source_kind=kind,
                       setter_cite=r["cites"].get(root, ""),
                       unresolved_forms=";".join(sorted({u.split("(")[0] for u in unres})))
            key = tuple(row[c] for c in _DAG_COLS)
            if key in seen:
                skipped["duplicate-row"] += 1
                continue
            seen.add(key)
            out.append(row)
    out.sort(key=lambda x: (int(x["target_flag"]), x["site_file"], str(x["site_event"]),
                            str(x["site_callsite"]), x["root_class"], x["source_kind"],
                            x["source_id"]))
    comp = Counter(x["cone_completeness"] for x in out)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# AUTO-GENERATED by tools/extract_questline_conditions.py --dag-corpus"
                 " -- DO NOT EDIT, re-emit.\n")
        fh.write("# One row per (AWARD SITE, cone ROOT) from the #1085 questline-condition"
                 " extractor; parameterised-event call sites are complete.\n")
        fh.write("# The artifacts it reads (decompiled EMEVD + talk ESD) are licensing-restricted"
                 " and absent from CI,\n")
        fh.write("#   so this table is COMMITTED and re-emitted by hand -- the same shape as"
                 " greenfield/flag_names.tsv.\n")
        fh.write("#   Re-emit: python tools/gen_inputs.py --ensure elden_ring_artifacts && \\\n")
        fh.write("#            python tools/extract_questline_conditions.py elden_ring_artifacts"
                 " --dag-corpus greenfield/questline_conditions.tsv\n")
        fh.write("# 🛑 A ROW IS A COND ROOT, NOT A VERDICT. cone_completeness says how much of the"
                 " cone was read:\n")
        fh.write("#   complete = nothing refused; budget_capped = only CAPS were hit (the cone can"
                 " MISS a prerequisite,\n")
        fh.write("#   never invent one); unreadable = a guard could not be read at all."
                 " build_questline_dag.py owns\n")
        fh.write("#   the admission rule and tallies what it refuses.\n")
        fh.write("# 🛑 disjunctive=Y: the SITE guards contain an `||` and the arms were UNIONED, so"
                 " those roots are an\n")
        fh.write("#   OVER-approximation. A disjunction met further down a setter chain is not"
                 " marked at all, which is\n")
        fh.write("#   why no consumer may read a site's roots as a proven conjunction.\n")
        fh.write("# 🛑 ObjAct / MSB / ChrActivateConditionParam / ceremony / shop-lineup gating is"
                 " OUTSIDE this corpus.\n")
        fh.write("#   Absence of a row is 'no gate visible here', never 'no gate'.\n")
        fh.write("# MEASURED THIS EMIT: %d row(s) | cone: %s\n"
                 % (len(out), ", ".join("%s %d" % kv for kv in sorted(comp.items()))))
        fh.write("# roots NOT addressable as a source id (dropped once, here, and counted): %s\n"
                 % (", ".join("%s %d" % kv for kv in sorted(skipped.items())) or "none"))
        w = csv.DictWriter(fh, _DAG_COLS, delimiter="\t", extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for row in out:
            w.writerow(row)
    print("wrote %s (%d rows; %s)"
          % (path, len(out), ", ".join("%s %d" % kv for kv in sorted(comp.items()))))
    return out


if __name__ == "__main__":
    art = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") \
        else "elden_ring_artifacts"
    od = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else "."
    _C, _R, _rows = run(art, od)
    if "--dag-corpus" in sys.argv:
        emit_dag_corpus(_rows, sys.argv[sys.argv.index("--dag-corpus") + 1])
