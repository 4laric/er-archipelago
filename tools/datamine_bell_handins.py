#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datamine_bell_handins.py -- which bell bearing unlocks which merchant at the Twin Maiden Husks.

WHY
---
`features/shops.py` has said since Phase 4 that the bell -> shop join is "NOT derivable matt-free
from disk", because the bell-item flags (400049 Kale, 400901+ nomadic/isolated/hermit) appear
NOWHERE in `ShopLineupParam` -- neither as `eventFlag_forStock` nor as `eventFlag_forRelease`.
That is true of the ITEM-PICKUP flags, and it sent `tools/datamine_bell_shops.py` looking for an
EMEVD handover event. There is no such event. The join is in the Twin Maidens' own TALK ESD, and
it is not a param relation at all:

    t600001110  (Twin Maiden Husks)
      "Offer a bell bearing"  -> PlayerEquipmentQuantityChange(Goods, 8910 + n)   # consume item
                              -> SetEventFlag(11109710 + n)                        # the HAND-IN flag
      "Bell Bearing Shop N"   -> AddTalkListDataIf(GetEventFlag(11109710 + n), e)  # entry appears
                              -> if entry == e: OpenRegularShop(begin, end)        # the SAME rows

⭐⭐⭐ THE FINDING, and it is what makes the QoL a one-flag write: the range the Twin Maidens open
for a merchant is the merchant's OWN `ShopLineupParam` block -- not a copy of it. Kale's talk
(`t800006000`) opens `100500..100524` and the Twin Maidens' "Kale's Bell Bearing" entry opens
`100500..100524`. So handing in a bell does NOT release rows or move stock: it adds a MENU ENTRY
pointing at rows that already exist. Setting `11109710 + n` is therefore the entire mechanism, and
it is idempotent, reversible and invisible to every check the seed minted (the rows keep their own
`eventFlag_forStock`, so the same AP location fires whether you buy at the merchant or at the hub).

WHAT THIS EMITS
---------------
`greenfield/bell_handins.tsv`, one line per bell that opens a shop range:

    handin_flag \t bell_goods_id \t bell_name \t shop_begin \t shop_end \t menu

`tools/gen_merchant_bells.py` bakes it into the client as `er-logic/src/merchant_bell_table.rs`.
It is STATIC GAME DATA -- seed-invariant -- so it does not travel in slot_data and does not move
`CONTRACT_HASH` (same argument as `gen_sweep_boss_names.py`).

🛑 WHAT IT DELIBERATELY DOES NOT COVER, and why the count is 36 and not 48
--------------------------------------------------------------------------
Twelve bells work the OTHER way: they release rows inside the Twin Maidens' own block 1018 via
`eventFlag_forRelease` (Bone / Meat / Medicine / Gravity Stone Peddler, and the DLC Herbalist,
Mushroom-Seller [1][2], Greasemonger, Moldmonger, Igon, Spellmachinist, String-Seller). Those have
no menu entry and no shop range, so this table has no row for them, and the client cannot key them
off a shop open. Deriving them would need "which merchant sells these goods", and the obvious join
does NOT work: matching each tranche's `equipId` set against every other shop block finds a
containing block for only 4 of the 12, and two of those four are provably coincidence (a 1-row
tranche matching an unrelated block). A wrong merchant here would hand the player someone else's
shelf, so the honest answer is to emit nothing and say so. The miner's / glovewort bells are the
same shape and are not merchants at all.

INPUT: ESDLang-decompiled talk ESD, exactly as `datamine_esd_gates.py` consumes it. In-sandbox:

    python tools/gen_inputs.py --ensure elden_ring_artifacts
    python tools/datamine_bell_handins.py --probe      # print the join, write nothing
    python tools/datamine_bell_handins.py              # write greenfield/bell_handins.tsv
