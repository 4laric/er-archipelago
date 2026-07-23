#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_esd_gates.py -- which EVENT FLAG gates each merchant shop range (bell-bearing logic).

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
for the auto-hand-in-on-talk QoL. Same shape extends to AwardItemLot (NPC dialogue gifts) for placing
gift checks -- reported here too, but the shop gate is the deliverable.

INPUT: ESDLang-decompiled Python. Produce it on Windows (one-time, like the WitchyBND unpacks):
    ESDLang.exe -er -esddir elden_ring_artifacts\\talk -writepy elden_ring_artifacts\\esd_py\\%e.py
(-writepy with %e in the template splits per ESD; without a split var it combines into one file.)
Point --pydir at the output dir (or --pyfile at the combined file).

OUTPUT: greenfield/esd_gates.tsv -- talk_id, gate_flag, gate_sense, shop_begin, shop_end
  gate_flag  = the EventFlag the OpenRegularShop sits behind (a bell-bearing / release flag); -1 = ungated
  gate_sense = 1 (flag must be SET) or 0 (flag must be CLEAR), from the `== 1` / `== 0` test
Join shop_begin..end to ShopLineupParam rows (as in datamine_merchant_shops) to get bell -> rows.

USAGE (after decompiling):
    python tools/datamine_esd_gates.py --probe               # show what it parsed, write nothing
    python tools/datamine_esd_gates.py                       # write greenfield/esd_gates.tsv
