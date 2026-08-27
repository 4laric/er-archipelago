#!/usr/bin/env python3
"""Per-branch ESD slicing for the questline extractor (#1085 phase 2).

Talk-ESD files decompile to valid Python, so we parse them with `ast` and
collect the guard condition stack along each PATH to a statement (if / elif /
else / while / assert-sequencing) instead of the lexical union v1 used.

Three things v1 could not see and this module can:

  1. ELSE / ELIF polarity.  `t322001203_x46` sets f12039170 only on the
     `else:` arm of `if GetEventFlag(12039157):` *inside* `if
     GetEventFlag(12039161):` -- the 12039161 requirement is a PATH fact.
  2. Assert scoping.  `assert X` constrains the REST OF ITS SUITE, not the
     whole function.
  3. Talk-list entry availability at MACHINE scope (see `entry_conditions`).

Comments are preserved (ast drops them) by re-attaching the contiguous comment
block immediately above each statement's first line -- the `# lot:NNNNNN`
markers that make ESD award sites visible live there.
"""
import ast, re
from collections import defaultdict

__all__ = ["parse_esd_file", "Machine", "entry_conditions"]

TRUEISH = ("True", "1")


def _lit(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


class Machine:
    """One `def tNNNNNNNNN_xNN(...)` state machine."""
    __slots__ = ("rel", "name", "params", "lines", "stmts", "calls",
                 "registers", "consumes", "workvals")

    def __init__(s, rel, name, params, lines):
        s.rel, s.name, s.params, s.lines = rel, name, params, lines
        s.stmts = []          # [(text, guards)]  guards = [(polarity, expr)]
        s.calls = []          # [(callee, guards, kwargs)]
        s.registers = {}      # entry index -> set(cond text)   AddTalkListData*
        s.consumes = set()    # entry indices tested by GetTalkListEntryResult
        s.workvals = defaultdict(set)


class _Slicer(ast.NodeVisitor):
    """Walks one function body carrying the path condition."""

    def __init__(self, mach, comments):
        self.m = mach
        self.comments = comments

    def _emit(self, node, guards):
        for c in self.comments.get(getattr(node, "lineno", -1), ()):
            self.m.stmts.append((c, list(guards)))
        try:
            txt = ast.unparse(node).replace("\n", " ")
        except Exception:
            return
        self.m.stmts.append((txt, list(guards)))
        self._scan(node, txt, guards)

    def _scan(self, node, txt, guards):
        m = self.m
        for c in ast.walk(node):
            if not isinstance(c, ast.Call):
                continue
            fn = c.func.id if isinstance(c.func, ast.Name) else None
            if fn is None:
                continue
            if re.match(r'^t\d+(_x\d+)?$', fn) and fn != m.name:
                kw = {k.arg: ast.unparse(k.value) for k in c.keywords if k.arg}
                m.calls.append((fn, list(guards), kw))
            elif fn == "AddTalkListDataIf" and len(c.args) >= 2:
                idx = _lit(c.args[1])
                if idx is not None:
                    m.registers.setdefault(idx, set()).add(ast.unparse(c.args[0]))
            elif fn == "AddTalkListData" and c.args:
                idx = _lit(c.args[0])
                if idx is not None:
                    m.registers.setdefault(idx, set()).add("True")
            elif fn == "SetWorkValue" and len(c.args) >= 2:
                idx = _lit(c.args[0])
                if idx is not None:
                    m.workvals[idx].add(ast.unparse(c.args[1]))

    def walk_body(self, body, guards):
        guards = list(guards)
        for st in body:
            if isinstance(st, ast.If):
                t = ast.unparse(st.test)
                self.walk_body(st.body, guards + [(True, t)])
                if st.orelse:
                    self.walk_body(st.orelse, guards + [(False, t)])
                continue
            if isinstance(st, ast.While):
                t = ast.unparse(st.test)
                g = guards if t in TRUEISH else guards + [(True, t)]
                self.walk_body(st.body, g)
                if st.orelse:
                    self.walk_body(st.orelse, guards)
                continue
            if isinstance(st, (ast.For, ast.With, ast.Try)):
                for f in ("body", "orelse", "finalbody"):
                    self.walk_body(getattr(st, f, []) or [], guards)
                for h in getattr(st, "handlers", []):
                    self.walk_body(h.body, guards)
                continue
            if isinstance(st, ast.FunctionDef):
                # ESD `def ExitPause():` sub-blocks run on state exit; the
                # enclosing path condition still holds.
                self.walk_body(st.body, guards)
                continue
            if isinstance(st, ast.Assert):
                t = ast.unparse(st.test)
                self._emit(st, guards + [(True, t)])
                guards = guards + [(True, t)]   # scoped to the REST of this suite
                continue
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) \
                    and isinstance(st.value.value, str):
                continue                        # """State N""" docstrings
            self._emit(st, guards)