"""
import argparse
import ast
import glob
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ART = os.path.join(REPO, "elden_ring_artifacts")
PYDIR_DEFAULT = os.path.join(ART, "talk")
FMG_DIRS = (os.path.join(ART, "msg", "item-msgbnd-dcx"),
            os.path.join(ART, "msg", "item_dlc01-msgbnd-dcx"),
            os.path.join(ART, "msg", "item_dlc02-msgbnd-dcx"))
OUT = os.path.join(REPO, "greenfield", "bell_handins.tsv")

# The Twin Maiden Husks. The ONE talk script that owns every hand-in and every re-sell entry.
TWIN_MAIDENS_TALK = 600001110

# The hand-in flag band. Both runs (base 11109710.., DLC 11109790..) live inside it, and it is used
# only to pick the BELL flag out of a compound condition -- never to enumerate. A condition like
# Gowry's incantation entry is `GetEventFlag(11109744) and GetEventFlag(1038519257)`; the second is
# a questline step, not a bell.
BELL_FLAG_LO, BELL_FLAG_HI = 11109710, 11109799

_TEXT_RE = re.compile(r'<text id="(\d+)"[^>]*>(.*?)</text>', re.S)


# ------------------------------------------------------------------------------------------------
# names
# ------------------------------------------------------------------------------------------------
def load_goods_names():
    """goods id -> FMG name, base then DLC (later files win, as the game layers them)."""
    names = {}
    for d in FMG_DIRS:
        for fp in sorted(glob.glob(os.path.join(d, "GoodsName*.fmg.xml"))):
            with open(fp, encoding="utf-8") as fh:
                for m in _TEXT_RE.finditer(fh.read()):
                    txt = m.group(2).strip()
                    if txt and txt != "%null%":
                        names[int(m.group(1))] = txt
    return names


def ascii_fold(name):
    """NFKD-fold to ASCII. Returns (folded, changed).

    In-game text is drawn by the GAME's font, which has no glyph for non-ASCII -- the same rule
    `gen_sweep_boss_names.py` enforces. Unlike that table we cannot just refuse: "Kale's Bell
    Bearing" is spelled with an acute in the FMG and there is no other source for the name. So fold
    it, and PRINT every fold rather than doing it quietly.
    """
    folded = "".join(c for c in unicodedata.normalize("NFKD", name)
                     if not unicodedata.combining(c))
    # The FMG uses a typographic apostrophe in some rows; the game font has no glyph for it either.
    folded = folded.replace("\u2019", "'").replace("\u2018", "'")
    folded = folded.replace("\u2013", "-").replace("\u2014", "-")
    # Vanilla ships `[ERROR]Nomadic Merchant's Bell Bearing [11]` in GoodsName -- FromSoftware's
    # own untranslated-string marker, present in the shipped FMG, not damage from this reader.
    # It is stripped here because the string is player-visible; the strip is reported like a fold.
    folded = folded.replace("[ERROR]", "").strip()
    return folded, folded != name


# ------------------------------------------------------------------------------------------------
# the ESD walk
# ------------------------------------------------------------------------------------------------
def _int(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, int) else None


def _call_name(node):
    return node.func.id if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) else None


def _flags_in(node):
    """Every literal argument of a GetEventFlag(...) call anywhere under `node`."""
    out = []
    for n in ast.walk(node):
        if _call_name(n) == "GetEventFlag" and n.args:
            v = _int(n.args[0])
            if v is not None:
                out.append(v)
    return out


def _entry_menu_flags(fn):
    """entry index -> the bell flag whose hand-in makes that menu entry appear.

    `AddTalkListDataIf(cond, entry, action, ...)` and its `Alt` sibling
    `AddTalkListDataAltIf(cond, entry, action, sort, bool)` share argument slots 0 and 1.
    """
    out = {}
    for n in ast.walk(fn):
        if _call_name(n) in ("AddTalkListDataIf", "AddTalkListDataAltIf") and len(n.args) >= 2:
            entry = _int(n.args[1])
            if entry is None:
                continue
            bells = [f for f in _flags_in(n.args[0]) if BELL_FLAG_LO <= f <= BELL_FLAG_HI]
            if len(set(bells)) == 1:
                out[entry] = bells[0]
    return out


def _entry_ranges(fn):
    """entry index -> (begin, end) from the `if GetTalkListEntryResult() == N:` dispatch chain.

    Only LITERAL ranges are taken. Every Twin-Maiden re-sell entry is literal (the merchants' own
    talk scripts are the ones that forward `shop1`/`shop2` through call-site kwargs, which is
    `datamine_esd_gates.py`'s problem, not ours).
    """
    out = {}
    for n in ast.walk(fn):
        if not isinstance(n, ast.If):
            continue
        t = n.test
        if not (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq)):
            continue
        if _call_name(t.left) != "GetTalkListEntryResult":
            continue
        entry = _int(t.comparators[0])
        if entry is None:
            continue
        for b in n.body:
            for c in ast.walk(b):
                if _call_name(c) == "OpenRegularShop" and len(c.args) == 2:
                    lo, hi = _int(c.args[0]), _int(c.args[1])
                    if lo is not None and hi is not None:
                        out[entry] = (lo, hi)
    return out


def _handin_maps(tree):
    """The affine goods<->flag pairing, DERIVED from the hand-in helpers rather than hardcoded.

    A hand-in helper does both halves in one function::

        PlayerEquipmentQuantityChange(ItemType.Goods, 8910 + GetTalkListEntryResult() - 1, -1)
        SetEventFlag(11109709 + GetTalkListEntryResult(), FlagState.On)

    Both arguments are affine in the entry index, so each helper yields
    `flag(e) = fa*e + fb` and `goods(e) = ga*e + gb`, and the pair gives flag -> goods for every e.
    Defaults on the enclosing `def` supply the parameter values ESDLang hoisted out (`val2=8910`).
    """
    maps = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        env = {}
        for arg, default in zip(fn.args.args[-len(fn.args.defaults):] if fn.args.defaults else [],
                                fn.args.defaults):
            v = _int(default)
            if v is not None:
                env[arg.arg] = v
        goods = flag = None
        for n in ast.walk(fn):
            if _call_name(n) == "PlayerEquipmentQuantityChange" and len(n.args) >= 2:
                goods = _affine(n.args[1], env)
            elif _call_name(n) == "SetEventFlag" and n.args:
                f = _affine(n.args[0], env)
                # A bare `SetEventFlag(<literal>)` is not the hand-in write; only the affine one is.
                if f and f[0] != 0:
                    flag = f
        if goods and flag and goods[0] == flag[0] != 0:
            maps.append((flag, goods))
    return maps


def _affine(node, env):
    """(a, b) for an expression a*GetTalkListEntryResult() + b, else None."""
    if isinstance(node, ast.Call) and _call_name(node) == "GetTalkListEntryResult":
        return (1, 0)
    if isinstance(node, ast.Name):
        return (0, env[node.id]) if node.id in env else None
    if isinstance(node, ast.Attribute):          # ItemType.Goods and friends -- not affine
        return None
    v = _int(node)
    if v is not None:
        return (0, v)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        lhs, rhs = _affine(node.left, env), _affine(node.right, env)
        if not lhs or not rhs:
            return None
        s = 1 if isinstance(node.op, ast.Add) else -1
        return (lhs[0] + s * rhs[0], lhs[1] + s * rhs[1])
    return None


def goods_for_flag(maps, flag, names):
    """Invert the affine pairing: which goods id hands in as `flag`.

    🛑 The base-game and DLC helpers BOTH have slope 1, so "the first map that divides evenly" is
    not an answer -- it silently resolved every DLC bell against the base run and returned goods
    ids nothing sells. The tie is broken by the only evidence available: the candidate whose FMG
    name is actually a bell bearing. If that is not exactly one, the row is left unresolved rather
    than guessed.
    """
    hits = []
    for (fa, fb), (ga, gb) in maps:
        e, rem = divmod(flag - fb, fa)
        if rem:
            continue
        goods = ga * e + gb
        if "Bell Bearing" in (names.get(goods) or ""):
            hits.append(goods)
    return hits[0] if len(set(hits)) == 1 else None


def scan(pydir):
    src = None
    for fp in glob.glob(os.path.join(pydir, "**", f"t{TWIN_MAIDENS_TALK}.py"), recursive=True):
        src = open(fp, encoding="utf-8").read()
        break
    if src is None:
        sys.exit(f"FATAL: t{TWIN_MAIDENS_TALK}.py not found under {pydir}. Decompile the talk ESD "
                 "first, or run `python tools/gen_inputs.py --ensure elden_ring_artifacts`.")
    tree = ast.parse(src)
    names = load_goods_names()
    maps = _handin_maps(tree)
    if not maps:
        sys.exit("FATAL: no hand-in helper found in the Twin Maidens' ESD -- the script shape "
                 "changed. Refusing to emit a table whose goods ids are unproven.")
    rows, unpaired = [], []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        menu, ranges = _entry_menu_flags(fn), _entry_ranges(fn)
        for entry, flag in sorted(menu.items()):
            rng = ranges.get(entry)
            if rng is None:
                unpaired.append((fn.name, entry, flag))
                continue
            rows.append((flag, goods_for_flag(maps, flag, names), rng[0], rng[1], fn.name))
    return maps, rows, unpaired


# ------------------------------------------------------------------------------------------------
# emit
# ------------------------------------------------------------------------------------------------
def build(pydir):
    maps, rows, unpaired = scan(pydir)
    names = load_goods_names()
    unresolved = []
    seen, out, folds = {}, [], []
    for flag, goods, lo, hi, menu in rows:
        if goods is None:
            unresolved.append((flag, lo, hi))
            continue
        raw = names.get(goods) or ""
        name, changed = ascii_fold(raw)
        if changed:
            folds.append((raw, name))
        # One bell can open TWO ranges (Miriel and Gowry each sell sorceries and incantations from
        # separate blocks). Both rows are real and both are kept; the client sets the same flag
        # whichever shelf you opened.
        key = (flag, lo, hi)
        if key in seen:
            continue
        seen[key] = True
        out.append((flag, goods, name, lo, hi, menu))
    out.sort(key=lambda r: (r[3], r[4]))
    return out, unpaired, folds, maps, unresolved


def overlaps(rows):
    """Ranges must be pairwise disjoint: the client looks a bell up BY the range it observed."""
    bad = []
    ordered = sorted(rows, key=lambda r: (r[3], r[4]))
    for a, b in zip(ordered, ordered[1:]):
        if b[3] <= a[4]:
            bad.append((a, b))
    return bad


def write_tsv(path, rows):
    lines = [
        "# AUTO-GENERATED by tools/datamine_bell_handins.py -- DO NOT EDIT BY HAND.",
        "# Which bell bearing adds which merchant to the Twin Maiden Husks, from the Maidens' own",
        "# talk ESD (t600001110). handin_flag is what `SetEventFlag` writes when you hand the bell",
        "# over; shop_begin..shop_end is the ShopLineupParam range the resulting menu entry opens,",
        "# and it is the merchant's OWN block -- handing in a bell adds a menu entry, it does not",
        "# copy or release stock. Ranges are pairwise disjoint, which is what lets the client look a",
        "# bell up by the range a shop-open handed it.",
        "# NOT HERE: the 12 bells that release rows inside block 1018 by eventFlag_forRelease",
        "# (the peddlers and most of the DLC sellers). They have no menu entry and no range; see the",
        "# module docstring for why guessing their merchant is worse than omitting them.",
        "handin_flag\tbell_goods_id\tbell_name\tshop_begin\tshop_end\tmenu",
    ]
    for flag, goods, name, lo, hi, menu in rows:
        lines.append(f"{flag}\t{goods}\t{name}\t{lo}\t{hi}\t{menu}")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pydir", default=PYDIR_DEFAULT,
                    help="dir of ESDLang-decompiled t*.py (recursed)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--probe", action="store_true", help="print the join; write nothing")
    args = ap.parse_args()

    if not os.path.isdir(args.pydir):
        sys.exit(f"FATAL: {args.pydir} not found. Run "
                 "`python tools/gen_inputs.py --ensure elden_ring_artifacts` first.")

    rows, unpaired, folds, maps, unresolved = build(args.pydir)
    if not rows:
        sys.exit("FATAL: no bell -> shop-range pairs found. Refusing to write an empty table.")
    bad = overlaps(rows)
    if bad:
        for a, b in bad:
            print(f"OVERLAP: {a[2]} {a[3]}..{a[4]} and {b[2]} {b[3]}..{b[4]}", file=sys.stderr)
        sys.exit("FATAL: shop ranges overlap, so a range no longer identifies one bell.")

    print(f"derived {len(maps)} hand-in helper(s): " +
          ", ".join(f"flag={fa}*e+{fb} goods={ga}*e+{gb}" for (fa, fb), (ga, gb) in maps))
    print(f"{len(rows)} bell -> shop-range pair(s)")
    for raw, folded in folds:
        print(f"  ASCII-folded {raw!r} -> {folded!r} (the game's font has no glyph for the original)")
    for flag, lo, hi in unresolved:
        print(f"  UNRESOLVED goods id for flag {flag} ({lo}..{hi}) -- row dropped", file=sys.stderr)
    for fn, entry, flag in unpaired:
        print(f"  no shop range for flag {flag} (menu {fn} entry {entry}) -- not emitted")
    if args.probe:
        for flag, goods, name, lo, hi, menu in rows:
            print(f"  {flag}  goods {goods:>8}  {lo}..{hi}  {name}  [{menu}]")
        return 0
    write_tsv(args.out, rows)
    print(f"Wrote {os.path.relpath(args.out, REPO)}: {len(rows)} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
