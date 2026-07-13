#!/usr/bin/env python3
"""Derive shoplineup_flags.json -- {ShopLineupParam row id: eventFlag_forStock} -- for the
matt-key (bedrock) shop resolver.

WHY THIS TABLE EXISTS
---------------------
A foreign (bedrock, fswap/archipelago@er) apworld does not emit `locationFlags`; its shop slots
travel as matt slot keys in `locationIdsToKeys` with token1 == 0000000000 and their
ShopLineupParam row ids in token3.  The client resolves those rows to pollable check flags via
`key_resolver.rs::shop_flags_from_keys`, which needs exactly this lookup:

    row id -> eventFlag_forStock          (the flag the game flips when the slot's stock changes)

loaded at connect by `key_resolver.rs::load_shoplineup_flags` from the DLL/mod directory.
`build.ps1` stages it there from `Archipelago\\worlds\\eldenring\\shoplineup_flags.json`, which is
why the OUTPUT LIVES INSIDE THE WORLD PACKAGE (`greenfield/eldenring/`): the .apworld ships it,
and installing the world puts it exactly where build.ps1 already looks.  Without this file
`load_shoplineup_flags` returns empty and every foreign shop check silently never fires -- the
Rust logic is sound, only the table was missing (main's 3530038 deleted the stale v0.1 copy at
`me3/shoplineup_flags.json` and nothing regenerated it; this tool is the regeneration).

THE PREDICATE
-------------
    eventFlag_forStock > 0

and nothing else.  Note this is DELIBERATELY WIDER than our own world's shop-check predicate
(`tools/datamine_shop_rows.py` additionally requires sellQuantity >= 1, because for an UNLIMITED
row the stock flag is an unlock gate, not a purchase record).  Here the table is not a check
SELECTION -- it is a row->flag LOOKUP for shop slots a foreign apworld already chose; dropping
the unlimited rows would turn those slots from "may fire on unlock" into "never fires at all",
which is strictly worse and invisible.  Measured against the foreign key set (2026-07-12):
exactly one referenced winning row is unlimited (100225, Iji's shop, sellQuantity=-1), carried
by 5 shop keys.  Content-equal to the retired v0.1 table (822 entries, verified against the
blob at 3530038^:me3/shoplineup_flags.json).

ShopLineupParam_Recipe.csv is EXCLUDED: measured zero rows with a nonzero eventFlag_forStock
(188/188 are flagless), so it contributes nothing.  The tool ASSERTS that stays true when the
csv is present -- if a future param dump grows a flagged recipe row, this fails loudly instead
of silently shrinking coverage.

Determinism: numeric key sort, one entry per line, LF, pure-ASCII, utf-8 write.

USAGE
    python tools/gen_shoplineup_flags.py            # regenerate greenfield/eldenring/shoplineup_flags.json
    python tools/gen_shoplineup_flags.py --check    # drift gate: exit 0 fresh, 3 stale, 4 cannot-check
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SLP_DIR = os.path.join(REPO, "elden_ring_artifacts", "vanilla_er", "vanilla_er")
OUT = os.path.join(REPO, "greenfield", "eldenring", "shoplineup_flags.json")


def derive():
    """{row_id(int): eventFlag_forStock(int)} for every ShopLineupParam row with a nonzero flag."""
    path = os.path.join(SLP_DIR, "ShopLineupParam.csv")
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            flag = int(r["eventFlag_forStock"])
            if flag > 0:
                out[int(r["ID"])] = flag
    # Recipe guard: today it contributes NOTHING (0/188 rows carry a stock flag). Assert that,
    # so a param dump that changes it fails the regen instead of silently losing coverage.
    recipe = os.path.join(SLP_DIR, "ShopLineupParam_Recipe.csv")
    if os.path.isfile(recipe):
        with open(recipe, newline="", encoding="utf-8-sig") as fh:
            flagged = [r["ID"] for r in csv.DictReader(fh) if int(r["eventFlag_forStock"]) > 0]
        if flagged:
            raise SystemExit(
                "ShopLineupParam_Recipe.csv now has %d rows with a stock flag (e.g. %s) -- the "
                "'recipes contribute nothing' assumption broke; extend derive() to include them."
                % (len(flagged), flagged[:5]))
    return out


def render(table):
    """Deterministic JSON: numeric key order, one entry per line (diff-friendly), LF, ASCII."""
    lines = ",\n".join('"%d": %d' % (k, table[k]) for k in sorted(table))
    return "{\n" + lines + "\n}\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify the committed table is fresh")
    args = ap.parse_args()

    if not os.path.isfile(os.path.join(SLP_DIR, "ShopLineupParam.csv")):
        # Exit codes mirror tools/gen_manifest.py: 4 = cannot-check (inputs absent), not "stale".
        print("SKIP: elden_ring_artifacts/vanilla_er/vanilla_er/ShopLineupParam.csv absent -- "
              "cannot %s shoplineup_flags.json here" % ("check" if args.check else "regenerate"))
        sys.exit(4 if args.check else 0)

    table = derive()
    text = render(table)
    if args.check:
        try:
            with open(OUT, encoding="utf-8") as fh:
                committed = fh.read()
        except FileNotFoundError:
            committed = None
        if committed != text:
            print("STALE: %s does not match a fresh derivation -- rerun tools/gen_shoplineup_flags.py"
                  % os.path.relpath(OUT, REPO))
            sys.exit(3)
        print("OK: shoplineup_flags.json is fresh (%d rows)" % len(table))
        sys.exit(0)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s (%d rows)" % (os.path.relpath(OUT, REPO), len(table)))


if __name__ == "__main__":
    main()
