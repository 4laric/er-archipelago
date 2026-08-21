#!/usr/bin/env python3
"""Datamine every shop-opening ESD call's row range -> greenfield/shop_open_ranges.tsv.

WHY (issue #937): a shop MENU shows exactly the ShopLineupParam rows in the (begin, end) range its
ESD passes to the opener -- that range is the display scope of one shelf. The client can give every
AP shop slot its PROPER item name (instead of the shared "Archipelago Items" label) iff no two slots
visible in the SAME menu share a spare preview-goods row; slots in different menus can share a row,
because one menu is open at a time and the client repaints the row's FMG entries at shop open.
features/shops.py assigns spare rows by COLORING against these scopes; this file is the ground truth
for "which slots can be on screen together".

THE OPENER MATTERS. The client's ESD detour currently interprets ONE command's arguments --
`OpenRegularShop` (command 22, the pair the 08-08 probe observed; esd_probe.rs in the client repo).
Rows whose every scope is an OpenRegularShop range are REPAINTABLE: the client rewrites their names
per open, so their spare rows are reusable across menus. Rows shown by any OTHER opener
(OpenTranspositionShop = Enia's remembrance menu, OpenChampionsEquipmentShop, OpenDragonCommunionShop,
OpenDupeShop = the Walking Mausoleums, OpenPuppetShop) get no repaint until those command ids are
probed, so their baseline label must stand alone -- shops.py gives them PRIVATE rows first. Hence the
opener column: it is the repaintability bit, not decoration.

CALL SHAPES the harvest must cover (all measured in the current corpus, 2026-08-21):
  * literal:   OpenRegularShop(100500, 100524)
  * 3-arg:     OpenDupeShop(False, 100300, 100309)          (leading bool: dupe-with-cost flag)
  * variable:  OpenRegularShop(shop1, shop2) inside a state fn `tNNN_xNN(...)`, with the range
               arriving as call-site kwargs `shop1=..., shop2=...` -- the nomadic-merchant shape.
               The fn->opener join slices to the next TOP-LEVEL `def t` (nested WhilePaused defs
               otherwise truncate the body before the opener call).
OpenSellShop is EXCLUDED: a sell menu displays the player's bag, not lineup rows.

Measured: 62 scopes, 8 opener kinds; 577/679 derived check rows covered (404 repaintable-only); the
busiest scopes are Enia's transposition 101898..101949 (51 checks) and the Twin Maiden re-sell
101800..101897 (31). The 102 uncovered rows (Dragon Communion spell rows 9000xx, mausoleum dupe rows
16001xx/16004xx, remembrance rows 1017xx, ...) open via ranges the text corpus does not carry as
harvestable literals; the coloring buckets them per shop block, which is the same-menu superset.

Input: elden_ring_artifacts/talk/<map-dir>/tNNNNNNNNN.py (the DECOMPILED text corpus). If the corpus
ever regresses to binary EzState, the zero-hit FATAL fires rather than emitting an empty truth file.
"""
import glob
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ER_REPO") or os.path.abspath(os.path.join(HERE, ".."))
TALK = os.path.join(REPO, "elden_ring_artifacts", "talk")
OUT = os.path.join(REPO, "greenfield", "shop_open_ranges.tsv")
SHOP_ROWS = os.path.join(REPO, "greenfield", "shop_rows.tsv")

MAX_RANGE_SPAN = 2000
LIT = re.compile(rb"(Open\w*Shop)\s*\(\s*(?:True|False)?\s*,?\s*(\d+)\s*,\s*(\d+)\s*\)")
VAR = re.compile(rb"(Open\w*Shop)\((?:True, |False, )?shop1, shop2\)")
DEF = re.compile(rb"def (t\d+_x\d+)\(")
CALL = re.compile(rb"(t\d+_x\d+)\(([^)]*)\)")
KW = re.compile(rb"shop1=(\d+), shop2=(\d+)")
EXCLUDED = {"OpenSellShop"}