ENTRY_RE = re.compile(r'GetTalkListEntryResult\(\)\s*==\s*(\d+)')


def _comment_map(txt):
    """lineno -> [contiguous comment lines directly above it]."""
    out, block = {}, []
    for i, raw in enumerate(txt.splitlines(), 1):
        s = raw.strip()
        if s.startswith("#"):
            block.append(s); continue
        if s:
            if block:
                out[i] = block
            block = []
    return out


def parse_esd_file(rel, txt):
    """-> {machine name: Machine}.  Returns {} if the file will not parse."""
    try:
        tree = ast.parse(txt)
    except SyntaxError:
        return {}
    comments = _comment_map(txt)
    src = txt.splitlines()
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("t"):
            continue
        params = [a.arg for a in node.args.args]
        lines = src[node.body[0].lineno - 1: (node.end_lineno or node.lineno)]
        m = Machine(rel, node.name, params, lines)
        _Slicer(m, comments).walk_body(node.body, [])
        for (_t, gs) in m.stmts:
            for (_p, e) in gs:
                for mm in ENTRY_RE.finditer(e):
                    m.consumes.add(int(mm.group(1)))
        out[node.name] = m
    return out


# ---------------------------------------------------------------------
# Talk-list protocol, at MACHINE scope.
#
# v1 keyed `AddTalkListDataIf` registrations per FILE and OR-ed every
# registration of an index.  Too coarse: `t322001203` registers entry 1 twice --
# conditionally in `_x45` (`AddTalkListDataIf(GetEventFlag(12039170), 1,
# 23220007, -1)`, line 968) and unconditionally in `_x37`
# (`AddTalkListData(1, 23220014, -1)`, line 843) -- so the OR collapsed to True
# and the Fia menu-entry gate vanished.
#
# The protocol is: a menu loop calls (transitively) the machine that registers
# entries, shows the menu, then branches on `GetTalkListEntryResult()`.  So the
# registration governing a consumer is the one at the SMALLEST call-graph
# distance from the consumer.  Only registrations at that minimum distance are
# OR-ed.
#
#   t322001203_x33 (consumer of entries 1..6)
#     -> _x34 -> _x42 -> _x45  registers 1..6 conditionally   [distance 3]
#   t322001203_x37 (consumer of entry 1) registers entry 1 itself [distance 0]
# ---------------------------------------------------------------------

def entry_conditions(machines, max_hops=6):
    """-> {(machine, entry index): [cond text, ...]} nearest-registration OR.

    Search is DOWNWARD-FIRST (callee closure), because the menu loop calls the
    registering machine; only if no descendant registers the index do we look
    upward at callers.  A bidirectional search finds spurious near hits: from
    `t322001203_x33` an unconditional `AddTalkListData(1, ...)` in the unrelated
    sibling `_x37` is 2 hops up-then-down, closer than the real registration in
    `_x45` at 3 hops down, and would collapse the entry-1 condition to True.
    """
    callees = defaultdict(set)
    callers = defaultdict(set)
    for name, m in machines.items():
        for (cal, _g, _kw) in m.calls:
            if cal in machines:
                callees[name].add(cal)
                callers[cal].add(name)

    def search(start, idx, adj):
        frontier, seen, d = {start}, {start}, 0
        while frontier and d <= max_hops:
            hit = set()
            for n in frontier:
                hit |= machines[n].registers.get(idx, set())
            if hit:
                return sorted(hit)
            nxt = set()
            for n in frontier:
                nxt |= adj[n]
            frontier = nxt - seen
            seen |= frontier
            d += 1
        return None

    out = {}
    for name, m in machines.items():
        for idx in m.consumes:
            best = search(name, idx, callees) or search(name, idx, callers)
            if best:
                out[(name, idx)] = best
    return out
