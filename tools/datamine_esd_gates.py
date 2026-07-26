#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_esd_gates.py -- which EVENT FLAG gates each merchant shop range (bell-bearing logic),
plus NPC dialogue item gifts (AwardItemLot).

WHY
---
datamine_merchant_shops.py answers "which merchant opens which shop rows, on which map" from the raw
ESD (OpenRegularShop args). It does NOT answer "what UNLOCKS that shop" -- the bell-bearing gate. That
gate is a CONDITION in the ESD state machine (`if EventFlag(<bell>) == 1: ... OpenRegularShop(a, b)`),
which the shops.py MerchantBellLogic docstring flagged as "not derivable matt-free from disk". It IS
derivable once the ESD is decompiled: thefifthmatt/ESDLang emits a subset of Python, so the gate is a
plain `if EventFlag(...)` around the shop call -- and Python's own `ast` parses it exactly (no binary
state-graph RE, no positional guessing).

This unlocks: real MerchantBellLogic (gate a merchant's Twin-Maiden re-sell behind its bell in logic),
the multi-region merchant resolution (a row reachable via HUB once its bell is in hand), and the data
for the auto-hand-in-on-talk QoL. The gift table is PROVENANCE data -- which NPC hands over which
item lot, behind which flag, on which map -- input to check-coordinate and availability work. It is
NOT a source of new checks: measured 2026-07-25, every gift lot that joins to an acquisition flag is
already an AP check (the cross-check below recomputes that at every emit).

THE CALL-SITE DEFECT (fixed 2026-07-25; same family as datamine_esd_flags.py F1)
--------------------------------------------------------------------------------
The first version read only LITERAL arguments. But ESDLang hoists shared dialogue shells into helper
functions and binds the payload at the CALL SITE:

    assert t000003000_x3(lot1=100000)     # caller binds the lot ...
    def t000003000_x3(lot1=_):
        AwardItemLot(lot1)                 # ... callee spends it

Measured on the complete 365-file corpus: 99 of 105 AwardItemLot sites take a parameter (6 literals),
and 32 of 137 OpenRegularShop sites do -- ALL of them roaming nomadic merchants, whose shop1/shop2
forward ~5 hops (_1000 -> x36 -> x92 -> x43 -> x44 -> x51). The literal-only reader emitted 6 of the 128
distinct gift lots and missed every nomadic merchant shop range.

Resolution is an ENVIRONMENT-CARRYING DESCENT, not a global (fn, param) -> {literals} pool: at each
call to a local machine function the kwargs are evaluated in the CALLER's environment and become the
callee's environment. Strict lexical scoping -- a (lot, gate) pair can never be cross-contaminated
between two call sites of the same helper, and `GetEventFlag(5 + flag5)` questline step-ladders
resolve per-path. Gates PROPAGATE across the call boundary (reaching the call required them); the
innermost enclosing flag test is the one attributed, as before. Walks start at ROOT states (functions
nothing else in the file calls -- the engine-invoked entries), so helper-only paths are real paths;
any award/shop site no root reaches is swept by an orphan walk of its enclosing def and TALLIED.
Nothing is dropped without a printed count (CONTRIBUTING: a filter with no tally is a lie).

INPUT: ESDLang-decompiled Python. Produce it on Windows (one-time, like the WitchyBND unpacks):
    ESDLang.exe -er -esddir elden_ring_artifacts\\talk -writepy elden_ring_artifacts\\esd_py\\%e.py
(-writepy with %e in the template splits per ESD; without a split var it combines into one file.)
Point --pydir at the output dir (or --pyfile at the combined file).

OUTPUT: greenfield/esd_gates.tsv -- talk_id, gate_flag, gate_sense, shop_begin, shop_end
        greenfield/esd_gifts.tsv -- talk_id, gate_flag, gate_sense, item_lot
  gate_flag  = the EventFlag the call sits behind (-1 = no enclosing flag test on that path)
  gate_sense = 1 (flag must be SET) or 0 (flag must be CLEAR), from the `== 1` / `== 0` test
A talk can emit SEVERAL rows for one shop range / lot -- one per distinct gate path. Rows are paths,
not checks; the emit prints rows AND distinct counts separately.

USAGE (after decompiling):
    python tools/datamine_esd_gates.py --probe        # show what it parsed, write nothing
    python tools/datamine_esd_gates.py                # write both TSVs
    python tools/datamine_esd_gates.py --no-resolve   # BREAK-TEST: literal args only, write nothing;
                                                      # gifts must collapse to ~6 sites or the
                                                      # resolver was never doing anything
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
PYDIR_DEFAULT = os.path.join(ART, "talk")   # ESDLang -writepy lands per-map .py under here (recursed)
OUT = os.path.join(REPO, "greenfield", "esd_gates.tsv")

# Function names ESDLang emits for the things we care about. Kept as a set so a decompiler-version
# rename is a one-line fix, and unrecognized-but-flag-shaped calls get reported rather than dropped.
_FLAG_FNS = {"EventFlag", "GetEventFlag"}
_SHOP_FNS = {"OpenRegularShop"}
_GIFT_FNS = {"AwardItemLot", "AwardItemLotWithoutAnyMessages"}

# Longest forwarding chain MEASURED on the 2026-07-25 corpus is 5 hops (nomadic merchants). The cap
# is slack; hits are TALLIED, so if a future corpus needs more this prints instead of silently losing.
_DEPTH_CAP = 24
# A per-file descent blowup is a walker bug (state graphs here are small), not a corpus fact -> FATAL.
_DESCENT_BUDGET = 200000


def _const_int(node):
    """int value of an ast node if it is an integer literal (handles unary minus), else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _const_int(node.operand)
        return -v if v is not None else None
    return None


def _call_name(node):
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Name):
            return f.id
        if isinstance(f, ast.Attribute):
            return f.attr
    return None


def _expr_int(node, env):
    """(value, how) of an int-valued ESD expression under the path environment `env`.

    how: literal | arg (a Name bound by the call chain) | argsum (const + Name questline step-ladder).
    (None, reason) when unresolvable on THIS path -- `_` is ESDLang's explicit unbound sentinel, and
    parameter DEFAULTS never bind (ESDLang emits every kwarg explicitly at every call site; verified
    in the sibling datamine_esd_flags.py, same corpus), so an empty env slot stays empty by design.
    """
    v = _const_int(node)
    if v is not None:
        return v, "literal"
    if isinstance(node, ast.Name):
        if node.id == "_":
            return None, "underscore (explicitly unbound)"
        if node.id in env:
            return env[node.id], "arg"
        return None, "param unbound on path"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        for a, b in ((node.left, node.right), (node.right, node.left)):
            base = _const_int(a)
            if base is not None and isinstance(b, ast.Name):
                if b.id in env:
                    return base + env[b.id], "argsum"
                return None, "binop const+param unbound"
        return None, "binop name+name (runtime)"
    return None, type(node).__name__ + " (runtime)"


def _flag_arg(node):
    """The flag expression of an EventFlag/GetEventFlag call, else None."""
    if _call_name(node) in _FLAG_FNS and node.args:
        return node.args[0]
    return None


def _flag_test(test, env, stats, unres):
    """If `test` is `EventFlag(F) == S` (or a bare `EventFlag(F)` truthy test), return (F, S); else None.
    S is the required sense: 1 for set, 0 for clear. A bare call is treated as `== 1`.
    F may be a literal, a bound parameter, or `const + param` -- resolved through `env`. A flag-shaped
    test whose F does NOT resolve is TALLIED (gate_unresolved), never silently treated as unrelated."""
    # EventFlag(F) == S  /  EventFlag(F) != S
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
        left, op, rhs = test.left, test.ops[0], test.comparators[0]
        fe = _flag_arg(left)
        if fe is not None:
            s = _const_int(rhs)
            if s is not None:
                fl, how = _expr_int(fe, env)
                if fl is None:
                    stats["gate_unresolved"] += 1
                    unres["gate: " + how] += 1
                    return None
                stats["gate_" + how] += 1
                if isinstance(op, ast.Eq):
                    return (fl, s)
                if isinstance(op, ast.NotEq):
                    return (fl, 0 if s else 1)
        return None
    # bare EventFlag(F) used as a truthy condition -> require set
    fe = _flag_arg(test)
    if fe is not None:
        fl, how = _expr_int(fe, env)
        if fl is None:
            stats["gate_unresolved"] += 1
            unres["gate: " + how] += 1
            return None
        stats["gate_" + how] += 1
        return (fl, 1)
    # not EventFlag(F) -> require clear
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        inner = _flag_test(test.operand, env, stats, unres)
        if inner:
            return (inner[0], 0 if inner[1] else 1)
    return None


class _Miner:
    """One decompiled talk ESD. Walks every ROOT state (a top-level def nothing else in the file
    calls -- the engine invokes those), carrying (env, gate-stack) down through calls to local machine
    functions, so each OpenRegularShop / AwardItemLot is attributed the flag condition(s) and argument
    values of the PATH that reached it. Cycle-guarded (a def already on the path is not re-entered)
    and depth-capped; both are tallied."""

    def __init__(self, talk, tree, stats, unres, resolve=True):
        self.talk, self.stats, self.unres, self.resolve = talk, stats, unres, resolve
        self.shops = []               # (talk, gate_flag, gate_sense, begin, end)
        self.gifts = []               # (talk, gate_flag, gate_sense, lot)
        self.defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        self.sites = {}               # id(Call) -> [kind, literal?, visits, resolutions]
        self.site_home = {}           # id(Call) -> enclosing top-level def name
        calls = collections.defaultdict(set)
        called, direct = set(), set()
        for name, fn in self.defs.items():
            for n in ast.walk(fn):
                cn = _call_name(n) if isinstance(n, ast.Call) else None
                if cn is None:
                    continue
                if cn in self.defs:
                    calls[name].add(cn)
                    called.add(cn)
                if cn in _SHOP_FNS or cn in _GIFT_FNS:
                    kind = "shop" if cn in _SHOP_FNS else "gift"
                    is_lit = bool(n.args) and all(_const_int(a) is not None for a in n.args[:2])
                    self.sites[id(n)] = [kind, is_lit, 0, 0]
                    self.site_home[id(n)] = name
                    direct.add(name)
        # transitively interesting = can reach an award/shop; descent is pruned to these
        interesting = set(direct)
        grew = True
        while grew:
            grew = False
            for f, cs in calls.items():
                if f not in interesting and cs & interesting:
                    interesting.add(f)
                    grew = True
        self.interesting = interesting
        self.roots = [n for n in self.defs if n not in called]
        self.descents = 0

    def run(self):
        for r in self.roots:
            self._walk(self.defs[r], {}, (), (r,))
        # ORPHAN SWEEP: an award/shop inside a def no root reaches (dead code, or a call edge shape
        # the descent does not follow) is still walked -- with an empty env -- and TALLIED, so a
        # structural change in the decompiler output degrades to "N orphan walks" in the stats
        # instead of silently vanishing rows.
        orphan_homes = {self.site_home[k] for k, s in self.sites.items() if s[2] == 0}
        for h in sorted(orphan_homes):
            self.stats["orphan_walks"] += 1
            self._walk(self.defs[h], {}, (), (h,))
        unseen = sum(1 for s in self.sites.values() if s[2] == 0)
        if unseen:
            raise RuntimeError("talk %s: %d award/shop site(s) never visited even by the orphan "
                               "sweep -- walker no longer covers the corpus shape" % (self.talk, unseen))

    def _walk(self, node, env, gates, stack):
        if isinstance(node, ast.FunctionDef):
            # nested defs (WhilePaused/ExitPause callbacks) run in their parent's context
            for n in node.body:
                self._walk(n, env, gates, stack)
            return
        if isinstance(node, ast.If):
            gate = _flag_test(node.test, env, self.stats, self.unres)
            self._walk(node.test, env, gates, stack)
            if gate:
                for n in node.body:
                    self._walk(n, env, gates + (gate,), stack)
                # the else-branch holds under the NEGATED flag test (sense flipped), so a
                # `if EventFlag(F)==0: pass else: OpenRegularShop(...)` still attributes the F-set gate.
                neg = (gate[0], 1 - gate[1])
                for n in node.orelse:
                    self._walk(n, env, gates + (neg,), stack)
            else:
                for n in node.body:
                    self._walk(n, env, gates, stack)
                for n in node.orelse:
                    self._walk(n, env, gates, stack)
            return
        if isinstance(node, ast.Call):
            self._call(node, env, gates, stack)
        for c in ast.iter_child_nodes(node):
            self._walk(c, env, gates, stack)

    def _call(self, node, env, gates, stack):
        nm = _call_name(node)
        if nm is None:
            return
        gf, gs = gates[-1] if gates else (-1, 1)
        if nm in _SHOP_FNS and len(node.args) >= 2:
            rec = self.sites[id(node)]
            rec[2] += 1
            a, ha = _expr_int(node.args[0], env)
            b, hb = _expr_int(node.args[1], env)
            if a is not None and b is not None:
                rec[3] += 1
                self.stats["shop_path_" + ha] += 1
                self.shops.append((self.talk, gf, gs, a, b))
            else:
                self.stats["shop_path_unresolved"] += 1
                self.unres["shop: " + (ha if a is None else hb)] += 1
        elif nm in _GIFT_FNS and node.args:
            rec = self.sites[id(node)]
            rec[2] += 1
            lot, how = _expr_int(node.args[0], env)
            if lot is not None:
                rec[3] += 1
                self.stats["gift_path_" + how] += 1
                self.gifts.append((self.talk, gf, gs, lot))
            else:
                self.stats["gift_path_unresolved"] += 1
                self.unres["gift: " + how] += 1
        elif self.resolve and nm in self.defs and nm in self.interesting:
            if nm in stack:
                self.stats["cycle_skips"] += 1
                return
            if len(stack) >= _DEPTH_CAP:
                self.stats["depth_cap_hits"] += 1
                return
            self.descents += 1
            if self.descents > _DESCENT_BUDGET:
                raise RuntimeError("talk %s: descent budget (%d) blown -- walker bug, not corpus"
                                   % (self.talk, _DESCENT_BUDGET))
            cenv = {}
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                v, _how = _expr_int(kw.value, env)
                if v is not None:
                    cenv[kw.arg] = v
            self._walk(self.defs[nm], cenv, gates, stack + (nm,))


def _talk_id_of(path):
    base = os.path.basename(path)
    stem = base[:-3] if base.endswith(".py") else base
    digits = "".join(ch for ch in stem if ch.isdigit())
    return str(int(digits)) if digits else stem


def _iter_sources(pydir, pyfile):
    if pyfile:
        yield _talk_id_of(pyfile), open(pyfile, encoding="utf-8", errors="replace").read()
        return
    # RECURSE: ESDLang -writepy lands .py in per-map subdirs (e.g. talk/m11_05_00_00-only/*.py).
    for fp in sorted(glob.glob(os.path.join(pydir, "**", "*.py"), recursive=True)):
        yield _talk_id_of(fp), open(fp, encoding="utf-8", errors="replace").read()


def scan(pydir, pyfile, resolve):
    stats = collections.Counter()
    unres = collections.Counter()
    all_shops, all_gifts = [], []
    site_tally = collections.Counter()
    parse_failed = []
    n_src = 0
    for talk_id, src in _iter_sources(pydir, pyfile):
        n_src += 1
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            parse_failed.append((talk_id, str(e)))
            continue
        stats["files"] += 1
        m = _Miner(talk_id, tree, stats, unres, resolve=resolve)
        m.run()
        all_shops.extend(m.shops)
        all_gifts.extend(m.gifts)
        for kind, is_lit, visits, res in m.sites.values():
            site_tally[kind + "_sites"] += 1
            site_tally[kind + ("_lit" if is_lit else "_param")] += 1
            site_tally[kind + ("_resolved" if res else "_never_resolved")] += 1
    if n_src == 0:
        sys.exit("FATAL: no ESDLang .py found under %s -- nothing scanned, nothing written."
                 % (pyfile or pydir))
    return all_shops, all_gifts, stats, unres, site_tally, parse_failed


def _read_tsv(path):
    """TSV rows as dicts. These files open with '#' comment lines; the first NON-comment line is the
    header -- csv.DictReader on the raw file would take a comment as the header and silently empty
    every join, so this reader is used everywhere instead."""
    hdr, out = None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if hdr is None:
                hdr = parts
                continue
            out.append(dict(zip(hdr, parts)))
    return out


def crosscheck_gifts(gift_rows, repo):
    """COMPUTED at every emit, never asserted in prose (CONTRIBUTING: comments rot; measurements
    don't). What this table is worth, measured on the complete 365-file corpus 2026-07-25:

      - NO NEW CHECKS. Every gift lot with an acquisition flag is already known to region_map.csv.
        (An earlier claim of "~126 invisible lots" was wrong; so was a later "98 = all already live".)
      - Its value is PROVENANCE and PLACEMENT: a block of joining lots are 400xxx key-item OBTAINED
        flags whose region_map rows sit at map=PENDING "Global / Common-event (unplaced)" -- this
        table hands each one a talk_id -> NPC -> map -> region, i.e. exactly the placement datum
        those rows are missing (39 of them on the 2026-07-25 corpus: Volcano Manor Invitation, the
        Sellen chain, Seluvis's Potion, ...).

    Buckets (each lot counted once, first match wins):
      live_check      -- a flag of the lot is in eldenring/data.py LOCATIONS (a live AP check)
      not_randomized  -- in data.py NOT_RANDOMIZED (deliberately dropped; e.g. Spectral Steed Whistle)
      pending         -- in region_map.csv with map == PENDING (unplaced; the prize, see above)
      placed_not_live -- in region_map.csv placed but neither live nor NOT_RANDOMIZED (should be 0;
                         data.py's own header calls that REAL data loss -- printed loudly)
      unknown_flag    -- flag joins flag_lots.tsv but appears nowhere downstream (should be 0)
      no_flag         -- lot has no acquisition flag at all (invisible to the flag poll)
    """
    fl_path = os.path.join(repo, "greenfield", "flag_lots.tsv")
    rm_path = os.path.join(repo, "greenfield", "region_map.csv")
    dp_path = os.path.join(repo, "greenfield", "eldenring", "data.py")
    missing = [p for p in (fl_path, rm_path, dp_path) if not os.path.exists(p)]
    if missing:
        # A missing input must not silently disable the guard (the sibling tool once lost every
        # cross-check to a moved REPO constant and emitted anyway). FATAL, nothing written.
        sys.exit("FATAL: cross-check input(s) missing: %s. Without them the no-new-checks claim "
                 "cannot be recomputed and this table is not evidence of anything. Set ER_REPO."
                 % ", ".join(missing))
    lot2flags = collections.defaultdict(set)
    for r in _read_tsv(fl_path):
        if r.get("flag", "").isdigit() and r.get("lot", "").isdigit():
            lot2flags[int(r["lot"])].add(int(r["flag"]))
    if not lot2flags:
        sys.exit("FATAL: flag_lots.tsv parsed to zero lot->flag rows -- header/comment drift broke "
                 "the join. Nothing written.")
    loc_flags, notrand = set(), set()
    tree = ast.parse(open(dp_path, encoding="utf-8").read())
    for n in tree.body:
        if not isinstance(n, ast.Assign) or not isinstance(n.targets[0], ast.Name):
            continue
        if n.targets[0].id == "LOCATIONS":
            for _region, locs in ast.literal_eval(n.value).items():
                loc_flags.update(int(t[2]) for t in locs)
        elif n.targets[0].id == "NOT_RANDOMIZED":
            notrand = {int(k) for k in ast.literal_eval(n.value)}
    if not loc_flags:
        sys.exit("FATAL: no LOCATIONS flags parsed from eldenring/data.py -- the generated shape "
                 "moved; the no-new-checks cross-check cannot run. Nothing written.")
    rm_pending, rm_placed = set(), set()
    import csv as _csv
    with open(rm_path, encoding="utf-8", newline="") as fh:
        for row in _csv.DictReader(fh):
            if not row.get("flag", "").isdigit():
                continue
            (rm_pending if row.get("map") == "PENDING" else rm_placed).add(int(row["flag"]))
    lots = {r[3] for r in gift_rows}
    buckets = {k: [] for k in ("live_check", "not_randomized", "pending",
                               "placed_not_live", "unknown_flag", "no_flag")}
    for l in sorted(lots):
        fs = lot2flags.get(l, set())
        if not fs:
            buckets["no_flag"].append(l)
        elif fs & loc_flags:
            buckets["live_check"].append(l)
        elif fs & notrand:
            buckets["not_randomized"].append(l)
        elif fs & rm_pending:
            buckets["pending"].append(l)
        elif fs & rm_placed:
            buckets["placed_not_live"].append(l)
        else:
            buckets["unknown_flag"].append(l)
    with_flag = len(lots) - len(buckets["no_flag"])
    if with_flag == 0:
        sys.exit("FATAL: zero gift lots join flag_lots.tsv -- the join is broken, not the data. "
                 "Nothing written.")
    return {"lots": len(lots), "with_flag": with_flag, "buckets": buckets}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pydir", default=PYDIR_DEFAULT, help="dir of ESDLang-decompiled t*.py (one per ESD)")
    ap.add_argument("--pyfile", help="a single combined ESDLang .py (all ESDs) instead of --pydir")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--probe", action="store_true", help="print what was parsed; write nothing")
    ap.add_argument("--no-resolve", action="store_true",
                    help="BREAK-TEST: disable call-site resolution (literal args only); implies --probe. "
                         "Gift sites must collapse to ~6 or the resolver is dead weight.")
    args = ap.parse_args()
    if args.no_resolve:
        args.probe = True

    if not args.pyfile and not os.path.isdir(args.pydir):
        sys.exit(f"FATAL: {args.pydir} not found. Decompile the ESDs first (see module docstring): "
                 f"ESDLang.exe -er -esddir elden_ring_artifacts/talk -writepy "
                 f"elden_ring_artifacts/esd_py/%e.py")

    all_shops, all_gifts, stats, unres, sites, parse_failed = scan(
        args.pydir, args.pyfile, resolve=not args.no_resolve)

    shop_rows = sorted(set(all_shops), key=lambda r: (int(r[0]),) + r[1:])
    gift_rows = sorted(set(all_gifts), key=lambda r: (int(r[0]),) + r[1:])
    shop_ranges = {(r[0], r[3], r[4]) for r in shop_rows}
    gift_lots = {r[3] for r in gift_rows}
    gated_shops = [s for s in shop_rows if s[1] != -1]
    gated_gifts = [g for g in gift_rows if g[1] != -1]

    print("files parsed          : %d  (%d parse-failed)" % (stats["files"], len(parse_failed)))
    print("walker                : orphan walks %d | cycle skips %d | depth-cap hits %d"
          % (stats["orphan_walks"], stats["cycle_skips"], stats["depth_cap_hits"]))
    print("SHOPS  sites          : %d = %d literal + %d param | resolved %d, never-resolved %d"
          % (sites["shop_sites"], sites["shop_lit"], sites["shop_param"],
             sites["shop_resolved"], sites["shop_never_resolved"]))
    print("       paths          : literal %d | arg %d | argsum %d | unresolved %d"
          % (stats["shop_path_literal"], stats["shop_path_arg"],
             stats["shop_path_argsum"], stats["shop_path_unresolved"]))
    print("       rows %d | distinct (talk,range) %d | gated rows %d | distinct gate flags %d"
          % (len(shop_rows), len(shop_ranges), len(gated_shops),
             len({r[1] for r in gated_shops})))
    print("GIFTS  sites          : %d = %d literal + %d param | resolved %d, never-resolved %d"
          % (sites["gift_sites"], sites["gift_lit"], sites["gift_param"],
             sites["gift_resolved"], sites["gift_never_resolved"]))
    print("       paths          : literal %d | arg %d | argsum %d | unresolved %d"
          % (stats["gift_path_literal"], stats["gift_path_arg"],
             stats["gift_path_argsum"], stats["gift_path_unresolved"]))
    print("       rows %d | distinct lots %d | gated rows %d | distinct gate flags %d"
          % (len(gift_rows), len(gift_lots), len(gated_gifts),
             len({r[1] for r in gated_gifts})))
    print("GATES  in `if` tests  : literal %d | arg %d | argsum %d | UNRESOLVED %d"
          % (stats["gate_literal"], stats["gate_arg"], stats["gate_argsum"],
             stats["gate_unresolved"]))
    if unres:
        print("UNRESOLVED reasons (all tallied, none dropped silently):")
        for k, v in unres.most_common(10):
            print("    %5d  %s" % (v, k))
    for t, e in parse_failed[:5]:
        print("  parse failed for %s: %s" % (t, e), file=sys.stderr)

    corpus = not args.pyfile
    if corpus and parse_failed:
        sys.exit("FATAL: %d file(s) failed to parse -- a partial corpus silently SHRINKS these "
                 "tables. Nothing written." % len(parse_failed))
    if not shop_rows:
        sys.exit("FATAL: no OpenRegularShop calls parsed. Check the decompiled .py is ESDLang output "
                 "(subset of Python) and that the function names match _SHOP_FNS. Run --probe.")
    if not gift_rows and not args.no_resolve:
        sys.exit("FATAL: zero AwardItemLot gift rows -- an empty result is a failure, not a clean run.")
    if not args.no_resolve and corpus:
        # The defect this rewrite fixes: param sites exist but nothing resolves through the call
        # chain. If either count is zero the resolver regressed to the literal-only reader.
        if sites["gift_param"] and stats["gift_path_arg"] == 0:
            sys.exit("FATAL: %d param gift sites but 0 arg-resolved paths -- call-site resolution is "
                     "dead. Nothing written." % sites["gift_param"])
        if sites["shop_param"] and stats["shop_path_arg"] == 0:
            sys.exit("FATAL: %d param shop sites but 0 arg-resolved paths -- call-site resolution is "
                     "dead. Nothing written." % sites["shop_param"])

    xc = crosscheck_gifts(gift_rows, REPO) if not args.no_resolve else None
    if xc:
        b = xc["buckets"]
        print("\nCROSS-CHECK gifts -> flag_lots -> region_map/data.py (computed, not asserted):")
        print("  distinct lots %d | with an acquisition flag %d | no flag %d"
              % (xc["lots"], xc["with_flag"], len(b["no_flag"])))
        print("  already a live AP check : %d" % len(b["live_check"]))
        print("  deliberately NOT_RANDOMIZED : %d  %s" % (len(b["not_randomized"]), b["not_randomized"]))
        print("  region_map PENDING/unplaced : %d  <- the placement prize; this table gives each a talk_id->map"
              % len(b["pending"]))
        print("      %s" % b["pending"])
        for k, lbl in (("placed_not_live", "placed in region_map but NOT live and NOT opted out"),
                       ("unknown_flag", "flag joins flag_lots but appears NOWHERE downstream")):
            if b[k]:
                print("  *** %s: %d %s -- data.py calls this REAL data loss; investigate before "
                      "trusting this emit" % (lbl, len(b[k]), b[k]))

    if args.probe:
        for (t, gf, gs, a, b) in shop_rows[:20]:
            g = f"EventFlag({gf})=={gs}" if gf != -1 else "UNGATED"
            print(f"  shop  talk {t}: OpenRegularShop({a},{b})  gate={g}")
        if len(shop_rows) > 20:
            print(f"  ... and {len(shop_rows) - 20} more shop rows")
        for (t, gf, gs, lot) in gift_rows[:20]:
            g = f"EventFlag({gf})=={gs}" if gf != -1 else "UNGATED"
            print(f"  gift  talk {t}: AwardItemLot({lot})  gate={g}")
        if len(gift_rows) > 20:
            print(f"  ... and {len(gift_rows) - 20} more gift rows")
        print("\n--probe: nothing written.")
        return 0

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_esd_gates.py -- the EventFlag gating each merchant\n")
        f.write("# shop range, from ESDLang-decompiled ESD (thefifthmatt). gate_flag = the bell-bearing/\n")
        f.write("# release flag (-1 = ungated on that path); gate_sense = 1 set / 0 clear. Join\n")
        f.write("# shop_begin..end to ShopLineupParam rows for bell -> rows (MerchantBellLogic,\n")
        f.write("# multi-region resolution). A talk emits one row PER GATE PATH; rows are paths,\n")
        f.write("# not merchants. Args resolve through the ESD call chain (call-site kwargs),\n")
        f.write("# not just literals -- nomadic merchants forward shop1/shop2 ~5 hops.\n")
        f.write("# MEASURED THIS RUN: %d sites (%d literal, %d param) | %d resolved | %d rows,\n"
                % (sites["shop_sites"], sites["shop_lit"], sites["shop_param"],
                   sites["shop_resolved"], len(shop_rows)))
        f.write("#   %d distinct (talk,range) | %d gated rows over %d distinct gate flags\n"
                % (len(shop_ranges), len(gated_shops), len({r[1] for r in gated_shops})))
        f.write("talk_id\tgate_flag\tgate_sense\tshop_begin\tshop_end\n")
        for (t, gf, gs, a, b) in shop_rows:
            f.write(f"{t}\t{gf}\t{gs}\t{a}\t{b}\n")
    print(f"esd_gates: {len(shop_rows)} row(s), {len(gated_shops)} EventFlag-gated -> {args.out}")

    # NPC DIALOGUE GIFTS. An `AwardItemLot(lot)` in a talk ESD is an item an NPC hands you in
    # conversation, usually behind `if EventFlag(received)==0:`; the gate_flag with gate_sense==0 is
    # the 'not yet received' acquisition flag. PROVENANCE table (who gives what, where, behind what)
    # -- the cross-check above proves it names no new checks, and re-proves it on every emit.
    b_ = xc["buckets"]
    gifts_out = os.path.join(os.path.dirname(args.out), "esd_gifts.tsv")
    with open(gifts_out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_esd_gates.py -- NPC dialogue item gifts (AwardItemLot)\n")
        f.write("# from ESDLang-decompiled talk ESD. gate_flag with gate_sense==0 is the 'not yet\n")
        f.write("# received' acquisition flag; item_lot is the ItemLotParam handed over; talk_id ->\n")
        f.write("# NPC map -> region (join as in datamine_merchant_shops). One row PER GATE PATH.\n")
        f.write("# Lots resolve through the ESD call chain (assert t.._x3(lot1=N) -> AwardItemLot(lot1));\n")
        f.write("# a literal-only read finds 6 of the lots below. NO NEW CHECKS -- every lot with an\n")
        f.write("# acquisition flag is already in region_map.csv; the value is PROVENANCE (who hands\n")
        f.write("# it over, behind which flag, on which map) and PLACEMENT for the PENDING rows.\n")
        f.write("# MEASURED THIS RUN (recomputed on every emit):\n")
        f.write("#   %d sites (%d literal, %d param) | %d rows | %d distinct lots\n"
                % (sites["gift_sites"], sites["gift_lit"], sites["gift_param"],
                   len(gift_rows), len(gift_lots)))
        f.write("#   lots: %d live AP checks | %d NOT_RANDOMIZED | %d region_map-PENDING (this\n"
                % (len(b_["live_check"]), len(b_["not_randomized"]), len(b_["pending"])))
        f.write("#   table is their placement source) | %d placed-not-live | %d unknown-flag |\n"
                % (len(b_["placed_not_live"]), len(b_["unknown_flag"])))
        f.write("#   %d with no acquisition flag (invisible to the flag poll)\n"
                % len(b_["no_flag"]))
        f.write("talk_id\tgate_flag\tgate_sense\titem_lot\n")
        for (t, gf, gs, lot) in gift_rows:
            f.write(f"{t}\t{gf}\t{gs}\t{lot}\n")
    _received = sum(1 for (_t, gf, gs, _l) in gift_rows if gf != -1 and gs == 0)
    print(f"esd_gifts: {len(gift_rows)} row(s), {len(gift_lots)} distinct lot(s), "
          f"{_received} with a received-flag gate -> {gifts_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