"""
import argparse
import ast
import glob
import os
import re
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
_SETFLAG_FNS = {"SetEventFlag", "SetEventFlagValue"}


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


def _flag_test(test):
    """If `test` is `EventFlag(F) == S` (or a bare `EventFlag(F)` truthy test), return (F, S); else None.
    S is the required sense: 1 for set, 0 for clear. A bare call is treated as `== 1`."""
    # EventFlag(F) == S  /  EventFlag(F) != S
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
        left, op, rhs = test.left, test.ops[0], test.comparators[0]
        if _call_name(left) in _FLAG_FNS and left.args:
            fl = _const_int(left.args[0])
            s = _const_int(rhs)
            if fl is not None and s is not None:
                if isinstance(op, ast.Eq):
                    return (fl, s)
                if isinstance(op, ast.NotEq):
                    return (fl, 0 if s else 1)
    # bare EventFlag(F) used as a truthy condition -> require set
    if _call_name(test) in _FLAG_FNS and test.args:
        fl = _const_int(test.args[0])
        if fl is not None:
            return (fl, 1)
    # not EventFlag(F) -> require clear
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        inner = _flag_test(test.operand)
        if inner:
            return (inner[0], 0 if inner[1] else 1)
    return None


_DEF_TALK_RE = re.compile(r"t(\d+)")   # ESDLang names state machines `def t<talkid>_x<state>(...)`


class _Walker(ast.NodeVisitor):
    """Walk a decompiled ESD, tracking the stack of EventFlag gates in scope so each OpenRegularShop /
    AwardItemLot is attributed to the flag condition(s) that must hold to reach it. talk_id is taken
    from the enclosing `def t<id>_x<n>` so a combined/per-map file attributes each merchant correctly."""
    def __init__(self, file_talk):
        self.talk_id = file_talk       # fallback until inside a t<id> function
        self.gate_stack = []          # [(flag, sense)] currently-enclosing EventFlag conditions
        self.shops = []               # (talk, gate_flag, gate_sense, begin, end)
        self.gifts = []               # (talk, gate_flag, gate_sense, lot)

    def visit_FunctionDef(self, node):
        m = _DEF_TALK_RE.match(node.name)
        prev = self.talk_id
        if m:
            self.talk_id = m.group(1)
        for n in node.body:
            self.visit(n)
        self.talk_id = prev

    def visit_If(self, node):
        gate = _flag_test(node.test)
        if gate:
            self.gate_stack.append(gate)
            for n in node.body:
                self.visit(n)
            self.gate_stack.pop()
            # the else-branch holds under the NEGATED flag test (sense flipped), so a
            # `if EventFlag(F)==0: pass else: OpenRegularShop(...)` still attributes the F-set gate.
            self.gate_stack.append((gate[0], 1 - gate[1]))
            for n in node.orelse:
                self.visit(n)
            self.gate_stack.pop()
        else:
            for n in node.body:
                self.visit(n)
            for n in node.orelse:
                self.visit(n)

    def _innermost_gate(self):
        return self.gate_stack[-1] if self.gate_stack else (-1, 1)

    def visit_Call(self, node):
        nm = _call_name(node)
        if nm in _SHOP_FNS and len(node.args) >= 2:
            a, b = _const_int(node.args[0]), _const_int(node.args[1])
            if a is not None and b is not None:
                gf, gs = self._innermost_gate()
                self.shops.append((self.talk_id, gf, gs, a, b))
        elif nm in _GIFT_FNS and node.args:
            lot = _const_int(node.args[0])
            if lot is not None:
                gf, gs = self._innermost_gate()
                self.gifts.append((self.talk_id, gf, gs, lot))
        self.generic_visit(node)


def _talk_id_of(path):
    base = os.path.basename(path)
    for stem in (base[:-3] if base.endswith(".py") else base,):
        digits = "".join(ch for ch in stem if ch.isdigit())
        return digits or stem
    return base


def _iter_sources(pydir, pyfile):
    if pyfile:
        yield _talk_id_of(pyfile), open(pyfile, encoding="utf-8", errors="replace").read()
        return
    # RECURSE: ESDLang -writepy lands .py in per-map subdirs (e.g. talk/m11_05_00_00-only/*.py).
    for fp in sorted(glob.glob(os.path.join(pydir, "**", "*.py"), recursive=True)):
        yield _talk_id_of(fp), open(fp, encoding="utf-8", errors="replace").read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pydir", default=PYDIR_DEFAULT, help="dir of ESDLang-decompiled t*.py (one per ESD)")
    ap.add_argument("--pyfile", help="a single combined ESDLang .py (all ESDs) instead of --pydir")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--probe", action="store_true", help="print what was parsed; write nothing")
    args = ap.parse_args()

    if not args.pyfile and not os.path.isdir(args.pydir):
        sys.exit(f"FATAL: {args.pydir} not found. Decompile the ESDs first (see module docstring): "
                 f"ESDLang.exe -er -esddir elden_ring_artifacts/talk -writepy "
                 f"elden_ring_artifacts/esd_py/%e.py")

    all_shops, all_gifts = [], []
    parsed = failed = 0
    for talk_id, src in _iter_sources(args.pydir, args.pyfile):
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            failed += 1
            if failed <= 5:
                print(f"  parse failed for {talk_id}: {e}", file=sys.stderr)
            continue
        parsed += 1
        # A combined file has many top-level def's; a per-ESD file usually one. Walk the whole module;
        # the talk id is per-file (per-ESD split) or "combined" (then gate rows still carry the shop
        # range, which is the join key that matters).
        w = _Walker(talk_id)
        w.visit(tree)
        all_shops.extend(w.shops)
        all_gifts.extend(w.gifts)

    # dedup
    all_shops = sorted(set(all_shops))
    all_gifts = sorted(set(all_gifts))
    gated = [s for s in all_shops if s[1] != -1]

    if args.probe:
        print(f"# PROBE: parsed {parsed} ESD(s) ({failed} parse-failed); {len(all_shops)} OpenRegularShop "
              f"call(s), {len(gated)} gated by an EventFlag; {len(all_gifts)} AwardItemLot gift(s).")
        for (t, gf, gs, a, b) in all_shops[:60]:
            g = f"EventFlag({gf})=={gs}" if gf != -1 else "UNGATED"
            print(f"  talk {t}: OpenRegularShop({a},{b})  gate={g}")
        if len(all_shops) > 60:
            print(f"  ... and {len(all_shops) - 60} more")
        return 0

    if not all_shops:
        sys.exit("FATAL: no OpenRegularShop calls parsed. Check the decompiled .py is ESDLang output "
                 "(subset of Python) and that the function names match _SHOP_FNS. Run --probe.")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# AUTO-GENERATED by tools/datamine_esd_gates.py -- the EventFlag gating each merchant\n")
        f.write("# shop range, from ESDLang-decompiled ESD (thefifthmatt). gate_flag = the bell-bearing/\n")
        f.write("# release flag (-1 = ungated); gate_sense = 1 set / 0 clear. Join shop_begin..end to\n")
        f.write("# ShopLineupParam rows for bell -> rows (MerchantBellLogic, multi-region resolution).\n")
        f.write("talk_id\tgate_flag\tgate_sense\tshop_begin\tshop_end\n")
        for (t, gf, gs, a, b) in all_shops:
            f.write(f"{t}\t{gf}\t{gs}\t{a}\t{b}\n")
    print(f"esd_gates: {len(all_shops)} shop range(s), {len(gated)} EventFlag-gated -> {args.out}")
    print(f"  (also saw {len(all_gifts)} AwardItemLot gift(s) -- NPC dialogue gift checks, next pass)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