def check_row_ids():
    """The derived shop-check rows (shop_rows.tsv) -- for the count column and the coverage report.
    Refuses without them: a display-scope file that cannot be cross-checked against the checks it
    exists to scope would be an unverifiable truth file."""
    if not os.path.isfile(SHOP_ROWS):
        sys.exit("FATAL: greenfield/shop_rows.tsv missing -- run tools/datamine_shop_rows.py first. "
                 "Nothing written.")
    rows, hdr = set(), None
    with open(SHOP_ROWS, encoding="utf-8-sig") as fh:
        for ln in fh:
            if ln.startswith("#") or not ln.strip():
                continue
            parts = ln.rstrip("\n").split("\t")
            if hdr is None:
                hdr, rid = parts, parts.index("row_id")
                continue
            rows.add(int(parts[rid]))
    return rows


def sane(a, b):
    return 0 < a <= b and b - a <= MAX_RANGE_SPAN


def main():
    if not os.path.isdir(TALK):
        sys.exit("FATAL: %s missing -- run tools/gen_inputs.py --ensure elden_ring_artifacts. "
                 "Nothing written." % TALK)
    files = sorted(glob.glob(os.path.join(TALK, "*", "t*.py")))
    if not files:
        sys.exit("FATAL: no talk ESDs under %s -- corpus layout changed? Nothing written." % TALK)

    scopes = defaultdict(set)  # (opener, begin, end) -> {talk_id}
    for path in files:
        with open(path, "rb") as fh:
            raw = fh.read()
        tid = os.path.splitext(os.path.basename(path))[0]
        for op, a, b in LIT.findall(raw):
            op, a, b = op.decode("ascii"), int(a), int(b)
            if op not in EXCLUDED and sane(a, b):
                scopes[(op, a, b)].add(tid)
        # variable form: which state fns pass (shop1, shop2) to an opener, and what call-site
        # kwargs feed them. Slice each fn body to the next TOP-LEVEL def.
        fn_op = {}
        for m in DEF.finditer(raw):
            nxt = raw.find(b"\ndef t", m.end())
            vm = VAR.search(raw[m.end(): nxt if nxt > 0 else len(raw)])
            if vm:
                fn_op[m.group(1)] = vm.group(1).decode("ascii")
        if fn_op:
            for m in CALL.finditer(raw):
                op = fn_op.get(m.group(1))
                if op is None or op in EXCLUDED:
                    continue
                km = KW.search(m.group(2))
                if km:
                    a, b = int(km.group(1)), int(km.group(2))
                    if sane(a, b):
                        scopes[(op, a, b)].add(tid)
    if not scopes:
        sys.exit("FATAL: %d talk files scanned and ZERO shop-open ranges found -- the decompiled-"
                 "text premise broke (binary corpus?). Nothing written." % len(files))

    checks = check_row_ids()
    covered = set()
    for (_, a, b) in scopes:
        covered.update(r for r in checks if a <= r <= b)
    orphans = sorted(checks - covered)
    if orphans:
        # Informational, not fatal: shops.py buckets rangeless rows per shop block (the same-menu
        # superset), and these menus are all non-repaintable anyway. But say it -- silence is how a
        # display-scope truth file rots.
        print("NOTE: %d check row(s) in no harvested scope (per-block bucketing applies): "
              "first %s" % (len(orphans), orphans[:8]))

    with open(OUT, "w", newline="\n", encoding="utf-8") as f:
        f.write("# AUTO-GENERATED by tools/datamine_shop_open_ranges.py -- every shop-opener call's\n")
        f.write("# (begin, end) ShopLineupParam range in the talk corpus: the display scope of one\n")
        f.write("# shop menu (issue #937). opener is the REPAINTABILITY bit: the client rewrites\n")
        f.write("# names at shop open only for OpenRegularShop (its ESD command-22 detour); rows\n")
        f.write("# shown by any other opener need baseline-unique spare rows. features/shops.py\n")
        f.write("# colors spare preview rows against these scopes. talk_ids is provenance.\n")
        f.write("opener\tbegin\tend\tcheck_rows\ttalk_ids\n")
        for (op, a, b) in sorted(scopes):
            n = sum(1 for r in checks if a <= r <= b)
            f.write("%s\t%d\t%d\t%d\t%s\n" % (op, a, b, n, ";".join(sorted(scopes[(op, a, b)]))))
    print("shop_open_ranges: %d scope(s), %d opener kind(s); %d/%d check rows covered -> %s"
          % (len(scopes), len({op for (op, _, _) in scopes}), len(covered), len(checks),
             os.path.relpath(OUT, REPO)))


if __name__ == "__main__":
    main()
