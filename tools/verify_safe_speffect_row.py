#!/usr/bin/env python3
"""Prove that a vanilla `SpEffectParam` row is safe to repurpose, straight out of `gen_inputs.db`.

WHY
---
The client rewrites the fields of a handful of vanilla `SpEffectParam` rows at runtime and applies
them to the player: `no_equip_load` (20012080), `no_fall_damage` (20010827) and, since 2026-07-31,
`scadu_blessing` (20012081). Doing that is only safe if the row is genuinely spare -- and until now
"spare" was asserted in a module docstring, in prose, once, by hand. That is not a check. A row that
looks unused but is referenced from, say, an `ItemLotParam` or a `BehaviorParam` would let a feature
silently rewrite something the game actually uses, and the symptom would show up in a playtest weeks
later as "enemies do the wrong thing in one dungeon".

The eligibility criteria live in `er-logic/src/safe_speffect_rows.rs`. This is the instrument that
tests them. No game install, no Smithbox, no regulation.bin: `gen_inputs.db` carries the full 239-
param CSV dump as zlib blobs.

WHAT IT CHECKS
--------------
1. NO-OP        -- every field identical to a row already vetted and shipped (default: 20012080),
                   ignoring the id and name columns. Comparing against a known-good row rather than
                   against a hand-listed table of "neutral values" means the definition of neutral
                   cannot drift away from what is actually shipping.
2. SILENT       -- `iconId` and `vfxId` are -1: no status icon, no particle.
3. PERMANENT    -- `effectEndurance` is -1. A finite duration expires out from under the feature.
                   (This is exactly what makes the vanilla Scadutree rungs DLC-only: they are 0.05s
                   and survive purely because the engine re-applies them, and only in the DLC.)
4. UNREFERENCED -- the id occurs EXACTLY ONCE across all 239 param tables: as its own row. This is
                   the expensive one and the one nobody would do by hand.

USAGE
-----
    python tools/verify_safe_speffect_row.py 20012081
    python tools/verify_safe_speffect_row.py 20012081 20012082 --db gen_inputs.db
    python tools/verify_safe_speffect_row.py --list-candidates    # rows that pass 1-3, for picking

Exit code is non-zero if any requested row fails, so it can be wired into a gate later. Read-only.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sqlite3
import sys
import zlib
from pathlib import Path

PARAM_GLOB = "vanilla_er/vanilla_er/%.csv"
SPEFFECT = "vanilla_er/vanilla_er/SpEffectParam.csv"

# The row every other claim is measured against: shipped since 2026-07-18 in no_equip_load, and the
# reason we know a row of this shape is inert in practice and not just on paper.
REFERENCE_ROW = "20012080"


def _load_csv(db: sqlite3.Connection, path: str) -> list[list[str]]:
    row = db.execute("SELECT blob FROM files WHERE path=?", (path,)).fetchone()
    if row is None:
        sys.exit(f"{path} is not in the bundle -- is this the right gen_inputs.db?")
    txt = zlib.decompress(row[0]).decode("utf-8-sig")
    return list(csv.reader(io.StringIO(txt)))


def _speffect_rows(db):
    rows = _load_csv(db, SPEFFECT)
    header = rows[0]
    return header, {r[0]: r for r in rows[1:] if r}


def _field(header, row, name):
    return row[header.index(name)] if name in header else None


def check_row(header, rows, rid: str, reference: str) -> list[str]:
    """Return a list of problems; empty means the row is eligible."""
    problems = []
    if rid not in rows:
        return [f"row {rid} does not exist in SpEffectParam"]
    ref = rows.get(reference)
    if ref is None:
        return [f"reference row {reference} does not exist -- cannot judge 'no-op'"]

    # 1. no-op: identical to the reference in every column but the id (col 0) and Name (col 1).
    if tuple(rows[rid][1:]) != tuple(ref[1:]):
        diff = [header[i] for i in range(1, len(header))
                if rows[rid][i] != ref[i]]
        problems.append(
            f"NOT a no-op: differs from the vetted reference {reference} in {len(diff)} field(s): "
            + ", ".join(diff[:8]) + (" ..." if len(diff) > 8 else ""))

    # 2. silent, 3. permanent -- checked explicitly even though (1) implies them, because a future
    #    change of REFERENCE_ROW must not be able to quietly relax them.
    for field, want in (("iconId", "-1"), ("vfxId", "-1"), ("effectEndurance", "-1")):
        got = _field(header, rows[rid], field)
        if got is not None and got.strip() != want:
            problems.append(f"{field} is {got!r}, expected {want} "
                            + ("(a finite duration expires out from under the feature)"
                               if field == "effectEndurance" else "(the row must be invisible)"))
    return problems


def cross_reference(db, rid: str) -> list[tuple[str, int]]:
    """Every param table in which the literal id appears, with a count. A safe row appears exactly
    once, in SpEffectParam, as itself."""
    pat = re.compile(r"(?<![0-9])" + re.escape(rid) + r"(?![0-9])")
    hits = []
    paths = [p for (p,) in db.execute(
        "SELECT path FROM files WHERE path LIKE ? ORDER BY path", (PARAM_GLOB,))]
    for p in paths:
        blob = db.execute("SELECT blob FROM files WHERE path=?", (p,)).fetchone()[0]
        txt = zlib.decompress(blob).decode("utf-8-sig", "replace")
        n = len(pat.findall(txt))
        if n:
            hits.append((p.split("/")[-1], n))
    return hits


def list_candidates(header, rows, reference, limit=40):
    ref = tuple(rows[reference][1:])
    out = [rid for rid, r in rows.items() if tuple(r[1:]) == ref]
    out.sort(key=int)
    print(f"{len(out)} rows are field-identical to the vetted reference {reference}.")
    print("(identical is necessary, NOT sufficient -- each still needs the cross-reference sweep)")
    print("first %d: %s" % (min(limit, len(out)), ", ".join(out[:limit])))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows", nargs="*", help="SpEffectParam row ids to verify")
    ap.add_argument("--db", default="gen_inputs.db", type=Path)
    ap.add_argument("--reference", default=REFERENCE_ROW,
                    help=f"already-vetted row to compare against (default {REFERENCE_ROW})")
    ap.add_argument("--list-candidates", action="store_true",
                    help="list rows that pass checks 1-3, to pick a candidate from")
    args = ap.parse_args()

    if not args.db.exists():
        sys.exit(f"{args.db} not found -- run from the repo root")
    db = sqlite3.connect(str(args.db))
    header, rows = _speffect_rows(db)
    print(f"SpEffectParam: {len(rows)} rows, {len(header)} columns "
          f"(from {args.db}, reference row {args.reference})\n")

    if args.list_candidates:
        list_candidates(header, rows, args.reference)
        return 0
    if not args.rows:
        ap.error("give at least one row id, or --list-candidates")

    failed = 0
    for rid in args.rows:
        print(f"=== {rid} ===")
        problems = check_row(header, rows, rid, args.reference)
        for p in problems:
            print(f"  FAIL  {p}")
        if not problems:
            print(f"  ok    no-op, silent, permanent (identical to {args.reference})")

        hits = cross_reference(db, rid)
        expected = [("SpEffectParam.csv", 1)]
        if hits == expected:
            print("  ok    unreferenced: occurs exactly once across all 239 param tables (itself)")
        else:
            problems.append("referenced elsewhere")
            print(f"  FAIL  referenced outside its own row: {hits}")
            print("        Repurposing this row would rewrite something the game reads.")
        failed += bool(problems)
        print(f"  => {rid} is {'ELIGIBLE' if not problems else 'NOT ELIGIBLE'} to repurpose\n")

    if failed:
        print(f"{failed} row(s) failed. Claim a different row; do not relax the criteria.")
    else:
        print("All requested rows are eligible. Record the claim in "
              "er-logic/src/safe_speffect_rows.rs in the SAME commit that uses it.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
